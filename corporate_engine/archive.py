"""Archive classification of historical cases. Owned by corporate_engine."""
from __future__ import annotations

from pathlib import Path

from corporate_engine.store import dump_json, load_json

KNOWN = {
    "20260909220810-actualiza-nuestra-lectur": {
        "archive_class": "development",
        "reason": "Corrida de desarrollo previa al cierre operacional; no es trabajo empresarial activo.",
    },
    "20260909221122-actualiza-nuestra-lectur": {
        "archive_class": "development",
        "reason": "Corrida de desarrollo previa al cierre operacional; no es trabajo empresarial activo.",
    },
    "20260909224343-necesito-que-se-haga-un-": {
        "archive_class": "development",
        "reason": "Corrida de desarrollo previa al cierre operacional; no es trabajo empresarial activo.",
    },
    "20260909230910-actualiza-nuestra-lectur": {
        "archive_class": "development",
        "reason": "Corrida de desarrollo previa al cierre operacional; no es trabajo empresarial activo.",
    },
    "20260910021858-actualizar-la-lectura-em": {
        "archive_class": "development",
        "reason": "Corrida de desarrollo (carbonato/hidróxido de litio); no es trabajo empresarial activo.",
    },
    "20260910052010-actualizar-la-lectura-em": {
        "archive_class": "failed_test",
        "reason": "Banco histórico: homepage USGS, Data Ready como objeto, cierre con ejes abiertos.",
    },
    "20260911003052-actualizar-la-lectura-em": {
        "archive_class": "failed_test",
        "reason": "Banco histórico: Data Ready de litio/níquel como hallazgos; sin documento oficial del zinc.",
    },
    "20260911010457-actualizar-la-lectura-em": {
        "archive_class": "superseded",
        "reason": "Banco histórico: PDF Cobalt Institute extraído pero hallazgos canónicos no coincidían; MCS USGS no adquirido.",
    },
}


def classify_id(case_id: str) -> dict | None:
    return KNOWN.get(case_id)


def apply_case_json(path: Path, *, force: bool = False) -> dict | None:
    path = Path(path)
    if not path.is_file():
        return None
    state = load_json(path, {})
    case_id = state.get("case_id") or path.parent.name
    known = classify_id(case_id)
    if not known:
        return None
    if state.get("archive_class") and not force:
        return state
    state["archive_class"] = known["archive_class"]
    state["archive_reason"] = known["reason"]
    state["active_business"] = False
    dump_json(path, state)
    return state


def apply_root(root: Path, *, force: bool = False) -> list[str]:
    updated = []
    root = Path(root)
    if not root.is_dir():
        return updated
    for path in root.glob("*/case.json"):
        if apply_case_json(path, force=force):
            updated.append(path.parent.name)
    return updated


def is_active_business(state: dict) -> bool:
    if state.get("active_business") is False:
        return False
    if state.get("archive_class") in {"failed_test", "superseded", "development"}:
        return False
    return True
