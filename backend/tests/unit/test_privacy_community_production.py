from __future__ import annotations

import sys
import types
from uuid import uuid4

import pytest

from app.models.user_settings import UserSettings
from app.signals.privacy_community_intelligence import PrivacyBudget, PrivacyPreservingCommunityEngine

_evidence_module = types.ModuleType("evidence_pb2")
sys.modules.setdefault("app.gen", types.ModuleType("app.gen"))
sys.modules.setdefault("app.gen.sparkle", types.ModuleType("app.gen.sparkle"))
sys.modules.setdefault("app.gen.sparkle.rag", types.ModuleType("app.gen.sparkle.rag"))
rag_v1_module = types.ModuleType("app.gen.sparkle.rag.v1")
rag_v1_module.evidence_pb2 = _evidence_module
sys.modules.setdefault("app.gen.sparkle.rag.v1", rag_v1_module)

from app.services.community_signal_bridge import CommunitySignalBridge  # noqa: E402


def test_privacy_engine_suppresses_below_k_cohort():
    engine = PrivacyPreservingCommunityEngine()

    result = engine.aggregate_cohort_signal(
        requester_id=str(uuid4()),
        cohort_criteria={"goal_type": "exam_sprint", "subject": "math"},
        raw_values=[0.2, 0.4, 0.7, 0.9],
        stat_name="completion_rate",
        min_cohort_size=5,
    )

    assert result["allowed"] is False
    assert result["reason"] == "below_privacy_floor"
    assert result["stat"]["cohort_size"] == 4
    assert result["observation"]["requires_user_confirmation"] is True


def test_privacy_budget_exhaustion_blocks_more_queries():
    budget = PrivacyBudget(user_id="u1", max_epsilon=0.4)

    assert budget.spend(0.3) is True
    assert budget.spend(0.2) is False
    assert budget.total_epsilon_spent == pytest.approx(0.3)


class _ScalarResult:
    def __init__(self, value=None):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeSession:
    def __init__(self, rows):
        self.rows = list(rows)

    async def execute(self, _statement):
        return _ScalarResult(self.rows.pop(0) if self.rows else None)


@pytest.mark.asyncio
async def test_opt_out_removes_contributor_from_aggregate_values():
    enabled_user = uuid4()
    disabled_user = uuid4()
    disabled_settings = UserSettings(
        user_id=disabled_user,
        transparency_level=0,
        system_update_level=1,
        ai_reasoning_mode="balanced",
        task_reminders_enabled=True,
        community_intelligence_enabled=False,
    )
    db = _FakeSession([None, disabled_settings])
    bridge = CommunitySignalBridge(db)

    values = await bridge._filter_opted_in_values(
        [
            {"user_id": str(enabled_user), "value": 0.9},
            {"user_id": str(disabled_user), "value": 0.1},
        ]
    )

    assert values == [0.9]


def test_cohort_keys_keep_distinct_cohorts_isolated():
    first = CommunitySignalBridge._cohort_key({"goal_type": "exam_sprint", "subject": "math"})
    second = CommunitySignalBridge._cohort_key({"goal_type": "exam_sprint", "subject": "english"})

    assert first != second
    assert first == CommunitySignalBridge._cohort_key({"subject": "math", "goal_type": "exam_sprint"})
