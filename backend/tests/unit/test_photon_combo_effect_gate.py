"""PHOTON-TUNE · combo 效果门槛 + 日上限/边际递减（D-MONETIZE 审计 §1.6-2/R2）。

审计背景：TOUR 活栈 10 冲刺 × 7 任务批量归档（actual_minutes≈0）单日刷出
5050 光子，vs 诚实日均 30-80——combo 加成 combo×10 无日上限是主放大器。

本文件用「新旧对照」钉住经济语义变更：
- 旧行为（刷量路径）= PHOTON_COMBO_EFFECT_GATE_ENABLED=False：actual_minutes=0
  的归档照样进 combo、combo×10 全额发放；
- 新行为（门槛拦截，默认开）= actual_minutes<1 的归档不进 combo 不发加成；
  有效归档的加成受日上限（PHOTON_COMBO_DAILY_CAP）与边际递减
  （PHOTON_COMBO_DAILY_DECAY_FACTOR/_FLOOR）约束，全部数值走 settings。
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.cache import cache_service
from app.models.achievement import Achievement, AchievementRarity, AchievementType, VisualEffectType
from app.models.shop import PhotonTransactionHistory
from app.models.task import Task, TaskStatus, TaskType
from app.services.achievement_engine import AchievementEngine, AchievementEvent
from app.services.photon_service import PhotonTransactionType


def _achievement(achievement_id: str) -> Achievement:
    return Achievement(
        id=achievement_id,
        name=f"Achievement {achievement_id}",
        description="photon-tune-combo",
        type=AchievementType.MILESTONE,
        rarity=AchievementRarity.RARE,
        trigger_code="TASKS_TOTAL",
        trigger_config={"count": 1},
        visual_effect_type=VisualEffectType.SUPERNOVA,
        visual_config={"pulse": True},
        reward_config=[],
        total_unlocked=0,
    )


def _combo_task(user_id) -> Task:
    return Task(
        user_id=user_id,
        title="photon-tune-combo-task",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=25,
        difficulty=1,
        energy_cost=1,
        status=TaskStatus.COMPLETED,
        completed_at=datetime(2026, 3, 10, 10, 0, 0),
    )


async def _bonus_rows(db, user_id) -> list[PhotonTransactionHistory]:
    result = await db.execute(
        select(PhotonTransactionHistory).where(
            PhotonTransactionHistory.user_id == user_id,
            PhotonTransactionHistory.transaction_type == PhotonTransactionType.GRANT_BONUS,
        )
    )
    return list(result.scalars().all())


# ============ 效果门槛：_combo_effective_unlock_count ============


@pytest.mark.asyncio
async def test_gate_blocks_zero_minute_archive_new_behavior(db_session, test_user, monkeypatch):
    """新行为（默认开）：actual_minutes=0 的批量归档贡献 0 有效解锁。"""
    engine = AchievementEngine(db_session)
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {"actual_minutes": 0}) == 0
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {}) == 0
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {"actual_minutes": None}) == 0


@pytest.mark.asyncio
async def test_gate_passes_real_learning_minutes(db_session, test_user, monkeypatch):
    """真实学习时长（actual_minutes ≥ 阈值）照常计入；阈值走 settings。"""
    engine = AchievementEngine(db_session)
    monkeypatch.setattr(settings, "PHOTON_COMBO_EFFECT_MIN_MINUTES", 10)
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {"actual_minutes": 25}) == 2
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {"actual_minutes": 9}) == 0
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {"actual_minutes": 10}) == 2


@pytest.mark.asyncio
async def test_gate_disabled_restores_old_farming_behavior(db_session, test_user, monkeypatch):
    """旧行为对照（回滚路径）：开关关闭时 0 分钟归档照样全额计入。"""
    monkeypatch.setattr(settings, "PHOTON_COMBO_EFFECT_GATE_ENABLED", False)
    engine = AchievementEngine(db_session)
    assert engine._combo_effective_unlock_count(AchievementEvent.TASK_COMPLETED, 2, {"actual_minutes": 0}) == 2


@pytest.mark.asyncio
async def test_non_task_events_not_gated(db_session, test_user):
    """契约/签到等自带真实行为判据的事件不受门槛影响。"""
    engine = AchievementEngine(db_session)
    assert engine._combo_effective_unlock_count(AchievementEvent.CONTRACT_COMPLETED, 1, {}) == 1
    assert engine._combo_effective_unlock_count(AchievementEvent.DAILY_CHECKIN, 1, {}) == 1


# ============ 门槛 × process_event 端到端（批量归档 vs 真实归档） ============


@pytest.mark.asyncio
async def test_process_event_batch_archive_gets_no_combo(db_session, test_user):
    """端到端新行为：批量归档（actual_minutes=0）解锁成就也不进 combo、零加成。"""
    db_session.add_all([_achievement("gate_one"), _achievement("gate_two"), _combo_task(test_user.id)])
    await db_session.commit()

    engine = AchievementEngine(db_session)
    db_session.sync_session.info["external_transaction_managed"] = True
    unlocked = await engine.process_event(
        user_id=test_user.id,
        event_type=AchievementEvent.TASK_COMPLETED,
        actual_minutes=0,
    )

    assert len(unlocked) == 2
    for entry in unlocked:
        assert entry.get("combo_info") is None
    assert await _bonus_rows(db_session, test_user.id) == []


@pytest.mark.asyncio
async def test_process_event_real_archive_builds_combo_and_grants(db_session, test_user):
    """端到端新行为：真实归档（actual_minutes=25）解锁 2 个即 combo=2；本例
    combo<3 不发加成（既有分档语义不变），combo≥3 的发放面见下组直调测试。"""
    db_session.add_all([_achievement("real_one"), _achievement("real_two"), _combo_task(test_user.id)])
    await db_session.commit()

    engine = AchievementEngine(db_session)
    db_session.sync_session.info["external_transaction_managed"] = True
    unlocked = await engine.process_event(
        user_id=test_user.id,
        event_type=AchievementEvent.TASK_COMPLETED,
        actual_minutes=25,
    )

    assert len(unlocked) == 2
    for entry in unlocked:
        assert entry["combo_info"]["combo"] >= 2
        assert entry["combo_info"]["bonus_photons"] == 0


# ============ 日上限 + 边际递减（直调 handler） ============


@pytest.mark.asyncio
async def test_handler_effective_zero_grants_nothing(db_session, test_user):
    engine = AchievementEngine(db_session)
    info = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=0)
    assert info is None
    assert await _bonus_rows(db_session, test_user.id) == []


@pytest.mark.asyncio
async def test_handler_first_grant_full_and_recorded(db_session, test_user, monkeypatch):
    """当日首笔：decay=1、未触顶 → 全额 combo×10，且审计流水在案。"""
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_CAP", 100)
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_DECAY_FACTOR", 0.5)

    engine = AchievementEngine(db_session)
    info = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=3)

    assert info["combo"] == 3
    assert info["bonus_photons"] == 30
    assert info["capped"] is False

    rows = await _bonus_rows(db_session, test_user.id)
    assert len(rows) == 1
    assert rows[0].amount == 30


@pytest.mark.asyncio
async def test_handler_marginal_decay_on_second_grant(db_session, test_user, monkeypatch):
    """边际递减：同日第二笔 = base × factor^1（0.5），n 次后触 floor。"""
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_DECAY_FACTOR", 0.5)
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_DECAY_FLOOR", 0.1)
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_CAP", 0)  # 关上限，单测衰减

    engine = AchievementEngine(db_session)
    first = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=3)
    second = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=3)

    assert first["bonus_photons"] == 30
    assert second["bonus_photons"] == 15  # 30 × 0.5^1

    rows = await _bonus_rows(db_session, test_user.id)
    assert [r.amount for r in rows] == [30, 15]


@pytest.mark.asyncio
async def test_handler_daily_cap_clips_then_stops(db_session, test_user, monkeypatch):
    """日上限：cap=40 → 首笔 30，第二笔衰减 15 被削到剩余 10，第三笔停发。"""
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_DECAY_FACTOR", 0.5)
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_DECAY_FLOOR", 0.1)
    monkeypatch.setattr(settings, "PHOTON_COMBO_DAILY_CAP", 40)

    engine = AchievementEngine(db_session)
    first = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=3)
    second = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=3)
    third = await engine._handle_achievement_combo(str(test_user.id), 3, effective_unlock_count=3)

    assert first["bonus_photons"] == 30
    assert second["bonus_photons"] == 10
    assert second["capped"] is True
    assert third["bonus_photons"] == 0
    assert third["capped"] is True
    # 连击展示不受上限影响（combo 照常累积）
    assert third["combo"] > first["combo"]

    rows = await _bonus_rows(db_session, test_user.id)
    assert [r.amount for r in rows] == [30, 10]


@pytest.mark.asyncio
async def test_handler_old_style_all_unlocks_when_effect_none(db_session, test_user):
    """effective_unlock_count=None（直调兼容面）= 旧语义全量计入，对照钉子。"""
    engine = AchievementEngine(db_session)
    info = await engine._handle_achievement_combo(str(test_user.id), 3)
    assert info is not None
    assert info["combo"] == 3
    assert info["bonus_photons"] == 30


@pytest.mark.asyncio
async def test_combo_counter_only_accumulates_effective_unlocks(db_session, test_user):
    """门槛拦截不解 combo 窗口计数：0 分钟事件后 combo 仍为 0，随后有效事件从 0 起算。"""
    engine = AchievementEngine(db_session)
    session_key = f"{settings.APP_NAME}:achievement_combo:{test_user.id}"

    blocked = await engine._handle_achievement_combo(str(test_user.id), 2, effective_unlock_count=0)
    assert blocked is None
    assert await cache_service.get(session_key) in (None, 0)

    granted = await engine._handle_achievement_combo(str(test_user.id), 2, effective_unlock_count=2)
    assert granted["combo"] == 2  # 只累计了有效解锁
