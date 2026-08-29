"""Extract only explicitly labelled operational facts; absent data stays unknown."""

import re

from .shipment_model import Shipment

FIELDS = {
    'operation_id': ('operación', 'operation id', 'shipment id'), 'commodity': ('producto', 'commodity'),
    'quantity': ('cantidad', 'quantity'), 'origin': ('origen', 'origin'), 'destination': ('destino', 'destination'),
    'incoterm': ('incoterm',), 'shipper': ('shipper', 'vendedor'), 'consignee': ('consignee', 'comprador'),
    'carrier': ('carrier', 'transportista'), 'forwarder': ('freight forwarder', 'forwarder'), 'insurer': ('aseguradora', 'insurer'),
    'port_loading': ('puerto de carga', 'port of loading'), 'port_discharge': ('puerto de descarga', 'port of discharge'),
    'vessel': ('vessel', 'buque'), 'booking': ('booking',), 'etd': ('etd',), 'eta': ('eta',), 'cut_off': ('cut-off', 'cut off'),
    'status': ('estado', 'status'), 'responsible': ('responsable', 'responsible'), 'evidence': ('evidencia', 'evidence'),
}
DOCUMENTS = {'commercial invoice': 'Factura comercial', 'invoice': 'Factura comercial', 'packing list': 'Packing list', 'bill of lading': 'B/L', 'b/l': 'B/L', 'booking': 'Confirmación de booking', 'shipping instruction': 'Shipping instructions', 'certificate of origin': 'Certificado de origen', 'insurance': 'Seguro de carga', 'inspection': 'Certificado de inspección'}


def parse(mission: str, documents: dict[str, str]) -> Shipment:
    shipment = Shipment(sources=list(documents))
    text = mission + '\n' + '\n'.join(documents.values())
    for line in text.splitlines():
        for key, labels in FIELDS.items():
            for label in labels:
                match = re.search(rf'(?i)(?:^|[|;])\s*{re.escape(label)}\s*[:=]\s*([^|;]+)', line)
                if match and key not in shipment.fields:
                    shipment.fields[key] = match.group(1).strip()
        clean = line.strip(' -•\t')
        if re.search(r'(?i)\b(atraso|rollover|daño|pérdida|rechazo|incidencia|desviación|demora)\b', clean):
            shipment.incidents.append(clean)
    names = ' '.join(documents).casefold()
    for marker, name in DOCUMENTS.items():
        shipment.documents[name] = 'RECIBIDO' if marker in names else 'NO DOCUMENTADO'
    return shipment
