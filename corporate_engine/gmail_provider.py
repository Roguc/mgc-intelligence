"""Gmail provider — implements EmailProvider; no expediente logic."""
from __future__ import annotations

import base64
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime

from corporate_engine import google_oauth as oauth
from corporate_engine.google_http import GoogleApiError, GoogleHttpClient
from corporate_engine.providers_base import EmailProvider, ProviderStatus


class GmailProvider(EmailProvider):
    """Official Gmail API adapter (send + inbound list/fetch)."""

    name = "GmailProvider"
    provider_key = "GOOGLE"

    def __init__(self, client: GoogleHttpClient | None = None, *, account: str | None = None):
        self._client = client
        self._account = account

    def status(self) -> ProviderStatus:
        state = oauth.google_auth_state()
        account = self._account or oauth.corporate_email_account()
        if state["status"] == oauth.STATUS_CONNECTED:
            return ProviderStatus(
                name=self.name,
                status=oauth.STATUS_CONNECTED,
                message="Gmail autorizado.",
                provider=self.provider_key,
                details={"account_label": account, "identity": "configured_account"},
            )
        if state["status"] in {oauth.STATUS_NOT_CONFIGURED, oauth.STATUS_PENDING_AUTH}:
            return ProviderStatus(
                name=self.name,
                status=state["status"],
                message=oauth.BUILT_PENDING,
                provider=self.provider_key,
                details={"account_label": account},
            )
        return ProviderStatus(
            name=self.name,
            status=oauth.STATUS_ERROR,
            message=state.get("message") or "Error de configuración Gmail.",
            provider=self.provider_key,
        )

    def _require_client(self) -> GoogleHttpClient:
        if self._client:
            return self._client
        raise RuntimeError(
            "GmailProvider sin cliente HTTP. "
            "Inyectar cliente OAuth o completar autorización."
        )

    def send(self, communication: dict) -> dict:
        """Send DRAFT/QUEUED communication. Returns Google message/thread ids."""
        client = self._require_client()
        raw = build_raw_message(communication, from_account=self._account or oauth.corporate_email_account())
        try:
            remote = client.gmail_send(raw)
        except GoogleApiError as error:
            raise RuntimeError(f"GMAIL_SEND_ERROR: {error}") from error
        return {
            "external_id": remote.get("id"),
            "thread_id": remote.get("threadId"),
            "label_ids": remote.get("labelIds") or [],
            "raw": remote,
            # Gmail send does not prove DELIVERED
            "delivery_evidence": False,
        }

    def list_inbound(
        self,
        *,
        query: str = "in:inbox",
        max_results: int = 25,
        page_token: str | None = None,
    ) -> dict:
        """List inbound mailbox refs (ids only); caller fetches full messages."""
        client = self._require_client()
        try:
            feed = client.gmail_list_messages(
                query=query,
                max_results=max_results,
                page_token=page_token,
            )
        except GoogleApiError as error:
            raise RuntimeError(f"GMAIL_LIST_ERROR: {error}") from error
        return {
            "items": feed.get("messages") or [],
            "next_page_token": feed.get("nextPageToken"),
            "result_size_estimate": feed.get("resultSizeEstimate"),
            "provider": self.provider_key,
        }

    def fetch_message(self, message_id: str) -> dict:
        """Fetch a known message by id and normalize to MC inbound shape."""
        client = self._require_client()
        try:
            remote = client.gmail_get_message(message_id, format="full")
        except GoogleApiError as error:
            raise RuntimeError(f"GMAIL_FETCH_ERROR: {error}") from error
        return from_gmail_message(remote)

    def resolve_account(self) -> str | None:
        account = self._account or oauth.corporate_email_account()
        if account:
            return account
        client = self._require_client()
        try:
            profile = client.gmail_get_profile()
        except GoogleApiError:
            return None
        email = (profile.get("emailAddress") or "").strip() or None
        if email:
            oauth.save_provider_config({"account": email})
        return email


