"""Mission registry for the corporate engine."""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re
import shutil
from typing import Iterable

from corporate_engine.contracts import mission as make_mission
from corporate_engine.floor import get_floor
from corporate_engine.store import dump_json, now


def case_id_for(mission: str) -> str:
    slug = re.sub("[^a-z0-9]+", "-", mission.casefold()).strip("-")[:24] or "mision"
    return f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{slug}"


def persist_documents(case: Path, paths: Iterable[Path]) -> list[dict]:
    target_dir = case / "documents"
    target_dir.mkdir(parents=True, exist_ok=True)
    documents = []
    for source in paths:
        target = target_dir / source.name
        number = 2
        while target.exists():
            target = target_dir / f"{source.stem}-{number}{source.suffix}"
            number += 1
        shutil.copy2(source, target)
        documents.append({
            "name": target.name,
            "original_name": source.name,
            "path": str(target),
            "sha256": sha256(target.read_bytes()).hexdigest(),
        })
    return documents


def open_case(root: Path, *, floor_id: str, mission_text: str, paths: Iterable[Path] = ()) -> Path:
    floor = get_floor(floor_id)
    if not mission_text or not str(mission_text).strip():
        raise ValueError("La misión es obligatoria.")
    case_id = case_id_for(mission_text)
    case = Path(root) / case_id
    if case.exists():
        raise FileExistsError(case)
    case.mkdir(parents=True, exist_ok=False)
    documents = persist_documents(case, paths)
    record = make_mission(
        case_id=case_id, floor_id=floor.floor_id, manager_id=floor.manager_id,
        text=mission_text.strip(), documents=documents,
    )
    payload = {
        "case_id": case_id,
        "floor_id": floor.floor_id,
        "manager_id": floor.manager_id,
        "mission": mission_text.strip(),
        "documents": documents,
        "status": "CREATED",
        "created_at": now(),
        "versions": [],
        "plan": None,
        "availability": (
            "Expediente registrado. Ejecute para enviar la misión al GER en OpenAI Platform. "
            "LNH gobierna el expediente; Platform ejecuta la inteligencia."
        ),
        "audit": [{"at": now(), "event": "MISSION_REGISTERED", "floor_id": floor.floor_id, "engine": "corporate_engine"}],
        "correction_pending": False,
        "engine": "corporate_engine",
        "mission_record": record,
    }
    dump_json(case / "case.json", payload)
    dump_json(case / "MISSION.json", {
        "case_id": case_id,
        "floor_id": floor.floor_id,
        "manager_id": floor.manager_id,
        "mission": mission_text.strip(),
        "created_at": payload["created_at"],
        "engine": "corporate_engine",
    })
    return case
