"""Fase 2A — Directorio IA: board sessions, freeze, isolated deliberation, mechanical consolidation.

Platform = cognitive engine. This module = governance only. No opinion rewriting.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
from uuid import uuid4

from corporate_engine.corporate_agents import (
    DIRECTORS,
    STATUS_BLOQUEADO_CREDITOS,
    binding_for_director,
    director_status,
    missing_director_ids,
)
from corporate_engine.corporate_expediente import (
    ACTOR_PRESIDENCIA,
    ACTOR_TYPE_HUMAN,
    ACTOR_TYPE_SYSTEM,
    audit_event,
    decision_record,
    load_expediente,
    save_expediente,
    task_record,
)
from corporate_engine.corporate_statuses import (
    APROBADO,
    APROBADO_CON_CONDICIONES,
    CORRECCION_SOLICITADA,
    DELIBERACION_COMPLETA,
    DERIVADO,
    EN_ANALISIS,
    EN_DIRECTORIO,
    EN_EJECUCION,
    PENDIENTE_PRESIDENCIA,
    REABIERTO,
    RECHAZADO,
    TASK_PENDIENTE,
    assert_transition,
)
from corporate_engine.corporate_workflow import unmet_prerequisites
from corporate_engine.platform import PlatformGateway, classify_platform_error
from corporate_engine.store import dump_json, load_json, now

SCHEMA = "LNH-DATA-001"
VOTES = frozenset({"A FAVOR", "A FAVOR CON CONDICIONES", "EN CONTRA", "ABSTENCIÓN"})
PRESIDENCY_DECISIONS = frozenset({"APROBAR", "APROBAR CON CONDICIONES", "CORREGIR", "RECHAZAR"})
SESSION_TIPOS = frozenset({"ordinaria", "extraordinaria", "periódica"})

# Board session statuses (administrative)
ST_BORRADOR = "BORRADOR"
ST_CONVOCADA = "CONVOCADA"
ST_PREPARACION = "PREPARACION"
ST_ANTECEDENTES_CERRADOS = "ANTECEDENTES_CERRADOS"
ST_DELIBERACION = "DELIBERACION"
ST_CONSOLIDADA = "CONSOLIDADA"
ST_PENDIENTE_PRESIDENCIA = "PENDIENTE_PRESIDENCIA"
ST_CERRADA = "CERRADA"
ST_BLOQUEADA_CREDITOS = "BLOQUEADA_POR_CREDITOS"


def board_root(corporate_root: Path) -> Path:
    path = Path(corporate_root) / "_directorio" / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _session_dir(corporate_root: Path, board_session_id: str) -> Path:
    return board_root(corporate_root) / board_session_id


def _new_id(prefix: str = "brd-") -> str:
    return f"{prefix}{uuid4().hex}"


def _append_exp_event(master: dict, **kwargs) -> None:
    master.setdefault("eventos", []).append(audit_event(
        expediente_id=master["expediente_id"],
        referencia_version=master.get("version_actual"),
        **kwargs,
    ))


def _save_session(folder: Path, session: dict) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    dump_json(folder / "SESSION.json", session)
    dump_json(folder / "votes.json", session.get("votes") or [])
    dump_json(folder / "director_runs.json", session.get("director_runs") or [])
    dump_json(folder / "consolidation.json", session.get("consolidation") or {})
    if session.get("frozen_pack"):
        dump_json(folder / "frozen_pack.json", session["frozen_pack"])
    return session


def load_board_session(corporate_root: Path, board_session_id: str) -> dict:
    folder = _session_dir(corporate_root, board_session_id)
    path = folder / "SESSION.json"
    if not path.is_file():
        raise FileNotFoundError("Sesión de Directorio no encontrada.")
    return load_json(path)


def list_board_sessions(corporate_root: Path) -> list[dict]:
    rows = []
    for folder in sorted(board_root(corporate_root).iterdir(), reverse=True):
        path = folder / "SESSION.json"
        if not path.is_file():
            continue
        item = load_json(path)
        rows.append({
            "board_session_id": item.get("board_session_id"),
            "tipo": item.get("tipo"),
            "fecha": item.get("fecha"),
            "estado": item.get("estado"),
            "agenda": item.get("agenda") or [],
            "expediente_ids": item.get("expediente_ids") or [],
            "base_version": item.get("base_version"),
            "quorum_ia": item.get("quorum_ia"),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        })
    return rows


def create_board_session(
    corporate_root: Path,
    *,
    tipo: str = "ordinaria",
    fecha: str | None = None,
    agenda: list | None = None,
    expediente_ids: list[str] | None = None,
    actor: str = ACTOR_PRESIDENCIA,
) -> dict:
    tipo_n = (tipo or "ordinaria").strip().casefold()
    if tipo_n in {"periodica", "periódica"}:
        tipo_n = "periódica"
    if tipo_n not in SESSION_TIPOS:
        raise ValueError("tipo de sesión debe ser ordinaria/extraordinaria/periódica.")
    expediente_ids = list(expediente_ids or [])
    for eid in expediente_ids:
        # validates existence
        from corporate_engine import corporate_expediente as corp
        corp.load_expediente(corp.directory(corporate_root, eid))

    session_id = _new_id("brd-")
    folder = _session_dir(corporate_root, session_id)
    participants = [
        {
            "director_id": d["id"],
            "name": d["name"],
            "mandate": d["mandate"],
            "platform_agent_id": None,
            "id_status": "NO CONFIGURADO",
            "connection_status": None,
        }
        for d in DIRECTORS
    ]
    for row in director_status():
        for p in participants:
            if p["director_id"] == row["id"]:
                p["platform_agent_id"] = row.get("platform_agent_id")
                p["id_status"] = "CONFIGURADO" if row.get("available") else "NO CONFIGURADO"
                p["connection_status"] = row.get("connection_status")
                p["platform_agent_id_truncated"] = row.get("platform_agent_id_truncated")

    session = {
        "schema": SCHEMA,
        "board_session_id": session_id,
        "tipo": tipo_n,
        "fecha": fecha or now(),
        "fecha_programada": fecha or now(),
        "fecha_efectiva": None,
        "estado": ST_CONVOCADA,
        "agenda": list(agenda or []),
        "expediente_ids": expediente_ids,
        "documentacion": [],
        "base_version": None,
        "frozen_pack": None,
        "antecedentes_checklist": None,
        "participantes": participants,
        "director_runs": [],
        "votes": [],
        "deliberaciones": [],
        "consolidation": None,
        "quorum_ia": False,
        "resultado": None,
        "human_decision": None,
        "decision_presidencia": None,
        "minutes": None,
        "events": [],
        "created_at": now(),
        "updated_at": now(),
        "created_by": actor,
        "platform_calls": 0,
    }
    session["events"].append({
        "event_id": uuid4().hex,
        "accion": "BOARD_SESSION_OPENED",
        "timestamp": now(),
        "actor": actor,
        "payload": {"tipo": tipo_n, "expediente_ids": expediente_ids},
    })
    _save_session(folder, session)

    for eid in expediente_ids:
        _link_expediente(corporate_root, session, eid, actor=actor)
    return session


def _link_expediente(corporate_root: Path, session: dict, expediente_id: str, *, actor: str) -> None:
    from corporate_engine import corporate_expediente as corp
    case = corp.directory(corporate_root, expediente_id)
    master = load_expediente(case)
    stub = {
        "board_session_id": session["board_session_id"],
        "tipo": session["tipo"],
        "fecha": session["fecha"],
        "estado": session["estado"],
        "agenda": session.get("agenda") or [],
        "base_version": session.get("base_version"),
        "director_runs": [],
        "votes": [],
        "quorum_ia": False,
        "human_decision": None,
        "minutes": None,
        "expediente_ids": list(session.get("expediente_ids") or []),
    }
    existing = {b.get("board_session_id") for b in master.get("board_sessions") or []}
    if session["board_session_id"] not in existing:
        master.setdefault("board_sessions", []).append(stub)
    _append_exp_event(
        master,
        actor=actor,
        actor_type=ACTOR_TYPE_HUMAN,
        accion="BOARD_SESSION_OPENED",
        objeto_afectado=session["board_session_id"],
        estado_anterior=master["estado_actual"],
        estado_nuevo=master["estado_actual"],
        motivo="Expediente vinculado a sesión de Directorio",
        payload={"board_session_id": session["board_session_id"]},
    )
    save_expediente(case, master)


def update_board_session(corporate_root: Path, board_session_id: str, payload: dict) -> dict:
    session = load_board_session(corporate_root, board_session_id)
    if session.get("estado") in {ST_CERRADA}:
        raise ValueError("Sesión cerrada; no se modifica.")
    if "tipo" in payload and payload["tipo"]:
        session["tipo"] = str(payload["tipo"]).strip().casefold()
    if "fecha" in payload and payload["fecha"]:
        session["fecha"] = payload["fecha"]
        session["fecha_programada"] = payload["fecha"]
    if "agenda" in payload and isinstance(payload["agenda"], list):
        session["agenda"] = payload["agenda"]
    if "documentacion" in payload and isinstance(payload["documentacion"], list):
        session["documentacion"] = payload["documentacion"]
    if "expediente_ids" in payload and isinstance(payload["expediente_ids"], list):
        for eid in payload["expediente_ids"]:
            if eid not in session["expediente_ids"]:
                session["expediente_ids"].append(eid)
                _link_expediente(corporate_root, session, eid, actor=payload.get("actor") or ACTOR_PRESIDENCIA)
    session["updated_at"] = now()
    return _save_session(_session_dir(corporate_root, board_session_id), session)


def prepare_antecedents(corporate_root: Path, board_session_id: str, *, actor: str = "LNH Backend") -> dict:
    """Verify docs/reports/overdues and record gaps. Does not call Platform."""
    session = load_board_session(corporate_root, board_session_id)
    from corporate_engine import corporate_expediente as corp
    from corporate_engine import corporate_workflow as workflow

    checklist = []
    for eid in session.get("expediente_ids") or []:
        case = corp.directory(corporate_root, eid)
        master = load_expediente(case)
        overdues = workflow.overdues_view(case)
        reports = list(master.get("resultados") or [])
        docs = list(master.get("documentos") or [])
        tasks = list(master.get("encargos") or [])
        pending_tasks = [t for t in tasks if t.get("status") in {"PENDIENTE", "EN_CURSO", "BLOQUEADO", "VENCIDO"}]
        missing = []
        if not docs:
            missing.append("Sin documentos autorizados")
        if not reports:
            missing.append("Sin informes corporativos recibidos")
        if overdues:
            missing.append(f"Encargos vencidos: {len(overdues)}")
        if pending_tasks:
            missing.append(f"Encargos no entregados: {len(pending_tasks)}")
        checklist.append({
            "expediente_id": eid,
            "estado": master.get("estado_actual"),
            "version_actual": master.get("version_actual"),
            "documentos": len(docs),
            "informes": len(reports),
            "encargos_pendientes": len(pending_tasks),
            "vencidos": overdues,
            "faltantes": missing,
            "completo": not missing,
        })
    session["antecedentes_checklist"] = {
        "prepared_at": now(),
        "items": checklist,
        "completo": all(item["completo"] for item in checklist) if checklist else False,
    }
    session["estado"] = ST_PREPARACION
    session["updated_at"] = now()
    session["events"].append({
        "event_id": uuid4().hex,
        "accion": "ANTECEDENTES_PREPARADOS",
        "timestamp": now(),
        "actor": actor,
        "payload": {"completo": session["antecedentes_checklist"]["completo"]},
    })
    return _save_session(_session_dir(corporate_root, board_session_id), session)


def freeze_antecedents(corporate_root: Path, board_session_id: str, *, actor: str = "LNH Backend") -> dict:
    """Freeze identical documentary base for all five Directors."""
    session = load_board_session(corporate_root, board_session_id)
    if not session.get("antecedentes_checklist"):
        session = prepare_antecedents(corporate_root, board_session_id, actor=actor)
    if session.get("frozen_pack") and session.get("base_version"):
        return session  # already frozen — immutable for primera ronda

    from corporate_engine import corporate_expediente as corp

    pack_items = []
    versions = []
    for eid in session.get("expediente_ids") or []:
        case = corp.directory(corporate_root, eid)
        master = load_expediente(case)
        versions.append(master.get("version_actual") or "v001")
        pack_items.append({
            "expediente_id": eid,
            "tipo": master.get("tipo"),
            "ambito": master.get("ambito"),
            "prioridad": master.get("prioridad"),
            "asunto": master.get("asunto"),
            "instruccion_original": master.get("instruccion_original"),
            "fecha_objetivo": master.get("fecha_objetivo"),
            "version": master.get("version_actual"),
            "documentos_autorizados": [
                {
                    "document_id": d.get("document_id"),
                    "nombre": d.get("nombre") or d.get("name"),
                    "version": d.get("version"),
                    "hash_sha256": d.get("hash_sha256"),
                }
                for d in (master.get("documentos") or [])
            ],
            "informes_corporativos": [
                {
                    "result_id": r.get("result_id"),
                    "agent_id": r.get("agent_id"),
                    "task_id": r.get("task_id"),
                    "fecha": r.get("fecha"),
                    "version": r.get("version"),
                    "contenido": r.get("contenido"),
                    "fuentes_evidencias": r.get("fuentes_evidencias") or [],
                    "limitaciones_informacion_pendiente": r.get("limitaciones_informacion_pendiente") or [],
                    "estado": r.get("estado"),
                    "platform_session_id": r.get("platform_session_id"),
                }
                for r in (master.get("resultados") or [])
            ],
            "fuentes": master.get("fuentes") or [],
            "evidencias": master.get("evidencias") or [],
            "decisiones": master.get("decisiones") or [],
            "routing": master.get("routing"),
        })
        previous = master["estado_actual"]
        if previous != EN_DIRECTORIO:
            if previous in {EN_ANALISIS, DERIVADO}:
                assert_transition(previous, EN_DIRECTORIO)
                master["estado_actual"] = EN_DIRECTORIO
            else:
                try:
                    assert_transition(previous, EN_DIRECTORIO)
                    master["estado_actual"] = EN_DIRECTORIO
                except ValueError:
                    pass
        _append_exp_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="BOARD_ANTECEDENTS_FROZEN",
            objeto_afectado=board_session_id,
            estado_anterior=previous,
            estado_nuevo=master["estado_actual"],
            motivo="Base documental congelada para deliberación independiente",
            payload={"board_session_id": board_session_id, "version": master.get("version_actual")},
        )
        save_expediente(case, master)

    base_version = f"freeze-{uuid4().hex[:12]}"
    frozen = {
        "base_version": base_version,
        "frozen_at": now(),
        "expediente_versions": versions,
        "items": pack_items,
        "identical_for_all_directors": True,
        "note": "Los cinco Directores reciben exactamente esta base. No se altera durante primera ronda.",
    }
    session["frozen_pack"] = frozen
    session["base_version"] = base_version
    session["estado"] = ST_ANTECEDENTES_CERRADOS
    session["updated_at"] = now()
    session["events"].append({
        "event_id": uuid4().hex,
        "accion": "ANTECEDENTES_CONGELADOS",
        "timestamp": now(),
        "actor": actor,
        "payload": {"base_version": base_version},
    })
    return _save_session(_session_dir(corporate_root, board_session_id), session)


def _director_prompt(session: dict, director: dict) -> str:
    """Authorized context only — does not include other directors' opinions."""
    payload = {
        "board_session_id": session["board_session_id"],
        "base_version": session.get("base_version"),
        "director": {
            "id": director["id"],
            "name": director["name"],
            "mandate": director["mandate"],
        },
        "instruccion_operativa": (
            "Delibere de forma independiente según su mandato ya configurado en OpenAI Platform. "
            "No tiene acceso a opiniones de otros Directores. "
            "Devuelva un JSON con: director, mandato, conclusion_ejecutiva, analisis, riesgos, "
            "condiciones, recomendacion, voto_consultivo "
            "(A FAVOR | A FAVOR CON CONDICIONES | EN CONTRA | ABSTENCIÓN), "
            "fundamento, informacion_pendiente."
        ),
        "paquete_antecedentes_congelado": session.get("frozen_pack"),
    }
    return (
        f"Contexto Directorio LNH — deliberación independiente {director['id']}\n"
        f"base_version={session.get('base_version')}\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _parse_director_output(text: str, director_id: str) -> dict:
    data = None
    if text:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    data = parsed
            except json.JSONDecodeError:
                data = None
    vote = None
    if data:
        vote = data.get("voto_consultivo") or data.get("voto") or data.get("vote")
        if vote:
            vote = str(vote).strip().upper()
            # normalize accents-ish
            aliases = {
                "A FAVOR": "A FAVOR",
                "AFAVOR": "A FAVOR",
                "A FAVOR CON CONDICIONES": "A FAVOR CON CONDICIONES",
                "EN CONTRA": "EN CONTRA",
                "ABSTENCION": "ABSTENCIÓN",
                "ABSTENCIÓN": "ABSTENCIÓN",
            }
            vote = aliases.get(vote, vote)
            if vote not in VOTES:
                vote = None
    return {
        "director_id": director_id,
        "raw_content": text or "",
        "structured": data,
        "voto_consultivo": vote,
        "conclusion_ejecutiva": (data or {}).get("conclusion_ejecutiva"),
        "analisis": (data or {}).get("analisis"),
        "riesgos": (data or {}).get("riesgos"),
        "condiciones": (data or {}).get("condiciones"),
        "recomendacion": (data or {}).get("recomendacion"),
        "fundamento": (data or {}).get("fundamento"),
        "informacion_pendiente": (data or {}).get("informacion_pendiente"),
        "mandato": (data or {}).get("mandato"),
    }


def run_independent_deliberation(
    corporate_root: Path,
    board_session_id: str,
    *,
    gateway: PlatformGateway | None = None,
    actor: str = "Mission Control",
    force: bool = False,
    bindings: dict | None = None,
) -> dict:
    """Primera ronda: 5 Managed Sessions aisladas. No contamination."""
    session = load_board_session(corporate_root, board_session_id)
    if not session.get("frozen_pack"):
        raise ValueError("Debe congelar antecedentes antes de deliberar.")
    if session.get("director_runs") and not force:
        raise ValueError("Primera ronda ya registrada. No sobrescribir; use nueva sesión/versión.")

    missing = [] if bindings else missing_director_ids()
    if missing:
        session["resultado"] = {
            "blocked": True,
            "reason": "DIRECTOR_AGENT_ID_PENDING",
            "missing_director_ids": missing,
            "note": "IDs de Directores no disponibles en configuración local. No se inventan.",
            "operational_status": STATUS_BLOQUEADO_CREDITOS if False else "ID PENDIENTE EN CONFIGURACIÓN",
        }
        session["updated_at"] = now()
        session["events"].append({
            "event_id": uuid4().hex,
            "accion": "DELIBERACION_BLOQUEADA",
            "timestamp": now(),
            "actor": actor,
            "payload": session["resultado"],
        })
        return _save_session(_session_dir(corporate_root, board_session_id), session)

    gw = gateway or PlatformGateway()
    folder = _session_dir(corporate_root, board_session_id)
    session["estado"] = ST_DELIBERACION
    session["fecha_efectiva"] = now()
    runs = []
    votes = []
    opinions = []
    credit_block = False

    for director in DIRECTORS:
        if bindings and director["id"] in bindings:
            binding = bindings[director["id"]]
        else:
            binding = binding_for_director(director["id"])
        run_dir = folder / "platform_runs" / director["id"]
        run_dir.mkdir(parents=True, exist_ok=True)
        prompt = _director_prompt(session, director)
        for other in DIRECTORS:
            if other["id"] != director["id"]:
                assert f"opinion:{other['id']}" not in prompt
        run_row = {
            "director_id": director["id"],
            "name": director["name"],
            "mandate": director["mandate"],
            "platform_agent_id": binding.platform_agent_id,
            "started_at": now(),
            "completed_at": None,
            "status": "starting",
            "platform_session_id": None,
            "turn_id": None,
            "error": None,
            "error_kind": None,
            "client_request_id": f"{board_session_id}:{director['id']}:r1",
            "isolation": {
                "receives_other_directors_opinions": False,
                "shared_base_version": session.get("base_version"),
            },
            "prompt_fingerprint": {
                "base_version": session.get("base_version"),
                "includes_other_opinions": False,
                "director_id": director["id"],
            },
        }
        try:
            sid = gw.reuse_or_create_session("", binding.platform_agent_id, binding.environment, run_dir)
            run_row["platform_session_id"] = sid
            run_row["status"] = "running"
            result = gw.run_mission(
                session=sid,
                prompt=prompt,
                case_dir=run_dir,
                actor=director["id"],
                platform_agent_id=binding.platform_agent_id,
                client_request_id=run_row["client_request_id"],
            )
            session["platform_calls"] = int(session.get("platform_calls") or 0) + 1
            text = result.get("assistant_output_raw") or result.get("assistant_output_clean") or ""
            parsed = _parse_director_output(text, director["id"])
            run_row["status"] = "completed"
            run_row["completed_at"] = now()
            run_row["turn_id"] = result.get("turn_id")
            run_row["result"] = parsed
            opinion = {
                "director": director["id"],
                "mandato": director["mandate"],
                "conclusion_ejecutiva": parsed.get("conclusion_ejecutiva"),
                "analisis": parsed.get("analisis"),
                "riesgos": parsed.get("riesgos"),
                "condiciones": parsed.get("condiciones"),
                "recomendacion": parsed.get("recomendacion"),
                "voto_consultivo": parsed.get("voto_consultivo"),
                "fundamento": parsed.get("fundamento"),
                "informacion_pendiente": parsed.get("informacion_pendiente"),
                "contenido_completo": parsed.get("raw_content"),
                "platform_session_id": sid,
                "turn_id": result.get("turn_id"),
                "base_version": session.get("base_version"),
            }
            opinions.append(opinion)
            if parsed.get("voto_consultivo"):
                vote_row = {
                    "director_id": director["id"],
                    "voto": parsed["voto_consultivo"],
                    "fundamento": parsed.get("fundamento"),
                    "condiciones": parsed.get("condiciones"),
                    "pendientes": parsed.get("informacion_pendiente"),
                    "timestamp": now(),
                    "base_version": session.get("base_version"),
                    "immutable": True,
                }
                votes.append(vote_row)
                session["events"].append({
                    "event_id": uuid4().hex,
                    "accion": "DIRECTOR_VOTE_RECORDED",
                    "timestamp": now(),
                    "actor": director["id"],
                    "payload": {"voto": vote_row["voto"]},
                })
        except Exception as error:
            kind = classify_platform_error(error)
            run_row["status"] = "failed"
            run_row["error"] = str(error)
            run_row["error_kind"] = kind
            run_row["completed_at"] = now()
            if kind == "CREDIT_BALANCE_EXHAUSTED":
                credit_block = True
            # Do not invent vote/opinion
        runs.append(run_row)
        # Persist after each director to keep recoverability without cross-contamination writes
        session["director_runs"] = runs
        session["deliberaciones"] = opinions
        session["votes"] = votes
        _save_session(folder, session)

        if credit_block:
            # Stop further Platform consumption after credit exhaustion
            for remaining in DIRECTORS:
                if remaining["id"] in {r["director_id"] for r in runs}:
                    continue
                runs.append({
                    "director_id": remaining["id"],
                    "name": remaining["name"],
                    "mandate": remaining["mandate"],
                    "status": "skipped",
                    "error_kind": "CREDIT_BALANCE_EXHAUSTED",
                    "error": "Detenido: créditos Platform agotados. No se simula deliberación.",
                    "isolation": {"receives_other_directors_opinions": False},
                })
            session["director_runs"] = runs
            session["estado"] = ST_BLOQUEADA_CREDITOS
            session["updated_at"] = now()
            session["events"].append({
                "event_id": uuid4().hex,
                "accion": "DELIBERACION_BLOQUEADA_CREDITOS",
                "timestamp": now(),
                "actor": actor,
                "payload": {"completed_runs": len([r for r in runs if r.get("status") == "completed"])},
            })
            return _save_session(folder, session)

    session["director_runs"] = runs
    session["deliberaciones"] = opinions
    session["votes"] = votes
    session = consolidate_board_session(corporate_root, board_session_id, session_override=session)
    return session


def consolidate_board_session(
    corporate_root: Path,
    board_session_id: str,
    *,
    session_override: dict | None = None,
    actor: str = "LNH Backend",
) -> dict:
    """Mechanical consolidation only — no cognitive rewrite."""
    session = session_override or load_board_session(corporate_root, board_session_id)
    opinions = list(session.get("deliberaciones") or [])
    votes = list(session.get("votes") or [])
    counts = {v: 0 for v in VOTES}
    for vote in votes:
        key = vote.get("voto")
        if key in counts:
            counts[key] += 1
    conditions = []
    pending_info = []
    for op in opinions:
        if op.get("condiciones"):
            conditions.append({"director": op.get("director"), "condiciones": op.get("condiciones")})
        if op.get("informacion_pendiente"):
            pending_info.append({"director": op.get("director"), "informacion_pendiente": op.get("informacion_pendiente")})

    complete = len(opinions) == 5 and len(votes) == 5
    consolidation = {
        "consolidated_at": now(),
        "method": "mechanical_only",
        "opinions_count": len(opinions),
        "votes_count": len(votes),
        "vote_counts": counts,
        "conditions": conditions,
        "informacion_pendiente": pending_info,
        "opinions_intact": opinions,
        "votes_intact": votes,
        "note": "Backend no interpreta ni genera opinión del Directorio.",
        "deliberacion_completa": complete,
    }
    session["consolidation"] = consolidation
    session["quorum_ia"] = complete
    session["resultado"] = {
        "vote_counts": counts,
        "quorum_ia": complete,
        "consultivo": True,
    }
    if complete:
        session["estado"] = ST_CONSOLIDADA
        # Move expedientes to DELIBERACION_COMPLETA then PENDIENTE_PRESIDENCIA
        from corporate_engine import corporate_expediente as corp
        for eid in session.get("expediente_ids") or []:
            case = corp.directory(corporate_root, eid)
            master = load_expediente(case)
            prev = master["estado_actual"]
            if prev == EN_DIRECTORIO:
                assert_transition(prev, DELIBERACION_COMPLETA)
                master["estado_actual"] = DELIBERACION_COMPLETA
                prev2 = master["estado_actual"]
                assert_transition(prev2, PENDIENTE_PRESIDENCIA)
                master["estado_actual"] = PENDIENTE_PRESIDENCIA
            elif prev == DELIBERACION_COMPLETA:
                assert_transition(prev, PENDIENTE_PRESIDENCIA)
                master["estado_actual"] = PENDIENTE_PRESIDENCIA
            _append_exp_event(
                master,
                actor=actor,
                actor_type=ACTOR_TYPE_SYSTEM,
                accion="HUMAN_GATE_REQUESTED",
                objeto_afectado=board_session_id,
                estado_anterior=prev,
                estado_nuevo=master["estado_actual"],
                motivo="Consolidación mecánica lista para Presidencia",
                payload={"board_session_id": board_session_id, "vote_counts": counts},
            )
            # sync board stub
            for stub in master.get("board_sessions") or []:
                if stub.get("board_session_id") == board_session_id:
                    stub["votes"] = votes
                    stub["director_runs"] = session.get("director_runs")
                    stub["quorum_ia"] = True
                    stub["base_version"] = session.get("base_version")
            save_expediente(case, master)
        session["estado"] = ST_PENDIENTE_PRESIDENCIA
    session["updated_at"] = now()
    session["events"].append({
        "event_id": uuid4().hex,
        "accion": "CONSOLIDACION_MECANICA",
        "timestamp": now(),
        "actor": actor,
        "payload": {"vote_counts": counts, "completa": complete},
    })
    return _save_session(_session_dir(corporate_root, board_session_id), session)


def presidency_decision(
    corporate_root: Path,
    board_session_id: str,
    *,
    decision: str,
    rationale: str = "",
    conditions: str | list | None = None,
    actor: str = ACTOR_PRESIDENCIA,
    expediente_id: str | None = None,
) -> dict:
    decision_u = str(decision or "").strip().upper()
    if decision_u not in PRESIDENCY_DECISIONS:
        raise ValueError("Decisión debe ser APROBAR | APROBAR CON CONDICIONES | CORREGIR | RECHAZAR.")
    session = load_board_session(corporate_root, board_session_id)
    if session.get("estado") not in {ST_PENDIENTE_PRESIDENCIA, ST_CONSOLIDADA}:
        # Allow if consolidation exists even when credit-partial? Only with valid material.
        if not session.get("consolidation", {}).get("deliberacion_completa"):
            raise ValueError("No hay deliberación completa válida para Human Gate.")

    targets = [expediente_id] if expediente_id else list(session.get("expediente_ids") or [])
    if not targets:
        raise ValueError("Sesión sin expedientes asociados.")

    from corporate_engine import corporate_expediente as corp

    state_map = {
        "APROBAR": APROBADO,
        "APROBAR CON CONDICIONES": APROBADO_CON_CONDICIONES,
        "CORREGIR": CORRECCION_SOLICITADA,
        "RECHAZAR": RECHAZADO,
    }
    new_state = state_map[decision_u]
    decisions = []
    for eid in targets:
        case = corp.directory(corporate_root, eid)
        master = load_expediente(case)
        prev = master["estado_actual"]
        if prev != PENDIENTE_PRESIDENCIA:
            if prev == DELIBERACION_COMPLETA:
                assert_transition(prev, PENDIENTE_PRESIDENCIA)
                master["estado_actual"] = PENDIENTE_PRESIDENCIA
                prev = PENDIENTE_PRESIDENCIA
            else:
                raise ValueError(f"Expediente {eid} no está en PENDIENTE_PRESIDENCIA ({prev}).")
        assert_transition(prev, new_state)
        master["estado_actual"] = new_state
        based_on = session.get("base_version") or master.get("version_actual")
        rec = decision_record(
            expediente_id=eid,
            authority=actor,
            decision=decision_u,
            conditions=conditions,
            rationale=rationale,
            based_on_version=based_on,
            resulting_actions=[],
            legal_formality="consultivo_directorio_ia",
        )
        master.setdefault("decisiones", []).append(rec)
        decisions.append(rec)
        accion = "PRESIDENCY_DECISION_RECORDED"
        if decision_u == "CORREGIR":
            accion = "CORRECTION_REQUESTED"
            # new version marker without destroying history
            current_v = master.get("version_actual") or "v001"
            try:
                num = int(str(current_v).lstrip("v")) + 1
            except ValueError:
                num = 2
            new_v = f"v{num:03d}"
            master["version_actual"] = new_v
            master.setdefault("historial_versiones", []).append({
                "version": new_v,
                "created_at": now(),
                "motivo": rationale or "Corrección solicitada por Presidencia",
                "based_on": based_on,
                "board_session_id": board_session_id,
            })
            # correction task to LNH-03 by default if no area specified
            task = task_record(
                expediente_id=eid,
                requested_by=actor,
                assigned_to="LNH-03",
                deliverable_type="correccion",
                objective=f"Corregir conforme decisión Presidencia: {rationale or 'sin detalle'}",
                due_at=master.get("fecha_objetivo"),
                priority=master.get("prioridad"),
                role="correccion_presidencia",
            )
            master.setdefault("encargos", []).append(task)
            rec["resulting_actions"] = [{"task_id": task["task_id"], "assigned_to": "LNH-03"}]
            _append_exp_event(
                master,
                actor=actor,
                actor_type=ACTOR_TYPE_HUMAN,
                accion="TASK_CREATED",
                objeto_afectado=task["task_id"],
                estado_anterior=new_state,
                estado_nuevo=new_state,
                motivo="Encargo de corrección post Human Gate",
            )
        elif decision_u in {"APROBAR", "APROBAR CON CONDICIONES"}:
            # Derive follow-up execution tasks (governance), not business ops
            follow = task_record(
                expediente_id=eid,
                requested_by=actor,
                assigned_to="LNH-06",
                deliverable_type="seguimiento_ejecucion",
                objective=f"Seguimiento post-aprobación Presidencia ({decision_u})",
                due_at=master.get("fecha_objetivo"),
                priority=master.get("prioridad"),
                role="seguimiento",
            )
            master.setdefault("encargos", []).append(follow)
            rec["resulting_actions"] = [{"task_id": follow["task_id"], "assigned_to": "LNH-06"}]
            try:
                assert_transition(new_state, EN_EJECUCION)
                master["estado_actual"] = EN_EJECUCION
            except ValueError:
                pass
            _append_exp_event(
                master,
                actor=actor,
                actor_type=ACTOR_TYPE_SYSTEM,
                accion="EXECUTION_DERIVED",
                objeto_afectado=follow["task_id"],
                estado_anterior=new_state,
                estado_nuevo=master["estado_actual"],
                motivo="Derivación a seguimiento/ejecución gobernada",
            )

        _append_exp_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_HUMAN,
            accion=accion,
            objeto_afectado=rec["decision_id"],
            estado_anterior=prev,
            estado_nuevo=master["estado_actual"],
            motivo=rationale or decision_u,
            payload={
                "decision": decision_u,
                "conditions": conditions,
                "based_on_version": based_on,
                "board_session_id": board_session_id,
            },
        )
        for stub in master.get("board_sessions") or []:
            if stub.get("board_session_id") == board_session_id:
                stub["human_decision"] = rec
        save_expediente(case, master)

    session["human_decision"] = decisions[0] if len(decisions) == 1 else decisions
    session["decision_presidencia"] = {
        "decision": decision_u,
        "actor": actor,
        "rationale": rationale,
        "conditions": conditions,
        "decided_at": now(),
        "based_on_version": session.get("base_version"),
        "decision_ids": [d["decision_id"] for d in decisions],
    }
    session["minutes"] = {
        "generated_at": now(),
        "agreements": [f"Decisión Presidencia: {decision_u}"],
        "tasks_derived": [a for d in decisions for a in (d.get("resulting_actions") or [])],
        "note": "Acta administrativa. No sustituye formalidad estatutaria.",
    }
    session["estado"] = ST_CERRADA
    session["updated_at"] = now()
    session["events"].append({
        "event_id": uuid4().hex,
        "accion": "BOARD_SESSION_CLOSED",
        "timestamp": now(),
        "actor": actor,
        "payload": {"decision": decision_u},
    })
    return _save_session(_session_dir(corporate_root, board_session_id), session)


def reopen_expediente(
    corporate_root: Path,
    expediente_id: str,
    *,
    motivo: str,
    actor: str = ACTOR_PRESIDENCIA,
) -> dict:
    from corporate_engine import corporate_expediente as corp
    case = corp.directory(corporate_root, expediente_id)
    master = load_expediente(case)
    prev = master["estado_actual"]
    assert_transition(prev, REABIERTO)
    master["estado_actual"] = REABIERTO
    _append_exp_event(
        master,
        actor=actor,
        actor_type=ACTOR_TYPE_HUMAN,
        accion="CASE_REOPENED",
        objeto_afectado=expediente_id,
        estado_anterior=prev,
        estado_nuevo=REABIERTO,
        motivo=motivo,
        payload={"version_partida": master.get("version_actual")},
    )
    save_expediente(case, master)
    return master


def board_session_view(corporate_root: Path, board_session_id: str) -> dict:
    session = load_board_session(corporate_root, board_session_id)
    return {
        **session,
        "capabilities": {
            "deliberate": bool(session.get("frozen_pack")),
            "human_gate": session.get("estado") == ST_PENDIENTE_PRESIDENCIA,
            "directors_ids_missing": missing_director_ids(),
        },
    }
