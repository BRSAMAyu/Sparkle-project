#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    python_bin = Path(os.environ.get("PYTHON_BIN", repo_root / "backend" / ".venv" / "bin" / "python"))
    if not python_bin.exists():
        python_bin = Path(sys.executable)
    command = [
        str(python_bin),
        "-m",
        "pytest",
        "backend/tests/unit/test_scene_idempotency.py",
        "-q",
    ]
    completed = subprocess.run(command, cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
