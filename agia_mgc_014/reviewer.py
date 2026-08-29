"""Basic quality controls for the generated PMO report."""


REQUIRED_SECTIONS = ('Resumen ejecutivo', 'Hitos y control de avance', 'Dependencias y ruta crítica', 'Trazabilidad de fuentes')


def review(report: str) -> list[str]:
    issues = [f'Falta sección requerida: {section}.' for section in REQUIRED_SECTIONS if section not in report]
    if 'autoriza producción' in report.casefold():
        issues.append('El informe no puede autorizar producción.')
    return issues
