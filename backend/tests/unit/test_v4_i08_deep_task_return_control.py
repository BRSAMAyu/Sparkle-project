"""V4-I08 · 深任务返回控制与恢复一致性 —— 可失败契约测试.

覆盖卡面三条验收（每面一正一反；变异必红锚点）：

1. **5s 内可查看/取消/离开；ack 不算有效答案**
   - 查询（GET 面 = ``get_run().to_dict()``：current_stage + steps wire +
     ``awaiting_step`` 的 prompt/artifacts 阶段产物）与取消路径的延迟用
     ``DEEP_TASK_RETURN_DEADLINE_SECONDS``（5.0s）``asyncio.wait_for`` 上限钉死
     ——路径超时即测试失败；
   - ack 类自动回应（``ACK_CLASS_ANSWER_MARKERS``）经
     :meth:`AgentRunService.complete_user_step` 显式拒绝（422 面）：步骤无完成
     戳、run 保持 AWAITING_USER、无 ``run.user_resumed`` 事件——ack 永不被记账
     为人类有效答案；
   - 合法答案动作（confirm/edit/decide）照常完成（正例面）。
2. **重启/断网/重试不双写；取消后外部副作用如实对账**
   - 用户取消经 X-09 既有账本证据机制物化 ``result_ref``（succeeded 写效果 +
     补偿提示 + interrupted unknown）——不假装回滚、不丢账；无账本行不造空证据；
   - 取消双发 / inflight 恢复两轮：恰一次迁移、恰一个事件、账本
     ``already_resolved``（不双写）。
3. **人类步骤等待，不由 Agent 伪造完成；预算暂停/unknown 显式对账**
   - awaiting user step 无完成戳时，任何 actor 经 ``transition`` 落
     SUCCEEDED/PARTIAL 一律 ``HumanStepNotCompletedError``（反例钉死）；
     用户显式作答后合法终态化（正例）；
   - ``enforce_budget`` 预算暂停与 sweep/inflight UNKNOWN_OUTCOME 都物化
     对账证据（外部已写效果如实可见）。

测试同构 ``test_hybrid_run_steps.py`` / ``test_x09_failure_recovery.py``
（sqlite + 最小 outbox DDL + registry 元数据 monkeypatch）。
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.core.run_state_machine import RunStatus
from app.core.run_steps import (
    ACK_CLASS_ANSWER_MARKERS,
    USER_STEP_ANSWER_ACTIONS,
    awaiting_step_projection,
    normalize_user_step_action,
)
from app.models.agent_run import AgentRun, AgentRunTransition
from app.models.agent_tool_call import AgentToolCall
from app.models.user import User
from app.services.agent_run_service import (
    DEEP_TASK_RETURN_DEADLINE_SECONDS,
    AgentRunService,
    BudgetExceededError,
    HumanStepNotCompletedError,
    InvalidUserStepAnswerError,
    RunNotFoundError,
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
        "label": "整理材料",
        "owner": "agent",
        "completion_condition": {"kind": "agent_output"},
    },
    {
        "step_id": "s2-decide",
        "ordinal": 2,
        "label": "你来挑重点",
        "owner": "human",
        "completion_condition": {"kind": "user_confirmation", "description": "确认重点清单"},
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


async def _outbox_count(db_session, event_type: str) -> int:
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM event_outbox WHERE event_type = :t"),
        {"t": event_type},
    )
    return int(result.scalar_one())


async def _transition_rows(db_session, run_id) -> list[AgentRunTransition]:
    result = await db_session.execute(select(AgentRunTransition).where(AgentRunTransition.run_id == run_id))
    return sorted(result.scalars().all(), key=lambda t: (t.occurred_at, t.id))


def _stub_registry(monkeypatch, *, write_tools: tuple[str, ...] = ()) -> None:
    """给对账证据物化喂确定性 registry 元数据（write/reversible=True）.

    ``build_evidence`` 在调用点 ``from app.tools.registry import tool_registry``
    动态取模块属性——monkeypatch 模块属性即生效（x09 _stub_registry_with 同法）。
    """
    from app.tools import registry as registry_module
    from app.tools.metadata import ToolEffect, ToolMetadata, ToolRiskLevel

    metadata = {
        name: ToolMetadata(
            name=name,
            effect=ToolEffect.WRITE,
            risk=ToolRiskLevel.MEDIUM,
            reversible=True,
            required_permission="plan.write",
            cost_usd=0.0,
        )
        for name in write_tools
    }
    monkeypatch.setattr(
        registry_module,
        "tool_registry",
        SimpleNamespace(get_tool=lambda n: None, get_tool_metadata=lambda n: metadata.get(n)),
    )


async def _ledger_row(
    db_session,
    user: User,
    run: AgentRun,
    *,
    status: str = "succeeded",
    tool: str = "deep_task_write",
    started_at: datetime | None = None,
) -> AgentToolCall:
    row = AgentToolCall(
        user_id=user.id,
        run_id=run.id,
        tool_name=tool,
        idempotency_key=f"key-{uuid4().hex[:8]}",
        args_hash="x" * 64,
        status=status,
        started_at=started_at or datetime.now(UTC).replace(tzinfo=None),
    )
    db_session.add(row)
    await db_session.commit()
    return row


async def _running_run_with_human_step_pending(db_session, user: User) -> tuple[AgentRunService, AgentRun]:
    """RUNNING run：agent 步已完成、human 步已 await（带 prompt + 阶段产物引用）。"""
    service = AgentRunService(db_session)
    run = (
        await service.create_run(
            user_id=user.id,
            objective="深任务：综述整理",
            steps=_STEP_PLAN,
        )
    ).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    await service.complete_agent_step(run.id, step_id="s1-prepare")
    run = (
        await service.await_user_step(
            run.id,
            step_id="s2-decide",
            prompt="请从候选中挑出今天的重点",
            artifact_refs=[{"scheme": "tool_call", "ref": "prep-1"}],
        )
    ).run
    return service, run


# ---------------------------------------------------------------------------
# 验收 1 · ack 不算有效答案（核心词表门：正例 + 反例）
# ---------------------------------------------------------------------------


def test_normalize_user_step_action_ack_class_never_valid():
    """[反例] ack 类自动回应标记一律拒绝——传输/通知层确认不是人类有效答案。"""
    for marker in sorted(ACK_CLASS_ANSWER_MARKERS):
        with pytest.raises(ValueError, match="ack-class"):
            normalize_user_step_action(marker)
        with pytest.raises(ValueError, match="ack-class"):
            normalize_user_step_action(marker.upper())
    with pytest.raises(ValueError, match="required"):
        normalize_user_step_action("")
    with pytest.raises(ValueError, match="out of vocabulary"):
        normalize_user_step_action("auto_confirm")


def test_normalize_user_step_action_valid_answers_accepted():
    """[正例] 合法答案动作（confirm/edit/decide）归一化通过；空白/大小写容忍。"""
    assert normalize_user_step_action("confirm") == "confirm"
    assert normalize_user_step_action("  Edit ") == "edit"
    assert normalize_user_step_action("DECIDE") == "decide"
    assert frozenset({"confirm", "edit", "decide"}) == USER_STEP_ANSWER_ACTIONS


async def test_ack_action_cannot_complete_human_step(db_session, outbox_tables, monkeypatch):
    """[反例] ack 作为 action 提交：422 面拒绝，步骤无完成戳、run 保持等待、
    无 resume 事件、awaiting 投影仍呈「轮到用户」——ack 不被记账为有效答案。"""
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    resumed_before = await _outbox_count(db_session, "run.user_resumed")

    with pytest.raises(InvalidUserStepAnswerError, match="ack-class"):
        await service.complete_user_step(
            run.id,
            step_id="s2-decide",
            user_id=user.id,
            idempotency_key=f"ack-{uuid4().hex[:8]}",
            action="ack",
        )
    with pytest.raises(InvalidUserStepAnswerError):
        await service.complete_user_step(
            run.id,
            step_id="s2-decide",
            user_id=user.id,
            idempotency_key=f"rcv-{uuid4().hex[:8]}",
            action="received",
        )

    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.AWAITING_USER
    step = next(s for s in fresh.steps if s["step_id"] == "s2-decide")
    assert "completion" not in step  # 无完成戳 = 未记账
    assert await _outbox_count(db_session, "run.user_resumed") == resumed_before
    projection = awaiting_step_projection(
        run_status=fresh.status.value,
        wait_kind=fresh.wait_kind,
        terminal_reason=fresh.terminal_reason,
        wait_expires_at=fresh.wait_expires_at,
        steps=fresh.steps,
    )
    assert projection is not None and projection["state"] == "awaiting"
    assert projection.get("prompt") == "请从候选中挑出今天的重点"


async def test_valid_answer_completes_human_step_and_stamps_action(db_session, outbox_tables):
    """[正例] 显式答案动作（decide/confirm）照常完成：完成戳 + resume 恰一次。"""
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)

    result = await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key=f"ans-{uuid4().hex[:8]}",
        action="decide",
        note="就这三条",
    )
    assert result.applied and result.resumed
    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.RUNNING
    step = next(s for s in fresh.steps if s["step_id"] == "s2-decide")
    assert step["completion"]["by"] == "user"
    assert step["completion"]["action"] == "decide"
    # 幂等重放：同步骤再确认（即使换 key）不二次 resume。
    replay = await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key=f"ans-{uuid4().hex[:8]}",
        action="confirm",
    )
    assert not replay.applied and replay.replay


# ---------------------------------------------------------------------------
# 验收 1 · 5s 内可查看/取消/离开（延迟上限钉死：超时即失败）
# ---------------------------------------------------------------------------


async def test_view_and_cancel_within_return_deadline(db_session, outbox_tables):
    """[正例+钉] 深任务运行中：查看（阶段产物/awaiting 面）与取消路径在
    ``DEEP_TASK_RETURN_DEADLINE_SECONDS`` 内完成——wait_for 超时上限可失败。"""
    assert DEEP_TASK_RETURN_DEADLINE_SECONDS <= 5.0  # 契约常量不被静默放宽
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)

    # 查看路径：当前阶段 + 阶段产物引用 + awaiting prompt 全部一次可见。
    started = time.perf_counter()
    view = await asyncio.wait_for(
        service.get_run(run.id, user_id=user.id),
        timeout=DEEP_TASK_RETURN_DEADLINE_SECONDS,
    )
    view_elapsed = time.perf_counter() - started
    payload = view.to_dict()
    assert payload["current_stage"] == "你来挑重点"
    assert payload["steps_done"] == 1 and payload["steps_total"] == 2
    awaiting = payload["awaiting_step"]
    assert awaiting["state"] == "awaiting"
    assert awaiting.get("artifacts") == [{"scheme": "tool_call", "ref": "prep-1"}]
    assert view_elapsed < DEEP_TASK_RETURN_DEADLINE_SECONDS

    # 取消路径：同上限内明确终态（离开 = 无需交互，恢复经持久态推导）。
    started = time.perf_counter()
    result = await asyncio.wait_for(
        service.cancel(run.id, user_id=user.id, idempotency_key=f"cancel-{uuid4().hex[:8]}"),
        timeout=DEEP_TASK_RETURN_DEADLINE_SECONDS,
    )
    cancel_elapsed = time.perf_counter() - started
    assert result.applied
    assert RunStatus(result.run.status) is RunStatus.CANCELLED
    assert result.run.terminal_reason == "user_cancelled"
    assert cancel_elapsed < DEEP_TASK_RETURN_DEADLINE_SECONDS


async def test_view_paths_404_isolation_within_deadline(db_session, outbox_tables):
    """[反例] 他人 run 不可见（跨用户隔离在 deadline 内明确 404，不泄漏）。"""
    user = await _make_user(db_session)
    other = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    started = time.perf_counter()
    with pytest.raises(RunNotFoundError):
        await asyncio.wait_for(
            service.get_run(run.id, user_id=other.id),
            timeout=DEEP_TASK_RETURN_DEADLINE_SECONDS,
        )
    assert time.perf_counter() - started < DEEP_TASK_RETURN_DEADLINE_SECONDS


# ---------------------------------------------------------------------------
# 验收 2 · 取消后外部副作用如实对账；重启/重试不双写
# ---------------------------------------------------------------------------


async def test_cancel_materializes_side_effect_reconciliation(db_session, outbox_tables, monkeypatch):
    """[正例] 取消已产生外部写的深任务：succeeded 写效果 + 补偿提示如实入
    result_ref 对账面——不假装回滚（效果已发生）也不丢账（明细可审计）。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    await _ledger_row(db_session, user, run, status="succeeded")
    await _ledger_row(db_session, user, run, status="failed", tool="deep_task_read")

    result = await service.cancel(run.id, user_id=user.id, idempotency_key=f"cancel-{uuid4().hex[:8]}")
    assert result.applied
    ref = result.run.result_ref
    assert ref is not None and ref["scheme"] == "partial_completion"
    assert ref["succeeded_steps"] == 1 and ref["failed_steps"] == 1
    assert ref["durable_progress"] is True  # 写效果已确认发生：不假装回滚
    assert len(ref["compensation_hints"]) == 1
    assert ref["compensation_hints"][0]["tool"] == "deep_task_write"
    # GET 面同源可见（run.to_dict 即 API 投影）。
    fresh = await service.get_run(run.id, user_id=user.id)
    assert fresh.to_dict()["result_ref"]["scheme"] == "partial_completion"


async def test_cancel_without_ledger_rows_writes_no_empty_evidence(db_session, outbox_tables):
    """[反例] 无任何账本行的取消不造空对账证据（result_ref 保持 None）。"""
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    result = await service.cancel(run.id, user_id=user.id)
    assert result.applied
    assert result.run.result_ref is None


async def test_cancel_double_fire_single_transition_single_event(db_session, outbox_tables, monkeypatch):
    """[反例·不双写] 取消重试/双发：恰一次迁移、恰一个事件、对账证据不重算。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    await _ledger_row(db_session, user, run, status="succeeded")
    key = f"cancel-{uuid4().hex[:8]}"

    first = await service.cancel(run.id, user_id=user.id, idempotency_key=key)
    assert first.applied
    status_changed = await _outbox_count(db_session, "run.status_changed")
    transitions = len(await _transition_rows(db_session, run.id))

    second = await service.cancel(run.id, user_id=user.id, idempotency_key=f"{key}:retry")
    assert not second.applied  # 幂等 no-op
    assert await _outbox_count(db_session, "run.status_changed") == status_changed
    assert len(await _transition_rows(db_session, run.id)) == transitions  # 不写第二行审计
    assert second.run.result_ref["succeeded_steps"] == 1  # 证据 first-wins 不重算


async def test_inflight_recovery_twice_no_double_write(db_session, outbox_tables, monkeypatch):
    """[反例·不双写] 重启后 inflight 恢复两轮：首轮 UNKNOWN_OUTCOME + 对账证据
    恰一次；第二轮账本 already_resolved、迁移/事件计数不变。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="重启恢复 run")).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=600)
    await _ledger_row(db_session, user, run, status="in_progress", started_at=stale)

    first = await service.recover_inflight_runs(stale_after_seconds=300)
    assert first["ledger_reconciled"] == 1
    decision = next(d for d in first["decisions"] if d.get("run_id") == str(run.id))
    assert decision["decision"] == "unknown_outcome"
    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.UNKNOWN_OUTCOME
    assert fresh.result_ref is not None and fresh.result_ref["interrupted_steps"] == 1
    status_changed = await _outbox_count(db_session, "run.status_changed")
    transitions = len(await _transition_rows(db_session, run.id))

    second = await service.recover_inflight_runs(stale_after_seconds=300)
    assert second["ledger_already_resolved"] >= 1  # 账本收敛单向：不重写
    decision = next(d for d in second["decisions"] if d.get("run_id") == str(run.id))
    assert decision["decision"] == "terminal_noop"  # 终态封闭：不二次裁决
    assert await _outbox_count(db_session, "run.status_changed") == status_changed
    assert len(await _transition_rows(db_session, run.id)) == transitions


