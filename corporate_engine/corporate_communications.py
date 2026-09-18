"""Fase 2B-1 — Corporate communications (DRAFT-first; no external send)."""
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
CHANNELS = frozenset({"EMAIL", "WHATSAPP", "INTERNAL"})
DIRECTIONS = frozenset({"INBOUND", "OUTBOUND", "INTERNAL"})
COMM_STATUSES = frozenset({
    "DRAFT", "PENDIENTE_APROBACION", "APROBADO", "RECHAZADO",
    "QUEUED", "SENT", "DELIVERED", "RECEIVED", "FAILED", "CANCELLED",
})
# Create path: only DRAFT / CANCELLED (send goes through email_gate)
ALLOWED_CREATE_STATUSES = frozenset({"DRAFT", "CANCELLED"})


def communications_root(corporate_root: Path) -> Path:
    path = Path(corporate_root) / "_comunicaciones"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _comm_dir(corporate_root: Path, communication_id: str) -> Path:
    return communications_root(corporate_root) / communication_id


def _new_id() -> str:
    return f"com-{uuid4().hex}"


def _save(folder: Path, item: dict) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    dump_json(folder / "COMM.json", item)
    return item


def load_communication(corporate_root: Path, communication_id: str) -> dict:
    path = _comm_dir(corporate_root, communication_id) / "COMM.json"
    if not path.is_file():
        raise FileNotFoundError("Comunicación no encontrada.")
    return load_json(path)


def effective_communication_timestamp(item: dict) -> str:
    """Sort/display timestamp: inbound → received_at; outbound sent → sent_at; else created_at."""
    direction = str(item.get("direction") or "").upper()
    status = str(item.get("status") or "").upper()
    if direction == "INBOUND":
        return str(item.get("received_at") or item.get("created_at") or "")
    if status in {"SENT", "DELIVERED"}:
        return str(item.get("sent_at") or item.get("created_at") or "")
    return str(item.get("created_at") or item.get("updated_at") or "")


