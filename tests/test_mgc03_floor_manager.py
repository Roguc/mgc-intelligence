import json
import tempfile
import unittest
from pathlib import Path

from mgc_03.manager import FLOOR_ID, FUTURE_AGENT_SLOTS, MGC03FloorManager

class MGC03FloorManagerTests(unittest.TestCase):
    def test_current_staffing_reaches_human_gate_without_simulating_agents(self):
        with tempfile.TemporaryDirectory() as directory:
            case = MGC03FloorManager().materialize_case(Path(directory), "MGC03-TECH-001", "Analizar mercado de minerales.")
            record = json.loads((case / "MGC03_TECHNICAL_EXECUTION_RECORD.json").read_text(encoding="utf-8"))
        self.assertIn(FLOOR_ID, [item["unit_id"] for item in record["organization"]])
        self.assertEqual([], record["plan"]["selected_agents"])
        self.assertEqual(list(FUTURE_AGENT_SLOTS), record["plan"]["staffing_gap"])
        self.assertEqual("HUMAN_GATE_REQUIRED", record["corporate_state"]["status"])

    def test_future_registered_capability_is_selected_by_registry(self):
        manager = MGC03FloorManager()
        manager.platform.agents.register(type("Agent", (), {"agent_id": "TEST-MARKET", "department_id": FLOOR_ID, "capabilities": ("mercado",), "status": "OPERATIONAL"})())
        received = manager.receive_mission("Analizar mercado de cobre.", "MGC03-TECH-002")
        self.assertEqual(("TEST-MARKET",), manager.plan(received["mission"].mission_id).selected_agents)
