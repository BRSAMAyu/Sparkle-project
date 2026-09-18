"""R2-P3-06（P3 清扫）：零任务级变更轮的节流 + feedback_log 追加窗口上限。

P2-2 修复的副作用（02-r2-engine-planning.md §2 R2-P3-06）：零任务级变更轮
不再武装 ``last_adjustment_at`` → 2h 调整冷却对"参数写了但没落地"的轮次永久
失效；每个新健康信号都会重写 plan_state（bump_version + feedback_log 追加 +
snapshots 追加）并向用户 enqueue 一条"本轮没有任务级调整"的 adaptation
update，无节流。

修复口径（报告建议第一选项）：
1. 零变更轮写独立的轻量 ``adaptive_meta.last_noop_adjustment_at``；
2. ``_handle_report`` 在 noop 节流窗口内直接跳过重评估（不写参数、不追加
   feedback_log、不给用户发消息）；``task_feedback_struggle`` 触发器豁免
   （用户正在挣扎，与 replan 冷却旁路同一哲学）；
3. ``upsert_plan_state`` 的 feedback_log 追加加窗口上限（保留最近 N 条）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import AsyncMock

from app.models.base import Base
from app.models.plan_state import PlanState
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.services.plan_progress_service import PlanHealthReport
from app.services.plan_state_service import FEEDBACK_LOG_WINDOW_LIMIT, PlanStateService


def _make_report() -> PlanHealthReport:
    return PlanHealthReport(
        plan_id=uuid4(),
        user_id=uuid4(),
        status="active",
        severity="warning",
        reasons=["progress_lag"],
        metrics={"progress_rate": 0.2},
        requires_adjustment=True,
        recommended_action="adjust",
    )


def _make_replanner(state_facts: dict | None) -> AdaptiveReplanner:
    replanner = object.__new__(AdaptiveReplanner)
    report_facts = state_facts if state_facts is not None else {"adaptive_meta": {}}
    replanner.db = None
    replanner._card_bridge = None
    replanner.plan_state_service = SimpleNamespace(
        get_plan_state=AsyncMock(return_value=SimpleNamespace(facts=report_facts, constraints={})),
        upsert_plan_state=AsyncMock(),
    )
    replanner.plan_health_signal_service = SimpleNamespace(maybe_publish=AsyncMock())
    replanner._calculate_adjustments = lambda *args, **kwargs: {"adaptive_adjustments": {"time_multiplier": 1.1}}
    replanner.plan_adjustment_applier = SimpleNamespace(
        apply_incremental_changes=AsyncMock(
            return_value=SimpleNamespace(
                applied=True,
                affected_task_ids=[],
                inserted_task_ids=[],
                hidden_task_ids=[],
                user_facing_summary=None,
            )
        )
    )
    replanner._enqueue_adaptation_update = AsyncMock()
    replanner._apply_cognitive_pattern_adjustments = AsyncMock(return_value=[])
    return replanner


@pytest.mark.asyncio
async def test_zero_change_round_records_noop_throttle_timestamp() -> None:
    """红：零变更轮必须写 last_noop_adjustment_at（冻结基线不写，冷却闸门永失效）。"""
    replanner = _make_replanner(None)
    report = _make_report()

    await replanner._apply_incremental_adjustment(report, trigger="task_feedback")

    upsert = replanner.plan_state_service.upsert_plan_state
    # 两次 upsert：参数写入 + fresh-read 后武装 noop 节流
    armed = [
        c.kwargs.get("patch", {}).get("facts", {}).get("adaptive_meta", {})
        for c in upsert.await_args_list
    ]
    assert any("last_noop_adjustment_at" in meta for meta in armed), (
        f"零变更轮未写 last_noop_adjustment_at，upsert 序列：{armed}"
    )
    # 决不写 last_adjustment_at（P2-2 语义保持：冷却只在任务级落地后武装）
    assert not any("last_adjustment_at" in meta for meta in armed)


@pytest.mark.asyncio
async def test_noop_throttle_suppresses_re_evaluation_within_window() -> None:
    """红：节流窗口内的重复健康信号跳过整轮重评估（不写参数/不发消息）。"""
    recent = datetime.now(UTC).isoformat()
    replanner = _make_replanner({"adaptive_meta": {"last_noop_adjustment_at": recent}})
    report = _make_report()

    await replanner._handle_report(report, trigger="task_feedback")

    replanner.plan_adjustment_applier.apply_incremental_changes.assert_not_awaited()
    replanner.plan_state_service.upsert_plan_state.assert_not_called()
    replanner._enqueue_adaptation_update.assert_not_called()


@pytest.mark.asyncio
async def test_struggle_trigger_bypasses_noop_throttle() -> None:
    """struggle 触发器豁免节流（用户挣扎必须被响应）。"""
    recent = datetime.now(UTC).isoformat()
    replanner = _make_replanner({"adaptive_meta": {"last_noop_adjustment_at": recent}})
    report = _make_report()

    await replanner._handle_report(report, trigger="task_feedback_struggle")

    replanner.plan_adjustment_applier.apply_incremental_changes.assert_awaited_once()


@pytest.mark.asyncio
async def test_expired_noop_throttle_allows_new_evaluation() -> None:
    """窗口过期后恢复正常评估。"""
    stale = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    replanner = _make_replanner({"adaptive_meta": {"last_noop_adjustment_at": stale}})
    report = _make_report()

    await replanner._handle_report(report, trigger="task_feedback")

    replanner.plan_adjustment_applier.apply_incremental_changes.assert_awaited_once()


# ===========================================================================
# feedback_log 追加窗口上限
# ===========================================================================


@pytest.fixture
async def sqlite_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    tables = [Base.metadata.tables["plan_states"]]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_feedback_log_append_is_window_capped(sqlite_session) -> None:
    """红：feedback_log 追加必须保留最近 N 条，无界增长将被钳制。"""
    service = PlanStateService(sqlite_session, redis=None)
    user_id = uuid4()
    plan_id = uuid4()

    for i in range(FEEDBACK_LOG_WINDOW_LIMIT + 25):
        await service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"feedback_log": {"entry": i}},
        )

    result = await sqlite_session.execute(select(PlanState).where(PlanState.plan_id == plan_id))
    state = result.scalar_one()
    assert len(state.feedback_log) == FEEDBACK_LOG_WINDOW_LIMIT
    # 保留的是最近的条目
    assert state.feedback_log[-1]["entry"] == FEEDBACK_LOG_WINDOW_LIMIT + 24
    assert state.feedback_log[0]["entry"] == 25