def _summary(item: dict) -> dict:
    effective_at = effective_communication_timestamp(item)
    return {
        "communication_id": item.get("communication_id"),
        "channel": item.get("channel"),
        "direction": item.get("direction"),
        "subject": item.get("subject"),
        "summary": item.get("summary"),
        "sender": item.get("sender"),
        "recipients": item.get("recipients") or [],
        "status": item.get("status"),
        "read_status": item.get("read_status") or ("UNREAD" if item.get("direction") == "INBOUND" else None),
        "expediente_id": item.get("expediente_id"),
        "board_session_id": item.get("board_session_id"),
        "task_id": item.get("task_id"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "sent_at": item.get("sent_at"),
        "received_at": item.get("received_at"),
        "effective_at": effective_at or None,
        "external_id": item.get("external_id"),
        "thread_id": item.get("thread_id"),
        "provider": item.get("provider"),
        "provider_status": item.get("provider_status"),
        "provider_error": item.get("provider_error"),
        "human_gate_status": item.get("human_gate_status"),
        "requires_human_gate": bool(item.get("requires_human_gate")),
        "approved_at": item.get("approved_at"),
        "template_name": item.get("template_name") or (item.get("template") or {}).get("name"),
    }


def list_communications(
    corporate_root: Path,
    *,
    channel: str | None = None,
    status: str | None = None,
    direction: str | None = None,
    expediente_id: str | None = None,
) -> list[dict]:
    rows = []
    root = communications_root(corporate_root)
    for folder in root.iterdir():
        path = folder / "COMM.json"
        if not path.is_file():
            continue
        item = load_json(path)
        if channel and item.get("channel") != str(channel).upper():
            continue
        if status and item.get("status") != str(status).upper():
            continue
        if direction and item.get("direction") != str(direction).upper():
            continue
        if expediente_id and item.get("expediente_id") != expediente_id:
            continue
        rows.append(_summary(item))
    rows.sort(key=lambda r: r.get("effective_at") or "", reverse=True)
    return rows


def _link_expediente(corporate_root: Path, item: dict, *, actor: str) -> None:
    exp_id = item.get("expediente_id")
    if not exp_id:
        return
    try:
        case = expediente_directory(corporate_root, exp_id)
    except FileNotFoundError:
        return
    master = load_expediente(case)
    stubs = master.setdefault("communications", [])
    stub = {
        "communication_id": item["communication_id"],
        "channel": item.get("channel"),
        "subject": item.get("subject"),
        "status": item.get("status"),
        "direction": item.get("direction"),
        "created_at": item.get("created_at"),
    }
    stubs[:] = [s for s in stubs if s.get("communication_id") != item["communication_id"]] + [stub]
    master.setdefault("eventos", []).append(audit_event(
        expediente_id=exp_id,
        actor=actor,
        actor_type=ACTOR_TYPE_SYSTEM if actor == "SYSTEM" else "HUMAN",
        accion="COMMUNICATION_LINKED",
        objeto_afectado="communications",
        estado_anterior=None,
        estado_nuevo=item.get("status"),
        referencia_version=master.get("version_actual"),
        motivo=f"Comunicación {item['communication_id']} vinculada",
    ))
    save_expediente(case, master)


def create_communication(
    corporate_root: Path,
    payload: dict | None = None,
    *,
    actor: str = "Presidencia LNH",
) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    channel = str(payload.get("channel") or "INTERNAL").upper()
    if channel not in CHANNELS:
        raise ValueError(f"channel no válido. Use: {', '.join(sorted(CHANNELS))}")
    direction = str(payload.get("direction") or ("INTERNAL" if channel == "INTERNAL" else "OUTBOUND")).upper()
    if direction not in DIRECTIONS:
        raise ValueError(f"direction no válido. Use: {', '.join(sorted(DIRECTIONS))}")
    status = str(payload.get("status") or "DRAFT").upper()
    # Create path never claims SENT/DELIVERED/QUEUED — use email_gate pipeline
    if status in {"SENT", "DELIVERED", "QUEUED", "RECEIVED", "APROBADO", "PENDIENTE_APROBACION"}:
        raise ValueError(
            "No se puede crear directamente en estado de envío/aprobación. Use DRAFT y el flujo Human Gate."
        )
    if status not in ALLOWED_CREATE_STATUSES:
        raise ValueError(f"status no válido al crear. Use: {', '.join(sorted(ALLOWED_CREATE_STATUSES))}")
    subject = str(payload.get("subject") or "").strip() or "(Sin asunto)"
    body = str(payload.get("body") or "")
    communication_id = payload.get("communication_id") or _new_id()
    if (_comm_dir(corporate_root, communication_id) / "COMM.json").is_file():
        raise ValueError("Ya existe una comunicación con ese communication_id.")
    stamp = now()
    requires_gate = bool(payload.get("requires_human_gate")) if "requires_human_gate" in payload else (
        channel in {"EMAIL", "WHATSAPP"}
    )
    item = {
        "kind": "corporate_communication",
        "schema": SCHEMA,
        "block": "F2B-2",
        "communication_id": communication_id,
        "channel": channel,
        "direction": direction,
        "subject": subject,
        "body": body,
        "summary": payload.get("summary") or (body[:160] if body else subject),
        "sender": payload.get("sender") or actor,
        "recipients": list(payload.get("recipients") or []),
        "cc": list(payload.get("cc") or []),
        "bcc": list(payload.get("bcc") or []),
        "expediente_id": payload.get("expediente_id") or None,
        "task_id": payload.get("task_id") or None,
        "board_session_id": payload.get("board_session_id") or None,
        "attachments": list(payload.get("attachments") or []),
        "template": payload.get("template") if isinstance(payload.get("template"), dict) else None,
        "template_name": payload.get("template_name") or None,
        "template_language": payload.get("template_language") or None,
        "template_components": list(payload.get("template_components") or []) if payload.get("template_components") else None,
        "status": status,
        "external_id": None,
        "thread_id": payload.get("thread_id") or None,
        "idempotency_key": payload.get("idempotency_key") or None,
        "provider": payload.get("provider") or (
            "GOOGLE" if channel == "EMAIL" else ("META" if channel == "WHATSAPP" else None)
        ),
        "provider_status": "NOT_CONFIGURED",
        "requires_human_gate": requires_gate,
        "human_gate_status": payload.get("human_gate_status") or None,
        "created_at": stamp,
        "updated_at": stamp,
        "sent_at": None,
        "received_at": None,
        "approved_at": None,
        "created_by": actor,
        "version": 1,
    }
    if item["idempotency_key"]:
        for existing in list_communications(corporate_root):
            full = load_communication(corporate_root, existing["communication_id"])
            if full.get("idempotency_key") == item["idempotency_key"]:
                return full
    _save(_comm_dir(corporate_root, communication_id), item)
    _link_expediente(corporate_root, item, actor=actor)
    return item


def communication_view(corporate_root: Path, communication_id: str) -> dict:
    return load_communication(corporate_root, communication_id)


def communications_for_expediente(corporate_root: Path, expediente_id: str) -> list[dict]:
    return list_communications(corporate_root, expediente_id=expediente_id)


def find_by_external_id(corporate_root: Path, external_id: str | None) -> dict | None:
    if not external_id:
        return None
    for row in list_communications(corporate_root):
        full = load_communication(corporate_root, row["communication_id"])
        if full.get("external_id") == external_id:
            return full
        if full.get("idempotency_key") in {f"gmail:{external_id}", f"whatsapp:{external_id}", f"inbound:{external_id}"}:
            return full
    return None


def ingest_inbound_communication(
    corporate_root: Path,
    payload: dict | None = None,
    *,
    actor: str = "SYSTEM",
) -> dict:
    """Materialize provider inbound message as RECEIVED. Idempotent on external_id.

    Used by Gmail (and later WhatsApp) sync — not the public DRAFT create path.
    Does not auto-create expediente.
    """
    payload = payload if isinstance(payload, dict) else {}
    channel = str(payload.get("channel") or "EMAIL").upper()
    if channel not in CHANNELS:
        raise ValueError(f"channel no válido. Use: {', '.join(sorted(CHANNELS))}")
    external_id = payload.get("external_id")
    if not external_id:
        raise ValueError("external_id es obligatorio para inbound.")
    existing = find_by_external_id(corporate_root, external_id)
    if existing:
        return {"item": existing, "created": False, "duplicate": True}

    idem = payload.get("idempotency_key") or f"{channel.lower()}:{external_id}"
    for row in list_communications(corporate_root):
        full = load_communication(corporate_root, row["communication_id"])
        if full.get("idempotency_key") == idem:
            return {"item": full, "created": False, "duplicate": True}

    stamp = now()
    received_at = payload.get("received_at") or stamp
    communication_id = payload.get("communication_id") or _new_id()
    subject = str(payload.get("subject") or "").strip() or "(Sin asunto)"
    body = str(payload.get("body") or "")
    item = {
        "kind": "corporate_communication",
        "schema": SCHEMA,
        "block": "F2B-2",
        "communication_id": communication_id,
        "channel": channel,
        "direction": "INBOUND",
        "subject": subject,
        "body": body,
        "summary": payload.get("summary") or (body[:160] if body else subject),
        "sender": payload.get("sender") or "",
        "recipients": list(payload.get("recipients") or []),
        "cc": list(payload.get("cc") or []),
        "bcc": list(payload.get("bcc") or []),
        "expediente_id": payload.get("expediente_id") or None,
        "task_id": payload.get("task_id") or None,
        "board_session_id": payload.get("board_session_id") or None,
        "attachments": list(payload.get("attachments") or []),
        "status": "RECEIVED",
        "read_status": payload.get("read_status") or "UNREAD",
        "external_id": external_id,
        "thread_id": payload.get("thread_id") or None,
        "idempotency_key": idem,
        "provider": payload.get("provider") or ("GOOGLE" if channel == "EMAIL" else channel),
        "provider_status": payload.get("provider_status") or "RECEIVED",
        "requires_human_gate": False,
        "human_gate_status": None,
        "source_ref": payload.get("source_ref") or {
            "provider": payload.get("provider"),
            "external_id": external_id,
            "thread_id": payload.get("thread_id"),
            "raw_headers": payload.get("raw_headers"),
            "label_ids": payload.get("label_ids"),
            "snippet": payload.get("snippet"),
        },
        "created_at": stamp,
        "updated_at": stamp,
        "sent_at": None,
        "received_at": received_at,
        "approved_at": None,
        "created_by": actor,
        "version": 1,
    }
    _save(_comm_dir(corporate_root, communication_id), item)
    if item.get("expediente_id"):
        _link_expediente(corporate_root, item, actor=actor)
    return {"item": item, "created": True, "duplicate": False}


def link_communication_to_expediente(
    corporate_root: Path,
    communication_id: str,
    expediente_id: str,
    *,
    actor: str = "Presidencia LNH",
) -> dict:
    """Link existing communication to an existing expediente. No auto-create."""
    expediente_id = str(expediente_id or "").strip()
    if not expediente_id:
        raise ValueError("expediente_id es obligatorio.")
    # Ensure expediente exists
    expediente_directory(corporate_root, expediente_id)
    item = load_communication(corporate_root, communication_id)
    previous = item.get("expediente_id")
    item["expediente_id"] = expediente_id
    item["updated_at"] = now()
    item["updated_by"] = actor
    item["version"] = int(item.get("version") or 1) + 1
    _save(_comm_dir(corporate_root, communication_id), item)
    _link_expediente(corporate_root, item, actor=actor)
    item["previous_expediente_id"] = previous
    return item


def mark_communication_read(
    corporate_root: Path,
    communication_id: str,
    *,
    actor: str = "Presidencia LNH",
) -> dict:
    item = load_communication(corporate_root, communication_id)
    if item.get("read_status") != "READ":
        item["read_status"] = "READ"
        item["read_at"] = now()
        item["updated_at"] = item["read_at"]
        item["updated_by"] = actor
        item["version"] = int(item.get("version") or 1) + 1
        _save(_comm_dir(corporate_root, communication_id), item)
    return item


def save_communication(corporate_root: Path, item: dict) -> dict:
    communication_id = item.get("communication_id")
    if not communication_id:
        raise ValueError("communication_id es obligatorio.")
    return _save(_comm_dir(corporate_root, communication_id), item)
