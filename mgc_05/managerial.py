"""Evidence-governed coordination for the MGC-05 departmental backend.

This module never interprets source documents or replaces a specialist. It
records what each specialist reported, compares explicit classifications, and
applies only the departmental conservative-evidence rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


MATERIAL_DOCUMENTS = {
    "B/L": ("b/l", "bl.pdf"),
    "SGS": ("sgs", "sgs.pdf"),
    "Laboratorio Preisser": ("laboratorio", "preisser", "mgc016_lab_input"),
}
LINKED = ("documento vinculado", "vínculo demostrado", "embarque realizado", "en proceso de embarque")
UNLINKED = ("no vinculado", "sin vinculación", "vínculo no demostrado", "no se menciona el vínculo", "antecedente histórico", "histórico")


@dataclass(frozen=True)
class SpecialistOutput:
    agent: str
    report: str
    evidence: tuple[str, ...]


def _normalise(text: str) -> str:
    return text.casefold()


def _mentions(text: str, values: Iterable[str]) -> bool:
    return any(value in text for value in values)


def classify_report(report: str) -> dict[str, set[str]]:
    """Return specialist-stated classifications without deciding factual truth."""
    lines = _normalise(report).splitlines()
    result = {"linked": set(), "unlinked": set(), "historical": set()}
    for document, aliases in MATERIAL_DOCUMENTS.items():
        relevant = [line for line in lines if any(alias in line for alias in aliases)]
        if not relevant:
            continue
        context = " ".join(relevant)
        if _mentions(context, LINKED):
            result["linked"].add(document)
        # A specialist may explicitly state the missing link once after listing
        # several documents.  Preserve that reported classification for each
        # material document mentioned in the same report; this does not decide
        # whether the link exists.
        if _mentions(context, UNLINKED) or (
            "no se menciona el vínculo directo con la operación actual" in _normalise(report)
        ):
            result["unlinked"].add(document)
        if "histórico" in context:
            result["historical"].add(document)
    return result


def build_handoffs(outputs: list[SpecialistOutput]) -> list[dict[str, object]]:
    """Record output/evidence handoffs; this is coordination metadata only."""
    handoffs: list[dict[str, object]] = []
    for index, source in enumerate(outputs):
        destinations = [item.agent for item in outputs[index + 1 :]] or ["Case Manager"]
        for destination in destinations:
            handoffs.append({
                "origin": source.agent,
                "destination": destination,
                "information_evidence": list(source.evidence),
                "information_needed_by_destination": "Informe y traza del especialista de origen para contrastar hallazgos; el destinatario conserva el deber de analizar los documentos originales dentro de su propia competencia.",
                "reason": "Resultado profesional disponible para coordinación y consolidación; no sustituye el análisis del destinatario.",
            })
    return handoffs


def detect_contradictions(outputs: list[SpecialistOutput]) -> list[dict[str, object]]:
    """Flag incompatible specialist classifications and apply the fixed rule."""
    views = {output.agent: classify_report(output.report) for output in outputs}
    contradictions: list[dict[str, object]] = []
    for subject in MATERIAL_DOCUMENTS:
        linked_by = [agent for agent, view in views.items() if subject in view["linked"]]
        unlinked_by = [agent for agent, view in views.items() if subject in view["unlinked"]]
        if linked_by and unlinked_by:
            contradictions.append({
                "subject": subject,
                "linked_by": linked_by,
                "unlinked_by": unlinked_by,
                "departmental_status": "VÍNCULO NO DEMOSTRADO / REQUIERE REVISIÓN HUMANA",
                "human_confirmation": f"Confirmar con evidencia documental suficiente si {subject} pertenece a la operación analizada.",
            })
    return contradictions


def build_managerial_record(outputs: list[SpecialistOutput]) -> dict[str, object]:
    contradictions = detect_contradictions(outputs)
    return {
        "handoffs": build_handoffs(outputs),
        "contradictions": contradictions,
        "human_decisions": [item["human_confirmation"] for item in contradictions],
        "departmental_status": "HUMAN_REVIEW_REQUIRED",
        "authority_notice": "Estado gerencial basado en divergencias explícitas de especialistas; no es una conclusión PMO, SOP, logística, jurídica, financiera ni técnica.",
    }


def render_department_report(case_id: str, mission: str, outputs: list[SpecialistOutput], record: dict[str, object]) -> str:
    """Render a managerial report that attributes all professional content."""
    lines = [
        "# Informe departamental MGC-05",
        "## Resumen Ejecutivo",
        "Este informe coordina y presenta resultados de especialistas. No reemplaza sus conclusiones profesionales.",
        "## Estado del expediente",
        f"Caso: {case_id}",
        f"Estado gerencial: {record['departmental_status']}",
        "## Trabajo realizado por especialista",
    ]
    for output in outputs:
        lines.extend([f"### {output.agent}", f"Informe original: {output.report}"])
    lines.append("## Handoffs")
    for handoff in record["handoffs"]:
        lines.append(f"- {handoff['origin']} → {handoff['destination']}: {handoff['reason']}")
    lines.extend(["## Hechos coincidentes", "No se declara un hecho coincidente nuevo: las conclusiones se mantienen atribuidas a cada especialista.", "## Contradicciones"])
    if record["contradictions"]:
        for item in record["contradictions"]:
            lines.append(f"- {item['subject']}: vinculado por {', '.join(item['linked_by'])}; no vinculado/no demostrado por {', '.join(item['unlinked_by'])}. Estado: {item['departmental_status']}.")
    else:
        lines.append("- No se detectaron contradicciones explícitas por la regla automática.")
    lines.extend([
        "## Evidencia no vinculada / histórica",
        "La pertenencia de evidencia histórica o no vinculada queda sujeta a la regla conservadora y a revisión humana.",
        "## Riesgos y bloqueos",
        "Se remite a los informes atribuidos de los especialistas; el backend no crea riesgos especializados.",
        "## Información faltante",
        "Se remite a los informes atribuidos de los especialistas; el backend no completa información faltante.",
        "## Decisiones / Confirmaciones Humanas Requeridas",
    ])
    decisions = record["human_decisions"]
    lines.extend([f"- {item}" for item in decisions] or ["- No se generaron confirmaciones automáticas."])
    lines.extend([
        "## Próximos pasos internos",
        "Revisión humana de las contradicciones antes de cualquier continuación del expediente.",
        "## Trazabilidad",
        "La trazabilidad documental y las conclusiones profesionales permanecen en los informes y trazas originales de cada especialista.",
        "## Misión recibida",
        mission,
        "## Anexos: informes profesionales originales",
    ])
    for output in outputs:
        lines.extend([f"### {output.agent} — contenido original", output.report])
    return "\n\n".join(lines)
