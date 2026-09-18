"""Fase 2B-2 — Google OAuth configuration (backend-only; no secrets in git)."""
from __future__ import annotations

import json
import os
from pathlib import Path

# Minimum privilege scopes for Calendar + Gmail (Block 2).
GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
)

STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_PENDING_AUTH = "PENDING_AUTH"
STATUS_CONNECTED = "CONNECTED"
STATUS_ERROR = "ERROR"

BUILT_PENDING = "CONSTRUIDO / PENDIENTE AUTORIZACIÓN GOOGLE"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def google_secrets_dir() -> Path:
    """Secure local directory for OAuth artifacts (gitignored via var/)."""
    override = os.environ.get("LNH_GOOGLE_OAUTH_DIR")
    if override:
        path = Path(override)
    else:
        path = _repo_root() / "var" / "google_oauth"
    path.mkdir(parents=True, exist_ok=True)
    return path


def client_secrets_path() -> Path:
    env = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRETS")
    if env:
        return Path(env)
    return google_secrets_dir() / "client_secret.json"


def token_path() -> Path:
    env = os.environ.get("GOOGLE_OAUTH_TOKEN_PATH")
    if env:
        return Path(env)
    return google_secrets_dir() / "token.json"


def load_json_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def corporate_calendar_provider_name() -> str:
    return (os.environ.get("CORPORATE_CALENDAR_PROVIDER") or "GOOGLE").strip().upper()


def corporate_email_provider_name() -> str:
    return (os.environ.get("CORPORATE_EMAIL_PROVIDER") or "GOOGLE").strip().upper()


def corporate_email_account() -> str | None:
    """Configured account identity — never hardcode; may be empty until OAuth."""
    value = (os.environ.get("CORPORATE_EMAIL_ACCOUNT") or "").strip()
    if value:
        return value
    token = load_json_file(token_path()) or {}
    return token.get("account") or token.get("email") or None


def google_calendar_id() -> str | None:
    """Selected Google calendar id (prefer LNH calendar). Not auto-created."""
    value = (os.environ.get("GOOGLE_CALENDAR_ID") or "").strip()
    if value:
        return value
    cfg = load_json_file(google_secrets_dir() / "config.json") or {}
    return cfg.get("calendar_id") or None


def oauth_configured() -> bool:
    secrets = load_json_file(client_secrets_path())
    return bool(secrets)


def token_present() -> bool:
    token = load_json_file(token_path())
    if not token:
        return False
    return bool(token.get("refresh_token") or token.get("token") or token.get("access_token"))


def google_auth_state() -> dict:
    """Backend-only auth readiness. Never returns secrets."""
    has_client = oauth_configured()
    has_token = token_present()
    account = corporate_email_account()
    calendar_id = google_calendar_id()
    if not has_client:
        status = STATUS_NOT_CONFIGURED
        message = BUILT_PENDING
    elif not has_token:
        status = STATUS_PENDING_AUTH
        message = BUILT_PENDING
    else:
        status = STATUS_CONNECTED
        message = "OAuth autorizado. Tokens en backend."
    return {
        "provider": "GOOGLE",
        "status": status,
        "message": message,
        "scopes": list(GOOGLE_SCOPES),
        "account_configured": bool(account),
        "account_label": account if account else None,
        "calendar_id_configured": bool(calendar_id),
        "calendar_id": calendar_id,
        "client_secrets_present": has_client,
        "token_present": has_token,
        "secrets_dir": str(google_secrets_dir()),
        "platform_calls": 0,
    }


def load_access_token(*, persist_refresh: bool = True) -> str | None:
    """Load OAuth access token from token.json; refresh if expired."""
    token_data = load_json_file(token_path())
    if not token_data:
        return None
    raw = token_data.get("token") or token_data.get("access_token")
    refresh = token_data.get("refresh_token")
    if not refresh and raw:
        return raw
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        creds = Credentials(
            token=raw,
            refresh_token=refresh,
            token_uri=token_data.get("token_uri") or "https://oauth2.googleapis.com/token",
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes") or list(GOOGLE_SCOPES),
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if persist_refresh:
                token_data["token"] = creds.token
                token_path().write_text(
                    json.dumps(token_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
        return creds.token or raw
    except Exception:
        return raw


def make_http_client():
    """Build GoogleHttpClient when OAuth token is available."""
    token = load_access_token()
    if not token:
        return None
    from corporate_engine.google_http import GoogleHttpClient

    return GoogleHttpClient(access_token=token)


def save_provider_config(payload: dict | None = None) -> dict:
    """Persist non-secret operational config (calendar_id, account label)."""
    payload = payload if isinstance(payload, dict) else {}
    path = google_secrets_dir() / "config.json"
    current = load_json_file(path) or {}
    if "calendar_id" in payload:
        current["calendar_id"] = payload.get("calendar_id") or None
    if "account" in payload or "CORPORATE_EMAIL_ACCOUNT" in payload:
        current["account"] = payload.get("account") or payload.get("CORPORATE_EMAIL_ACCOUNT") or None
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    if current.get("account") and not os.environ.get("CORPORATE_EMAIL_ACCOUNT"):
        # Session-only hint; durable value stays in config.json
        pass
    return {
        "calendar_id": current.get("calendar_id"),
        "account": current.get("account"),
        "saved": True,
    }
