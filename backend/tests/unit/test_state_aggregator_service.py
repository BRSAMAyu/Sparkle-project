from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.achievement import Achievement, AchievementRarity, AchievementType, UserAchievement
from app.models.calendar_event import CalendarEvent
from app.models.achievement import UserStreakStats
from app.models.focus import FocusSession, FocusStatus, FocusType
from app.models.memory import EpisodicMemory
from app.state_aggregator.service import StateAggregatorService


@pytest.mark.asyncio
async def test_state_aggregator_returns_only_requested_fields(db_session, monkeypatch) -> None:
    user_id = uuid4()
    now = datetime.utcnow()

    db_session.add(
        EpisodicMemory(
            user_id=user_id,
            summary="已逾期承诺",
            source_type="chat",
            source_id="session_1",
            source_lane="inferred_extraction",
            subject_type="commitment",
            occurred_at=now - timedelta(days=1),
            due_at=now - timedelta(hours=4),
            evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
        )
    )
    await db_session.commit()

    service = StateAggregatorService(db_session)
    monkeypatch.setattr(
        service.predictive_service,
        "get_next_intent_forecast",
        AsyncMock(return_value={"predicted_action_type": "light_review"}),
    )

    state = await service.get_user_state(user_id, required_fields=("commitment_summary",))

    assert state.commitment_summary is not None
    assert state.commitment_summary.value.overdue_count == 1
    assert state.recent_person_mentions is None
    assert state.engagement_state is None
    assert state.learning_state is None


@pytest.mark.asyncio
async def test_state_aggregator_builds_social_engagement_and_learning_fields(db_session, monkeypatch) -> None:
    user_id = uuid4()
    now = datetime.utcnow()
    db_session.add_all(
        [
            EpisodicMemory(
                user_id=user_id,
                summary="最近提到一位学习伙伴",
                source_type="chat",
                source_id="session_1",
                source_lane="inferred_extraction",
                subject_type="person_mention",
                occurred_at=now - timedelta(days=1),
                evidence_refs=[{"type": "chat_turn", "id": "turn_1"}],
            ),
            EpisodicMemory(
                user_id=user_id,
                summary="最近提到一段与他人的关系动态",
                source_type="chat",
                source_id="session_1",
                source_lane="inferred_extraction",
                subject_type="relationship",
                occurred_at=now - timedelta(days=2),
                evidence_refs=[{"type": "chat_turn", "id": "turn_2"}],
            ),
            FocusSession(
                user_id=user_id,
                task_id=None,
                start_time=now - timedelta(hours=2),
                end_time=now - timedelta(hours=1, minutes=30),
                duration_minutes=30,
                focus_type=FocusType.POMODORO,
                status=FocusStatus.COMPLETED,
            ),
            UserStreakStats(
                user_id=user_id,
                current_streak=4,
                max_streak=6,
                last_activity_date=now - timedelta(hours=1),
            ),
        ]
    )
    await db_session.commit()

    service = StateAggregatorService(db_session)
    monkeypatch.setattr(
        service.predictive_service,
        "get_next_intent_forecast",
        AsyncMock(
            return_value={
                "predicted_action_type": "light_review",
                "within_category_preference": {
                    "preferred_tool": "reopen_error_book",
                    "confidence": 0.82,
                },
            }
        ),
    )

    state = await service.get_user_state(
        user_id,
        required_fields=("recent_person_mentions", "engagement_state", "learning_state"),
    )

    assert state.recent_person_mentions is not None
    assert len(state.recent_person_mentions.value.mentions) == 1
    assert state.recent_person_mentions.value.relationship_count == 1

    assert state.engagement_state is not None
    assert state.engagement_state.value.session_count_7d == 1
    assert state.engagement_state.value.streak == 4
    assert state.engagement_state.value.last_active_at is not None

    assert state.learning_state is not None
    assert state.learning_state.value.within_category_preference == {
        "preferred_tool": "reopen_error_book",
        "confidence": 0.82,
    }


@pytest.mark.asyncio
async def test_state_aggregator_builds_achievement_and_calendar_fields(db_session, monkeypatch) -> None:
    user_id = uuid4()
    now = datetime.utcnow()
    achievement = Achievement(
        id="streak_7",
        name="七日连胜",
        type=AchievementType.STREAK,
        rarity=AchievementRarity.RARE,
        trigger_code="STREAK_DAYS",
    )
    db_session.add(achievement)
    await db_session.flush()

    db_session.add(
        UserAchievement(
            user_id=user_id,
            achievement_id=achievement.id,
            progress=1.0,
            progress_value=7,
            progress_target=7,
            unlocked_at=now - timedelta(days=1),
        )
    )
    db_session.add(
        CalendarEvent(
            user_id=user_id,
            title="热力学复盘",
            start_time=now + timedelta(hours=3),
            end_time=now + timedelta(hours=4),
            plan_id=None,
            task_id=uuid4(),
            source="manual",
        )
    )
    await db_session.commit()

    service = StateAggregatorService(db_session)
    monkeypatch.setattr(
        service.predictive_service,
        "get_next_intent_forecast",
        AsyncMock(return_value={"exam_urgency": {"days_left": 9, "urgent": True}}),
    )

    state = await service.get_user_state(
        user_id,
        required_fields=("achievement_summary", "calendar_context"),
    )

    assert state.schema_version == "user_state.v1.6"
    assert state.achievement_summary is not None
    assert state.achievement_summary.value.recent_unlocks[0].achievement_id == "streak_7"
    assert state.achievement_summary.value.total_achievement_score >= 2.0
    assert state.calendar_context is not None
    assert state.calendar_context.value.workload_density in {"low", "medium", "high"}
    assert state.calendar_context.value.exam_urgency == {"days_left": 9, "urgent": True}


@pytest.mark.asyncio
async def test_state_aggregator_builds_recent_reflections_summary(db_session) -> None:
    user_id = uuid4()
    now = datetime.utcnow()
    db_session.add_all(
        [
            EpisodicMemory(
                user_id=user_id,
                summary="最近一段时间计划推进反复停住，说明当前推进颗粒度仍然偏重。",
                source_type="reflection",
                source_id="reflection-1",
                source_lane="inferred_extraction",
                subject_type="self",
                occurred_at=now - timedelta(hours=2),
                tags=["stage25:reflection", "reflection_category:plan_stall"],
                evidence_refs=[{"type": "summary", "id": "reflection-1"}],
            ),
            EpisodicMemory(
                user_id=user_id,
                summary="同一天连续失败说明当前负荷已经溢出。",
                source_type="reflection",
                source_id="reflection-2",
                source_lane="inferred_extraction",
                subject_type="self",
                occurred_at=now - timedelta(days=1),
                tags=["stage25:reflection", "reflection_category:overload"],
                evidence_refs=[{"type": "summary", "id": "reflection-2"}],
            ),
        ]
    )
    await db_session.commit()

    state = await StateAggregatorService(db_session).get_user_state(
        user_id,
        required_fields=("recent_reflections",),
    )

    assert state.recent_reflections is not None
    assert state.recent_reflections.value.count == 2
    assert state.recent_reflections.value.last_category == "plan_stall"
