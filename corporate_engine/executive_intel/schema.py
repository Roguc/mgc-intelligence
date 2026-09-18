"""Shared datum shape for executive indicators."""
from __future__ import annotations

from corporate_engine.executive_intel import (
    STATUS_ACTUALIZADO,
    STATUS_DESACTUALIZADO,
    STATUS_NO_DISPONIBLE,
)
from corporate_engine.store import now


def indicator(
    *,
    key: str,
    label: str,
    value,
    unit: str | None,
    source: str,
    source_url: str | None = None,
    observed_at: str | None = None,
    fetched_at: str | None = None,
    status: str = STATUS_ACTUALIZADO,
    error: str | None = None,
    category: str = "general",
    meta: dict | None = None,
) -> dict:
    return {
        "key": key,
        "label": label,
        "value": value,
        "unit": unit,
        "source": source,
        "source_url": source_url,
        "observed_at": observed_at,
        "fetched_at": fetched_at or now(),
        "status": status if status in {
            STATUS_ACTUALIZADO, STATUS_DESACTUALIZADO, STATUS_NO_DISPONIBLE,
        } else STATUS_NO_DISPONIBLE,
        "error": error,
        "category": category,
        "meta": meta or {},
    }


def unavailable(
    *,
    key: str,
    label: str,
    source: str,
    error: str,
    category: str = "general",
    source_url: str | None = None,
) -> dict:
    return indicator(
        key=key,
        label=label,
        value=None,
        unit=None,
        source=source,
        source_url=source_url,
        status=STATUS_NO_DISPONIBLE,
        error=error,
        category=category,
    )
