import tempfile,unittest
from pathlib import Path
from corporate.api import CorporateAPI
from corporate.inference import InferenceRequest,MockInferenceGateway
from corporate.models import Mission
from corporate.platform import build_mgc_platform
class Tests(unittest.TestCase):
 def test_platform(self):
  gateway=MockInferenceGateway({"AGIA-MGC-014":"fixture"});p=build_mgc_platform(gateway);self.assertEqual("MGC-05",p.agents.get("AGIA-MGC-016").department_id);m=p.missions.register(Mission("M-001","Controlar hito y embarque","MGC-05"))
  with tempfile.TemporaryDirectory() as t:
   f=Path(t)/"evidence.txt";f.write_text("fixture",encoding="utf-8");r=p.register_case(m.mission_id,"C-001",[f])
  self.assertEqual("CASE_CREATED",r["state"]["status"]);self.assertEqual(1,len(r["evidence"]));result=gateway.execute(InferenceRequest("M-001","AGIA-MGC-014","fixture prompt"));p.observability.record("INFERENCE_COMPLETED",cost_usd=result.cost_usd);self.assertEqual(0.0,p.observability.costs()["cost_usd"]);self.assertTrue(p.human_gate.decision("C-001","REQUIERE_CORRECCIÓN","fixture",1)["human_required"]);self.assertEqual(3,len(CorporateAPI(p).agents()))
