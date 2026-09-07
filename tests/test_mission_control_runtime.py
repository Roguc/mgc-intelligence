from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os

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

    def test_identity_changes_when_corporate_view_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._make_runtime(root)
            original = runtime_identity(root)["fingerprint"]
            (root / "corporate_mission_control.py").write_text("new corporate view\n", encoding="utf-8")

            updated = runtime_identity(root)["fingerprint"]

        self.assertNotEqual(original, updated)

    def test_identity_changes_when_provider_changes(self) -> None:
        with patch.dict(os.environ, {"MGC_INFERENCE_PROVIDER": "ollama"}, clear=False):
            ollama = runtime_identity()["fingerprint"]
        with patch.dict(os.environ, {"MGC_INFERENCE_PROVIDER": "alibaba", "MGC_ALIBABA_BASE_URL": "https://workspace.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"}, clear=False):
            alibaba = runtime_identity()["fingerprint"]
        self.assertNotEqual(ollama, alibaba)
