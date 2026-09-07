from pathlib import Path
import tempfile
import streamlit as st
from corporate.platform import build_mgc_platform
from mgc_05.backend import approve_case,correct_case,create_case,run_case
from mission_control import case_artifacts,evidence_summary,executive_status,human_gate_action,load_case,selected_agent_summary
from corporate_mission_control import render as render_corporate_mission_control
from remote_compute import runtime
ROOT=Path("outputs")/"mgc_05";platform=build_mgc_platform()
st.set_page_config(page_title="LNH Mission Control", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
:root{--ink:#17232d;--muted:#71808a;--navy:#102531;--blue:#0e5792;--sage:#557d61;--paper:#f4f6f7;--panel:#fff;--line:#dbe2e6;--amber:#9b6b16;--danger:#b64642}#MainMenu,footer,header{visibility:hidden}
[data-testid='stAppViewContainer']{background:var(--paper);color:var(--ink)}.block-container{max-width:1660px;padding:1.4rem 2.4rem 3.4rem}
[data-testid='stSidebar']{background:linear-gradient(180deg,#142e3b,#0c202a 76%);min-width:264px;border-right:0}[data-testid='stSidebar'] [data-testid='stSidebarContent']{padding:1.4rem .9rem}
[data-testid='stSidebar'] .stButton{margin:1px 0}[data-testid='stSidebar'] .stButton button{height:37px!important;background:transparent!important;border:0!important;color:#dbe8ed!important;justify-content:flex-start;padding:0 .75rem;font-size:.84rem;font-weight:580;box-shadow:none!important}[data-testid='stSidebar'] .stButton button[kind='primary']{background:#1d5b84!important;color:#fff!important;border-radius:6px!important}[data-testid='stSidebar'] .stButton button:hover{background:#1a4052!important;color:#fff!important}
.lnh-sidebar-brand{padding:.35rem .7rem 1.5rem;border-bottom:1px solid rgba(205,226,235,.14);margin-bottom:.7rem}.lnh-sidebar-brand b{display:block;font-size:1.55rem;letter-spacing:.04em;color:#fff}.lnh-sidebar-brand span{display:block;font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;color:#a6c0cc;margin-top:3px}.lnh-nav-group{color:#86b0c3;font-size:.62rem;font-weight:800;letter-spacing:.12em;margin:1.15rem .72rem .34rem}.lnh-sidebar-footer{color:#91aab6;font-size:.68rem;line-height:1.45;margin:2rem .7rem .4rem}
h1,h2,h3{color:var(--ink);letter-spacing:-.035em}h1{font-size:2rem!important;margin:.05rem 0 .18rem!important}h2{font-size:1.12rem!important;margin:1.5rem 0 .65rem!important}.stCaption{color:var(--muted)!important}.stButton>button{background:var(--blue);border:1px solid var(--blue);border-radius:6px;color:#fff;font-weight:700;min-height:39px;box-shadow:0 1px 2px rgba(17,43,57,.12)}.stButton>button:hover{background:#0b4878;border-color:#0b4878;color:#fff}
.lnh-shell-header{display:flex;justify-content:space-between;align-items:center;background:#fff;border:1px solid var(--line);border-radius:8px;padding:11px 16px;margin-bottom:14px;font-size:.78rem;color:var(--muted)}.lnh-shell-header b{color:var(--ink);letter-spacing:.07em}.lnh-breadcrumb{color:#63819a;font-size:.75rem;margin:0 0 .55rem}.lnh-breadcrumb span{padding:0 .34rem;color:#a7b4bc}.lnh-page-eyebrow,.lnh-kicker{font-size:.64rem;letter-spacing:.12em;color:#39708f;font-weight:800;text-transform:uppercase;margin-bottom:.22rem}
.lnh-card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px 17px;min-height:112px;margin:0 0 12px;box-shadow:0 2px 5px rgba(20,40,53,.035)}.lnh-card-title{font-size:.94rem;font-weight:760;color:var(--ink)}.lnh-card-detail{font-size:.81rem;line-height:1.46;color:var(--muted);margin-top:6px}.lnh-badge{display:inline-block;margin-top:10px;padding:3px 9px;border-radius:999px;background:#edf1f3;color:#5e6f78;font-size:.66rem;font-weight:800}.lnh-badge.ok{background:#e2efe6;color:#2e7046}.lnh-badge.build{background:#fff0d2;color:#8b6115}.lnh-badge.off{background:#edf0f2;color:#66747c}
.lnh-metric{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 16px;min-height:104px;box-shadow:0 2px 5px rgba(20,40,53,.03)}.lnh-metric-value{font-size:1.78rem;font-weight:780;line-height:1.15;color:var(--ink)}.lnh-metric-text{font-size:1.04rem}.lnh-metric-note{font-size:.78rem;color:var(--muted);line-height:1.35;margin-top:.38rem}.lnh-empty{border:1px dashed #b9c8d0;background:#fbfcfc;border-radius:8px;padding:16px;color:#627681;font-size:.86rem;line-height:1.5}
[data-testid='stTabs']{background:#fff;border:1px solid var(--line);border-radius:8px;padding:0 12px;margin-top:.9rem}[data-testid='stTabs'] button{font-size:.77rem;font-weight:720;color:#627682;white-space:nowrap}.stAlert{border-radius:8px}.stDataFrame{border:1px solid var(--line);border-radius:8px;overflow:hidden}
@media(max-width:900px){.block-container{padding:1rem 1rem 2.3rem}h1{font-size:1.55rem!important}.lnh-card{min-height:auto}}
</style>""",unsafe_allow_html=True)
if "remote_compute_status" not in st.session_state:
 st.session_state["remote_compute_status"]=runtime().prepare(timeout_seconds=20).to_dict()
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
