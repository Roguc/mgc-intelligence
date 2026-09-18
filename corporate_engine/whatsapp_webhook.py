"""WhatsApp webhook architecture stub (Fase 2B-3).

Production webhook is NOT configured yet. This module defines the contract so
inbound statuses/messages can be wired later without rebuilding MetaWhatsAppProvider.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from corporate_engine.meta_whatsapp_provider import from_webhook_message


def verify_webhook_challenge(query: dict) -> str | None:
    """Meta GET verification. Returns challenge string if token matches.

    Requires WHATSAPP_WEBHOOK_VERIFY_TOKEN in env. Returns None if not configured
    or verification fails — production endpoint should not be exposed until set.
    """
    mode = (query.get("hub.mode") or query.get("hub_mode") or [None])
    token = (query.get("hub.verify_token") or query.get("hub_verify_token") or [None])
    challenge = (query.get("hub.challenge") or query.get("hub_challenge") or [None])
    if isinstance(mode, list):
        mode = mode[0]
    if isinstance(token, list):
        token = token[0]
    if isinstance(challenge, list):
        challenge = challenge[0]
    expected = (os.environ.get("WHATSAPP_WEBHOOK_VERIFY_TOKEN") or "").strip()
    if not expected:
        return None
    if mode == "subscribe" and token == expected and challenge is not None:
        return str(challenge)
    return None


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Optional X-Hub-Signature-256 check when WHATSAPP_APP_SECRET is configured."""
    secret = (os.environ.get("WHATSAPP_APP_SECRET") or "").strip()
    if not secret:
        # Not configured yet — production must enable before accepting live traffic.
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.split("=", 1)[1]
    return hmac.compare_digest(digest, provided)


def parse_webhook_payload(payload: dict | None) -> dict:
    """Extract inbound messages and status updates without persisting."""
    payload = payload if isinstance(payload, dict) else {}
    messages: list[dict] = []
    statuses: list[dict] = []
    for entry in payload.get("entry") or []:
        for change in (entry.get("changes") or []):
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict):
                continue
            meta = {
                "display_phone_number": (value.get("metadata") or {}).get("display_phone_number"),
                "phone_number_id": (value.get("metadata") or {}).get("phone_number_id"),
            }
            for msg in value.get("messages") or []:
                if isinstance(msg, dict):
                    messages.append(from_webhook_message({**meta, "message": msg}))
            for status in value.get("statuses") or []:
                if isinstance(status, dict):
                    statuses.append({
                        "external_id": status.get("id"),
                        "status": str(status.get("status") or "").upper(),
                        "timestamp": status.get("timestamp"),
                        "recipient_id": status.get("recipient_id"),
                        "conversation": status.get("conversation"),
                        "errors": status.get("errors"),
                        # Evidence flags — only true when Meta reports them
                        "delivery_evidence": str(status.get("status") or "").lower() == "delivered",
                        "read_evidence": str(status.get("status") or "").lower() == "read",
                    })
    return {
        "messages": messages,
        "statuses": statuses,
        "object": payload.get("object"),
        "production_enabled": False,
        "platform_calls": 0,
    }


def apply_status_evidence(communication: dict, status_event: dict) -> dict:
    """Update delivery/read evidence from Meta status webhook. No invented states."""
    item = dict(communication)
    status = str(status_event.get("status") or "").upper()
    if status == "DELIVERED" and status_event.get("delivery_evidence"):
        item["delivery_evidence"] = True
        item["provider_status"] = "DELIVERED"
        # Only set DELIVERED when Meta evidence exists
        item["status"] = "DELIVERED"
    elif status == "READ" and status_event.get("read_evidence"):
        item["read_evidence"] = True
        item["provider_status"] = "READ"
        # Do not invent READ as communication status unless product decides later
    elif status == "FAILED":
        item["provider_status"] = "ERROR"
        item["provider_error"] = str(status_event.get("errors") or "Meta status FAILED")
    return item
