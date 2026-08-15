from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the repository root from this source file location."""
    return Path(__file__).resolve().parents[2]
