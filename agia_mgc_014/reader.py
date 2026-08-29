"""Read local project inputs without external services."""

from pathlib import Path
import csv


def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {'.txt', '.md'}:
        return path.read_text(encoding='utf-8', errors='replace')
    if suffix == '.docx':
        from docx import Document
        document = Document(path)
        paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
        tables = [' | '.join(cell.text.strip() for cell in row.cells) for table in document.tables for row in table.rows]
        return '\n'.join(paragraphs + tables)
    if suffix == '.pdf':
        from pypdf import PdfReader
        return '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
    if suffix == '.csv':
        with path.open(encoding='utf-8-sig', errors='replace', newline='') as source:
            rows = list(csv.reader(source))
        return _tabular_text(rows)
    if suffix == '.xlsx':
        from openpyxl import load_workbook
        workbook = load_workbook(path, read_only=True, data_only=True)
        sections = []
        for worksheet in workbook.worksheets:
            rows = [['' if value is None else str(value) for value in row] for row in worksheet.iter_rows(values_only=True)]
            text = _tabular_text(rows)
            if text:
                sections.append(f'[Hoja: {worksheet.title}]\n{text}')
        return '\n'.join(sections)
    raise ValueError(f'Formato no soportado: {suffix}')


def _tabular_text(rows: list[list[str]]) -> str:
    """Preserve headings so standard PMO CSV/XLSX tables become labelled records."""
    if not rows:
        return ''
    headers = [cell.strip() for cell in rows[0]]
    lines = []
    for row in rows[1:]:
        pairs = [f'{headers[index]}: {value}' for index, value in enumerate(row) if index < len(headers) and str(value).strip()]
        if pairs:
            lines.append(' | '.join(pairs))
    return '\n'.join(lines)
