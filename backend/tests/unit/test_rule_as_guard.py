from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "guards" / "check_rule_as_vision_compliance.py"
sys.path.insert(0, str(REPO_ROOT))

from scripts.guards.check_rule_as_vision_compliance import scan_rule_as


def test_rule_as_guard_passes_on_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_rule_as_guard_flags_unconsumed_attachment_without_ignore(tmp_path) -> None:
    profile_context = tmp_path / "profile_context_service.py"
    profile_context.write_text(
        """
class ProfileContextService:
    async def _attach_custom_signal(self, user_id, context):
        context.custom_signal = {"value": 1}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    routing_engine = tmp_path / "routing_engine.py"
    routing_engine.write_text("", encoding="utf-8")
    prompts = tmp_path / "prompts.py"
    prompts.write_text("", encoding="utf-8")

    violations = scan_rule_as(
        profile_context_service=profile_context,
        consumer_targets=(routing_engine, prompts),
    )

    assert any("custom_signal" in item for item in violations)


def test_rule_as_guard_allows_explicit_ignore(tmp_path) -> None:
    profile_context = tmp_path / "profile_context_service.py"
    profile_context.write_text(
        """
class ProfileContextService:
    # rule-as: ignore future_stage
    async def _attach_custom_signal(self, user_id, context):
        context.custom_signal = {"value": 1}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    routing_engine = tmp_path / "routing_engine.py"
    routing_engine.write_text("", encoding="utf-8")
    prompts = tmp_path / "prompts.py"
    prompts.write_text("", encoding="utf-8")

    assert scan_rule_as(
        profile_context_service=profile_context,
        consumer_targets=(routing_engine, prompts),
    ) == []
