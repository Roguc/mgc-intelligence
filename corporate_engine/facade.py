"""HTTP-facing facade. Adapters call this. Operational logic stays in the engine."""
from __future__ import annotations

import logging
import traceback
from pathlib import Path

from corporate_engine.catalog import FLOORS, hierarchy
from corporate_engine.cycle import Runtime, run_cycle
from corporate_engine.errors import Conflict
from corporate_engine.gate import correct_case, decide_case, run_case
from corporate_engine.mission import open_case
from corporate_engine.presentation import authorize_operation, case_view, plan_view
from corporate_engine.publish import CONSOLIDATION_NAME
from corporate_engine.store import load_json, now, write_text

LOGGER = logging.getLogger("lnh.corporate_engine")


def business_message(error: BaseException) -> str:
    text = str(error)
    lowered = text.casefold()
    if "credit_balance_exhausted" in lowered or "no credits remaining" in lowered:
        return (
            "OpenAI Platform rechazó la ejecución: no hay créditos en la organización. "
            "Cargue saldo en Billing y reintente este mismo expediente."
        )
    if any(token in lowered for token in ("timeout", "timed out", "network", "offline", "connection", "dns")):
        return "No se pudo completar una consulta externa. El expediente conserva su estado; el detalle técnico quedó en la bitácora."
    return "No se pudo completar el trabajo del piso de inteligencia. Consulte la bitácora técnica del expediente antes de reintentar."


def log_technical(case: Path, error: BaseException) -> None:
    LOGGER.exception("corporate_engine error in %s", case)
    folder = Path(case) / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now().replace(":", "").replace("-", "")
    payload = f"{now()}\n{type(error).__name__}: {error}\n{traceback.format_exc()}"
    write_text(folder / f"technical_{stamp}.log", payload)
    write_text(folder / "technical.log", payload)


def perform_operation(case: Path, action: str, rationale: str = "", *, job_id: str | None = None,
                      runtime: Runtime | None = None, floor_id: str = "MGC-03",
                      expected_version=None, jobs: list | None = None):
    case = Path(case)
    if expected_version is None:
        state = load_json(case / "case.json") or {}
        versions = state.get("versions") or []
        expected_version = versions[-1].get("version") if versions else None
    authorize_operation(case, floor_id, action, rationale, expected_version, jobs=jobs or [])
    if action == "EJECUTAR":
        return run_case(case, runtime=runtime)
    if action == "CORREGIR":
        return correct_case(case, rationale, runtime=runtime)
    if action in {"APROBAR", "RECHAZAR"}:
        return decide_case(case, action, rationale, job_id=job_id)
    raise ValueError("Acción no disponible para el piso o estado actual del expediente.")


__all__ = (
    "Runtime", "run_cycle", "run_case", "correct_case", "decide_case", "open_case",
    "CONSOLIDATION_NAME", "business_message", "log_technical", "plan_view",
    "hierarchy", "FLOORS", "case_view", "authorize_operation", "perform_operation",
    "Conflict",
)
