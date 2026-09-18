"""HTTP adapter. Operational decisions live in corporate_engine."""
from __future__ import annotations

import base64
import json
import re
import shutil
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from corporate_engine import facade as engine
from corporate_engine import corporate_expediente as corp
from corporate_engine import corporate_areas as areas
from corporate_engine import corporate_agents as agents
from corporate_engine import corporate_workflow as workflow
from corporate_engine import corporate_platform_exec as platform_exec
from corporate_engine import corporate_board as board
from corporate_engine import corporate_calendar as calendar
from corporate_engine import corporate_communications as communications
from corporate_engine import corporate_notifications as notifications
from corporate_engine import corporate_automation as automation
from corporate_engine import providers as connectors
from corporate_engine import calendar_sync
from corporate_engine import email_gate
from corporate_engine import email_sync
from corporate_engine import google_oauth
from corporate_engine.executive_intel import board as executive_board_mod
from corporate_engine.executive_intel import weather as executive_weather
from corporate_engine.executive_intel import chile_indicators as executive_chile
from corporate_engine.executive_intel import news as executive_news
from corporate_engine.executive_intel import alerts as executive_alerts
from corporate_engine.errors import Conflict
from corporate_engine.platform import classify_platform_error


def read_json(path, default=None):
    if not path.is_file():
        return default
    for attempt in range(5):
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            if attempt == 4:
                raise
            time.sleep(.03)