# ---------------------------------------------------------------------------
# 验收 3 · 人类步骤不被伪造完成；预算暂停/unknown 显式对账
# ---------------------------------------------------------------------------


async def test_cancel_colliding_with_inflight_write_buckets_unknown_not_failed(db_session, outbox_tables, monkeypatch):
    """[FIX-561] 取消撞在飞写工具（竞窗 ≤ tool timeout）：result_ref 物化
    interrupted/outcome-unknown 而非虚报 failed；恢复 pass 修正账本真值后，
    first-wins 冻结的投影保持诚实（failed 恒 0——修前误标终身驻留）。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    await _ledger_row(db_session, user, run, status="succeeded")  # 已完成写步
    inflight = await _ledger_row(db_session, user, run, status="in_progress")  # 在飞写步

    result = await service.cancel(run.id, user_id=user.id)
    assert result.applied
    ref = result.run.result_ref
    assert ref is not None
    assert ref["succeeded_steps"] == 1
    assert ref["interrupted_steps"] == 1
    assert ref["failed_steps"] == 0  # 不虚报失败（修前 =1）
    assert ref["interrupted"][0]["idempotency_key"] == inflight.idempotency_key
    assert ref["interrupted"][0]["outcome"] == "unknown"

    # 恢复 pass / executor resolve 修正账本真值（终点同为 interrupted）后：
    # run 面投影冻结但标签本就诚实——与账本权威面一致，无误标驻留。
    row = await db_session.get(AgentToolCall, inflight.id)
    assert row is not None and row.status == "in_progress"  # 物化不改账本真值
    row.status = "interrupted"
    row.error_type = "InterruptedAtRecovery"
    await db_session.commit()

    fresh = await service.get_run(run.id, user_id=user.id)
    ref2 = fresh.to_dict()["result_ref"]
    assert ref2["failed_steps"] == 0  # 修前此处恒 failed=1（误标驻留）
    assert ref2["interrupted_steps"] == 1
    assert fresh.to_dict()["status"] == RunStatus.CANCELLED.value


async def test_cancel_with_failed_row_keeps_failed_bucket(db_session, outbox_tables, monkeypatch):
    """[反例锚] 真 failed 行照实落 failed 桶——修复只纠 in_progress 的误标，
    不搬真失败（succeeded/failed/interrupted 三桶语义不钝化）。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    await _ledger_row(db_session, user, run, status="failed")

    result = await service.cancel(run.id, user_id=user.id)
    assert result.applied
    ref = result.run.result_ref
    assert ref["failed_steps"] == 1
    assert ref["interrupted_steps"] == 0
    assert ref["succeeded_steps"] == 0


