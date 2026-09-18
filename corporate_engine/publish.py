"""Publish a professional version only from a valid Platform result."""
from __future__ import annotations

from pathlib import Path

from corporate_engine.pack import DOCX_NAME, PDF_NAME, write_professional_pack
from corporate_engine.contracts import case_version
from corporate_engine.statuses import INCOMPLETE, READY_FOR_HUMAN_GATE
from corporate_engine.store import dump_json, load_json, now, write_text

CONSOLIDATION_NAME = "MGC-03_CONSOLIDATION.md"


def published_body(run: dict) -> str:
    for item in run.get("artifacts") or []:
        if isinstance(item, dict) and str(item.get("content") or "").strip():
            return str(item.get("content") or "")
    return str(run.get("assistant_output_clean") or run.get("assistant_output_raw") or "")


def mark_technical(case: Path, status: str, message: str, *, missing=None) -> dict:
    case = Path(case)
    state = load_json(case / "case.json")
    state["status"] = status
    state["availability"] = message
    state["missing_data"] = list(missing or [])
    state.setdefault("audit", []).append({"at": now(), "event": status, "message": message, "engine": "corporate_engine"})
    dump_json(case / "case.json", state)
    dump_json(case / "TECHNICAL_STATUS.json", {
        "status": status, "message": message, "missing_data": list(missing or []), "at": now(),
    })
    return state


def publish_version(case: Path, *, floor, ingested=None, runs=None, errors=None,
                    consolidation=None, proposal=None, parent_version=None, correction=None, gaps=None,
                    workstreams=None) -> dict:
    case = Path(case)
    state = load_json(case / "case.json")
    if ingested:
        runs = list(ingested.get("runs") or [])
        ger = ingested.get("ger_run") or (runs[0] if runs else {})
        if not ingested.get("valid"):
            return mark_technical(
                case, INCOMPLETE,
                "Resultado de Platform incompleto. No se publica versión profesional.",
                missing=ingested.get("missing_data") or [],
            )
    else:
        runs = list(runs or [])
        ger = next((item for item in runs if item.get("specialist_id") == floor.manager_id), runs[0] if runs else {})
    versions = list(state.get("versions") or [])
    n = len(versions) + 1
    folder = case / f"v{n:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    reports = []
    sources = []
    findings = []
    reports_by_agent = {}
    for run in runs:
        agent = run.get("specialist_id") or floor.manager_id
        name = f"{agent}.md"
        text = published_body(run)
        if not str(text).strip():
            continue
        write_text(folder / name, text)
        reports_by_agent[agent] = text
        reports.append({
            "agent": agent,
            "report": name,
            "run_id": run.get("run_id"),
            "evidence": [item.get("source_id") or item.get("url") for item in (run.get("sources") or []) if isinstance(item, dict)],
            "handoff": "Resultado recuperado desde OpenAI Platform.",
        })
        sources.extend(run.get("sources") or [])
        findings.extend(run.get("findings") or [])
    error_rows = []
    for item in errors or []:
        error_rows.append({
            "agent": item.get("agent_id") or item.get("agent"),
            "error": item.get("error"),
            "at": item.get("at") or now(),
            "run_id": item.get("run_id"),
        })
    if not reports:
        return mark_technical(case, INCOMPLETE, "Platform no entregó texto profesional. No se publica versión.")
    payload = {}
    if isinstance(consolidation, dict):
        payload = consolidation.get("payload") if "payload" in consolidation else consolidation
    summary = published_body(ger) if ger else next(iter(reports_by_agent.values()))
    write_text(folder / CONSOLIDATION_NAME, summary if str(summary).strip() else "# Consolidación\n\nSin texto.\n")
    write_text(case / CONSOLIDATION_NAME, summary if str(summary).strip() else "# Consolidación\n\nSin texto.\n")
    pack = {
        "sources": sources,
        "findings": findings,
        "gaps": list(gaps or []) + list((payload or {}).get("limitations") or []),
        "contradictions": (payload or {}).get("contradictions") or [],
        "conclusions": findings,
        "selected_agents": [run.get("specialist_id") for run in runs if run.get("specialist_id")],
        "sufficiency": (payload or {}).get("rationale") or "Resultado de OpenAI Platform listo para Human Gate.",
        "next_steps": ["Human Gate: APROBAR / CORREGIR / RECHAZAR."],
        "reports_by_agent": reports_by_agent,
        "not_demonstrated": [],
    }
    write_professional_pack(folder, state.get("mission") or "", pack)
    evidence = {
        "case_id": state["case_id"],
        "sources": sources,
        "findings": findings,
        "evidence": sources,
        "by_agent": {
            run.get("specialist_id"): {
                "run_id": run.get("run_id"),
                "sources": run.get("sources") or [],
                "findings": run.get("findings") or [],
                "errors": run.get("errors") or [],
                "usage": run.get("usage") or {},
            }
            for run in runs
        },
        "errors": error_rows,
        "missing_data": list((ingested or {}).get("missing_data") or []),
    }
    dump_json(case / "data_evidence.json", evidence)
    dump_json(folder / "data_evidence.json", evidence)
    plan = {
        "selected_agents": pack["selected_agents"],
        "agent_ids": pack["selected_agents"],
        "tasks": list(workstreams or []),
        "interpretation": (proposal or {}).get("understanding") if isinstance(proposal, dict) else {},
        "mission": state.get("mission"),
        "origin": "openai-platform",
    }
    dump_json(folder / "plan.json", plan)
    version = case_version(
        case_id=state["case_id"], version=n, parent_version=parent_version,
        reports=reports, errors=error_rows, status=READY_FOR_HUMAN_GATE,
        routes=plan["selected_agents"], correction=correction, handoffs=[],
        contradictions=pack.get("contradictions") or [],
        human_decisions=gaps or [], gaps=pack.get("gaps") or [], findings=findings,
        selected_agents=plan["selected_agents"],
        professional_reports=[
            {"format": "pdf", "name": PDF_NAME, "path": f"{folder.name}/{PDF_NAME}"},
            {"format": "docx", "name": DOCX_NAME, "path": f"{folder.name}/{DOCX_NAME}"},
        ] if (folder / PDF_NAME).is_file() else [],
        engine="corporate_engine",
        execution_id=(ger or {}).get("execution_id") or (ger or {}).get("turn_id"),
        session_id=(ger or {}).get("session_id"),
    )
    dump_json(folder / "version.json", version)
    audit = list(state.get("audit") or [])
    audit.append({"at": now(), "event": "VERSION_CREATED", "version": n, "engine": "corporate_engine"})
    state.update({
        "versions": versions + [version],
        "status": READY_FOR_HUMAN_GATE,
        "plan": plan,
        "availability": "Resultado de OpenAI Platform listo para Human Gate.",
        "audit": audit,
        "correction_pending": False,
        "engine": "corporate_engine",
    })
    dump_json(case / "case.json", state)
    return version
