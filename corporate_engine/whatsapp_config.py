"""Fase 2B-3 — WhatsApp Cloud API configuration (backend-only; never expose tokens)."""
from __future__ import annotations

import json
import os
from pathlib import Path

STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_PENDING_AUTH = "PENDING_AUTH"
STATUS_CONNECTED = "CONNECTED"
STATUS_ERROR = "ERROR"

BUILT_PENDING = "CONSTRUIDO / PENDIENTE CREDENCIAL WHATSAPP"

# Official Graph API version for Cloud API message endpoint.
DEFAULT_GRAPH_API_VERSION = "v21.0"

# Confirmed LNH corporate identifiers (non-secret).
DEFAULT_PHONE_NUMBER_ID = "117045607940661"
DEFAULT_WABA_ID = "108005232186959"
DEFAULT_DISPLAY_NUMBER = "+56988912564"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_dotenv_file() -> None:
    """Load KEY=VALUE from repo .env into os.environ if key not already set.

    Never prints values. .env is gitignored.
    """
    path = _repo_root() / ".env"
    if not path.is_file():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#") or "=" not in raw:
                continue
            key, _, value = raw.partition("=")
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip().strip('"').strip("'")
            os.environ[key] = value
    except OSError:
        return


_load_dotenv_file()


def whatsapp_secrets_dir() -> Path:
    override = os.environ.get("LNH_WHATSAPP_DIR")
    if override:
        path = Path(override)
    else:
        path = _repo_root() / "var" / "whatsapp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_path() -> Path:
    env = os.environ.get("WHATSAPP_TOKEN_PATH")
    if env:
        return Path(env)
    return whatsapp_secrets_dir() / "token.json"


def config_path() -> Path:
    return whatsapp_secrets_dir() / "config.json"


def load_json_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def corporate_whatsapp_provider_name() -> str:
    return (os.environ.get("CORPORATE_WHATSAPP_PROVIDER") or "META").strip().upper()


def graph_api_version() -> str:
    value = (os.environ.get("WHATSAPP_GRAPH_API_VERSION") or "").strip()
    if value:
        return value if value.startswith("v") else f"v{value}"
    cfg = load_json_file(config_path()) or {}
    version = str(cfg.get("graph_api_version") or DEFAULT_GRAPH_API_VERSION).strip()
    return version if version.startswith("v") else f"v{version}"


def phone_number_id() -> str | None:
    value = (os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or "").strip()
    if value:
        return value
    cfg = load_json_file(config_path()) or {}
    return (cfg.get("phone_number_id") or None)


def waba_id() -> str | None:
    value = (os.environ.get("WHATSAPP_WABA_ID") or "").strip()
    if value:
        return value
    cfg = load_json_file(config_path()) or {}
    return (cfg.get("waba_id") or None)


def display_phone_number() -> str | None:
    value = (os.environ.get("WHATSAPP_DISPLAY_PHONE_NUMBER") or "").strip()
    if value:
        return value
    cfg = load_json_file(config_path()) or {}
    return cfg.get("display_phone_number") or None


def load_access_token() -> str | None:
    """Load access token from env or local token.json. Never log or return via API."""
    env = (os.environ.get("WHATSAPP_ACCESS_TOKEN") or "").strip()
    if env:
        return env
    token_file = load_json_file(token_path()) or {}
    raw = token_file.get("access_token") or token_file.get("token")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    # Plain text fallback (single line file)
    plain = whatsapp_secrets_dir() / "access_token.txt"
    if plain.is_file():
        text = plain.read_text(encoding="utf-8").strip()
        if text:
            return text
    return None


def token_present() -> bool:
    return bool(load_access_token())


def ids_configured() -> bool:
    return bool(phone_number_id() and waba_id())


def ensure_default_config() -> dict:
    """Persist non-secret operational IDs locally if missing."""
    path = config_path()
    current = load_json_file(path) or {}
    changed = False
    if not current.get("phone_number_id"):
        current["phone_number_id"] = os.environ.get("WHATSAPP_PHONE_NUMBER_ID") or DEFAULT_PHONE_NUMBER_ID
        changed = True
    if not current.get("waba_id"):
        current["waba_id"] = os.environ.get("WHATSAPP_WABA_ID") or DEFAULT_WABA_ID
        changed = True
    if not current.get("display_phone_number"):
        current["display_phone_number"] = (
            os.environ.get("WHATSAPP_DISPLAY_PHONE_NUMBER") or DEFAULT_DISPLAY_NUMBER
        )
        changed = True
    if not current.get("graph_api_version"):
        current["graph_api_version"] = DEFAULT_GRAPH_API_VERSION
        changed = True
    if not current.get("provider"):
        current["provider"] = "META"
        changed = True
    if not current.get("app_name"):
        current["app_name"] = "LNH Mission Control"
        changed = True
    if not current.get("waba_name"):
        current["waba_name"] = "Latitud Norte"
        changed = True
    if changed:
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def whatsapp_auth_state() -> dict:
    """Backend-only readiness. Never includes access token or secrets."""
    ensure_default_config()
    has_ids = ids_configured()
    has_token = token_present()
    provider = corporate_whatsapp_provider_name()
    if provider != "META":
        status = STATUS_ERROR
        message = f"Proveedor WhatsApp no soportado: {provider}"
    elif not has_ids:
        status = STATUS_NOT_CONFIGURED
        message = BUILT_PENDING
    elif not has_token:
        status = STATUS_PENDING_AUTH
        message = (
            "Phone Number ID / WABA configurados. "
            "Pendiente WHATSAPP_ACCESS_TOKEN en .env o var/whatsapp/token.json."
        )
    else:
        status = STATUS_CONNECTED
        message = "WhatsApp Cloud API configurable (token presente en backend)."
    return {
        "provider": "META",
        "status": status,
        "message": message,
        "phone_number_id_configured": bool(phone_number_id()),
        "phone_number_id": phone_number_id(),
        "waba_id_configured": bool(waba_id()),
        "waba_id": waba_id(),
        "display_phone_number": display_phone_number(),
        "graph_api_version": graph_api_version(),
        "token_present": has_token,
        "webhook_configured": False,
        "secrets_dir": str(whatsapp_secrets_dir()),
        "platform_calls": 0,
    }


def save_provider_config(payload: dict | None = None) -> dict:
    """Persist non-secret operational config. Rejects any token fields."""
    payload = payload if isinstance(payload, dict) else {}
    forbidden = {"access_token", "token", "WHATSAPP_ACCESS_TOKEN", "app_secret", "client_secret"}
    if any(k in payload for k in forbidden):
        raise ValueError("No se aceptan secretos por este endpoint. Use archivo local / variable de entorno.")
    path = config_path()
    current = load_json_file(path) or {}
    for key in (
        "phone_number_id", "waba_id", "display_phone_number",
        "graph_api_version", "app_name", "waba_name",
    ):
        if key in payload:
            current[key] = payload.get(key) or None
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "phone_number_id": current.get("phone_number_id"),
        "waba_id": current.get("waba_id"),
        "display_phone_number": current.get("display_phone_number"),
        "graph_api_version": current.get("graph_api_version"),
        "saved": True,
    }
