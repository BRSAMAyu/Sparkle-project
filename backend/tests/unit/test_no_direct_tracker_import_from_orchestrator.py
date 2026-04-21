from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rule_an_orchestrator_isolation_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stage29" / "check_rule_an_orchestrator_isolation.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_orchestrator_tree_has_no_tracker_import_tokens() -> None:
    orchestration_root = REPO_ROOT / "backend" / "app" / "orchestration"
    text = "\n".join(path.read_text(encoding="utf-8") for path in orchestration_root.rglob("*.py"))
    assert "SRLPhaseTrackerService" not in text
    assert "srl_phase_tracker_service" not in text
