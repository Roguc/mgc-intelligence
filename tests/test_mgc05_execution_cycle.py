import json
import os
import tempfile
import unittest
from pathlib import Path

from mgc_05.backend import approve_case, correct_case, create_case, run_case


class MGC05ExecutionCycleTests(unittest.TestCase):
    def setUp(self):
        self.previous_mode = os.environ.get("MGC_INFERENCE_MODE")
        os.environ["MGC_INFERENCE_MODE"] = "rules"

    def tearDown(self):
        if self.previous_mode is None:
            os.environ.pop("MGC_INFERENCE_MODE", None)
        else:
            os.environ["MGC_INFERENCE_MODE"] = self.previous_mode

    def test_specialist_reports_are_required_before_consolidation_and_human_correction_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operacion.txt"
            source.write_text(
                "Hito: precalificación | Incoterm: FOB | Documento: LOI | Estado: declarado.",
                encoding="utf-8",
            )
            case = create_case(
                "Analizar proyecto, proceso SOP y logística de embarque.", [source], root / "cases"
            )
            first_output, first = run_case(case)
            self.assertEqual("HUMAN_REVIEW_REQUIRED", first["status"])
            self.assertEqual({"AGIA-MGC-014", "AGIA-MGC-015", "AGIA-MGC-016"}, {item["agent"] for item in first["reports"]})
            self.assertTrue((first_output / "MGC-05_DEPARTMENT_REPORT.md").exists())

            second_output, second = correct_case(case, "Distinguir con mayor claridad la evidencia declarada.")
            self.assertEqual(1, second["parent_version"])
            self.assertEqual("Distinguir con mayor claridad la evidencia declarada.", second["correction"])
            self.assertTrue((second_output / "MGC-05_DEPARTMENT_REPORT.md").exists())
            record = json.loads((case / "human_decisions" / "HUMAN_DECISION_RECORD_v001.json").read_text(encoding="utf-8"))
            self.assertEqual("CORREGIR", record["decision"])
            state = json.loads((case / "case.json").read_text(encoding="utf-8"))
            self.assertEqual(2, len(state["versions"]))

    def test_approval_requires_a_completed_professional_consolidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "operacion.txt"
            source.write_text("Documento: LOI", encoding="utf-8")
            case = create_case("Analizar proyecto PMO.", [source], root / "cases")
            state = json.loads((case / "case.json").read_text(encoding="utf-8"))
            state["versions"] = [{"version": 1, "status": "SPECIALIST_EXECUTION_BLOCKED"}]
            (case / "case.json").write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "informe profesional consolidado"):
                approve_case(case, "APROBADO", "No corresponde aprobar una ejecución bloqueada.")
