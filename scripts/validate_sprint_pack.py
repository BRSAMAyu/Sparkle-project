#!/usr/bin/env python3
"""Compatibility wrapper for the backend Sprint Pack validator."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    script = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "scripts"
        / "validate_sprint_pack.py"
    )
    runpy.run_path(str(script), run_name="__main__")
