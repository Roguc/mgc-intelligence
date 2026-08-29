"""Human-readable PMO report; technical structures remain supporting evidence."""

from .professional_profile import AGENT_CODE, AGENT_NAME, DEPARTMENT, STATUS
from .project_model import ProjectAnalysis


def _bullets(items: list[str], empty: str) -> str:
    return '\n'.join(f'- {item}' for item in items) if items else f'- {empty}'


def _task_rows(analysis: ProjectAnalysis) -> str:
    if not analysis.tasks:
        return 'No se recibió información estructurada suficiente de hitos o actividades.'
    rows = ['| Hito / actividad | Responsable | Fecha objetivo | Estado | Avance | Evidencia |', '| --- | --- | --- | --- | --- | --- |']
    for task in analysis.tasks:
        rows.append('| {0} | {1} | {2} | {3} | {4} | {5} |'.format(
            task.name, task.owner or 'REQUIERE CONFIRMACIÓN', task.target_date.isoformat() if task.target_date else 'REQUIERE CONFIRMACIÓN',
            task.status or 'UNKNOWN', f'{task.progress:g}%' if task.progress is not None else 'UNKNOWN', task.evidence or 'No informada'
        ))
    return '\n'.join(rows)


def build_report(mission: str, analysis: ProjectAnalysis) -> str:
    alert_lines = [f'**{alert.level}** — {alert.task + ": " if alert.task else ""}{alert.message}' for alert in analysis.alerts]
    dependencies = [f'{task.name} depende de: {", ".join(task.dependencies)}.' for task in analysis.tasks if task.dependencies]
    critical = ' → '.join(analysis.critical_path) if analysis.critical_path else analysis.critical_path_reason
    recommendation = 'ESCALAR Y CONTROLAR' if any(alert.level == 'CRÍTICA' for alert in analysis.alerts) else 'AVANZAR CONDICIONADO A VALIDACIÓN HUMANA'
    return f'''# Informe profesional PMO — {AGENT_CODE}

## Identificación

- Agente: {AGENT_NAME}
- Departamento: {DEPARTMENT}
- Estado del agente: {STATUS}
- Misión: {mission}

## Resumen ejecutivo

**{recommendation}**. Este informe organiza el control de proyecto a partir de la información suministrada. No aprueba proyectos, cambios, contratos, pagos ni compromisos externos.

## Estado de información

### DOCUMENTADO

- Se recibieron la misión y las fuentes indicadas en la trazabilidad.
- Hitos o actividades estructurados identificados: {len(analysis.tasks)}.

### DECLARADO

{_bullets(analysis.declared, 'No se identificaron declaraciones explícitas.')}

### REQUIERE CONFIRMACIÓN

{_bullets(analysis.assumptions, 'No se registraron supuestos adicionales.')}

## Hitos y control de avance

{_task_rows(analysis)}

## Dependencias y ruta crítica

### Dependencias documentadas

{_bullets(dependencies, 'No se identificaron dependencias explícitas.')}

### Ruta crítica

{critical}

## Desviaciones

{_bullets(analysis.deviations, 'No se detectaron desviaciones con evidencia suficiente.')}

## Riesgos

{_bullets(analysis.risks, 'No se identificaron riesgos explícitos en las fuentes.')}

## Issues

{_bullets(analysis.issues, 'No se identificaron issues explícitos en las fuentes.')}

## Alertas PMO

{_bullets(alert_lines, 'No se generaron alertas automáticas.')}

## Próximas acciones y recuperación

{_bullets(analysis.recovery_actions, 'PROPUESTA: mantener seguimiento y solicitar los datos faltantes antes de emitir una conclusión de plazo.')}

## Aprobación requerida

- Requiere revisión humana para decisiones de prioridad, responsables, baseline, cambios, riesgos altos y cualquier compromiso externo.
- Si existe una alerta crítica, dos inconsistencias relevantes o confianza inferior a 80%, corresponde escalar según el nivel de impacto.

## Trazabilidad de fuentes

{_bullets(analysis.sources, 'No se adjuntaron documentos.')}
'''
