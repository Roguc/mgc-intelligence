"""Assemble executive intel board for Mission Control Presidencia."""
from __future__ import annotations

from pathlib import Path

from corporate_engine.executive_intel.chile_indicators import fetch_chile_economy, fetch_copper_market
from corporate_engine.executive_intel.weather import fetch_santiago_weather
from corporate_engine.store import now


def executive_board(corporate_root: Path | None = None, *, force: bool = False) -> dict:
    weather = fetch_santiago_weather(corporate_root=corporate_root, force=force)
    economy = fetch_chile_economy(corporate_root=corporate_root, force=force)
    markets = fetch_copper_market(corporate_root=corporate_root, force=force)
    return {
        "block": "F2C-1",
        "title": "Información ejecutiva — Presidencia",
        "generated_at": now(),
        "weather": weather,
        "economy": economy,
        "markets": markets,
        "sources": [
            {"name": weather.get("source"), "url": weather.get("source_url"), "domain": "clima"},
            {"name": economy.get("source"), "url": economy.get("source_url"), "domain": "economia"},
            {"name": markets.get("source"), "url": markets.get("source_url"), "domain": "mercados"},
        ],
        "notes": [
            "Sin análisis inteligente ni recomendaciones en backend.",
            "Estados: ACTUALIZADO | DESACTUALIZADO | NO_DISPONIBLE.",
            "BCCh BDE API opcional (requiere token); mindicador.cl usado como fuente pública verificada.",
        ],
        "platform_calls": 0,
    }
