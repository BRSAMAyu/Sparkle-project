from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_scaffolding_guard_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stage29" / "check_scaffolding_aggregator_only.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_scaffolding_file_has_no_tracker_import() -> None:
    text = (REPO_ROOT / "backend" / "app" / "scaffolding" / "scaffolding_fsm.py").read_text(encoding="utf-8")
    assert "SRLPhaseTrackerService" not in text
    assert "srl_phase_tracker_service" not in text
