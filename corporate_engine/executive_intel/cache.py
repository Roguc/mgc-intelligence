"""File-backed cache for executive intel. No Platform."""
from __future__ import annotations

import time
from pathlib import Path

from corporate_engine.store import dump_json, load_json, now


def cache_root(corporate_root: Path | None = None) -> Path:
    if corporate_root is not None:
        path = Path(corporate_root) / "_executive_intel" / "cache"
    else:
        path = Path(__file__).resolve().parents[2] / "outputs" / "lnh_corporate" / "_executive_intel" / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_path(corporate_root: Path | None, key: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in key)
    return cache_root(corporate_root) / f"{safe}.json"


def read_entry(corporate_root: Path | None, key: str) -> dict | None:
    path = cache_path(corporate_root, key)
    data = load_json(path, default=None)
    return data if isinstance(data, dict) else None


def write_entry(corporate_root: Path | None, key: str, payload: dict) -> dict:
    entry = {
        "key": key,
        "saved_at": now(),
        "saved_epoch": time.time(),
        "payload": payload,
    }
    dump_json(cache_path(corporate_root, key), entry)
    return entry


def age_seconds(entry: dict | None) -> float | None:
    if not entry:
        return None
    epoch = entry.get("saved_epoch")
    if epoch is None:
        return None
    try:
        return max(0.0, time.time() - float(epoch))
    except (TypeError, ValueError):
        return None
