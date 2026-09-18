from __future__ import annotations

from pathlib import Path

from corporate_engine.store import dump_json, write_text


def persist_run(case_dir: Path, run: dict) -> Path:
    run_id = str(run.get("run_id") or "")
    specialist = str(run.get("specialist_id") or "SPECIALIST")
    if not run_id:
        raise ValueError("SpecialistRun sin run_id.")
    folder = Path(case_dir) / "runs" / specialist / run_id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "SPECIALIST_RUN.json"
    dump_json(target, run)
    clean = str(run.get("assistant_output_clean") or "")
    if clean.strip():
        write_text(folder / "assistant.md", clean)
    tools = [event for event in (run.get("tool_events") or []) if event.get("kind") != "assistant"]
    if tools:
        dump_json(folder / "tool_events.json", tools)
    for item in run.get("artifacts") or []:
        if not isinstance(item, dict) or not item.get("content"):
            continue
        name = Path(str(item.get("name") or "deliverable.md")).name
        (folder / "artifacts").mkdir(exist_ok=True)
        write_text(folder / "artifacts" / name, str(item["content"]))
    return target
