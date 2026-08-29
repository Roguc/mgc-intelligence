import tempfile
import unittest
from pathlib import Path

from agia_mgc_016.agent import run_with_result


class OperationsAgentTests(unittest.TestCase):
    def test_builds_shipment_and_detects_cif_insurance_gap(self):
        text = 'Operación: OP-01 | Producto: Cobre | Origen: Chile | Destino: China | Incoterm: CIF | Booking: BK-1 | ETD: 2026-09-10 | Responsable: Ana'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); doc = root / 'case.txt'; doc.write_text(text, encoding='utf-8')
            result = run_with_result('Controlar embarque.', [doc], root / 'out')
            report = result.report_path.read_text(encoding='utf-8')
        self.assertIn('Expediente operacional', report)
        self.assertTrue(any('seguro de carga' in alert.message for alert in result.shipment.alerts))
        self.assertNotIn('Booking informado sin ETD', report)

    def test_does_not_invent_missing_data_and_records_incident(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); doc = root / 'case.txt'; doc.write_text('Incidencia: atraso de entrega informado.', encoding='utf-8')
            result = run_with_result('Revisar operación.', [doc], root / 'out')
            report = result.report_path.read_text(encoding='utf-8')
        self.assertIn('REQUIERE CONFIRMACIÓN', report)
        self.assertTrue(result.shipment.incidents)
        self.assertTrue(any('preservar evidencia' in alert.message for alert in result.shipment.alerts))


if __name__ == '__main__':
    unittest.main()
