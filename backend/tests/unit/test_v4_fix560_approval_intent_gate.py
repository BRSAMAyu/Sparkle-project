"""V4-FIX-560 · approval 等待态源头 intent 门 —— 可失败契约测试.

向量（I08 双审 C-1 升格，台账 V3-FIX-560）：引擎信任边界内直调
:meth:`AgentRunService.transition` 三步链
``RUNNING → AWAITING_APPROVAL → SUCCEEDED``（无 intent、无任何 approval 动作）
曾 ``applied=True`` 且无自愈——approval 等待的解除通道是 intent 状态漏斗
（approve/reject 变更 intent → ``project_intent_status`` 投影），无 intent 的
approval 等待没有任何解除通道，属死态；伪造的「审批暂停」审计行还为
豁免提供掩盖面。

修法（R2 建议 b 案）：**transition 进入 AWAITING_APPROVAL 时要求 intent_id
非空**，逐源头拒绝（任何 actor），与 I08 的 user_step 守卫
（:class:`HumanStepNotCompletedError`）同构——图零改动，服务层钉死。

覆盖（每面一正一反；变异必红锚点）：

1. [反例] 无 intent 的 run 任何 actor 都进不了 AWAITING_APPROVAL——错误信息
   写明「无 intent 的 approval 等待无解除通道」；run 原状态保持、无
   ``run.awaiting_user`` 事件、无 ``AWAITING_APPROVAL`` 审计行（伪造等待态
   从未存在）；
2. [反例] 原三步链亲构造：第二步即断，SUCCEEDED 永远接不到伪造的审批暂停；
   QUEUED 入口同样拒绝；
3. [正例] intent 绑定的合法链照常：RUNNING → AWAITING_APPROVAL（applied、
   wait_kind=approval、事件照发）→ resume(EXECUTING)（解除通道真实存在）→
   SUCCEEDED；
4. [正例] in-tree 唯一生产者 ``project_intent_status``（waiting_approval 投影）
   不受影响；
5. [图优先] ``AWAITING_USER → AWAITING_APPROVAL`` 禁边仍先由封闭迁移图拒绝
   （IllegalRunTransitionError 先于 intent 门，无 intent 也不例外）。

测试同构 ``test_v4_i08_deep_task_return_control.py``（sqlite + 最小 outbox DDL；
复用 ``test_agent_run_service`` 的 user/intent 建行 helper）。
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.core.run_state_machine import IllegalRunTransitionError, RunStatus
from app.models.agent_run import AgentRunTransition
from app.services.agent_run_service import (
    AgentRunService,
    ApprovalWaitRequiresIntentError,
)
from tests.unit.test_agent_run_service import (  # noqa: F401 — 复用 helpers
    _OUTBOX_DDL,
    _make_intent,
    _make_user,
)

_FORGED_CHAIN_ACTORS = ["worker", "system", "recovery", "projection", "user"]


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


async def _awaiting_approval_transitions(db_session, run_id) -> list[AgentRunTransition]:
    result = await db_session.execute(
        select(AgentRunTransition).where(
            AgentRunTransition.run_id == run_id,
            AgentRunTransition.to_status == RunStatus.AWAITING_APPROVAL.value,
        )
    )
    return list(result.scalars().all())


async def _outbox_awaiting_count(db_session) -> int:
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM event_outbox WHERE event_type = 'run.awaiting_user' AND payload LIKE '%approval%'")
    )
    return int(result.scalar_one())


# ---------------------------------------------------------------------------
# 1. 反例 · 无 intent 的 approval 等待逐源头拒绝（向量钉死）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("actor", _FORGED_CHAIN_ACTORS)
async def test_intentless_run_cannot_enter_awaiting_approval_any_actor(db_session, outbox_tables, actor):
    """[反例] 无 intent 绑定的 run：任何 actor 直调 transition 进 AWAITING_APPROVAL
    一律 ApprovalWaitRequiresIntentError——等待态从未存在，无事件无审计。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj", idempotency_key="k1")
    assert created.run.intent_id is None
    running = await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    assert running.applied is True

    with pytest.raises(ApprovalWaitRequiresIntentError, match="无 intent 的 approval 等待无解除通道"):
        await service.transition(created.run.id, RunStatus.AWAITING_APPROVAL, actor=actor)

    fresh = await service.get_run(created.run.id, user_id=user.id)
    assert RunStatus(fresh.status) is RunStatus.RUNNING  # 原状态保持
    assert fresh.wait_kind is None and fresh.wait_expires_at is None  # 未落任何等待戳
    assert await _awaiting_approval_transitions(db_session, created.run.id) == []  # 伪造等待从未入账
    assert await _outbox_awaiting_count(db_session) == 0  # 无 run.awaiting_user 事件


