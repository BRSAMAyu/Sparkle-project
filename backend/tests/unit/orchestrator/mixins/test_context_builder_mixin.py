"""
Unit tests for ContextBuilderMixin.

Tests the context building methods that assemble user/session/plan context
for the orchestrator.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestration.context_builder import ContextBuilderMixin


# Create a minimal class that includes the mixin
class MinimalOrchestrator(ContextBuilderMixin):
    """Minimal orchestrator with ContextBuilderMixin for testing."""
    def __init__(self, redis_client=None):
        self.redis = redis_client or MagicMock()
        self.context_pruner = MagicMock()
        self.state_manager = MagicMock()


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return MinimalOrchestrator()


def test_build_profile_payload_with_full_data(orchestrator):
    """Test _build_profile_payload with complete user data."""
    user_context_data = {
        "nickname": "TestUser",
        "timezone": "Asia/Shanghai",
        "language": "zh-CN",
        "is_pro": False,
        "persona_type": "growth",
        "preferences": {"flame_level": 5}
    }
    preferences = {"difficulty": 0.7}
    llm_profile_data = {"temperature": 0.8}

    result = orchestrator._build_profile_payload(
        user_context_data=user_context_data,
        preferences=preferences,
        llm_profile_data=llm_profile_data,
        preference_version=1,
        experiment_cohort="test_cohort",
    )

    assert result["identity"]["nickname"] == "TestUser"
    assert result["identity"]["timezone"] == "Asia/Shanghai"
    assert result["identity"]["flame_level"] == 5
    assert result["preferences"]["difficulty"] == 0.7
    assert result["llm_profile"]["temperature"] == 0.8
    assert result["preference_version"] == 1
    assert result["experiment_cohort"] == "test_cohort"


def test_build_profile_payload_with_minimal_data(orchestrator):
    """Test _build_profile_payload with minimal/missing data."""
    result = orchestrator._build_profile_payload(
        user_context_data=None,
        preferences=None,
        llm_profile_data=None,
        preference_version=0,
        experiment_cohort=None,
    )

    assert result["identity"] == {}
    assert result["preferences"] == {}
    assert result["llm_profile"] == {}
    assert result["preference_version"] == 0
    assert result["experiment_cohort"] is None


def test_build_profile_payload_extracts_prefs_from_user_context(orchestrator):
    """Test that preferences are extracted from user_context_data if not provided separately."""
    user_context_data = {
        "nickname": "User",
        "preferences": {"difficulty": 0.5, "verbosity": "concise"}
    }

    result = orchestrator._build_profile_payload(
        user_context_data=user_context_data,
        preferences=None,
        llm_profile_data=None,
        preference_version=1,
        experiment_cohort=None,
    )

    assert result["preferences"]["difficulty"] == 0.5
    assert result["preferences"]["verbosity"] == "concise"


def test_build_profile_payload_with_valid_llm_profile_string(orchestrator):
    """Test non-dict llm_profile_data is ignored by the helper."""
    import json
    llm_profile_json = json.dumps({"temperature": 0.9, "tone": "formal"})

    result = orchestrator._build_profile_payload(
        user_context_data=None,
        preferences=None,
        llm_profile_data=llm_profile_json,
        preference_version=1,
        experiment_cohort=None,
    )

    assert result["llm_profile"] == {}


@pytest.mark.asyncio
async def test_attach_stage34_memory_context_injects_goal_and_episodic_top_level(orchestrator, monkeypatch):
    plan = SimpleNamespace(
        id="plan-1",
        name="热力学冲刺",
        is_active=True,
        type=SimpleNamespace(value="growth"),
        plan_stage=SimpleNamespace(value="daily"),
        subject="physics",
        target_date=None,
        progress=0.4,
    )
    memory = SimpleNamespace(
        id="memory-1",
        summary="上次复盘时发现自己总把熵增方向和系统边界混在一起。",
        subject_type="self",
        source_type="direct_capture",
        occurred_at=None,
        importance_score=0.8,
        confidence=0.7,
        tags=["thermo"],
    )

    monkeypatch.setattr(
        "app.orchestration.context_builder.PlanService.list_active",
        AsyncMock(return_value=[plan]),
    )
    monkeypatch.setattr(
        "app.orchestration.context_builder.MemoryService.list_recent_episodic",
        AsyncMock(return_value=[memory]),
    )

    payload = {"cognitive_context": {}}
    result = await orchestrator._attach_stage34_memory_context(
        payload,
        user_id="00000000-0000-0000-0000-000000000123",
        db_session=MagicMock(),
    )

    assert result["active_goals"][0]["title"] == "热力学冲刺"
    assert result["episodic_memories"][0]["summary"].startswith("上次复盘时发现")
    assert result["cognitive_context"]["active_goals"][0]["title"] == "热力学冲刺"
    assert result["cognitive_context"]["episodic_memories"][0]["subject_type"] == "self"


@pytest.mark.asyncio
async def test_attach_stage34_memory_context_returns_empty_lists_when_no_records(orchestrator, monkeypatch):
    monkeypatch.setattr(
        "app.orchestration.context_builder.PlanService.list_active",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.orchestration.context_builder.MemoryService.list_recent_episodic",
        AsyncMock(return_value=[]),
    )

    result = await orchestrator._attach_stage34_memory_context(
        {},
        user_id="00000000-0000-0000-0000-000000000123",
        db_session=MagicMock(),
    )

    assert result["active_goals"] == []
    assert result["episodic_memories"] == []
