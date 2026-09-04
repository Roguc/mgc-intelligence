"""Regression using the existing departmental outputs; it never invokes inference."""
import os
import unittest
from pathlib import Path

from mgc_05.managerial import SpecialistOutput, build_managerial_record, render_department_report


CASE = Path(os.environ.get(
    "MGC05_EXISTING_CASE",
    r"C:\Users\Robinson\LNH\mgc-intelligence\outputs\mgc_05\20260903155942-an-lisis-interno-departa\v001",
))


class ExistingCaseTests(unittest.TestCase):
    def test_existing_outputs_apply_conservative_evidence_rule_without_mutation(self):
        reports = sorted(CASE.glob("AGIA-MGC-*.md"))
        self.assertEqual(3, len(reports))
        before = {path: path.read_bytes() for path in reports}
        outputs = [SpecialistOutput(path.stem.rsplit("_", 1)[0], path.read_text(encoding="utf-8"), (path.name,)) for path in reports]
        record = build_managerial_record(outputs)
        self.assertTrue(record["contradictions"])
        self.assertTrue(all(item["departmental_status"] == "VÍNCULO NO DEMOSTRADO / REQUIERE REVISIÓN HUMANA" for item in record["contradictions"]))
        self.assertTrue(record["handoffs"])
        self.assertTrue(all("information_needed_by_destination" in item for item in record["handoffs"]))
        self.assertTrue(record["human_decisions"])
        report = render_department_report("fixture-case", "fixture mission", outputs, record)
        self.assertIn("decisiones / confirmaciones humanas requeridas", report.casefold())
        self.assertEqual(before, {path: path.read_bytes() for path in reports})
