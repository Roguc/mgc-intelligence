"""Block 2 workflow: routing application, tasks, dependencies, deadlines.

Deterministic only. No Platform calls. No cognitive interpretation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from corporate_engine.corporate_expediente import (
    ACTOR_PRESIDENCIA,
    ACTOR_TYPE_SYSTEM,
    audit_event,
    dependency_record,
    load_expediente,
    save_expediente,
    task_record,
)
from corporate_engine.corporate_routing import plan_routing
from corporate_engine.corporate_statuses import (
    DERIVADO,
    EN_CLASIFICACION,
    REGISTRADO,
    TASK_BLOQUEADO,
    TASK_CANCELADO,
    TASK_EN_CURSO,
    TASK_ENTREGADO,
    TASK_PENDIENTE,
    TASK_VENCIDO,
    assert_transition,
)
from corporate_engine.store import now

TERMINAL_TASK = {TASK_ENTREGADO, TASK_CANCELADO, TASK_VENCIDO}


def _parse_due(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if len(text) == 10 and text[4] == "-":
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _task_map(master: dict) -> dict[str, dict]:
    return {t["task_id"]: t for t in master.get("encargos") or []}


def _deps_for(master: dict, task_id: str) -> list[dict]:
    return [d for d in (master.get("dependencias") or []) if d["dependent_task_id"] == task_id]


def unmet_prerequisites(master: dict, task_id: str) -> list[str]:
    tasks = _task_map(master)
    blocked = []
    for dep in _deps_for(master, task_id):
        pre = tasks.get(dep["prerequisite_task_id"])
        if not pre or pre.get("status") != TASK_ENTREGADO:
            blocked.append(dep["prerequisite_task_id"])
    return blocked


def _append_event(master: dict, **kwargs) -> None:
    master.setdefault("eventos", []).append(audit_event(
        expediente_id=master["expediente_id"],
        referencia_version=master.get("version_actual"),
        **kwargs,
    ))


def _default_dependencies(tipo: str, by_area: dict[str, dict]) -> list[tuple[str, str]]:
    """Structured dependency edges between area task_ids. No invented content."""
    edges: list[tuple[str, str]] = []
    if tipo == "Inversión":
        # Finance and legal can proceed in parallel after strategic draft? Spec doesn't force.
        # Keep finance/legal independent; no mandatory chain invented.
        return edges
    if tipo == "Proyecto":
        owner = next((t for a, t in by_area.items() if a != "LNH-06" and a != "LNH-03"), None)
        pmo = by_area.get("LNH-06")
        if owner and pmo:
            edges.append((owner["task_id"], pmo["task_id"]))
    if tipo == "Compra":
        fin = by_area.get("LNH-04")
        legal = by_area.get("LNH-10")
        if fin and legal:
            edges.append((fin["task_id"], legal["task_id"]))
    return edges


def apply_routing(case: Path, overrides: dict | None = None) -> dict:
    case = Path(case)
    master = load_expediente(case)
    if master.get("routing_applied"):
        return master
    if master["estado_actual"] not in {REGISTRADO, EN_CLASIFICACION}:
        raise ValueError(
            f"Routing solo aplica desde REGISTRADO/EN_CLASIFICACION; estado actual: {master['estado_actual']}"
        )

    overrides = overrides or {}
    structured = {
        "area_competente": overrides.get("area_competente") or master.get("area_competente"),
        "area_solicitante": overrides.get("area_solicitante") or master.get("area_solicitante"),
        "area_responsable": overrides.get("area_responsable") or master.get("area_responsable"),
        "funcion_propietaria": overrides.get("funcion_propietaria") or master.get("funcion_propietaria"),
        "obligacion_contractual": overrides.get("obligacion_contractual")
        if "obligacion_contractual" in overrides
        else master.get("obligacion_contractual"),
        "remitir_directorio": overrides.get("remitir_directorio")
        if "remitir_directorio" in overrides
        else master.get("remitir_directorio"),
    }
    for key, value in structured.items():
        if value is not None:
            master[key] = value

    plan = plan_routing(
        tipo=master["tipo"],
        ambito=master["ambito"],
        prioridad=master["prioridad"],
        **structured,
    )
    correlation = audit_event(
        expediente_id=master["expediente_id"],
        actor="LNH Backend",
        actor_type=ACTOR_TYPE_SYSTEM,
        accion="ROUTING_ASSIGNED",
        objeto_afectado="routing",
        estado_anterior=master["estado_actual"],
        estado_nuevo=None,
        referencia_version=master["version_actual"],
        motivo=plan["rule_id"],
        payload={"destinations": [d["assigned_to"] for d in plan["destinations"]]},
    )["correlation_id"]

    previous = master["estado_actual"]
    if plan["requires_classification"]:
        target_state = EN_CLASIFICACION
        _append_event(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="ROUTING_REQUIRES_CLASSIFICATION",
            objeto_afectado="LNH-03",
            estado_anterior=previous,
            estado_nuevo=target_state,
            motivo=plan["classification_reason"],
            correlation_id=correlation,
            payload={"classification_owner": "LNH-03"},
        )
    else:
        target_state = DERIVADO

    if previous != target_state:
        assert_transition(previous, target_state)
    master["estado_actual"] = target_state
    master["routing"] = plan
    master["routing_applied"] = True
    master["routing_applied_at"] = now()

    _append_event(
        master,
        actor="LNH Backend",
        actor_type=ACTOR_TYPE_SYSTEM,
        accion="ROUTING_ASSIGNED",
        objeto_afectado="routing",
        estado_anterior=previous,
        estado_nuevo=target_state,
        motivo=plan["rule_id"],
        correlation_id=correlation,
        payload={
            "destinations": plan["destinations"],
            "requires_classification": plan["requires_classification"],
            "directorio": plan["directorio"],
            "urgency": plan["urgency"],
        },
    )

    due_at = master.get("fecha_objetivo")
    by_area: dict[str, dict] = {}
    for dest in plan["destinations"]:
        task = task_record(
            expediente_id=master["expediente_id"],
            requested_by=master.get("creado_por") or ACTOR_PRESIDENCIA,
            assigned_to=dest["assigned_to"],
            deliverable_type=dest.get("deliverable_type") or "informe",
            objective=(
                f"{dest['role']}: {master['asunto']} "
                f"(ámbito {master['ambito']}; sin ejecución Platform en Bloque 2)"
            ),
            due_at=due_at,
            priority=master["prioridad"],
            gate_after=plan.get("next_gate"),
            role=dest.get("role"),
        )
        master["encargos"].append(task)
        by_area[dest["assigned_to"]] = task
        _append_event(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_CREATED",
            objeto_afectado=task["task_id"],
            estado_anterior=target_state,
            estado_nuevo=target_state,
            motivo=f"Encargo a {dest['label']}",
            correlation_id=correlation,
            payload={"assigned_to": dest["assigned_to"], "due_at": due_at, "priority": master["prioridad"]},
        )
        if due_at:
            _append_event(
                master,
                actor="LNH Backend",
                actor_type=ACTOR_TYPE_SYSTEM,
                accion="TASK_DUE",
                objeto_afectado=task["task_id"],
                estado_anterior=target_state,
                estado_nuevo=target_state,
                motivo=f"Fecha objetivo registrada: {due_at}",
                correlation_id=correlation,
                payload={"due_at": due_at},
            )

    for pre_id, dep_id in _default_dependencies(master["tipo"], by_area):
        add_dependency(case, pre_id, dep_id, persist=False, master=master, correlation_id=correlation)

    save_expediente(case, master)
    return master


def add_dependency(
    case: Path,
    prerequisite_task_id: str,
    dependent_task_id: str,
    *,
    persist: bool = True,
    master: dict | None = None,
    correlation_id: str | None = None,
) -> dict:
    case = Path(case)
    master = master or load_expediente(case)
    tasks = _task_map(master)
    if prerequisite_task_id not in tasks or dependent_task_id not in tasks:
        raise ValueError("Ambos encargos de la dependencia deben existir en el expediente.")
    if prerequisite_task_id == dependent_task_id:
        raise ValueError("Una dependencia no puede referenciar el mismo encargo.")
    dep = dependency_record(
        expediente_id=master["expediente_id"],
        prerequisite_task_id=prerequisite_task_id,
        dependent_task_id=dependent_task_id,
    )
    master.setdefault("dependencias", []).append(dep)
    dependent = tasks[dependent_task_id]
    if prerequisite_task_id not in dependent["dependencies"]:
        dependent["dependencies"].append(prerequisite_task_id)
    _append_event(
        master,
        actor="LNH Backend",
        actor_type=ACTOR_TYPE_SYSTEM,
        accion="DEPENDENCY_CREATED",
        objeto_afectado=dep["dependency_id"],
        estado_anterior=master["estado_actual"],
        estado_nuevo=master["estado_actual"],
        motivo=f"{prerequisite_task_id} debe completarse antes de {dependent_task_id}",
        correlation_id=correlation_id,
        payload=dep,
    )
    # If dependent already trying to run, block it
    if dependent["status"] in {TASK_PENDIENTE, TASK_EN_CURSO} and unmet_prerequisites(master, dependent_task_id):
        if dependent["status"] != TASK_BLOQUEADO:
            dependent["status"] = TASK_BLOQUEADO
            dependent["blocked_by"] = unmet_prerequisites(master, dependent_task_id)
            _append_event(
                master,
                actor="LNH Backend",
                actor_type=ACTOR_TYPE_SYSTEM,
                accion="TASK_BLOCKED",
                objeto_afectado=dependent_task_id,
                estado_anterior=master["estado_actual"],
                estado_nuevo=master["estado_actual"],
                motivo="Bloqueado por dependencia no satisfecha",
                payload={"blocked_by": dependent["blocked_by"]},
            )
    if persist:
        save_expediente(case, master)
    return dep


def update_task_status(
    case: Path,
    task_id: str,
    status: str,
    *,
    actor: str = "LNH Backend",
    result_id: str | None = None,
    motivo: str = "",
) -> dict:
    case = Path(case)
    master = load_expediente(case)
    task = _task_map(master).get(task_id)
    if not task:
        raise FileNotFoundError("Encargo no encontrado.")
    allowed = {
        TASK_PENDIENTE, TASK_EN_CURSO, TASK_BLOQUEADO, TASK_ENTREGADO, TASK_VENCIDO, TASK_CANCELADO,
    }
    if status not in allowed:
        raise ValueError(f"Estado de encargo no válido: {status}")

    previous = task["status"]
    if status == TASK_EN_CURSO:
        blocked = unmet_prerequisites(master, task_id)
        if blocked:
            task["status"] = TASK_BLOQUEADO
            task["blocked_by"] = blocked
            _append_event(
                master,
                actor=actor,
                actor_type=ACTOR_TYPE_SYSTEM,
                accion="TASK_BLOCKED",
                objeto_afectado=task_id,
                estado_anterior=master["estado_actual"],
                estado_nuevo=master["estado_actual"],
                motivo=motivo or "No puede iniciar: prerrequisitos pendientes",
                payload={"blocked_by": blocked, "attempted": TASK_EN_CURSO},
            )
            save_expediente(case, master)
            return task
        task["status"] = TASK_EN_CURSO
        task["blocked_by"] = []
        _append_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_STARTED",
            objeto_afectado=task_id,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=motivo or f"{previous} → {TASK_EN_CURSO}",
        )
    elif status == TASK_ENTREGADO:
        blocked = unmet_prerequisites(master, task_id)
        if blocked:
            raise ValueError("No se puede entregar: dependencias pendientes.")
        task["status"] = TASK_ENTREGADO
        if result_id:
            task["result_id"] = result_id
        _append_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_DELIVERED",
            objeto_afectado=task_id,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=motivo or "Entrega registrada (sin generación de informe en backend)",
            payload={"result_id": task.get("result_id")},
        )
        # Unblock dependents that only waited on this task
        for other in master["encargos"]:
            if other["status"] == TASK_BLOQUEADO and not unmet_prerequisites(master, other["task_id"]):
                other["status"] = TASK_PENDIENTE
                other["blocked_by"] = []
    elif status == TASK_BLOQUEADO:
        task["status"] = TASK_BLOQUEADO
        task["blocked_by"] = unmet_prerequisites(master, task_id)
        _append_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_BLOCKED",
            objeto_afectado=task_id,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=motivo or "Encargo bloqueado",
            payload={"blocked_by": task["blocked_by"]},
        )
    elif status == TASK_VENCIDO:
        task["status"] = TASK_VENCIDO
        task["escalamiento"] = {
            "prioridad": task.get("priority") or master.get("prioridad"),
            "at": now(),
            "rule": "TASK_OVERDUE",
        }
        _append_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_OVERDUE",
            objeto_afectado=task_id,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=motivo or "Vencido sin entrega; sin informe simulado",
            payload={"escalamiento": task["escalamiento"]},
        )
    elif status == TASK_CANCELADO:
        task["status"] = TASK_CANCELADO
        _append_event(
            master,
            actor=actor,
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="STATE_TRANSITION",
            objeto_afectado=task_id,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=motivo or "Encargo cancelado",
            payload={"task_status_from": previous, "task_status_to": TASK_CANCELADO},
        )
    else:
        task["status"] = status

    save_expediente(case, master)
    return task


def evaluate_overdues(case: Path, *, as_of: datetime | None = None) -> list[dict]:
    case = Path(case)
    master = load_expediente(case)
    moment = as_of or datetime.now(timezone.utc)
    changed = []
    for task in master.get("encargos") or []:
        if task["status"] in TERMINAL_TASK:
            continue
        due = _parse_due(task.get("due_at"))
        if not due:
            continue
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if moment >= due:
            update_task_status(
                case, task["task_id"], TASK_VENCIDO,
                motivo=f"Vencimiento determinístico en {task.get('due_at')}",
            )
            master = load_expediente(case)
            changed.append(_task_map(master)[task["task_id"]])
    master = load_expediente(case)
    master["vencimientos"] = [
        {
            "task_id": t["task_id"],
            "assigned_to": t["assigned_to"],
            "due_at": t.get("due_at"),
            "status": t["status"],
            "escalamiento": t.get("escalamiento"),
        }
        for t in master.get("encargos") or []
        if t["status"] == TASK_VENCIDO
    ]
    save_expediente(case, master)
    return changed


def routing_view(case: Path) -> dict:
    master = load_expediente(case)
    return {
        "expediente_id": master["expediente_id"],
        "estado_actual": master["estado_actual"],
        "routing_applied": bool(master.get("routing_applied")),
        "routing": master.get("routing"),
    }


def tasks_view(case: Path) -> list[dict]:
    return list(load_expediente(case).get("encargos") or [])


def dependencies_view(case: Path) -> list[dict]:
    return list(load_expediente(case).get("dependencias") or [])


def overdues_view(case: Path) -> list[dict]:
    master = load_expediente(case)
    evaluate_overdues(case)
    master = load_expediente(case)
    return list(master.get("vencimientos") or [])
