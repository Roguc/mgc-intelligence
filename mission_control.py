"""View-model helpers for the local Streamlit Mission Control."""
from pathlib import Path
import json
def load_case(case: Path) -> dict:
 state=json.loads((case/"case.json").read_text(encoding="utf-8"));versions=state.get("versions",[]);return {"case_id":state["case_id"],"status":state["status"],"documents":state["documents"],"latest":versions[-1] if versions else None,"path":case}
def case_artifacts(case: Path) -> list[Path]:
 info=load_case(case);latest=info["latest"]
 if not latest:return []
 version=case/f"v{latest['version']:03d}";return [p for p in (version/"MGC-05_DEPARTMENT_REPORT.md",version/"plan.json",version/"handoffs.json",version/"contradictions.json") if p.exists()]
def human_gate_action(case: Path, decision: str, rationale: str, approve_case, correct_case):
 if decision=="CORREGIR":return correct_case(case,rationale)
 if decision not in {"APROBAR","RECHAZAR"}:raise ValueError("Decisión humana no válida.")
 return approve_case(case,"APROBADO" if decision=="APROBAR" else "RECHAZADO",rationale)
