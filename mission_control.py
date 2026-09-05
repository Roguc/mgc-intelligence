"""View-model helpers for the local Streamlit Mission Control."""
from pathlib import Path
import json
def load_case(case: Path) -> dict:
 state=json.loads((case/"case.json").read_text(encoding="utf-8"));versions=state.get("versions",[]);return {"case_id":state["case_id"],"status":state["status"],"documents":state["documents"],"latest":versions[-1] if versions else None,"path":case}
def case_artifacts(case: Path) -> list[Path]:
 info=load_case(case);latest=info["latest"]
 if not latest:return []
 version=case/f"v{latest['version']:03d}";return [p for p in (version/"MGC-05_DEPARTMENT_REPORT.md",version/"MGC-05_EXECUTION_STATUS.md",version/"plan.json",version/"handoffs.json",version/"contradictions.json") if p.exists()]
def human_gate_action(case: Path, decision: str, rationale: str, approve_case, correct_case):
 if decision=="CORREGIR":return correct_case(case,rationale)
 if decision not in {"APROBAR","RECHAZAR"}:raise ValueError("Decisión humana no válida.")
 return approve_case(case,"APROBADO" if decision=="APROBAR" else "RECHAZADO",rationale)

def executive_status(case_info: dict) -> dict:
 latest=case_info["latest"]
 if not latest:return {"title":"Expediente creado","completed":"Documentos registrados.","blocked":"Aún no se ha ejecutado el Gerente de Piso.","next":"Ejecutar la misión."}
 if latest.get("status")=="INFRASTRUCTURE_BLOCKED":return {"title":"Infraestructura bloqueada","completed":"El expediente y sus documentos fueron registrados.","blocked":"El motor de inferencia no está disponible; no existe informe profesional ni resultado para aprobar.","next":"Restablecer la infraestructura y ejecutar una nueva versión."}
 if latest.get("status")=="SPECIALIST_EXECUTION_BLOCKED":return {"title":"Ejecución profesional incompleta","completed":"El expediente y los resultados disponibles fueron registrados.","blocked":"Uno o más especialistas no completaron su informe; no existe consolidado profesional para aprobar.","next":"Restablecer el runtime documental y ejecutar una nueva versión."}
 return {"title":"En revisión humana","completed":"El Gerente de Piso generó plan, resultados y consolidado.","blocked":"Las decisiones externas permanecen bajo revisión humana.","next":"Revisar el consolidado y registrar APROBAR, CORREGIR o RECHAZAR."}

def selected_agent_summary(routes: list[str]) -> list[str]:
 labels={"014":"Control de Proyectos y PMO","015":"Procesos, SOP y Mejora Continua","016":"Comercio Exterior y Logística"}
 return [f"AGIA-MGC-{item}: {labels.get(item,'Especialidad registrada')} — seleccionado por las capacidades detectadas en la misión." for item in routes]

def evidence_summary(case: Path) -> dict:
 ledger=json.loads((case/"data_evidence.json").read_text(encoding="utf-8"))
 return {"sources":len(ledger["sources"]),"evidence":len(ledger["evidence"]),"findings":len(ledger["findings"]),"outputs":len(ledger["outputs"]),"tco":ledger["tco"]}
