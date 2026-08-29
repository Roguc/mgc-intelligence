"""Critical path calculation only from explicit dates and resolvable dependencies."""

from .project_model import Task


def calculate_critical_path(tasks: list[Task]) -> tuple[list[str] | None, str | None]:
    if not tasks:
        return None, 'RUTA CRÍTICA NO DETERMINABLE CON INFORMACIÓN DISPONIBLE: no se informaron actividades estructuradas.'
    names = {task.name.casefold(): task for task in tasks}
    if any(not task.start_date or not task.target_date for task in tasks):
        return None, 'RUTA CRÍTICA NO DETERMINABLE CON INFORMACIÓN DISPONIBLE: faltan fechas de inicio u objetivo.'
    if any(dep.casefold() not in names for task in tasks for dep in task.dependencies):
        return None, 'RUTA CRÍTICA NO DETERMINABLE CON INFORMACIÓN DISPONIBLE: existen dependencias no resueltas.'
    graph = {task.name.casefold(): [dep.casefold() for dep in task.dependencies] for task in tasks}
    cache, active = {}, set()

    def longest(name: str):
        if name in cache:
            return cache[name]
        if name in active:
            raise ValueError('ciclo')
        active.add(name)
        task = names[name]
        duration = max((task.target_date - task.start_date).days, 0)
        predecessors = [longest(dep) for dep in graph[name]]
        result = (duration, [task.name]) if not predecessors else (duration + max(predecessors, key=lambda item: item[0])[0], max(predecessors, key=lambda item: item[0])[1] + [task.name])
        active.remove(name)
        cache[name] = result
        return result

    try:
        result = max((longest(name) for name in names), key=lambda item: item[0])
    except ValueError:
        return None, 'RUTA CRÍTICA NO DETERMINABLE CON INFORMACIÓN DISPONIBLE: se detectó un ciclo de dependencias.'
    return result[1], None
