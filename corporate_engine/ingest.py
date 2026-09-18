"""Ingest Platform results into the LNH case file. Does not research or invent."""
from __future__ import annotations

from pathlib import Path
import json
import re

from corporate_engine.artifacts import capture_artifacts
from corporate_engine.classify import looks_like_runtime_pollution
from corporate_engine.contracts import specialist_run as make_run
from corporate_engine.evidence import apply as apply_evidence
from corporate_engine.persist import persist_run
from corporate_engine.store import dump_json, load_json, now, write_text

AGENT_FILE = re.compile(r"^(GER-MGC-03|AGIA-MGC-00[5-8])(?:\.[A-Za-z0-9]+)?$", re.I)


def _run_from_platform(case, floor, result: dict) -> dict:
    state_case = case
    run = make_run(
        case_id=state_case,
        floor_id=floor.floor_id,
        manager_id=floor.manager_id,
        specialist_id=floor.manager_id,
        platform_agent_id=result.get("platform_agent_id") or floor.manager_platform_agent_id,
        workstream_id="platform-ger",
    )
    raw = str(result.get("assistant_output_raw") or "")
    events = result.get("tool_events") or []
    artifacts, missing = capture_artifacts(
        events, raw, case_id=run["case_id"], specialist_id=run["specialist_id"],
        run_id=run["run_id"], workstream_id=run["workstream_id"],
    )
    run.update({
        "session_id": result.get("session_id"),
        "turn_id": result.get("turn_id"),
        "execution_id": result.get("execution_id") or result.get("turn_id"),
        "model": result.get("model"),
        "assistant_output_raw": raw,
        "assistant_output_clean": raw,
        "artifacts": artifacts,
        "tool_events": [event for event in events if event.get("kind") != "assistant"],
        "tools_used": result.get("tools_used") or [],
        "usage": {
            "input_tokens": result.get("prompt_eval_count"),
            "output_tokens": result.get("eval_count"),
        },
        "cost": result.get("cost_usd"),
        "completed_at": result.get("finished_at") or now(),
        "missing_data": list(missing),
        "lineage": {
            "session_id": result.get("session_id"),
            "turn_id": result.get("turn_id"),
            "execution_id": result.get("execution_id") or result.get("turn_id"),
            "platform_agent_id": result.get("platform_agent_id"),
        },
    })
    extra_sources = []
    for item in result.get("tool_sources") or []:
        if isinstance(item, dict) and item.get("url"):
            extra_sources.append({
                "url": item.get("url"), "title": item.get("title") or "",
                "origin": item.get("origin") or "platform_tool", "provenance": "platform_tool_event",
                "source_id": item.get("url"),
            })
    apply_evidence(run)
    if extra_sources:
        seen = {str(row.get("url") or "") for row in run.get("sources") or []}
        for item in extra_sources:
            if item["url"] not in seen:
                run.setdefault("sources", []).append({
                    **item, "case_id": run["case_id"], "specialist_id": run["specialist_id"],
                    "run_id": run["run_id"],
                })
                seen.add(item["url"])
        if run.get("sources") and "sources" in (run.get("missing_data") or []):
            run["missing_data"] = [item for item in run["missing_data"] if item != "sources"]
    return run


def _specialist_runs_from_artifacts(ger_run: dict, floor) -> list[dict]:
    rows = []
    for item in ger_run.get("artifacts") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        match = AGENT_FILE.match(name)
        if not match:
            continue
        agent_id = match.group(1).upper().replace("AGIA-MGC-00", "AGIA-MGC-00")
        if agent_id == "GER-MGC-03":
            continue
        try:
            binding = floor.specialist(agent_id)
        except KeyError:
            continue
        run = make_run(
            case_id=ger_run["case_id"], floor_id=floor.floor_id, manager_id=floor.manager_id,
            specialist_id=binding.specialist_id, platform_agent_id=binding.platform_agent_id,
            workstream_id="platform-artifact",
        )
        run["assistant_output_raw"] = str(item.get("content") or "")
        run["assistant_output_clean"] = run["assistant_output_raw"]
        run["artifacts"] = [item]
        run["session_id"] = ger_run.get("session_id")
        run["turn_id"] = ger_run.get("turn_id")
        apply_evidence(run)
        rows.append(run)
    return rows


def _observed_specialists(items: list, floor) -> list[str]:
    blob = json.dumps(items or [], ensure_ascii=False)
    found = []
    for spec in floor.specialists:
        if spec.specialist_id in blob or spec.name in blob:
            found.append(spec.specialist_id)
    return found


def ingest_result(case: Path, floor, result: dict) -> dict:
    case = Path(case)
    case_id = (load_json(case / "case.json") or {}).get("case_id") or case.name
    ger = _run_from_platform(case_id, floor, result)
    persist_run(case, ger)
    specialists = _specialist_runs_from_artifacts(ger, floor)
    for run in specialists:
        persist_run(case, run)
    dump_json(case / "PLATFORM_RESULT.json", {
        "session_id": result.get("session_id"),
        "turn_id": result.get("turn_id"),
        "execution_id": result.get("execution_id") or result.get("turn_id"),
        "turn_status": result.get("turn_status"),
        "model": result.get("model"),
        "usage": ger.get("usage"),
        "cost": ger.get("cost"),
        "tools_used": ger.get("tools_used"),
        "observed_specialists": _observed_specialists(result.get("items") or [], floor),
        "tool_event_types": sorted({
            str(item.get("type") or "") for item in (result.get("items") or []) if isinstance(item, dict) and item.get("type")
        }),
        "received_at": now(),
    })
    write_text(case / "GER_OUTPUT.md", str(ger.get("assistant_output_clean") or ""))
    raw = str(ger.get("assistant_output_clean") or "")
    polluted = looks_like_runtime_pollution(raw)
    valid = (
        str(result.get("turn_status") or "").lower() in {"completed", "complete", "succeeded"}
        and bool(raw.strip())
        and not polluted
    )
    missing = list(ger.get("missing_data") or [])
    if not valid and "professional_result" not in missing:
        missing.append("professional_result")
        ger["missing_data"] = missing
        persist_run(case, ger)
    return {
        "valid": valid,
        "ger_run": ger,
        "specialist_runs": specialists,
        "runs": [ger] + specialists,
        "missing_data": missing,
        "polluted": polluted,
    }
