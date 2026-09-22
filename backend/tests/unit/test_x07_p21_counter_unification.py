"""X-07 P2-1 · 双计数统一——steps 计划完成戳为真源，steps_done/steps_total 派生.

债项（X-07 验收 P2-1）：``agent_runs.steps_done/steps_total``（X-05 单调计数）
与 ``steps`` JSONB 计划的 completion 戳（X-07）**双计数并存**——X-07 四方法推
进计划戳时不同步计数列，UI 两处进度可能不同步（计划显示 1/3 完成、计数面
仍 0/3）。统一策略（最小侵入）：

- **真源**：有 steps 计划时，completion 戳计数 = steps_done 的下界真源、
  ``len(plan)`` = steps_total 真源（计划只定义一次、长度不变）；
- **派生**：读面（``to_dict``）与写点（服务层）统一经
  :func:`app.core.run_steps.reconcile_step_counters` 推导，字段名与形状不变
  （移动端 ``agent_run_read_service`` 兼容面零改动）；
- **单调兜底**：派生只升不降（``max(存储值, 完成戳数)``）——X-05「steps_done
  不得倒退」语义原样保留；无计划（execution 轨道）原值透传，X-05 零改动。

红测先立：先证脱节（计划推进、计数不动），统一后转绿。
测试同构 ``test_hybrid_run_steps.py``（sqlite + 最小 outbox DDL）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.run_state_machine import RunStatus
from app.core.run_steps import normalize_run_steps
from app.models.user import User
from app.services.agent_run_service import AgentRunService

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
)

_STEP_PLAN = [
    {
        "step_id": "s1-prepare",
        "ordinal": 1,
        "label": "整理错题",
        "owner": "agent",
        "completion_condition": {"kind": "agent_output"},
    },
    {
        "step_id": "s2-decide",
        "ordinal": 2,
        "label": "挑出今日复习卡",
        "owner": "human",
        "completion_condition": {"kind": "user_confirmation"},
    },
    {
        "step_id": "s3-check",
        "ordinal": 3,
        "owner": "hybrid",
        "completion_condition": {"kind": "user_edit"},
    },
]


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


async def _make_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _completed_count(wire_steps: list[dict]) -> int:
    return sum(1 for s in wire_steps if s.get("completed"))


# ---------------------------------------------------------------------------
# 0. 纯函数契约：reconcile_step_counters
# ---------------------------------------------------------------------------


async def test_reconcile_step_counters_pure_contract(db_session):
    from app.core.run_steps import reconcile_step_counters

    plan = normalize_run_steps(_STEP_PLAN)
    stamped = [dict(s) for s in plan]
    stamped[0] = {**stamped[0], "completion": {"by": "agent", "idempotency_key": "k1", "completed_at": "t"}}

    # 有计划：done = max(存储, 完成戳数)；total = len(plan)
    assert reconcile_step_counters(steps_done=0, steps_total=9, steps=stamped) == (1, 3)
    # 单调兜底：存储值更大时不得倒退
    assert reconcile_step_counters(steps_done=2, steps_total=3, steps=stamped) == (2, 3)
    # 无计划：原值透传（X-05 execution 轨道零改动）
    assert reconcile_step_counters(steps_done=4, steps_total=7, steps=[]) == (4, 7)
    assert reconcile_step_counters(steps_done=None, steps_total=None, steps=None) == (0, None)


# ---------------------------------------------------------------------------
# 1. 红证脱节：计划推进、计数不动 → 统一后一致
# ---------------------------------------------------------------------------


async def test_complete_agent_step_syncs_steps_done_with_plan(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="obj", steps=_STEP_PLAN)).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")

    result = await service.complete_agent_step(run.id, step_id="s1-prepare", user_id=user.id)
    assert result.applied is True

    wire = result.run.to_dict()
    # 计划面：1/3 完成
    assert _completed_count(wire["steps"]) == 1
    # 计数面必须与计划一致（统一前脱节：steps_done 停在 0）
    assert result.run.steps_done == 1
    assert wire["steps_done"] == 1
    assert wire["steps_total"] == 3


async def test_complete_user_step_syncs_steps_done_with_plan(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="obj", steps=_STEP_PLAN)).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    await service.complete_agent_step(run.id, step_id="s1-prepare", user_id=user.id)
    await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id)

    result = await service.complete_user_step(
        run.id, step_id="s2-decide", user_id=user.id, idempotency_key="u-1"
    )
    assert result.applied is True

    wire = result.run.to_dict()
    assert _completed_count(wire["steps"]) == 2
    # agent 步 + 用户步都计入（统一前脱节：停在 0）
    assert result.run.steps_done == 2
    assert wire["steps_done"] == 2
    assert wire["steps_total"] == 3


# ---------------------------------------------------------------------------
# 2. steps_total 真源：有计划时 len(plan) 胜出（计划只定义一次、长度不变）
# ---------------------------------------------------------------------------


async def test_create_run_prefers_plan_total_over_explicit_steps_total(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (
        await service.create_run(user_id=user.id, objective="obj", steps_total=9, steps=_STEP_PLAN)
    ).run
    # 统一前：显式 9 与计划 3 并存（两处进度不同步）
    assert run.steps_total == 3


async def test_define_run_steps_aligns_total_keeps_done_monotonic(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    # 无计划创建、显式 total=4、序号推进到 2（X-05 轨道先跑了两个里程碑）
    run = (await service.create_run(user_id=user.id, objective="obj", steps_total=4)).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    await service.record_step(run.id, user_id=user.id, step_id="m1", ordinal=2)

    await service.define_run_steps(run.id, steps=_STEP_PLAN, user_id=user.id)

    # total 对齐计划；done 单调兜底不倒退（max(2, 0)=2）
    assert run.steps_total == 3
    assert run.steps_done == 2


# ---------------------------------------------------------------------------
# 3. 读面派生：历史脱节行（统一前落库的戳/计数）在 to_dict 一致呈现
# ---------------------------------------------------------------------------


async def test_to_dict_derivation_covers_historical_divergence(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="obj", steps=_STEP_PLAN)).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    await service.complete_agent_step(run.id, step_id="s1-prepare", user_id=user.id)

    # 模拟历史行：计数列停在 0（统一前落库），计划戳已在
    await db_session.execute(
        text("UPDATE agent_runs SET steps_done = 0 WHERE id = :id"), {"id": str(run.id)}
    )
    await db_session.commit()
    await db_session.refresh(run)

    wire = run.to_dict()
    assert wire["steps_done"] == 1  # 读面派生：与计划一致
    assert wire["steps_total"] == 3

    # 读面单调兜底：计数列若被外部推得更高，派生不倒退
    await db_session.execute(
        text("UPDATE agent_runs SET steps_done = 2 WHERE id = :id"), {"id": str(run.id)}
    )
    await db_session.commit()
    await db_session.refresh(run)
    assert run.to_dict()["steps_done"] == 2


# ---------------------------------------------------------------------------
# 4. 混合轨道：record_step（X-05 里程碑）在有计划 run 上的统一行为
# ---------------------------------------------------------------------------


async def test_record_step_with_plan_total_follows_plan(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="obj", steps=_STEP_PLAN)).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")

    result = await service.record_step(
        run.id, user_id=user.id, step_id="milestone-x", ordinal=2, steps_total=5
    )
    # 序号单调推进保留；total 被计划收口（统一前：显式 5 覆盖）
    assert result.applied is True
    assert result.run.steps_done == 2
    assert result.run.steps_total == 3


# ---------------------------------------------------------------------------
# 5. X-05 零改动守卫：无计划 run 的计数行为原样
# ---------------------------------------------------------------------------


async def test_planless_run_counters_passthrough_unchanged(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="obj", steps_total=4)).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker", steps_done=1, steps_total=4)
    assert run.steps_done == 1 and run.steps_total == 4

    result = await service.record_step(run.id, user_id=user.id, step_id="m2", ordinal=3, steps_total=4)
    assert result.run.steps_done == 3 and result.run.steps_total == 4

    # 乱序迟到：不回退（R2 F5 单调语义原样）
    late = await service.record_step(run.id, user_id=user.id, step_id="m2", ordinal=2, steps_total=4)
    assert late.applied is False
    assert late.run.steps_done == 3

    wire = run.to_dict()
    assert wire["steps_done"] == 3 and wire["steps_total"] == 4
