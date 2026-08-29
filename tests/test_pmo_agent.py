import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from agia_mgc_014.agent import run_with_result


class PMOAgentTests(unittest.TestCase):
    def test_generates_pmo_report_and_critical_path_from_explicit_data(self):
        today = date.today()
        start = (today - timedelta(days=10)).isoformat()
        target_one = (today - timedelta(days=2)).isoformat()
        target_two = (today + timedelta(days=5)).isoformat()
        content = '\n'.join([
            f'Tarea: Diseño | Responsable: Ana | Inicio: {start} | Fecha objetivo: {target_one} | Estado: En curso | Avance: 50% | Evidencia: acta.pdf',
            f'Tarea: Aprobación | Responsable: Bruno | Inicio: {target_one} | Fecha objetivo: {target_two} | Estado: Pendiente | Dependencia: Diseño',
        ])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document = root / 'plan.txt'
            document.write_text(content, encoding='utf-8')
            result = run_with_result('Controlar el proyecto.', [document], root / 'out')
            report = result.report_path.read_text(encoding='utf-8')
        self.assertIn('Informe profesional PMO', report)
        self.assertIn('Diseño → Aprobación', report)
        self.assertIn('compromiso vencido', report)
        self.assertFalse(result.review_issues)

    def test_does_not_invent_missing_dates_or_owners(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document = root / 'plan.txt'
            document.write_text('Hito: Contrato | Estado: En curso | Avance: 40%', encoding='utf-8')
            result = run_with_result('Revisar hitos.', [document], root / 'out')
            report = result.report_path.read_text(encoding='utf-8')
        self.assertIn('REQUIERE CONFIRMACIÓN', report)
        self.assertIn('RUTA CRÍTICA NO DETERMINABLE', report)
        self.assertIn('Avance declarado sin evidencia suficiente', report)

    def test_detects_unresolved_dependency_and_circular_dependency(self):
        content = '\n'.join([
            'Tarea: A | Responsable: Ana | Inicio: 2026-01-01 | Fecha objetivo: 2026-01-02 | Dependencia: B',
            'Tarea: B | Responsable: Bruno | Inicio: 2026-01-01 | Fecha objetivo: 2026-01-03 | Dependencia: A',
            'Tarea: C | Responsable: Carla | Inicio: 2026-01-01 | Fecha objetivo: 2026-01-04 | Dependencia: NoExiste',
        ])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document = root / 'plan.txt'
            document.write_text(content, encoding='utf-8')
            result = run_with_result('Analizar dependencias.', [document], root / 'out')
        messages = [alert.message for alert in result.analysis.alerts]
        self.assertTrue(any('no resuelta' in message for message in messages))
        self.assertTrue(any('circular' in message for message in messages))

    def test_reads_csv_input(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            document = root / 'plan.csv'
            document.write_text('Tarea,Responsable,Fecha objetivo\nEntrega,Ana,2026-12-01', encoding='utf-8')
            result = run_with_result('Revisar CSV.', [document], root / 'out')
        self.assertEqual(result.analysis.sources, ['plan.csv'])
        self.assertEqual(result.analysis.tasks[0].name, 'Entrega')


if __name__ == '__main__':
    unittest.main()
