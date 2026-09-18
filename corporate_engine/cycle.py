"""Submit the LNH case to the GER on OpenAI Platform. LNH does not orchestrate specialists."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from corporate_engine.audit import record as record_audit
from corporate_engine.floor import get_floor
from corporate_engine.ingest import ingest_result
from corporate_engine.platform import (
    PlatformGateway,
    RecoveryPending,
    RECOVERY_MESSAGE,
    TERMINAL_FAIL,
    classify_platform_error,
    load_execution,
    save_execution,
    windows_user_env,
)
from corporate_engine.progress import emit as progress
from corporate_engine.publish import mark_technical, publish_version
from corporate_engine.statuses import (
    INCOMPLETE,
    PLATFORM_CONNECTION_ERROR,
    PLATFORM_EXECUTION_ERROR,
    PLATFORM_RUNNING,
    PROCESSING_RESULT,
    RECOVERY_PENDING,
    RESULT_RECEIVED,
    SUBMITTED_TO_PLATFORM,
)
from corporate_engine.store import dump_json, load_json, now, write_text


def execution_instruction(state: dict, floor, correction: str | None) -> str:
    documents = state.get("documents") or []
    doc_lines = "\n".join(f"- {item.get('original_name') or item.get('name')}" for item in documents) or "(sin documentos)"
    roster = "\n".join(
        [f"- {floor.manager_id}: {floor.manager_name}"]
        + [f"- {item.specialist_id}: {item.name}" for item in floor.specialists]
    )
    block = ""
    if correction and str(correction).strip():
        block = (
            "\nCorrección humana sobre el mismo case_id. Conserve el historial y profundice:\n"
            + str(correction).strip()
            + "\n"
        )
    return (
        f"Expediente LNH {state['case_id']}\n"
        f"Empresa {floor.company_id} · Piso {floor.floor_id}\n"
        f"Gerente {floor.manager_id}\n\n"
        f"Misión:\n{state.get('mission') or ''}\n\n"
        f"Documentos en el expediente:\n{doc_lines}\n\n"
        f"Agentes configurados en OpenAI Platform (usted decide su uso; LNH no los despacha):\n{roster}\n"
        f"{block}\n"
        "Ejecute el trabajo profesional completo en OpenAI Platform: interprete la misión, "
        "planifique, delegue, use las herramientas disponibles, revise, profundice si hace falta, "
        "resuelva contradicciones y consolide el informe profesional para el Human Gate de LNH.\n"
        "LNH no planificará ni ejecutará especialistas. Devuelva el resultado profesional consolidado.\n"
    )


class Runtime:
    gateway_factory = PlatformGateway

    def __init__(self, *, gateway=None, manager_session_fn=None):
        self.gateway = gateway or type(self).gateway_factory()
        self.manager_session = manager_session_fn or windows_user_env


def _set_status(case: Path, status: str, **fields) -> dict:
    state = load_json(case / "case.json")
    state["status"] = status
    state.update(fields)
    state.setdefault("audit", []).append({"at": now(), "event": status, "engine": "corporate_engine"})
    dump_json(case / "case.json", state)
    return state


def run_cycle(case: Path, *, correction: str | None = None, runtime: Runtime | None = None) -> dict:
    runtime = runtime or Runtime()
    case = Path(case)
    state = load_json(case / "case.json")
    floor = get_floor(state["floor_id"])
    if not floor.executable:
        raise RuntimeError(f"{floor.floor_id} no está habilitado en el motor corporativo.")
    session = runtime.gateway.reuse_or_create_session(
        "", floor.manager_platform_agent_id, floor.manager_environment, case,
    )
    if not session:
        mark_technical(case, PLATFORM_CONNECTION_ERROR, "Falta OPENAI_AGENTS_SESSION_ID u OPENAI_API_KEY.")
        raise RuntimeError(f"{floor.manager_id} no está conectado: configure {floor.manager_session_env} y OPENAI_API_KEY.")

    stored = load_execution(case)
    prior_failed = str(stored.get("turn_status") or "").lower() in TERMINAL_FAIL
    inflight = stored.get("submit_status") in {
        "SUBMITTING", "UNKNOWN", "ACKNOWLEDGED",
    } and stored.get("post_attempted") and not stored.get("allow_resend") and not prior_failed
    recovering = state.get("status") in {RECOVERY_PENDING, SUBMITTED_TO_PLATFORM, PLATFORM_RUNNING}
    new_instruction = bool(correction) and not recovering and not inflight
    if new_instruction or not stored.get("client_request_id") or prior_failed:
        request_id = uuid4().hex
        failed_turns = list(stored.get("failed_turns") or [])
        if prior_failed and stored.get("turn_id"):
            failed_turns.append({
                "turn_id": stored.get("turn_id"),
                "turn_status": stored.get("turn_status"),
                "platform_error": stored.get("platform_error") or {},
                "client_request_id": stored.get("client_request_id"),
            })
        save_execution(case, {
            **stored, "client_request_id": request_id, "session_id": session,
            "post_attempted": False, "post_acknowledged": False, "turn_id": None,
            "turn_status": None, "allow_resend": False, "failed_turns": failed_turns,
            "recovery_required": False, "submit_status": None,
        })
    else:
        request_id = stored["client_request_id"]

    prompt = execution_instruction(state, floor, correction)
    inference = case / "inference" / request_id
    inference.mkdir(parents=True, exist_ok=True)
    write_text(inference / "prompt.txt", prompt)
    dump_json(inference / "input.json", {"case_id": state["case_id"], "correction": correction})

    _set_status(case, SUBMITTED_TO_PLATFORM, availability="Misión enviada al GER en OpenAI Platform.")
    progress(case, "platform_submit", "Instrucción enviada al GER-MGC-03 en OpenAI Platform.",
             actor=floor.manager_id, phase="platform")
    try:
        _set_status(case, PLATFORM_RUNNING)
        result = runtime.gateway.run_mission(
            session=session, prompt=prompt, case_dir=case, actor=floor.manager_id,
            platform_agent_id=floor.manager_platform_agent_id, client_request_id=request_id,
        )
    except RecoveryPending as error:
        execution = load_execution(case)
        save_execution(case, {
            **execution, "allow_resend": False, "recovery_required": True,
            "submit_status": execution.get("submit_status") or "UNKNOWN",
        })
        mark_technical(case, RECOVERY_PENDING, RECOVERY_MESSAGE)
        record_audit(
            case_dir=case, case_id=state["case_id"], actor=floor.manager_id, role="manager",
            phase="execute", agent_id=floor.manager_id, platform_agent_id=floor.manager_platform_agent_id,
            session_id=session, status="recovery_pending", error=str(error), start=now(), end=now(),
        )
        return load_json(case / "case.json")
    except TimeoutError as error:
        execution = load_execution(case)
        save_execution(case, {**execution, "allow_resend": False, "recovery_required": True,
                              "submit_status": execution.get("submit_status") or "UNKNOWN"})
        mark_technical(case, RECOVERY_PENDING, RECOVERY_MESSAGE)
        record_audit(
            case_dir=case, case_id=state["case_id"], actor=floor.manager_id, role="manager",
            phase="execute", agent_id=floor.manager_id, platform_agent_id=floor.manager_platform_agent_id,
            session_id=session, status="recovery_pending", error=str(error), start=now(), end=now(),
        )
        return load_json(case / "case.json")
    except Exception as error:
        kind = classify_platform_error(error)
        status = PLATFORM_CONNECTION_ERROR if kind in {"timeout", "dns", "connection_reset"} else PLATFORM_EXECUTION_ERROR
        mark_technical(case, status, str(error))
        record_audit(
            case_dir=case, case_id=state["case_id"], actor=floor.manager_id, role="manager",
            phase="execute", agent_id=floor.manager_id, platform_agent_id=floor.manager_platform_agent_id,
            session_id=session, status="failed", error=str(error), start=now(), end=now(),
        )
        raise

    _set_status(case, RESULT_RECEIVED)
    write_text(inference / "raw_response.txt", str(result.get("assistant_output_raw") or ""))
    record_audit(
        case_dir=case, case_id=state["case_id"], actor=floor.manager_id, role="manager",
        phase="execute", agent_id=floor.manager_id,
        platform_agent_id=result.get("platform_agent_id") or floor.manager_platform_agent_id,
        session_id=result.get("session_id"), turn_id=result.get("turn_id"),
        model=result.get("model"), tokens_input=result.get("prompt_eval_count"),
        tokens_output=result.get("eval_count"), cost=result.get("cost_usd"),
        tools_used=result.get("tools_used"), start=result.get("started_at"),
        end=result.get("finished_at"), status=result.get("turn_status"),
    )
    _set_status(case, PROCESSING_RESULT)
    ingested = ingest_result(case, floor, result)
    if not ingested["valid"]:
        mark_technical(
            case, INCOMPLETE,
            "OpenAI Platform devolvió un resultado técnico incompleto. No se publica versión profesional.",
            missing=ingested.get("missing_data") or [],
        )
        return load_json(case / "case.json")
    parent = None
    versions = (load_json(case / "case.json") or {}).get("versions") or []
    if versions:
        parent = versions[-1].get("version")
    return publish_version(
        case, floor=floor, ingested=ingested, parent_version=parent, correction=correction,
    )
