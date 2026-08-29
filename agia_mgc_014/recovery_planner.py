"""Propose recovery actions; the agent never changes a baseline."""

from .project_model import Alert


def propose_recovery(deviations: list[str], alerts: list[Alert]) -> list[str]:
    proposals = []
    if deviations:
        proposals.append('PROPUESTA: convocar revisión de recuperación con los responsables para confirmar impacto, fechas y decisiones requeridas.')
        proposals.append('PROPUESTA: documentar forecast y solicitud de cambio antes de alterar cualquier baseline vigente.')
    if any('sin responsable' in alert.message for alert in alerts):
        proposals.append('PROPUESTA: Dirección o el responsable funcional debe asignar propietario a los hitos sin responsable.')
    if any('sin fecha objetivo' in alert.message for alert in alerts):
        proposals.append('PROPUESTA: acordar fechas objetivo y registrar la aprobación humana correspondiente.')
    if any(alert.level == 'CRÍTICA' for alert in alerts):
        proposals.append('PROPUESTA: suspender la recomendación de avance afectada y escalar el incidente crítico.')
    return proposals
