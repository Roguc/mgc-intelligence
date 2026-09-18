"""Fase 2C — Executive information layer (2C-1 clima/economía + 2C-2 noticias).

Backend only fetches, normalizes, caches and presents. No AI analysis.
"""
from __future__ import annotations

STATUS_ACTUALIZADO = "ACTUALIZADO"
STATUS_DESACTUALIZADO = "DESACTUALIZADO"
STATUS_NO_DISPONIBLE = "NO_DISPONIBLE"

STATUSES = frozenset({STATUS_ACTUALIZADO, STATUS_DESACTUALIZADO, STATUS_NO_DISPONIBLE})

# Cache TTLs (seconds) — 2C-1
TTL_WEATHER_SEC = 30 * 60
TTL_DAILY_INDICATOR_SEC = 6 * 60 * 60
TTL_MONTHLY_INDICATOR_SEC = 24 * 60 * 60
TTL_MARKET_SEC = 6 * 60 * 60

# Soft staleness: still show cached value but mark DESACTUALIZADO — 2C-1
STALE_WEATHER_SEC = 3 * 60 * 60
STALE_DAILY_SEC = 36 * 60 * 60
STALE_MONTHLY_SEC = 10 * 24 * 60 * 60
STALE_MARKET_SEC = 36 * 60 * 60

# 2C-2 news
TTL_NEWS_SEC = 45 * 60
STALE_NEWS_SEC = 6 * 60 * 60
NEWS_CATEGORIES = ("nacional", "internacional", "mineria", "inmobiliario")
