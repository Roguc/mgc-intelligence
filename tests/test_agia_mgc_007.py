import os
import tempfile
import unittest
from pathlib import Path

os.environ["MGC_INFERENCE_MODE"] = "rules"

from agia_mgc_007.agent import run
from agia_mgc_007.profile import AGENT_ID, OFFICIAL_PROFILE
from mgc_03.manager import MGC03FloorManager

class AGIAMGC007Tests(unittest.TestCase):
    def test_official_profile_and_registry_selection(self):
        manager = MGC03FloorManager()
        received = manager.receive_mission("Diseñar investigación secundaria de competencia minera.", "MGC03-007-TEST")
        plan = manager.plan(received["mission"].mission_id)
        self.assertIn(AGENT_ID, plan.selected_agents)
        self.assertEqual("Sociólogo o Investigador de Mercados", OFFICIAL_PROFILE["profession"])
        self.assertEqual("Diseñado - pendiente de aprobación", OFFICIAL_PROFILE["status"])

    def test_rules_execution_materializes_output_without_external_action(self):
        with tempfile.TemporaryDirectory() as directory:
            report, record = run("Preparar borrador interno.", [], Path(directory))
            self.assertTrue(report.is_file())
            self.assertEqual("rules", record["engine"])
