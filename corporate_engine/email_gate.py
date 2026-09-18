"""Outbound Human Gate + provider send pipeline (EMAIL / WHATSAPP).

Fase 2B-2: Gmail. Fase 2B-3: Meta WhatsApp Cloud API.
Same DRAFT → PENDIENTE_APROBACION → APROBADO → QUEUED → SENT flow.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from corporate_engine import corporate_communications as communications
from corporate_engine.corporate_expediente import (
    ACTOR_TYPE_SYSTEM,
    audit_event,
    load_expediente,
    save_expediente,
    directory as expediente_directory,
)
from corporate_engine.providers import get_email_provider, get_whatsapp_provider
from corporate_engine.store import now

OUTBOUND_GATE_CHANNELS = frozenset({"EMAIL", "WHATSAPP"})

GATE_PENDING = "PENDIENTE_APROBACION"
GATE_APPROVED = "APROBADO"
GATE_REJECTED = "RECHAZADO"
GATE_CORRECT = "CORREGIR"
GATE_INVALIDATED = "APROBACION_INVALIDADA"

# Extended communication statuses for email pipeline
STATUS_DRAFT = "DRAFT"
STATUS_PENDING = "PENDIENTE_APROBACION"
STATUS_APPROVED = "APROBADO"
STATUS_QUEUED = "QUEUED"
STATUS_SENT = "SENT"
STATUS_FAILED = "FAILED"
STATUS_CANCELLED = "CANCELLED"
STATUS_REJECTED = "RECHAZADO"


def content_fingerprint(item: dict) -> str:
    """Fingerprint recipients + content + template. Any change invalidates approval."""
    payload = {
        "recipients": item.get("recipients") or [],
        "cc": item.get("cc") or [],
        "bcc": item.get("bcc") or [],
        "subject": item.get("subject") or "",
        "body": item.get("body") or "",
        "template_name": item.get("template_name") or (item.get("template") or {}).get("name"),
        "template_language": item.get("template_language") or (item.get("template") or {}).get("language"),
        "template_components": item.get("template_components") or (item.get("template") or {}).get("components"),
        "template": item.get("template"),
        "attachments": [
            {
                "name": a.get("name") or a.get("filename"),
                "hash": a.get("hash") or a.get("sha256") or a.get("content_base64", "")[:32],
            }
            for a in (item.get("attachments") or [])
            if isinstance(a, dict)
        ],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _channel_prefix(channel: str) -> str:
    return "WHATSAPP" if str(channel).upper() == "WHATSAPP" else "EMAIL"


def _save(corporate_root: Path, item: dict) -> dict:
    return communications._save(  # noqa: SLF001
        communications._comm_dir(corporate_root, item["communication_id"]), item
    )


def _audit_expediente(corporate_root: Path, item: dict, *, actor: str, accion: str, motivo: str = "") -> None:
    exp_id = item.get("expediente_id")
    if not exp_id:
        return
    case = expediente_directory(corporate_root, exp_id)
    master = load_expediente(case)
    master.setdefault("eventos", []).append(audit_event(
        expediente_id=exp_id,
        actor=actor,
        actor_type=ACTOR_TYPE_SYSTEM if actor == "SYSTEM" else "HUMAN",
        accion=accion,
        objeto_afectado=item["communication_id"],
        estado_anterior=item.get("human_gate_status"),
        estado_nuevo=item.get("status"),
        referencia_version=master.get("version_actual"),
        motivo=motivo or accion,
        payload={
            "provider": item.get("provider"),
            "external_id": item.get("external_id"),
            "human_gate_status": item.get("human_gate_status"),
        },
    ))
    # refresh stub
    stubs = master.setdefault("communications", [])
    stub = {
        "communication_id": item["communication_id"],
        "channel": item.get("channel"),
        "subject": item.get("subject"),
        "status": item.get("status"),
        "direction": item.get("direction"),
        "provider": item.get("provider"),
        "external_id": item.get("external_id"),
        "human_gate_status": item.get("human_gate_status"),
        "created_at": item.get("created_at"),
    }
    stubs[:] = [s for s in stubs if s.get("communication_id") != item["communication_id"]] + [stub]
    save_expediente(case, master)


def submit_for_approval(corporate_root: Path, communication_id: str, *, actor: str = "Presidencia LNH") -> dict:
    item = communications.load_communication(corporate_root, communication_id)
    channel = str(item.get("channel") or "").upper()
    if channel not in OUTBOUND_GATE_CHANNELS:
        raise ValueError("Human Gate de envío aplica a canales EMAIL y WHATSAPP.")
    if item.get("status") not in {STATUS_DRAFT, GATE_CORRECT, STATUS_REJECTED, GATE_INVALIDATED, STATUS_PENDING}:
        if item.get("status") == STATUS_SENT:
            raise ValueError("La comunicación ya fue enviada.")
    item["status"] = STATUS_PENDING
    item["human_gate_status"] = GATE_PENDING
    item["requires_human_gate"] = True
    item["approval_fingerprint"] = content_fingerprint(item)
    item["submitted_for_approval_at"] = now()
    item["updated_at"] = now()
    item["version"] = int(item.get("version") or 1) + 1
    _save(corporate_root, item)
    prefix = _channel_prefix(channel)
    _audit_expediente(corporate_root, item, actor=actor, accion=f"{prefix}_SUBMITTED_FOR_APPROVAL")
    return item


def human_gate_decision(
    corporate_root: Path,
    communication_id: str,
    *,
    decision: str,
    rationale: str = "",
    actor: str = "Presidencia LNH",
) -> dict:
    decision_u = str(decision or "").strip().upper()
    if decision_u not in {"APROBAR", "CORREGIR", "RECHAZAR"}:
        raise ValueError("Decisión no válida. Use APROBAR, CORREGIR o RECHAZAR.")
    item = communications.load_communication(corporate_root, communication_id)
    if item.get("status") != STATUS_PENDING and item.get("human_gate_status") != GATE_PENDING:
        raise ValueError("La comunicación no está pendiente de aprobación.")
    # Invalidate if content changed since submission
    current_fp = content_fingerprint(item)
    if item.get("approval_fingerprint") and current_fp != item.get("approval_fingerprint"):
        item["human_gate_status"] = GATE_INVALIDATED
        item["status"] = STATUS_DRAFT
        item["updated_at"] = now()
        _save(corporate_root, item)
        raise ValueError("El contenido cambió tras el envío a aprobación. Se invalidó la solicitud.")

    if decision_u == "APROBAR":
        item["status"] = STATUS_APPROVED
        item["human_gate_status"] = GATE_APPROVED
        item["approved_at"] = now()
        item["approved_by"] = actor
        item["approval_rationale"] = rationale
        item["approved_fingerprint"] = current_fp
    elif decision_u == "CORREGIR":
        item["status"] = STATUS_DRAFT
        item["human_gate_status"] = GATE_CORRECT
        item["correction_rationale"] = rationale
        item["approved_at"] = None
        item["approved_fingerprint"] = None
    else:
        item["status"] = STATUS_REJECTED
        item["human_gate_status"] = GATE_REJECTED
        item["rejection_rationale"] = rationale
        item["approved_at"] = None
        item["approved_fingerprint"] = None
    item["updated_at"] = now()
    item["version"] = int(item.get("version") or 1) + 1
    _save(corporate_root, item)
    prefix = _channel_prefix(item.get("channel") or "EMAIL")
    _audit_expediente(
        corporate_root, item, actor=actor,
        accion=f"{prefix}_HUMAN_GATE_{decision_u}",
        motivo=rationale or decision_u,
    )
    return item


def update_email_content(
    corporate_root: Path,
    communication_id: str,
    payload: dict | None = None,
    *,
    actor: str = "Presidencia LNH",
) -> dict:
    """Update recipients/subject/body/template/attachments; invalidate approval if needed."""
    payload = payload if isinstance(payload, dict) else {}
    item = communications.load_communication(corporate_root, communication_id)
    if item.get("status") == STATUS_SENT:
        raise ValueError("No se puede editar una comunicación ya enviada.")
    for key in ("subject", "body", "summary", "sender", "template_name", "template_language"):
        if key in payload:
            item[key] = payload[key]
    if "template" in payload:
        item["template"] = payload.get("template")
    for key in ("recipients", "cc", "bcc", "attachments"):
        if key in payload:
            item[key] = list(payload.get(key) or [])
    if "template_components" in payload:
        item["template_components"] = list(payload.get("template_components") or [])
    new_fp = content_fingerprint(item)
    approved_fp = item.get("approved_fingerprint")
    if item.get("human_gate_status") == GATE_APPROVED and approved_fp and new_fp != approved_fp:
        item["human_gate_status"] = GATE_INVALIDATED
        item["status"] = STATUS_DRAFT
        item["approved_at"] = None
        item["approved_fingerprint"] = None
        item["approval_invalidated_at"] = now()
        item["approval_invalidated_reason"] = "Contenido modificado tras aprobación"
    elif item.get("status") == STATUS_PENDING:
        # keep pending but fingerprint drift will fail decision
        item["approval_fingerprint"] = item.get("approval_fingerprint")  # unchanged intentional
    item["content_fingerprint"] = new_fp
    item["updated_at"] = now()
    item["updated_by"] = actor
    item["version"] = int(item.get("version") or 1) + 1
    _save(corporate_root, item)
    prefix = _channel_prefix(item.get("channel") or "EMAIL")
    _audit_expediente(corporate_root, item, actor=actor, accion=f"{prefix}_CONTENT_UPDATED")
    return item


def queue_and_send(
    corporate_root: Path,
    communication_id: str,
    *,
    provider=None,
    actor: str = "Presidencia LNH",
    force_sensitive_gate: bool = True,
) -> dict:
    """APROBADO → QUEUED → Email/WhatsApp provider → SENT (never DELIVERED without evidence)."""
    item = communications.load_communication(corporate_root, communication_id)
    channel = str(item.get("channel") or "").upper()
    if channel not in OUTBOUND_GATE_CHANNELS:
        raise ValueError("Solo canales EMAIL y WHATSAPP se envían por proveedor externo.")
    sensitive = force_sensitive_gate or item.get("requires_human_gate", True)
    if sensitive:
        if item.get("human_gate_status") != GATE_APPROVED or item.get("status") != STATUS_APPROVED:
            raise ValueError("Se requiere Human Gate APROBADO antes del envío.")
        if content_fingerprint(item) != item.get("approved_fingerprint"):
            item["human_gate_status"] = GATE_INVALIDATED
            item["status"] = STATUS_DRAFT
            _save(corporate_root, item)
            raise ValueError("Aprobación invalidada: el contenido cambió. Requiere nueva aprobación.")

    if provider is None:
        provider = get_whatsapp_provider() if channel == "WHATSAPP" else get_email_provider()
    default_provider_key = "META" if channel == "WHATSAPP" else "GOOGLE"
    item["status"] = STATUS_QUEUED
    item["queued_at"] = now()
    item["provider"] = getattr(provider, "provider_key", None) or default_provider_key
    item["updated_at"] = now()
    _save(corporate_root, item)

    try:
        result = provider.send(item)
        external_id = result.get("external_id")
        if not external_id:
            raise RuntimeError("El proveedor no devolvió external/message id. No se marca SENT.")
        item["status"] = STATUS_SENT
        item["sent_at"] = now()
        item["external_id"] = external_id
        item["thread_id"] = result.get("thread_id") or item.get("thread_id")
        item["provider_status"] = "SENT"
        item["delivery_evidence"] = bool(result.get("delivery_evidence"))
        item["read_evidence"] = bool(result.get("read_evidence"))
        # Explicitly do NOT set DELIVERED/READ without Meta/Gmail evidence
        item["provider_result"] = {
            "external_id": external_id,
            "thread_id": result.get("thread_id"),
            "wa_id": result.get("wa_id"),
            "delivery_evidence": bool(result.get("delivery_evidence")),
            "read_evidence": bool(result.get("read_evidence")),
            "raw": result.get("raw"),
        }
        item.pop("provider_error", None)
    except Exception as error:  # noqa: BLE001
        item["status"] = STATUS_FAILED
        item["provider_status"] = "ERROR"
        item["provider_error"] = str(error)
        item["failed_at"] = now()
    item["version"] = int(item.get("version") or 1) + 1
    item["updated_at"] = now()
    _save(corporate_root, item)
    prefix = _channel_prefix(channel)
    _audit_expediente(
        corporate_root, item, actor=actor,
        accion=f"{prefix}_SENT" if item["status"] == STATUS_SENT else f"{prefix}_SEND_FAILED",
        motivo=item.get("provider_error") or "",
    )
    return item
