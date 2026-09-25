"""wt392 · 双轮审查第二轮 · WT391-HUNT-R3 F1-F3 修复守卫（红测先行）.

独立复核结论（全部 CONFIRMED，逐项在 REPORT 登记）：

- **F1（P1）J-06 死 run 钉死**：``start_hybrid_journey`` 用默认幂等键
  ``hybrid_journey:{task_id}``，但 prep 检索失败/零命中发生在 run 两次内部
  提交（``create_run`` + ``transition(RUNNING)``）**之后**——重试永远
  resolve 到这个无产物死 run：judgment 409、confirm 409、无任何 cancel
  路由。第二面：awaiting judgment 可等任意久（``wait_expires_at=None``），
  但 admin sweep 把心跳 >6h 的 AWAITING_USER 判 ``UNKNOWN_OUTCOME`` 终态，
  同样被默认键永久钉死。
  契约：① prep 失败启动把本次死 run 诚实补偿到 FAILED；② 幂等键命中
  **终态** run 时不开新 attempt 会永久钉死——重试必须释放键开新 attempt；
  ③ 活跃 run 仍幂等回放（双击/重开不重复建 run）。
- **F2（P1）J-06 confirm 半确认孤儿**：``confirm_outcome`` 先
  ``complete_user_step``（完成戳+resume 在内部事务提交）后
  ``TaskService.complete_task``；后者任何一次失败（NotFoundError/状态迁移
  校验/DB）→ 500，重试命中完成戳走 ``_confirmed_replay`` 谎报
  「已确认」——任务从未完成、run 永停 RUNNING、outcome 永不捕获。
  契约：事务重排——任务完成先于完成戳；complete_task 失败 → 完成戳未写、
  run 仍在 AWAITING_USER（可恢复），错误映射为 HybridJourneyStateError；
  complete_task 成功后任一步失败 → 重试经「已 COMPLETED 跳过」分支收敛。
- **F3（P1）Tier 提权**：``_resolve_request_user_tier`` 让客户端 WS
  ``extra_context.user_tier/userTier`` **覆盖**网关权威
  ``user_profile.is_pro``——free 用户单条消息自提 pro 车道（free 钳制旁路
  + 免疫自适应重排）。wt380 双形态解析本体是网关注入兼容面（内部/基准
  调用方无 user_profile 时仍要可用，wt380 契约锁 8/8 不回退）；
  但真实链路网关对每条消息都填 user_profile（``buildAgentUserProfile``，
  chatflow 单一装配点）——契约：**user_profile 已权威声明时，客户端
  extra_context 的升档词一律忽略**（降级词 free 仍允许，钳制语义）。

纪律：pytest + sqlite 口径（StaticPool 内存库）；J-06 fixture/种子复用
``test_j06_hybrid_journey``（同装配、零第二套 fixture）。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, update

from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun
from app.models.galaxy import KnowledgeNode
from app.models.task import TaskStatus
from tests.unit.test_j06_hybrid_journey import (  # noqa: F401  (fixtures/种子复用；注册名 bus_stub/j06_db)
    _scripted_outline_llm,
    _seed_goal,
    _seed_materials,
    _seed_task,
    bus_stub_fixture,
    j06_db_fixture,
)


async def _seed_world(db, *, with_materials: bool):
    """J-06 e2e 同款真实锚点：goal + 节点 + 在飞任务（材料可选）。"""
    from tests.unit.test_action_command_service import _make_user

    user = await _make_user(db)
    await _seed_goal(db, user)
    node = KnowledgeNode(name=f"wt392 联邦学习 {uuid4().hex[:6]}", importance_level=3, is_seed=True)
    db.add(node)
    await db.flush()
    task = await _seed_task(db, user, node)
    stored = chunks = None
    if with_materials:
        stored, chunks = await _seed_materials(db, user)
    await db.commit()
    return user, task, stored, chunks


async def _drive_to_outcome_awaiting(db, user, task) -> str:
    """start → judgment（脚本化 LLM）→ awaiting outcome；返回 run_id。"""
    from app.services.hybrid_journey_service import start_hybrid_journey, submit_judgment

    started = await start_hybrid_journey(db, user_id=user.id, task_id=task.id)
    run_view = started["run"]
    citations = started["citations"]
    chosen = citations[:2]
    judged = await submit_judgment(
        db,
        user_id=user.id,
        run_id=run_view["run_id"],
        selected_refs=[c["source_ref"] for c in chosen],
        focus_note="优先隐私机制对比",
        idempotency_key=f"judge-{run_view['run_id'][:8]}",
        llm_chat=_scripted_outline_llm(tuple(c["snippet"] for c in chosen)),
    )
    assert judged["run"]["awaiting_step"] is not None
    assert judged["run"]["awaiting_step"]["step_id"] == "outcome"
    return run_view["run_id"]


# ============================================================================
# F1 · J-06 死 run 钉死：prep 失败补偿 + 终态键释放 → 旅程可恢复
# ============================================================================


@pytest.mark.asyncio
async def test_f1_prep_failure_compensates_run_and_retry_starts_fresh_attempt(j06_db, bus_stub):
    """prep 零命中（新用户常态）→ 422 no_materials；补传材料重试必须能
    真实重检索开新 attempt——死 run 被补偿为 FAILED，默认键不钉死旅程。"""
    from app.services.hybrid_journey_service import NoMaterialError, start_hybrid_journey

    user, task, _stored, _chunks = await _seed_world(j06_db, with_materials=False)

    with pytest.raises(NoMaterialError):
        await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)

    dead = (
        (await j06_db.execute(select(AgentRun).where(AgentRun.user_id == user.id)))
        .scalars()
        .one()
    )
    dead_run_id = dead.id

    # 补传材料后重试（无显式幂等键 → 同默认键 hybrid_journey:{task_id}）
    _stored, _chunks = await _seed_materials(j06_db, user)
    await j06_db.commit()
    retry = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)

    assert retry["run"]["run_id"] != str(dead_run_id), (
        "重试必须开新 attempt run，而不是回放到无产物死 run"
    )
    assert retry.get("citations"), "重试必须真实重检索（死壳回放没有 citations）"
    awaiting = retry["run"].get("awaiting_step")
    assert awaiting is not None and awaiting["step_id"] == "judgment", (
        "新 attempt 必须走到判断等待面"
    )
    await j06_db.refresh(dead)
    assert RunStatus(str(dead.status)) is RunStatus.FAILED, (
        "prep 失败的死 run 必须被补偿为诚实终态 FAILED（否则 sweep 还要 6h 才判死）"
    )


@pytest.mark.asyncio
async def test_f1_swept_terminal_run_releases_default_key_on_retry(j06_db, bus_stub):
    """判断挂起 >6h 被 admin sweep 判 UNKNOWN_OUTCOME 后，重试 start 必须
    开新 attempt（键命中终态 run 即释放），而不是永久回放死 run。"""
    from app.services.agent_run_service import AgentRunService
    from app.services.hybrid_journey_service import start_hybrid_journey

    user, task, _stored, _chunks = await _seed_world(j06_db, with_materials=True)

    # 走到 awaiting judgment（本测只关心 AWAITING_USER 的 sweep 面）
    started = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    swept_run_id = uuid.UUID(started["run"]["run_id"])

    stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=7)
    await j06_db.execute(update(AgentRun).where(AgentRun.id == swept_run_id).values(heartbeat_at=stale))
    await j06_db.commit()

    await AgentRunService(j06_db).recover_stale_runs(stale_after_seconds=6 * 3600)
    swept = (await j06_db.execute(select(AgentRun).where(AgentRun.id == swept_run_id))).scalars().one()
    assert RunStatus(str(swept.status)) is RunStatus.UNKNOWN_OUTCOME, "前置：sweep 判死"

    retry = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    assert retry["run"]["run_id"] != str(swept_run_id), "终态 run 必须释放幂等键（开新 attempt）"
    assert retry.get("citations"), "新 attempt 必须真实重检索"
    awaiting = retry["run"].get("awaiting_step")
    assert awaiting is not None and awaiting["step_id"] == "judgment"


@pytest.mark.asyncio
async def test_f1_active_run_still_replays_idempotently(j06_db, bus_stub):
    """回归守卫：活跃 run（awaiting judgment）重复 start 仍幂等回放同一 run，
    不开新 attempt（F1 修复不得破坏「同 task 重复启动收敛同一 run」）。"""
    from app.services.hybrid_journey_service import start_hybrid_journey

    user, task, _stored, _chunks = await _seed_world(j06_db, with_materials=True)
    started = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    replay = await start_hybrid_journey(j06_db, user_id=user.id, task_id=task.id)
    assert replay["run"]["run_id"] == started["run"]["run_id"], "活跃 run 必须幂等回放"
    assert replay["run"].get("awaiting_step", {}).get("step_id") == "judgment"


# ============================================================================
# F2 · J-06 confirm 半确认孤儿：任务完成先于完成戳（事务重排）
# ============================================================================


@pytest.mark.asyncio
async def test_f2_complete_task_failure_retry_completes_honestly(j06_db, bus_stub, monkeypatch):
    """complete_task 瞬时失败（重试收敛）：
    - 首次 confirm 失败后 run 必须仍在 AWAITING_USER（完成戳未写）；
    - 重试必须真实完成任务并 SUCCEEDED，而不是谎报「已确认过」。"""
    from app.core.exceptions import NotFoundError
    from app.services.hybrid_journey_service import confirm_outcome, get_hybrid_journey_state
    from app.services.task_service import TaskService

    user, task, _stored, _chunks = await _seed_world(j06_db, with_materials=True)
    run_id = await _drive_to_outcome_awaiting(j06_db, user, task)

    real_complete = TaskService.complete
    fail_flag = {"on": True}

    async def flaky_complete(db_, task_, *args, **kwargs):
        if fail_flag["on"]:
            raise NotFoundError(message="transient complete_task failure")
        return await real_complete(db_, task_, *args, **kwargs)

    monkeypatch.setattr(TaskService, "complete", flaky_complete)
    with pytest.raises(Exception):
        await confirm_outcome(j06_db, user_id=user.id, run_id=run_id, idempotency_key="c1")
    monkeypatch.setattr(TaskService, "complete", real_complete)

    state_after_fail = await get_hybrid_journey_state(j06_db, user_id=user.id, run_id=run_id)
    assert state_after_fail["run"].get("awaiting_step") is not None, (
        "complete_task 失败后 run 必须仍在等待确认（完成戳未写）——半确认孤儿即回放谎报之源"
    )

    confirmed = await confirm_outcome(j06_db, user_id=user.id, run_id=run_id, idempotency_key="c2")
    await j06_db.refresh(task)
    assert task.status == TaskStatus.COMPLETED, "重试必须真实完成任务（而非谎报已确认）"
    assert confirmed["run"]["status"] == "SUCCEEDED", "重试后 run 必须真终态"
    assert confirmed["receipt"]["receipt_type"] == "hybrid_journey_completed"


@pytest.mark.asyncio
async def test_f2_task_anchor_gone_leaves_run_recoverable_not_stamped(j06_db, bus_stub):
    """任务锚消失（NotFoundError 面）：confirm 诚实拒绝（StateError→409 面），
    且完成戳未写——run 停在 AWAITING_USER 可恢复，而非已戳 RUNNING 的孤儿。"""
    from app.services.hybrid_journey_service import (
        HybridJourneyStateError,
        confirm_outcome,
        get_hybrid_journey_state,
    )

    user, task, _stored, _chunks = await _seed_world(j06_db, with_materials=True)
    run_id = await _drive_to_outcome_awaiting(j06_db, user, task)

    await j06_db.delete(task)
    await j06_db.commit()

    with pytest.raises(HybridJourneyStateError):
        await confirm_outcome(j06_db, user_id=user.id, run_id=run_id, idempotency_key="c1")

    state = await get_hybrid_journey_state(j06_db, user_id=user.id, run_id=run_id)
    assert state["run"].get("awaiting_step") is not None, (
        "任务锚消失的失败不得写完成戳：run 必须仍可恢复（等待确认），而非已戳 RUNNING 孤儿"
    )


# ============================================================================
# F3 · Tier 提权面：网关权威 user_profile 已声明时，客户端 extra_context
#      升档词一律忽略；降级词与「无声明」双形态契约保留（wt380 本体不动）
# ============================================================================


def _chat_request(*, is_pro: bool | None, extra: dict | None):
    from app.gen.agent.v1 import agent_service_pb2

    kwargs: dict = {}
    if is_pro is not None:
        kwargs["user_profile"] = agent_service_pb2.UserProfile(is_pro=is_pro)
    if extra is not None:
        kwargs["extra_context"] = extra
    return agent_service_pb2.ChatRequest(**kwargs)


def _resolve(request):
    from app.services.agent_grpc_service import AgentServiceImpl

    return AgentServiceImpl._resolve_request_user_tier(request)


@pytest.mark.parametrize(
    "key", ["user_tier", "userTier"], ids=["snake", "camel"]
)
def test_f3_declared_free_profile_blocks_client_elevation(key: str):
    """红测（wt391 F3）：free 用户伪造 userTier=pro 必须仍是 free。"""
    for word in ("pro", "premium", "paid"):
        assert _resolve(_chat_request(is_pro=False, extra={key: word})) == "free", (
            f"网关权威 is_pro=False 时客户端 {key}={word!r} 不得自提 pro 车道"
        )


def test_f3_declared_pro_profile_and_free_override_contract():
    """pro 权威不被动摇；free 降级词仍允许（钳制语义不能被绕过，wt380 契约）。"""
    assert _resolve(_chat_request(is_pro=True, extra=None)) == "pro"
    assert _resolve(_chat_request(is_pro=True, extra={"user_tier": "pro"})) == "pro"
    assert _resolve(_chat_request(is_pro=True, extra={"userTier": "free"})) == "free"


@pytest.mark.parametrize(
    "key", ["user_tier", "userTier"], ids=["snake", "camel"]
)
def test_f3_undeclared_profile_dual_form_contract_preserved(key: str):
    """无 user_profile（内部/基准调用方）→ wt380 双形态契约原样保留。"""
    assert _resolve(_chat_request(is_pro=None, extra={key: "pro"})) == "pro"
    assert _resolve(_chat_request(is_pro=None, extra={key: "free"})) == "free"


def test_f3_malformed_extra_context_falls_back_to_authority():
    """extra_context 解析异常/垃圾词 → 权威值兜底（free），不崩不升档。"""
    assert _resolve(_chat_request(is_pro=False, extra={"user_tier": "enterprise-ultra"})) == "free"
    assert _resolve(_chat_request(is_pro=True, extra={"user_tier": "  PRO  "})) == "pro"
