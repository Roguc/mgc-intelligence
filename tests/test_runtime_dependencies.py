import unittest

from runtime_dependencies import missing_dependencies


class RuntimeDependencyTests(unittest.TestCase):
    def test_reports_missing_pdf_reader_for_the_actual_runtime_check(self):
        def importer(name):
            if name == "pypdf":
                raise ImportError(name)
            return object()

        self.assertEqual(["pypdf"], missing_dependencies(importer))
