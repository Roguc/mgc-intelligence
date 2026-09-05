"""Runtime identity used by the Mission Control launcher.

The launcher records this small, deterministic fingerprint beside its runtime
state.  A running Streamlit process is reused only when it was started with
the same Mission Control source identity.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


RUNTIME_FILES = (
    "app.py",
    "mission_control.py",
    "mgc_05/backend.py",
    "remote_compute.py",
    "ollama_inference.py",
    "runtime_dependencies.py",
)


def fingerprint(paths: list[Path]) -> str:
    """Return a content fingerprint that is stable across working directories."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def runtime_identity(repo: Path | None = None) -> dict[str, object]:
    """Describe the source files that define the local Mission Control runtime."""
    root = repo or Path(__file__).resolve().parent
    paths = [root / relative for relative in RUNTIME_FILES]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Mission Control runtime files missing: {', '.join(missing)}")
    return {"fingerprint": fingerprint(paths), "files": list(RUNTIME_FILES)}
