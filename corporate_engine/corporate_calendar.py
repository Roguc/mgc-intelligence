"""Fase 2B-1 — Corporate calendar events (persistent, expediente-linked)."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from corporate_engine.corporate_expediente import (
    ACTOR_TYPE_SYSTEM,
    audit_event,
    load_expediente,
    save_expediente,
    directory as expediente_directory,
)
from corporate_engine.store import dump_json, load_json, now

SCHEMA = "LNH-DATA-001"
EVENT_TYPES = frozenset({
    "REUNION", "DIRECTORIO", "VENCIMIENTO", "SEGUIMIENTO",
    "HUMAN_GATE", "TAREA", "HITO", "OTRO",
})
EVENT_STATUSES = frozenset({
    "BORRADOR", "PROGRAMADO", "CONFIRMADO", "COMPLETADO", "CANCELADO",
})
STATUS_TRANSITIONS = {
    "BORRADOR": frozenset({"PROGRAMADO", "CANCELADO"}),
    "PROGRAMADO": frozenset({"CONFIRMADO", "COMPLETADO", "CANCELADO"}),
    "CONFIRMADO": frozenset({"COMPLETADO", "CANCELADO"}),
    "COMPLETADO": frozenset(),
    "CANCELADO": frozenset(),
}


def calendar_root(corporate_root: Path) -> Path:
    path = Path(corporate_root) / "_calendario" / "events"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _event_dir(corporate_root: Path, event_id: str) -> Path:
    return calendar_root(corporate_root) / event_id


def _new_id() -> str:
    return f"evt-{uuid4().hex}"


def _save_event(folder: Path, event: dict) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    dump_json(folder / "EVENT.json", event)
    return event


def load_event(corporate_root: Path, event_id: str) -> dict:
    path = _event_dir(corporate_root, event_id) / "EVENT.json"
    if not path.is_file():
        raise FileNotFoundError("Evento de calendario no encontrado.")
    return load_json(path)


def list_events(
    corporate_root: Path,
    *,
    event_type: str | None = None,
    status: str | None = None,
    expediente_id: str | None = None,
    company_scope: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    rows = []
    root = calendar_root(corporate_root)
    for folder in sorted(root.iterdir(), reverse=True):
        path = folder / "EVENT.json"
        if not path.is_file():
            continue
        item = load_json(path)
        if event_type and item.get("event_type") != event_type:
            continue
        if status and item.get("status") != status:
            continue
        if expediente_id and item.get("expediente_id") != expediente_id:
            continue
        if company_scope and item.get("company_scope") != company_scope:
            continue
        start = str(item.get("start_at") or "")
        if date_from and start and start[:10] < str(date_from)[:10]:
            continue
        if date_to and start and start[:10] > str(date_to)[:10]:
            continue
        rows.append(_summary(item))
    rows.sort(key=lambda r: r.get("start_at") or "", reverse=False)
    return rows


def _summary(item: dict) -> dict:
    return {
        "event_id": item.get("event_id"),
        "title": item.get("title"),
        "event_type": item.get("event_type"),
        "start_at": item.get("start_at"),
        "end_at": item.get("end_at"),
        "status": item.get("status"),
        "priority": item.get("priority"),
        "expediente_id": item.get("expediente_id"),
        "board_session_id": item.get("board_session_id"),
        "company_scope": item.get("company_scope"),
        "corporate_area": item.get("corporate_area"),
        "all_day": bool(item.get("all_day")),
        "timezone": item.get("timezone") or "America/Santiago",
        "updated_at": item.get("updated_at"),
        "external_id": item.get("external_id"),
        "sync_status": item.get("sync_status") or "LOCAL_ONLY",
        "provider": item.get("provider"),
    }


def _link_expediente(corporate_root: Path, event: dict, *, actor: str) -> None:
    exp_id = event.get("expediente_id")
    if not exp_id:
        return
    try:
        case = expediente_directory(corporate_root, exp_id)
    except FileNotFoundError:
        return
    master = load_expediente(case)
    stubs = master.setdefault("calendar_events", [])
    stub = {
        "event_id": event["event_id"],
        "title": event.get("title"),
        "event_type": event.get("event_type"),
        "start_at": event.get("start_at"),
        "status": event.get("status"),
    }
    stubs[:] = [s for s in stubs if s.get("event_id") != event["event_id"]] + [stub]
    master.setdefault("eventos", []).append(audit_event(
        expediente_id=exp_id,
        actor=actor,
        actor_type=ACTOR_TYPE_SYSTEM if actor == "SYSTEM" else "HUMAN",
        accion="CALENDAR_EVENT_LINKED",
        objeto_afectado="calendar_events",
        estado_anterior=None,
        estado_nuevo=event.get("status"),
        referencia_version=master.get("version_actual"),
        motivo=f"Evento {event['event_id']} vinculado",
    ))
    save_expediente(case, master)


def create_event(corporate_root: Path, payload: dict | None = None, *, actor: str = "Presidencia LNH") -> dict:
    payload = payload if isinstance(payload, dict) else {}
    title = str(payload.get("title") or "").strip()
    if not title:
        raise ValueError("title es obligatorio.")
    event_type = str(payload.get("event_type") or "OTRO").upper()
    if event_type not in EVENT_TYPES:
        raise ValueError(f"event_type no válido. Use: {', '.join(sorted(EVENT_TYPES))}")
    status = str(payload.get("status") or "PROGRAMADO").upper()
    if status not in EVENT_STATUSES:
        raise ValueError(f"status no válido. Use: {', '.join(sorted(EVENT_STATUSES))}")
    start_at = payload.get("start_at") or now()
    end_at = payload.get("end_at") or start_at
    event_id = payload.get("event_id") or _new_id()
    if (_event_dir(corporate_root, event_id) / "EVENT.json").is_file():
        raise ValueError("Ya existe un evento con ese event_id.")
    stamp = now()
    event = {
        "kind": "calendar_event",
        "schema": SCHEMA,
        "block": "F2B-1",
        "event_id": event_id,
        "title": title,
        "description": str(payload.get("description") or ""),
        "event_type": event_type,
        "start_at": start_at,
        "end_at": end_at,
        "timezone": payload.get("timezone") or "America/Santiago",
        "all_day": bool(payload.get("all_day")),
        "status": status,
        "priority": payload.get("priority") or "NORMAL",
        "expediente_id": payload.get("expediente_id") or None,
        "board_session_id": payload.get("board_session_id") or None,
        "task_id": payload.get("task_id") or None,
        "company_scope": payload.get("company_scope") or "LNH",
        "corporate_area": payload.get("corporate_area") or None,
        "participants": list(payload.get("participants") or []),
        "organizer": payload.get("organizer") or actor,
        "location": payload.get("location") or "",
        "meeting_url": payload.get("meeting_url") or "",
        "source": payload.get("source") or "MISSION_CONTROL",
        "external_id": payload.get("external_id") or None,
        "sync_status": "LOCAL_ONLY",
        "idempotency_key": payload.get("idempotency_key") or None,
        "created_at": stamp,
        "updated_at": stamp,
        "created_by": actor,
        "version": 1,
    }
    # Idempotency: reuse if same key already stored
    if event["idempotency_key"]:
        for existing in list_events(corporate_root):
            full = load_event(corporate_root, existing["event_id"])
            if full.get("idempotency_key") == event["idempotency_key"]:
                return full
    _save_event(_event_dir(corporate_root, event_id), event)
    _link_expediente(corporate_root, event, actor=actor)
    return event


def update_event_status(
    corporate_root: Path,
    event_id: str,
    status: str,
    *,
    actor: str = "Presidencia LNH",
    motivo: str = "",
) -> dict:
    status = str(status or "").upper()
    if status not in EVENT_STATUSES:
        raise ValueError(f"status no válido. Use: {', '.join(sorted(EVENT_STATUSES))}")
    event = load_event(corporate_root, event_id)
    current = event.get("status")
    allowed = STATUS_TRANSITIONS.get(current, frozenset())
    if status != current and status not in allowed:
        raise ValueError(f"Transición de estado no permitida: {current} → {status}")
    event["status"] = status
    event["updated_at"] = now()
    event["version"] = int(event.get("version") or 1) + 1
    if motivo:
        event["status_motivo"] = motivo
    _save_event(_event_dir(corporate_root, event_id), event)
    if event.get("expediente_id"):
        _link_expediente(corporate_root, event, actor=actor)
    return event


def save_event(corporate_root: Path, event: dict) -> dict:
    event_id = event.get("event_id")
    if not event_id:
        raise ValueError("event_id es obligatorio.")
    return _save_event(_event_dir(corporate_root, event_id), event)


def event_view(corporate_root: Path, event_id: str) -> dict:
    return load_event(corporate_root, event_id)


def events_for_expediente(corporate_root: Path, expediente_id: str) -> list[dict]:
    return list_events(corporate_root, expediente_id=expediente_id)
