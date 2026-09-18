"""UI catalog. Not agent execution. Independent of the retired roster module."""
from __future__ import annotations

from corporate_engine.floor import mgc03_floor

COMPANIES = {
    "MGC": {"name": "Miner Global Connect", "status": "Activo"},
    "LNRE": {"name": "Latitud Norte Real Estate", "status": "Estructurado sin pisos habilitados"},
}


def _mgc03_floor_catalog() -> dict:
    floor = mgc03_floor()
    agents = [(floor.manager_id, floor.manager_name, "Operativo")]
    agents.extend((item.specialist_id, item.name, "Operativo") for item in floor.specialists)
    return {
        "company": floor.company_id,
        "name": floor.name,
        "manager": f"{floor.manager_id} | {floor.manager_name}",
        "status": "Operativo",
        "agents": tuple(agents),
        "availability": (
            "GER-MGC-03 recibe la misión en OpenAI Platform y dirige el piso allí. "
            "LNH conserva el expediente, la evidencia y el Human Gate. "
            "La interfaz no elige ni despacha especialistas."
        ),
    }


FLOORS = {
    "MGC-03": _mgc03_floor_catalog(),
    "MGC-05": {
        "company": "MGC",
        "name": "MGC-05 Operaciones y PMO",
        "manager": "Gerente de Piso MGC-05",
        "status": "Retirado del runtime de agentes",
        "agents": (
            ("AGIA-MGC-014", "Control de Proyectos y PMO", "Operativo"),
            ("AGIA-MGC-015", "Procesos, SOP y Mejora Continua", "Operativo"),
            ("AGIA-MGC-016", "Comercio Exterior y Logística", "Operativo"),
        ),
        "availability": (
            "Piloto tecnológico retirado. MGC-05 no ejecuta agentes. "
            "Si se rehabilita, será configuración sobre la plataforma corporativa, no un backend paralelo."
        ),
    },
}


def hierarchy() -> dict:
    return {
        "holding": {"id": "LNH", "name": "Latitud Norte Holding"},
        "companies": [{"id": key, **value} for key, value in COMPANIES.items()],
        "floors": [
            {
                "id": key,
                **value,
                "agents": [{"id": a, "name": n, "status": s} for a, n, s in value["agents"]],
            }
            for key, value in FLOORS.items()
        ],
    }


def floor_ids() -> tuple[str, ...]:
    return tuple(FLOORS)
