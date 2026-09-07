"""Runtime identity used by the Mission Control launcher.

The launcher records this small, deterministic fingerprint beside its runtime
state.  A running Streamlit process is reused only when it was started with
the same Mission Control source identity.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


RUNTIME_FILES = (
    "app.py",
    "mission_control.py",
    "corporate_mission_control.py",
    "mgc_05/backend.py",
    "remote_compute.py",
    "alibaba_model_studio.py",
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


def runtime_settings() -> tuple[str, str]:
    """Settings that require a controlled restart, excluding credentials."""
    return (
        os.getenv("MGC_INFERENCE_PROVIDER", "ollama").casefold(),
        os.getenv("MGC_ALIBABA_BASE_URL", "").strip(),
    )


def runtime_identity(repo: Path | None = None) -> dict[str, object]:
    """Describe the source files that define the local Mission Control runtime."""
    root = repo or Path(__file__).resolve().parent
    paths = [root / relative for relative in RUNTIME_FILES]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Mission Control runtime files missing: {', '.join(missing)}")
    digest = hashlib.sha256(fingerprint(paths).encode("utf-8"))
    for value in runtime_settings():
        digest.update(value.encode("utf-8"))
        digest.update(b"\0")
    return {"fingerprint": digest.hexdigest(), "files": list(RUNTIME_FILES)}
