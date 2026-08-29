"""Compare documented target and actual status; do not fabricate a baseline or forecast."""

from datetime import date

from .project_model import Task


COMPLETE = {'completado', 'completa', 'cerrado', 'finalizado', 'done', 'complete'}


def analyze_deviations(tasks: list[Task], today: date | None = None) -> list[str]:
    today = today or date.today()
    deviations = []
    for task in tasks:
        status = (task.status or '').casefold()
        if task.actual_date and task.target_date and task.actual_date > task.target_date:
            deviations.append(f'{task.name}: cierre real posterior a la fecha objetivo ({task.target_date.isoformat()}).')
        elif task.target_date and task.target_date < today and status not in COMPLETE:
            deviations.append(f'{task.name}: compromiso vencido frente a fecha objetivo {task.target_date.isoformat()}; no existe evidencia de cierre.')
        if task.progress is not None and task.progress > 100:
            deviations.append(f'{task.name}: avance declarado superior a 100%; requiere validación.')
    return deviations
