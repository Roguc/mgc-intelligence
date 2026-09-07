"""Technical execution wrapper for the official AGIA-MGC-007 profile."""

from datetime import datetime, timezone
from pathlib import Path

from ollama_inference import enabled, professional_report, write_trace
from .profile import AGENT_ID, OFFICIAL_PROFILE

SECTIONS = ("Resumen ejecutivo", "Alcance", "Datos y fuentes", "Hallazgos", "Riesgos", "Recomendación", "Aprobación requerida")

def _mandate() -> str:
    return "\n".join((
        OFFICIAL_PROFILE["mission"],
        f"Metodología: {OFFICIAL_PROFILE['methodology']}",
        f"Controles: {OFFICIAL_PROFILE['controls']}",
        f"Autonomía: {OFFICIAL_PROFILE['autonomy']}",
        f"Permitido: {OFFICIAL_PROFILE['allowed']}",
        f"Prohibido: {OFFICIAL_PROFILE['prohibited']}",
        f"Escalamiento: {OFFICIAL_PROFILE['escalation']}",
        "No realices acciones externas; produce sólo análisis interno y borradores para revisión humana.",
    ))

def run(mission: str, paths: list[Path], output_dir: Path) -> tuple[Path, dict]:
    """Materialize a real internal report and immutable trace through the configured engine."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if enabled():
        report, trace = professional_report(AGENT_ID, _mandate(), mission, paths, list(SECTIONS))
        target = output_dir / f"{AGENT_ID}_{trace['execution_id']}.md"
        target.write_text(report, encoding="utf-8")
        trace_path = write_trace(output_dir, AGENT_ID, trace, target)
        return target, {"engine": trace["runtime"], "trace": trace_path.name, "executed_at": trace["executed_at"]}
    target = output_dir / f"{AGENT_ID}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.md"
    target.write_text("# Informe técnico AGIA-MGC-007\n\nMotor de inferencia local no habilitado. No se produjo análisis profesional.\n", encoding="utf-8")
    return target, {"engine": "rules", "trace": None, "executed_at": datetime.now(timezone.utc).isoformat()}
