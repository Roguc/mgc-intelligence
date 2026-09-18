"""Durable JSON/text writes with Windows-safe replace."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import time

WIN_BUSY = {5, 32}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default=None):
    path = Path(path)
    if not path.is_file():
        return default
    last = None
    for attempt in range(6):
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError) as error:
            last = error
            time.sleep(0.02 * (attempt + 1))
    if not path.is_file():
        return default
    raise last


def write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    last = None
    payload = text if isinstance(text, str) else str(text)
    for attempt in range(8):
        try:
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(path)
            return
        except OSError as error:
            last = error
            if getattr(error, "winerror", None) not in WIN_BUSY and not isinstance(error, PermissionError):
                raise
            time.sleep(0.04 * (attempt + 1))
    if last:
        raise last


def dump_json(path: Path, payload) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=str))
