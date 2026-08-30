import tempfile,unittest
from pathlib import Path
from mgc_05.backend import approve_case,create_case,correct_case,run_case
class Tests(unittest.TestCase):
 def test_cycle(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d=r/'x.txt';d.write_text('INCOTERMS: FOB\nIRON ORE',encoding='utf-8');c=create_case('Controlar embarque y proyecto',[d],r/'cases');folder,v=run_case(c);self.assertEqual(v['routes'],['014','016']);self.assertTrue(all('handoff' in x for x in v['reports']));_,v=correct_case(c,'revisar seguro');self.assertEqual(v['version'],2);self.assertEqual(approve_case(c,'APROBADO','ok')['version'],2)
 def test_blocks_external(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):create_case('Enviar email',[],Path(t))