def from_gmail_message(remote: dict) -> dict:
    """Map Gmail API message → corporate inbound fields. No invented content."""
    headers = _header_map(remote.get("payload") or {})
    subject = headers.get("subject") or "(Sin asunto)"
    sender = headers.get("from") or ""
    to_addrs = _split_addrs(headers.get("to") or "")
    cc_addrs = _split_addrs(headers.get("cc") or "")
    body = _extract_body(remote.get("payload") or {})
    received_at = _internal_date_iso(remote.get("internalDate")) or _header_date_iso(headers.get("date"))
    label_ids = list(remote.get("labelIds") or [])
    unread = "UNREAD" in label_ids
    return {
        "external_id": remote.get("id"),
        "thread_id": remote.get("threadId"),
        "subject": subject,
        "sender": sender,
        "recipients": to_addrs,
        "cc": cc_addrs,
        "body": body,
        "summary": (body or subject)[:160],
        "received_at": received_at,
        "label_ids": label_ids,
        "snippet": remote.get("snippet") or "",
        "provider": "GOOGLE",
        "provider_status": "RECEIVED",
        "gmail_history_id": remote.get("historyId"),
        "raw_headers": {
            "from": headers.get("from"),
            "to": headers.get("to"),
            "cc": headers.get("cc"),
            "date": headers.get("date"),
            "message_id": headers.get("message-id"),
        },
        "read_status": "UNREAD" if unread else "READ",
    }


def build_raw_message(communication: dict, *, from_account: str | None) -> str:
    subject = communication.get("subject") or "(Sin asunto)"
    body = communication.get("body") or ""
    recipients = _addr_list(communication.get("recipients"))
    cc = _addr_list(communication.get("cc"))
    bcc = _addr_list(communication.get("bcc"))
    if not recipients:
        raise ValueError("recipients es obligatorio para envío Gmail.")
    msg = MIMEMultipart()
    if from_account:
        msg["From"] = from_account
    msg["To"] = ", ".join(recipients)
    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))
    for attachment in communication.get("attachments") or []:
        if not isinstance(attachment, dict):
            continue
        content_b64 = attachment.get("content_base64")
        filename = attachment.get("name") or attachment.get("filename") or "attachment.bin"
        if not content_b64:
            continue
        from email.mime.base import MIMEBase
        from email import encoders
        part = MIMEBase("application", "octet-stream")
        part.set_payload(base64.b64decode(content_b64))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)
    return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


def _addr_list(value) -> list[str]:
    rows = []
    for item in value or []:
        if isinstance(item, str) and item.strip():
            rows.append(item.strip())
        elif isinstance(item, dict):
            addr = item.get("address") or item.get("email") or item.get("name")
            if addr:
                rows.append(str(addr).strip())
    return rows


def _header_map(payload: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for header in payload.get("headers") or []:
        name = str(header.get("name") or "").strip().lower()
        if not name:
            continue
        out[name] = str(header.get("value") or "")
    return out


def _split_addrs(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"\s*,\s*", value.strip())
    return [p for p in parts if p]


def _decode_b64url(data: str) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8", errors="replace")
    except (ValueError, UnicodeError):
        return ""


def _extract_body(payload: dict) -> str:
    """Prefer text/plain; fall back to text/html stripped lightly; else snippet empty."""
    mime = (payload.get("mimeType") or "").lower()
    body = payload.get("body") or {}
    data = body.get("data")
    if data and mime.startswith("text/plain"):
        return _decode_b64url(data)
    plain_parts: list[str] = []
    html_parts: list[str] = []
    stack = [payload]
    while stack:
        node = stack.pop()
        node_mime = (node.get("mimeType") or "").lower()
        node_body = node.get("body") or {}
        node_data = node_body.get("data")
        if node_data:
            text = _decode_b64url(node_data)
            if node_mime.startswith("text/plain"):
                plain_parts.append(text)
            elif node_mime.startswith("text/html"):
                html_parts.append(text)
        for part in node.get("parts") or []:
            stack.append(part)
    if plain_parts:
        return "\n".join(plain_parts).strip()
    if html_parts:
        # Do not invent; keep raw HTML body available as-is for MC display.
        return "\n".join(html_parts).strip()
    if data:
        return _decode_b64url(data)
    return ""


def _internal_date_iso(value) -> str | None:
    if value is None or value == "":
        return None
    try:
        ms = int(value)
        from datetime import datetime, timezone
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OSError):
        return None


def _header_date_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            from datetime import timezone
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
