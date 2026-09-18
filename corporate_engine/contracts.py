"""Corporate contracts. One responsibility per constructor."""
from __future__ import annotations

from uuid import uuid4

from corporate_engine.store import now


def new_id(prefix: str = "") -> str:
    return (prefix + uuid4().hex) if prefix else uuid4().hex


def stamp(payload: dict, *, case_id: str, actor: str, status: str) -> dict:
    row = dict(payload)
    row.setdefault("id", new_id())
    row["case_id"] = case_id
    row["actor"] = actor
    row["status"] = status
    row.setdefault("created_at", now())
    row.setdefault("updated_at", row["created_at"])
    row.setdefault("provenance", {})
    row.setdefault("lineage", {})
    row.setdefault("missing_data", [])
    row.setdefault("errors", [])
    return row


def mission(*, case_id: str, floor_id: str, manager_id: str, text: str, documents: list) -> dict:
    return stamp({
        "id": case_id,
        "floor_id": floor_id,
        "manager_id": manager_id,
        "mission": text,
        "documents": documents,
    }, case_id=case_id, actor="LNH", status="REGISTERED")


def workstream(*, case_id: str, floor_id: str, manager_id: str, specialist_id: str,
               platform_agent_id: str, workstream_id: str, objective: str, **fields) -> dict:
    if not all([case_id, floor_id, manager_id, specialist_id, platform_agent_id, workstream_id, objective]):
        raise ValueError("Workstream incompleto.")
    return stamp({
        "id": workstream_id,
        "workstream_id": workstream_id,
        "floor_id": floor_id,
        "manager_id": manager_id,
        "specialist_id": specialist_id,
        "platform_agent_id": platform_agent_id,
        "objective": objective,
        "scope": fields.get("scope") or "",
        "geographic_scope": fields.get("geographic_scope") or "",
        "time_horizon": fields.get("time_horizon") or "",
        "commercial_constraints": fields.get("commercial_constraints") or "",
        "acceptance_criteria": list(fields.get("acceptance_criteria") or []),
        "evidence_requirements": list(fields.get("evidence_requirements") or []),
        "restrictions": fields.get("restrictions") or "",
        "dependencies": list(fields.get("dependencies") or []),
        "expected_format": fields.get("expected_format") or "markdown profesional",
        "output_requirements": fields.get("output_requirements") or "",
    }, case_id=case_id, actor=manager_id, status="READY")


def specialist_run(*, case_id: str, floor_id: str, manager_id: str, specialist_id: str,
                   platform_agent_id: str, workstream_id: str) -> dict:
    run_id = new_id()
    return stamp({
        "id": run_id,
        "run_id": run_id,
        "floor_id": floor_id,
        "manager_id": manager_id,
        "specialist_id": specialist_id,
        "platform_agent_id": platform_agent_id,
        "workstream_id": workstream_id,
        "session_id": None,
        "turn_id": None,
        "assistant_output_raw": "",
        "assistant_output_clean": "",
        "artifacts": [],
        "tool_events": [],
        "tools_used": [],
        "sources": [],
        "findings": [],
        "usage": {},
        "cost": None,
        "started_at": now(),
        "completed_at": None,
    }, case_id=case_id, actor=specialist_id, status="RUNNING")


def artifact(*, case_id: str, specialist_id: str, run_id: str, workstream_id: str,
             name: str, content: str, path: str, origin: str, kind: str = "markdown") -> dict:
    return stamp({
        "artifact_id": new_id("art-"),
        "specialist_id": specialist_id,
        "run_id": run_id,
        "workstream_id": workstream_id,
        "name": name,
        "type": kind,
        "path": path,
        "origin": origin,
        "content": content,
        "provenance": {"origin": origin, "path": path},
        "lineage": {"run_id": run_id, "specialist_id": specialist_id, "workstream_id": workstream_id},
    }, case_id=case_id, actor=specialist_id, status="CAPTURED")


