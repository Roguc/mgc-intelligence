"""Professional PDF/Word pack owned by corporate_engine. No corporate.professional_report."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import re

PDF_NAME = "Informe_profesional_MGC-03.pdf"
DOCX_NAME = "Informe_profesional_MGC-03.docx"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _kind(item: dict) -> str:
    return str(item.get("specialist_kind") or item.get("classification") or item.get("kind") or "").strip()


def _statement(item: dict) -> str:
    return str(item.get("statement") or item.get("claim") or item.get("text") or item.get("id") or "").strip()


def _windows_font(name: str) -> Path | None:
    windir = Path(os.environ.get("WINDIR") or r"C:\\Windows")
    candidate = windir / "Fonts" / name
    return candidate if candidate.is_file() else None


def _blocks(text: str) -> list[tuple[str, str]]:
    blocks = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("|"):
            continue
        if re.match(r"^#{1,6}\s+", line):
            blocks.append(("h", re.sub(r"^#{1,6}\s+", "", line)))
        elif re.match(r"^[-*]\s+", line):
            blocks.append(("li", re.sub(r"^[-*]\s+", "", line)))
        else:
            blocks.append(("p", line))
    return blocks


def write_docx(path: Path, title: str, sections: list[tuple[str, str]]) -> None:
    from docx import Document
    from docx.shared import Pt

    document = Document()
    heading = document.add_heading(title, 0)
    heading.runs[0].font.size = Pt(18)
    document.add_paragraph(f"Generado {_now()}")
    for kind, text in sections:
        if kind == "h":
            document.add_heading(text, level=1)
        elif kind == "h2":
            document.add_heading(text, level=2)
        elif kind == "li":
            document.add_paragraph(text, style="List Bullet")
        else:
            document.add_paragraph(text)
    document.save(path)


def _pdf_text(text: str) -> str:
    return (text or "").replace("\t", " ").replace("\x00", "")


def write_pdf(path: Path, title: str, sections: list[tuple[str, str]]) -> None:
    regular = _windows_font("arial.ttf") or _windows_font("calibri.ttf")
    bold = _windows_font("arialbd.ttf") or _windows_font("calibrib.ttf") or regular
    if not regular:
        raise RuntimeError("No hay fuente TrueType del sistema para emitir el PDF profesional.")
    from fpdf import FPDF

    pdf = FPDF(format="A4", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.add_font("Body", "", str(regular))
    pdf.add_font("Body", "B", str(bold))

    def _cell(height, text, *, bold=False, size=10):
        pdf.set_font("Body", "B" if bold else "", size)
        pdf.multi_cell(0, height, _pdf_text(text), new_x="LMARGIN", new_y="NEXT")

    _cell(8, title, bold=True, size=16)
    _cell(5, f"Generado {_now()}", size=9)
    pdf.ln(3)
    for kind, text in sections:
        if kind in {"h", "h2"}:
            _cell(7, text, bold=True, size=13 if kind == "h" else 11)
            pdf.ln(1)
        else:
            prefix = "• " if kind == "li" else ""
            _cell(5, prefix + text, size=10)
            pdf.ln(0.6)
    pdf.output(str(path))


def sections_from_pack(mission: str, pack: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = [
        ("h", "Cierre gerencial MGC-03"),
        ("p", mission),
        ("p", pack.get("sufficiency") or "Cierre gerencial pendiente de Human Gate."),
        ("p", f"Fuentes: {len(pack.get('sources') or [])}. Hallazgos: {len(pack.get('findings') or [])}."),
        ("h", "Hallazgos"),
    ]
    findings = pack.get("findings") or []
    if findings:
        for item in findings:
            rows.append(("li", f"[{_kind(item) or 'HALLAZGO'}] {_statement(item)}"))
    else:
        rows.append(("p", "Sin hallazgos materializados."))
    rows.append(("h", "Gaps y límites"))
    gaps = pack.get("gaps") or []
    if gaps:
        for gap in gaps[:24]:
            rows.append(("li", str(gap)))
    else:
        rows.append(("p", "No hay gaps listados."))
    rows.append(("h", "Fuentes"))
    for item in pack.get("sources") or []:
        rows.append(("li", f"{item.get('url') or item.get('source_id') or ''}: {item.get('title') or item.get('locator') or item.get('document') or ''}"))
    rows.append(("h", "Próximos pasos"))
    for step in pack.get("next_steps") or ["Human Gate: APROBAR / CORREGIR / RECHAZAR."]:
        rows.append(("li", str(step)))
    reports_by_agent = pack.get("reports_by_agent") if isinstance(pack.get("reports_by_agent"), dict) else {}
    if reports_by_agent:
        for agent, text in reports_by_agent.items():
            if not str(text or "").strip():
                continue
            rows.append(("h", f"Informe {agent}"))
            rows.extend(_blocks(str(text)))
    return rows


def write_professional_pack(folder: Path, mission: str, pack: dict) -> dict:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    sections = sections_from_pack(mission, pack)
    pdf = folder / PDF_NAME
    docx = folder / DOCX_NAME
    write_docx(docx, "Informe profesional MGC-03", sections)
    write_pdf(pdf, "Informe profesional MGC-03", sections)
    return {
        "pdf": PDF_NAME,
        "docx": DOCX_NAME,
        "pdf_bytes": pdf.stat().st_size if pdf.is_file() else 0,
        "docx_bytes": docx.stat().st_size if docx.is_file() else 0,
    }
