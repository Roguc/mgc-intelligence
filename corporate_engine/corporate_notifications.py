"""Fase 2B-1 — Internal Mission Control notifications."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from corporate_engine.store import dump_json, load_json, now

SCHEMA = "LNH-DATA-001"
NOTIF_TYPES = frozenset({
    "NUEVO_EXPEDIENTE",
    "TAREA_ASIGNADA",
    "TAREA_VENCIDA",
    "HUMAN_GATE_PENDIENTE",
    "DIRECTORIO_REQUERIDO",
    "SESION_PROGRAMADA",
    "DECISION_REGISTRADA",
    "COMUNICACION_RECIBIDA",
    "SISTEMA",
})
NOTIF_STATUSES = frozenset({"UNREAD", "READ", "ARCHIVED"})
PRIORITIES = frozenset({"LOW", "NORMAL", "HIGH", "CRITICAL"})


def notifications_root(corporate_root: Path) -> Path:
    path = Path(corporate_root) / "_notificaciones"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _notif_dir(corporate_root: Path, notification_id: str) -> Path:
    return notifications_root(corporate_root) / notification_id


def _new_id() -> str:
    return f"ntf-{uuid4().hex}"


def _save(folder: Path, item: dict) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    dump_json(folder / "NOTIF.json", item)
    return item


def load_notification(corporate_root: Path, notification_id: str) -> dict:
    path = _notif_dir(corporate_root, notification_id) / "NOTIF.json"
    if not path.is_file():
        raise FileNotFoundError("Notificación no encontrada.")
    return load_json(path)


def _summary(item: dict) -> dict:
    priority = item.get("priority") or item.get("severity") or "NORMAL"
    return {
        "notification_id": item.get("notification_id"),
        "type": item.get("type"),
        "title": item.get("title"),
        "message": item.get("message"),
        "severity": item.get("severity") or priority,
        "priority": priority,
        "recipient_scope": item.get("recipient_scope"),
        "recipient_area": item.get("recipient_area"),
        "expediente_id": item.get("expediente_id"),
        "communication_id": item.get("communication_id"),
        "task_id": item.get("task_id"),
        "board_session_id": item.get("board_session_id"),
        "status": item.get("status"),
        "created_at": item.get("created_at"),
        "read_at": item.get("read_at"),
        "idempotency_key": item.get("idempotency_key"),
    }


def list_notifications(
    corporate_root: Path,
    *,
    status: str | None = None,
    notif_type: str | None = None,
    expediente_id: str | None = None,
) -> list[dict]:
    rows = []
    root = notifications_root(corporate_root)
    for folder in sorted(root.iterdir(), reverse=True):
        path = folder / "NOTIF.json"
        if not path.is_file():
            continue
        item = load_json(path)
        if status and item.get("status") != str(status).upper():
            continue
        if notif_type and item.get("type") != str(notif_type).upper():
            continue
        if expediente_id and item.get("expediente_id") != expediente_id:
            continue
        rows.append(_summary(item))
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows


def unread_count(corporate_root: Path) -> int:
    return len(list_notifications(corporate_root, status="UNREAD"))


def create_notification(
    corporate_root: Path,
    payload: dict | None = None,
    *,
    actor: str = "SYSTEM",
) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    notif_type = str(payload.get("type") or "SISTEMA").upper()
    if notif_type not in NOTIF_TYPES:
        raise ValueError(f"type no válido. Use: {', '.join(sorted(NOTIF_TYPES))}")
    title = str(payload.get("title") or "").strip()
    message = str(payload.get("message") or "").strip()
    if not title or not message:
        raise ValueError("title y message son obligatorios.")
    priority = str(payload.get("priority") or payload.get("severity") or "NORMAL").upper()
    if priority not in PRIORITIES:
        raise ValueError(f"priority no válido. Use: {', '.join(sorted(PRIORITIES))}")
    idem = payload.get("idempotency_key")
    if idem:
        for existing in list_notifications(corporate_root):
            if existing.get("idempotency_key") == idem:
                return load_notification(corporate_root, existing["notification_id"])
            # also check full file for key if summary omits older shape
        for folder in notifications_root(corporate_root).iterdir():
            path = folder / "NOTIF.json"
            if not path.is_file():
                continue
            full = load_json(path)
            if full.get("idempotency_key") == idem:
                return full
    notification_id = payload.get("notification_id") or _new_id()
    if (_notif_dir(corporate_root, notification_id) / "NOTIF.json").is_file():
        raise ValueError("Ya existe una notificación con ese notification_id.")
    stamp = now()
    item = {
        "kind": "corporate_notification",
        "schema": SCHEMA,
        "block": "F2B-1",
        "notification_id": notification_id,
        "type": notif_type,
        "title": title,
        "message": message,
        "priority": priority,
        "severity": priority,
        "recipient_scope": payload.get("recipient_scope") or "PRESIDENCIA",
        "recipient_area": payload.get("recipient_area") or None,
        "expediente_id": payload.get("expediente_id") or None,
        "communication_id": payload.get("communication_id") or None,
        "task_id": payload.get("task_id") or None,
        "board_session_id": payload.get("board_session_id") or None,
        "status": "UNREAD",
        "idempotency_key": idem,
        "created_at": stamp,
        "read_at": None,
        "archived_at": None,
        "created_by": actor,
        "version": 1,
    }
    _save(_notif_dir(corporate_root, notification_id), item)
    return item


def mark_read(corporate_root: Path, notification_id: str) -> dict:
    item = load_notification(corporate_root, notification_id)
    if item.get("status") == "ARCHIVED":
        return item
    if item.get("status") != "READ":
        item["status"] = "READ"
        item["read_at"] = now()
        item["version"] = int(item.get("version") or 1) + 1
        _save(_notif_dir(corporate_root, notification_id), item)
    return item


def archive_notification(corporate_root: Path, notification_id: str) -> dict:
    item = load_notification(corporate_root, notification_id)
    if item.get("status") != "ARCHIVED":
        item["status"] = "ARCHIVED"
        item["archived_at"] = now()
        if not item.get("read_at"):
            item["read_at"] = item["archived_at"]
        item["version"] = int(item.get("version") or 1) + 1
        _save(_notif_dir(corporate_root, notification_id), item)
    return item


def notifications_for_expediente(corporate_root: Path, expediente_id: str) -> list[dict]:
    return list_notifications(corporate_root, expediente_id=expediente_id)
