"""Operational controls for documents, dates, Incoterm, custody and delivery."""

from .shipment_model import Shipment, Alert


def analyze(shipment: Shipment) -> Shipment:
    required = ('operation_id', 'commodity', 'origin', 'destination', 'incoterm')
    for field in required:
        if not shipment.fields.get(field):
            shipment.alerts.append(Alert('ALTA', f'Dato operacional crítico faltante: {field}.'))
    if shipment.fields.get('booking') and not shipment.fields.get('etd'):
        shipment.alerts.append(Alert('ALTA', 'Booking informado sin ETD documentado.'))
    if shipment.fields.get('etd') and not shipment.fields.get('eta'):
        shipment.alerts.append(Alert('MEDIA', 'ETD informado sin ETA documentada.'))
    if shipment.fields.get('incoterm', '').upper() == 'CIF' and shipment.documents.get('Seguro de carga') != 'RECIBIDO':
        shipment.alerts.append(Alert('ALTA', 'Incoterm CIF informado sin seguro de carga documentado; requiere validación operacional y contractual.'))
    if shipment.fields.get('incoterm') and not shipment.fields.get('responsible'):
        shipment.alerts.append(Alert('ALTA', 'Incoterm informado sin responsable operacional documentado.'))
    if shipment.incidents:
        shipment.alerts.append(Alert('ALTA', 'Incidencia logística documentada; preservar evidencia y escalar según impacto.'))
    if not shipment.sources:
        shipment.alerts.append(Alert('MEDIA', 'No se adjuntaron fuentes documentales; la información permanece declarada.'))
    shipment.next_actions = ['PROPUESTA: completar datos y documentos marcados como no documentados antes de recomendar avance operacional.']
    if shipment.incidents:
        shipment.next_actions.append('PROPUESTA: registrar incidencia, responsable, evidencia, impacto y próxima acción; escalar si afecta custodia o entrega.')
    if any(alert.level == 'ALTA' for alert in shipment.alerts):
        shipment.next_actions.append('PROPUESTA: requerir revisión humana antes de cualquier compromiso externo, pago, contrato o instrucción irreversible.')
    return shipment
