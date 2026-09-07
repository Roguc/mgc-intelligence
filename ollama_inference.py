"""Professional inference facade for MGC-05, backed by the configured gateway."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from uuid import uuid4
from urllib.request import Request, urlopen

MODEL = os.getenv('MGC_OLLAMA_MODEL', 'qwen3:14b')
MAX_DOCUMENT_CONTEXT_CHARS = 12000


def _as_text(value: object) -> str:
    """Normalise optional extractor/runtime values without fabricating text."""
    return value if isinstance(value, str) else ''


class ProfessionalQualityError(RuntimeError):
    """Carries the immutable attempt record when a report is rejected."""
    def __init__(self, message: str, trace: dict):
        super().__init__(message)
        self.trace = trace


def enabled() -> bool:
    """Rules mode is retained only for deterministic unit tests."""
    return os.getenv('MGC_INFERENCE_MODE', 'ollama').casefold() != 'rules'


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
            capture_output=True, text=True, encoding='utf-8', errors='replace', check=False,
        )
        images = list(Path(directory).glob('page-*.png'))
        if rendered.returncode or not images:
            return ''
        result = subprocess.run(
            [tesseract, str(images[0]), 'stdout', '-l', 'eng'],
            capture_output=True, text=True, encoding='utf-8', errors='replace', check=False,
        )
        return _as_text(result.stdout).strip() if result.returncode == 0 else ''


def _page_chunks(path: Path, width: int = 1500) -> list[dict[str, str | int]]:
    """Extract verbatim local text with an OCR fallback for scanned PDF pages."""
    if path.suffix.casefold() == '.pdf':
        from pypdf import PdfReader
        pages = []
        try:
            reader = PdfReader(path)
            for index, pdf_page in enumerate(reader.pages, start=1):
                text = _as_text(pdf_page.extract_text()).strip()
                method = 'pdf_text'
                if len(text) < 20:
                    text = _as_text(_ocr_pdf_page(path, index)).strip()
                    method = 'ocr' if text else 'unreadable'
                pages.append((index, text, method))
        except Exception:
            pages = [(1, '', 'unreadable')]
    else:
        from agia_mgc_014.reader import read_document
        pages = [(1, _as_text(read_document(path)), 'native_text')]
    chunks = []
    for page, text, method in pages:
        text = _as_text(text)
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
    selected_characters = sum(len(str(chunk['text'])) for chunk in selected)
    for chunk in sorted(all_chunks, key=lambda item: item['score'], reverse=True):
        if (len(selected) >= 12 or (chunk['document'], chunk['page'], chunk['start']) in selected_ids
                or selected_characters + len(str(chunk['text'])) > MAX_DOCUMENT_CONTEXT_CHARS):
            continue
        selected.append(chunk); selected_ids.add((chunk['document'], chunk['page'], chunk['start']))
        selected_characters += len(str(chunk['text']))
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


def required_section_issues(report: str, sections: list[str]) -> list[str]:
    """Require model-developed sections; never create placeholder content."""
    issues = []
    for section in sections:
        match = re.search(rf'^\s*#{{1,6}}\s+(?:\*\*)?(?:\d+[.)]\s*)?{re.escape(section)}(?:\*\*)?\s*$', report, re.IGNORECASE | re.MULTILINE)
        if not match:
            issues.append(f'Sección obligatoria ausente: {section}.')
            continue
        following = report[match.end():]
        next_heading = re.search(r'^\s*#{1,6}\s+', following, re.MULTILINE)
        content = following[:next_heading.start() if next_heading else len(following)].strip()
        if len(content) < 40 or 'la inferencia no desarrolló esta sección' in content.casefold():
            issues.append(f'Sección obligatoria sin desarrollo profesional: {section}.')
    if len(report) < 2200:
        issues.append('Informe insuficientemente desarrollado para revisión profesional.')
    citations = re.findall(r'\[[^\]\n]+,\s*p\.\s*\d+\]', report, re.IGNORECASE)
    if len(citations) < 3:
        issues.append('Trazabilidad documental insuficiente: se requieren al menos tres citas documento-página.')
    categories = ('documentado', 'infer', 'requiere confirmación')
    if any(category not in report.casefold() for category in categories):
        issues.append('Falta distinción explícita entre evidencia documentada, inferencia y confirmación requerida.')
    return issues


def _generate(prompt: str, execution_id: str, attempt: int) -> tuple[dict, str]:
    from remote_compute import runtime
    return runtime().generate(prompt, execution_id, attempt)


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
    execution_id = uuid4().hex
    prompt = f'''# Rol profesional\n{agent_code}\n{mandate}\n\n# Misión\n{mission}\n\n# Reglas obligatorias\n- Usa exclusivamente los documentos originales reproducidos abajo como fuente de verdad.\n- Distingue DOCUMENTADO, DECLARADO, INFERIDO, PROPUESTO y REQUIERE CONFIRMACIÓN.\n- No inventes hechos, fechas, responsables, autenticidad, vínculos documentales ni datos ausentes.\n- No autorices ni ejecutes pagos, contratos, correos, contactos externos, embarques, producción o acciones irreversibles.\n- Cuando un documento sea histórico, contradictorio o no pueda asociarse a una operación, dilo expresamente.\n- Separa explícitamente operación actual, antecedentes históricos y documentos no vinculados. No fusiones expedientes sin evidencia documental.\n- Toda conclusión material debe citar el documento y página entre corchetes: [nombre de documento, p. N].\n- No atribuyas una fecha de ejecución distinta de {datetime.now(timezone.utc).date().isoformat()}.\n- Escribe un informe profesional completo en español, con trazabilidad por nombre de documento, riesgos, acciones internas y escalamiento humano.\n- Usa exactamente los encabezados Markdown exigidos y desarrolla cada sección; una brecha debe explicar qué falta y por qué.\n\n# Secciones obligatorias\n{chr(10).join(f'## {section}' for section in sections)}\n\n# Documentos originales\n{documents}'''
    from remote_compute import runtime
    status = runtime().prepare()
    if not status.ready:
        raise RuntimeError(status.executive_message)
    started = datetime.now(timezone.utc)
    attempts = []
    result, report = _generate(prompt, execution_id, 1)
    attempts.append({'attempt':1,'response_sha256':sha256(report.encode('utf-8')).hexdigest(),'technical_valid':True,'prompt_eval_count':result.get('prompt_eval_count'),'eval_count':result.get('eval_count'),'total_duration_ns':result.get('total_duration')})
    trace = {
        'execution_id': execution_id, 'agent': agent_code, 'runtime': getattr(runtime(), 'provider_name', 'unknown'), 'model': result.get('model', getattr(runtime(), 'model', MODEL)),
        'executed_at': started.isoformat(), 'documents': document_trace,
        'selected_fragments': [{key: fragment[key] for key in ('document', 'page', 'start', 'end', 'method')} for fragment in selected_fragments],
        'context_characters': sum(len(str(fragment['text'])) for fragment in selected_fragments),
        'document_to_conclusion': _document_conclusion_trace(report, document_trace),
        'prompt_eval_count': result.get('prompt_eval_count'), 'eval_count': result.get('eval_count'),
        'total_duration_ns': result.get('total_duration'), 'load_duration_ns': result.get('load_duration'),
        'cost_usd': 0.0,
        'attempts': attempts,
    }
    return report, trace


def write_trace(output_dir: Path, agent_code: str, trace: dict, report_path: Path | None = None) -> Path:
    trace['case_id'] = output_dir.parent.name
    trace['version'] = output_dir.name
    if report_path is not None:
        trace['report'] = report_path.name
        trace['report_sha256'] = sha256(report_path.read_bytes()).hexdigest()
    target = output_dir / f"{agent_code}_{trace['execution_id']}_LOCAL_INFERENCE_TRACE.json"
    target.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding='utf-8')
    return target
