from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from scripts.guards.check_rule_bb_financial_atomicity import scan_rule_bb
from scripts.guards.check_rule_bc_idempotency_key import scan_rule_bc


def test_rule_bb_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/guards/check_rule_bb_financial_atomicity.py")],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_bc_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts/guards/check_rule_bc_idempotency_key.py")],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_bb_guard_flags_missing_atomic_tokens(tmp_path) -> None:
    photon_service = tmp_path / "photon_service.py"
    photon_service.write_text("async def deduct_photons():\n    pass\n", encoding="utf-8")
    achievement_engine = tmp_path / "achievement_engine.py"
    achievement_engine.write_text("async def process_event():\n    pass\n", encoding="utf-8")

    violations = scan_rule_bb(
        photon_service=photon_service,
        achievement_engine=achievement_engine,
    )

    assert any("BB001" in item for item in violations)
    assert any("BB002" in item for item in violations)


def test_rule_bc_guard_flags_missing_idempotency_key(tmp_path) -> None:
    shop = tmp_path / "shop.py"
    shop.write_text(
        """
async def purchase_item(request):
    return {"ok": True}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    violations = scan_rule_bc({shop: ("purchase_item",)})

    assert any("BC002" in item for item in violations)
