"""Human Gate on the same case_id. History is never deleted."""
from __future__ import annotations

from pathlib import Path

from corporate_engine.contracts import human_decision as make_decision
from corporate_engine.cycle import run_cycle
from corporate_engine.statuses import (
    APPROVED,
    CORRECTION_REQUESTED,
    GATE_READY,
    REJECTED,
    TERMINAL_HUMAN,
)
from corporate_engine.store import dump_json, load_json, now


def decide_case(case: Path, action: str, rationale: str, *, job_id: str | None = None) -> dict:
    if not rationale or not rationale.strip():
        raise ValueError("Registre el fundamento de la decisión humana.")
    case = Path(case)
    state = load_json(case / "case.json")
    if not state.get("versions"):
        raise ValueError("No existe versión.")
    latest = state["versions"][-1]
    if action == "APROBAR" and (latest.get("status") not in GATE_READY or not latest.get("reports")):
        raise ValueError("No existe un informe profesional consolidado disponible para aprobación.")
    record = make_decision(
        case_id=state["case_id"], action=action, rationale=rationale.strip(), version=latest["version"],
    )
    decisions = case / "human_decisions"
    decisions.mkdir(exist_ok=True)
    dump_json(decisions / f"HUMAN_DECISION_RECORD_v{latest['version']:03d}.json", record)
    dump_json(case / "HUMAN_DECISION_RECORD.json", record)
    if job_id:
        dump_json(decisions / f"WEB_DECISION_{job_id}.json", record)
    state["status"] = APPROVED if action == "APROBAR" else REJECTED
    state["correction_pending"] = False
    state.setdefault("audit", []).append({
        "at": now(), "event": "HUMAN_DECISION", "decision": record["decision"], "record": record["id"],
        "engine": "corporate_engine",
    })
    dump_json(case / "case.json", state)
    return record


def correct_case(case: Path, rationale: str, runtime=None) -> dict:
    if not rationale or not rationale.strip():
        raise ValueError("Corrección humana obligatoria.")
    case = Path(case)
    state = load_json(case / "case.json")
    if not state.get("versions"):
        raise ValueError("No existe una versión profesional para corregir.")
    parent = state["versions"][-1]["version"]
    record = make_decision(
        case_id=state["case_id"], action="CORREGIR", rationale=rationale.strip(), version=parent,
    )
    decisions = case / "human_decisions"
    decisions.mkdir(exist_ok=True)
    dump_json(decisions / f"HUMAN_DECISION_RECORD_v{parent:03d}.json", record)
    dump_json(case / "HUMAN_DECISION_RECORD.json", record)
    state["status"] = CORRECTION_REQUESTED
    state["correction_pending"] = True
    state["last_correction"] = rationale.strip()
    state.setdefault("audit", []).append({
        "at": now(), "event": "HUMAN_CORRECTION_REQUESTED", "source_version": parent,
        "record": record["id"], "engine": "corporate_engine",
    })
    dump_json(case / "case.json", state)
    return run_case(case, runtime=runtime)


def run_case(case: Path, runtime=None) -> dict:
    case = Path(case)
    state = load_json(case / "case.json")
    latest = (state.get("versions") or [None])[-1]
    already = (
        not state.get("correction_pending")
        and latest
        and not latest.get("errors")
        and latest.get("status") in GATE_READY
        and bool(latest.get("reports"))
        and state.get("status") not in {CORRECTION_REQUESTED, "CORRECTION_IN_PROGRESS"}
    )
    if already:
        return latest
    if state.get("status") in TERMINAL_HUMAN:
        return latest
    return run_cycle(case, correction=state.get("last_correction") if state.get("correction_pending") else None,
                     runtime=runtime)