async def test_intentless_approval_gate_rejected_from_queued_too(db_session, outbox_tables):
    """[反例] QUEUED → AWAITING_APPROVAL（图内合法边）同样过 intent 门：死态与
    入口无关，排队 run 伪造审批暂停同拒。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj")

    with pytest.raises(ApprovalWaitRequiresIntentError, match="no release channel"):
        await service.transition(created.run.id, RunStatus.AWAITING_APPROVAL, actor="system")
    fresh = await service.get_run(created.run.id)
    assert RunStatus(fresh.status) is RunStatus.QUEUED


async def test_forged_three_step_chain_dies_at_approval_entry(db_session, outbox_tables):
    """[反例·原向量亲构造] RUNNING→AWAITING_APPROVAL→SUCCEEDED 三步链：第二步
    即断（C-1 向量的第一步不再 applied=True），伪造豁免链不可达。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj", idempotency_key="k2")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")

    with pytest.raises(ApprovalWaitRequiresIntentError):
        await service.transition(created.run.id, RunStatus.AWAITING_APPROVAL, actor="worker")
    # 链断在第二步：终态化不可借「审批暂停已发生」继续（死态从未落库）。
    fresh = await service.get_run(created.run.id)
    assert RunStatus(fresh.status) is RunStatus.RUNNING
    assert await _awaiting_approval_transitions(db_session, created.run.id) == []


# ---------------------------------------------------------------------------
# 2. 正例 · intent 绑定的合法链 / 唯一生产者照常
# ---------------------------------------------------------------------------


async def test_intent_bound_approval_chain_still_legal(db_session, outbox_tables):
    """[正例] intent 绑定的 run：approval 等待照常落（事件+审计+wait_kind），经
    resume 解除（intent 漏斗/用户动作即解除通道）后合法终态化——守卫只钉
    「无 intent」，不挡诚实审批链。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)
    created = await service.create_run(
        user_id=user.id,
        objective="obj",
        intent_id=intent.id,
        idempotency_key="k3",
    )

    running = await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    assert running.applied is True
    awaiting = await service.transition(
        created.run.id,
        RunStatus.AWAITING_APPROVAL,
        actor="worker",
        wait_kind="approval",
    )
    assert awaiting.applied is True
    assert awaiting.run.status is RunStatus.AWAITING_APPROVAL
    assert awaiting.run.wait_kind == "approval"
    assert awaiting.event_name == "run.awaiting_user"  # 语义事件照发
    assert len(await _awaiting_approval_transitions(db_session, created.run.id)) == 1
    assert await _outbox_awaiting_count(db_session) == 1

    resumed = await service.resume(created.run.id, user_id=user.id, to_status=RunStatus.EXECUTING)
    assert resumed.applied is True and resumed.event_name == "run.user_resumed"
    done = await service.transition(created.run.id, RunStatus.SUCCEEDED, actor="worker", reason="completed")
    assert done.applied is True and done.run.terminal_reason == "completed"


async def test_projection_remains_the_only_legal_producer(db_session, outbox_tables):
    """[正例] in-tree 唯一生产者 project_intent_status（waiting_approval 投影）
    不受影响——run 由 intent 漏斗找到，天然绑定。"""
    user = await _make_user(db_session)
    intent = await _make_intent(db_session, user)
    service = AgentRunService(db_session)

    r1 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="dispatched")
    assert r1.run.status is RunStatus.RUNNING
    r2 = await service.project_intent_status(intent_id=intent.id, user_id=user.id, new_status="waiting_approval")
    assert r2 is not None and r2.applied is True
    assert r2.run.status is RunStatus.AWAITING_APPROVAL and r2.run.wait_kind == "approval"
    assert r2.run.intent_id == intent.id


# ---------------------------------------------------------------------------
# 3. 图优先 · 禁边仍由封闭迁移图先拒
# ---------------------------------------------------------------------------


async def test_user_approval_swap_is_still_graph_illegal_first(db_session, outbox_tables):
    """[图优先] AWAITING_USER → AWAITING_APPROVAL 禁边（等待类型变更无业务语义）
    仍先抛 IllegalRunTransitionError——intent 门不抢图判定、不改错误族。"""
    user = await _make_user(db_session)
    service = AgentRunService(db_session)
    created = await service.create_run(user_id=user.id, objective="obj", idempotency_key="k4")
    await service.transition(created.run.id, RunStatus.RUNNING, actor="worker")
    await service.transition(created.run.id, RunStatus.AWAITING_USER, actor="worker")

    with pytest.raises(IllegalRunTransitionError):
        await service.transition(created.run.id, RunStatus.AWAITING_APPROVAL, actor="worker")
    fresh = await service.get_run(created.run.id)
    assert RunStatus(fresh.status) is RunStatus.AWAITING_USER
