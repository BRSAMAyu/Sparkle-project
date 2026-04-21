from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def _run(script_name: str) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stage29" / script_name)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_an_isolation_scan_passes() -> None:
    _run("check_rule_an_orchestrator_isolation.py")


def test_rule_an_no_hardcoded_phase_scan_passes() -> None:
    _run("check_rule_an_orchestrator_no_hardcoded_phase.py")


def test_scaffolding_aggregator_only_scan_passes() -> None:
    _run("check_scaffolding_aggregator_only.py")
