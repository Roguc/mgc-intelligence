"""Case presentation, capabilities and operation authorization. Lives in the engine."""
from __future__ import annotations

from pathlib import Path

from corporate_engine.archive import apply_case_json, apply_root, is_active_business
from corporate_engine.catalog import FLOORS
from corporate_engine.errors import Conflict
from corporate_engine.pack import DOCX_NAME, PDF_NAME
from corporate_engine.progress import load as load_progress
from corporate_engine.publish import CONSOLIDATION_NAME
from corporate_engine.statuses import GATE_READY, RECOVERY_PENDING, TERMINAL_HUMAN, PLATFORM_RUNNING, SUBMITTED_TO_PLATFORM
from corporate_engine.store import load_json

ACTION_CAPABILITY = {
    "EJECUTAR": "execute",
    "CORREGIR": "correct",
    "APROBAR": "approve",
    "RECHAZAR": "reject",
}


def _version_dir(case: Path, record: dict):
    number = record.get("version")
    if number is None:
        return None
    for folder in sorted(case.glob(f"v{int(number):03d}*")):
        stored = load_json(folder / "version.json", {}) or {}
        if stored.get("version") == number and stored.get("at") == record.get("at"):
            return folder
    standard = case / f"v{int(number):03d}"
    return standard if standard.is_dir() else None


def plan_view(plan: dict) -> dict:
    if not isinstance(plan, dict):
        return {}
    tasks = plan.get("tasks") or []
    selected = list(plan.get("selected_agents") or plan.get("agent_ids") or [])
    return {
        **plan,
        "agent_ids": selected or plan.get("agent_ids") or [],
        "sequence": plan.get("sequence") or [
            f"{t.get('workstream_id') or t.get('id', '')}: {t.get('objective', '')}".strip(": ") for t in tasks
        ],
        "mission": ((plan.get("interpretation") or {}).get("fields") or {}).get("objective")
        or plan.get("mission"),
    }


def capabilities(*, floor_id: str, state: dict, selected: dict, latest: dict,
                 reports: list, consolidated: str | None, busy: bool) -> dict:
    current = selected.get("version") == latest.get("version")
    closed = state.get("status") in TERMINAL_HUMAN
    unlocked = floor_id == "MGC-03" and not busy and not closed
    gate_status = latest.get("status") in GATE_READY or state.get("status") in GATE_READY
    mgc03_done = (
        floor_id == "MGC-03" and gate_status and bool(reports)
        and not state.get("correction_pending") and not selected.get("errors")
    )
    recovering = state.get("status") in {RECOVERY_PENDING, SUBMITTED_TO_PLATFORM, PLATFORM_RUNNING}
    execute = unlocked and current and not mgc03_done and not recovering
    approve = (
        unlocked and current and gate_status and bool(consolidated) and bool(reports)
        and all(r.get("content") for r in reports) and not selected.get("errors")
    )
    if state.get("archive_class") in {"failed_test", "superseded", "development"}:
        approve = False
        execute = False
    return {
        "execute": execute,
        "correct": unlocked and current and bool(latest),
        "reject": unlocked and current and bool(latest),
        "approve": approve,
    }


