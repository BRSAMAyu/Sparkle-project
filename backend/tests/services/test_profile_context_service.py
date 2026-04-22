from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.models.cognitive import BehaviorPattern
from app.models.error_book import ErrorRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.personalization.preference_service import PreferenceService
from app.services.profile_context_service import ProfileContextService
from app.state_aggregator.schema import (
    MetacognitionDimensionSummaryValue,
    MetacognitionProfileSummaryValue,
    SRLPhaseSummaryValue,
    StateFieldEnvelope,
    UserStateV1,
    WorkingMemorySnapshotValue,
    WorkingMemorySnapshotValueItem,
)


@pytest.mark.asyncio
async def test_profile_context_service_maps_patterns_to_policy_signals(db_session, test_user):
    db_session.add_all(
        [
            BehaviorPattern(
                user_id=test_user.id,
                pattern_name="The Perfectionism-Avoidance Loop",
                pattern_type="cognitive",
                confidence_score=0.96,
                description="English placeholder",
                solution_text="English placeholder",
            ),
            BehaviorPattern(
                user_id=test_user.id,
                pattern_name="The Night-Time Energy Mismatch Loop",
                pattern_type="cognitive/execution",
                confidence_score=0.93,
                description="English placeholder",
                solution_text="English placeholder",
            ),
        ]
    )
    await db_session.commit()

    service = ProfileContextService(db_session, redis=None)

    context = await service.get_profile_context(test_user.id)

    patterns = {
        item.pattern_name: item
        for item in context.cognitive_summary.active_patterns
    }

    assert "完美主义回避循环" in patterns
    assert "夜间能量错配循环" in patterns
    assert patterns["完美主义回避循环"].policy_signals == [
        "task.difficulty.start_easy",
        "llm.feedback.emphasize_progress",
    ]
    assert patterns["夜间能量错配循环"].policy_signals == [
        "push.timing.earlier_reminder",
    ]
    assert "risk.execution_delay" in context.cognitive_summary.risk_signals
    assert "risk.focus_fatigue" in context.cognitive_summary.risk_signals
    assert context.user_insight_state is not None
    assert context.user_insight_state.constraints


@pytest.mark.asyncio
async def test_profile_context_service_backfills_knowledge_summary_without_node_statuses(
    db_session,
    test_user,
):
    db_session.add(
        ErrorRecord(
            user_id=test_user.id,
            subject_code="cs",
            chapter="指针与内存",
            question_text="什么是指针",
            user_answer="我把 p 当成了值本身",
            correct_answer="p 是地址，*p 才是值",
            mastery_level=0.18,
            suggested_concepts=["指针基础"],
            latest_analysis={"recommended_knowledge": ["地址与解引用"]},
        )
    )
    db_session.add(
        Task(
            user_id=test_user.id,
            title="完成一次指针复盘",
            type=TaskType.ERROR_FIX,
            tags=[],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            actual_minutes=28,
            priority=3,
        )
    )
    await db_session.commit()

    service = ProfileContextService(db_session, redis=None)

    context = await service.get_profile_context(test_user.id)

    assert context.knowledge_summary.overall_mastery > 0
    assert context.knowledge_summary.weak_spots
    assert context.knowledge_summary.weak_spots[0].node_name == "指针与内存"
    assert context.knowledge_summary.recent_mastery_changes
    assert context.knowledge_summary.recent_mastery_changes[0].node_name == "完成一次指针复盘"
    assert "指针与内存" in context.knowledge_summary.active_learning_subjects
    assert context.user_insight_state is not None
    assert context.user_insight_state.recent_wins


class _RedisCache:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self._store[key] = value

    async def delete(self, *keys: str):
        for key in keys:
            self._store.pop(key, None)


@pytest.mark.asyncio
async def test_profile_context_service_refreshes_stale_cached_preference_version(db_session):
    redis = _RedisCache()
    user = User(username="profilecache", email="profilecache@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    service = ProfileContextService(db_session, redis=redis)
    first = await service.get_profile_context(user.id)
    assert first.preference_version == 1
    stale_cache = dict(redis._store)

    await PreferenceService(db_session, redis).update_explicit(user.id, {"depth_preference": 0.2})
    redis._store.update(stale_cache)

    refreshed = await service.get_profile_context(user.id)

    assert refreshed.preference_version == 2
    assert refreshed.preferences["depth_preference"] == 0.2


@pytest.mark.asyncio
async def test_profile_context_service_embeds_user_state_v1_payload(db_session, test_user, monkeypatch):
    async def _fake_get_user_state(self, user_id, required_fields, **kwargs):
        assert user_id == test_user.id
        if tuple(required_fields) == ("srl_phase",):
            return UserStateV1(
                user_id=user_id,
                srl_phase=StateFieldEnvelope(
                    value=SRLPhaseSummaryValue(
                        current_phase="performance",
                        phase_started_at=datetime(2026, 4, 22, 9, 0, 0),
                        confidence=0.81,
                        source="aggregator",
                    ),
                    computed_at=datetime(2026, 4, 22, 9, 5, 0),
                    source_snapshot_ids=("srl_phase:test",),
                    freshness_seconds=0,
                ),
            )
        return UserStateV1(
            user_id=user_id,
            working_memory_snapshot=StateFieldEnvelope(
                value=WorkingMemorySnapshotValue(
                    active_session_id="session-1",
                    items=(
                        WorkingMemorySnapshotValueItem(
                            summary="今天先把错题复盘完。",
                            subject_type="task",
                            mention_count=2,
                            consolidated=False,
                            last_seen_at=datetime(2026, 4, 22, 9, 0, 0),
                        ),
                    ),
                ),
                computed_at=datetime(2026, 4, 22, 9, 5, 0),
                source_snapshot_ids=("wm:test",),
                freshness_seconds=0,
            ),
            metacognition_profile=StateFieldEnvelope(
                value=MetacognitionProfileSummaryValue(
                    items=(
                        MetacognitionDimensionSummaryValue(
                            dim="time_estimation_bias",
                            sample_size=28,
                            bias_mean=0.18,
                            trend="improving",
                        ),
                    )
                ),
                computed_at=datetime(2026, 4, 22, 9, 6, 0),
                source_snapshot_ids=("metacognition:time_estimation_bias",),
                freshness_seconds=0,
            ),
        )

    monkeypatch.setattr(
        "app.services.profile_context_service.StateAggregatorService.get_user_state",
        _fake_get_user_state,
    )
    monkeypatch.setattr(
        "app.services.profile_context_service.MetacognitionService.get_snapshot",
        AsyncMock(return_value={"generated_at": "2026-04-22T09:06:00", "dimensions": []}),
    )
    monkeypatch.setattr(
        "app.services.profile_context_service.MetacognitionService.build_dashboard_payload",
        AsyncMock(return_value={"available": False, "cards": []}),
    )
    monkeypatch.setattr(
        "app.services.profile_context_service.MetacognitionService.build_prompt_process_scaffolding",
        AsyncMock(return_value=None),
    )

    context = await ProfileContextService(db_session, redis=None).get_profile_context(test_user.id)

    assert context.user_state_v1 is not None
    assert context.user_state_v1["schema_version"] == "user_state.v1.13"
    assert context.user_state_v1["working_memory_snapshot"]["value"]["items"][0]["summary"] == "今天先把错题复盘完。"
    assert context.user_state_v1["metacognition_profile"]["value"]["items"][0]["dim"] == "time_estimation_bias"
