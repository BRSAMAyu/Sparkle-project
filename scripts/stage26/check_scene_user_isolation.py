#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    command = [
        str(repo_root / "backend" / ".venv" / "bin" / "python"),
        "-m",
        "pytest",
        "backend/tests/unit/test_scene_user_isolation.py",
        "-q",
    ]
    completed = subprocess.run(command, cwd=repo_root)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
