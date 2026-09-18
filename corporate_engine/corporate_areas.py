"""Official corporate destinations — LNH-WF-001 §4 / LNH-DATA-001 governance.

Deterministic catalog only. No cognitive classification.
"""
from __future__ import annotations

CORPORATE_AREAS: dict[str, dict] = {
    "LNH-03": {
        "id": "LNH-03",
        "name": "Corporate Office",
        "competencia": "Gobierno, coordinación, instrucciones, acuerdos, autoridades, asuntos transversales.",
    },
    "LNH-04": {
        "id": "LNH-04",
        "name": "Finanzas Corporativas",
        "competencia": "Caja, presupuesto, capital, TCO, control y riesgo financiero.",
    },
    "LNH-05": {
        "id": "LNH-05",
        "name": "Desarrollo Corporativo",
        "competencia": "Nuevas empresas, inversiones estratégicas, adquisiciones, alianzas, expansión.",
    },
    "LNH-06": {
        "id": "LNH-06",
        "name": "PMO",
        "competencia": "Proyectos, hitos, dependencias, plazos, responsables, evidencia y seguimiento.",
    },
    "LNH-07": {
        "id": "LNH-07",
        "name": "IA y Automatización",
        "competencia": "Arquitectura, IA, tecnología, automatización, integraciones y estándares técnicos.",
    },
    "LNH-08": {
        "id": "LNH-08",
        "name": "Marketing Corporativo",
        "competencia": "Marca, posicionamiento, comunicación y reputación corporativa.",
    },
    "LNH-09": {
        "id": "LNH-09",
        "name": "Business Intelligence",
        "competencia": "Datos, KPIs, calidad, dashboards, reporting e inteligencia corporativa.",
    },
    "LNH-10": {
        "id": "LNH-10",
        "name": "Jurídico y Compliance",
        "competencia": "Contratos, sociedades, regulación, compliance, privacidad, PI y riesgo jurídico.",
    },
}

BUSINESS_SCOPES: frozenset[str] = frozenset({"LNH", "MGC", "LNR", "Holding completo"})

PRESIDENCIA = "Presidencia"
DIRECTORIO = "Directorio"


def area_label(area_id: str) -> str:
    row = CORPORATE_AREAS.get(area_id)
    if not row:
        return area_id
    return f"{row['id']} {row['name']}"


def assert_area(area_id: str | None) -> str | None:
    if area_id is None or area_id == "":
        return None
    key = str(area_id).strip().upper()
    if key not in CORPORATE_AREAS:
        raise ValueError(f"Área corporativa no registrada: {area_id}")
    return key


def list_areas() -> list[dict]:
    return [dict(item) for item in CORPORATE_AREAS.values()]
