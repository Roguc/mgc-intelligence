"""Execute corporate tasks via OpenAI Platform Managed Sessions.

Reuses PlatformGateway. No local cognitive engine.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
from uuid import uuid4

from corporate_engine.corporate_agents import binding_for, missing_agent_ids
from corporate_engine.corporate_areas import CORPORATE_AREAS, assert_area
from corporate_engine.corporate_expediente import (
    ACTOR_TYPE_SYSTEM,
    audit_event,
    load_expediente,
    save_expediente,
    task_record,
)
from corporate_engine.corporate_statuses import (
    DERIVADO,
    EN_ANALISIS,
    EN_CLASIFICACION,
    TASK_EN_CURSO,
    TASK_ENTREGADO,
    TASK_PENDIENTE,
    TASK_VENCIDO,
    TASK_CANCELADO,
    assert_transition,
)
from corporate_engine.corporate_workflow import unmet_prerequisites
from corporate_engine.platform import (
    PlatformGateway,
    RecoveryPending,
    RECOVERY_MESSAGE,
    classify_platform_error,
    load_execution,
    save_execution,
)
from corporate_engine.store import dump_json, now

RESULT_DIR = "results"


def _append(master: dict, **kwargs) -> None:
    master.setdefault("eventos", []).append(audit_event(
        expediente_id=master["expediente_id"],
        referencia_version=master.get("version_actual"),
        **kwargs,
    ))


def _task_map(master: dict) -> dict[str, dict]:
    return {t["task_id"]: t for t in master.get("encargos") or []}


def _antecedent_results(master: dict, task: dict) -> list[dict]:
    results = {r["result_id"]: r for r in master.get("resultados") or []}
    by_task = {r.get("task_id"): r for r in master.get("resultados") or []}
    rows = []
    for dep_id in task.get("dependencies") or []:
        item = by_task.get(dep_id)
        if item:
            rows.append({
                "task_id": dep_id,
                "result_id": item.get("result_id"),
                "agent_id": item.get("agent_id"),
                "contenido": item.get("contenido"),
                "estado": item.get("estado"),
            })
    return rows


def build_authorized_context(master: dict, task: dict) -> str:
    """Authorized structured context only — not a professional mandate rewrite."""
    docs = [
        {
            "nombre": d.get("nombre") or d.get("name"),
            "document_id": d.get("document_id"),
            "version": d.get("version"),
            "hash_sha256": d.get("hash_sha256"),
        }
        for d in (master.get("documentos") or [])
    ]
    payload = {
        "expediente_id": master["expediente_id"],
        "tipo": master.get("tipo"),
        "ambito": master.get("ambito"),
        "prioridad": master.get("prioridad"),
        "asunto": master.get("asunto"),
        "instruccion_original": master.get("instruccion_original"),
        "encargo": {
            "task_id": task["task_id"],
            "assigned_to": task.get("assigned_to"),
            "role": task.get("role"),
            "objective": task.get("objective"),
            "deliverable_type": task.get("deliverable_type"),
            "due_at": task.get("due_at") or master.get("fecha_objetivo"),
            "priority": task.get("priority") or master.get("prioridad"),
            "gate_after": task.get("gate_after"),
        },
        "documentos_autorizados": docs,
        "evidencias_disponibles": master.get("evidencias") or [],
        "fuentes_disponibles": master.get("fuentes") or [],
        "dependencias_satisfechas": _antecedent_results(master, task),
        "decisiones_condiciones": master.get("decisiones") or [],
        "instruccion_operativa": (
            "Ejecute el encargo según su mandato profesional ya configurado en OpenAI Platform. "
            "Devuelva el producto solicitado. Si el rol es clasificación, responda además un JSON "
            "estructurado con destinations[{assigned_to, role}] usando solo áreas LNH-03..LNH-10."
        ),
    }
    return (
        f"Contexto corporativo autorizado LNH (expediente {master['expediente_id']})\n"
        f"task_id={task['task_id']} assigned_to={task.get('assigned_to')}\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _extract_classification(text: str) -> dict | None:
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    destinations = data.get("destinations") or data.get("destinos") or []
    if not isinstance(destinations, list):
        return None
    return data


def _apply_classification_routing(case: Path, master: dict, recommendation: dict, *, correlation_id: str) -> dict:
    """Validate Platform classification destinations against official catalog only."""
    valid = []
    rejected = []
    for item in recommendation.get("destinations") or recommendation.get("destinos") or []:
        if not isinstance(item, dict):
            rejected.append(item)
            continue
        area = item.get("assigned_to") or item.get("area_id") or item.get("id")
        try:
            area = assert_area(area)
        except ValueError:
            rejected.append(item)
            continue
        if area not in CORPORATE_AREAS:
            rejected.append(item)
            continue
        valid.append({
            "assigned_to": area,
            "label": f"{area} {CORPORATE_AREAS[area]['name']}",
            "name": CORPORATE_AREAS[area]["name"],
            "role": item.get("role") or "derivado_clasificacion",
            "deliverable_type": item.get("deliverable_type") or "informe",
        })
    master["classification_recommendation"] = {
        "raw": recommendation,
        "valid_destinations": valid,
        "rejected": rejected,
        "recorded_at": now(),
    }
    if not valid:
        _append(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="PLATFORM_RESULT_RECEIVED",
            objeto_afectado="classification",
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo="Clasificación sin destinos válidos del catálogo oficial",
            correlation_id=correlation_id,
            payload={"rejected": rejected},
        )
        save_expediente(case, master)
        return master

    # Expand routing / create tasks for validated destinations not already assigned.
    existing = {t["assigned_to"] for t in master.get("encargos") or []}
    plan = dict(master.get("routing") or {})
    plan["destinations"] = list(plan.get("destinations") or []) + [
        d for d in valid if d["assigned_to"] not in {x.get("assigned_to") for x in plan.get("destinations") or []}
    ]
    plan["requires_classification"] = False
    plan["classification_applied"] = True
    master["routing"] = plan
    due_at = master.get("fecha_objetivo")
    for dest in valid:
        if dest["assigned_to"] in existing:
            continue
        task = task_record(
            expediente_id=master["expediente_id"],
            requested_by="LNH-03",
            assigned_to=dest["assigned_to"],
            deliverable_type=dest["deliverable_type"],
            objective=f"{dest['role']}: {master['asunto']} (derivado por clasificación LNH-03)",
            due_at=due_at,
            priority=master.get("prioridad"),
            role=dest["role"],
        )
        master["encargos"].append(task)
        existing.add(dest["assigned_to"])
        _append(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_CREATED",
            objeto_afectado=task["task_id"],
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=f"Encargo post-clasificación a {dest['label']}",
            correlation_id=correlation_id,
            payload={"assigned_to": dest["assigned_to"]},
        )
    previous = master["estado_actual"]
    if previous != DERIVADO:
        assert_transition(previous, DERIVADO)
        master["estado_actual"] = DERIVADO
    _append(
        master,
        actor="LNH Backend",
        actor_type=ACTOR_TYPE_SYSTEM,
        accion="ROUTING_ASSIGNED",
        objeto_afectado="routing",
        estado_anterior=previous,
        estado_nuevo=master["estado_actual"],
        motivo="Routing aplicado desde recomendación estructurada LNH-03 Platform",
        correlation_id=correlation_id,
        payload={"valid": valid, "rejected": rejected},
    )
    save_expediente(case, master)
    return master


def _persist_result(case: Path, master: dict, task: dict, binding, session_row: dict, platform_result: dict) -> dict:
    result_id = f"res-{uuid4().hex}"
    content = platform_result.get("assistant_output_raw") or platform_result.get("assistant_output_clean") or ""
    sources = []
    for item in platform_result.get("sources") or []:
        if isinstance(item, dict):
            sources.append(item)
        elif item:
            sources.append({"referencia": str(item)})
    result = {
        "result_id": result_id,
        "expediente_id": master["expediente_id"],
        "task_id": task["task_id"],
        "agent_id": binding.area_id,
        "platform_agent_id": binding.platform_agent_id,
        "platform_session_id": session_row.get("platform_session_id"),
        "fecha": now(),
        "version": master.get("version_actual") or "v001",
        "contenido": content,
        "fuentes_evidencias": sources,
        "limitaciones_informacion_pendiente": platform_result.get("missing_data") or [],
        "estado": "RECIBIDO",
        "turn_id": platform_result.get("turn_id"),
        "usage_cost": platform_result.get("usage") or platform_result.get("cost"),
    }
    folder = Path(case) / RESULT_DIR
    folder.mkdir(parents=True, exist_ok=True)
    dump_json(folder / f"{result_id}.json", result)
    master.setdefault("resultados", []).append(result)
    return result


def execute_corporate_task(
    case: Path,
    task_id: str,
    *,
    gateway: PlatformGateway | None = None,
    idempotency_key: str | None = None,
    actor: str = "Mission Control",
) -> dict:
    case = Path(case)
    missing = missing_agent_ids()
    if missing:
        raise RuntimeError(f"Faltan agent_id Platform para: {', '.join(missing)}")

    master = load_expediente(case)
    task = _task_map(master).get(task_id)
    if not task:
        raise FileNotFoundError("Encargo no encontrado.")

    request_id = (idempotency_key or task.get("client_request_id") or f"corp-{task_id}").strip()
    # Idempotency first: same Mission Control action must not spawn another session/report.
    for row in master.get("platform_sessions") or []:
        if row.get("task_id") == task_id and row.get("client_request_id") == request_id:
            if row.get("status") in {"completed", "COMPLETED"} and row.get("result_id"):
                return {
                    "idempotent": True,
                    "task": task,
                    "session": row,
                    "result_id": row.get("result_id"),
                }
            if row.get("status") in {"running", "RUNNING", "submitted", "starting"}:
                raise ValueError("Ya hay una ejecución Platform en curso para este encargo (idempotencia).")

    if task.get("status") in {TASK_ENTREGADO, TASK_CANCELADO}:
        raise ValueError(f"El encargo ya está en estado terminal {task['status']}.")
    if task.get("status") == TASK_VENCIDO:
        raise ValueError("El encargo está VENCIDO; no se ejecuta automáticamente.")

    blocked = unmet_prerequisites(master, task_id)
    if blocked:
        raise ValueError(f"Dependencias pendientes: {', '.join(blocked)}")

    # (request_id already computed above for idempotency)
    task["client_request_id"] = request_id

    binding = binding_for(task["assigned_to"])
    gw = gateway or PlatformGateway()
    correlation = uuid4().hex

    exec_dir = case / "platform_runs" / task_id
    exec_dir.mkdir(parents=True, exist_ok=True)

    previous_state = master["estado_actual"]
    if previous_state in {DERIVADO, EN_CLASIFICACION}:
        assert_transition(previous_state, EN_ANALISIS)
        master["estado_actual"] = EN_ANALISIS
    elif previous_state != EN_ANALISIS:
        # Allow retry while already EN_ANALISIS
        if previous_state not in {EN_ANALISIS}:
            raise ValueError(f"Estado de expediente no ejecutable: {previous_state}")

    task["status"] = TASK_EN_CURSO
    task["blocked_by"] = []
    _append(
        master,
        actor=actor,
        actor_type=ACTOR_TYPE_SYSTEM,
        accion="TASK_STARTED",
        objeto_afectado=task_id,
        estado_anterior=previous_state,
        estado_nuevo=master["estado_actual"],
        motivo=f"Inicio ejecución Platform {binding.area_id}",
        correlation_id=correlation,
        payload={"platform_agent_id": binding.platform_agent_id, "client_request_id": request_id},
    )

    session_row = {
        "platform_session_id": None,
        "agent_id": binding.area_id,
        "platform_agent_id": binding.platform_agent_id,
        "expediente_id": master["expediente_id"],
        "task_id": task_id,
        "started_at": now(),
        "completed_at": None,
        "status": "starting",
        "turn_event_references": [],
        "result_id": None,
        "usage_cost": None,
        "error": None,
        "client_request_id": request_id,
        "error_kind": None,
    }
    master.setdefault("platform_sessions", []).append(session_row)
    save_expediente(case, master)

    try:
        session = gw.reuse_or_create_session(
            "", binding.platform_agent_id, binding.environment, exec_dir,
        )
        save_execution(exec_dir, {
            **load_execution(exec_dir),
            "session_id": session,
            "client_request_id": request_id,
            "lnh_expediente_id": master["expediente_id"],
            "lnh_task_id": task_id,
            "platform_agent_id": binding.platform_agent_id,
        })
        session_row["platform_session_id"] = session
        session_row["status"] = "running"
        task["platform_session_id"] = session
        _append(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="PLATFORM_SESSION_CREATED",
            objeto_afectado=session,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo=f"Sesión Managed Agents para {binding.area_id}",
            correlation_id=correlation,
            payload={"task_id": task_id, "platform_agent_id": binding.platform_agent_id},
        )
        save_expediente(case, master)

        prompt = build_authorized_context(master, task)
        result = gw.run_mission(
            session=session,
            prompt=prompt,
            case_dir=exec_dir,
            actor=binding.area_id,
            platform_agent_id=binding.platform_agent_id,
            client_request_id=request_id,
        )
        _append(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="PLATFORM_EVENT_RECEIVED",
            objeto_afectado=result.get("turn_id") or session,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo="Turno Platform recibido",
            correlation_id=correlation,
            payload={
                "turn_id": result.get("turn_id"),
                "turn_status": result.get("turn_status"),
                "session_id": session,
            },
        )
        stored = _persist_result(case, master, task, binding, session_row, result)
        session_row["status"] = "completed"
        session_row["completed_at"] = now()
        session_row["result_id"] = stored["result_id"]
        session_row["turn_event_references"] = [
            {"turn_id": result.get("turn_id"), "execution_id": result.get("execution_id")}
        ]
        if result.get("usage") or result.get("cost"):
            session_row["usage_cost"] = result.get("usage") or result.get("cost")
        task["status"] = TASK_ENTREGADO
        task["result_id"] = stored["result_id"]
        _append(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="PLATFORM_RESULT_RECEIVED",
            objeto_afectado=stored["result_id"],
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo="Resultado corporativo persistido sin reescritura cognitiva",
            correlation_id=correlation,
            payload={"task_id": task_id, "result_id": stored["result_id"]},
        )
        _append(
            master,
            actor="LNH Backend",
            actor_type=ACTOR_TYPE_SYSTEM,
            accion="TASK_DELIVERED",
            objeto_afectado=task_id,
            estado_anterior=master["estado_actual"],
            estado_nuevo=master["estado_actual"],
            motivo="Encargo ENTREGADO",
            correlation_id=correlation,
            payload={"result_id": stored["result_id"]},
        )
        # Unblock dependents
        for other in master["encargos"]:
            if other.get("status") == "BLOQUEADO" and not unmet_prerequisites(master, other["task_id"]):
                other["status"] = TASK_PENDIENTE
                other["blocked_by"] = []
        save_expediente(case, master)

        role = (task.get("role") or "").casefold()
        if binding.area_id == "LNH-03" and "clasific" in role:
            recommendation = _extract_classification(stored["contenido"])
            if recommendation:
                master = load_expediente(case)
                _apply_classification_routing(case, master, recommendation, correlation_id=correlation)

        return {
            "idempotent": False,
            "task": _task_map(load_expediente(case))[task_id],
            "session": session_row,
            "result_id": stored["result_id"],
            "expediente_estado": load_expediente(case)["estado_actual"],
        }
    except RecoveryPending as error:
        session_row["status"] = "recovery"
        session_row["error"] = str(error) or RECOVERY_MESSAGE
        session_row["error_kind"] = "recovery"
        session_row["completed_at"] = now()
        _fail_task(master, task, session_row, correlation, error, kind="recovery")
        save_expediente(case, master)
        raise
    except Exception as error:
        kind = classify_platform_error(error)
        session_row["status"] = "failed"
        session_row["error"] = str(error)
        session_row["error_kind"] = kind
        session_row["completed_at"] = now()
        exec_state = load_execution(exec_dir)
        if exec_state.get("session_id"):
            session_row["platform_session_id"] = session_row.get("platform_session_id") or exec_state.get("session_id")
            session_row["turn_event_references"] = [{
                "turn_id": exec_state.get("turn_id"),
                "execution_id": exec_state.get("execution_id"),
            }]
        _fail_task(master, task, session_row, correlation, error, kind=kind)
        save_expediente(case, master)
        raise


def _fail_task(master, task, session_row, correlation, error, *, kind: str) -> None:
    # Keep task EN_CURSO? User: do not mark ENTREGADO. Leave EN_CURSO or set back for retry.
    # Allow controlled retry: set status PENDIENTE only if allow_resend; else keep EN_CURSO with error.
    task["last_error"] = str(error)
    task["last_error_kind"] = kind
    if kind in {"billing", "CREDIT_BALANCE_EXHAUSTED"}:
        task["status"] = TASK_PENDIENTE  # recoverable when credits restored
    _append(
        master,
        actor="LNH Backend",
        actor_type=ACTOR_TYPE_SYSTEM,
        accion="PLATFORM_EXECUTION_FAILED",
        objeto_afectado=task["task_id"],
        estado_anterior=master["estado_actual"],
        estado_nuevo=master["estado_actual"],
        motivo=f"Fallo Platform ({kind})",
        correlation_id=correlation,
        payload={
            "error": str(error),
            "error_kind": kind,
            "platform_session_id": session_row.get("platform_session_id"),
            "turn_event_references": session_row.get("turn_event_references"),
        },
    )
