"""Santiago weather via Open-Meteo Forecast API (no API key)."""
from __future__ import annotations

from corporate_engine.executive_intel import (
    STATUS_ACTUALIZADO,
    STATUS_DESACTUALIZADO,
    STATUS_NO_DISPONIBLE,
    STALE_WEATHER_SEC,
    TTL_WEATHER_SEC,
)
from corporate_engine.executive_intel import cache as intel_cache
from corporate_engine.executive_intel.http_util import ProviderHttpError, http_get_json
from corporate_engine.executive_intel.schema import unavailable
from corporate_engine.store import now

SOURCE = "Open-Meteo Forecast API"
SOURCE_URL = "https://api.open-meteo.com/v1/forecast"
# Santiago Centro (approx.)
LAT = -33.4489
LON = -70.6693

# WMO weather interpretation codes (subset)
WEATHER_LABELS = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna",
    55: "Llovizna intensa",
    61: "Lluvia ligera",
    63: "Lluvia",
    65: "Lluvia intensa",
    71: "Nieve ligera",
    80: "Chubascos",
    95: "Tormenta",
}


def _label_code(code) -> str:
    try:
        code_i = int(code)
    except (TypeError, ValueError):
        return "Condición desconocida"
    return WEATHER_LABELS.get(code_i, f"Código WMO {code_i}")


def fetch_santiago_weather(*, corporate_root=None, force: bool = False) -> dict:
    cache_key = "weather_santiago"
    entry = intel_cache.read_entry(corporate_root, cache_key)
    age = intel_cache.age_seconds(entry)
    if entry and not force and age is not None and age < TTL_WEATHER_SEC:
        payload = dict(entry.get("payload") or {})
        payload["cache_hit"] = True
        payload["cache_age_sec"] = age
        return payload

    url = (
        f"{SOURCE_URL}?latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"
        "&timezone=America%2FSantiago&forecast_days=5"
    )
    try:
        remote = http_get_json(url)
        current = remote.get("current") or {}
        daily = remote.get("daily") or {}
        times = daily.get("time") or []
        forecast = []
        for idx, day in enumerate(times):
            forecast.append({
                "date": day,
                "weather_code": (daily.get("weather_code") or [None])[idx] if idx < len(daily.get("weather_code") or []) else None,
                "condition": _label_code((daily.get("weather_code") or [None])[idx] if idx < len(daily.get("weather_code") or []) else None),
                "temp_max_c": (daily.get("temperature_2m_max") or [None])[idx] if idx < len(daily.get("temperature_2m_max") or []) else None,
                "temp_min_c": (daily.get("temperature_2m_min") or [None])[idx] if idx < len(daily.get("temperature_2m_min") or []) else None,
                "precipitation_mm": (daily.get("precipitation_sum") or [None])[idx] if idx < len(daily.get("precipitation_sum") or []) else None,
            })
        code = current.get("weather_code")
        payload = {
            "location": "Santiago, Chile",
            "latitude": LAT,
            "longitude": LON,
            "timezone": remote.get("timezone") or "America/Santiago",
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "wind_kmh": current.get("wind_speed_10m"),
                "weather_code": code,
                "condition": _label_code(code),
                "observed_at": current.get("time"),
            },
            "forecast": forecast,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "fetched_at": now(),
            "status": STATUS_ACTUALIZADO,
            "error": None,
            "cache_hit": False,
            "platform_calls": 0,
        }
        if payload["current"]["temperature_c"] is None:
            payload["status"] = STATUS_NO_DISPONIBLE
            payload["error"] = "Open-Meteo no devolvió temperatura actual."
        intel_cache.write_entry(corporate_root, cache_key, payload)
        return payload
    except ProviderHttpError as error:
        if entry and entry.get("payload"):
            stale = dict(entry["payload"])
            stale["status"] = STATUS_DESACTUALIZADO if (age or 0) < STALE_WEATHER_SEC else STATUS_NO_DISPONIBLE
            if stale["status"] == STATUS_NO_DISPONIBLE:
                return {
                    "location": "Santiago, Chile",
                    "current": None,
                    "forecast": [],
                    "source": SOURCE,
                    "source_url": SOURCE_URL,
                    "fetched_at": now(),
                    "status": STATUS_NO_DISPONIBLE,
                    "error": str(error),
                    "cache_hit": True,
                    "platform_calls": 0,
                }
            stale["error"] = f"Usando caché. Último error: {error}"
            stale["cache_hit"] = True
            stale["cache_age_sec"] = age
            return stale
        return {
            "location": "Santiago, Chile",
            "current": None,
            "forecast": [],
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "fetched_at": now(),
            "status": STATUS_NO_DISPONIBLE,
            "error": str(error),
            "cache_hit": False,
            "platform_calls": 0,
        }
