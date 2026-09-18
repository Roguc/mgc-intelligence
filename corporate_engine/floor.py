"""Floor catalog. Platform agent IDs are LNH configuration, not a local runtime."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistBinding:
    specialist_id: str
    name: str
    capabilities: tuple[str, ...]
    platform_agent_id: str
    environment: dict
    discipline: str = ""


@dataclass(frozen=True)
class FloorBinding:
    floor_id: str
    name: str
    company_id: str
    manager_id: str
    manager_name: str
    manager_platform_agent_id: str
    manager_session_env: str
    manager_environment: dict
    specialists: tuple[SpecialistBinding, ...]
    executable: bool = True

    def specialist(self, specialist_id: str) -> SpecialistBinding:
        for item in self.specialists:
            if item.specialist_id == specialist_id:
                return item
        raise KeyError(specialist_id)


def mgc03_floor() -> FloorBinding:
    return FloorBinding(
        floor_id="MGC-03",
        name="MGC-03 Investigación y Análisis de Mercados",
        company_id="MGC",
        manager_id="GER-MGC-03",
        manager_name="Gerente IA de Inteligencia de Mercado",
        manager_platform_agent_id="agent_4d77bd5d9d07456099210b3bc795f18661795026c1d34bc387",
        manager_session_env="OPENAI_AGENTS_SESSION_ID",
        manager_environment={"type": "openai_hosted"},
        specialists=(
            SpecialistBinding(
                "AGIA-MGC-005", "Geólogo IA de Proyectos y Activos Mineros",
                ("geología", "proyectos mineros", "activos mineros", "yacimientos", "pertenencias", "recursos y reservas"),
                "agent_d635217631444b58a4f670af801826caecd6a126d8aa42cb95",
                {"type": "openai_hosted"}, "Geología de proyectos y activos mineros.",
            ),
            SpecialistBinding(
                "AGIA-MGC-006", "Analista IA de Commodities, Oferta y Demanda",
                ("commodities", "oferta y demanda", "balances de mercado", "precios", "stocks", "curvas de precio"),
                "agent_706f5dc1b5f64b3290d09a8241d51132a4cf58883ae04119a4",
                {"type": "openai_hosted"}, "Commodities, oferta, demanda y precios.",
            ),
            SpecialistBinding(
                "AGIA-MGC-007", "Investigador IA de Mercado y Competencia Minera",
                ("mercado", "competencia", "vendedores", "compradores", "inteligencia de mercado"),
                "agent_5f1d26bdbf894a13b92226c29b3405a52c9b8a71867c41ae8b",
                {"type": "openai_hosted"}, "Investigación de mercado y competencia minera.",
            ),
            SpecialistBinding(
                "AGIA-MGC-008", "Analista IA de Riesgo País, Regulación y Comercio Internacional",
                ("riesgo país", "regulación minera", "comercio internacional", "aranceles", "sanciones", "permisos y royalties"),
                "agent_4d77856eb1b542b3ab7be04a32a6d014be3f452b83f648a493",
                {"type": "openai_hosted"}, "Riesgo país, regulación y comercio internacional.",
            ),
        ),
        executable=True,
    )


def get_floor(floor_id: str) -> FloorBinding:
    if floor_id != "MGC-03":
        raise KeyError(f"Piso {floor_id} no está en el motor corporativo.")
    return mgc03_floor()
