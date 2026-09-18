"""Fase 2B providers factory. Google is current; Microsoft 365 not implemented."""
from __future__ import annotations

from corporate_engine import google_oauth as oauth
from corporate_engine.providers_base import (
    STATUS_NOT_CONFIGURED,
    CalendarProvider,
    EmailProvider,
    ProviderStatus,
    WhatsAppProvider,
)

__all__ = (
    "STATUS_NOT_CONFIGURED",
    "ProviderStatus",
    "CalendarProvider",
    "EmailProvider",
    "WhatsAppProvider",
    "get_calendar_provider",
    "get_email_provider",
    "get_whatsapp_provider",
    "providers_board",
)


def get_calendar_provider(*, client=None, calendar_id: str | None = None) -> CalendarProvider:
    name = oauth.corporate_calendar_provider_name()
    if name == "GOOGLE":
        from corporate_engine.google_calendar_provider import GoogleCalendarProvider
        if client is None:
            client = oauth.make_http_client()
        return GoogleCalendarProvider(client=client, calendar_id=calendar_id)
    return CalendarProvider()


def get_email_provider(*, client=None, account: str | None = None) -> EmailProvider:
    name = oauth.corporate_email_provider_name()
    if name == "GOOGLE":
        from corporate_engine.gmail_provider import GmailProvider
        if client is None:
            client = oauth.make_http_client()
        return GmailProvider(client=client, account=account)
    return EmailProvider()


def get_whatsapp_provider(*, client=None, phone_number_id: str | None = None) -> WhatsAppProvider:
    from corporate_engine import whatsapp_config as wa_cfg
    name = wa_cfg.corporate_whatsapp_provider_name()
    if name == "META":
        from corporate_engine.meta_whatsapp_provider import MetaWhatsAppProvider
        return MetaWhatsAppProvider(client=client, phone_number_id=phone_number_id)
    return WhatsAppProvider()


def providers_board(*, calendar_client=None, email_client=None, whatsapp_client=None) -> dict:
    from corporate_engine import whatsapp_config as wa_cfg
    calendar = get_calendar_provider(client=calendar_client)
    email = get_email_provider(client=email_client)
    whatsapp = get_whatsapp_provider(client=whatsapp_client)
    auth = oauth.google_auth_state()
    wa_auth = wa_cfg.whatsapp_auth_state()
    cal_status = calendar.status()
    mail_status = email.status()
    wa_status = whatsapp.status()
    return {
        "calendar": {
            **cal_status.__dict__,
            "configured_provider": oauth.corporate_calendar_provider_name(),
        },
        "email": {
            **mail_status.__dict__,
            "configured_provider": oauth.corporate_email_provider_name(),
            "account_identity": oauth.corporate_email_account(),
        },
        "whatsapp": {
            **wa_status.__dict__,
            "configured_provider": wa_cfg.corporate_whatsapp_provider_name(),
            "phone_number_id": wa_auth.get("phone_number_id"),
            "waba_id": wa_auth.get("waba_id"),
            "display_phone_number": wa_auth.get("display_phone_number"),
            "token_present": wa_auth.get("token_present"),
            "webhook_configured": False,
            # Never expose access_token
        },
        "google_oauth": {
            "status": auth["status"],
            "message": auth["message"],
            "scopes": auth["scopes"],
            "calendar_id_configured": auth["calendar_id_configured"],
            "account_configured": auth["account_configured"],
        },
        "whatsapp_meta": {
            "status": wa_auth["status"],
            "message": wa_auth["message"],
            "phone_number_id_configured": wa_auth["phone_number_id_configured"],
            "waba_id_configured": wa_auth["waba_id_configured"],
            "token_present": wa_auth["token_present"],
            "graph_api_version": wa_auth["graph_api_version"],
            "webhook_configured": False,
        },
        "microsoft365": {
            "status": "NOT_IMPLEMENTED",
            "message": "Microsoft 365 / Outlook cancelado para 2B-2. Arquitectura genérica conservada.",
        },
        "block": "F2B-3",
        "external_send_enabled": mail_status.status == oauth.STATUS_CONNECTED,
        "whatsapp_send_enabled": wa_status.status == wa_cfg.STATUS_CONNECTED,
        "local_core_available": True,
        "platform_calls": 0,
        "built_pending_authorization": auth["status"] in {
            oauth.STATUS_NOT_CONFIGURED, oauth.STATUS_PENDING_AUTH,
        } or wa_auth["status"] in {
            wa_cfg.STATUS_NOT_CONFIGURED, wa_cfg.STATUS_PENDING_AUTH,
        },
    }
