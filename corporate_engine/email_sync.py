"""Email inbound sync: Gmail API → Mission Control communications + notifications.

Channel-agnostic ingest lives in corporate_communications.ingest_inbound_communication
so WhatsApp (Bloque 3) can reuse the same MC → expediente/notificación/Human Gate path.
"""
from __future__ import annotations

from pathlib import Path

from corporate_engine import corporate_communications as communications
from corporate_engine import corporate_notifications as notifications
from corporate_engine.gmail_provider import GmailProvider
from corporate_engine.providers import get_email_provider
from corporate_engine.store import dump_json, load_json, now


def sync_state_path(corporate_root: Path) -> Path:
    path = Path(corporate_root) / "_comunicaciones" / "email_sync_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_sync_state(corporate_root: Path) -> dict:
    return load_json(sync_state_path(corporate_root), default={
        "processed_external_ids": [],
        "last_pull_at": None,
        "last_query": None,
        "audit": [],
    }) or {}


def save_sync_state(corporate_root: Path, state: dict) -> dict:
    dump_json(sync_state_path(corporate_root), state)
    return state


def _audit(state: dict, action: str, **payload) -> None:
    rows = state.setdefault("audit", [])
    rows.append({"at": now(), "action": action, **payload})
    state["audit"] = rows[-200:]


def pull_inbound_email(
    corporate_root: Path,
    *,
    provider: GmailProvider | None = None,
    actor: str = "SYSTEM",
    query: str = "in:inbox",
    max_results: int = 25,
) -> dict:
    """Gmail INBOX → local RECEIVED communications + COMUNICACION_RECIBIDA notifications.

    Idempotent on Gmail message id. Does not create expediente automatically.
    platform_calls always 0 (no OpenAI Platform).
    """
    provider = provider or get_email_provider()
    if not isinstance(provider, GmailProvider):
        raise RuntimeError("Email provider actual no soporta inbound Gmail.")
    status = provider.status()
    if status.status != "CONNECTED" and provider._client is None:  # noqa: SLF001
        return {
            "created": 0,
            "duplicates": 0,
            "errors": 0,
            "skipped": 0,
            "items": [],
            "message": status.message,
            "platform_calls": 0,
        }

    try:
        if hasattr(provider, "resolve_account"):
            provider.resolve_account()
    except Exception:  # noqa: BLE001
        pass

    state = load_sync_state(corporate_root)
    processed = set(state.get("processed_external_ids") or [])
    feed = provider.list_inbound(query=query, max_results=max_results)
    created = duplicates = errors = skipped = 0
    items: list[dict] = []

    for ref in feed.get("items") or []:
        message_id = ref.get("id") if isinstance(ref, dict) else None
        if not message_id:
            skipped += 1
            continue
        if message_id in processed and communications.find_by_external_id(corporate_root, message_id):
            duplicates += 1
            continue
        try:
            mapped = provider.fetch_message(message_id)
            result = communications.ingest_inbound_communication(
                corporate_root,
                {
                    "channel": "EMAIL",
                    "external_id": mapped.get("external_id") or message_id,
                    "thread_id": mapped.get("thread_id"),
                    "subject": mapped.get("subject"),
                    "body": mapped.get("body"),
                    "summary": mapped.get("summary"),
                    "sender": mapped.get("sender"),
                    "recipients": mapped.get("recipients") or [],
                    "cc": mapped.get("cc") or [],
                    "received_at": mapped.get("received_at"),
                    "provider": "GOOGLE",
                    "provider_status": "RECEIVED",
                    "read_status": mapped.get("read_status") or "UNREAD",
                    "raw_headers": mapped.get("raw_headers"),
                    "label_ids": mapped.get("label_ids"),
                    "snippet": mapped.get("snippet"),
                    "idempotency_key": f"gmail:{mapped.get('external_id') or message_id}",
                },
                actor=actor,
            )
            item = result["item"]
            if result.get("duplicate"):
                duplicates += 1
            else:
                created += 1
                _notify_inbound(corporate_root, item, actor=actor)
            processed.add(message_id)
            items.append({
                "communication_id": item.get("communication_id"),
                "external_id": item.get("external_id"),
                "subject": item.get("subject"),
                "created": bool(result.get("created")),
                "duplicate": bool(result.get("duplicate")),
            })
        except Exception as error:  # noqa: BLE001 — continue other messages
            errors += 1
            _audit(state, "PULL_ERROR", external_id=message_id, error=str(error), actor=actor)

    state["processed_external_ids"] = sorted(processed)[-2000:]
    state["last_pull_at"] = now()
    state["last_query"] = query
    _audit(
        state, "PULL",
        created=created, duplicates=duplicates, errors=errors, skipped=skipped, actor=actor,
    )
    save_sync_state(corporate_root, state)
    return {
        "created": created,
        "duplicates": duplicates,
        "errors": errors,
        "skipped": skipped,
        "items": items,
        "query": query,
        "platform_calls": 0,
    }


def _notify_inbound(corporate_root: Path, item: dict, *, actor: str = "SYSTEM") -> dict:
    external_id = item.get("external_id")
    subject = item.get("subject") or "(Sin asunto)"
    sender = item.get("sender") or "Remitente desconocido"
    return notifications.create_notification(
        corporate_root,
        {
            "type": "COMUNICACION_RECIBIDA",
            "title": f"Email recibido: {subject}",
            "message": f"De {sender}",
            "priority": "NORMAL",
            "recipient_scope": "PRESIDENCIA",
            "expediente_id": item.get("expediente_id"),
            "communication_id": item.get("communication_id"),
            "idempotency_key": f"auto:COMUNICACION_RECIBIDA:gmail:{external_id}",
        },
        actor=actor,
    )
