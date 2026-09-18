"""Thin Meta Graph HTTP transport for WhatsApp Cloud API. Injectable for tests."""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

HttpFn = Callable[[str, str, dict | None, dict | None], dict]


class WhatsAppApiError(RuntimeError):
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
        # Never include Authorization header in error text
        raise WhatsAppApiError(
            f"WhatsApp API HTTP {error.code}",
            status=error.code,
            payload=_sanitize_error_payload(payload),
        ) from error


def _sanitize_error_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        # Keep Meta error structure; drop accidental token-like keys
        cleaned = {}
        for key, value in payload.items():
            if str(key).lower() in {"access_token", "token", "authorization"}:
                continue
            cleaned[key] = value
        return cleaned
    return payload


class WhatsAppHttpClient:
    """OAuth bearer client for Graph API. Token injected; never logged."""

    def __init__(
        self,
        *,
        access_token: str | None = None,
        http: HttpFn | None = None,
        graph_version: str = "v21.0",
        base_url: str = "https://graph.facebook.com",
    ):
        self.access_token = access_token
        self.http = http or default_http
        self.graph_version = graph_version if str(graph_version).startswith("v") else f"v{graph_version}"
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        if not self.access_token:
            raise WhatsAppApiError("Sin access_token. Credencial WhatsApp pendiente.", status=401)
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def send_message(self, phone_number_id: str, body: dict) -> dict:
        pid = urllib.parse.quote(str(phone_number_id), safe="")
        url = f"{self.base_url}/{self.graph_version}/{pid}/messages"
        return self.http("POST", url, self._headers(), body)

    def get_phone_number(self, phone_number_id: str) -> dict:
        """Optional readiness probe — never required for send path."""
        pid = urllib.parse.quote(str(phone_number_id), safe="")
        url = f"{self.base_url}/{self.graph_version}/{pid}"
        return self.http("GET", url, self._headers(), None)