@pytest.mark.parametrize("target", [RunStatus.SUCCEEDED, RunStatus.PARTIAL])
@pytest.mark.parametrize("actor", ["worker", "system", "recovery", "projection", "user"])
async def test_no_path_succeeds_run_over_unanswered_human_step(db_session, outbox_tables, target, actor):
    """[反例] awaiting user step 无完成戳：任何 actor 都不能把 run 落成
    SUCCEEDED/PARTIAL——Agent/自动路径伪造人类步骤完成被服务层钉死。"""
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    status_changed = await _outbox_count(db_session, "run.status_changed")

    with pytest.raises(HumanStepNotCompletedError, match="must not forge human-step completion"):
        await service.transition(run.id, target, actor=actor)

    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.AWAITING_USER  # 等待态原样保持
    assert await _outbox_count(db_session, "run.status_changed") == status_changed  # 无事件


async def test_user_answer_then_succeed_is_legal(db_session, outbox_tables):
    """[正例] 用户显式作答（hybrid journey confirm 流同构）：完成戳 + resume 后
    RUNNING→SUCCEEDED 合法终态化——守卫只钉「未答」，不挡诚实完成。"""
    user = await _make_user(db_session)
    service, run = await _running_run_with_human_step_pending(db_session, user)
    await service.complete_user_step(
        run.id,
        step_id="s2-decide",
        user_id=user.id,
        idempotency_key=f"ans-{uuid4().hex[:8]}",
        action="confirm",
    )
    result = await service.transition(
        run.id,
        RunStatus.SUCCEEDED,
        actor="system",
        reason="completed",
        result_ref={"scheme": "journey_artifact", "ref": "artifact-1"},
    )
    assert result.applied
    assert RunStatus(result.run.status) is RunStatus.SUCCEEDED


