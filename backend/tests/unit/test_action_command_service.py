"""X-03 · ActionCommandService 协议机制测试（统一 command path 的验收证据）.

验收覆盖（卡面 Acceptance 一一对应）：
- 重复确认不重复写（同 proposal 重复 approve 恰一次 commit：恰一行 COMMITTED
  审计、恰一条 action.accepted 事件、subject 恰一次变更、receipt 原样重放）；
- 版本冲突不覆盖（stale version → ACTION_VERSION_CONFLICT + subject 未被覆盖
  + proposal 保持 PENDING）；
- 未授权不执行（permission decision 前置；confirmation 模式无确认 → 403；
  高风险永不让 auto 直通）；
- expiry（过期作废：显式 EXPIRED 持久状态 + 410 + sweep）；
- cancel（终态封闭 + 幂等 + user_cancelled 归因，X-05 对齐）/ reject 区分；
- receipt 权威性（get_receipt / 幂等键查询 / 未落账 409）；
- diff 可渲染（before/after/changed_fields）；
- 创建幂等（(user_id, idempotency_key) 恰一次）；
- 词表冻结（状态/命令/归因/授权 reason codes / 事件名零新增）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import (
    ACTION_COMMAND_PROTOCOL_VERSION,
    TERMINAL_REASON_VOCABULARY,
    ActionCommandType,
    AuthorizationDeniedError,
    ProposalExpiredError,
    ProposalNotFoundError,
    ProposalNotPendingError,
    ProposalSource,
    ProposalStatus,
    VersionConflictError,
)
from app.core.event_registry import EVENT_REGISTRY
from app.models.action_proposal import ActionProposal, ActionProposalTransition
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.models.user_settings import UserSettings
from app.schemas.task import TaskUpdate
from app.services.action_authorization import authorize_commit, decide_authorization_mode
from app.services.action_command_service import ActionCommandService
from app.services.task_service import TaskService

# --- sqlite 测试下的 outbox DDL（X-05 test_agent_run_service 同法） -------------

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


async def _make_task(db_session, user: User, *, status: TaskStatus = TaskStatus.IN_PROGRESS) -> Task:
    task = Task(
        user_id=user.id,
        title="刷完高数第三章习题",
        type=TaskType.LEARNING,
        tags=["x03"],
        estimated_minutes=30,
        difficulty=3,
        energy_cost=2,
        status=status,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


async def _grant_low_risk_auto(db_session, user: User, *, enabled: bool = True) -> None:
    """服务端真源写入：UserSettings.low_risk_auto_execute（R2 P2-3 返修后的总开关）.

    P-04 起完整预授权 = 总开关 ∧ 类别级 allowlist（UserPreferencesCenter.explicit
    的 grant/revoke 面）。本 helper 同时授予全部 auto-eligible 类别，保持「总开关
    即授权」的既有用例语义；类别维度本身由 test_p04_auto_execution_permissions.py
    单独验收（未授予类别 → confirmation）。
    """
    from app.services.action_permission_service import ActionPermissionService

    settings = UserSettings(user_id=user.id, low_risk_auto_execute=enabled)
    db_session.add(settings)
    await db_session.commit()
    if enabled:
        permissions = ActionPermissionService(db_session)
        for category in ("task.update_status", "task.update_fields"):
            await permissions.grant_category(user.id, category)


async def _outbox_count(db_session, event_type: str) -> int:
    result = await db_session.execute(
        text("SELECT COUNT(*) FROM event_outbox WHERE event_type = :t"), {"t": event_type}
    )
    return int(result.scalar_one())


async def _committed_transitions(db_session, proposal_id) -> list:
    return list(
        (
            await db_session.execute(
                select(ActionProposalTransition).where(
                    ActionProposalTransition.proposal_id == proposal_id,
                    ActionProposalTransition.to_status == ProposalStatus.COMMITTED.value,
                )
            )
        )
        .scalars()
        .all()
    )


async def _propose_complete(db_session, user: User, task: Task, **kwargs):
    return await ActionCommandService(db_session).create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
        payload={"task_id": str(task.id), "to_status": "COMPLETED"},
        source=ProposalSource.AURORA.value,
        **kwargs,
    )


# ============================================================================
# 1. 重复确认不重复写（恰一次 commit）
# ============================================================================


async def test_repeated_approve_commits_exactly_once(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)

    result = await _propose_complete(db_session, user, task)
    proposal = result.proposal
    assert result.created is True
    assert proposal.status is ProposalStatus.PENDING

    service = ActionCommandService(db_session)
    first = await service.approve(proposal.id, user_id=user.id, idempotency_key="confirm-1")
    assert first.applied is True
    assert first.already_committed is False

    # 重复确认（不同幂等键、无键，各种重放形态）
    second = await service.approve(proposal.id, user_id=user.id, idempotency_key="confirm-2")
    third = await service.approve(proposal.id, user_id=user.id)
    assert second.already_committed is True and second.applied is False
    assert third.already_committed is True and third.applied is False
    assert second.proposal.receipt["receipt_id"] == first.proposal.receipt["receipt_id"]
    assert third.proposal.receipt["receipt_id"] == first.proposal.receipt["receipt_id"]

    # 恰一次 commit：审计、事件、领域效果
    assert len(await _committed_transitions(db_session, proposal.id)) == 1
    assert await _outbox_count(db_session, "action.accepted") == 1
    assert await _outbox_count(db_session, "action.proposed") == 1
    await db_session.refresh(task)
    assert task.status is TaskStatus.COMPLETED  # 领域效果恰一次（COMPLETED 无出边，重放即证据）
    assert task.completed_at is not None


async def test_concurrent_approve_second_is_replay(db_session, outbox_tables):
    """并发 approve：第二个调用方看到 COMMITTED → no-op（行锁+复查语义的串行化等价）."""
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)

    service = ActionCommandService(db_session)
    await service.approve(result.proposal.id, user_id=user.id, idempotency_key="k1")
    replay = await service.approve(result.proposal.id, user_id=user.id, idempotency_key="k1")
    assert replay.applied is False and replay.already_committed is True
    assert len(await _committed_transitions(db_session, result.proposal.id)) == 1


# ============================================================================
# 2. 版本冲突不覆盖（乐观并发）
# ============================================================================


async def test_stale_version_rejected_without_overwrite(db_session, outbox_tables):
    user = await _make_user(db_session)
    user_id = user.id  # rollback 会使 ORM 对象过期；持原始值（X-05 house 模式）
    task = await _make_task(db_session, user)
    task_id = task.id
    result = await _propose_complete(db_session, user, task)
    proposal = result.proposal
    proposal_id = proposal.id
    stale_token = proposal.subject_version_token

    # proposal 创建后、确认前：权威路径另有一次写（updated_at bump）
    await TaskService.update(db_session, task, TaskUpdate(priority=5))
    await db_session.refresh(task)
    fresh_token = ActionCommandService(db_session).proposal_projection(proposal)["subject_version_token"]

    service = ActionCommandService(db_session)
    with pytest.raises(VersionConflictError) as exc_info:
        await service.approve(proposal_id, user_id=user_id)
    err = exc_info.value
    assert err.error_code == "ACTION_VERSION_CONFLICT"
    assert err.details["proposal_version_token"] == stale_token
    assert err.details["current_version_token"] != stale_token
    assert fresh_token  # 词法占位：projection 可读

    # 不覆盖：任务仍是中间写的结果，未被 proposal 的 COMPLETED 覆盖
    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS
    assert task.priority == 5

    # proposal 保持 PENDING（可刷新重提，或取消）——不是静默丢弃
    await db_session.refresh(proposal)
    assert proposal.status is ProposalStatus.PENDING
    # 且没有落任何 commit 痕迹
    assert proposal.receipt is None
    assert len(await _committed_transitions(db_session, proposal_id)) == 0
    assert await _outbox_count(db_session, "action.accepted") == 0

    # 冲突后仍可取消（生命周期不被冲突卡死）
    cancelled = await service.cancel(proposal_id, user_id=user_id)
    assert cancelled.applied is True
    reloaded = await service.get_proposal(proposal_id, user_id=user_id)
    assert reloaded.status is ProposalStatus.CANCELLED
    _ = task_id  # 语义占位：任务身份在冲突断言中已复核


async def test_fresh_version_approves_cleanly(db_session, outbox_tables):
    """无中间写时版本 token 一致 → 正常落账（冲突检查不放过头）."""
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)
    service = ActionCommandService(db_session)
    committed = await service.approve(result.proposal.id, user_id=user.id)
    assert committed.applied is True
    await db_session.refresh(task)
    assert task.status is TaskStatus.COMPLETED


# ============================================================================
# 3. 未授权不执行（permission decision 前置）
# ============================================================================


def test_authorization_mode_decision_rules():
    # auto 需四条件同时成立
    auto = decide_authorization_mode(risk_class="low", reversible=True, user_auto_grant=True)
    assert auto.mode == "auto"
    assert "risk_low_reversible_auto_grant" in auto.reason_codes

    assert decide_authorization_mode(risk_class="high", reversible=True, user_auto_grant=True).mode == "confirmation"
    assert decide_authorization_mode(risk_class="low", reversible=False, user_auto_grant=True).mode == "confirmation"
    assert decide_authorization_mode(risk_class="low", reversible=True).mode == "confirmation"
    assert (
        decide_authorization_mode(
            risk_class="low", reversible=True, user_auto_grant=True, requires_human_approval=True
        ).mode
        == "confirmation"
    )


def test_authorize_commit_denies_without_confirmation():
    # confirmation 模式、无确认记录 → 拒绝（软件强制，不执行）
    with pytest.raises(AuthorizationDeniedError) as exc_info:
        authorize_commit({"mode": "confirmation", "confirmed_by": None})
    assert exc_info.value.error_code == "ACTION_UNAUTHORIZED"

    # 授权记录缺失：保守拒绝（绝不放行）
    with pytest.raises(AuthorizationDeniedError):
        authorize_commit(None)

    # 有确认 / auto 模式：放行
    assert authorize_commit({"mode": "confirmation", "confirmed_by": "user"}).allowed is True
    assert authorize_commit({"mode": "auto"}).allowed is True


async def test_unconfirmed_proposal_never_auto_executes(db_session, outbox_tables):
    """execute_if_authorized 只在授权 mode=auto 时直通；否则保持 PENDING 等确认."""
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)

    result = await _propose_complete(db_session, user, task, execute_if_authorized=True)
    assert result.proposal.status is ProposalStatus.PENDING  # 无 auto 授权 → 不执行
    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS


async def test_high_risk_never_auto_path(db_session, outbox_tables):
    """不可逆命令（终态目标 COMPLETED）即使服务端已授权+请求直通也必须走确认.

    R2 P2-1/P2-2 返修前：update_status 硬编码 reversible=True——不可逆的完成
    任务可走 auto 直通；返修后 per-command 语义导出，终态目标 medium/不可逆。
    """
    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)
    result = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
        payload={"task_id": str(task.id), "to_status": "COMPLETED"},
        execute_if_authorized=True,
    )
    assert result.proposal.status is ProposalStatus.PENDING
    assert result.proposal.authorization["mode"] == "confirmation"
    assert "auto_forbidden_irreversible" in result.proposal.authorization["reason_codes"]
    assert result.proposal.risk_class == "medium"
    assert result.proposal.reversible == "false"
    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS  # 未执行


async def test_auto_grant_path_commits_inline(db_session, outbox_tables):
    """低风险+可逆+服务端已授权+请求直通 → 创建即落账（V2「用户已授予的低风险自动权限」）.

    R2 P2-3 返修：授权真源是 UserSettings.low_risk_auto_execute（服务端自查），
    不是任何调用方参数。
    """
    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)
    result = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 9}},
        execute_if_authorized=True,
    )
    assert result.proposal.status is ProposalStatus.COMMITTED
    assert result.proposal.receipt is not None
    assert result.proposal.authorization["mode"] == "auto"
    await db_session.refresh(task)
    assert task.priority == 9


# ============================================================================
# 4. expiry（过期作废 + 显式状态 + sweep）
# ============================================================================


async def test_expired_proposal_rejected_and_state_explicit(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)
    proposal = result.proposal

    # 时间推进到过期（直接改行，模拟等待）
    proposal.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    db_session.add(proposal)
    await db_session.commit()

    service = ActionCommandService(db_session)
    with pytest.raises(ProposalExpiredError) as exc_info:
        await service.approve(proposal.id, user_id=user.id)
    assert exc_info.value.error_code == "ACTION_EXPIRED"

    # 状态显式持久化为 EXPIRED（非读时挥发）；有审计行与 action.rejected 事件
    await db_session.refresh(proposal)
    assert proposal.status is ProposalStatus.EXPIRED
    assert proposal.terminal_reason == "expired"
    assert await _outbox_count(db_session, "action.rejected") == 1

    # 过期后不可再 approve（终态封闭）
    with pytest.raises(ProposalNotPendingError):
        await service.approve(proposal.id, user_id=user.id)

    # 领域未被写
    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS


async def test_expiry_sweep_bulk_expires(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    for _ in range(3):
        await _propose_complete(db_session, user, task)
    # 全部推进为过期
    rows = list(
        (await db_session.execute(select(ActionProposal).where(ActionProposal.user_id == user.id))).scalars().all()
    )
    for row in rows:
        row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
    await db_session.commit()

    expired_count = await ActionCommandService(db_session).expire_stale_proposals()
    assert expired_count == 3
    for row in rows:
        await db_session.refresh(row)
        assert row.status is ProposalStatus.EXPIRED


# ============================================================================
# 5. cancel / reject（终态封闭 + 幂等 + X-05 归因对齐）
# ============================================================================


async def test_cancel_semantics(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)

    service = ActionCommandService(db_session)
    cancelled = await service.cancel(result.proposal.id, user_id=user.id)
    assert cancelled.applied is True
    await db_session.refresh(result.proposal)
    assert result.proposal.status is ProposalStatus.CANCELLED
    assert result.proposal.terminal_reason == "user_cancelled"  # X-05 归因对齐

    # 取消后 approve → 409（不复活）
    with pytest.raises(ProposalNotPendingError):
        await service.approve(result.proposal.id, user_id=user.id)
    # 领域未被写
    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS
    # 重复取消 → 幂等 no-op
    again = await service.cancel(result.proposal.id, user_id=user.id)
    assert again.applied is False


async def test_reject_distinct_from_cancel(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)

    service = ActionCommandService(db_session)
    rejected = await service.reject(result.proposal.id, user_id=user.id)
    assert rejected.applied is True
    await db_session.refresh(result.proposal)
    assert result.proposal.status is ProposalStatus.REJECTED
    assert result.proposal.terminal_reason == "user_rejected"
    # 拒绝后取消 → 409（终态封闭）
    with pytest.raises(ProposalNotPendingError):
        await service.cancel(result.proposal.id, user_id=user.id)


# ============================================================================
# 6. receipt 权威性 + diff 可渲染
# ============================================================================


async def test_receipt_authoritative_and_diff_renderable(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)

    proposal = result.proposal
    # diff 结构（UI 确认卡数据面）
    assert set(proposal.diff) == {"before", "after", "changed_fields"}
    assert proposal.diff["before"]["status"] == "IN_PROGRESS"
    assert proposal.diff["after"]["status"] == "COMPLETED"
    assert "status" in proposal.diff["changed_fields"]

    service = ActionCommandService(db_session)
    committed = await service.approve(proposal.id, user_id=user.id)

    receipt = await service.get_receipt(proposal.id, user_id=user.id)
    assert receipt["receipt_id"] == committed.proposal.receipt["receipt_id"]
    assert receipt["status"] == "COMMITTED"
    assert receipt["protocol_version"] == ACTION_COMMAND_PROTOCOL_VERSION
    assert receipt["subject"]["id"] == str(task.id)
    assert receipt["confirmed_by"] == "user"
    assert receipt["committed_at"]
    assert receipt["diff"]["after"]["status"] == "COMPLETED"
    # effects 富化（同 commit 或增量补写）
    assert any(e["kind"] == "task.status_changed" for e in receipt["effects"])
    assert receipt["authorization"]["confirmed_by"] == "user"

    # 重放 receipt 与首次完全一致（权威性）
    again = await service.get_receipt(proposal.id, user_id=user.id)
    assert again == receipt


async def test_receipt_not_available_before_commit(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)
    service = ActionCommandService(db_session)
    with pytest.raises(ProposalNotPendingError):
        await service.get_receipt(result.proposal.id, user_id=user.id)


async def test_cross_user_isolation_404(db_session, outbox_tables):
    user_a = await _make_user(db_session)
    user_b = await _make_user(db_session)
    task = await _make_task(db_session, user_a)
    result = await _propose_complete(db_session, user_a, task)
    service = ActionCommandService(db_session)
    with pytest.raises(ProposalNotFoundError):
        await service.approve(result.proposal.id, user_id=user_b.id)
    with pytest.raises(ProposalNotFoundError):
        await service.get_proposal(result.proposal.id, user_id=user_b.id)


# ============================================================================
# 7. 创建幂等 + 命令预筛
# ============================================================================


async def test_create_idempotent_on_key(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)

    first = await _propose_complete(db_session, user, task, idempotency_key="req-42")
    second = await _propose_complete(db_session, user, task, idempotency_key="req-42")
    assert first.created is True
    assert second.created is False
    assert second.proposal.id == first.proposal.id
    assert await _outbox_count(db_session, "action.proposed") == 1


async def test_illegal_transition_rejected_at_proposal_time(db_session, outbox_tables):
    """确定性预筛：COMPLETED→PENDING 非法迁移在 proposal 创建时即拒（422 语义）."""
    user = await _make_user(db_session)
    task = await _make_task(db_session, user, status=TaskStatus.COMPLETED)
    service = ActionCommandService(db_session)
    from app.core.action_command import CommandValidationError

    with pytest.raises(CommandValidationError) as exc_info:
        await service.create_proposal(
            user_id=user.id,
            command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
            payload={"task_id": str(task.id), "to_status": "PENDING"},
        )
    assert "illegal task status transition" in str(exc_info.value)


async def test_unknown_command_type_rejected(db_session, outbox_tables):
    user = await _make_user(db_session)
    service = ActionCommandService(db_session)
    from app.core.action_command import CommandValidationError

    with pytest.raises(CommandValidationError):
        await service.create_proposal(
            user_id=user.id,
            command_type="galaxy.delete_everything",
            payload={},
        )


async def test_create_batch_flow(db_session, outbox_tables):
    """create 型命令：无 subject/版本面；diff before=None；effects=创建 refs."""
    user = await _make_user(db_session)
    service = ActionCommandService(db_session)
    result = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_CREATE_BATCH.value,
        payload={"tasks": [{"title": "复习错题 A", "estimated_minutes": 20}, {"title": "复习错题 B"}]},
    )
    assert result.proposal.subject_id is None
    assert result.proposal.subject_version_token is None
    assert result.proposal.diff["before"] is None
    assert result.proposal.diff["after"]["count"] == 2

    committed = await service.approve(result.proposal.id, user_id=user.id)
    assert committed.applied is True
    receipt = await service.get_receipt(result.proposal.id, user_id=user.id)
    created_refs = receipt["effects"][0]
    assert created_refs["kind"] == "task.created_batch"
    assert created_refs["count"] == 2

    tasks = list(
        (await db_session.execute(select(Task).where(Task.user_id == user.id).order_by(Task.created_at.asc())))
        .scalars()
        .all()
    )
    assert len(tasks) == 2
    assert {t.title for t in tasks} == {"复习错题 A", "复习错题 B"}


async def test_update_fields_whitelist_enforced(db_session, outbox_tables):
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)
    from app.core.action_command import CommandValidationError

    with pytest.raises(CommandValidationError) as exc_info:
        await service.create_proposal(
            user_id=user.id,
            command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
            payload={"task_id": str(task.id), "fields": {"status": "COMPLETED"}},  # 白名单外
        )
    assert "whitelist" in str(exc_info.value)


# ============================================================================
# 8. 词表冻结（契约变更需 bump）
# ============================================================================


def test_vocabularies_frozen():
    assert {s.value for s in ProposalStatus} == {"PENDING", "COMMITTED", "CANCELLED", "EXPIRED", "REJECTED"}
    assert {t.value for t in ActionCommandType} == {
        "task.update_status",
        "task.update_fields",
        "task.create_batch",
    }
    assert {"committed", "user_cancelled", "user_rejected", "expired"} == TERMINAL_REASON_VOCABULARY
    # 事件词表零新增（D-01 36 名冻结由 contract 测试双保险；此处钉 action.* live）
    assert EVENT_REGISTRY["action.proposed"].status == "live"
    assert EVENT_REGISTRY["action.accepted"].status == "live"
    assert EVENT_REGISTRY["action.rejected"].status == "live"
    assert EVENT_REGISTRY["action.proposed"].producers == ("app/services/action_command_service.py",)


# ============================================================================
# 9. 入口适配层（chat/task/Aurora 同一权威路径的薄参数化）
# ============================================================================


async def test_entry_adapters_share_authority_path(db_session, outbox_tables):
    from app.services.action_command_service import propose_task_status_change

    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await propose_task_status_change(
        db_session, user_id=user.id, task_id=task.id, to_status="COMPLETED", source="chat"
    )
    assert result.proposal.source == "chat"
    assert result.proposal.command_type == "task.update_status"
    service = ActionCommandService(db_session)
    committed = await service.approve(result.proposal.id, user_id=user.id)
    assert committed.applied is True
    await db_session.refresh(task)
    assert task.status is TaskStatus.COMPLETED


# ============================================================================
# 10. REVISION 2 返修（R2 PASS_WITH_CONDITIONS → P2-2 语义导出 / P2-3 服务端
#     真源 / P3-1 auto 直通重试活性 / P3-2 validate_subject 行锁）
# ============================================================================


async def test_per_command_semantics_export(db_session, outbox_tables):
    """R2 P2-2：risk/reversible 由命令域语义导出（FSM 终态目标=不可逆），逐命令断言.

    返修前 update_status 硬编码 ("low", True)——不可逆的完成任务可走 auto 直通，
    「auto 需可逆」条件形同虚设；返修后语义取自 _VALID_TRANSITIONS 单一真源。
    """
    from app.services.action_commands.task_commands import (
        _IRREVERSIBLE_TARGET_STATUSES,
        status_change_semantics,
    )
    from app.services.task_service import _VALID_TRANSITIONS

    # 导出表与 FSM 真源一致：无出边的状态恰为不可逆集合（防漂移）
    assert (
        frozenset(status for status, targets in _VALID_TRANSITIONS.items() if not targets)
        == _IRREVERSIBLE_TARGET_STATUSES
    )
    assert frozenset({TaskStatus.COMPLETED, TaskStatus.ABANDONED}) == _IRREVERSIBLE_TARGET_STATUSES

    # 纯函数逐目标断言（X-01 RiskClass 词表：low/medium）
    assert status_change_semantics(TaskStatus.COMPLETED) == ("medium", False)
    assert status_change_semantics(TaskStatus.ABANDONED) == ("medium", False)
    assert status_change_semantics(TaskStatus.PAUSED) == ("low", True)
    assert status_change_semantics(TaskStatus.IN_PROGRESS) == ("low", True)
    assert status_change_semantics(TaskStatus.STUCK) == ("low", True)

    # 真实 prepare 链路落库行断言（proposal.risk_class / reversible 列）
    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)

    p_terminal = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
        payload={"task_id": str(task.id), "to_status": "COMPLETED"},
    )
    assert (p_terminal.proposal.risk_class, p_terminal.proposal.reversible) == ("medium", "false")

    p_soft = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
        payload={"task_id": str(task.id), "to_status": "PAUSED"},
    )
    assert (p_soft.proposal.risk_class, p_soft.proposal.reversible) == ("low", "true")

    p_fields = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 4}},
    )
    assert (p_fields.proposal.risk_class, p_fields.proposal.reversible) == ("low", "true")

    p_batch = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_CREATE_BATCH.value,
        payload={"tasks": [{"title": "复习错题 C"}]},
    )
    assert (p_batch.proposal.risk_class, p_batch.proposal.reversible) == ("low", "false")


async def test_auto_grant_truth_source_is_user_settings(db_session, outbox_tables):
    """R2 P2-3：user_auto_grant 真源=UserSettings.low_risk_auto_execute（服务端自查）.

    授权值不是任何调用方参数：显式 True 行 → auto；显式 False 行 / 无行 → 保守
    confirmation。create_proposal 签名上已不存在授权入参（结构性防自授）。
    """
    user_true = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user_true, enabled=True)
    user_false = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user_false, enabled=False)
    user_norow = await _make_user(db_session)

    async def _mode_for(user: User) -> str:
        task = await _make_task(db_session, user)
        result = await ActionCommandService(db_session).create_proposal(
            user_id=user.id,
            command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
            payload={"task_id": str(task.id), "fields": {"priority": 2}},
            execute_if_authorized=True,
        )
        return str(result.proposal.authorization["mode"])

    assert await _mode_for(user_true) == "auto"
    assert await _mode_for(user_false) == "confirmation"
    assert await _mode_for(user_norow) == "confirmation"

    # 授权行为必须溯源 settings：签名不接受授权入参（自授在结构上不可能）
    import inspect

    params = inspect.signature(ActionCommandService.create_proposal).parameters
    assert "user_auto_grant" not in params
    assert "requires_human_approval" not in params


def test_requires_human_approval_is_server_derived():
    """R2 P2-3：审批标记服务端推导（X-02 R1：高风险必须人工审批），非调用方输入."""
    from app.services.action_command_service import _requires_human_approval

    class _Prepared:  # PreparedCommand 最小替身（只取 risk_class 面）
        def __init__(self, risk_class):
            self.risk_class = risk_class

    assert _requires_human_approval(_Prepared("high")) is True
    assert _requires_human_approval(_Prepared("critical")) is True
    assert _requires_human_approval(_Prepared("medium")) is False
    assert _requires_human_approval(_Prepared("low")) is False
    assert _requires_human_approval(_Prepared(None)) is False


async def test_auto_direct_pass_retry_resumes_execution(db_session, outbox_tables):
    """R2 P3-1（活性）：auto 直通崩溃后同 key 重试恢复执行意图.

    返修前：幂等早退发生在 execute_if_authorized 检查之前——重试早退返回
    PENDING、永不执行（安全但活性缺陷）。返修后：PENDING + mode=auto + 重试
    携带执行旗标 → 重入 approve 落账；恰一次不变。
    """
    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)

    # 第一次调用在 create-commit 之后、inline approve 之前崩溃
    # （模拟：请求处理进程死亡于 approve 前——proposal 已持久、未执行）
    first = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 7}},
        idempotency_key="retry-after-crash",
    )
    assert first.created is True
    assert first.proposal.status is ProposalStatus.PENDING
    assert first.proposal.authorization["mode"] == "auto"
    await db_session.refresh(task)
    assert task.priority != 7  # 未执行

    # 同 key 重试携带原执行意图 → 恢复执行（不再早退 PENDING 永不执行）
    retry = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 7}},
        idempotency_key="retry-after-crash",
        execute_if_authorized=True,
    )
    assert retry.created is False
    assert retry.proposal.status is ProposalStatus.COMMITTED
    await db_session.refresh(task)
    assert task.priority == 7
    assert len(await _committed_transitions(db_session, retry.proposal.id)) == 1
    assert await _outbox_count(db_session, "action.accepted") == 1

    # 再次重试 → 重放（already_committed 零新写）
    replay = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 7}},
        idempotency_key="retry-after-crash",
        execute_if_authorized=True,
    )
    assert replay.proposal.status is ProposalStatus.COMMITTED
    assert len(await _committed_transitions(db_session, retry.proposal.id)) == 1
    assert await _outbox_count(db_session, "action.accepted") == 1


async def test_auto_retry_without_intent_stays_pending(db_session, outbox_tables):
    """重试不带执行旗标 → 维持早退语义（重放响应，不执行）——意图旗标是恢复的钥匙."""
    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)
    await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 5}},
        idempotency_key="no-intent-retry",
    )
    retry = await service.create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": 5}},
        idempotency_key="no-intent-retry",
    )
    assert retry.created is False
    assert retry.proposal.status is ProposalStatus.PENDING
    await db_session.refresh(task)
    assert task.priority != 5


async def test_validate_subject_locks_task_row_on_postgres(db_session, outbox_tables):
    """R2 P3-2：validate_subject 的 subject SELECT 携带 FOR UPDATE（PG 编译面断言）.

    sqlite 方言静默丢弃 FOR UPDATE（真并发仅在 PG 成立）；本测试在 PG 方言上
    编译捕获语句，钉住行锁不回退。锁序 proposal → task（无反序路径）。
    """
    import unittest.mock as mock

    from sqlalchemy.dialects import postgresql
    from sqlalchemy.sql.selectable import Select

    from app.services.action_commands.task_commands import TaskUpdateStatusCommand

    user = await _make_user(db_session)
    task = await _make_task(db_session, user)
    result = await _propose_complete(db_session, user, task)

    captured: list = []
    real_execute = AsyncSession.execute

    async def spy_execute(self, stmt, *args, **kwargs):
        if isinstance(stmt, Select):
            captured.append(stmt)
        return await real_execute(self, stmt, *args, **kwargs)

    with mock.patch.object(AsyncSession, "execute", spy_execute):
        await TaskUpdateStatusCommand().validate_subject(db_session, proposal=result.proposal)

    task_selects = [s for s in captured if "FROM tasks" in str(s)]
    assert task_selects, "validate_subject must SELECT the task row"
    compiled = str(task_selects[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled, compiled
