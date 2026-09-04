import unittest
from corporate.data_evidence import initialize,record_execution,record_human_decision
class Tests(unittest.TestCase):
 def test_lineage_and_tco(self):
  ledger=initialize("C-1",[{"name":"a.pdf","path":"a.pdf","sha256":"abc"}],"rules");record_execution(ledger,1,[{"agent":"AGIA-MGC-014","report":"r.md"}],[{"subject":"B/L","departmental_status":"VÍNCULO NO DEMOSTRADO / REQUIERE REVISIÓN HUMANA"}],"rules");record_human_decision(ledger,"APROBADO",1)
  self.assertEqual(0,ledger["tco"]["usage"]["inference_calls"]);self.assertEqual(1,ledger["tco"]["usage"]["rule_executions"]);self.assertEqual(0.0,ledger["tco"]["budget"]["actual"]);self.assertTrue(ledger["findings"]);self.assertTrue(ledger["audit"])
