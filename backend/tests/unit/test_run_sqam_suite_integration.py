from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_run_sqam_suite_passes() -> None:
    result = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "stage32" / "run_sqam_suite.sh")],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Stage 32 SQAM suite passed" in result.stdout