class CorporateWebAPI:
    def __init__(self, mgc05_root: Path, mgc03_root: Path, corporate_root: Path | None = None):
        self.mgc05_root, self.mgc03_root = Path(mgc05_root), Path(mgc03_root)
        parent = self.mgc03_root.parent if self.mgc03_root.parent.name == "outputs" else self.mgc03_root.parent
        self.corporate_root = Path(corporate_root) if corporate_root is not None else (parent / "lnh_corporate")
        self._guard = threading.RLock()
        self._active = {}

    def health(self):
        return {
            "status": "ok",
            "service": "LNH Corporate API",
            "workspace_api": 1,
            "corporate_expedientes": 1,
            "corporate_routing": 1,
            "corporate_platform_exec": 1,
            "corporate_directorio": 1,
            "corporate_calendar": 1,
            "corporate_communications": 1,
            "corporate_notifications": 1,
            "corporate_google_calendar": 1,
            "corporate_gmail": 1,
            "schema": "LNH-DATA-001",
            "block": "F2B-2",
            "fase": "2B",
            "lnh_agents_missing": agents.missing_agent_ids(),
            "lnh_directors_ids_missing": agents.missing_director_ids(),
            "platform_calls": 0,
            "google_auth": connectors.providers_board().get("google_oauth", {}).get("status"),
        }

    def hierarchy(self):
        return engine.hierarchy()

    def root(self, floor):
        if floor not in engine.FLOORS:
            raise ValueError("Piso no registrado.")
        return (self.mgc05_root if floor == "MGC-05" else self.mgc03_root).resolve()

    def directory(self, floor, case_id):
        root = self.root(floor)
        if not case_id or re.search(r'[\\/:\x00]', case_id) or case_id in (".", ".."):
            raise ValueError("Identificador de expediente no válido.")
        case = (root / case_id).resolve()
        if case.parent != root or not (case / "case.json").is_file():
            raise FileNotFoundError("Expediente no encontrado.")
        return case

    def jobs(self, case):
        with self._guard:
            records = [read_json(p) for p in sorted((case / "web_jobs").glob("*.json"))]
            active = self._active.get(str(case))
            for job in records:
                if job["status"] == "running" and (not active or active["id"] != job["id"]):
                    job.update(status="interrupted", error="La API se reinició durante la operación. Revise los artefactos antes de reintentar.")
        return sorted(records, key=lambda j: j["started_at"])

    def case(self, floor_id, case_id, version=None):
        case = self.directory(floor_id, case_id)
        return engine.case_view(case, floor_id, version, jobs=self.jobs(case))

    def cases(self, floor_id=None):
        rows = []
        floors = [floor_id] if floor_id else list(engine.FLOORS)
        for floor in floors:
            if floor not in engine.FLOORS:
                raise ValueError("Piso no registrado.")
            for path in sorted(self.root(floor).glob("*/case.json"), reverse=True):
                item = self.case(floor, path.parent.name)
                rows.append({k: item[k] for k in ("case_id", "floor_id", "mission", "status")} | {
                    "documents": len(item["documents"]),
                    "latest_version": item["latest"].get("version"),
                    "has_report": bool(item["outputs"].get(engine.CONSOLIDATION_NAME)),
                    "requires_decision": item["capabilities"]["approve"] and item.get("active_business"),
                    "busy": any(j["status"] == "running" for j in item["jobs"]),
                    "archive_class": (item.get("raw") or {}).get("archive_class"),
                    "active_business": item.get("active_business"),
                })
        return rows

    def create(self, mission, floor, documents):
        if not isinstance(mission, str) or not mission.strip():
            raise ValueError("La misión es obligatoria.")
        root = self.root(floor)
        if not isinstance(documents, list) or len(documents) > 50:
            raise ValueError("Adjunte hasta 50 documentos.")
        with tempfile.TemporaryDirectory() as tmp:
            paths = []
            for index, item in enumerate(documents):
                name = item.get("name", "") if isinstance(item, dict) else ""
                if not isinstance(name, str) or not name or re.search(r'[\\/:\x00]', name) or name in (".", ".."):
                    raise ValueError("Nombre de documento no válido.")
                if Path(name).suffix.lower() not in {".txt", ".md", ".pdf", ".docx", ".csv", ".xlsx"}:
                    raise ValueError("Formato admitido: TXT, MD, PDF, DOCX, CSV o XLSX.")
                try:
                    content = base64.b64decode(item["content"], validate=True)
                except (ValueError, KeyError, TypeError) as error:
                    raise ValueError("Contenido del documento no válido.") from error
                target = Path(tmp) / str(index) / name
                target.parent.mkdir()
                target.write_bytes(content)
                paths.append(target)
            with self._guard:
                if floor != "MGC-03":
                    raise ValueError(
                        "Sólo MGC-03 está habilitado en la plataforma corporativa de agentes. "
                        "MGC-05 quedó como piloto retirado; no se crean expedientes nuevos en ese runtime."
                    )
                try:
                    case = engine.open_case(root, floor_id="MGC-03", mission_text=mission.strip(), paths=paths)
                except FileExistsError as error:
                    raise Conflict("Ya se registró esta instrucción en este segundo. Abra el expediente existente o reintente.") from error
            return self.case(floor, case.name)

    def artifact(self, floor, case_id, name):
        case = self.directory(floor, case_id)
        target = (case / name).resolve()
        if not name or not target.is_relative_to(case) or not target.is_file():
            raise FileNotFoundError("Archivo no encontrado en el expediente.")
        return target

    def _materialize_documents(self, documents):
        if not isinstance(documents, list) or len(documents) > 50:
            raise ValueError("Adjunte hasta 50 documentos.")
        paths = []
        tmp = Path(tempfile.mkdtemp(prefix="lnh-corp-docs-"))
        try:
            for index, item in enumerate(documents):
                name = item.get("name", "") if isinstance(item, dict) else ""
                if not isinstance(name, str) or not name or re.search(r'[\\/:\x00]', name) or name in (".", ".."):
                    raise ValueError("Nombre de documento no válido.")
                if Path(name).suffix.lower() not in {".txt", ".md", ".pdf", ".docx", ".csv", ".xlsx"}:
                    raise ValueError("Formato admitido: TXT, MD, PDF, DOCX, CSV o XLSX.")
                try:
                    content = base64.b64decode(item["content"], validate=True)
                except (ValueError, KeyError, TypeError) as error:
                    raise ValueError("Contenido del documento no válido.") from error
                target = tmp / str(index) / name
                target.parent.mkdir(parents=True)
                target.write_bytes(content)
                paths.append(target)
            return tmp, paths
        except Exception:
            shutil.rmtree(tmp, ignore_errors=True)
            raise

    def create_corporate_expediente(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Se requiere un objeto JSON.")
        tmp = None
        try:
            tmp, paths = self._materialize_documents(payload.get("documents") or [])
            with self._guard:
                self.corporate_root.mkdir(parents=True, exist_ok=True)
                try:
                    case = corp.open_corporate_expediente(
                        self.corporate_root,
                        tipo=payload.get("tipo"),
                        ambito=payload.get("ambito"),
                        prioridad=payload.get("prioridad") or "P2",
                        asunto=payload.get("asunto"),
                        instruccion_original=payload.get("instruccion_original") or payload.get("instruccion"),
                        fecha_objetivo=payload.get("fecha_objetivo") or None,
                        creado_por=payload.get("creado_por") or corp.ACTOR_PRESIDENCIA,
                        clasificacion_seguridad=payload.get("clasificacion_seguridad"),
                        expediente_padre=payload.get("expediente_padre"),
                        paths=paths,
                    )
                except FileExistsError as error:
                    raise Conflict(
                        "Ya se registró esta instrucción en este segundo. Abra el expediente existente o reintente."
                    ) from error
                master = corp.load_expediente(case)
                for key in (
                    "area_competente", "area_solicitante", "area_responsable",
                    "funcion_propietaria", "obligacion_contractual", "remitir_directorio",
                ):
                    if key in payload:
                        master[key] = payload.get(key)
                corp.save_expediente(case, master)
                if payload.get("apply_routing", True):
                    workflow.apply_routing(case)
            return corp.expediente_view(case)
        finally:
            if tmp is not None:
                shutil.rmtree(tmp, ignore_errors=True)

    def corporate_expedientes(self):
        return corp.list_expedientes(self.corporate_root)

    def corporate_expediente(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        view = corp.expediente_view(case)
        # Live relation views (IDs/refs) — do not duplicate document bodies.
        view["calendar_events"] = calendar.events_for_expediente(self.corporate_root, expediente_id)
        view["communications"] = communications.communications_for_expediente(
            self.corporate_root, expediente_id
        )
        view["notifications"] = notifications.notifications_for_expediente(
            self.corporate_root, expediente_id
        )
        return view

    def corporate_expediente_events(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        return corp.events_view(case)

    def corporate_areas(self):
        return areas.list_areas()

    def corporate_agents(self):
        return agents.status_board(self.corporate_root)

    def corporate_routing(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        return workflow.routing_view(case)

    def apply_corporate_routing(self, expediente_id, payload=None):
        case = corp.directory(self.corporate_root, expediente_id)
        with self._guard:
            workflow.apply_routing(case, payload or {})
        return workflow.routing_view(case)

    def corporate_tasks(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        return workflow.tasks_view(case)

    def update_corporate_task(self, expediente_id, task_id, payload):
        if not isinstance(payload, dict):
            raise ValueError("Se requiere un objeto JSON.")
        case = corp.directory(self.corporate_root, expediente_id)
        with self._guard:
            return workflow.update_task_status(
                case,
                task_id,
                payload.get("status"),
                actor=payload.get("actor") or "Mission Control",
                result_id=payload.get("result_id"),
                motivo=payload.get("motivo") or "",
            )

    def corporate_dependencies(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        return workflow.dependencies_view(case)

    def create_corporate_dependency(self, expediente_id, payload):
        if not isinstance(payload, dict):
            raise ValueError("Se requiere un objeto JSON.")
        case = corp.directory(self.corporate_root, expediente_id)
        with self._guard:
            return workflow.add_dependency(
                case,
                payload.get("prerequisite_task_id"),
                payload.get("dependent_task_id"),
            )

    def corporate_overdues(self, expediente_id=None):
        if expediente_id:
            case = corp.directory(self.corporate_root, expediente_id)
            with self._guard:
                return workflow.overdues_view(case)
        rows = []
        for item in corp.list_expedientes(self.corporate_root):
            case = corp.directory(self.corporate_root, item["expediente_id"])
            with self._guard:
                for overdue in workflow.overdues_view(case):
                    rows.append({"expediente_id": item["expediente_id"], **overdue})
        return rows

    def corporate_results(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        return list(corp.load_expediente(case).get("resultados") or [])

    def corporate_sessions(self, expediente_id):
        case = corp.directory(self.corporate_root, expediente_id)
        return list(corp.load_expediente(case).get("platform_sessions") or [])

    def board_sessions(self):
        return board.list_board_sessions(self.corporate_root)

    def board_session(self, board_session_id):
        return board.board_session_view(self.corporate_root, board_session_id)

    # —— Fase 2B-1 Calendar / Communications / Notifications ——

    def calendar_events(self, query=None):
        query = query or {}
        return calendar.list_events(
            self.corporate_root,
            event_type=(query.get("tipo") or [None])[0] or (query.get("event_type") or [None])[0],
            status=(query.get("estado") or [None])[0] or (query.get("status") or [None])[0],
            expediente_id=(query.get("expediente") or [None])[0] or (query.get("expediente_id") or [None])[0],
            company_scope=(query.get("empresa") or [None])[0] or (query.get("company_scope") or [None])[0],
            date_from=(query.get("desde") or [None])[0] or (query.get("date_from") or [None])[0],
            date_to=(query.get("hasta") or [None])[0] or (query.get("date_to") or [None])[0],
        )

    def calendar_event(self, event_id):
        return calendar.event_view(self.corporate_root, event_id)

    def create_calendar_event(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return calendar.create_event(
                self.corporate_root,
                payload,
                actor=payload.get("actor") or payload.get("created_by") or "Presidencia LNH",
            )

    def update_calendar_event_status(self, event_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return calendar.update_event_status(
                self.corporate_root,
                event_id,
                payload.get("status") or payload.get("estado"),
                actor=payload.get("actor") or "Presidencia LNH",
                motivo=payload.get("motivo") or "",
            )

    def communications(self, query=None):
        query = query or {}
        return communications.list_communications(
            self.corporate_root,
            channel=(query.get("canal") or [None])[0] or (query.get("channel") or [None])[0],
            status=(query.get("estado") or [None])[0] or (query.get("status") or [None])[0],
            direction=(query.get("direccion") or [None])[0] or (query.get("direction") or [None])[0],
            expediente_id=(query.get("expediente") or [None])[0] or (query.get("expediente_id") or [None])[0],
        )

    def communication(self, communication_id):
        return communications.communication_view(self.corporate_root, communication_id)

    def create_communication(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return communications.create_communication(
                self.corporate_root,
                payload,
                actor=payload.get("actor") or payload.get("created_by") or "Presidencia LNH",
            )

    def notifications(self, query=None):
        query = query or {}
        rows = notifications.list_notifications(
            self.corporate_root,
            status=(query.get("estado") or [None])[0] or (query.get("status") or [None])[0],
            notif_type=(query.get("tipo") or [None])[0] or (query.get("type") or [None])[0],
            expediente_id=(query.get("expediente") or [None])[0] or (query.get("expediente_id") or [None])[0],
        )
        return {
            "notifications": rows,
            "unread_count": notifications.unread_count(self.corporate_root),
            "platform_calls": 0,
        }

    def mark_notification_read(self, notification_id, payload=None):
        with self._guard:
            return notifications.mark_read(self.corporate_root, notification_id)

    def archive_notification(self, notification_id, payload=None):
        with self._guard:
            return notifications.archive_notification(self.corporate_root, notification_id)

    def create_notification(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return notifications.create_notification(
                self.corporate_root,
                payload,
                actor=payload.get("actor") or "SYSTEM",
            )

    def expediente_calendar_events(self, expediente_id):
        corp.directory(self.corporate_root, expediente_id)
        return calendar.events_for_expediente(self.corporate_root, expediente_id)

    def expediente_communications(self, expediente_id):
        corp.directory(self.corporate_root, expediente_id)
        return communications.communications_for_expediente(self.corporate_root, expediente_id)

    def expediente_notifications(self, expediente_id):
        corp.directory(self.corporate_root, expediente_id)
        return notifications.notifications_for_expediente(self.corporate_root, expediente_id)

    def providers_status(self):
        return connectors.providers_board()

    def google_oauth_status(self):
        return google_oauth.google_auth_state()

    def save_google_provider_config(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return google_oauth.save_provider_config(payload)

    def whatsapp_status(self):
        from corporate_engine import whatsapp_config as wa_cfg
        return wa_cfg.whatsapp_auth_state()

    def save_whatsapp_provider_config(self, payload=None):
        from corporate_engine import whatsapp_config as wa_cfg
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return wa_cfg.save_provider_config(payload)

    def executive_board(self, query=None):
        query = query or {}
        force = str((query.get("force") or [None])[0] or "").lower() in {"1", "true", "yes"}
        return executive_board_mod.executive_board(self.corporate_root, force=force)

    def executive_weather(self, query=None):
        query = query or {}
        force = str((query.get("force") or [None])[0] or "").lower() in {"1", "true", "yes"}
        return executive_weather.fetch_santiago_weather(corporate_root=self.corporate_root, force=force)

    def executive_economy(self, query=None):
        query = query or {}
        force = str((query.get("force") or [None])[0] or "").lower() in {"1", "true", "yes"}
        return executive_chile.fetch_chile_economy(corporate_root=self.corporate_root, force=force)

    def executive_markets(self, query=None):
        query = query or {}
        force = str((query.get("force") or [None])[0] or "").lower() in {"1", "true", "yes"}
        return executive_chile.fetch_copper_market(corporate_root=self.corporate_root, force=force)

    def executive_news(self, query=None):
        query = query or {}
        force = str((query.get("force") or [None])[0] or "").lower() in {"1", "true", "yes"}
        category = (query.get("category") or [None])[0]
        try:
            limit = int((query.get("limit") or [12])[0] or 12)
        except (TypeError, ValueError):
            limit = 12
        return executive_news.fetch_executive_news(
            corporate_root=self.corporate_root,
            force=force,
            category=category,
            limit=max(1, min(limit, 30)),
        )

    def executive_alerts(self, query=None):
        query = query or {}
        force_scan = str((query.get("scan") or [None])[0] or "").lower() in {"1", "true", "yes"}
        estado = (query.get("estado") or [None])[0]
        try:
            limit = int((query.get("limit") or [40])[0] or 40)
        except (TypeError, ValueError):
            limit = 40
        with self._guard:
            listing_meta = executive_alerts.list_executive_alerts(self.corporate_root, limit=1)
            updated_at = listing_meta.get("updated_at")
            stale = True
            if updated_at:
                from datetime import datetime, timezone
                try:
                    text = str(updated_at)
                    if text.endswith("Z"):
                        text = text[:-1] + "+00:00"
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(text)).total_seconds()
                    stale = age > 120
                except ValueError:
                    stale = True
            if force_scan or not updated_at or stale:
                floor_cases = self.cases()
                executive_alerts.scan_executive_alerts(
                    self.corporate_root,
                    floor_cases=floor_cases,
                    include_external=True,
                )
            return executive_alerts.list_executive_alerts(
                self.corporate_root,
                estado=estado,
                limit=max(1, min(limit, 200)),
            )

    def scan_executive_alerts(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            floor_cases = self.cases()
            summary = executive_alerts.scan_executive_alerts(
                self.corporate_root,
                floor_cases=floor_cases,
                include_external=bool(payload.get("include_external", True)),
            )
            listing = executive_alerts.list_executive_alerts(
                self.corporate_root,
                estado=payload.get("estado"),
                limit=int(payload.get("limit") or 40),
            )
            return {**summary, "alerts": listing.get("alerts") or [], "platform_calls": 0}

    def set_executive_alert_state(self, alert_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return executive_alerts.set_alert_state(
                self.corporate_root,
                alert_id,
                estado=payload.get("estado") or payload.get("status"),
                actor=payload.get("actor") or "Presidencia LNH",
                note=payload.get("note") or payload.get("motivo") or "",
            )

    def refresh_executive_board(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return executive_board_mod.executive_board(
                self.corporate_root,
                force=bool(payload.get("force", True)),
            )

    def sync_calendar_event(self, event_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return calendar_sync.push_event_to_google(
                self.corporate_root,
                event_id,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def sync_calendar_push(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return calendar_sync.push_pending_local(
                self.corporate_root,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def sync_calendar_pull(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return calendar_sync.pull_from_google(
                self.corporate_root,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def submit_communication_approval(self, communication_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return email_gate.submit_for_approval(
                self.corporate_root,
                communication_id,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def communication_human_gate(self, communication_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return email_gate.human_gate_decision(
                self.corporate_root,
                communication_id,
                decision=payload.get("decision") or payload.get("accion"),
                rationale=payload.get("rationale") or payload.get("motivo") or "",
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def update_communication_content(self, communication_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return email_gate.update_email_content(
                self.corporate_root,
                communication_id,
                payload,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def send_communication(self, communication_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return email_gate.queue_and_send(
                self.corporate_root,
                communication_id,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def sync_email_pull(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return email_sync.pull_inbound_email(
                self.corporate_root,
                actor=payload.get("actor") or "SYSTEM",
                query=payload.get("query") or "in:inbox",
                max_results=int(payload.get("max_results") or 25),
            )

    def link_communication_expediente(self, communication_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return communications.link_communication_to_expediente(
                self.corporate_root,
                communication_id,
                payload.get("expediente_id") or payload.get("expediente"),
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def mark_communication_read(self, communication_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return communications.mark_communication_read(
                self.corporate_root,
                communication_id,
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def run_f2b_sync(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        floor_cases = payload.get("floor_cases")
        with self._guard:
            return automation.run_deterministic_sync(
                self.corporate_root,
                floor_cases=floor_cases,
                pull_email=payload.get("pull_email", True),
            )

    def create_board_session(self, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.create_board_session(
                self.corporate_root,
                tipo=payload.get("tipo") or "ordinaria",
                fecha=payload.get("fecha"),
                agenda=payload.get("agenda"),
                expediente_ids=payload.get("expediente_ids"),
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def update_board_session(self, board_session_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.update_board_session(self.corporate_root, board_session_id, payload)

    def prepare_board_session(self, board_session_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.prepare_antecedents(
                self.corporate_root, board_session_id,
                actor=payload.get("actor") or "Mission Control",
            )

    def freeze_board_session(self, board_session_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.freeze_antecedents(
                self.corporate_root, board_session_id,
                actor=payload.get("actor") or "Mission Control",
            )

    def deliberate_board_session(self, board_session_id, payload=None):
        """Starts isolated deliberation. Uses Platform only when invoked; never auto on create."""
        payload = payload if isinstance(payload, dict) else {}
        key = f"board:{board_session_id}:deliberate"
        with self._guard:
            if key in self._active:
                raise Conflict("Ya hay una deliberación en curso para esta sesión.")
            job = {
                "id": uuid4().hex,
                "action": "DELIBERATE",
                "board_session_id": board_session_id,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            self._active[key] = job

            def work():
                try:
                    result = board.run_independent_deliberation(
                        self.corporate_root,
                        board_session_id,
                        actor=payload.get("actor") or "Mission Control",
                    )
                    job["status"] = "completed"
                    job["board_estado"] = result.get("estado")
                    job["blocked"] = bool((result.get("resultado") or {}).get("blocked"))
                    job["error_kind"] = (result.get("resultado") or {}).get("reason")
                except Exception as error:
                    kind = classify_platform_error(error)
                    job["status"] = "failed"
                    job["error"] = str(error)
                    job["error_kind"] = kind
                finally:
                    job["finished_at"] = datetime.now(timezone.utc).isoformat()
                    with self._guard:
                        self._active.pop(key, None)

            # Sync path when payload.sync=true (tests); async default for UI
            if payload.get("sync"):
                work()
                return {**job, **({"session": board.board_session_view(self.corporate_root, board_session_id)} if job.get("status") == "completed" else {})}
            threading.Thread(target=work, daemon=True).start()
            return dict(job)

    def consolidate_board_session(self, board_session_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.consolidate_board_session(
                self.corporate_root, board_session_id,
                actor=payload.get("actor") or "LNH Backend",
            )

    def board_presidency_decision(self, board_session_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.presidency_decision(
                self.corporate_root,
                board_session_id,
                decision=payload.get("decision"),
                rationale=payload.get("rationale") or payload.get("fundamento") or "",
                conditions=payload.get("conditions") or payload.get("condiciones"),
                actor=payload.get("actor") or "Presidencia LNH",
                expediente_id=payload.get("expediente_id"),
            )

    def reopen_corporate_expediente(self, expediente_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        with self._guard:
            return board.reopen_expediente(
                self.corporate_root,
                expediente_id,
                motivo=payload.get("motivo") or "Reapertura Presidencia",
                actor=payload.get("actor") or "Presidencia LNH",
            )

    def execute_corporate_task(self, expediente_id, task_id, payload=None):
        payload = payload if isinstance(payload, dict) else {}
        case = corp.directory(self.corporate_root, expediente_id)
        key = f"corp:{expediente_id}:{task_id}"
        with self._guard:
            if key in self._active:
                raise Conflict("Ya hay una ejecución Platform en curso para este encargo.")
            idem = payload.get("idempotency_key") or payload.get("client_request_id") or f"corp-{task_id}"
            job = {
                "id": uuid4().hex,
                "action": "EXECUTE_TASK",
                "task_id": task_id,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "idempotency_key": idem,
            }
            folder = case / "web_jobs"
            folder.mkdir(exist_ok=True)

            def save():
                target = folder / (job["id"] + ".json")
                temporary = target.with_suffix(".tmp")
                text = json.dumps(job, ensure_ascii=False, indent=2)
                temporary.write_text(text, encoding="utf-8")
                temporary.replace(target)

            save()
            self._active[key] = job

            def work():
                try:
                    result = platform_exec.execute_corporate_task(
                        case, task_id,
                        idempotency_key=idem,
                        actor=payload.get("actor") or "Mission Control",
                    )
                    job["status"] = "completed"
                    job["result_id"] = result.get("result_id")
                    job["idempotent"] = bool(result.get("idempotent"))
                except Exception as error:
                    kind = classify_platform_error(error)
                    job["status"] = "failed"
                    job["error"] = str(error)
                    job["error_kind"] = kind
                finally:
                    job["finished_at"] = datetime.now(timezone.utc).isoformat()
                    with self._guard:
                        save()
                        self._active.pop(key, None)

            threading.Thread(target=work, daemon=True).start()
            return dict(job)

    def operate(self, floor, case_id, action, rationale="", expected_version=None):
        case = self.directory(floor, case_id)
        with self._guard:
            if str(case) in self._active:
                raise Conflict("Ya hay una operación en curso en este expediente.")
            engine.authorize_operation(case, floor, action, rationale, expected_version, jobs=self.jobs(case))
            job = {
                "id": uuid4().hex,
                "action": action,
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "source_version": expected_version,
            }
            folder = case / "web_jobs"
            folder.mkdir(exist_ok=True)

            def save():
                target = folder / (job["id"] + ".json")
                temporary = target.with_suffix(".tmp")
                payload = json.dumps(job, ensure_ascii=False, indent=2)
                last = None
                for attempt in range(8):
                    try:
                        temporary.write_text(payload, encoding="utf-8")
                        temporary.replace(target)
                        return
                    except OSError as error:
                        last = error
                        if getattr(error, "winerror", None) not in (5, 32) and not isinstance(error, PermissionError):
                            raise
                        time.sleep(0.03 * (attempt + 1))
                if last:
                    raise last

            save()
            self._active[str(case)] = job

            def work():
                try:
                    engine.perform_operation(
                        case, action, rationale, job_id=job["id"],
                        expected_version=expected_version, floor_id=floor,
                    )
                    case_status = read_json(case / "case.json")["status"]
                    job["case_status"] = case_status
                    technical_fail = {
                        "PLATFORM_CONNECTION_ERROR", "PLATFORM_EXECUTION_ERROR", "INCOMPLETE",
                    }
                    if case_status == "RECOVERY_PENDING":
                        job["status"] = "recovery"
                        job["error"] = (read_json(case / "TECHNICAL_STATUS.json") or {}).get("message") or case_status
                    elif case_status in technical_fail:
                        job["status"] = "failed"
                        job["error"] = (read_json(case / "TECHNICAL_STATUS.json") or {}).get("message") or case_status
                    else:
                        job["status"] = "completed"
                except Exception as error:
                    engine.log_technical(case, error)
                    job.update(status="failed", error=engine.business_message(error), error_technical=str(error))
                finally:
                    job["finished_at"] = datetime.now(timezone.utc).isoformat()
                    with self._guard:
                        save()
                        self._active.pop(str(case), None)

            threading.Thread(target=work, daemon=True).start()
            return dict(job)
