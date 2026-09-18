"""Generic provider base types shared by Google and future connectors."""
from __future__ import annotations

from dataclasses import dataclass, field

STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    status: str = STATUS_NOT_CONFIGURED
    message: str = "Proveedor no configurado."
    provider: str | None = None
    details: dict = field(default_factory=dict)


class CalendarProvider:
    """Generic calendar connector interface."""

    name = "CalendarProvider"

    def status(self) -> ProviderStatus:
        return ProviderStatus(name=self.name)

    def sync(self, *args, **kwargs):
        raise RuntimeError("CalendarProvider NOT_CONFIGURED.")

    def upsert_event(self, event: dict) -> dict:
        raise RuntimeError("CalendarProvider NOT_CONFIGURED.")

    def list_remote_events(self, **kwargs) -> dict:
        raise RuntimeError("CalendarProvider NOT_CONFIGURED.")


class EmailProvider:
    """Generic email connector interface (outbound + inbound)."""

    name = "EmailProvider"

    def status(self) -> ProviderStatus:
        return ProviderStatus(name=self.name)

    def send(self, *args, **kwargs):
        raise RuntimeError("EmailProvider NOT_CONFIGURED. No se envían correos.")

    def list_inbound(self, **kwargs) -> dict:
        """Provider → Mission Control inbound feed. Override in concrete adapters."""
        raise RuntimeError("EmailProvider NOT_CONFIGURED. No se reciben correos.")

    def fetch_message(self, message_id: str) -> dict:
        raise RuntimeError("EmailProvider NOT_CONFIGURED.")


class WhatsAppProvider:
    """Reserved for Fase 2B Bloque 3 — same MC ingest/notify/gate surface as email."""

    name = "WhatsAppProvider"

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            status=STATUS_NOT_CONFIGURED,
            message="WhatsApp se integrará en Fase 2B — Bloque 3. Misma estructura: entrante/saliente → MC → expediente/notificación/Human Gate.",
            provider="WHATSAPP",
        )

    def send(self, *args, **kwargs):
        raise RuntimeError("WhatsAppProvider NOT_CONFIGURED.")

    def list_inbound(self, **kwargs) -> dict:
        raise RuntimeError("WhatsAppProvider NOT_CONFIGURED. Inbound reservado para Bloque 3.")

    def fetch_message(self, message_id: str) -> dict:
        raise RuntimeError("WhatsAppProvider NOT_CONFIGURED.")
