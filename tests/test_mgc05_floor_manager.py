import unittest
from mgc_05.floor_manager import FloorManager
from mgc_05.managerial import SpecialistOutput
class Tests(unittest.TestCase):
 def test_floor(self):
  manager=FloorManager();plan=manager.plan("Controlar proyecto, proceso SOP y embarque FOB")
  self.assertEqual(("AGIA-MGC-014","AGIA-MGC-015","AGIA-MGC-016"),plan.agent_ids);self.assertEqual(2,len(plan.dependencies))
  outputs=[SpecialistOutput("AGIA-MGC-014","Documento Vinculado BL.pdf SGS.pdf Laboratorio Preisser",("014.md",)),SpecialistOutput("AGIA-MGC-015","B/L SGS Laboratorio Preisser No se menciona el vínculo directo con la operación actual",("015.md",)),SpecialistOutput("AGIA-MGC-016","B/L En proceso de embarque",("016.md",))]
  record,report=manager.consolidate("CASE-1","fixture",outputs);self.assertEqual(3,len(record["contradictions"]));self.assertTrue(record["human_decisions"]);self.assertIn("Decisiones / Confirmaciones Humanas Requeridas",report)