def case_view(case: Path, floor_id: str, version=None, *, jobs: list | None = None) -> dict:
    case = Path(case)
    apply_case_json(case / "case.json")
    state = load_json(case / "case.json") or {}
    versions = state.get("versions", [])
    latest = versions[-1] if versions else {}
    selected = latest
    if version is not None:
        selected = next((v for v in versions if str(v["version"]) == str(version)), None)
        if selected is None:
            raise FileNotFoundError("Versión no encontrada.")
    folder = _version_dir(case, selected)
    artifacts = []
    for path in sorted(case.rglob("*")):
        if path.is_file() and path.resolve().is_relative_to(case):
            artifacts.append({"path": path.relative_to(case).as_posix(), "name": path.name, "size": path.stat().st_size})

    def text(name):
        path = folder / name if folder else None
        return path.read_text(encoding="utf-8", errors="replace") if path and path.is_file() else None

    reports = []
    for report in selected.get("reports", []):
        name = report.get("report", "")
        if not name or Path(name).name != name:
            continue
        reports.append({
            **report,
            "content": text(name),
            "path": f"{folder.name}/{name}" if folder and (folder / name).is_file() else None,
        })
    traces = []
    if folder:
        traces = [{"path": p.relative_to(case).as_posix(), "data": load_json(p)} for p in sorted(folder.glob("*_LOCAL_INFERENCE_TRACE.json"))]
    progress = load_progress(case)
    evidence = load_json(case / "data_evidence.json") or {}
    if progress:
        snap = progress.get("snapshot") or {}
        evidence = {
            **evidence,
            "sources": evidence.get("sources") or [],
            "findings": evidence.get("findings") or [],
            "live": {
                "phase": progress.get("phase"),
                "actor": progress.get("actor"),
                "updated_at": progress.get("updated_at"),
                "sources_located": snap.get("sources_located"),
                "sources_accepted": snap.get("sources_accepted"),
                "sources_discarded": snap.get("sources_discarded"),
                "findings": snap.get("findings"),
                "round": snap.get("round"),
                "open_axes": snap.get("open_axes"),
            },
        }
    activity = list(progress.get("events") or []) or state.get("audit", [])
    professional_reports = []
    if folder:
        for name, fmt, label in (
            (PDF_NAME, "pdf", "Ver/Descargar informe PDF"),
            (DOCX_NAME, "docx", "Ver/Descargar informe Word"),
        ):
            if (folder / name).is_file():
                professional_reports.append({"format": fmt, "name": name, "label": label, "path": f"{folder.name}/{name}"})
    for item in selected.get("professional_reports") or []:
        if item.get("path") and not any(row.get("path") == item.get("path") for row in professional_reports):
            professional_reports.append({**item, "label": item.get("label") or (
                "Ver/Descargar informe PDF" if item.get("format") == "pdf" else "Ver/Descargar informe Word")})
    decisions = [load_json(p) for p in sorted((case / "human_decisions").glob("*.json"))]
    last_decision = load_json(case / "HUMAN_DECISION_RECORD.json")
    if last_decision and last_decision not in decisions:
        decisions.append(last_decision)
    job_rows = list(jobs or [])
    busy = any(j.get("status") == "running" for j in job_rows)
    consolidated = text(CONSOLIDATION_NAME)
    outputs = {name: value for name in (CONSOLIDATION_NAME,) if (value := text(name)) is not None}
    plan = load_json(folder / "plan.json") if folder else state.get("plan")
    if isinstance(plan, dict) and floor_id == "MGC-03":
        plan = plan_view(plan)
    caps = capabilities(
        floor_id=floor_id, state=state, selected=selected, latest=latest,
        reports=reports, consolidated=consolidated, busy=busy,
    )
    return {
        "case_id": state["case_id"],
        "floor_id": floor_id,
        "mission": state.get("mission", ""),
        "status": state["status"],
        "documents": state.get("documents", []),
        "latest": latest,
        "selected": selected,
        "versions": versions,
        "raw": state,
        "outputs": outputs,
        "plan": plan,
        "reports": reports,
        "traces": traces,
        "evidence": evidence,
        "activity": activity,
        "operational_progress": progress,
        "decisions": decisions,
        "jobs": job_rows,
        "artifacts": artifacts,
        "version_directory": folder.name if folder else None,
        "professional_reports": professional_reports,
        "capabilities": caps,
        "availability": state.get("availability") or FLOORS[floor_id]["availability"],
        "active_business": is_active_business(state),
    }


def case_index(root: Path, floor_id: str) -> list[dict]:
    if floor_id == "MGC-03":
        apply_root(root)
    rows = []
    for path in sorted(root.glob("*/case.json"), reverse=True):
        item = case_view(path.parent, floor_id, jobs=[])
        rows.append({k: item[k] for k in ("case_id", "floor_id", "mission", "status")} | {
            "documents": len(item["documents"]),
            "latest_version": item["latest"].get("version"),
            "has_report": bool(item["outputs"].get(CONSOLIDATION_NAME)),
            "requires_decision": item["capabilities"]["approve"] and item.get("active_business"),
            "busy": False,
            "archive_class": (item.get("raw") or {}).get("archive_class"),
            "active_business": item.get("active_business"),
        })
    return rows


def authorize_operation(case: Path, floor_id: str, action: str, rationale: str,
                        expected_version, *, jobs: list) -> dict:
    detail = case_view(case, floor_id, jobs=jobs)
    capability = ACTION_CAPABILITY.get(action)
    if not capability or not detail["capabilities"][capability]:
        raise ValueError("Acción no disponible para el piso o estado actual del expediente.")
    if expected_version != detail["latest"].get("version"):
        raise Conflict("El expediente cambió de versión. Actualice antes de continuar.")
    if action != "EJECUTAR" and (not isinstance(rationale, str) or not rationale.strip()):
        raise ValueError("Registre el fundamento de la decisión humana.")
    if floor_id != "MGC-03":
        raise ValueError("Este piso no ejecuta agentes en la plataforma corporativa.")
    return detail
