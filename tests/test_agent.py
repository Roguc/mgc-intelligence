import tempfile
import unittest
from pathlib import Path
from agia_mgc_015.agent import run

class AgentTests(unittest.TestCase):
 def test_generates_traceable_report_without_inventing(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp); doc=root/'case.txt'; doc.write_text('El vendedor afirma tener licencia. La licencia no ha sido verificada independientemente.',encoding='utf-8')
   report,issues=run('Analizar oferta', [doc], root/'out'); text=report.read_text(encoding='utf-8')
   self.assertIn('Pendiente de verificar',text); self.assertIn('case.txt',text); self.assertFalse(issues)

if __name__=='__main__': unittest.main()
