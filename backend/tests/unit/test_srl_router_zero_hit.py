from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_router_zero_hit_script_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stage29" / "check_srl_not_router.py")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_router_sources_do_not_reference_srl_tokens() -> None:
    router_root = REPO_ROOT / "backend" / "app" / "routing"
    text = "\n".join(path.read_text(encoding="utf-8") for path in router_root.glob("*.py"))
    assert "srl_phase" not in text
    assert "SRLPhaseTrackerService" not in text
