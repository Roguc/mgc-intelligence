"""Calendar sync LOCAL ↔ Google. Auditable and idempotent."""
from __future__ import annotations

from pathlib import Path

from corporate_engine import corporate_calendar as calendar
from corporate_engine.google_calendar_provider import GoogleCalendarProvider, from_google_event
from corporate_engine.providers import get_calendar_provider
from corporate_engine.store import dump_json, load_json, now

SYNC_LOCAL_ONLY = "LOCAL_ONLY"
SYNC_PENDING = "PENDING_SYNC"
SYNC_SYNCED = "SYNCED"
SYNC_ERROR = "SYNC_ERROR"
SYNC_CONFLICT = "SYNC_CONFLICT"

SYNC_STATUSES = frozenset({
    SYNC_LOCAL_ONLY, SYNC_PENDING, SYNC_SYNCED, SYNC_ERROR, SYNC_CONFLICT,
})


def sync_state_path(corporate_root: Path) -> Path:
    path = Path(corporate_root) / "_calendario" / "sync_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_sync_state(corporate_root: Path) -> dict:
    return load_json(sync_state_path(corporate_root), default={
        "sync_token": None,
        "last_push_at": None,
        "last_pull_at": None,
        "audit": [],
    }) or {}


def save_sync_state(corporate_root: Path, state: dict) -> dict:
    dump_json(sync_state_path(corporate_root), state)
    return state


def _audit(state: dict, action: str, **payload) -> None:
    rows = state.setdefault("audit", [])
    rows.append({"at": now(), "action": action, **payload})
    state["audit"] = rows[-200:]


def push_event_to_google(
    corporate_root: Path,
    event_id: str,
    *,
    provider: GoogleCalendarProvider | None = None,
    actor: str = "SYSTEM",
) -> dict:
    """LOCAL → GOOGLE for one event."""
    event = calendar.load_event(corporate_root, event_id)
    provider = provider or get_calendar_provider()
    if not isinstance(provider, GoogleCalendarProvider):
        raise RuntimeError("Calendar provider actual no es Google.")
    status = provider.status()
    if status.status != "CONNECTED" and provider._client is None:  # noqa: SLF001 — intentional for mock inject
        # Allow injected mock client even if OAuth file absent
        if provider._client is None:
            event["sync_status"] = SYNC_ERROR
            event["sync_error"] = status.message
            event["updated_at"] = now()
            calendar.save_event(corporate_root, event)
            return event

    event["sync_status"] = SYNC_PENDING
    event["updated_at"] = now()
    calendar.save_event(corporate_root, event)

    try:
        remote = provider.upsert_event(event)
        event["external_id"] = remote.get("external_id")
        event["sync_status"] = SYNC_SYNCED
        event["sync_etag"] = remote.get("etag")
        event["sync_error"] = None
        event["synced_at"] = now()
        event["provider"] = "GOOGLE"
        event["version"] = int(event.get("version") or 1) + 1
    except Exception as error:  # noqa: BLE001 — persist SYNC_ERROR
        event["sync_status"] = SYNC_ERROR
        event["sync_error"] = str(error)
        event["version"] = int(event.get("version") or 1) + 1

    event["updated_at"] = now()
    calendar.save_event(corporate_root, event)
    state = load_sync_state(corporate_root)
    _audit(state, "PUSH", event_id=event_id, sync_status=event["sync_status"],
           external_id=event.get("external_id"), actor=actor)
    state["last_push_at"] = now()
    save_sync_state(corporate_root, state)
    return event


