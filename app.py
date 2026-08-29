from pathlib import Path
import tempfile

import streamlit as st

from agia_mgc_015.agent import run as run_process_agent
from agia_mgc_014.agent import run_with_result as run_pmo_agent


AGENTS = {
    'AGIA-MGC-014 — Ingeniero IA de Control de Proyectos y PMO': 'pmo',
    'AGIA-MGC-015 — Analista IA de Procesos, SOP y Mejora Continua': 'process',
}

st.set_page_config(page_title='Miner Global Connect Intelligence', layout='wide')
st.title('Miner Global Connect Intelligence')
st.caption('MGC-05 Operaciones y PMO · Ejecución local · Sin APIs externas')
selected = st.selectbox('Agente', list(AGENTS))
mission = st.text_area('Misión o instrucción profesional', height=150)
files = st.file_uploader(
    'Documentos de trabajo',
    type=['txt', 'md', 'docx', 'pdf', 'csv', 'xlsx'] if AGENTS[selected] == 'pmo' else ['txt', 'md', 'docx', 'pdf'],
    accept_multiple_files=True,
)

if st.button('Generar informe profesional', type='primary'):
    if not mission.strip():
        st.error('Ingrese una misión.')
        st.stop()
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        paths = []
        for file in files or []:
            path = folder / file.name
            path.write_bytes(file.getvalue())
            paths.append(path)
        if AGENTS[selected] == 'pmo':
            result = run_pmo_agent(mission, paths, Path('outputs'))
            target, issues = result.report_path, result.review_issues
        else:
            target, issues = run_process_agent(mission, paths, Path('outputs'))
    text = target.read_text(encoding='utf-8')
    st.markdown(text)
    if issues:
        st.warning('\n'.join(issues))
    st.download_button('Exportar informe', text, target.name, 'text/markdown')
