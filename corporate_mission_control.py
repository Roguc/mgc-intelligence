"""Corporate navigation and case helpers for the existing Mission Control app.

The module presents only case data that has already been materialized by a
floor.  It does not replace a manager, agent, source system or Human Gate.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
from typing import Iterable


HOLDING_AREAS = (
    "Directorio", "Corporate Office", "Finanzas Corporativas",
    "Desarrollo Corporativo", "PMO", "IA y Automatización",
    "Marketing Corporativo", "Business Intelligence", "Jurídico y Compliance",
)

COMPANIES = {
    "MGC": {"name": "Miner Global Connect", "status": "Activo"},
    "LNRE": {"name": "Latitud Norte Real Estate", "status": "Estructurado sin pisos habilitados"},
}

FLOORS = {
    "MGC-03": {
        "company": "MGC", "name": "MGC-03 Research y Análisis de Mercados",
        "manager": "Gerente de Piso MGC-03", "status": "En construcción",
        "agents": (("AGIA-MGC-007", "Investigador IA de Mercado y Competencia Minera", "Diseñado - pendiente de aprobación"),),
        "availability": "El gerente puede recibir y planificar una misión; la integración E2E con AGIA-MGC-007 aún no está disponible.",
    },
    "MGC-05": {
        "company": "MGC", "name": "MGC-05 Operaciones y PMO",
        "manager": "Gerente de Piso MGC-05", "status": "Operativo",
        "agents": (
            ("AGIA-MGC-014", "Control de Proyectos y PMO", "Operativo"),
            ("AGIA-MGC-015", "Procesos, SOP y Mejora Continua", "Operativo"),
            ("AGIA-MGC-016", "Comercio Exterior y Logística", "Operativo"),
        ),
        "availability": "El gerente MGC-05 puede crear expediente, seleccionar especialistas, coordinar resultados y presentar Human Gate.",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def floors(company_id: str | None = None) -> list[dict[str, object]]:
    return [{"floor_id": key, **value} for key, value in FLOORS.items() if company_id is None or value["company"] == company_id]


def _case_id(mission: str) -> str:
    slug = re.sub("[^a-z0-9]+", "-", mission.casefold()).strip("-")[:24] or "mision"
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{slug}"


def _persist_documents(case: Path, paths: Iterable[Path]) -> list[dict[str, str]]:
    target_dir = case / "documents"
    target_dir.mkdir(parents=True, exist_ok=True)
    documents: list[dict[str, str]] = []
    for source in paths:
        target = target_dir / source.name
        number = 2
        while target.exists():
            target = target_dir / f"{source.stem}-{number}{source.suffix}"
            number += 1
        shutil.copy2(source, target)
        documents.append({"name": target.name, "original_name": source.name, "path": str(target), "sha256": sha256(target.read_bytes()).hexdigest()})
    return documents


def create_mgc03_case(root: Path, mission_text: str, paths: Iterable[Path] = ()) -> Path:
    """Use the existing MGC-03 manager to register and plan, never to infer."""
    from mgc_03.manager import MGC03FloorManager

    if not mission_text or not mission_text.strip():
        raise ValueError("La misión es obligatoria.")
    case_id = _case_id(mission_text)
    case = root / case_id
    case.mkdir(parents=True, exist_ok=False)
    documents = _persist_documents(case, paths)
    manager = MGC03FloorManager()
    received = manager.receive_mission(mission_text, case_id, [Path(item["path"]) for item in documents])
    plan = manager.plan(received["mission"].mission_id)
    supervision = manager.supervise(case_id, plan)
    payload = {
        "case_id": case_id, "floor_id": "MGC-03", "mission": mission_text.strip(), "documents": documents,
        "status": supervision["state"], "created_at": _now(),
        "plan": {"selected_agents": list(plan.selected_agents), "sequence": list(plan.sequence), "handoffs": list(plan.handoffs), "staffing_gap": list(plan.staffing_gap), "state": plan.state},
        "supervision": supervision,
        "availability": "Pendiente de implementación: no se ejecutó AGIA-MGC-007 ni se produjo consolidado gerencial.",
    }
    (case / "case.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return case


def load_corporate_case(case: Path, floor_id: str) -> dict:
    state = json.loads((case / "case.json").read_text(encoding="utf-8"))
    if floor_id == "MGC-03":
        return {"case_id": state["case_id"], "status": state["status"], "documents": state.get("documents", []), "latest": None, "raw": state, "floor_id": floor_id}
    versions = state.get("versions", [])
    return {"case_id": state["case_id"], "status": state["status"], "documents": state["documents"], "latest": versions[-1] if versions else None, "raw": state, "floor_id": floor_id}


def case_dirs(root: Path) -> list[Path]:
    return sorted([item for item in root.iterdir() if item.is_dir()], reverse=True) if root.exists() else []


def corporate_snapshot(mgc05_root: Path, mgc03_root: Path) -> dict[str, int]:
    mgc05_cases, mgc03_cases = case_dirs(mgc05_root), case_dirs(mgc03_root)
    pending, reports = 0, 0
    for case in mgc05_cases:
        try:
            state = load_corporate_case(case, "MGC-05")
        except (OSError, json.JSONDecodeError, KeyError):
            continue
        pending += int(state["status"] != "CLOSED")
        reports += len(list(case.rglob("MGC-05_DEPARTMENT_REPORT.md")))
    return {"missions": len(mgc05_cases) + len(mgc03_cases), "pending_decisions": pending, "reports": reports, "activity_records": len(mgc05_cases) + len(mgc03_cases)}


def executive_status(case: dict) -> dict[str, str]:
    if case["floor_id"] == "MGC-03":
        return {"title": "Planificación MGC-03 registrada", "completed": "La misión, el expediente y el plan inicial fueron registrados.", "blocked": "No existe ejecución integrada de AGIA-MGC-007 ni consolidado MGC-03.", "next": "Pendiente de implementación: ciclo E2E MGC-03 y Human Gate ejecutable."}
    latest = case["latest"]
    if not latest:
        return {"title": "Expediente creado", "completed": "Documentos registrados.", "blocked": "Aún no se ha ejecutado el Gerente de Piso.", "next": "Enviar misión al Gerente."}
    if latest.get("status") == "INFRASTRUCTURE_BLOCKED":
        return {"title": "Infraestructura bloqueada", "completed": "El expediente y sus documentos fueron registrados.", "blocked": "El motor no está disponible; no existe informe profesional ni resultado para aprobar.", "next": "Restablecer infraestructura y enviar una nueva versión."}
    if latest.get("status") == "SPECIALIST_EXECUTION_BLOCKED":
        return {"title": "Ejecución profesional incompleta", "completed": "El expediente y resultados disponibles fueron registrados.", "blocked": "Uno o más especialistas no completaron informe; no existe consolidado aprobable.", "next": "Restablecer el runtime documental y enviar nuevamente al Gerente."}
    return {"title": "En revisión humana", "completed": "El Gerente de Piso generó plan, resultados y consolidado.", "blocked": "Las decisiones externas permanecen bajo revisión humana.", "next": "Revisar el consolidado y registrar una decisión humana."}


def agent_reason(floor_id: str, agents: Iterable[str]) -> list[str]:
    if floor_id == "MGC-03":
        return ["AGIA-MGC-007 — seleccionado por coincidencia literal de capacidades del Agent Registry." for agent in agents if agent == "AGIA-MGC-007"]
    labels = {"014": "Control de Proyectos y PMO", "015": "Procesos, SOP y Mejora Continua", "016": "Comercio Exterior y Logística"}
    return [f"AGIA-MGC-{agent}: {labels.get(agent, 'Especialidad registrada')} — seleccionado por las capacidades detectadas en la misión." for agent in agents]


def evidence_rows(case: Path, floor_id: str) -> tuple[dict[str, int], list[dict[str, str]], dict]:
    info = load_corporate_case(case, floor_id)
    if floor_id == "MGC-03":
        rows = [{"source": item["name"], "evidence": item["sha256"], "finding": "No disponible", "output": "No disponible"} for item in info["documents"]]
        tco = {"budget": {"actual": "PENDIENTE", "forecast": "PENDIENTE", "eac": "PENDIENTE"}, "usage": {"gpu_hours": "PENDIENTE", "retries": "PENDIENTE"}}
        return {"sources": len(rows), "evidence": len(rows), "findings": 0, "outputs": 0}, rows, tco
    ledger = json.loads((case / "data_evidence.json").read_text(encoding="utf-8"))
    outputs = ", ".join(str(item.get("document", "")) for item in ledger.get("outputs", [])) or "No disponible"
    findings = ", ".join(str(item.get("subject", "")) for item in ledger.get("findings", [])) or "No disponible"
    evidence = {item.get("source_id"): item for item in ledger.get("evidence", [])}
    rows = [{"source": str(item.get("document", "No disponible")), "evidence": str(evidence.get(item.get("source_id"), {}).get("locator", "No disponible")), "finding": findings, "output": outputs} for item in ledger.get("sources", [])]
    return {"sources": len(ledger["sources"]), "evidence": len(ledger["evidence"]), "findings": len(ledger["findings"]), "outputs": len(ledger["outputs"])}, rows, ledger["tco"]


def render(st, *, mgc05_root: Path, mgc03_root: Path, create_mgc05_case, run_mgc05_case, approve_mgc05_case, correct_mgc05_case) -> None:
    """Render the corporate UI while delegating all execution to existing floors."""
    import tempfile

    def card(title: str, detail: str, status: str = "") -> None:
        badge = f"<br><span class='badge'>{status}</span>" if status else ""
        st.markdown(f"<div class='card'><b>{title}</b><br>{detail}{badge}</div>", unsafe_allow_html=True)

    def root_for(floor_id: str) -> Path:
        return mgc05_root if floor_id == "MGC-05" else mgc03_root

    if "selected_floor" not in st.session_state:
        st.session_state["selected_floor"] = "MGC-05"
    if "selected_company" not in st.session_state:
        st.session_state["selected_company"] = "MGC"

    pages = ("Mi Oficina", "Holding", "Empresas", "Pisos", "Gerentes y agentes", "Misiones", "Evidencia y conocimiento", "Reportes")
    page = st.sidebar.radio("Navegación", pages, index=pages.index(st.session_state.get("corporate_page", "Mi Oficina")))
    st.session_state["corporate_page"] = page
    st.sidebar.markdown("---")
    st.sidebar.caption("Mi Oficina → Holding → Empresas → Pisos → Gerentes → Agentes")

    if page == "Mi Oficina":
        summary = corporate_snapshot(mgc05_root, mgc03_root)
        st.title("Mi Oficina")
        st.caption("CEO / Presidencia · Centro de mando de Latitud Norte Holding")
        a, b, c, d = st.columns(4)
        a.metric("Misiones registradas", summary["missions"])
        b.metric("Decisiones pendientes", summary["pending_decisions"])
        c.metric("Informes recibidos", summary["reports"])
        d.metric("Registros de actividad", summary["activity_records"])
        st.subheader("Accesos ejecutivos")
        for title, state in (("Correo", "No conectado"), ("Calendario", "No conectado"), ("Actividades", "Disponible mediante expedientes locales"), ("Decisiones", "Disponible mediante Human Gate de MGC-05"), ("Informes", "Disponibles cuando un piso los materializa")):
            card(title, "No hay datos externos simulados.", state)
        return

    if page == "Holding":
        st.title("Latitud Norte Holding")
        st.caption("Áreas corporativas estructuralmente disponibles. No se atribuyen operaciones, métricas ni dotación no materializadas.")
        columns = st.columns(3)
        for index, area in enumerate(HOLDING_AREAS):
            with columns[index % 3]:
                card(area, "Sin datos operativos registrados.", "No habilitado")
        return

    if page == "Empresas":
        st.title("Empresas")
        for company_id, company in COMPANIES.items():
            available = floors(company_id)
            card(company["name"], f"Pisos materializados: {len(available)}.", company["status"])
            for floor in available:
                if st.button(f"Abrir {floor['floor_id']}", key=f"company-{floor['floor_id']}"):
                    st.session_state["selected_company"] = company_id
                    st.session_state["selected_floor"] = floor["floor_id"]
                    st.session_state["corporate_page"] = "Pisos"
                    st.rerun()
            if not available:
                st.caption("No hay pisos habilitados en la plataforma actual.")
        return

    if page in {"Pisos", "Gerentes y agentes"}:
        if page == "Pisos":
            st.title("Pisos")
            for floor in floors(st.session_state["selected_company"]):
                card(str(floor["name"]), str(floor["availability"]), str(floor["status"]))
                if st.button("Seleccionar piso", key=f"floor-{floor['floor_id']}"):
                    st.session_state["selected_floor"] = floor["floor_id"]
                    st.rerun()
            selected = next((item for item in floors() if item["floor_id"] == st.session_state["selected_floor"]), None)
            if selected:
                st.subheader(f"{selected['floor_id']} · {selected['name']}")
                st.write(f"Gerente: {selected['manager']}")
                for agent_id, name, status in selected["agents"]:
                    st.write(f"• {agent_id} — {name} ({status})")
        else:
            st.title("Gerentes y agentes")
            for floor in floors():
                st.subheader(f"{floor['floor_id']} · {floor['name']}")
                card(str(floor["manager"]), str(floor["availability"]), str(floor["status"]))
                for agent_id, name, status in floor["agents"]:
                    card(agent_id, str(name), str(status))
        return

    if page == "Misiones":
        floor_ids = [item["floor_id"] for item in floors()]
        selected_floor = st.selectbox("Piso destinatario", floor_ids, index=floor_ids.index(st.session_state["selected_floor"]))
        st.session_state["selected_floor"] = selected_floor
        floor = next(item for item in floors() if item["floor_id"] == selected_floor)
        st.title(f"Misiones · {selected_floor}")
        st.caption(f"Enviar misión al Gerente de Piso · {floor['manager']}")
        st.info(str(floor["availability"]))
        mission = st.text_area("Misión en lenguaje natural", placeholder="Describa el objetivo y el resultado requerido.", height=120)
        uploads = st.file_uploader("Documentos de evidencia adicionales (opcionales)", type=["txt", "md", "docx", "pdf", "csv", "xlsx"], accept_multiple_files=True)
        if st.button("Enviar misión al Gerente", type="primary"):
            if not mission.strip():
                st.error("Ingrese una misión.")
            else:
                with tempfile.TemporaryDirectory() as temporary:
                    paths, failures = [], []
                    for upload in uploads or []:
                        try:
                            path = Path(temporary) / upload.name
                            path.write_bytes(upload.getvalue())
                            paths.append(path)
                        except Exception as error:
                            failures.append(f"{upload.name}: {error}")
                    if failures:
                        st.error("No se cargaron algunos documentos: " + "; ".join(failures))
                    try:
                        if selected_floor == "MGC-05":
                            case = create_mgc05_case(mission, paths, mgc05_root)
                            _, details = run_mgc05_case(case)
                            state = details["status"]
                        else:
                            case = create_mgc03_case(mgc03_root, mission, paths)
                            state = load_corporate_case(case, "MGC-03")["status"]
                        st.session_state["active_case"] = str(case)
                        st.success(f"Expediente corporativo registrado: {case.name}. Estado: {state}.")
                    except Exception as error:
                        st.error(f"No se pudo enviar la misión al Gerente: {error}")

        st.divider()
        st.header("Expediente de misión")
        available_cases = case_dirs(root_for(selected_floor))
        choices = [""] + [item.name for item in available_cases]
        default = Path(st.session_state.get("active_case", "")).name
        case_id = st.selectbox("Expediente", choices, index=choices.index(default) if default in choices else 0)
        if not case_id:
            return
        case = root_for(selected_floor) / case_id
        info = load_corporate_case(case, selected_floor)
        status = executive_status(info)
        st.subheader(status["title"])
        st.success("Completado: " + status["completed"])
        st.warning("Bloqueado / pendiente: " + status["blocked"])
        st.info("Próxima acción: " + status["next"])
        a, b, c = st.columns(3)
        a.metric("Estado", info["status"])
        b.metric("Documentos", len(info["documents"]))
        c.metric("Versión", info["latest"]["version"] if info["latest"] else "No disponible")
        st.subheader("Objetivo interpretado y entregable")
        st.write(info["raw"].get("mission", "No disponible"))
        st.write("Entregable: " + ("Pendiente de implementación / No disponible" if selected_floor == "MGC-03" else "Informe departamental MGC-05, si los especialistas completan la ejecución."))
        st.subheader("Plan, especialistas, dependencias y progreso")
        if selected_floor == "MGC-03":
            plan = info["raw"].get("plan", {})
            for item in agent_reason("MGC-03", plan.get("selected_agents", [])):
                st.write("• " + item)
            st.write("Dependencias: " + ("Registradas" if plan.get("handoffs") else "No disponible"))
            st.write("Progreso: Pendiente de implementación / No disponible")
        elif info["latest"]:
            for item in agent_reason("MGC-05", info["latest"].get("routes", [])):
                st.write("• " + item)
            st.write("Dependencias y handoffs: disponibles en el artefacto técnico del expediente.")
            st.write("Progreso por especialista: Pendiente de implementación / No disponible")
        else:
            st.write("Pendiente de implementación / No disponible")
        st.subheader("Herramientas, fuentes y evidencia")
        st.write("Herramientas utilizadas: Pendiente de implementación / No disponible")
        st.write("Fuentes y evidencia: disponibles en Evidencia y conocimiento cuando el expediente las materializa.")
        if selected_floor == "MGC-05" and info["latest"]:
            version = case / f"v{info['latest']['version']:03d}"
            report, status_report = version / "MGC-05_DEPARTMENT_REPORT.md", version / "MGC-05_EXECUTION_STATUS.md"
            if report.exists():
                st.subheader("Revisión gerencial y consolidado")
                st.markdown(report.read_text(encoding="utf-8"))
            elif status_report.exists():
                st.subheader("Estado de ejecución")
                st.markdown(status_report.read_text(encoding="utf-8"))
        else:
            st.subheader("Resultados, revisión gerencial y consolidado")
            st.write("Pendiente de implementación / No disponible")
        st.subheader("Historial")
        events = info["raw"].get("audit", [])
        st.write(f"Eventos registrados: {len(events)}" if events else "Pendiente de implementación / No disponible")
        st.subheader("Human Gate")
        if selected_floor == "MGC-05":
            st.caption("CORREGIR registra la observación humana y la dirige al Gerente MGC-05. El ciclo inteligente posterior corresponde a una etapa posterior.")
            decision = st.selectbox("Decisión", ["APROBAR", "CORREGIR", "RECHAZAR"])
            rationale = st.text_area("Fundamento / observación para el Gerente")
            if st.button("Registrar decisión humana"):
                try:
                    if decision == "CORREGIR":
                        correct_mgc05_case(case, rationale)
                    else:
                        approve_mgc05_case(case, "APROBADO" if decision == "APROBAR" else "RECHAZADO", rationale)
                    st.success("Decisión humana registrada.")
                except Exception as error:
                    st.error(str(error))
        else:
            st.info("Pendiente de implementación: MGC-03 no cuenta aún con Human Gate ejecutable desde Mission Control.")
        with st.expander("Artefactos técnicos de auditoría"):
            for artifact in _artifacts(case, selected_floor, info):
                st.download_button(f"Descargar {artifact.name}", artifact.read_bytes(), artifact.name)
        return

    if page == "Evidencia y conocimiento":
        st.title("Evidencia y conocimiento")
        floor_ids = [item["floor_id"] for item in floors()]
        selected_floor = st.selectbox("Piso", floor_ids, index=floor_ids.index(st.session_state["selected_floor"]))
        cases = case_dirs(root_for(selected_floor))
        case_id = st.selectbox("Expediente con trazabilidad", [""] + [item.name for item in cases])
        if case_id:
            case = root_for(selected_floor) / case_id
            summary, rows, tco = evidence_rows(case, selected_floor)
            a, b, c, d = st.columns(4)
            a.metric("Fuentes", summary["sources"])
            b.metric("Evidencias", summary["evidence"])
            c.metric("Hallazgos", summary["findings"])
            d.metric("Outputs", summary["outputs"])
            st.subheader("Ruta de conocimiento disponible")
            for row in rows:
                card(row["source"], f"Evidencia: {row['evidence']}<br>Hallazgo: {row['finding']}<br>Output: {row['output']}")
            st.subheader("TCO ejecutivo")
            st.write(f"Costo real: {tco['budget']['actual']} · Forecast: {tco['budget']['forecast']} · EAC: {tco['budget']['eac']} · GPU horas: {tco['usage']['gpu_hours']} · Reprocesos: {tco['usage']['retries']}")
            st.caption("La ruta Fuente → Evidencia → Hallazgo → Output usa exclusivamente registros materializados; los campos no producidos indican No disponible.")
        else:
            st.info("Seleccione un expediente para consultar evidencia materializada.")
        return

    st.title("Reportes")
    reports = [item for case in case_dirs(mgc05_root) for item in case.rglob("MGC-05_DEPARTMENT_REPORT.md")]
    if reports:
        for report in sorted(reports, reverse=True):
            st.download_button(f"Descargar {report.parent.parent.name} · {report.name}", report.read_bytes(), report.name)
    else:
        st.info("No hay informes departamentales MGC-05 materializados.")
    st.caption("Los informes de otros pisos aparecerán cuando sus respectivos gerentes los materialicen.")


def _artifacts(case: Path, floor_id: str, info: dict) -> list[Path]:
    if floor_id == "MGC-03":
        return [case / "case.json"]
    latest = info["latest"]
    if not latest:
        return []
    version = case / f"v{latest['version']:03d}"
    return [item for item in (version / "MGC-05_DEPARTMENT_REPORT.md", version / "MGC-05_EXECUTION_STATUS.md", version / "plan.json", version / "handoffs.json", version / "contradictions.json") if item.exists()]
