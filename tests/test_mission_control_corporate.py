from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from corporate_mission_control import (
    COMPANIES,
    HOLDING_AREAS,
    agent_reason,
    create_mgc03_case,
    evidence_rows,
    floors,
    load_corporate_case,
)


class MissionControlCorporateTests(unittest.TestCase):
    def test_catalog_reflects_current_corporate_states(self):
        self.assertEqual({"MGC", "LNRE"}, set(COMPANIES))
        self.assertEqual(9, len(HOLDING_AREAS))
        catalog = {item["floor_id"]: item for item in floors("MGC")}
        self.assertEqual("Operativo", catalog["MGC-05"]["status"])
        self.assertEqual("En construcción", catalog["MGC-03"]["status"])
        self.assertEqual("AGIA-MGC-007", catalog["MGC-03"]["agents"][0][0])

    def test_mgc03_case_is_retained_without_specialist_execution(self):
        with TemporaryDirectory() as folder:
            root = Path(folder) / "mgc03"
            source = Path(folder) / "evidence.txt"
            source.write_text("evidencia", encoding="utf-8")
            case = create_mgc03_case(root, "Preparar investigación secundaria de competencia minera", [source])
            loaded = load_corporate_case(case, "MGC-03")
            self.assertEqual("MGC-03", loaded["floor_id"])
            self.assertEqual(1, len(loaded["documents"]))
            self.assertTrue((case / "documents" / "evidence.txt").is_file())
            self.assertEqual([], loaded["raw"]["supervision"]["outputs_received"])
            self.assertIn("AGIA-MGC-007", loaded["raw"]["plan"]["selected_agents"])
            summary, rows, _ = evidence_rows(case, "MGC-03")
            self.assertEqual(1, summary["sources"])
            self.assertEqual("No disponible", rows[0]["finding"])

    def test_agent_reasons_keep_mgc03_execution_explicitly_unavailable(self):
        reason = agent_reason("MGC-03", ["AGIA-MGC-007"])
        self.assertEqual(1, len(reason))
        self.assertIn("coincidencia literal", reason[0])
        self.assertEqual([], agent_reason("MGC-03", []))


if __name__ == "__main__":
    unittest.main()
