from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mission_control_runtime import RUNTIME_FILES, runtime_identity


class MissionControlRuntimeTests(unittest.TestCase):
    def _make_runtime(self, root: Path) -> None:
        for relative in RUNTIME_FILES:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"initial content for {relative}\n", encoding="utf-8")

    def test_identity_includes_every_runtime_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._make_runtime(root)
            identity = runtime_identity(root)

        self.assertEqual(list(RUNTIME_FILES), identity["files"])
        self.assertEqual(64, len(identity["fingerprint"]))

    def test_identity_changes_when_mission_control_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._make_runtime(root)
            original = runtime_identity(root)["fingerprint"]
            (root / "mission_control.py").write_text("new source version\n", encoding="utf-8")

            updated = runtime_identity(root)["fingerprint"]

        self.assertNotEqual(original, updated)
