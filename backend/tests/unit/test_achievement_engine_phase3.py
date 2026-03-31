from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import and_, select

from app.config import settings
from app.core.cache import cache_service
from app.models.achievement import (
    Achievement,
    AchievementRarity,
    AchievementType,
    UserAchievement,
    UserGalaxySkin,
    UserStreakStats,
    UserTitle,
    VisualEffectType,
)
from app.models.plan import Plan, PlanType
from app.models.shop import PhotonTransactionHistory
from app.models.task import Task, TaskStatus, TaskType
from app.services.achievement_engine import AchievementEngine, AchievementEvent


def _achievement(
    achievement_id: str,
    *,
    prerequisites: list[str] | None = None,
    reward_config: list[dict] | None = None,
    trigger_code: str = "TASKS_TOTAL",
    trigger_config: dict | None = None,
) -> Achievement:
    achievement = Achievement(
        id=achievement_id,
        name=f"Achievement {achievement_id}",
        description="phase3-test",
        type=AchievementType.MILESTONE,
        rarity=AchievementRarity.RARE,
        trigger_code=trigger_code,
        trigger_config=trigger_config or {"count": 1},
        prerequisites=prerequisites,
        visual_effect_type=VisualEffectType.SUPERNOVA,
        visual_config={"pulse": True},
        reward_config=reward_config or [],
        total_unlocked=0,
    )
    achievement.created_at = datetime(2026, 3, 10, 9, 0, 0)
    achievement.updated_at = datetime(2026, 3, 10, 9, 0, 0)
    return achievement


@pytest.mark.asyncio
async def test_check_prerequisites_requires_all_prerequisites(db_session, test_user):
    prerequisite = _achievement("prerequisite_root")
    child = _achievement("prerequisite_child", prerequisites=["prerequisite_root"])
    db_session.add_all([prerequisite, child])
    await db_session.commit()

    engine = AchievementEngine(db_session)

    assert await engine._check_prerequisites(test_user.id, child) is False

    db_session.add(
        UserAchievement(
            user_id=test_user.id,
            achievement_id=prerequisite.id,
            progress=1.0,
            unlocked_at=datetime(2026, 3, 10, 10, 0, 0),
        )
    )
    await db_session.commit()
    await cache_service.delete(
        f"{settings.APP_NAME}:achievement:{test_user.id}:{prerequisite.id}:unlocked"
    )

    assert await engine._check_prerequisites(test_user.id, child) is True


@pytest.mark.asyncio
async def test_grant_rewards_unlocks_titles_skins_and_freeze_charges(db_session, test_user):
    achievement = _achievement(
        "reward_bundle",
        reward_config=[
            {"type": "title", "value": "phase3_title", "display": "第三阶段见证者"},
            {"type": "galaxy_skin", "skin_id": "default"},
            {"type": "freeze_charge", "quantity": 1},
        ],
    )
    db_session.add(achievement)
    await db_session.commit()

    engine = AchievementEngine(db_session)
    await engine._grant_rewards(test_user.id, achievement)
    await db_session.commit()

    title_result = await db_session.execute(
        select(UserTitle).where(
            and_(
                UserTitle.user_id == test_user.id,
                UserTitle.title_id == "phase3_title",
            )
        )
    )
    skin_result = await db_session.execute(
        select(UserGalaxySkin).where(
            and_(
                UserGalaxySkin.user_id == test_user.id,
                UserGalaxySkin.skin_id == "default",
            )
        )
    )
    stats_result = await db_session.execute(
        select(UserStreakStats).where(UserStreakStats.user_id == test_user.id)
    )

    assert title_result.scalar_one_or_none() is not None
    assert skin_result.scalar_one_or_none() is not None
    assert stats_result.scalar_one().freeze_charges == 2


@pytest.mark.asyncio
async def test_grant_rewards_records_photon_balance_and_history(db_session, test_user):
    achievement = _achievement(
        "reward_photons",
        reward_config=[
            {"type": "photon", "quantity": 88},
        ],
    )
    db_session.add(achievement)
    await db_session.commit()

    engine = AchievementEngine(db_session)
    await engine._grant_rewards(test_user.id, achievement)
    await db_session.commit()
    await db_session.refresh(test_user)

    transaction_result = await db_session.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == test_user.id
        )
    )
    transaction = transaction_result.scalar_one_or_none()

    assert test_user.photon_balance == 88
    assert transaction is not None
    assert transaction.transaction_type == "grant_achievement"
    assert transaction.amount == 88
    assert transaction.related_item_id == achievement.id


@pytest.mark.asyncio
async def test_streak_days_progress_uses_streak_stats(db_session, test_user):
    achievement = _achievement(
        "streak_test",
        trigger_code="STREAK_DAYS",
        trigger_config={"days": 10},
    )
    stats = UserStreakStats(
        user_id=test_user.id,
        current_streak=7,
        max_streak=7,
    )
    db_session.add_all([achievement, stats])
    await db_session.commit()

    engine = AchievementEngine(db_session)
    progress, current, target = await engine._evaluate_progress(test_user.id, achievement)

    assert current == 7
    assert target == 10
    assert progress == pytest.approx(0.7)


@pytest.mark.asyncio
async def test_sprint_progress_variants(db_session, test_user):
    now = datetime(2026, 3, 10, 9, 0, 0)
    plan1 = Plan(
        user_id=test_user.id,
        name="sprint-1",
        type=PlanType.SPRINT,
        is_active=False,
        progress=1.0,
    )
    plan1.updated_at = now
    plan2 = Plan(
        user_id=test_user.id,
        name="sprint-2",
        type=PlanType.SPRINT,
        is_active=False,
        progress=0.9,
    )
    plan2.updated_at = now - timedelta(days=1)
    plan3 = Plan(
        user_id=test_user.id,
        name="sprint-3",
        type=PlanType.SPRINT,
        is_active=False,
        progress=0.7,
    )
    plan3.updated_at = now - timedelta(days=2)

    achievement_total = _achievement(
        "sprint_total_test",
        trigger_code="SPRINTS_TOTAL",
        trigger_config={"count": 3},
    )
    achievement_perfect = _achievement(
        "sprint_perfect_test",
        trigger_code="SPRINT_PERFECT",
        trigger_config={"count": 1},
    )
    achievement_streak = _achievement(
        "sprint_streak_test",
        trigger_code="SPRINTS_STREAK",
        trigger_config={"streak": 2},
    )
    achievement_ahead = _achievement(
        "sprint_ahead_test",
        trigger_code="SPRINT_AHEAD",
        trigger_config={"count": 1},
    )

    db_session.add_all([
        plan1,
        plan2,
        plan3,
        achievement_total,
        achievement_perfect,
        achievement_streak,
        achievement_ahead,
    ])
    await db_session.commit()

    engine = AchievementEngine(db_session)

    progress, current, target = await engine._evaluate_progress(test_user.id, achievement_total)
    assert current == 3
    assert target == 3
    assert progress == 1.0

    progress, current, target = await engine._evaluate_progress(test_user.id, achievement_perfect)
    assert current == 1
    assert target == 1
    assert progress == 1.0

    progress, current, target = await engine._evaluate_progress(test_user.id, achievement_streak)
    assert current == 2
    assert target == 2
    assert progress == 1.0

    progress, current, target = await engine._evaluate_progress(
        test_user.id,
        achievement_ahead,
        completion_rate=1.0,
        days_ahead=2,
    )
    assert current == 2
    assert target == 1
    assert progress == 1.0


@pytest.mark.asyncio
async def test_combo_info_added_when_multiple_achievements_unlock(db_session, test_user):
    achievement_one = _achievement("combo_one", trigger_code="TASKS_TOTAL", trigger_config={"count": 1})
    achievement_two = _achievement("combo_two", trigger_code="TASKS_TOTAL", trigger_config={"count": 1})
    task = Task(
        user_id=test_user.id,
        title="combo-task",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=25,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
        completed_at=datetime(2026, 3, 10, 10, 0, 0),
    )
    db_session.add_all([achievement_one, achievement_two, task])
    await db_session.commit()

    engine = AchievementEngine(db_session)
    db_session.sync_session.info["external_transaction_managed"] = True
    unlocked = await engine.process_event(
        user_id=test_user.id,
        event_type=AchievementEvent.TASK_COMPLETED,
    )

    assert len(unlocked) == 2
    for entry in unlocked:
        assert entry["combo_info"]["combo"] >= 2


@pytest.mark.asyncio
async def test_unlock_achievement_is_idempotent_for_existing_unlocked_record(db_session, test_user):
    achievement = _achievement("already_unlocked")
    existing_record = UserAchievement(
        user_id=test_user.id,
        achievement_id=achievement.id,
        progress=1.0,
        unlocked_at=datetime(2026, 3, 10, 10, 0, 0),
    )
    achievement.total_unlocked = 1
    db_session.add_all([achievement, existing_record])
    await db_session.commit()

    engine = AchievementEngine(db_session)
    result = await engine._unlock_achievement(str(test_user.id), achievement)

    assert result is None
    await db_session.refresh(achievement)
    assert achievement.total_unlocked == 1


@pytest.mark.asyncio
async def test_unlock_visual_element_delegates_to_visual_element_service(db_session, test_user):
    engine = AchievementEngine(db_session)

    with patch("app.services.visual_element_service.VisualElementService") as service_cls:
        service = service_cls.return_value
        service.unlock_element = AsyncMock(return_value=AsyncMock(success=True))

        await engine._unlock_visual_element(str(test_user.id), "bg_aurora", "achv_1")

    service.unlock_element.assert_awaited_once()
    request = service.unlock_element.await_args.kwargs["request"]
    assert request.element_id == "bg_aurora"
    assert request.source == "achievement"
    assert request.source_id == "achv_1"


@pytest.mark.asyncio
async def test_notify_unlocks_sends_websocket_payload_with_photon_reward(db_session, test_user):
    engine = AchievementEngine(db_session)
    ws_manager = AsyncMock()
    unlocked_payload = [
        {
            "achievement_id": "reward_bundle",
            "name": "奖励包",
            "rarity": AchievementRarity.EPIC,
            "visual_effect": {"pulse": True},
            "visual_effect_type": VisualEffectType.SUPERNOVA,
            "rewards": [{"type": "photon", "quantity": 88}],
            "is_first": False,
            "combo_info": {"combo": 2},
            "unlocked_at": datetime(2026, 3, 10, 10, 0, 0),
        }
    ]

    with patch("app.core.websocket.get_ws_manager", return_value=ws_manager):
        await engine._notify_unlocks(str(test_user.id), unlocked_payload)

    ws_manager.send_personal_message.assert_awaited_once()
    message, recipient = ws_manager.send_personal_message.await_args.args
    assert recipient == str(test_user.id)
    assert message["type"] == "achievement_unlock"
    assert message["achievement_data"]["achievement_id"] == "reward_bundle"
    assert message["achievement_data"]["photon_granted"] == 88
    assert message["achievement_data"]["has_photon_reward"] is True
    assert message["achievement_data"]["combo_info"] == {"combo": 2}


@pytest.mark.asyncio
async def test_notify_milestones_sends_websocket_payload(db_session, test_user):
    engine = AchievementEngine(db_session)
    ws_manager = AsyncMock()
    milestones = [
        {
            "achievement_id": "reward_bundle",
            "achievement_name": "奖励包",
            "milestone_percent": 75,
            "message": "进度达到75%",
            "type": "progress_milestone",
        }
    ]

    with patch("app.core.websocket.get_ws_manager", return_value=ws_manager):
        await engine._notify_milestones(str(test_user.id), milestones)

    ws_manager.send_personal_message.assert_awaited_once()
    message, recipient = ws_manager.send_personal_message.await_args.args
    assert recipient == str(test_user.id)
    assert message["type"] == "achievement_milestone"
    assert message["data"]["milestone_percent"] == 75


@pytest.mark.asyncio
async def test_grant_rewards_schedules_photon_compensation_after_commit_failure(db_session, test_user):
    achievement = _achievement(
        "reward_retry",
        reward_config=[{"type": "photon", "quantity": 66}],
    )
    engine = AchievementEngine(db_session)
    callbacks = []

    def capture_callback(callback):
        callbacks.append(callback)

    engine._enqueue_after_commit = capture_callback
    engine._schedule_photon_reward_retry = AsyncMock()

    with patch("app.services.photon_service.PhotonService.grant_photons", AsyncMock(side_effect=RuntimeError("boom"))):
        await engine._grant_rewards(str(test_user.id), achievement)

    assert len(callbacks) == 1
    await callbacks[0]()
    engine._schedule_photon_reward_retry.assert_awaited_once_with(
        user_id=str(test_user.id),
        achievement_id=achievement.id,
        achievement_name=achievement.name,
        quantity=66,
    )
