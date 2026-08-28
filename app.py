from pathlib import Path
import tempfile
import streamlit as st
from agia_mgc_015.agent import run

st.set_page_config(page_title='AGIA-MGC-015',layout='wide')
st.title('AGIA-MGC-015 — Analista IA de Procesos, SOP y Mejora Continua')
st.caption('Miner Global Connect · MGC-05 Operaciones y PMO · Sin APIs externas')
mission=st.text_area('Misión o instrucción profesional',height=130)
files=st.file_uploader('Documentos de trabajo',type=['txt','md','docx','pdf'],accept_multiple_files=True)
if st.button('Generar informe profesional',type='primary'):
    if not mission.strip(): st.error('Ingrese una misión.'); st.stop()
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp); paths=[]
        for file in files or []:
            path=folder/file.name; path.write_bytes(file.getvalue()); paths.append(path)
        target,issues=run(mission,paths,Path('outputs'))
    text=target.read_text(encoding='utf-8'); st.markdown(text)
    if issues: st.warning('\n'.join(issues))
    st.download_button('Exportar informe',text,target.name,'text/markdown')
