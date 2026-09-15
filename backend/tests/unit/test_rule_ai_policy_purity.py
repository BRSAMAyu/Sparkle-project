from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_rule_ai_policy_purity_guard_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/stage24/check_rule_ai_policy_purity.py")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_rule_ai_policy_purity_targets_expected_files() -> None:
    script = (REPO_ROOT / "scripts/stage24/check_rule_ai_policy_purity.py").read_text(encoding="utf-8")

    assert "policy_compiler_service.py" in script
    assert "policy_scheduler_service.py" in script
