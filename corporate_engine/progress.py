"""Live progress for Mission Control. Same filename as the historical adapter."""
from __future__ import annotations

from pathlib import Path
import threading

from corporate_engine.store import dump_json, load_json, now

NAME = "operational_progress.json"
MAX_EVENTS = 80
_LOCK = threading.Lock()


def load(case: Path) -> dict:
    return load_json(Path(case) / NAME, {}) or {}


def emit(case, kind: str, summary: str, **fields) -> dict:
    root = Path(case)
    if not root.exists():
        return {}
    with _LOCK:
        current = load(root)
        events = list(current.get("events") or [])
        event = {"at": now(), "kind": kind, "summary": summary,
                 **{key: value for key, value in fields.items() if value is not None}}
        events.append(event)
        payload = {
            "updated_at": event["at"],
            "phase": fields.get("phase") or current.get("phase") or kind,
            "actor": fields.get("actor") or current.get("actor"),
            "snapshot": dict(current.get("snapshot") or {}),
            "events": events[-MAX_EVENTS:],
        }
        dump_json(root / NAME, payload)
        return payload
