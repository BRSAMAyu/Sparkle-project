"""Shared fixtures and helpers for Signal-to-Action Spine tests."""

from __future__ import annotations

import itertools
from unittest.mock import AsyncMock

import pytest

from app.signals.types import ActionableSignal, _uid
from app.signals.self_model import SparkleSelfModelService
from app.signals.achievement_reinforcement import AchievementReinforcementConsumer
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.aurora_wake import AuroraWakeJudge
from app.signals.community_signal import CommunitySignalDetector
from app.signals.spine_orchestrator import SpineOrchestrator
from app.signals.signal_ranker import SignalRanker
from tests.unit.spine._helpers import FakeRedis, FakeRedisWithHset, _make_redis_mock


# ── Helper Factories ──────────────────────────────────────────────────

_make_signal_counter = itertools.count()


def _make_signal(state_key: str, priority: str = "medium", confidence: float = 0.8,
                 scope: str = "sprint", possible_effects: list[str] | None = None,
                 claim: str | None = None) -> ActionableSignal:
    return ActionableSignal(
        signal_id=f"sig_{state_key}_{next(_make_signal_counter)}",
        source_event_ids=["evt_1"],
        source_system="test",
        state_key=state_key,
        claim=claim or f"test_{state_key}",
        confidence=confidence,
        evidence_summary="test",
        scope=scope,
        ttl_hours=24,
        possible_effects=possible_effects if possible_effects is not None else ["effect_1"],
        priority=priority,
    )


def _make_lifecycle_skill(
    *,
    skill_id: str = "skill_life_1",
    scope: str = "personal",
    effective_count: int = 5,
    sample_size: int = 6,
    applicable_when: dict | None = None,
):
    from app.signals.types import SkillEntry

    return SkillEntry(
        skill_id=skill_id,
        scope=scope,
        source_policy_key="repair_knowledge_bottleneck",
        strategy={"intervention_summary": "Show a worked example before the drill."},
        applicable_when=applicable_when or {"goal_mode": "exam_rescue", "state_key": "knowledge_transfer"},
        evidence={"effective_count": effective_count, "total_observed": sample_size, "avg_confidence": 0.84},
        privacy={"contains_personal_data": scope == "personal", "shareable": scope != "personal"},
        effective_count=effective_count,
        sample_size=sample_size,
    )


# ── Pytest Fixtures ───────────────────────────────────────────────────

@pytest.fixture
def fake_redis():
    return FakeRedis()


@pytest.fixture
def self_model_svc(fake_redis):
    return SparkleSelfModelService(redis_client=fake_redis)


@pytest.fixture
def achievement_consumer():
    return AchievementReinforcementConsumer()


@pytest.fixture
def recall_detector():
    return RecallOpportunityDetector()


@pytest.fixture
def wake_judge():
    return AuroraWakeJudge()


@pytest.fixture
def community_detector():
    return CommunitySignalDetector()


@pytest.fixture
def policy_engine():
    return PolicyEngine()


@pytest.fixture
def spine():
    return SpineOrchestrator(_make_redis_mock())


@pytest.fixture
def ranker():
    return SignalRanker()
