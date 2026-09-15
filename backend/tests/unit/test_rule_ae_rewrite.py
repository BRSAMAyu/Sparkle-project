from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from check_rule_ae_conflict_audit import check_rule_ae


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _base_source() -> str:
    return """
class ConflictResolverService:
    async def apply_live_decision(self, decision):
        if decision.action == "accept":
            await self.record_resolution()
            return decision
        if decision.action == "reject":
            await self.record_resolution()
            return decision
        await self.record_resolution()
        return decision

    async def record_shadow_comparison(self):
        await self.record_resolution()

    async def arbitrate_unresolved_conflict(self):
        await self.record_resolution()
"""


def test_rule_ae_passes_for_audited_conflict_paths(tmp_path) -> None:
    path = _write(tmp_path / "conflict.py", _base_source())
    assert check_rule_ae(path) == []


def test_rule_ae_fails_when_accept_branch_loses_audit_call(tmp_path) -> None:
    path = _write(
        tmp_path / "conflict.py",
        _base_source().replace('if decision.action == "accept":\n            await self.record_resolution()\n', 'if decision.action == "accept":\n            return decision\n'),
    )
    violations = check_rule_ae(path)
    assert any(item.startswith("AE003") for item in violations)


def test_rule_ae_fails_when_shadow_comparison_loses_record_resolution(tmp_path) -> None:
    path = _write(
        tmp_path / "conflict.py",
        _base_source().replace("    async def record_shadow_comparison(self):\n        await self.record_resolution()\n", "    async def record_shadow_comparison(self):\n        pass\n"),
    )
    violations = check_rule_ae(path)
    assert any(item.startswith("AE004") for item in violations)


def test_rule_ae_fails_when_user_arbitration_loses_record_resolution(tmp_path) -> None:
    path = _write(
        tmp_path / "conflict.py",
        _base_source().replace("    async def arbitrate_unresolved_conflict(self):\n        await self.record_resolution()\n", "    async def arbitrate_unresolved_conflict(self):\n        pass\n"),
    )
    violations = check_rule_ae(path)
    assert any(item.startswith("AE004") for item in violations)
