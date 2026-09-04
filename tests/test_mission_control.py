import json,tempfile,unittest
from pathlib import Path
from mission_control import case_artifacts,executive_status,human_gate_action,load_case,selected_agent_summary
class Tests(unittest.TestCase):
 def test_case_view_and_human_gate(self):
  with tempfile.TemporaryDirectory() as t:
   c=Path(t)/"case";(c/"v001").mkdir(parents=True);(c/"case.json").write_text(json.dumps({"case_id":"case","status":"HUMAN_REVIEW_REQUIRED","documents":[{"name":"a.pdf"}],"versions":[{"version":1,"routes":["014"],"status":"HUMAN_REVIEW_REQUIRED"}]}),encoding="utf-8")
   for name in ("MGC-05_DEPARTMENT_REPORT.md","plan.json","handoffs.json","contradictions.json"):(c/"v001"/name).write_text("{}",encoding="utf-8")
   self.assertEqual("case",load_case(c)["case_id"]);self.assertEqual(4,len(case_artifacts(c)));self.assertEqual("approved",human_gate_action(c,"APROBAR","ok",lambda *x:"approved",lambda *x:"corrected"));self.assertEqual("corrected",human_gate_action(c,"CORREGIR","fix",lambda *x:"approved",lambda *x:"corrected"))
 def test_executive_status(self):
  self.assertIn("no existe informe profesional",executive_status({"latest":{"status":"INFRASTRUCTURE_BLOCKED"}})["blocked"]);self.assertEqual(1,len(selected_agent_summary(["014"])))
