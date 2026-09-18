"""Google Calendar provider — implements CalendarProvider; no expediente logic."""
from __future__ import annotations

from corporate_engine import google_oauth as oauth
from corporate_engine.google_http import GoogleApiError, GoogleHttpClient
from corporate_engine.providers_base import CalendarProvider, ProviderStatus


class GoogleCalendarProvider(CalendarProvider):
    """Official Google Calendar API adapter."""

    name = "GoogleCalendarProvider"
    provider_key = "GOOGLE"

    def __init__(self, client: GoogleHttpClient | None = None, *, calendar_id: str | None = None):
        self._client = client
        self._calendar_id = calendar_id

    def status(self) -> ProviderStatus:
        state = oauth.google_auth_state()
        calendar_id = self._calendar_id or oauth.google_calendar_id()
        if state["status"] == oauth.STATUS_CONNECTED:
            if calendar_id:
                return ProviderStatus(
                    name=self.name,
                    status=oauth.STATUS_CONNECTED,
                    message="Google Calendar autorizado.",
                    provider=self.provider_key,
                    details={
                        "calendar_id": calendar_id,
                        "account_label": state.get("account_label"),
                    },
                )
            return ProviderStatus(
                name=self.name,
                status=oauth.STATUS_CONNECTED,
                message="OAuth autorizado. Pendiente seleccionar GOOGLE_CALENDAR_ID (calendario LNH).",
                provider=self.provider_key,
                details={
                    "calendar_id": None,
                    "account_label": state.get("account_label"),
                    "calendar_id_pending": True,
                },
            )
        if state["status"] in {oauth.STATUS_NOT_CONFIGURED, oauth.STATUS_PENDING_AUTH}:
            return ProviderStatus(
                name=self.name,
                status=state["status"],
                message=oauth.BUILT_PENDING,
                provider=self.provider_key,
                details={"calendar_id": calendar_id},
            )
        return ProviderStatus(
            name=self.name,
            status=oauth.STATUS_ERROR,
            message=state.get("message") or "Error de configuración Google Calendar.",
            provider=self.provider_key,
        )

    def _require_client(self) -> GoogleHttpClient:
        if self._client:
            return self._client
        raise RuntimeError(
            "GoogleCalendarProvider sin cliente HTTP. "
            "Inyectar cliente OAuth o completar autorización."
        )

    def resolved_calendar_id(self) -> str:
        cid = self._calendar_id or oauth.google_calendar_id()
        if not cid:
            raise ValueError(
                "GOOGLE_CALENDAR_ID no configurado. "
                "Seleccione el calendario LNH sin crearlo automáticamente."
            )
        return cid

    def upsert_event(self, event: dict) -> dict:
        """LOCAL → GOOGLE. Returns {external_id, etag, raw}."""
        client = self._require_client()
        calendar_id = self.resolved_calendar_id()
        body = _to_google_event(event)
        external_id = event.get("external_id")
        try:
            if external_id:
                remote = client.calendar_patch(calendar_id, external_id, body)
            else:
                remote = client.calendar_insert(calendar_id, body)
        except GoogleApiError as error:
            raise RuntimeError(f"SYNC_ERROR: {error}") from error
        return {
            "external_id": remote.get("id"),
            "etag": remote.get("etag"),
            "html_link": remote.get("htmlLink"),
            "updated": remote.get("updated"),
            "raw": remote,
        }

    def list_remote_events(self, *, sync_token: str | None = None) -> dict:
        """GOOGLE → LOCAL feed (caller maps into corporate model)."""
        client = self._require_client()
        calendar_id = self.resolved_calendar_id()
        try:
            return client.calendar_list_events(calendar_id, sync_token=sync_token)
        except GoogleApiError as error:
            raise RuntimeError(f"SYNC_ERROR: {error}") from error

    def list_calendars(self) -> list[dict]:
        client = self._require_client()
        try:
            payload = client.calendar_list_calendars()
        except GoogleApiError as error:
            raise RuntimeError(f"SYNC_ERROR: {error}") from error
        rows = []
        for item in payload.get("items") or []:
            rows.append({
                "id": item.get("id"),
                "summary": item.get("summary"),
                "primary": bool(item.get("primary")),
                "access_role": item.get("accessRole"),
            })
        return rows


def _to_google_event(event: dict) -> dict:
    start = event.get("start_at")
    end = event.get("end_at") or start
    all_day = bool(event.get("all_day"))
    body = {
        "summary": event.get("title") or "(Sin título)",
        "description": event.get("description") or "",
        "location": event.get("location") or "",
    }
    if event.get("meeting_url"):
        body["description"] = (body["description"] + f"\n{event['meeting_url']}").strip()
    if all_day:
        body["start"] = {"date": str(start)[:10]}
        body["end"] = {"date": str(end)[:10]}
    else:
        tz = event.get("timezone") or "America/Santiago"
        body["start"] = {"dateTime": start, "timeZone": tz}
        body["end"] = {"dateTime": end, "timeZone": tz}
    # Corporate markers for idempotent pull
    body["extendedProperties"] = {
        "private": {
            "lnh_event_id": event.get("event_id") or "",
            "lnh_expediente_id": event.get("expediente_id") or "",
            "lnh_source": "MISSION_CONTROL",
        }
    }
    return body


def from_google_event(remote: dict) -> dict:
    """Map Google event → local corporate fields (no invent)."""
    start = remote.get("start") or {}
    end = remote.get("end") or {}
    all_day = "date" in start
    private = ((remote.get("extendedProperties") or {}).get("private")) or {}
    return {
        "external_id": remote.get("id"),
        "title": remote.get("summary") or "(Sin título)",
        "description": remote.get("description") or "",
        "location": remote.get("location") or "",
        "start_at": start.get("dateTime") or start.get("date"),
        "end_at": end.get("dateTime") or end.get("date"),
        "all_day": all_day,
        "timezone": start.get("timeZone") or "America/Santiago",
        "meeting_url": remote.get("hangoutLink") or "",
        "etag": remote.get("etag"),
        "updated_remote": remote.get("updated"),
        "lnh_event_id": private.get("lnh_event_id") or None,
        "lnh_expediente_id": private.get("lnh_expediente_id") or None,
        "status_remote": remote.get("status"),
    }
