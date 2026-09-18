"""Meta WhatsApp Cloud API provider — implements WhatsAppProvider; no expediente logic."""
from __future__ import annotations

import re

from corporate_engine import whatsapp_config as wa_cfg
from corporate_engine.providers_base import ProviderStatus, WhatsAppProvider
from corporate_engine.whatsapp_http import WhatsAppApiError, WhatsAppHttpClient


class MetaWhatsAppProvider(WhatsAppProvider):
    """Official Meta Cloud API adapter (outbound send + inbound ingest hooks)."""

    name = "MetaWhatsAppProvider"
    provider_key = "META"

    def __init__(
        self,
        client: WhatsAppHttpClient | None = None,
        *,
        phone_number_id: str | None = None,
        waba_id: str | None = None,
    ):
        self._client = client
        self._phone_number_id = phone_number_id
        self._waba_id = waba_id

    def status(self) -> ProviderStatus:
        state = wa_cfg.whatsapp_auth_state()
        details = {
            "phone_number_id": state.get("phone_number_id"),
            "waba_id": state.get("waba_id"),
            "display_phone_number": state.get("display_phone_number"),
            "graph_api_version": state.get("graph_api_version"),
            "token_present": state.get("token_present"),
            "webhook_configured": False,
        }
        if state["status"] == wa_cfg.STATUS_CONNECTED:
            return ProviderStatus(
                name=self.name,
                status=wa_cfg.STATUS_CONNECTED,
                message="WhatsApp Cloud API listo (credencial presente).",
                provider=self.provider_key,
                details=details,
            )
        if state["status"] in {wa_cfg.STATUS_NOT_CONFIGURED, wa_cfg.STATUS_PENDING_AUTH}:
            return ProviderStatus(
                name=self.name,
                status=state["status"],
                message=state["message"],
                provider=self.provider_key,
                details=details,
            )
        return ProviderStatus(
            name=self.name,
            status=wa_cfg.STATUS_ERROR,
            message=state.get("message") or "Error de configuración WhatsApp.",
            provider=self.provider_key,
            details=details,
        )

    def resolved_phone_number_id(self) -> str:
        pid = self._phone_number_id or wa_cfg.phone_number_id()
        if not pid:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID no configurado.")
        return pid

    def _require_client(self) -> WhatsAppHttpClient:
        if self._client:
            return self._client
        token = wa_cfg.load_access_token()
        if not token:
            raise RuntimeError(
                "MetaWhatsAppProvider sin access_token. "
                "Configure WHATSAPP_ACCESS_TOKEN en .env o var/whatsapp/token.json."
            )
        return WhatsAppHttpClient(
            access_token=token,
            graph_version=wa_cfg.graph_api_version(),
        )

    def send(self, communication: dict) -> dict:
        """Send approved outbound WhatsApp message. SENT only if Meta returns message id."""
        client = self._require_client()
        phone_number_id = self.resolved_phone_number_id()
        body = build_outbound_payload(communication)
        try:
            remote = client.send_message(phone_number_id, body)
        except WhatsAppApiError as error:
            detail = ""
            if isinstance(error.payload, dict):
                err = error.payload.get("error") or {}
                detail = err.get("message") or str(error.payload)
            raise RuntimeError(f"WHATSAPP_SEND_ERROR: {detail or error}") from error

        message_id = _extract_message_id(remote)
        if not message_id:
            raise RuntimeError(
                "WHATSAPP_SEND_ERROR: Meta no devolvió message id. No se marca SENT."
            )
        contacts = remote.get("contacts") or []
        wa_id = None
        if contacts and isinstance(contacts[0], dict):
            wa_id = contacts[0].get("wa_id")
        return {
            "external_id": message_id,
            "thread_id": wa_id or communication.get("thread_id"),
            "wa_id": wa_id,
            "provider_status": "SENT",
            "delivery_evidence": False,
            "read_evidence": False,
            # Minimal auditable response — never include request Authorization
            "raw": {
                "messaging_product": remote.get("messaging_product"),
                "contacts": contacts,
                "messages": remote.get("messages"),
            },
        }

    def list_inbound(self, **kwargs) -> dict:
        """Inbound arrives via webhook; polling not used for Cloud API production."""
        raise RuntimeError(
            "WhatsApp inbound usa webhooks Meta. "
            "Arquitectura preparada; webhook de producción aún no configurado."
        )

    def fetch_message(self, message_id: str) -> dict:
        raise RuntimeError(
            "Cloud API no expone fetch genérico de mensaje por id como Gmail. "
            "Usar webhook statuses/messages."
        )

    def ingest_webhook_event(self, event: dict) -> dict:
        """Normalize a Meta webhook change for future email_sync-style ingest.

        Does not persist. Does not require production webhook to be live.
        """
        return from_webhook_message(event)


