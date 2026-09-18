"""Thin Google REST transport. Injectable for tests; no Platform."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable


HttpFn = Callable[[str, str, dict | None, dict | None], dict]


class GoogleApiError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


def default_http(method: str, url: str, headers: dict | None = None, body: dict | None = None) -> dict:
    data = None
    req_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail) if detail else None
        except json.JSONDecodeError:
            payload = detail
        raise GoogleApiError(f"Google API HTTP {error.code}", status=error.status, payload=payload) from error


class GoogleHttpClient:
    """OAuth-aware HTTP client. Uses access_token from token file / injected token."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        http: HttpFn | None = None,
        base_calendar: str = "https://www.googleapis.com/calendar/v3",
        base_gmail: str = "https://gmail.googleapis.com/gmail/v1",
    ):
        self.access_token = access_token
        self.http = http or default_http
        self.base_calendar = base_calendar.rstrip("/")
        self.base_gmail = base_gmail.rstrip("/")

    def _headers(self) -> dict:
        if not self.access_token:
            raise GoogleApiError("Sin access_token. OAuth pendiente.", status=401)
        return {"Authorization": f"Bearer {self.access_token}"}

    def calendar_insert(self, calendar_id: str, event_body: dict) -> dict:
        cid = urllib.parse.quote(calendar_id, safe="")
        return self.http("POST", f"{self.base_calendar}/calendars/{cid}/events", self._headers(), event_body)

    def calendar_patch(self, calendar_id: str, event_id: str, event_body: dict) -> dict:
        cid = urllib.parse.quote(calendar_id, safe="")
        eid = urllib.parse.quote(event_id, safe="")
        return self.http("PATCH", f"{self.base_calendar}/calendars/{cid}/events/{eid}", self._headers(), event_body)

    def calendar_list_events(self, calendar_id: str, *, sync_token: str | None = None, page_token: str | None = None) -> dict:
        cid = urllib.parse.quote(calendar_id, safe="")
        query = {}
        if sync_token:
            query["syncToken"] = sync_token
        if page_token:
            query["pageToken"] = page_token
        qs = ("?" + urllib.parse.urlencode(query)) if query else ""
        return self.http("GET", f"{self.base_calendar}/calendars/{cid}/events{qs}", self._headers(), None)

    def calendar_list_calendars(self) -> dict:
        return self.http("GET", f"{self.base_calendar}/users/me/calendarList", self._headers(), None)

    def gmail_send(self, raw_message_b64: str) -> dict:
        return self.http(
            "POST",
            f"{self.base_gmail}/users/me/messages/send",
            self._headers(),
            {"raw": raw_message_b64},
        )

    def gmail_list_messages(
        self,
        *,
        query: str | None = None,
        label_ids: list[str] | None = None,
        max_results: int = 25,
        page_token: str | None = None,
    ) -> dict:
        params: dict[str, str] = {"maxResults": str(max(1, min(int(max_results), 100)))}
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token
        for label in label_ids or []:
            # Gmail accepts repeated labelIds; encode as first for simplicity via comma is invalid —
            # use single INBOX label via query when multiple needed.
            params["labelIds"] = label
            break
        qs = "?" + urllib.parse.urlencode(params)
        return self.http("GET", f"{self.base_gmail}/users/me/messages{qs}", self._headers(), None)

    def gmail_get_message(self, message_id: str, *, format: str = "full") -> dict:
        mid = urllib.parse.quote(message_id, safe="")
        qs = "?" + urllib.parse.urlencode({"format": format})
        return self.http("GET", f"{self.base_gmail}/users/me/messages/{mid}{qs}", self._headers(), None)

    def gmail_get_profile(self) -> dict:
        return self.http("GET", f"{self.base_gmail}/users/me/profile", self._headers(), None)
