import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from agia_mgc_014.reader import read_document
from ollama_inference import _page_chunks


class PdfRuntimeTests(unittest.TestCase):
    def test_real_runtime_reads_pdf_for_agent_and_inference_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidencia.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=100, height=100)
            with path.open("wb") as target:
                writer.write(target)
            self.assertEqual("", read_document(path))
            chunks = _page_chunks(path)
            self.assertEqual("evidencia.pdf", chunks[0]["document"])
            self.assertEqual(1, chunks[0]["page"])