async def test_budget_pause_materializes_reconciliation(db_session, outbox_tables, monkeypatch):
    """[正例] 预算暂停（BUDGET_EXCEEDED）的显式对账：已发生外部写效果入
    result_ref + 审计 details 带对账标记与 usage 快照——暂停不是「无事发生」。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (
        await service.create_run(
            user_id=user.id,
            objective="预算受限深任务",
            budget={"limits": {"max_tool_calls": 1}},
        )
    ).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    await _ledger_row(db_session, user, run, status="succeeded")

    with pytest.raises(BudgetExceededError, match="budget exceeded"):
        await service.enforce_budget(run.id, user_id=user.id, prospective_tool_calls=2)

    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.BUDGET_EXCEEDED
    assert fresh.terminal_reason == "budget_exceeded"
    assert fresh.result_ref is not None
    assert fresh.result_ref["succeeded_steps"] == 1
    assert fresh.result_ref["durable_progress"] is True
    last_transition = (await _transition_rows(db_session, run.id))[-1]
    assert last_transition.details.get("side_effect_reconciliation") is True
    assert "tool_calls" in last_transition.details.get("budget_exceeded", [])


async def test_budget_under_limit_leaves_run_running_without_evidence(db_session, outbox_tables):
    """[反例] 未超限不终态化、不预写对账证据（闸门只在真超限时落面）。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (
        await service.create_run(
            user_id=user.id,
            objective="预算内深任务",
            budget={"limits": {"max_tool_calls": 10}},
        )
    ).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    evaluation = await service.enforce_budget(run.id, user_id=user.id, prospective_tool_calls=1)
    assert not evaluation.is_exceeded
    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.RUNNING and fresh.result_ref is None


