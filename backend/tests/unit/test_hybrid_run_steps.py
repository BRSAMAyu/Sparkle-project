"""X-07 · Hybrid Handoff 契约测试（owner 标注 / 幂等 resume / 恢复推导 / 取消过期）.

覆盖卡面验收：
- run step 结构标 owner（agent|human|hybrid）+ 完成条件（封闭词表）；
- 用户确认/编辑触发 resume——**幂等双发恰一次**（同 key 重放 / 换 key 重发 /
  resume 已提交后迟到的重试一律 no-op，「用户操作两次不会 resume 两次」）；
- awaiting step 从持久化推导（冷启动/重开不靠内存）；
- 取消（user_cancelled）/过期（wait_expired→TIMED_OUT）后的迟到确认被明确
  拒绝，且 awaiting_step 投影如实呈现 expired/cancelled（零新状态机边）；
- 预算闸门：resume 前超限 → BUDGET_EXCEEDED 明确终态（完成戳保留，事实不掩
  盖）；

测试同构 ``test_agent_run_service.py``（sqlite + 最小 outbox DDL）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.run_state_machine import RunStatus
from app.core.run_steps import normalize_run_steps
from app.models.user import User
from app.services.agent_run_service import (
    AgentRunService,
    BudgetExceededError,
    MissingIdempotencyKeyError,
    RunNotAwaitingUserStepError,
    RunNotFoundError,
    RunStepPlanConflictError,
    UnknownRunStepError,
)

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
        "completion_condition": {"kind": "user_confirmation", "description": "确认复习卡清单"},
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


async def _make_run_with_plan(db_session, user: User, *, budget: dict | None = None):
    """QUEUED run + 三步 hybrid 计划（agent → human → hybrid）。"""
    service = AgentRunService(db_session)
    result = await service.create_run(
        user_id=user.id,
        objective="期末复习：错题变复习卡",
        steps=_STEP_PLAN,
        budget=budget,
    )
    assert result.created
    return result.run


async def _outbox_rows(db_session, event_type: str) -> list[dict]:
    result = await db_session.execute(
        text(
            "SELECT event_type, payload, metadata, sequence_number FROM event_outbox "
            "WHERE event_type = :t ORDER BY sequence_number"
        ),
        {"t": event_type},
    )
    return [dict(row._mapping) for row in result.all()]


async def _start(db_session, service: AgentRunService, run) -> None:
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")


# ---------------------------------------------------------------------------
# 1. 步骤计划：创建携带 / 持久化 / wire 投影
# ---------------------------------------------------------------------------


async def test_create_run_with_steps_plan_persists_owner_and_condition(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)

    assert len(run.steps) == 3
    assert [s["owner"] for s in run.steps] == ["agent", "human", "hybrid"]
    assert run.steps_total == 3

    wire = run.to_dict()
    assert [s["step_id"] for s in wire["steps"]] == ["s1-prepare", "s2-decide", "s3-check"]
    assert wire["steps"][1]["completion_condition"]["kind"] == "user_confirmation"
    assert all(not s["completed"] for s in wire["steps"])
    # 无等待 → awaiting_step 推导为 None（进度面由 steps 呈现）
    assert wire["awaiting_step"] is None


async def test_define_run_steps_first_win_replay_and_conflict(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)

    # 同内容重投（at-least-once 生产者）→ 幂等 no-op
    replay = await service.define_run_steps(run.id, steps=_STEP_PLAN, user_id=user.id)
    assert replay.applied is False

    # 不同内容 → 冲突拒绝（计划只许定义一次）
    mutated = [dict(s) for s in _STEP_PLAN]
    mutated[0]["label"] = "换一个计划"
    with pytest.raises(RunStepPlanConflictError):
        await service.define_run_steps(run.id, steps=mutated, user_id=user.id)

    # 终态 run 拒绝
    await service.transition(run.id, RunStatus.CANCELLED, actor="user", reason="user_cancelled")
    with pytest.raises(ValueError, match="terminal"):
        await service.define_run_steps(run.id, steps=[], user_id=user.id)


async def test_normalize_run_steps_fail_closed():
    with pytest.raises(ValueError, match="owner"):
        normalize_run_steps(
            [{"step_id": "a", "ordinal": 1, "owner": "robot", "completion_condition": {"kind": "agent_output"}}]
        )
    with pytest.raises(ValueError, match="completion kind"):
        normalize_run_steps(
            [{"step_id": "a", "ordinal": 1, "owner": "agent", "completion_condition": {"kind": "vibes"}}]
        )
    with pytest.raises(ValueError, match="duplicate step_id"):
        normalize_run_steps(
            [
                {"step_id": "a", "ordinal": 1, "owner": "agent", "completion_condition": {"kind": "agent_output"}},
                {"step_id": "a", "ordinal": 2, "owner": "agent", "completion_condition": {"kind": "agent_output"}},
            ]
        )
    with pytest.raises(ValueError, match="artifact ref requires"):
        normalize_run_steps(
            [
                {
                    "step_id": "a",
                    "ordinal": 1,
                    "owner": "agent",
                    "completion_condition": {"kind": "agent_output"},
                    "artifacts": [{"scheme": "", "ref": "x"}],
                }
            ]
        )


async def test_complete_agent_step_owner_discipline_and_replay(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)

    # AGENT 不得代替用户完成 HUMAN 步骤（认知归属不可越权）
    with pytest.raises(ValueError, match="owner='human'"):
        await service.complete_agent_step(run.id, step_id="s2-decide", user_id=user.id)

    first = await service.complete_agent_step(
        run.id,
        step_id="s1-prepare",
        user_id=user.id,
        artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}],
        idempotency_key="agent:s1:1",
    )
    assert first.applied is True
    assert first.event_name == "run.step_completed"
    # 不改 run 状态（进度事件 ≠ 状态迁移；是否交棒由 await_user_step 显式决定）
    assert first.run.status is RunStatus.RUNNING
    step = next(s for s in first.run.to_dict()["steps"] if s["step_id"] == "s1-prepare")
    assert step["completed"] is True
    assert step["completion"]["by"] == "agent"

    # 重放 → 幂等 no-op
    replay = await service.complete_agent_step(run.id, step_id="s1-prepare", user_id=user.id)
    assert replay.applied is False
    assert len(await _outbox_rows(db_session, "run.step_completed")) == 1

    # 乱序（下一个 pending 是另一个 agent 步骤时，跳步完成被拒）
    plan = [
        {"step_id": "a1", "ordinal": 1, "owner": "agent", "completion_condition": {"kind": "agent_output"}},
        {"step_id": "a2", "ordinal": 2, "owner": "agent", "completion_condition": {"kind": "agent_output"}},
    ]
    run2 = (await service.create_run(user_id=user.id, objective="two agent steps", steps=plan)).run
    await service.transition(run2.id, RunStatus.RUNNING, actor="worker")
    with pytest.raises(ValueError, match="next pending step"):
        await service.complete_agent_step(run2.id, step_id="a2", user_id=user.id)


# ---------------------------------------------------------------------------
# 2. 「轮到你」：await_user_step（transition + awaiting 戳 + 事件恰一次）
# ---------------------------------------------------------------------------


async def test_await_user_step_transitions_and_projects(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)
    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )

    expires = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=30)
    result = await service.await_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        prompt="Agent 已备好 5 张复习卡，请挑选",
        artifact_refs=[{"scheme": "action_proposal", "ref": str(uuid4())}],
        wait_expires_at=expires,
    )

    assert result.run.status is RunStatus.AWAITING_USER
    assert result.run.wait_kind == "user_step"
    assert result.event_name == "run.awaiting_user"

    wire = result.run.to_dict()
    awaiting = wire["awaiting_step"]
    assert awaiting is not None
    assert awaiting["state"] == "awaiting"
    assert awaiting["step_id"] == "s2-decide"
    # 「你做」可达（U-04 P2 解锁）：owner=human → ownership=human
    assert awaiting["ownership"] == "human"
    assert awaiting["prompt"].startswith("Agent 已备好")
    assert awaiting["artifacts"][0]["scheme"] == "action_proposal"
    assert awaiting["expires_at"] is not None

    events = await _outbox_rows(db_session, "run.awaiting_user")
    assert len(events) == 1


async def test_await_user_step_replay_and_guards(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)
    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )

    first = await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id, prompt="请挑选")
    assert first.applied is True

    # 已在等待中重投同一步 → 落戳但事件/迁移不重发（applied=False）
    replay = await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id, prompt="请挑选")
    assert replay.applied is False
    assert len(await _outbox_rows(db_session, "run.awaiting_user")) == 1

    # 未完成的下一步不能提前 await（顺序执行）
    with pytest.raises(ValueError, match="next pending step"):
        await service.await_user_step(run.id, step_id="s3-check", user_id=user.id)
    # 计划外步骤
    with pytest.raises(UnknownRunStepError):
        await service.await_user_step(run.id, step_id="ghost", user_id=user.id)


# ---------------------------------------------------------------------------
# 3. 幂等 resume（acceptance ①核心）：两次操作只 resume 一次
# ---------------------------------------------------------------------------


async def test_complete_user_step_resumes_once_and_replays(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)
    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )
    await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id, prompt="请挑选")

    first = await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key="x07:s2:confirm",
        action="confirm",
    )
    assert first.applied is True
    assert first.resumed is True
    assert first.event_name == "run.user_resumed"
    assert first.run.status is RunStatus.RUNNING

    # 第二次点击（同 key）：重放 no-op——不二次 resume、不写第二条审计/事件
    second = await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key="x07:s2:confirm",
    )
    assert second.applied is False
    assert second.resumed is False
    assert second.replay is True

    # 换 key 重发（双端重试）：同样 first-wins no-op
    third = await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key="x07:s2:confirm-from-other-device",
    )
    assert third.applied is False
    assert third.resumed is False

    resumed_events = await _outbox_rows(db_session, "run.user_resumed")
    assert len(resumed_events) == 1
    transitions = await service.list_transitions(run.id, user_id=user.id)
    resume_rows = [
        t for t in transitions if t.to_status == RunStatus.RUNNING.value and t.from_status == "AWAITING_USER"
    ]
    assert len(resume_rows) == 1
    # 完成戳恰一个（记录第一次的用户输入）
    step = next(s for s in third.run.to_dict()["steps"] if s["step_id"] == "s2-decide")
    assert step["completed"] is True
    assert step["completion"]["idempotency_key"] == "x07:s2:confirm"


async def test_complete_user_step_guards(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)

    # 缺幂等键 → 422 语义（MissingIdempotencyKeyError）
    with pytest.raises(MissingIdempotencyKeyError):
        await service.complete_user_step(run.id, step_id="s2-decide", user_id=user.id, idempotency_key="  ")
    # run 不在等待（RUNNING）→ 409 语义
    with pytest.raises(RunNotAwaitingUserStepError):
        await service.complete_user_step(run.id, step_id="s2-decide", user_id=user.id, idempotency_key="k1")
    # 计划外步骤
    with pytest.raises(UnknownRunStepError):
        await service.complete_user_step(run.id, step_id="ghost", user_id=user.id, idempotency_key="k1")
    # 不存在的 run
    with pytest.raises(RunNotFoundError):
        await service.complete_user_step(uuid4(), step_id="s2-decide", user_id=user.id, idempotency_key="k1")


async def test_complete_user_step_edit_stamps_artifacts_and_note(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)
    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )
    await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id)

    result = await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key="x07:s2:edit-1",
        action="edit",
        artifact_refs=[{"scheme": "galaxy", "ref": "node/复习卡-集合A"}],
        note="把第 3 张卡换成了积分题",
    )
    assert result.applied and result.resumed
    step = next(s for s in result.run.to_dict()["steps"] if s["step_id"] == "s2-decide")
    assert step["completion"]["action"] == "edit"
    assert step["completion"]["note"] == "把第 3 张卡换成了积分题"
    assert step["completion"]["artifacts"] == [{"scheme": "galaxy", "ref": "node/复习卡-集合A"}]


# ---------------------------------------------------------------------------
# 4. 取消/过期明确（acceptance ②）：零新状态机边，迟到确认明确拒绝
# ---------------------------------------------------------------------------


async def test_cancel_then_complete_rejected_and_projection_cancelled(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)
    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )
    await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id)

    await service.cancel(run.id, user_id=user.id)

    with pytest.raises(RunNotAwaitingUserStepError, match="terminal"):
        await service.complete_user_step(run.id, step_id="s2-decide", user_id=user.id, idempotency_key="late-1")
    fresh = await service.get_run(run.id, user_id=user.id)
    awaiting = fresh.to_dict()["awaiting_step"]
    assert awaiting is not None
    assert awaiting["state"] == "cancelled"
    assert fresh.terminal_reason == "user_cancelled"


async def test_wait_expiry_sweep_then_complete_rejected_and_projection_expired(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(db_session, user)
    service = AgentRunService(db_session)
    await _start(db_session, service, run)

    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )
    past = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
    await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id, wait_expires_at=past)

    sweep = await service.recover_stale_runs()
    assert any(a["kind"] == "wait_expired_timed_out" for a in sweep["actions"])

    fresh = await service.get_run(run.id, user_id=user.id)
    assert fresh.status is RunStatus.TIMED_OUT
    assert fresh.terminal_reason == "wait_expired"
    assert fresh.to_dict()["awaiting_step"]["state"] == "expired"

    with pytest.raises(RunNotAwaitingUserStepError, match="terminal"):
        await service.complete_user_step(run.id, step_id="s2-decide", user_id=user.id, idempotency_key="late-2")


# ---------------------------------------------------------------------------
# 5. 预算闸门：resume 前超限 → BUDGET_EXCEEDED 明确终态（事实不掩盖）
# ---------------------------------------------------------------------------


async def test_complete_user_step_budget_gate_terminalizes(db_session, outbox_tables):
    user = await _make_user(db_session)
    run = await _make_run_with_plan(
        db_session,
        user,
        budget={"limits": {"max_tool_calls": 1}},
    )
    service = AgentRunService(db_session)
    await _start(db_session, service, run)
    await service.record_run_usage(run.id, user_id=user.id, tool_calls=2)  # 预算打满（usage > limit）
    await service.complete_agent_step(
        run.id, step_id="s1-prepare", user_id=user.id, artifact_refs=[{"scheme": "tool_call", "ref": "tc-1"}]
    )
    await service.await_user_step(run.id, step_id="s2-decide", user_id=user.id)

    with pytest.raises(BudgetExceededError):
        await service.complete_user_step(run.id, step_id="s2-decide", user_id=user.id, idempotency_key="x07:s2:confirm")

    fresh = await service.get_run(run.id, user_id=user.id)
    assert fresh.status is RunStatus.BUDGET_EXCEEDED
    assert fresh.terminal_reason == "budget_exceeded"
    # 完成戳保留：用户操作是事实，终态也是事实（不互相掩盖）
    step = next(s for s in fresh.to_dict()["steps"] if s["step_id"] == "s2-decide")
    assert step["completed"] is True
