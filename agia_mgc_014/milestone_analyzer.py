"""Milestone completeness controls."""

from .project_model import Alert, Task


def analyze_milestones(tasks: list[Task]) -> list[Alert]:
    alerts = []
    for task in tasks:
        if not task.owner:
            alerts.append(Alert('ALTA', 'Actividad o hito sin responsable definido.', task.name))
        if not task.target_date:
            alerts.append(Alert('ALTA', 'Actividad o hito sin fecha objetivo.', task.name))
        if task.status and task.status.casefold() not in {'no iniciado', 'pendiente'} and not task.evidence:
            alerts.append(Alert('MEDIA', 'Avance declarado sin evidencia suficiente.', task.name))
        if task.blocker:
            alerts.append(Alert('ALTA', f'Bloqueo declarado: {task.blocker}', task.name))
    return alerts
