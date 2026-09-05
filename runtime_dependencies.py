"""Required local dependencies for the Mission Control runtime."""

from __future__ import annotations

import importlib
from typing import Callable


REQUIRED_IMPORTS = {
    "streamlit": "streamlit",
    "python-docx": "docx",
    "pypdf": "pypdf",
    "openpyxl": "openpyxl",
}


def missing_dependencies(importer: Callable[[str], object] = importlib.import_module) -> list[str]:
    """Return package names unavailable to the actual Python runtime."""
    missing: list[str] = []
    for package, module in REQUIRED_IMPORTS.items():
        try:
            importer(module)
        except ImportError:
            missing.append(package)
    return missing
