"""Local HTTP transport for the Corporate workspace adapter."""
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote, quote
from corporate.web_api import CorporateWebAPI, Conflict

ROOT = Path(__file__).resolve().parent
API = CorporateWebAPI(
    ROOT / "outputs" / "mgc_05",
    ROOT / "outputs" / "mgc_03",
    ROOT / "outputs" / "lnh_corporate",
)
MAX_BODY = 40 * 1024 * 1024

class Handler(BaseHTTPRequestHandler):
    def end_headers(self):
        origin = self.headers.get("Origin", "")
        if origin in {"http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:5174"}:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _route(self):
        parsed = urlparse(self.path)
        return [unquote(p) for p in parsed.path.split("/") if p], parse_qs(parsed.query)

    def _error(self, error):
        status = HTTPStatus.CONFLICT if isinstance(error, Conflict) else HTTPStatus.NOT_FOUND if isinstance(error, FileNotFoundError) else HTTPStatus.BAD_REQUEST if isinstance(error, (ValueError, KeyError, TypeError)) else HTTPStatus.INTERNAL_SERVER_ERROR
        self._json({"error": str(error)}, status)

    def do_GET(self):
        parts, query = self._route()
        try:
            if parts == ["api", "health"]:
                self._json(API.health())
            elif parts == ["api", "corporate", "hierarchy"]:
                self._json(API.hierarchy())
            elif parts == ["api", "corporate", "areas"]:
                self._json(API.corporate_areas())
            elif parts == ["api", "corporate", "agents"]:
                self._json(API.corporate_agents())
            elif parts == ["api", "corporate", "board-sessions"]:
                self._json(API.board_sessions())
            elif len(parts) == 4 and parts[:3] == ["api", "corporate", "board-sessions"]:
                self._json(API.board_session(parts[3]))
            elif parts == ["api", "corporate", "calendar", "events"]:
                self._json(API.calendar_events(query))
            elif len(parts) == 5 and parts[:4] == ["api", "corporate", "calendar", "events"]:
                self._json(API.calendar_event(parts[4]))
            elif parts == ["api", "corporate", "communications"]:
                self._json(API.communications(query))
            elif len(parts) == 4 and parts[:3] == ["api", "corporate", "communications"]:
                self._json(API.communication(parts[3]))
            elif parts == ["api", "corporate", "notifications"]:
                self._json(API.notifications(query))
            elif parts == ["api", "corporate", "providers"]:
                self._json(API.providers_status())
            elif parts == ["api", "corporate", "providers", "google"]:
                self._json(API.google_oauth_status())
            elif parts == ["api", "corporate", "providers", "whatsapp"]:
                self._json(API.whatsapp_status())
            elif parts == ["api", "corporate", "executive", "board"]:
                self._json(API.executive_board(query))
            elif parts == ["api", "corporate", "executive", "weather"]:
                self._json(API.executive_weather(query))
            elif parts == ["api", "corporate", "executive", "economy"]:
                self._json(API.executive_economy(query))
            elif parts == ["api", "corporate", "executive", "markets"]:
                self._json(API.executive_markets(query))
            elif parts == ["api", "corporate", "executive", "news"]:
                self._json(API.executive_news(query))
            elif parts == ["api", "corporate", "executive", "alerts"]:
                self._json(API.executive_alerts(query))
            elif parts == ["api", "corporate", "overdues"]:
                self._json(API.corporate_overdues())
            elif parts == ["api", "corporate", "expedientes"]:
                self._json(API.corporate_expedientes())
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "events":
                self._json(API.corporate_expediente_events(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "calendar-events":
                self._json(API.expediente_calendar_events(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "communications":
                self._json(API.expediente_communications(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "notifications":
                self._json(API.expediente_notifications(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "routing":
                self._json(API.corporate_routing(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "tasks":
                self._json(API.corporate_tasks(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "dependencies":
                self._json(API.corporate_dependencies(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "overdues":
                self._json(API.corporate_overdues(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "results":
                self._json(API.corporate_results(parts[3]))
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "sessions":
                self._json(API.corporate_sessions(parts[3]))
            elif len(parts) == 4 and parts[:3] == ["api", "corporate", "expedientes"]:
                self._json(API.corporate_expediente(parts[3]))
            elif parts == ["api", "cases"]:
                self._json(API.cases(query.get("floor", [None])[0]))
            elif len(parts) == 4 and parts[:2] == ["api", "cases"]:
                self._json(API.case(parts[2], parts[3], query.get("version", [None])[0]))
            elif len(parts) == 5 and parts[:2] == ["api", "cases"] and parts[4] == "artifact":
                path = API.artifact(parts[2], parts[3], query.get("path", [""])[0])
                data = path.read_bytes()
                self.send_response(200)
                suffix = path.suffix.lower()
                types = {
                    ".pdf": "application/pdf",
                    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    ".md": "text/markdown; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                }
                content_type = types.get(suffix, "application/octet-stream")
                disposition = "inline" if suffix == ".pdf" else "attachment"
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Disposition", f"{disposition}; filename*=UTF-8''" + quote(path.name))
                self.send_header("Content-Length", str(len(data)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)
            else:
                raise FileNotFoundError("Ruta no encontrada.")
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._error(error)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > MAX_BODY:
                self._json({"error": "Solicitud vacía o superior a 40 MB."}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
                return
            if length <= 0:
                payload = {}
            else:
                payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Se requiere un objeto JSON.")
            parts, _ = self._route()
            if parts == ["api", "corporate", "expedientes"]:
                self._json(API.create_corporate_expediente(payload), HTTPStatus.CREATED)
            elif parts == ["api", "corporate", "calendar", "events"]:
                self._json(API.create_calendar_event(payload), HTTPStatus.CREATED)
            elif len(parts) == 6 and parts[:4] == ["api", "corporate", "calendar", "events"] and parts[5] == "status":
                self._json(API.update_calendar_event_status(parts[4], payload), HTTPStatus.OK)
            elif len(parts) == 6 and parts[:4] == ["api", "corporate", "calendar", "events"] and parts[5] == "sync":
                self._json(API.sync_calendar_event(parts[4], payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "calendar", "sync", "push"]:
                self._json(API.sync_calendar_push(payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "calendar", "sync", "pull"]:
                self._json(API.sync_calendar_pull(payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "communications"]:
                self._json(API.create_communication(payload), HTTPStatus.CREATED)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "communications"] and parts[4] == "submit-approval":
                self._json(API.submit_communication_approval(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "communications"] and parts[4] == "human-gate":
                self._json(API.communication_human_gate(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "communications"] and parts[4] == "content":
                self._json(API.update_communication_content(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "communications"] and parts[4] == "send":
                self._json(API.send_communication(parts[3], payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "communications", "sync", "pull"]:
                self._json(API.sync_email_pull(payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "communications"] and parts[4] == "link-expediente":
                self._json(API.link_communication_expediente(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "communications"] and parts[4] == "read":
                self._json(API.mark_communication_read(parts[3], payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "providers", "google", "config"]:
                self._json(API.save_google_provider_config(payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "providers", "whatsapp", "config"]:
                self._json(API.save_whatsapp_provider_config(payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "executive", "refresh"]:
                self._json(API.refresh_executive_board(payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "executive", "alerts", "scan"]:
                self._json(API.scan_executive_alerts(payload), HTTPStatus.OK)
            elif len(parts) == 6 and parts[:4] == ["api", "corporate", "executive", "alerts"] and parts[5] == "state":
                self._json(API.set_executive_alert_state(parts[4], payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "notifications"]:
                self._json(API.create_notification(payload), HTTPStatus.CREATED)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "notifications"] and parts[4] == "read":
                self._json(API.mark_notification_read(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "notifications"] and parts[4] == "archive":
                self._json(API.archive_notification(parts[3], payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "f2b-sync"]:
                self._json(API.run_f2b_sync(payload), HTTPStatus.OK)
            elif parts == ["api", "corporate", "board-sessions"]:
                self._json(API.create_board_session(payload), HTTPStatus.CREATED)
            elif len(parts) == 4 and parts[:3] == ["api", "corporate", "board-sessions"]:
                self._json(API.update_board_session(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "board-sessions"] and parts[4] == "prepare":
                self._json(API.prepare_board_session(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "board-sessions"] and parts[4] == "freeze":
                self._json(API.freeze_board_session(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "board-sessions"] and parts[4] == "deliberate":
                self._json(API.deliberate_board_session(parts[3], payload), HTTPStatus.ACCEPTED)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "board-sessions"] and parts[4] == "consolidate":
                self._json(API.consolidate_board_session(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "board-sessions"] and parts[4] == "human-gate":
                self._json(API.board_presidency_decision(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "reopen":
                self._json(API.reopen_corporate_expediente(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "routing":
                self._json(API.apply_corporate_routing(parts[3], payload), HTTPStatus.OK)
            elif len(parts) == 5 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "dependencies":
                self._json(API.create_corporate_dependency(parts[3], payload), HTTPStatus.CREATED)
            elif len(parts) == 7 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "tasks" and parts[6] == "status":
                self._json(API.update_corporate_task(parts[3], parts[5], payload), HTTPStatus.OK)
            elif len(parts) == 7 and parts[:3] == ["api", "corporate", "expedientes"] and parts[4] == "tasks" and parts[6] == "execute":
                self._json(API.execute_corporate_task(parts[3], parts[5], payload), HTTPStatus.ACCEPTED)
            elif parts == ["api", "cases"]:
                self._json(API.create(payload.get("mission"), payload.get("floor_id", "MGC-03"), payload.get("documents", [])), HTTPStatus.CREATED)
            elif len(parts) == 5 and parts[:2] == ["api", "cases"] and parts[4] in ("execute", "human-gate"):
                action = "EJECUTAR" if parts[4] == "execute" else payload.get("decision")
                if parts[4] == "human-gate" and action not in ("APROBAR", "CORREGIR", "RECHAZAR"):
                    raise ValueError("Decisión humana no válida.")
                self._json(API.operate(parts[2], parts[3], action, payload.get("rationale", ""), payload.get("expected_version")), HTTPStatus.ACCEPTED)
            else:
                raise FileNotFoundError("Ruta no encontrada.")
        except (OSError, ValueError, KeyError, TypeError) as error:
            self._error(error)

    def log_message(self, _format, *_args):
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--data-root", type=Path, default=ROOT / "outputs")
    args = parser.parse_args()
    API = CorporateWebAPI(
        args.data_root / "mgc_05",
        args.data_root / "mgc_03",
        args.data_root / "lnh_corporate",
    )
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
