"""Deterministic corporate routing — LNH-WF-001 §3.

Uses only structured fields (tipo, ambito, prioridad, áreas explícitas,
flags registradas). Never interprets free-text instrucción.
"""
from __future__ import annotations

from corporate_engine.corporate_areas import (
    CORPORATE_AREAS,
    DIRECTORIO,
    PRESIDENCIA,
    assert_area,
    area_label,
)


def _dest(area_id: str, role: str) -> dict:
    meta = CORPORATE_AREAS[area_id]
    return {
        "assigned_to": area_id,
        "label": area_label(area_id),
        "name": meta["name"],
        "role": role,
        "deliverable_type": "informe",
    }


def plan_routing(
    *,
    tipo: str,
    ambito: str,
    prioridad: str,
    area_competente: str | None = None,
    area_solicitante: str | None = None,
    area_responsable: str | None = None,
    funcion_propietaria: str | None = None,
    obligacion_contractual: bool | None = None,
    remitir_directorio: bool | None = None,
) -> dict:
    """Return a deterministic routing plan. Does not persist."""
    competent = assert_area(area_competente)
    solicitante = assert_area(area_solicitante)
    responsable = assert_area(area_responsable)
    propietaria = assert_area(funcion_propietaria)

    destinations: list[dict] = []
    requires_classification = False
    classification_reason = None
    directorio = {
        "candidate": False,
        "mandatory_by_rule": False,
        "activated": False,
        "note": "Directorio no se activa en Bloque 2; solo se marca candidatura/regla.",
    }
    next_gate = PRESIDENCIA
    rule_id = f"WF-001/{tipo}"

    if tipo == "Otro":
        requires_classification = True
        classification_reason = "Tipo Otro: LNH-03 Corporate Office clasifica en Platform."
        destinations = [_dest("LNH-03", "clasificacion")]
        rule_id = "WF-001/Otro→LNH-03"

    elif tipo == "Inversión":
        destinations = [
            _dest("LNH-05", "analisis_estrategico"),
            _dest("LNH-04", "analisis_financiero"),
            _dest("LNH-10", "analisis_juridico"),
        ]
        directorio["candidate"] = True
        directorio["mandatory_by_rule"] = True
        directorio["note"] = (
            "Inversión: candidata/obligatoria a Directorio según LNH-WF-001. "
            "Sin umbrales financieros inventados."
        )
        next_gate = DIRECTORIO
        rule_id = "WF-001/Inversión→LNH-05+LNH-04+LNH-10→Directorio→Presidencia"

    elif tipo == "Proyecto":
        destinations = [_dest("LNH-06", "pmo")]
        if propietaria:
            destinations.append(_dest(propietaria, "funcion_propietaria"))
        else:
            requires_classification = True
            classification_reason = (
                "Proyecto requiere función propietaria estructurada; "
                "sin ella LNH-03 clasifica el propietario."
            )
            destinations.append(_dest("LNH-03", "clasificacion_propietario"))
        rule_id = "WF-001/Proyecto→LNH-06+propietaria"

    elif tipo == "Compra":
        destinations = [_dest("LNH-04", "control_financiero")]
        if solicitante:
            destinations.append(_dest(solicitante, "area_solicitante"))
        else:
            requires_classification = True
            classification_reason = (
                "Compra requiere área solicitante estructurada; "
                "sin ella LNH-03 clasifica el solicitante."
            )
            destinations.append(_dest("LNH-03", "clasificacion_solicitante"))
        if obligacion_contractual is True:
            destinations.append(_dest("LNH-10", "obligacion_contractual"))
        rule_id = "WF-001/Compra→LNH-04+solicitante[+LNH-10]"

    elif tipo == "Propuesta":
        if competent:
            destinations = [_dest(competent, "area_competente")]
            next_gate = PRESIDENCIA
            directorio["candidate"] = bool(remitir_directorio)
            rule_id = "WF-001/Propuesta→area→Presidencia"
        else:
            requires_classification = True
            classification_reason = "Propuesta sin área competente estructurada → LNH-03."
            destinations = [_dest("LNH-03", "clasificacion")]
            rule_id = "WF-001/Propuesta→clasificacion"

    elif tipo == "Decisión requerida":
        if competent:
            destinations = [_dest(competent, "area_competente")]
            directorio["candidate"] = True
            directorio["note"] = (
                "Decisión requerida: posible Directorio cuando corresponda; "
                "sin umbrales inventados. Presidencia decide gates."
            )
            next_gate = DIRECTORIO if remitir_directorio else PRESIDENCIA
            if remitir_directorio:
                directorio["mandatory_by_rule"] = False
                directorio["candidate"] = True
            rule_id = "WF-001/Decision→area→posible_Directorio→Presidencia"
        else:
            requires_classification = True
            classification_reason = "Decisión requerida sin área competente → LNH-03."
            destinations = [_dest("LNH-03", "clasificacion")]
            rule_id = "WF-001/Decision→clasificacion"

    elif tipo == "Investigación":
        if competent:
            destinations = [_dest(competent, "area_competente")]
            next_gate = PRESIDENCIA
            rule_id = "WF-001/Investigacion→area→Presidencia"
        else:
            requires_classification = True
            classification_reason = "Investigación sin área competente → LNH-03."
            destinations = [_dest("LNH-03", "clasificacion")]
            rule_id = "WF-001/Investigacion→clasificacion"

    elif tipo == "Instrucción":
        owner = responsable or competent
        if owner:
            destinations = [_dest(owner, "area_responsable")]
            next_gate = PRESIDENCIA
            rule_id = "WF-001/Instruccion→area→seguimiento"
        else:
            requires_classification = True
            classification_reason = "Instrucción sin área responsable estructurada → LNH-03."
            destinations = [_dest("LNH-03", "clasificacion")]
            rule_id = "WF-001/Instruccion→clasificacion"

    else:
        requires_classification = True
        classification_reason = "Tipo no mapeado de forma determinística → LNH-03."
        destinations = [_dest("LNH-03", "clasificacion")]
        rule_id = "WF-001/fallback→LNH-03"

    # Deduplicate destinations preserving order
    seen = set()
    unique = []
    for item in destinations:
        key = item["assigned_to"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    urgency = {
        "prioridad": prioridad,
        "escalamiento": {"P0": "inmediato", "P1": "alto", "P2": "normal", "P3": "ordinario"}.get(prioridad, "normal"),
        "note": "Prioridad controla urgencia/orden/escalamiento; no competencia ni omisión de gates.",
    }

    return {
        "rule_id": rule_id,
        "tipo": tipo,
        "ambito": ambito,
        "prioridad": prioridad,
        "destinations": unique,
        "requires_classification": requires_classification,
        "classification_reason": classification_reason,
        "classification_owner": "LNH-03" if requires_classification else None,
        "directorio": directorio,
        "next_gate": next_gate,
        "presidency": PRESIDENCIA,
        "structured_inputs": {
            "area_competente": competent,
            "area_solicitante": solicitante,
            "area_responsable": responsable,
            "funcion_propietaria": propietaria,
            "obligacion_contractual": obligacion_contractual,
            "remitir_directorio": remitir_directorio,
        },
        "urgency": urgency,
        "cognitive": False,
        "platform_invoked": False,
    }
