"""Economy and audit records. Missing Platform fields stay null."""
from __future__ import annotations

from pathlib import Path
import threading

from corporate_engine.contracts import audit_call
from corporate_engine.store import dump_json, load_json, now

ECONOMY = "inference_economy.json"
AUDIT = "audit_calls.json"
_LOCK = threading.Lock()


def record(*, case_dir: Path, case_id: str, actor: str, role: str, phase: str, agent_id=None,
           platform_agent_id=None, session_id=None, turn_id=None, model=None,
           tokens_input=None, tokens_output=None, cost=None, tools_used=None,
           start=None, end=None, status=None, error=None) -> dict:
    case_dir = Path(case_dir)
    call = audit_call(
        case_id=case_id, actor=actor, role=role, agent_id=agent_id, platform_agent_id=platform_agent_id,
        session_id=session_id, turn_id=turn_id, model=model, tokens_input=tokens_input,
        tokens_output=tokens_output, cost=cost, tools_used=tools_used, start=start or now(),
        end=end or now(), status=status, error=error, phase=phase,
    )
    with _LOCK:
        audit = load_json(case_dir / AUDIT, {"calls": []}) or {"calls": []}
        audit.setdefault("calls", []).append(call)
        dump_json(case_dir / AUDIT, audit)
        economy = load_json(case_dir / ECONOMY, {
            "calls": [], "prompt_tokens": None, "completion_tokens": None, "cost_usd": None,
        }) or {"calls": [], "prompt_tokens": None, "completion_tokens": None, "cost_usd": None}
        economy.setdefault("calls", []).append({
            "at": call["created_at"],
            "actor": actor,
            "role": role,
            "agent_id": call["agent_id"],
            "phase": phase,
            "model": model,
            "prompt_tokens": tokens_input,
            "completion_tokens": tokens_output,
            "tokens_total": call["tokens_total"],
            "cost_usd": cost,
            "platform_agent_id": platform_agent_id,
            "session_id": session_id,
            "turn_id": turn_id,
            "tools": list(tools_used or []),
            "status": status,
            "error": error,
            "missing_data": call["missing_data"],
            "start": call["start"],
            "end": call["end"],
        })
        dump_json(case_dir / ECONOMY, economy)
    return call