def build_outbound_payload(communication: dict) -> dict:
    """Build Cloud API /messages body from corporate communication."""
    to = _first_recipient(communication.get("recipients"))
    if not to:
        raise ValueError("recipients es obligatorio para envío WhatsApp (E.164 sin + o con +).")
    to_digits = normalize_whatsapp_to(to)

    template = communication.get("template") if isinstance(communication.get("template"), dict) else None
    template_name = (
        (template or {}).get("name")
        or communication.get("template_name")
    )
    if template_name:
        language = (
            (template or {}).get("language")
            or communication.get("template_language")
            or "es"
        )
        if isinstance(language, dict):
            language_code = language.get("code") or "es"
        else:
            language_code = str(language)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_digits,
            "type": "template",
            "template": {
                "name": str(template_name),
                "language": {"code": language_code},
            },
        }
        components = (template or {}).get("components") or communication.get("template_components")
        if components:
            payload["template"]["components"] = components
        return payload

    body_text = str(communication.get("body") or communication.get("summary") or "").strip()
    if not body_text:
        raise ValueError("body o template es obligatorio para envío WhatsApp.")
    return {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_digits,
        "type": "text",
        "text": {"preview_url": False, "body": body_text},
    }


def normalize_whatsapp_to(value: str) -> str:
    """Meta accepts digits only (country code + number). Keep digits from E.164."""
    digits = re.sub(r"\D+", "", str(value or ""))
    if not digits:
        raise ValueError("Destinatario WhatsApp inválido.")
    return digits


def from_webhook_message(event: dict) -> dict:
    """Map Meta webhook message object → corporate inbound shape (no invention)."""
    event = event if isinstance(event, dict) else {}
    msg = event.get("message") if isinstance(event.get("message"), dict) else event
    text_body = ""
    if isinstance(msg.get("text"), dict):
        text_body = msg["text"].get("body") or ""
    elif msg.get("type") == "button" and isinstance(msg.get("button"), dict):
        text_body = msg["button"].get("text") or ""
    return {
        "external_id": msg.get("id"),
        "thread_id": msg.get("from"),
        "sender": msg.get("from") or "",
        "recipients": [event.get("display_phone_number") or wa_cfg.display_phone_number() or ""],
        "subject": f"WhatsApp de {msg.get('from') or 'desconocido'}",
        "body": text_body,
        "summary": (text_body or "")[:160],
        "received_at": None,
        "provider": "META",
        "provider_status": "RECEIVED",
        "read_status": "UNREAD",
        "channel": "WHATSAPP",
        "raw_type": msg.get("type"),
        "timestamp": msg.get("timestamp"),
    }


def _first_recipient(recipients) -> str | None:
    for item in recipients or []:
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            addr = item.get("phone") or item.get("wa_id") or item.get("address") or item.get("email")
            if addr:
                return str(addr).strip()
    return None


def _extract_message_id(remote: dict) -> str | None:
    messages = remote.get("messages") if isinstance(remote, dict) else None
    if not messages:
        return None
    first = messages[0] if isinstance(messages, list) and messages else None
    if isinstance(first, dict):
        mid = first.get("id")
        return str(mid) if mid else None
    return None
