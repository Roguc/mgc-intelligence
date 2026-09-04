import os
os.environ['MGC_INFERENCE_MODE'] = 'rules'
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from mgc_05.backend import approve_case,create_case,correct_case,run_case
class Tests(unittest.TestCase):
 def test_cycle(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d=r/'x.txt';d.write_text('INCOTERMS: FOB\nIRON ORE',encoding='utf-8');c=create_case('Controlar embarque y proyecto',[d],r/'cases');self.assertTrue((c/'corporate_case.json').exists());folder,v=run_case(c);self.assertEqual(v['routes'],['014','016']);self.assertTrue(all('handoff' in x for x in v['reports']));_,v=correct_case(c,'revisar seguro');self.assertEqual(v['version'],2);self.assertEqual(approve_case(c,'APROBADO','ok')['version'],2)
 def test_infrastructure_failure_aborts_before_dispatch(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d=r/'x.txt';d.write_text('INCOTERMS: FOB\nIRON ORE',encoding='utf-8');c=create_case('Controlar embarque',[d],r/'cases')
   old=os.environ.pop('MGC_INFERENCE_MODE',None)
   try:
    with patch('mgc_05.backend.inference_healthcheck',return_value={'ok':False,'error':'offline'}):
     folder,v=run_case(c)
   finally:
    if old is not None: os.environ['MGC_INFERENCE_MODE']=old
   self.assertEqual(v['status'],'INFRASTRUCTURE_BLOCKED');self.assertEqual(v['reports'],[])
 def test_blocks_external(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):create_case('Enviar email',[],Path(t))
