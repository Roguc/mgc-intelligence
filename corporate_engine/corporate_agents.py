"""LNH corporate agent bindings — Platform configuration, not a local runtime.

IDs were inventoried from OpenAI Agents API GET /v1/agents (official listing).
Override any ID with environment variable LNH_0N_AGENT_ID without committing secrets.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from corporate_engine.corporate_areas import CORPORATE_AREAS, assert_area
from corporate_engine.platform import windows_user_env

# Operational labels for Mission Control (local evidence only — never invent Platform state).
STATUS_CONFIGURADO = "CONFIGURADO"
STATUS_CONECTADO = "CONECTADO"
STATUS_DISPONIBLE = "DISPONIBLE"
STATUS_BLOQUEADO_CREDITOS = "BLOQUEADO POR CRÉDITOS"
STATUS_EN_EJECUCION = "EN EJECUCIÓN"
STATUS_ERROR = "ERROR"
STATUS_WORKFLOW_PENDIENTE = "WORKFLOW PENDIENTE DE INTEGRACIÓN"


@dataclass(frozen=True)
class CorporateAgentBinding:
    area_id: str
    name: str
    platform_agent_id: str
    environment: dict


# Official Platform agent IDs (not API keys). Source: OpenAI Agents list.
_PLATFORM_DEFAULTS: dict[str, str] = {
    "LNH-03": "agent_a616c9a3345546f2a4796977c7e730fc2a70e73bd9494446a9",
    "LNH-04": "agent_ae2dc1212ca34f989795800cc0787b2ad49536788f6a4e0f8e",
    "LNH-05": "agent_9870fb6abfb24b5fb7d430583953c410b028d7d5ad8d438ab6",
    "LNH-06": "agent_3e1258c17b9744dfb3a00dc8052cfb6edfefccf761664f22be",
    "LNH-07": "agent_0789f22d80294d0a9a8f4be6bd3dd4636fca96ea48b4403b92",
    "LNH-08": "agent_c2c77d6b3fd54423803ac6ca18faa5d40d5c291d92a040e89a",
    "LNH-09": "agent_7ac8ce2461d448a4b07bb81b14cddd7033846efb51fd437b8c",
    "LNH-10": "agent_57695ca7416f4d859c743d6e2b39535248694ee552e543ceb9",
}

# Directors exist in Platform; workflow/backend integration is not Block 3.
# Do not invent platform_agent_id here — only declare known governance identity.
DIRECTORS: tuple[dict, ...] = (
    {"id": "DIR-01", "name": "DIR-01 | Director IA — Estrategia y Crecimiento", "mandate": "Estrategia y Crecimiento", "role": "director_ia"},
    {"id": "DIR-02", "name": "DIR-02 | Director IA — Finanzas, Caja y Capital", "mandate": "Finanzas, Caja y Capital", "role": "director_ia"},
    {"id": "DIR-03", "name": "DIR-03 | Director IA — Riesgo, Compliance y Patrimonio", "mandate": "Riesgo, Compliance y Patrimonio", "role": "director_ia"},
    {"id": "DIR-04", "name": "DIR-04 | Director IA — Operaciones, Sistemas y Tecnología", "mandate": "Operaciones, Sistemas y Tecnología", "role": "director_ia"},
    {"id": "DIR-05", "name": "DIR-05 | Director IA — Empresas, Mercado e Inversiones", "mandate": "Empresas, Mercado e Inversiones", "role": "director_ia"},
)


def _env_override(area_id: str) -> str:
    key = area_id.replace("-", "_") + "_AGENT_ID"  # LNH_03_AGENT_ID
    return (windows_user_env(key) or os.getenv(key) or "").strip()


def truncate_agent_id(platform_agent_id: str | None) -> str | None:
    if not platform_agent_id:
        return None
    value = str(platform_agent_id)
    if len(value) <= 22:
        return value
    return f"{value[:14]}…{value[-8:]}"


def binding_for(area_id: str) -> CorporateAgentBinding:
    area = assert_area(area_id)
    if area not in CORPORATE_AREAS:
        raise KeyError(f"Área corporativa no registrada: {area_id}")
    platform_id = _env_override(area) or _PLATFORM_DEFAULTS.get(area) or ""
    if not platform_id:
        raise KeyError(f"Falta platform agent_id para {area}")
    meta = CORPORATE_AREAS[area]
    return CorporateAgentBinding(
        area_id=area,
        name=meta["name"],
        platform_agent_id=platform_id,
        environment={"type": "openai_hosted"},
    )


def mapping_status() -> list[dict]:
    rows = []
    for area_id, meta in CORPORATE_AREAS.items():
        override = _env_override(area_id)
        default = _PLATFORM_DEFAULTS.get(area_id) or ""
        platform_id = override or default
        available = bool(platform_id)
        rows.append({
            "area_id": area_id,
            "name": meta["name"],
            "platform_agent_id": platform_id or None,
            "platform_agent_id_truncated": truncate_agent_id(platform_id) if available else None,
            "source": "env" if override else ("platform_inventory" if default else None),
            "available": available,
            "config_status": STATUS_CONFIGURADO if available else "NO CONFIGURADO",
            "connection_status": STATUS_CONECTADO if available else "NO CONECTADO",
            "backend_connected": available,
        })
    return rows


# Official Platform Director agent IDs (not API keys).
# Source: OpenAI Agents API GET /v1/agents (consulta de listado, sin sesiones ni inferencia).
_DIRECTOR_PLATFORM_DEFAULTS: dict[str, str] = {
    "DIR-01": "agent_ac9f8c9daa54466cafcb0147459b76c2546e0033de88483d91",
    "DIR-02": "agent_91d4919f473e43a594bf77b2de019e3c12a4bf5c5476498596",
    "DIR-03": "agent_db69c700b94a4f388316c1d980296a6f47304c34ccf04f7b91",
    "DIR-04": "agent_8c7e3a65e17346e8868fbf0cb7ea5a63303661bcb2be4da499",
    "DIR-05": "agent_9c23e1bc3dd14c5fb38e97cd75b8b5ecf77bd5111cd24d09b3",
}


def _director_env_override(director_id: str) -> str:
    key = director_id.replace("-", "_") + "_AGENT_ID"  # DIR_01_AGENT_ID
    return (windows_user_env(key) or os.getenv(key) or "").strip()


def binding_for_director(director_id: str) -> CorporateAgentBinding:
    meta = next((d for d in DIRECTORS if d["id"] == director_id), None)
    if not meta:
        raise KeyError(f"Director no registrado: {director_id}")
    platform_id = _director_env_override(director_id) or _DIRECTOR_PLATFORM_DEFAULTS.get(director_id) or ""
    if not platform_id:
        raise KeyError(f"Falta platform agent_id para {director_id} (configure DIR_0N_AGENT_ID).")
    return CorporateAgentBinding(
        area_id=director_id,
        name=meta["name"],
        platform_agent_id=platform_id,
        environment={"type": "openai_hosted"},
    )


def missing_agent_ids() -> list[str]:
    return [row["area_id"] for row in mapping_status() if not row["available"]]


def missing_director_ids() -> list[str]:
    return [row["id"] for row in director_status() if not row.get("available")]


def director_status(*, credit_block_observed: bool = False) -> list[dict]:
    """Directors CONFIGURADO + CONECTADO; workflow Fase 2A. Env override: DIR_0N_AGENT_ID."""
    rows = []
    for item in DIRECTORS:
        override = _director_env_override(item["id"])
        default = _DIRECTOR_PLATFORM_DEFAULTS.get(item["id"]) or ""
        platform_id = override or default
        available = bool(platform_id)
        operational = (
            STATUS_BLOQUEADO_CREDITOS if (available and credit_block_observed)
            else (STATUS_DISPONIBLE if available else "NO CONFIGURADO")
        )
        rows.append({
            "id": item["id"],
            "code": item["id"],
            "name": item["name"],
            "mandate": item["mandate"],
            "role": item.get("role") or "director_ia",
            "platform_agent_id": platform_id or None,
            "platform_agent_id_truncated": truncate_agent_id(platform_id) if available else None,
            "available": available,
            "config_status": STATUS_CONFIGURADO if available else "NO CONFIGURADO",
            "connection_status": STATUS_CONECTADO if available else "NO CONECTADO",
            "workflow_status": "INTEGRADO FASE 2A",
            "operational_status": operational,
            "backend_connected": available,
            "source": "env" if override else ("platform_inventory" if default else None),
            "note": "agent_id inventariado desde OpenAI Agents API (GET /v1/agents)." if available else "Falta agent_id.",
        })
    return rows


def registry_fase2a(*, credit_block_observed: bool = False) -> list[dict]:
    """Exact 13 Fase 2A agents: LNH-03..10 + DIR-01..05."""
    rows = []
    for a in mapping_status():
        rows.append({
            "code": a["area_id"],
            "name": a["name"],
            "role": "agente_corporativo",
            "platform_agent_id": a.get("platform_agent_id"),
            "platform_agent_id_truncated": a.get("platform_agent_id_truncated"),
            "config_status": a.get("config_status"),
            "connection_status": a.get("connection_status"),
            "integration_available": a.get("available"),
            "kind": "corporate",
        })
    for d in director_status(credit_block_observed=credit_block_observed):
        rows.append({
            "code": d["id"],
            "name": d["name"],
            "role": d.get("role") or "director_ia",
            "platform_agent_id": d.get("platform_agent_id"),
            "platform_agent_id_truncated": d.get("platform_agent_id_truncated"),
            "config_status": d.get("config_status"),
            "connection_status": d.get("connection_status"),
            "workflow_status": d.get("workflow_status"),
            "operational_status": d.get("operational_status"),
            "integration_available": d.get("available"),
            "kind": "director",
        })
    return rows


def _scan_area_activity(corporate_root: Path | None) -> dict[str, dict]:
    """Local expediente evidence only. Does not call Platform."""
    stats = {
        area_id: {
            "active_tasks": 0,
            "related_expedientes": [],
            "seen_credit_block": False,
            "seen_running": False,
            "seen_error": False,
            "last_error_kind": None,
        }
        for area_id in CORPORATE_AREAS
    }
    if not corporate_root:
        return stats
    root = Path(corporate_root)
    if not root.is_dir():
        return stats
    from corporate_engine import corporate_expediente as corp

    for summary in corp.list_expedientes(root):
        expediente_id = summary.get("expediente_id")
        if not expediente_id:
            continue
        try:
            master = corp.load_expediente(corp.directory(root, expediente_id))
        except Exception:
            continue
        for task in master.get("encargos") or []:
            area = task.get("assigned_to")
            if area not in stats:
                continue
            row = stats[area]
            if expediente_id not in row["related_expedientes"]:
                row["related_expedientes"].append(expediente_id)
            status = (task.get("status") or "").upper()
            if status in {"PENDIENTE", "EN_CURSO", "BLOQUEADO"}:
                row["active_tasks"] += 1
            if status == "EN_CURSO":
                row["seen_running"] = True
            kind = (task.get("last_error_kind") or "").upper()
            if kind == "CREDIT_BALANCE_EXHAUSTED" or "CREDIT" in kind:
                row["seen_credit_block"] = True
                row["last_error_kind"] = task.get("last_error_kind")
            elif task.get("last_error") and status != "ENTREGADO":
                row["seen_error"] = True
                row["last_error_kind"] = task.get("last_error_kind") or "ERROR"
        for session in master.get("platform_sessions") or []:
            area = session.get("agent_id")
            if area not in stats:
                continue
            kind = (session.get("error_kind") or "").upper()
            if kind == "CREDIT_BALANCE_EXHAUSTED" or "CREDIT" in kind:
                stats[area]["seen_credit_block"] = True
                stats[area]["last_error_kind"] = session.get("error_kind")
            if (session.get("status") or "").lower() in {"running", "starting", "submitted"}:
                stats[area]["seen_running"] = True
    return stats


def _operational_status(activity: dict, *, credit_block_any: bool) -> str:
    if activity.get("seen_running"):
        return STATUS_EN_EJECUCION
    # Account-level credit exhaustion blocks cognitive completion for all mapped agents.
    if activity.get("seen_credit_block") or credit_block_any:
        return STATUS_BLOQUEADO_CREDITOS
    if activity.get("seen_error"):
        return STATUS_ERROR
    return STATUS_DISPONIBLE


def status_board(corporate_root: Path | None = None) -> dict:
    """Mission Control board: mapping + local operational evidence. No Platform calls."""
    activity = _scan_area_activity(corporate_root)
    credit_block_any = any(row.get("seen_credit_block") for row in activity.values())
    agents = []
    for base in mapping_status():
        area = base["area_id"]
        act = activity.get(area) or {}
        operational = (
            _operational_status(act, credit_block_any=credit_block_any)
            if base["available"]
            else "NO CONFIGURADO"
        )
        agents.append({
            **base,
            "operational_status": operational,
            "active_tasks": act.get("active_tasks") or 0,
            "related_expedientes": list(act.get("related_expedientes") or []),
            "related_expedientes_count": len(act.get("related_expedientes") or []),
            "last_error_kind": act.get("last_error_kind"),
        })
    return {
        "agents": agents,
        "directors": director_status(credit_block_observed=credit_block_any),
        "registry_fase2a": registry_fase2a(credit_block_observed=credit_block_any),
        "registry_count": 13,
        "directors_ids_missing": missing_director_ids(),
        "credit_block_observed": credit_block_any,
        "platform_calls": 0,
        "fase": "2A",
    }