def pull_from_google(
    corporate_root: Path,
    *,
    provider: GoogleCalendarProvider | None = None,
    actor: str = "SYSTEM",
) -> dict:
    """GOOGLE → LOCAL. Idempotent via external_id / lnh_event_id. No full personal dump."""
    provider = provider or get_calendar_provider()
    if not isinstance(provider, GoogleCalendarProvider):
        raise RuntimeError("Calendar provider actual no es Google.")
    state = load_sync_state(corporate_root)
    feed = provider.list_remote_events(sync_token=state.get("sync_token"))
    created = updated = skipped = conflicts = 0
    for remote in feed.get("items") or []:
        if remote.get("status") == "cancelled":
            skipped += 1
            continue
        mapped = from_google_event(remote)
        external_id = mapped.get("external_id")
        existing = _find_by_external_id(corporate_root, external_id)
        if not existing and mapped.get("lnh_event_id"):
            try:
                existing = calendar.load_event(corporate_root, mapped["lnh_event_id"])
            except FileNotFoundError:
                existing = None
        if existing:
            result = _merge_remote(corporate_root, existing, mapped)
            if result == SYNC_CONFLICT:
                conflicts += 1
            else:
                updated += 1
        else:
            # Only import events already marked as LNH / explicit private props
            # or when human/config allows — Block 2: require lnh_source marker OR explicit import flag
            private_ok = bool(mapped.get("lnh_event_id") or mapped.get("lnh_expediente_id"))
            if not private_ok:
                skipped += 1
                continue
            calendar.create_event(corporate_root, {
                "title": mapped["title"],
                "description": mapped.get("description"),
                "event_type": "OTRO",
                "start_at": mapped.get("start_at"),
                "end_at": mapped.get("end_at"),
                "all_day": mapped.get("all_day"),
                "timezone": mapped.get("timezone"),
                "location": mapped.get("location"),
                "meeting_url": mapped.get("meeting_url"),
                "expediente_id": mapped.get("lnh_expediente_id"),
                "external_id": external_id,
                "source": "GOOGLE",
                "idempotency_key": f"google:{external_id}",
            }, actor=actor)
            # stamp sync fields
            created_evt = _find_by_external_id(corporate_root, external_id)
            if created_evt:
                created_evt["sync_status"] = SYNC_SYNCED
                created_evt["provider"] = "GOOGLE"
                created_evt["sync_etag"] = mapped.get("etag")
                calendar.save_event(corporate_root, created_evt)
            created += 1

    if feed.get("nextSyncToken"):
        state["sync_token"] = feed["nextSyncToken"]
    state["last_pull_at"] = now()
    _audit(state, "PULL", created=created, updated=updated, skipped=skipped,
           conflicts=conflicts, actor=actor)
    save_sync_state(corporate_root, state)
    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "conflicts": conflicts,
        "sync_token": state.get("sync_token"),
        "platform_calls": 0,
    }


def push_pending_local(corporate_root: Path, *, provider=None, actor: str = "SYSTEM") -> dict:
    pushed = errors = 0
    for row in calendar.list_events(corporate_root):
        full = calendar.load_event(corporate_root, row["event_id"])
        if full.get("sync_status") in {SYNC_SYNCED}:
            continue
        if full.get("source") == "GOOGLE" and full.get("external_id"):
            continue
        result = push_event_to_google(corporate_root, full["event_id"], provider=provider, actor=actor)
        if result.get("sync_status") == SYNC_SYNCED:
            pushed += 1
        elif result.get("sync_status") == SYNC_ERROR:
            errors += 1
    return {"pushed": pushed, "errors": errors, "platform_calls": 0}


def _find_by_external_id(corporate_root: Path, external_id: str | None) -> dict | None:
    if not external_id:
        return None
    for row in calendar.list_events(corporate_root):
        full = calendar.load_event(corporate_root, row["event_id"])
        if full.get("external_id") == external_id:
            return full
    return None


def _merge_remote(corporate_root: Path, local: dict, mapped: dict) -> str:
    local_updated = str(local.get("updated_at") or "")
    remote_updated = str(mapped.get("updated_remote") or "")
    last_sync = str(local.get("synced_at") or "")
    local_dirty = last_sync and local_updated > last_sync
    remote_dirty = last_sync and remote_updated > last_sync
    if local_dirty and remote_dirty and local.get("sync_etag") != mapped.get("etag"):
        local["sync_status"] = SYNC_CONFLICT
        local["sync_error"] = "Conflicto LOCAL vs GOOGLE"
        local["updated_at"] = now()
        calendar.save_event(corporate_root, local)
        return SYNC_CONFLICT
    # Prefer remote when not locally dirty
    if not local_dirty:
        local["title"] = mapped.get("title") or local.get("title")
        local["description"] = mapped.get("description") or local.get("description")
        local["start_at"] = mapped.get("start_at") or local.get("start_at")
        local["end_at"] = mapped.get("end_at") or local.get("end_at")
        local["all_day"] = mapped.get("all_day")
        local["location"] = mapped.get("location") or local.get("location")
    local["external_id"] = mapped.get("external_id")
    local["sync_etag"] = mapped.get("etag")
    local["sync_status"] = SYNC_SYNCED
    local["provider"] = "GOOGLE"
    local["synced_at"] = now()
    local["updated_at"] = now()
    calendar.save_event(corporate_root, local)
    return SYNC_SYNCED
