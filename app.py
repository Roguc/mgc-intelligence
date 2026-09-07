from pathlib import Path
import tempfile
import streamlit as st
from corporate.platform import build_mgc_platform
from mgc_05.backend import approve_case,correct_case,create_case,run_case
from mission_control import case_artifacts,evidence_summary,executive_status,human_gate_action,load_case,selected_agent_summary
from corporate_mission_control import render as render_corporate_mission_control
from remote_compute import runtime
ROOT=Path("outputs")/"mgc_05";platform=build_mgc_platform()
st.set_page_config(page_title="LNH Mission Control",layout="wide")
st.markdown("<style>[data-testid='stAppViewContainer']{background:#f6f3eb;color:#242620}[data-testid='stSidebar']{background:#eeece4;border-right:1px solid #ddd8cb}h1,h2,h3{color:#293b29}.stButton>button{background:#657d5c;color:white;border:0;border-radius:7px}.card{background:#fbfaf6;border:1px solid #e1ddd1;border-radius:10px;padding:16px;margin-bottom:10px}.badge{background:#e5ebdf;color:#40533d;border-radius:14px;padding:3px 9px}</style>",unsafe_allow_html=True)
st.sidebar.markdown("# ✧ LNH");st.sidebar.caption("HOLDING")
if "remote_compute_status" not in st.session_state:
 st.session_state["remote_compute_status"]=runtime().prepare(timeout_seconds=20).to_dict()
remote=st.session_state["remote_compute_status"]
if remote["ready"]:st.sidebar.success("Motor de inteligencia listo.")
elif remote["state"]=="PREPARING":st.sidebar.info("Preparando motor de inteligencia.")
else:st.sidebar.warning("Cómputo remoto no disponible. Inicie Vast.")
render_corporate_mission_control(
 st,
 mgc05_root=ROOT,
 mgc03_root=Path("outputs")/"mgc_03",
 create_mgc05_case=create_case,
 run_mgc05_case=run_case,
 approve_mgc05_case=approve_case,
 correct_mgc05_case=correct_case,
)
st.stop()
page=st.sidebar.radio("Navegación",["Inicio","Empresas","Pisos","Agentes","Misiones","Evidencia"])
st.sidebar.markdown("---");st.sidebar.caption("Vista corporativa")
def cards(units):
 for unit in units:st.markdown(f"<div class='card'><b>{unit.name}</b><br><span class='badge'>{unit.kind}</span></div>",unsafe_allow_html=True)
if page=="Inicio":
 st.title("Mission Control");st.caption("Visión ejecutiva del ecosistema corporativo")
 a,b,c=st.columns(3);a.metric("Empresas",1);b.metric("Pisos activos",1);c.metric("Agentes operacionales",3)
 st.subheader("Actividad");st.info("MGC-05 es el primer piso funcional disponible para gestionar misiones internas.")
elif page=="Empresas":
 st.title("Empresas");cards([platform.organizations.get("MGC")])
elif page=="Pisos":
 st.title("Pisos / Departamentos");cards([platform.organizations.get("MGC-05")]);st.write("Acceso operativo disponible en Misiones.")
elif page=="Agentes":
 st.title("Agentes de MGC-05")
 for agent in platform.agents.all():st.markdown(f"<div class='card'><b>{agent.agent_id}</b><br>{agent.name}<br><span class='badge'>{agent.status}</span></div>",unsafe_allow_html=True)
elif page=="Evidencia":
 st.title("Evidencia y costos");available=sorted([p for p in ROOT.iterdir() if p.is_dir()]) if ROOT.exists() else [];case_id=st.selectbox("Expediente con trazabilidad",[""]+[p.name for p in available])
 if case_id:
  summary=evidence_summary(ROOT/case_id);a,b,c,d=st.columns(4);a.metric("Fuentes",summary["sources"]);b.metric("Evidencias",summary["evidence"]);c.metric("Hallazgos",summary["findings"]);d.metric("Outputs",summary["outputs"])
  tco=summary["tco"];st.subheader("TCO ejecutivo");st.write(f"Costo real: {tco['budget']['actual']} · Forecast: {tco['budget']['forecast']} · EAC: {tco['budget']['eac']} · GPU horas: {tco['usage']['gpu_hours']} · Reprocesos: {tco['usage']['retries']}")
  with st.expander("Detalle técnico descargable"):st.download_button("Descargar ledger Data / Evidence / TCO",(ROOT/case_id/"data_evidence.json").read_bytes(),"data_evidence.json")
