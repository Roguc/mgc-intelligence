from pathlib import Path
import tempfile
import streamlit as st
from corporate.platform import build_mgc_platform
from mgc_05.backend import approve_case,correct_case,create_case,run_case
from mission_control import case_artifacts,human_gate_action,load_case
ROOT=Path("outputs")/"mgc_05";platform=build_mgc_platform()
st.set_page_config(page_title="LNH Mission Control",layout="wide")
st.markdown("<style>[data-testid='stAppViewContainer']{background:#f6f3eb;color:#242620}[data-testid='stSidebar']{background:#eeece4;border-right:1px solid #ddd8cb}h1,h2,h3{color:#293b29}.stButton>button{background:#657d5c;color:white;border:0;border-radius:7px}.card{background:#fbfaf6;border:1px solid #e1ddd1;border-radius:10px;padding:16px;margin-bottom:10px}.badge{background:#e5ebdf;color:#40533d;border-radius:14px;padding:3px 9px}</style>",unsafe_allow_html=True)
st.sidebar.markdown("# ✧ LNH");st.sidebar.caption("HOLDING");st.sidebar.markdown("---");st.sidebar.markdown("Inicio  \nEmpresas  \nPisos  \nAgentes  \nMisiones  \nEvidencia");st.sidebar.markdown("---");st.sidebar.caption("Vista corporativa")
st.title("Mission Control");st.caption("LNH → Miner Global Connect → MGC-05 Operaciones y PMO")
left,right=st.columns([1.1,1])
with left:
 st.subheader("Estructura corporativa")
 for unit in platform.organizations.all():st.markdown(f"<div class='card'><b>{unit.name}</b><br><span class='badge'>{unit.kind}</span></div>",unsafe_allow_html=True)
with right:
 st.subheader("Piso activo");st.markdown("<div class='card'><b>MGC-05 · Operaciones y PMO</b><br>Gerente de Piso · 3 agentes operacionales</div>",unsafe_allow_html=True);st.write("AGIA-MGC-014 · PMO");st.write("AGIA-MGC-015 · Procesos/SOP");st.write("AGIA-MGC-016 · Comercio exterior y logística")
st.divider();st.header("Nueva misión")
mission=st.text_area("Misión en lenguaje natural",placeholder="Describa la misión y el resultado requerido.",height=120);files=st.file_uploader("Documentos de evidencia",type=["txt","md","docx","pdf","csv","xlsx"],accept_multiple_files=True)
if st.button("Crear expediente y ejecutar Gerente de Piso",type="primary"):
 if not mission.strip():st.error("Ingrese una misión.")
 else:
  with tempfile.TemporaryDirectory() as temp:
   paths=[]
   for uploaded in files or []:
    path=Path(temp)/uploaded.name;path.write_bytes(uploaded.getvalue());paths.append(path)
   try:
    case=create_case(mission,paths,ROOT);_,details=run_case(case);st.session_state["active_case"]=str(case);st.success(f"Expediente creado: {case.name} · Estado: {details['status']}")
   except Exception as exc:st.error(f"No se pudo ejecutar el piso: {exc}")
st.divider();st.header("Expediente y Human Gate")
available=sorted([p for p in ROOT.iterdir() if p.is_dir()]) if ROOT.exists() else [];choices=[""]+[p.name for p in available];default=Path(st.session_state.get("active_case","")).name;case_id=st.selectbox("Expediente",choices,index=choices.index(default) if default in choices else 0)
if case_id:
 case=ROOT/case_id;info=load_case(case);latest=info["latest"];a,b,c=st.columns(3);a.metric("Estado",info["status"]);b.metric("Documentos",len(info["documents"]));c.metric("Versión",latest["version"] if latest else 0)
 if latest:
  st.subheader("Plan, agentes y progreso");st.json({"agentes":latest.get("routes",[]),"estado":latest.get("status"),"errores":latest.get("errors",[])})
  for artifact in case_artifacts(case):st.download_button(f"Descargar {artifact.name}",artifact.read_bytes(),artifact.name)
  report=case/f"v{latest['version']:03d}"/"MGC-05_DEPARTMENT_REPORT.md"
  if report.exists():st.subheader("Consolidado del Gerente de Piso");st.markdown(report.read_text(encoding="utf-8"))
 decision=st.selectbox("Human Gate",["APROBAR","CORREGIR","RECHAZAR"]);rationale=st.text_area("Fundamento / instrucción de corrección")
 if st.button("Registrar decisión humana"):
  try:human_gate_action(case,decision,rationale,approve_case,correct_case);st.success("Decisión humana registrada.")
  except Exception as exc:st.error(str(exc))
