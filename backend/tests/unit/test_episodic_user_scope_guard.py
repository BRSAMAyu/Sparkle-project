from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_episodic_user_scope.py"


def test_episodic_user_scope_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout
