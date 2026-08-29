from .professional_profile import AGENT_CODE, AGENT_NAME, DEPARTMENT, STATUS
from .shipment_model import Shipment


def bullets(items, empty):
    return '\n'.join(f'- {item}' for item in items) if items else f'- {empty}'


def build_report(mission: str, shipment: Shipment) -> str:
    values = '\n'.join(f'- {key}: {value}' for key, value in shipment.fields.items()) or '- REQUIERE CONFIRMACIÓN'
    docs = '\n'.join(f'| {name} | {status} |' for name, status in shipment.documents.items())
    alerts = [f'**{alert.level}** — {alert.message}' for alert in shipment.alerts]
    incidents = shipment.incidents
    recommendation = 'DETENER RECOMENDACIÓN Y ESCALAR' if any(a.level == 'ALTA' for a in shipment.alerts) else 'AVANZAR CONDICIONADO A REVISIÓN HUMANA'
    return f'''# Informe operacional de comercio exterior y logística — {AGENT_CODE}

## Identificación

- Agente: {AGENT_NAME}
- Departamento: {DEPARTMENT}
- Estado: {STATUS}
- Misión: {mission}

## Resumen operacional

**{recommendation}**. El informe organiza información operacional suministrada; no aprueba contratos, pagos, contrapartes, embarques ni compromisos externos.

## Expediente operacional

{values}

## Matriz documental

| Documento | Estado operacional |
| --- | --- |
{docs}

Los documentos recibidos no se declaran válidos ni auténticos sólo por estar disponibles; pueden requerir validación especializada.

## Hitos y fechas críticas

{bullets([f'{key.upper()}: {value}' for key, value in shipment.fields.items() if key in ('booking', 'cut_off', 'etd', 'eta', 'vessel', 'port_loading', 'port_discharge')], 'No se documentaron hitos o fechas críticas suficientes.')}

## Coherencia Incoterm y operación

{bullets([f'Incoterm informado: {shipment.fields["incoterm"]}. La interpretación contractual requiere revisión humana cuando corresponda.'] if shipment.fields.get('incoterm') else [], 'Incoterm no documentado; no es posible evaluar coherencia operacional.')}

## Incidencias y custodia

{bullets(incidents, 'No se identificaron incidencias explícitas.')}

## Alertas

{bullets(alerts, 'No se generaron alertas automáticas.')}

## Próximas acciones

{bullets(shipment.next_actions, 'PROPUESTA: solicitar expediente operacional mínimo.')}

## Aprobación requerida

- Revisión humana para riesgo alto, excepción, dato sensible, decisión jurídica o financiera, compromiso comercial y acción irreversible.
- Desvíos materiales de custodia o entrega requieren preservar evidencia, detener recomendación si corresponde y escalar.

## Trazabilidad

{bullets(shipment.sources, 'No se adjuntaron documentos.')}
'''
