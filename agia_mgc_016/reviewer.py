def review(report: str) -> list[str]:
    required = ('Expediente operacional', 'Matriz documental', 'Alertas', 'Trazabilidad')
    return [f'Falta sección requerida: {section}.' for section in required if section not in report]