else:
 st.title("Misiones · MGC-05");st.caption("LNH → Miner Global Connect → MGC-05 Operaciones y PMO")
 mission=st.text_area("Misión en lenguaje natural",placeholder="Describa la misión y el resultado requerido.",height=120)
 files=st.file_uploader("Documentos de evidencia",type=["txt","md","docx","pdf","csv","xlsx"],accept_multiple_files=True)
 if st.button("Crear expediente y ejecutar Gerente de Piso",type="primary"):
  if not mission.strip():st.error("Ingrese una misión.")
  else:
   with tempfile.TemporaryDirectory() as temp:
    paths=[];failures=[]
    for uploaded in files or []:
     try:
      path=Path(temp)/uploaded.name;path.write_bytes(uploaded.getvalue());paths.append(path)
     except Exception as exc:failures.append(f"{uploaded.name}: {exc}")
    if failures:st.error("No se cargaron algunos documentos: "+"; ".join(failures))
    if paths:
     st.success(f"Documentos cargados correctamente: {len(paths)}.")
     try:
      case=create_case(mission,paths,ROOT);_,details=run_case(case);st.session_state["active_case"]=str(case);st.success(f"Expediente creado: {case.name}. Estado: {details['status']}.")
     except Exception as exc:st.error(f"No se pudo ejecutar el piso: {exc}")
    elif not failures:st.warning("No se adjuntaron documentos: no se creó expediente. Adjunte evidencia para continuar.")
 st.divider();st.header("Expediente y Human Gate")
 available=sorted([p for p in ROOT.iterdir() if p.is_dir()]) if ROOT.exists() else [];choices=[""]+[p.name for p in available];default=Path(st.session_state.get("active_case","")).name;case_id=st.selectbox("Expediente",choices,index=choices.index(default) if default in choices else 0)
 if case_id:
  case=ROOT/case_id;info=load_case(case);latest=info["latest"];summary=executive_status(info)
  st.subheader(summary["title"]);st.success("Completado: "+summary["completed"]);st.warning("Bloqueado / pendiente: "+summary["blocked"]);st.info("Próxima acción: "+summary["next"])
  a,b,c=st.columns(3);a.metric("Estado",info["status"]);b.metric("Documentos",len(info["documents"]));c.metric("Versión",latest["version"] if latest else 0)
  if latest:
   st.subheader("Plan y especialistas seleccionados")
   for item in selected_agent_summary(latest.get("routes",[])):st.write("• "+item)
   report=case/f"v{latest['version']:03d}"/"MGC-05_DEPARTMENT_REPORT.md"
   execution_status=case/f"v{latest['version']:03d}"/"MGC-05_EXECUTION_STATUS.md"
   if report.exists():st.subheader("Consolidado del Gerente de Piso");st.markdown(report.read_text(encoding="utf-8"))
   elif execution_status.exists():st.subheader("Estado de ejecución");st.markdown(execution_status.read_text(encoding="utf-8"))
   with st.expander("Detalle técnico descargable"):
    for artifact in case_artifacts(case):st.download_button(f"Descargar {artifact.name}",artifact.read_bytes(),artifact.name)
  decision=st.selectbox("Human Gate",["APROBAR","CORREGIR","RECHAZAR"]);rationale=st.text_area("Fundamento / instrucción de corrección")
  if st.button("Registrar decisión humana"):
   try:human_gate_action(case,decision,rationale,approve_case,correct_case);st.success("Decisión humana registrada.")
   except Exception as exc:st.error(str(exc))
