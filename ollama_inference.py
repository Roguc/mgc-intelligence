"""Local-only professional inference for MGC-05 via Ollama on localhost."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.request import Request, urlopen

MODEL = os.getenv('MGC_OLLAMA_MODEL', 'qwen3:14b')


def enabled() -> bool:
    """Rules mode is retained only for deterministic unit tests."""
    return os.getenv('MGC_INFERENCE_MODE', 'ollama').casefold() == 'ollama'


def _ocr_pdf_page(path: Path, page: int) -> str:
    """Extract a scanned PDF page locally; no model-generated text is used."""
    tesseract = shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    pdftoppm = shutil.which('pdftoppm')
    if not Path(tesseract).is_file() or not pdftoppm:
        return ''
    with tempfile.TemporaryDirectory(prefix='mgc-ocr-') as directory:
        prefix = Path(directory) / 'page'
        rendered = subprocess.run(
            [pdftoppm, '-f', str(page), '-l', str(page), '-r', '200', '-png', str(path), str(prefix)],
            capture_output=True, text=True, check=False,
        )
        images = list(Path(directory).glob('page-*.png'))
        if rendered.returncode or not images:
            return ''
        result = subprocess.run(
            [tesseract, str(images[0]), 'stdout', '-l', 'eng'],
            capture_output=True, text=True, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ''


def _page_chunks(path: Path, width: int = 2400) -> list[dict[str, str | int]]:
    """Extract verbatim local text with an OCR fallback for scanned PDF pages."""
    if path.suffix.casefold() == '.pdf':
        from pypdf import PdfReader
        pages = []
        for index, pdf_page in enumerate(PdfReader(path).pages, start=1):
            text = (pdf_page.extract_text() or '').strip()
            method = 'pdf_text'
            if len(text) < 20:
                text = _ocr_pdf_page(path, index)
                method = 'ocr' if text else 'unreadable'
            pages.append((index, text, method))
    else:
        from agia_mgc_014.reader import read_document
        pages = [(1, read_document(path), 'native_text')]
    chunks = []
    for page, text, method in pages:
        if not text.strip():
            chunks.append({'document': path.name, 'page': page, 'start': 0, 'end': 0, 'method': method, 'text': '[No se extrajo texto legible; no infieras su contenido.]'})
            continue
        for start in range(0, len(text), width):
            chunks.append({'document': path.name, 'page': page, 'start': start, 'end': min(start + width, len(text)), 'method': method, 'text': text[start:start + width]})
    return chunks


def _documents(paths: list[Path], query: str) -> tuple[str, list[dict[str, str]], list[dict[str, str | int]]]:
    """Select original text fragments under the 8k context budget with provenance."""
    all_chunks, trace = [], []
    for path in paths:
        chunks = _page_chunks(path)
        trace.append({
            'name': path.name,
            'sha256': sha256(path.read_bytes()).hexdigest(),
            'fragments_available': len(chunks),
            'extraction_methods': sorted({str(chunk['method']) for chunk in chunks}),
        })
        all_chunks.extend(chunks)
    terms = {word.casefold() for word in query.split() if len(word) > 3}
    for chunk in all_chunks:
        chunk['score'] = sum(term in str(chunk['text']).casefold() for term in terms)
    # Preserve coverage: first choose the most relevant original fragment per document.
    selected = []
    for name in dict.fromkeys(chunk['document'] for chunk in all_chunks):
        selected.append(max((chunk for chunk in all_chunks if chunk['document'] == name), key=lambda chunk: (chunk['score'], -int(chunk['page']), -int(chunk['start']))))
    selected_ids = {(chunk['document'], chunk['page'], chunk['start']) for chunk in selected}
    for chunk in sorted(all_chunks, key=lambda item: item['score'], reverse=True):
        if len(selected) >= 10 or (chunk['document'], chunk['page'], chunk['start']) in selected_ids:
            continue
        selected.append(chunk); selected_ids.add((chunk['document'], chunk['page'], chunk['start']))
    selected.sort(key=lambda item: (str(item['document']), int(item['page']), int(item['start'])))
    sections = [f"\n--- DOCUMENTO ORIGINAL: {chunk['document']} | página {chunk['page']} | caracteres {chunk['start']}-{chunk['end']} ---\n{chunk['text']}" for chunk in selected]
    return ''.join(sections), trace, selected


def _document_conclusion_trace(report: str, documents: list[dict[str, str]]) -> list[dict[str, object]]:
    """Preserve every report line that cites a source document."""
    return [
        {
            'document': document['name'],
            'report_references': [line.strip() for line in report.splitlines() if document['name'].casefold() in line.casefold()],
        }
        for document in documents
    ]


def _ensure_required_sections(report: str, sections: list[str]) -> str:
    """Do not silently lose an obligatory section when a model omits it."""
    missing = [section for section in sections if section.casefold() not in report.casefold()]
    if not missing:
        return report
    appendix = '\n\n## Control de estructura y elementos pendientes\n'
    for section in missing:
        appendix += f'\n### {section}\nREQUIERE CONFIRMACIÓN: la inferencia no desarrolló esta sección; no se infiere contenido.\n'
    return report.rstrip() + appendix


def professional_report(
    agent_code: str,
    mandate: str,
    mission: str,
    paths: list[Path],
    required_sections: list[str] | None = None,
) -> tuple[str, dict]:
    """Produce one internal report with a local Ollama runtime only."""
    documents, document_trace, selected_fragments = _documents(paths, f'{mandate} {mission}')
    sections = required_sections or []
    prompt = f'''# Rol profesional\n{agent_code}\n{mandate}\n\n# Misión\n{mission}\n\n# Reglas obligatorias\n- Usa exclusivamente los documentos originales reproducidos abajo como fuente de verdad.\n- Distingue DOCUMENTADO, DECLARADO, INFERIDO, PROPUESTO y REQUIERE CONFIRMACIÓN.\n- No inventes hechos, fechas, responsables, autenticidad, vínculos documentales ni datos ausentes.\n- No autorices ni ejecutes pagos, contratos, correos, contactos externos, embarques, producción o acciones irreversibles.\n- Cuando un documento sea histórico, contradictorio o no pueda asociarse a una operación, dilo expresamente.\n- Separa explícitamente operación actual, antecedentes históricos y documentos no vinculados. No fusiones expedientes sin evidencia documental.\n- Toda conclusión material debe citar el documento y página entre corchetes: [nombre de documento, p. N].\n- No atribuyas una fecha de ejecución distinta de {datetime.now(timezone.utc).date().isoformat()}.\n- Escribe un informe profesional completo en español, con trazabilidad por nombre de documento, riesgos, acciones internas y escalamiento humano.\n\n# Secciones obligatorias\n{chr(10).join(f'## {section}' for section in sections)}\n\n# Documentos originales\n{documents}'''
    from remote_compute import runtime
    status = runtime().prepare()
    if not status.ready:
        raise RuntimeError(status.executive_message)
    payload = {'model': MODEL, 'prompt': prompt, 'stream': False, 'think': False, 'options': {'temperature': 0.1, 'num_ctx': 8192}}
    request = Request(f'{runtime().endpoint_url}/api/generate', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    started = datetime.now(timezone.utc)
    try:
        with urlopen(request, timeout=600) as response:
            result = json.loads(response.read().decode('utf-8'))
    except Exception as error:
        raise RuntimeError(f'Ollama local no pudo generar el informe: {error}') from error
    report = result.get('response', '').strip()
    if not report:
        raise RuntimeError('Ollama local no devolvió un informe profesional.')
    report = _ensure_required_sections(report, sections)
    trace = {
        'agent': agent_code, 'runtime': 'ollama-localhost', 'model': MODEL,
        'executed_at': started.isoformat(), 'documents': document_trace,
        'selected_fragments': [{key: fragment[key] for key in ('document', 'page', 'start', 'end', 'method')} for fragment in selected_fragments],
        'document_to_conclusion': _document_conclusion_trace(report, document_trace),
        'prompt_eval_count': result.get('prompt_eval_count'), 'eval_count': result.get('eval_count'),
        'total_duration_ns': result.get('total_duration'), 'load_duration_ns': result.get('load_duration'),
        'cost_usd': 0.0,
    }
    return report, trace


def write_trace(output_dir: Path, agent_code: str, trace: dict) -> Path:
    target = output_dir / f'{agent_code}_LOCAL_INFERENCE_TRACE.json'
    target.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
    return target