async def test_sweep_unknown_outcome_materializes_reconciliation(db_session, outbox_tables, monkeypatch):
    """[正例] 孤儿 run 的 UNKNOWN_OUTCOME 显式对账：sweep 终态化前物化已发生
    副作用——已写外部如实可见，结局未知不掩盖「已发生」这一事实。"""
    _stub_registry(monkeypatch, write_tools=("deep_task_write",))
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    run = (await service.create_run(user_id=user.id, objective="断网孤儿 run")).run
    await service.transition(run.id, RunStatus.RUNNING, actor="worker")
    await _ledger_row(db_session, user, run, status="succeeded")
    # 心跳回拨至陈旧（模拟断网/重启后的孤儿）。
    run.heartbeat_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
    await db_session.commit()

    summary = await service.recover_stale_runs(stale_after_seconds=300)
    action = next(a for a in summary["actions"] if a.get("run_id") == str(run.id))
    assert action["kind"] == "orphan_unknown_outcome" and action["applied"]
    fresh = await service.get_run(run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.UNKNOWN_OUTCOME
    assert fresh.terminal_reason == "worker_restart_orphan"
    assert fresh.result_ref is not None
    assert fresh.result_ref["succeeded_steps"] == 1 and fresh.result_ref["durable_progress"] is True
