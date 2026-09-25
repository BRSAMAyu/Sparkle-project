"""Q-02 · Golden Journeys service 层随行锁（sqlite 隔离真服务直驱，wt384/wt393 手法）.

HTTP 驱动（scripts/devtools/q02_run_golden_journeys.py）覆盖三端共享的后端语义段；
本文件对**需要可控时钟/进程内重启语义**的旅程补真服务直驱链（不 mock 语义、
sqlite 引擎 + 真实 schema，backdate 口径与 tests/aurora/test_comeback_context.py 同源）：

- GJ09 Memory delete → cache invalidation → no reuse：
  真实 ``MemoryService.revoke_episodic_memory``（M-07 统一删除管线）→
  召回面（``list_recent_episodic``）0 复用 + 幂等重删无重复副作用；
- GJ12 Proactive suggestion → reject/mute → cooldown/suppression：
  真实 ``ProactiveSuggestionFeedbackService``（P-03 服务端真逻辑，DB 持久态）；
- GJ14 Agent worker restart → run recovery：
  真实 ``AgentRunService``（X-05）：QUEUED 陈旧→CANCELLED、RUNNING 孤儿→
  UNKNOWN_OUTCOME(worker_restart_orphan)、AWAITING 过期→TIMED_OUT、
  新鲜 run 不误伤、``recover_inflight_runs``（进程重启恢复面）可用。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.models.memory import EpisodicMemory
from app.models.user import User
from app.services.agent_run_service import AgentRunService
from app.services.memory_service import MemoryService
from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

# ---------------------------------------------------------------------------
# 公共小件（与既有服务测试同款口径）
# ---------------------------------------------------------------------------

_OUTBOX_DDL = (
    """
    CREATE TABLE IF NOT EXISTS event_outbox (
        id VARCHAR(36) PRIMARY KEY,
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        event_version INTEGER NOT NULL DEFAULT 1,
        payload JSON NOT NULL,
        metadata JSON,
        sequence_number INTEGER NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        published_at DATETIME
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS event_sequence_counters (
        aggregate_type VARCHAR(100) NOT NULL,
        aggregate_id VARCHAR(36) NOT NULL,
        next_sequence INTEGER NOT NULL,
        PRIMARY KEY (aggregate_type, aggregate_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS memory_epochs (
        user_id VARCHAR(36) PRIMARY KEY,
        epoch INTEGER NOT NULL DEFAULT 1,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
)


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


@pytest.fixture(name="patch_enqueue")
def patch_enqueue_fixture(monkeypatch):
    """hermetic：不碰本机 dev Redis / 系统更新队列（M-07 测试同款）。"""
    monkeypatch.setattr("app.services.memory_service.SystemUpdateService.enqueue", AsyncMock())
    monkeypatch.setattr(
        "app.aurora.runtime_v1.self_model.SparkleSelfModelService.record_user_correction",
        AsyncMock(),
    )


async def _make_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"q02_{user_id.hex[:8]}",
        email=f"q02_{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


async def _make_episodic(db_session, user: User, summary: str) -> EpisodicMemory:
    mem = EpisodicMemory(
        user_id=user.id,
        summary=summary,
        source_type="chat",
        subject_type="preference",
        occurred_at=datetime.now(UTC).replace(tzinfo=None),
        confidence=0.9,
    )
    db_session.add(mem)
    await db_session.commit()
    await db_session.refresh(mem)
    return mem


async def _backdate_heartbeat(db_session, run_id, seconds: int) -> None:
    await db_session.execute(
        text("UPDATE agent_runs SET heartbeat_at = :h WHERE id = :r"),
        {"h": datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=seconds), "r": str(run_id)},
    )
    await db_session.commit()
    db_session.expire_all()  # 防 ORM 身份映射陈旧对象假象


# ---------------------------------------------------------------------------
# GJ09 · Memory delete → cache invalidation → no reuse
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_q02_gj09_memory_delete_no_reuse_chain(db_session, patch_enqueue, outbox_tables):
    user = await _make_user(db_session)
    service = MemoryService(db_session)

    mem = await _make_episodic(db_session, user, "用户对花生严重过敏（Q02-GJ09 旅程样本）")

    # 删除前：召回面可见
    before = await service.list_recent_episodic(user_id=user.id, limit=20)
    assert any(m.id == mem.id for m in before), "删除前召回面应包含该记忆"

    # 真实删除（revoke：revoked_at 软删，M-07 管线同事务 epoch/事件）
    record = await service.revoke_episodic_memory(
        user_id=user.id, memory_id=mem.id, reason="user_deleted"
    )
    assert record is not None and record.revoked_at is not None

    # 删除后：召回面 0 复用（revoked 排除在真源查询内，非渲染遮蔽）
    after = await service.list_recent_episodic(user_id=user.id, limit=20)
    assert all(m.id != mem.id for m in after), "删除后召回面不得复用已删记忆"

    # 幂等：重复删除 no-op（终态一致，无重复副作用）
    repeat = await service.revoke_episodic_memory(
        user_id=user.id, memory_id=mem.id, reason="user_deleted"
    )
    assert repeat is None or getattr(repeat, "revoked_at", None) is not None


# ---------------------------------------------------------------------------
# GJ12 · Proactive suggestion → reject/mute → cooldown/suppression
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_q02_gj12_proactive_feedback_suppression_chain(db, test_user):
    now = datetime.now(UTC)

    # 未反馈 → 不抑制（真实生成任务据此判定）
    assert await ProactiveSuggestionFeedbackService(db).is_suppressed(
        test_user.id, "comeback_nudge", now=now
    ) is False

    svc = ProactiveSuggestionFeedbackService(db)
    # reject（今天不再看）→ 当日 cooldown；次日窗口过期恢复
    await svc.record_ignore_today(test_user.id, "comeback_nudge", now=now)
    assert await ProactiveSuggestionFeedbackService(db).is_suppressed(
        test_user.id, "comeback_nudge", now=now + timedelta(hours=1)
    )
    assert await ProactiveSuggestionFeedbackService(db).is_suppressed(
        test_user.id, "comeback_nudge", now=now + timedelta(days=1)
    ) is False

    # mute this type → 持久静音且跨类型隔离
    await svc.record_mute(test_user.id, "comeback_nudge", now=now)
    assert await ProactiveSuggestionFeedbackService(db).is_suppressed(
        test_user.id, "comeback_nudge", now=now + timedelta(days=8)
    )
    assert await ProactiveSuggestionFeedbackService(db).is_suppressed(
        test_user.id, "plan_repair", now=now
    ) is False


# ---------------------------------------------------------------------------
# GJ14 · Agent worker restart → run recovery
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_q02_gj14_worker_restart_recovery_chain(db_session, outbox_tables):
    from app.core.run_state_machine import RunStatus

    user = await _make_user(db_session)
    user_id_val = user.id  # expire_all 后 ORM 属性访问会触发同步 IO，提前取值
    service = AgentRunService(db_session)

    # worker 死在 RUNNING（心跳 7h 陈旧）→ UNKNOWN_OUTCOME(worker_restart_orphan)
    crashed = await service.create_run(user_id=user_id_val, objective="Q02-GJ14：worker 崩溃遗留")
    crashed_run_id = crashed.run.id
    await service.transition(crashed_run_id, RunStatus.RUNNING, actor="worker")
    await _backdate_heartbeat(db_session, crashed_run_id, seconds=7 * 3600)

    # QUEUED 陈旧（从未启动）→ CANCELLED(queue_stale)
    queued = await service.create_run(user_id=user_id_val, objective="Q02-GJ14：排队陈旧")
    queued_run_id = queued.run.id
    await _backdate_heartbeat(db_session, queued_run_id, seconds=7 * 3600)

    # AWAITING_USER 等待过期 → TIMED_OUT(wait_expired)
    awaited = await service.create_run(user_id=user_id_val, objective="Q02-GJ14：等待过期")
    awaited_run_id = awaited.run.id
    expires = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    await service.transition(
        awaited_run_id, RunStatus.AWAITING_USER, actor="worker", wait_expires_at=expires
    )

    # 新鲜 RUNNING（心跳新鲜）→ 恢复 sweep 不误伤
    fresh = await service.create_run(user_id=user_id_val, objective="Q02-GJ14：新鲜在跑")
    fresh_run_id = fresh.run.id
    await service.transition(fresh_run_id, RunStatus.RUNNING, actor="worker")

    report = await service.recover_stale_runs(stale_after_seconds=6 * 3600)
    assert report["applied"] >= 3

    crashed_after = await service.get_run(crashed_run_id)
    assert crashed_after.status is RunStatus.UNKNOWN_OUTCOME
    assert crashed_after.terminal_reason == "worker_restart_orphan"

    queued_after = await service.get_run(queued_run_id)
    assert queued_after.status is RunStatus.CANCELLED
    assert queued_after.terminal_reason == "queue_stale"

    awaited_after = await service.get_run(awaited_run_id)
    assert awaited_after.status is RunStatus.TIMED_OUT
    assert awaited_after.terminal_reason == "wait_expired"

    fresh_after = await service.get_run(fresh_run_id)
    assert fresh_after.status is RunStatus.RUNNING

    # 进程重启恢复面（X-09）：inflight 恢复可调用且不误伤新鲜 run
    inflight = await service.recover_inflight_runs(stale_after_seconds=6 * 3600)
    assert isinstance(inflight, dict)
    still_fresh = await service.get_run(fresh_run_id)
    assert still_fresh.status is RunStatus.RUNNING
