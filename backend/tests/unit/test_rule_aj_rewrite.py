from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from stage25.check_rule_aj_user_id_isolation import check_rule_aj


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _valid_source() -> str:
    return """
class RouteHistoryService:
    async def read_recent_decisions(self, user_id, limit=20):
        normalized_user_id = self._require_user_id(user_id)
        stmt = select(RoutingDecisionLog).where(RoutingDecisionLog.user_id == normalized_user_id)
        return stmt

    async def read_decision_chain(self, user_id, decision_id):
        normalized_user_id = self._require_user_id(user_id)
        await self._load_decision_for_user(normalized_user_id, decision_id)
        await self._load_related_decisions(user_id=normalized_user_id, anchor=None)

    async def _load_decision_for_user(self, user_id, decision_id):
        return select(RoutingDecisionLog).where(RoutingDecisionLog.user_id == user_id)

    async def _load_related_decisions(self, user_id, anchor):
        return select(RoutingDecisionLog).where(RoutingDecisionLog.user_id == user_id)
"""


def test_rule_aj_passes_for_user_scoped_route_history_reads(tmp_path) -> None:
    path = _write(tmp_path / "route_history_service.py", _valid_source())
    assert check_rule_aj(path) == []


def test_rule_aj_fails_when_public_read_method_lacks_user_id(tmp_path) -> None:
    path = _write(tmp_path / "route_history_service.py", _valid_source().replace("read_recent_decisions(self, user_id, limit=20)", "read_recent_decisions(self, limit=20)"))
    violations = check_rule_aj(path)
    assert any(item.startswith("AJ002") for item in violations)


def test_rule_aj_fails_when_public_read_method_skips_normalization(tmp_path) -> None:
    path = _write(
        tmp_path / "route_history_service.py",
        _valid_source().replace("        normalized_user_id = self._require_user_id(user_id)\n", "", 1),
    )
    violations = check_rule_aj(path)
    assert any(item.startswith("AJ003") for item in violations)


def test_rule_aj_fails_when_helper_query_loses_user_filter(tmp_path) -> None:
    path = _write(
        tmp_path / "route_history_service.py",
        _valid_source().replace(
            "    async def _load_related_decisions(self, user_id, anchor):\n        return select(RoutingDecisionLog).where(RoutingDecisionLog.user_id == user_id)\n",
            "    async def _load_related_decisions(self, user_id, anchor):\n        return select(RoutingDecisionLog)\n",
        ),
    )
    violations = check_rule_aj(path)
    assert any(item.startswith("AJ007") for item in violations)
