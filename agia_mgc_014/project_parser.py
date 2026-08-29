"""Extract explicitly labelled PMO information from semi-structured inputs."""

from datetime import date
import re

from .project_model import Task

LABELS = {
    'name': ('tarea', 'hito', 'actividad', 'task', 'milestone', 'nombre'),
    'owner': ('responsable', 'owner', 'dueño'),
    'start_date': ('inicio', 'fecha inicio', 'start date'),
    'target_date': ('fecha objetivo', 'fecha meta', 'vencimiento', 'target date', 'deadline', 'fecha'),
    'actual_date': ('fecha real', 'actual date', 'completado el'),
    'status': ('estado', 'status'),
    'progress': ('avance', 'progreso', 'progress'),
    'dependencies': ('dependencia', 'dependencias', 'dependency', 'depends on'),
    'blocker': ('bloqueo', 'blocker'),
    'evidence': ('evidencia', 'evidence', 'respaldo'),
}


def _parse_date(value: str):
    value = value.strip()
    for pattern in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return date.fromisoformat(value) if pattern == '%Y-%m-%d' else __import__('datetime').datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _label_value(line: str, labels: tuple[str, ...]):
    for label in labels:
        match = re.search(rf'(?i)(?:^|[|;])\s*{re.escape(label)}\s*[:=]\s*([^|;]+)', line)
        if match:
            return match.group(1).strip()
    return None


def _task_from_line(line: str, source: str):
    values = {field: _label_value(line, labels) for field, labels in LABELS.items()}
    name = values['name']
    if not name:
        return None
    dependencies = [] if not values['dependencies'] else [item.strip() for item in re.split(r'[,/]', values['dependencies']) if item.strip()]
    progress = None
    if values['progress']:
        match = re.search(r'\d+(?:[.,]\d+)?', values['progress'])
        if match:
            progress = float(match.group().replace(',', '.'))
    return Task(
        name=name,
        owner=values['owner'],
        start_date=_parse_date(values['start_date']) if values['start_date'] else None,
        target_date=_parse_date(values['target_date']) if values['target_date'] else None,
        actual_date=_parse_date(values['actual_date']) if values['actual_date'] else None,
        status=values['status'], progress=progress, dependencies=dependencies,
        blocker=values['blocker'], evidence=values['evidence'], source=source,
    )


def parse_tasks(mission: str, documents: dict[str, str]) -> list[Task]:
    tasks = []
    sources = {'Instrucción humana': mission, **documents}
    for source, content in sources.items():
        for raw_line in content.splitlines():
            task = _task_from_line(raw_line.strip(' -•\t'), source)
            if task:
                tasks.append(task)
    unique = {}
    for task in tasks:
        key = task.name.casefold()
        if key not in unique:
            unique[key] = task
    return list(unique.values())
