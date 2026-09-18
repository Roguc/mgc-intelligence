"""Fase 2B-1 — Deterministic internal automations (no email/WhatsApp/Platform)."""
from __future__ import annotations

from pathlib import Path

from corporate_engine import corporate_calendar as calendar
from corporate_engine import corporate_notifications as notifs
from corporate_engine import corporate_expediente as corp
from corporate_engine import corporate_workflow as workflow
from corporate_engine import corporate_board as board
from corporate_engine.store import now


def _idem(kind: str, *parts: str) -> str:
    return f"auto:{kind}:" + ":".join(str(p) for p in parts if p)


def sync_overdue_task_notifications(corporate_root: Path) -> list[dict]:
    """TAREA_VENCIDA for overdue corporate tasks. Idempotent."""
    created = []
    for item in corp.list_expedientes(corporate_root):
        case = corp.directory(corporate_root, item["expediente_id"])
        for overdue in workflow.overdues_view(case):
            task_id = overdue.get("task_id") or overdue.get("encargos_id") or overdue.get("id")
            key = _idem("TAREA_VENCIDA", item["expediente_id"], task_id)
            notif = notifs.create_notification(corporate_root, {
                "type": "TAREA_VENCIDA",
                "title": "Tarea vencida",
                "message": f"La tarea {task_id} del expediente {item['expediente_id']} está vencida.",
                "priority": "HIGH",
                "expediente_id": item["expediente_id"],
                "task_id": task_id,
                "idempotency_key": key,
            })
            created.append(notif)
    return created


def sync_human_gate_notifications(corporate_root: Path, floor_cases: list[dict] | None = None) -> list[dict]:
    """HUMAN_GATE_PENDIENTE from floor cases requiring decision. Idempotent."""
    created = []
    for row in floor_cases or []:
        if not row.get("requires_decision"):
            continue
        case_id = row.get("case_id")
        floor_id = row.get("floor_id")
        key = _idem("HUMAN_GATE_PENDIENTE", floor_id, case_id)
        notif = notifs.create_notification(corporate_root, {
            "type": "HUMAN_GATE_PENDIENTE",
            "title": "Human Gate pendiente",
            "message": f"Expediente de piso {floor_id}/{case_id} requiere decisión humana.",
            "priority": "HIGH",
            "idempotency_key": key,
            "recipient_area": floor_id,
        })
        created.append(notif)
    return created


def sync_board_session_events(corporate_root: Path) -> list[dict]:
    """DIRECTORIO calendar events for programmed board sessions. Idempotent."""
    created = []
    for session in board.list_board_sessions(corporate_root):
        sid = session.get("board_session_id")
        estado = str(session.get("estado") or "")
        if estado in {"CERRADA", "CANCELADA"}:
            continue
        fecha = session.get("fecha") or now()
        key = _idem("DIRECTORIO", sid)
        event = calendar.create_event(corporate_root, {
            "title": f"Sesión de Directorio {sid}",
            "description": f"Tipo {session.get('tipo') or '—'} · estado {estado}",
            "event_type": "DIRECTORIO",
            "start_at": fecha,
            "end_at": fecha,
            "status": "PROGRAMADO",
            "board_session_id": sid,
            "expediente_id": (session.get("expediente_ids") or [None])[0],
            "company_scope": "LNH",
            "corporate_area": "DIRECTORIO",
            "idempotency_key": key,
            "source": "AUTOMATION",
        }, actor="SYSTEM")
        created.append(event)
        notifs.create_notification(corporate_root, {
            "type": "SESION_PROGRAMADA",
            "title": "Sesión de Directorio programada",
            "message": f"Sesión {sid} registrada en calendario corporativo.",
            "priority": "NORMAL",
            "board_session_id": sid,
            "expediente_id": event.get("expediente_id"),
            "idempotency_key": _idem("SESION_PROGRAMADA", sid),
        })
    return created


def sync_expediente_due_events(corporate_root: Path) -> list[dict]:
    """VENCIMIENTO calendar events from expediente fecha_objetivo. Idempotent."""
    created = []
    for item in corp.list_expedientes(corporate_root):
        due = item.get("fecha_objetivo")
        if not due:
            continue
        exp_id = item["expediente_id"]
        key = _idem("VENCIMIENTO", exp_id, str(due)[:10])
        event = calendar.create_event(corporate_root, {
            "title": f"Vencimiento expediente {exp_id}",
            "description": item.get("asunto") or "",
            "event_type": "VENCIMIENTO",
            "start_at": due,
            "end_at": due,
            "all_day": True,
            "status": "PROGRAMADO",
            "expediente_id": exp_id,
            "company_scope": item.get("ambito") or "LNH",
            "idempotency_key": key,
            "source": "AUTOMATION",
        }, actor="SYSTEM")
        created.append(event)
    return created


def sync_decision_notifications(corporate_root: Path) -> list[dict]:
    """DECISION_REGISTRADA from expediente decisiones already recorded. Idempotent."""
    created = []
    for item in corp.list_expedientes(corporate_root):
        case = corp.directory(corporate_root, item["expediente_id"])
        master = corp.load_expediente(case)
        for decision in master.get("decisiones") or []:
            decision_id = decision.get("decision_id") or decision.get("id")
            if not decision_id:
                continue
            key = _idem("DECISION_REGISTRADA", item["expediente_id"], decision_id)
            notif = notifs.create_notification(corporate_root, {
                "type": "DECISION_REGISTRADA",
                "title": "Decisión registrada",
                "message": (
                    f"Decisión {decision.get('decision') or decision_id} "
                    f"registrada en expediente {item['expediente_id']}."
                ),
                "priority": "NORMAL",
                "expediente_id": item["expediente_id"],
                "idempotency_key": key,
            })
            created.append(notif)
    return created


def run_deterministic_sync(
    corporate_root: Path,
    *,
    floor_cases: list[dict] | None = None,
    pull_email: bool = True,
) -> dict:
    """Run Block-1 automations + optional Gmail inbound pull. No Platform."""
    email_result = {"created": 0, "duplicates": 0, "errors": 0, "skipped": True}
    if pull_email:
        try:
            from corporate_engine import email_sync
            from corporate_engine.providers import get_email_provider
            from corporate_engine.gmail_provider import GmailProvider
            provider = get_email_provider()
            if isinstance(provider, GmailProvider) and provider.status().status == "CONNECTED":
                email_result = email_sync.pull_inbound_email(corporate_root)
            else:
                email_result = {
                    "created": 0,
                    "duplicates": 0,
                    "errors": 0,
                    "skipped": True,
                    "message": "Gmail no CONNECTED — inbound omitido",
                    "platform_calls": 0,
                }
        except Exception as error:  # noqa: BLE001 — never break local sync
            email_result = {
                "created": 0,
                "duplicates": 0,
                "errors": 1,
                "skipped": True,
                "message": str(error),
                "platform_calls": 0,
            }
    return {
        "overdue_notifications": len(sync_overdue_task_notifications(corporate_root)),
        "human_gate_notifications": len(sync_human_gate_notifications(corporate_root, floor_cases)),
        "board_events": len(sync_board_session_events(corporate_root)),
        "due_events": len(sync_expediente_due_events(corporate_root)),
        "decision_notifications": len(sync_decision_notifications(corporate_root)),
        "email_inbound": email_result,
        "synced_at": now(),
        "platform_calls": 0,
    }
