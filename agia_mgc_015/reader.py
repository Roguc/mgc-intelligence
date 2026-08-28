from pathlib import Path

def read_document(path: Path) -> str:
    suffix=path.suffix.lower()
    if suffix in {'.txt','.md'}: return path.read_text(encoding='utf-8',errors='replace')
    if suffix=='.docx':
        from docx import Document
        return '\n'.join(p.text for p in Document(path).paragraphs)
    if suffix=='.pdf':
        from pypdf import PdfReader
        return '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
    raise ValueError(f'Formato no soportado: {suffix}')
