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


def test_router_sources_consume_srl_only_via_stage33_gate() -> None:
    target_paths = (
        REPO_ROOT / "backend" / "app" / "orchestration" / "routing_engine.py",
        REPO_ROOT / "backend" / "app" / "orchestration" / "dual_core_router.py",
        REPO_ROOT / "backend" / "app" / "orchestration" / "prompts.py",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in target_paths)

    assert "srl_phase_hint" in text
    assert 'stage33_modes.get("srl")' in text
    assert "AURORA_STAGE33_SRL_MODE" in text
    assert "SRLPhaseTrackerService" not in text
