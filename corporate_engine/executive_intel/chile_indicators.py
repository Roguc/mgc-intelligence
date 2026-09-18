"""Chile economic + copper indicators via mindicador.cl (public API).

Series used (verified live):
- uf, utm, dolar, ipc, tpm, libra_cobre

mindicador.cl republishes official Chilean statistical series for public consumption.
BCCh official BDE API remains optional when BCCH_API_TOKEN is configured later.
"""
from __future__ import annotations

from corporate_engine.executive_intel import (
    STATUS_ACTUALIZADO,
    STATUS_DESACTUALIZADO,
    STATUS_NO_DISPONIBLE,
    STALE_DAILY_SEC,
    STALE_MARKET_SEC,
    STALE_MONTHLY_SEC,
    TTL_DAILY_INDICATOR_SEC,
    TTL_MARKET_SEC,
    TTL_MONTHLY_INDICATOR_SEC,
)
from corporate_engine.executive_intel import cache as intel_cache
from corporate_engine.executive_intel.http_util import ProviderHttpError, http_get_json
from corporate_engine.executive_intel.schema import indicator, unavailable
from corporate_engine.store import now

SOURCE = "mindicador.cl"
SOURCE_URL = "https://mindicador.cl/api"
COPPER_URL = "https://mindicador.cl/api/libra_cobre"

# key -> (label, unit override or None, category, ttl, stale)
SERIES = {
    "uf": ("UF", "CLP", "economy", TTL_DAILY_INDICATOR_SEC, STALE_DAILY_SEC),
    "utm": ("UTM", "CLP", "economy", TTL_MONTHLY_INDICATOR_SEC, STALE_MONTHLY_SEC),
    "dolar": ("USD/CLP (dólar observado)", "CLP", "economy", TTL_DAILY_INDICATOR_SEC, STALE_DAILY_SEC),
    "ipc": ("IPC (var. mensual)", "%", "economy", TTL_MONTHLY_INDICATOR_SEC, STALE_MONTHLY_SEC),
    "tpm": ("TPM", "%", "economy", TTL_DAILY_INDICATOR_SEC, STALE_DAILY_SEC),
}


def fetch_chile_economy(*, corporate_root=None, force: bool = False) -> dict:
    cache_key = "chile_economy_mindicador"
    entry = intel_cache.read_entry(corporate_root, cache_key)
    age = intel_cache.age_seconds(entry)
    if entry and not force and age is not None and age < TTL_DAILY_INDICATOR_SEC:
        payload = dict(entry.get("payload") or {})
        payload["cache_hit"] = True
        payload["cache_age_sec"] = age
        return payload

    try:
        remote = http_get_json(SOURCE_URL)
        indicators = []
        for key, (label, unit_default, category, _ttl, _stale) in SERIES.items():
            row = remote.get(key)
            if not isinstance(row, dict) or row.get("valor") is None:
                indicators.append(unavailable(
                    key=key, label=label, source=SOURCE, source_url=SOURCE_URL,
                    error=f"Serie {key} no disponible en mindicador.cl",
                    category=category,
                ))
                continue
            indicators.append(indicator(
                key=key,
                label=label,
                value=row.get("valor"),
                unit=row.get("unidad_medida") or unit_default,
                source=SOURCE,
                source_url=SOURCE_URL,
                observed_at=row.get("fecha"),
                status=STATUS_ACTUALIZADO,
                category=category,
                meta={"codigo": row.get("codigo"), "nombre": row.get("nombre")},
            ))
        payload = {
            "indicators": indicators,
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "fetched_at": now(),
            "status": STATUS_ACTUALIZADO if any(i.get("value") is not None for i in indicators) else STATUS_NO_DISPONIBLE,
            "error": None,
            "cache_hit": False,
            "platform_calls": 0,
        }
        intel_cache.write_entry(corporate_root, cache_key, payload)
        return payload
    except ProviderHttpError as error:
        if entry and entry.get("payload"):
            stale = dict(entry["payload"])
            stale["status"] = STATUS_DESACTUALIZADO if (age or 0) < STALE_DAILY_SEC else STATUS_NO_DISPONIBLE
            stale["error"] = f"Usando caché. Último error: {error}"
            stale["cache_hit"] = True
            stale["cache_age_sec"] = age
            for item in stale.get("indicators") or []:
                if item.get("value") is not None:
                    item["status"] = STATUS_DESACTUALIZADO
            return stale
        return {
            "indicators": [
                unavailable(key=k, label=SERIES[k][0], source=SOURCE, source_url=SOURCE_URL,
                            error=str(error), category=SERIES[k][2])
                for k in SERIES
            ],
            "source": SOURCE,
            "source_url": SOURCE_URL,
            "fetched_at": now(),
            "status": STATUS_NO_DISPONIBLE,
            "error": str(error),
            "cache_hit": False,
            "platform_calls": 0,
        }


