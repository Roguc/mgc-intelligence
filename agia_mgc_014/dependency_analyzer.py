"""Dependency validation without inventing missing links or durations."""

from .project_model import Alert, Task


def analyze_dependencies(tasks: list[Task]) -> list[Alert]:
    names = {task.name.casefold() for task in tasks}
    alerts = []
    graph = {task.name.casefold(): [dep.casefold() for dep in task.dependencies] for task in tasks}
    for task in tasks:
        for dependency in task.dependencies:
            if dependency.casefold() not in names:
                alerts.append(Alert('ALTA', f'Dependencia no resuelta o no informada: {dependency}.', task.name))
    visited, active = set(), set()

    def visit(node: str):
        if node in active:
            return True
        if node in visited:
            return False
        visited.add(node)
        active.add(node)
        circular = any(visit(child) for child in graph.get(node, []) if child in graph)
        active.remove(node)
        return circular

    if any(visit(node) for node in graph):
        alerts.append(Alert('CRÍTICA', 'Se detectó una dependencia circular o incoherente.'))
    return alerts
