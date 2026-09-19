"""UnderstandingDepthMetricService 单测（数据飞轮：理解深度日基线）。

红绿协议核心：合成分单调性 —— 任一维度"更懂用户"（记忆注入↑、个性化 run↑、
纠正↓、重复提问↓）→ score 不降。DB 用例跑在 conftest 的 sqlite 内存基座上，
不触碰主仓 PostgreSQL（主库只读纪律）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.memory import MemoryCorrection
from app.models.understanding_depth import UnderstandingDepthDaily
from app.services.understanding_depth_metric_service import (
    CORRECTION_TOLERANCE,
    HIT_SATURATION,
    UnderstandingDepthMetricService,
    compute_components,
    compute_score,
    normalize_memory_counts,
)


def _components(**overrides) -> dict:
    base = compute_components(
        memory_counts_list=[2, 2],
        chat_messages=["今天想复习数据结构的二叉树部分", "顺便帮我安排明天的学习计划"],
        correction_count=0,
    )
    base.update(overrides)
    return base


# ---------------------------------------------------------------- 纯函数：单调性


def test_score_zero_when_all_components_absent():
    assert compute_score({}) == 0.0


def test_more_memory_injection_increases_score():
    """记忆命中越多 → memory_injection 分量越高 → 合成分越高。"""
    low = compute_score(_components(memory_injection=0.2))
    high = compute_score(_components(memory_injection=0.8))
    assert HIT_SATURATION == 3.0  # 饱和点契约钉死
    assert low < high <= 1.0


def test_memory_injection_saturates_at_hit_saturation():
    got = compute_components(memory_counts_list=[3, 3, 3], chat_messages=[], correction_count=0)
    assert got["memory_injection"] == 1.0
    over = compute_components(memory_counts_list=[9, 9], chat_messages=[], correction_count=0)
    assert over["memory_injection"] == 1.0


def test_more_personalized_runs_increase_score():
    low = compute_score(_components(personalization=0.2))
    high = compute_score(_components(personalization=0.9))
    assert low < high <= 1.0


def test_fewer_corrections_increase_score():
    """用户主动纠正越少 → non_correction 越高 → 合成分越高。"""
    often = compute_score(_components(non_correction=0.2))
    rarely = compute_score(_components(non_correction=0.9))
    assert rarely > often
    saturated = compute_components(memory_counts_list=[], chat_messages=["a" * 10] * 2, correction_count=1)
    assert saturated["non_correction"] == 0.0  # 1 次纠正/2 轮 = 0.5 ≥ 容忍度 → 归零
    assert CORRECTION_TOLERANCE == 0.5


def test_fewer_repeats_increase_score():
    """重复提问越少 → non_repeat 越高 → 合成分越高。"""
    msgs_repeat = ["数据结构期中考试什么时候", "数据结构期中考试什么时候", "帮我制定复习计划"]
    msgs_fresh = ["数据结构期中考试什么时候", "操作系统进程调度有哪些算法", "帮我制定复习计划"]
    repeat = compute_components(memory_counts_list=[], chat_messages=msgs_repeat, correction_count=0)
    fresh = compute_components(memory_counts_list=[], chat_messages=msgs_fresh, correction_count=0)
    assert repeat["non_repeat"] < fresh["non_repeat"]
    assert compute_score(repeat) < compute_score(fresh)


def test_score_stays_in_unit_interval():
    worst = compute_score(_components(memory_injection=0.0, personalization=0.0, non_correction=0.0, non_repeat=0.0))
    best = compute_score(_components(memory_injection=1.0, personalization=1.0, non_correction=1.0, non_repeat=1.0))
    assert 0.0 <= worst <= best <= 1.0
    assert worst == 0.0 and best == 1.0


def test_short_messages_exempt_from_repeat_detection():
    got = compute_components(
        memory_counts_list=[], chat_messages=["嗯", "嗯", "好", "好的", "谢谢"], correction_count=0
    )
    assert got["non_repeat"] == 1.0  # 寒暄短消息不参与重复判定


def test_normalize_memory_counts_ignores_malformed_payload():
    assert normalize_memory_counts(None) == 0
    assert normalize_memory_counts("oops") == 0
    assert normalize_memory_counts({"preferences": -1, "goals": "2", "episodic": 2}) == 2
    assert normalize_memory_counts({"preferences": 1, "goals": 1, "episodic": 1}) == 3


# ---------------------------------------------------------------- sqlite 落表


@pytest.mark.asyncio
async def test_compute_daily_for_user_persists_row_and_is_idempotent(db_session):
    user_id = uuid4()
    day = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0)
    db_session.add(
        ContextPackRun(
            user_id=user_id,
            intent="chat",
            budgets={},
            token_usage={},
            memory_counts={"preferences": 2, "goals": 0, "episodic": 1},
            created_at=day,
        )
    )
    db_session.add(
        ContextPackRun(
            user_id=user_id,
            intent="chat",
            budgets={},
            token_usage={},
            memory_counts={"preferences": 0, "goals": 0, "episodic": 0},
            created_at=day,
        )
    )
    db_session.add(
        ChatMessage(
            user_id=user_id,
            session_id=uuid4(),
            role=MessageRole.USER,
            content="我下周三有数据结构期中考试",
            created_at=day,
        )
    )
    db_session.add(
        MemoryCorrection(
            user_id=user_id,
            memory_type="preference",
            memory_id=uuid4(),
            action="corrected",
            created_at=day,
        )
    )
    await db_session.commit()

    service = UnderstandingDepthMetricService(db_session)
    score = await service.compute_daily_for_user(user_id=user_id, day=day.date())

    assert score is not None and 0.0 <= score <= 1.0
    from sqlalchemy import select

    stored = (await db_session.execute(select(UnderstandingDepthDaily))).scalars().all()
    assert len(stored) == 1
    row = stored[0]
    assert row.metric_date == day.date()
    assert row.components["context_pack_runs"] == 2
    assert row.components["chat_turns"] == 1
    assert row.components["memory_corrections"] == 1
    assert row.components["avg_memory_injected"] == 1.5
    assert row.context_pack_runs == 2 and row.chat_turns == 1

    # 幂等重算：不新增行、分数稳定
    again = await service.compute_daily_for_user(user_id=user_id, day=day.date())
    stored_after = (await db_session.execute(select(UnderstandingDepthDaily))).scalars().all()
    assert again == score
    assert len(stored_after) == 1


@pytest.mark.asyncio
async def test_compute_daily_for_user_skips_inactive_day(db_session):
    service = UnderstandingDepthMetricService(db_session)
    assert await service.compute_daily_for_user(user_id=uuid4(), day=datetime.utcnow().date()) is None


@pytest.mark.asyncio
async def test_compute_daily_all_covers_active_users_only(db_session):
    from sqlalchemy import select

    active, quiet = uuid4(), uuid4()
    now = datetime.utcnow().replace(hour=9, minute=0, second=0, microsecond=0)
    db_session.add(
        ChatMessage(
            user_id=active,
            session_id=uuid4(),
            role=MessageRole.USER,
            content="帮我看看高数极限的题目",
            created_at=now,
        )
    )
    # quiet 用户只有三天前的旧消息，不落在当日窗口
    db_session.add(
        ChatMessage(
            user_id=quiet,
            session_id=uuid4(),
            role=MessageRole.USER,
            content="三天前的旧消息",
            created_at=now - timedelta(days=3),
        )
    )
    await db_session.commit()

    summary = await UnderstandingDepthMetricService(db_session).compute_daily_all(day=now.date())
    assert summary["active_users"] == 1
    assert summary["computed"] == 1

    rows = (await db_session.execute(select(UnderstandingDepthDaily))).scalars().all()
    assert len(rows) == 1 and rows[0].user_id == active