def fetch_copper_market(*, corporate_root=None, force: bool = False) -> dict:
    """Copper reference: libra de cobre (USD/lb) from mindicador.cl — Chile mining standard."""
    cache_key = "market_copper_libra"
    entry = intel_cache.read_entry(corporate_root, cache_key)
    age = intel_cache.age_seconds(entry)
    if entry and not force and age is not None and age < TTL_MARKET_SEC:
        payload = dict(entry.get("payload") or {})
        payload["cache_hit"] = True
        payload["cache_age_sec"] = age
        return payload

    try:
        remote = http_get_json(COPPER_URL)
        serie = remote.get("serie") if isinstance(remote, dict) else None
        latest = serie[0] if isinstance(serie, list) and serie else None
        if not isinstance(latest, dict) or latest.get("valor") is None:
            payload = {
                "indicators": [unavailable(
                    key="libra_cobre",
                    label="Cobre (libra)",
                    source=SOURCE,
                    source_url=COPPER_URL,
                    error="Serie libra_cobre sin valor",
                    category="markets",
                )],
                "justification": (
                    "Referencia de precio del cobre relevante para MGC (minería) "
                    "y el holding LNH; serie pública mindicador.cl libra_cobre."
                ),
                "source": SOURCE,
                "source_url": COPPER_URL,
                "fetched_at": now(),
                "status": STATUS_NO_DISPONIBLE,
                "error": "Sin valor",
                "cache_hit": False,
                "platform_calls": 0,
            }
            return payload
        item = indicator(
            key="libra_cobre",
            label="Cobre (libra)",
            value=latest.get("valor"),
            unit=remote.get("unidad_medida") or "USD/lb",
            source=SOURCE,
            source_url=COPPER_URL,
            observed_at=latest.get("fecha"),
            status=STATUS_ACTUALIZADO,
            category="markets",
            meta={"nombre": remote.get("nombre"), "codigo": remote.get("codigo")},
        )
        payload = {
            "indicators": [item],
            "justification": (
                "Precio de la libra de cobre — referencia de mercado para actividades "
                "mineras documentadas de MGC / Latitud Norte Holding."
            ),
            "source": SOURCE,
            "source_url": COPPER_URL,
            "fetched_at": now(),
            "status": STATUS_ACTUALIZADO,
            "error": None,
            "cache_hit": False,
            "platform_calls": 0,
        }
        intel_cache.write_entry(corporate_root, cache_key, payload)
        return payload
    except ProviderHttpError as error:
        if entry and entry.get("payload"):
            stale = dict(entry["payload"])
            stale["status"] = STATUS_DESACTUALIZADO if (age or 0) < STALE_MARKET_SEC else STATUS_NO_DISPONIBLE
            stale["error"] = f"Usando caché. Último error: {error}"
            stale["cache_hit"] = True
            for item in stale.get("indicators") or []:
                if item.get("value") is not None:
                    item["status"] = STATUS_DESACTUALIZADO
            return stale
        return {
            "indicators": [unavailable(
                key="libra_cobre", label="Cobre (libra)", source=SOURCE,
                source_url=COPPER_URL, error=str(error), category="markets",
            )],
            "justification": (
                "Referencia cobre para MGC; fuente no disponible en esta consulta."
            ),
            "source": SOURCE,
            "source_url": COPPER_URL,
            "fetched_at": now(),
            "status": STATUS_NO_DISPONIBLE,
            "error": str(error),
            "cache_hit": False,
            "platform_calls": 0,
        }
