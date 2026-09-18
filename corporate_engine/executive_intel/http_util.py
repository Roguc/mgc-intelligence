"""HTTP helpers for executive providers."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class ProviderHttpError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


def _request(url: str, *, timeout: int, headers: dict, method: str = "GET"):
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise ProviderHttpError(f"HTTP {error.code}", status=error.code, payload=detail[:500]) from error
    except urllib.error.URLError as error:
        raise ProviderHttpError(f"Network error: {error.reason}") from error


def http_get_json(url: str, *, timeout: int = 30, headers: dict | None = None) -> dict | list:
    req_headers = {"User-Agent": "LNH-MissionControl/2C-executive", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    with _request(url, timeout=timeout, headers=req_headers) as response:
        raw = response.read().decode("utf-8")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise ProviderHttpError(f"Invalid JSON: {error}") from error


def http_get_text(url: str, *, timeout: int = 30, headers: dict | None = None) -> str:
    req_headers = {
        "User-Agent": "LNH-MissionControl/2C-executive",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    if headers:
        req_headers.update(headers)
    with _request(url, timeout=timeout, headers=req_headers) as response:
        return response.read().decode("utf-8", errors="replace")


def http_resolve_url(url: str, *, timeout: int = 12, headers: dict | None = None) -> str:
    """Follow redirects to obtain a final article URL when available."""
    if not url:
        return url
    req_headers = {
        "User-Agent": "LNH-MissionControl/2C-executive",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.geturl() or url
    except Exception:
        return url
