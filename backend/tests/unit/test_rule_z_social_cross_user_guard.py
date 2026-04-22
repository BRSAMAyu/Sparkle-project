from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_rule_z_social_cross_user.py"
sys.path.insert(0, str(REPO_ROOT))

from scripts.guards.check_rule_z_social_cross_user import scan_social_cross_user


def test_rule_z_social_cross_user_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_z_social_cross_user_guard_rejects_trait_leak(tmp_path) -> None:
    target = tmp_path / "social_signal_bridge.py"
    target.write_text(
        """
from uuid import UUID

class SocialSignalBridge:
    async def _fetch_for_user(self, user_id: UUID):
        await self.provider.fetch_social_snapshot(user_id)
        await self.preference_service.get_preferences(user_id)
        return {"metacognition": "oops"}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    violations = scan_social_cross_user(target)

    assert any("metacognition" in item for item in violations)