def tool_event(*, case_id: str, actor: str, run_id: str, kind: str, type_name, name, text, usage=None) -> dict:
    return stamp({
        "run_id": run_id,
        "kind": kind,
        "type": type_name,
        "name": name,
        "text": text,
        "usage": usage or {},
        "provenance": {"kind": kind, "type": type_name},
        "lineage": {"run_id": run_id},
    }, case_id=case_id, actor=actor, status="RECORDED")


def source(*, case_id: str, specialist_id: str, run_id: str, url=None, title="", origin="",
           provenance="", excerpt="", artifact_id=None, source_id=None) -> dict:
    return stamp({
        "source_id": source_id or url or new_id("src-"),
        "specialist_id": specialist_id,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "url": url,
        "title": title,
        "origin": origin,
        "excerpt": excerpt,
        "provenance": provenance or origin,
        "lineage": {"run_id": run_id, "specialist_id": specialist_id, "artifact_id": artifact_id},
    }, case_id=case_id, actor=specialist_id, status="EXTRACTED")


def finding(*, case_id: str, specialist_id: str, run_id: str, statement: str, origin="",
            provenance="", evidence_ids=None, artifact_id=None) -> dict:
    return stamp({
        "finding_id": new_id("fnd-"),
        "specialist_id": specialist_id,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "statement": statement,
        "origin": origin,
        "evidence_ids": list(evidence_ids or []),
        "provenance": provenance or origin,
        "lineage": {"run_id": run_id, "specialist_id": specialist_id, "artifact_id": artifact_id},
    }, case_id=case_id, actor=specialist_id, status="EXTRACTED")


def manager_review(*, case_id: str, manager_id: str, specialist_id: str, run_id: str,
                   decision: str, payload: dict) -> dict:
    return stamp({
        "manager_id": manager_id,
        "specialist_id": specialist_id,
        "run_id": run_id,
        "decision": decision,
        "payload": payload,
    }, case_id=case_id, actor=manager_id, status=decision)


def consolidation(*, case_id: str, manager_id: str, payload: dict) -> dict:
    return stamp({
        "manager_id": manager_id,
        "payload": payload,
        "decision": payload.get("decision"),
        "rationale": payload.get("rationale"),
    }, case_id=case_id, actor=manager_id, status=str(payload.get("decision") or "ESCALATE"))


def human_decision(*, case_id: str, action: str, rationale: str, version: int) -> dict:
    return stamp({
        "action": action,
        "decision": "APROBADO" if action == "APROBAR" else ("RECHAZADO" if action == "RECHAZAR" else "CORREGIR"),
        "rationale": rationale,
        "version": version,
    }, case_id=case_id, actor="LNH", status=action)


def audit_call(*, case_id: str, actor: str, role: str, agent_id, platform_agent_id, session_id,
               turn_id, model, tokens_input, tokens_output, cost, tools_used, start, end,
               status, error=None, phase: str) -> dict:
    missing = []
    if tokens_input is None:
        missing.append("tokens_input")
    if tokens_output is None:
        missing.append("tokens_output")
    if cost is None:
        missing.append("cost")
    if model is None:
        missing.append("model")
    total = None
    if tokens_input is not None and tokens_output is not None:
        total = int(tokens_input) + int(tokens_output)
    elif tokens_input is None or tokens_output is None:
        missing.append("tokens_total")
    return stamp({
        "role": role,
        "agent_id": agent_id or actor,
        "platform_agent_id": platform_agent_id,
        "session_id": session_id,
        "turn_id": turn_id,
        "model": model,
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "tokens_total": total,
        "cost": cost,
        "tools_used": list(tools_used or []),
        "start": start,
        "end": end,
        "error": error,
        "phase": phase,
        "missing_data": missing,
    }, case_id=case_id, actor=actor, status=status or "unknown")


def case_version(*, case_id: str, version: int, parent_version, reports, errors, status: str, **fields) -> dict:
    return stamp({
        "id": f"{case_id}:v{version:03d}",
        "version": version,
        "parent_version": parent_version,
        "reports": reports,
        "errors": errors,
        "at": now(),
        **fields,
    }, case_id=case_id, actor="GER-MGC-03", status=status)
