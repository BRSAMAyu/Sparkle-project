"""P-04 · 低风险 Auto-execute 授权模型测试（allowlist + grant/revoke + receipt）.

卡面验收（headless 口径一一对应）：
- **allowlist 内低风险操作经预授权后真实 auto 执行**：断言执行 + receipt 落库；
- **allowlist 外 / 高风险 / 不可逆操作即使有授权也走 proposal**（负向）：
  - 总开关（UserSettings.low_risk_auto_execute）开了但类别未授予 → confirmation；
  - 类别已授予但操作本身 medium/不可逆（终态目标）→ confirmation（授权永不
    压过风险门）；
  - 不可逆类别（task.create_batch）本身不可被授予（授权面入口即拒）；
- **revoke 后同类操作回退 proposal**（时序）：grant → auto 执行；revoke → 新
  操作回 confirmation；revoke 前已创建未执行的 auto proposal 不再被 resume 直通；
- **receipt 含操作内容 / 依据 / 撤销入口**：auto 执行 receipt 携带
  command_type/payload/effects + authorization.reason_codes/grant_basis +
  revoke_entry（category + 撤销端点路径）。

红测先行：本文件在 base f3b8bc56 上全红（ActionPermissionService/reason code/
receipt revoke_entry 均不存在）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.action_command import (
    AUTHORIZATION_REASON_VOCABULARY,
    ActionCommandType,
    ProposalStatus,
)
from app.models.user import User
from app.services.action_authorization import decide_authorization_mode
from app.services.action_command_service import ActionCommandService
from tests.unit.test_action_command_service import (
    _OUTBOX_DDL,
    _grant_low_risk_auto,
    _make_task,
    _make_user,
)

# --- sqlite 测试下的 outbox DDL（X-03/X-05 同法） -----------------------------


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


async def _grant_category(db_session, user: User, category: str) -> None:
    """P-04 授权面写入：UserPreferencesCenter.explicit 命名空间键（函数级 import：
    红测阶段模块不存在，让本文件收集后逐例失败而非 collection error）."""
    from app.services.action_permission_service import ActionPermissionService

    await ActionPermissionService(db_session).grant_category(user.id, category)


async def _grant_master_only(db_session, user: User) -> None:
    """只开总开关（UserSettings.low_risk_auto_execute），不动类别 allowlist——
    本文件的 allowlist 维度用例专用（shared helper 会顺手授予全部 eligible 类别）."""
    from app.models.user_settings import UserSettings

    db_session.add(UserSettings(user_id=user.id, low_risk_auto_execute=True))
    await db_session.commit()


async def _propose_fields(db_session, user: User, task, *, priority: int, **kwargs):
    return await ActionCommandService(db_session).create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task.id), "fields": {"priority": priority}},
        **kwargs,
    )


# ============================================================================
# 1. allowlist 内低风险操作经预授权后真实 auto 执行 + receipt 落库
# ============================================================================


async def test_allowlisted_category_auto_executes_with_receipt(db_session, outbox_tables):
    from app.models.action_proposal import ActionProposal
    from sqlalchemy import select

    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    await _grant_category(db_session, user, "task.update_fields")
    task = await _make_task(db_session, user)

    result = await _propose_fields(db_session, user, task, priority=9, execute_if_authorized=True)
    assert result.proposal.status is ProposalStatus.COMMITTED  # 真实执行
    assert result.proposal.authorization["mode"] == "auto"
    await db_session.refresh(task)
    assert task.priority == 9

    # receipt 落库（DB 真相，非内存回放）
    rows = list(
        (
            await db_session.execute(
                select(ActionProposal).where(
                    ActionProposal.user_id == user.id,
                    ActionProposal.status == ProposalStatus.COMMITTED.value,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].receipt is not None
    assert rows[0].receipt["receipt_id"]


# ============================================================================
# 2. 负向：allowlist 外 / 高风险 / 不可逆——即使有授权也走 proposal
# ============================================================================


async def test_category_outside_allowlist_stays_proposal_despite_master_grant(db_session, outbox_tables):
    """总开关开了、类别未授予 → confirmation（P-04 前该操作可 auto——授权面收窄）."""
    user = await _make_user(db_session)
    await _grant_master_only(db_session, user)
    await _grant_category(db_session, user, "task.update_fields")  # 只授一个类别
    task = await _make_task(db_session, user)

    # 未授予类别（task.update_status 的低风险可逆目标）→ proposal
    result = await ActionCommandService(db_session).create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
        payload={"task_id": str(task.id), "to_status": "PAUSED"},
        execute_if_authorized=True,
    )
    assert result.proposal.status is ProposalStatus.PENDING
    assert result.proposal.authorization["mode"] == "confirmation"
    assert "auto_forbidden_category_not_allowlisted" in result.proposal.authorization["reason_codes"]
    await db_session.refresh(task)
    assert task.status.value != "PAUSED"

    # 类别隔离：已授予类别同用户仍 auto（allowlist 是按类别的预授权面）
    other = await _make_task(db_session, user)
    ok = await _propose_fields(db_session, user, other, priority=4, execute_if_authorized=True)
    assert ok.proposal.status is ProposalStatus.COMMITTED


async def test_high_risk_and_irreversible_stay_proposal_even_when_category_granted(db_session, outbox_tables):
    """授权永不压过风险门：类别已授予，不可逆目标（COMPLETED）仍走 proposal."""
    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    await _grant_category(db_session, user, "task.update_status")
    task = await _make_task(db_session, user)

    result = await ActionCommandService(db_session).create_proposal(
        user_id=user.id,
        command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
        payload={"task_id": str(task.id), "to_status": "COMPLETED"},
        execute_if_authorized=True,
    )
    assert result.proposal.status is ProposalStatus.PENDING
    assert result.proposal.authorization["mode"] == "confirmation"
    assert "auto_forbidden_irreversible" in result.proposal.authorization["reason_codes"]
    assert result.proposal.risk_class == "medium"
    await db_session.refresh(task)
    assert task.status.value != "COMPLETED"


async def test_irreversible_or_unknown_category_not_grantable(db_session):
    """授权面入口即拒：不可逆类别与词表外类别不可被授予（宁可保守）."""
    from app.core.action_command import CommandValidationError
    from app.services.action_permission_service import ActionPermissionService

    user = await _make_user(db_session)
    service = ActionPermissionService(db_session)
    with pytest.raises(CommandValidationError):
        await service.grant_category(user.id, "task.create_batch")  # irreversible-by-definition
    with pytest.raises(CommandValidationError):
        await service.grant_category(user.id, "galaxy.delete_everything")  # 词表外


def test_allowlist_dimension_is_deterministic_reason_code():
    """纯函数层：category_allowed=False 显式压掉 auto（新 reason code 入封闭词表）."""
    assert "auto_forbidden_category_not_allowlisted" in AUTHORIZATION_REASON_VOCABULARY
    denied = decide_authorization_mode(
        risk_class="low", reversible=True, user_auto_grant=True, category_allowed=False
    )
    assert denied.mode == "confirmation"
    assert "auto_forbidden_category_not_allowlisted" in denied.reason_codes


# ============================================================================
# 3. revoke 后同类操作回退 proposal（时序）
# ============================================================================


async def test_revoke_falls_back_to_proposal_timing(db_session, outbox_tables):
    from app.services.action_permission_service import ActionPermissionService

    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    permissions = ActionPermissionService(db_session)
    await permissions.grant_category(user.id, "task.update_fields")
    task = await _make_task(db_session, user)
    service = ActionCommandService(db_session)

    # t1：预授权期内 → auto 真实执行
    first = await _propose_fields(db_session, user, task, priority=3, execute_if_authorized=True)
    assert first.proposal.status is ProposalStatus.COMMITTED
    await db_session.refresh(task)
    assert task.priority == 3

    # t2：revoke → 同类新操作回退 proposal（时序：决策逐次读真源，不缓存授权）
    await permissions.revoke_category(user.id, "task.update_fields")
    second = await _propose_fields(db_session, user, task, priority=4, execute_if_authorized=True)
    assert second.proposal.status is ProposalStatus.PENDING
    assert second.proposal.authorization["mode"] == "confirmation"
    assert "auto_forbidden_category_not_allowlisted" in second.proposal.authorization["reason_codes"]
    await db_session.refresh(task)
    assert task.priority == 3  # 未被执行

    # t3：revoke 前已创建未执行的 auto proposal——resume 直通不再生效（撤销对
    # 未落账操作即时生效，不靠创建时点授权存续）
    await permissions.grant_category(user.id, "task.update_fields")  # 再授予
    task_b = await _make_task(db_session, user)
    pending = await _propose_fields(db_session, user, task_b, priority=5, idempotency_key="pre-revoke")
    assert pending.proposal.authorization["mode"] == "auto"
    assert pending.proposal.status is ProposalStatus.PENDING
    await permissions.revoke_category(user.id, "task.update_fields")

    retry = await _propose_fields(
        db_session, user, task_b, priority=5, idempotency_key="pre-revoke", execute_if_authorized=True
    )
    assert retry.proposal.status is ProposalStatus.PENDING  # 不再 resume 直通
    await db_session.refresh(task_b)
    assert task_b.priority != 5

    # revoke 不夺走用户 confirmation 权：显式确认仍可执行同一 proposal
    approved = await service.approve(retry.proposal.id, user_id=user.id)
    assert approved.applied is True
    await db_session.refresh(task_b)
    assert task_b.priority == 5

    # t4：重新授予 → 同类操作恢复 auto（grant/revoke 可逆、幂等）
    await permissions.grant_category(user.id, "task.update_fields")
    task_c = await _make_task(db_session, user)
    third = await _propose_fields(db_session, user, task_c, priority=6, execute_if_authorized=True)
    assert third.proposal.status is ProposalStatus.COMMITTED


# ============================================================================
# 4. receipt 含操作内容 / 依据 / 撤销入口
# ============================================================================


async def test_auto_receipt_contains_content_basis_and_revoke_entry(db_session, outbox_tables):
    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    await _grant_category(db_session, user, "task.update_fields")
    task = await _make_task(db_session, user)

    result = await _propose_fields(db_session, user, task, priority=8, execute_if_authorized=True)
    assert result.proposal.status is ProposalStatus.COMMITTED
    receipt = result.proposal.receipt

    # 操作内容：命令域 + payload + diff + 实际 effects
    assert receipt["command_type"] == "task.update_fields"
    assert receipt["diff"]["after"]["priority"] == 8
    assert any(e["kind"] == "task.fields_updated" for e in receipt["effects"])

    # 依据：授权 reason codes + 预授权 granted_at（grant_basis）
    assert receipt["authorization"]["mode"] == "auto"
    assert "risk_low_reversible_auto_grant" in receipt["authorization"]["reason_codes"]
    assert receipt["authorization"]["grant_basis"]["category"] == "task.update_fields"
    assert receipt["authorization"]["grant_basis"]["category_granted_at"]
    assert receipt["authorization"]["grant_basis"]["master_grant"] is True

    # 撤销入口：类别 + 撤销端点（用户可从 receipt 一键关掉该类自动执行）
    revoke_entry = receipt["revoke_entry"]
    assert revoke_entry["category"] == "task.update_fields"
    assert "/action-permissions/task.update_fields/revoke" in revoke_entry["path"]

    # 确认路径（非 auto）commit 的 receipt 不携带 auto 语义
    user2 = await _make_user(db_session)
    task2 = await _make_task(db_session, user2)
    manual = await ActionCommandService(db_session).create_proposal(
        user_id=user2.id,
        command_type=ActionCommandType.TASK_UPDATE_FIELDS.value,
        payload={"task_id": str(task2.id), "fields": {"priority": 7}},
    )
    committed = await ActionCommandService(db_session).approve(manual.proposal.id, user_id=user2.id)
    assert committed.applied is True
    manual_receipt = committed.proposal.receipt
    assert manual_receipt["authorization"]["mode"] == "confirmation"
    assert manual_receipt["revoke_entry"] is None


# ============================================================================
# 5. 授权面状态投影 + API
# ============================================================================


async def test_allowlist_state_projection(db_session):
    from app.services.action_permission_service import ActionPermissionService

    user = await _make_user(db_session)
    service = ActionPermissionService(db_session)

    # t0：什么都未授——全词表可见、全部不可 auto
    state = await service.get_allowlist_state(user.id)
    assert state["master_grant"] is False
    categories = {c["category"]: c for c in state["categories"]}
    assert set(categories) == {"task.update_status", "task.update_fields", "task.create_batch"}
    assert categories["task.update_status"]["eligible"] is True
    assert categories["task.update_fields"]["eligible"] is True
    assert categories["task.create_batch"]["eligible"] is False  # 不可逆类别不可授予
    assert categories["task.update_fields"]["allowed"] is False

    # t1：只授类别、总开关未开 → allowed 仍 False（合成真值 = master ∧ category）
    await service.grant_category(user.id, "task.update_fields")
    state = await service.get_allowlist_state(user.id)
    categories = {c["category"]: c for c in state["categories"]}
    assert state["master_grant"] is False
    assert categories["task.update_fields"]["granted_at"]
    assert categories["task.update_fields"]["allowed"] is False

    # t2：开总开关 → 该类别 allowed=True，未授予类别仍 False
    await _grant_master_only(db_session, user)
    state = await service.get_allowlist_state(user.id)
    categories = {c["category"]: c for c in state["categories"]}
    assert state["master_grant"] is True
    assert categories["task.update_fields"]["allowed"] is True
    assert categories["task.update_status"]["allowed"] is False

    # t3：revoke → allowed 回 False，granted_at 审计痕迹保留
    await service.revoke_category(user.id, "task.update_fields")
    state = await service.get_allowlist_state(user.id)
    categories = {c["category"]: c for c in state["categories"]}
    assert categories["task.update_fields"]["allowed"] is False
    assert categories["task.update_fields"]["granted_at"]  # 审计痕迹保留


async def test_action_permission_api_grant_revoke_flow(db_session, outbox_tables):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.api.deps import get_current_user, get_db
    from app.api.v1.action_permissions import router as permissions_router

    app = FastAPI()
    app.include_router(permissions_router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    user = await _make_user(db_session)
    await _grant_master_only(db_session, user)
    app.dependency_overrides[get_current_user] = lambda: user

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    # 未授予：列表可见、不可 auto
    resp = await client.get("/api/v1/action-permissions")
    assert resp.status_code == 200
    state = resp.json()
    assert state["master_grant"] is True
    categories = {c["category"]: c for c in state["categories"]}
    assert categories["task.update_fields"]["allowed"] is False

    # grant → 低风险可逆操作 inline auto（经统一 command path）
    resp = await client.post("/api/v1/action-permissions/task.update_fields/grant")
    assert resp.status_code == 200, resp.text
    assert resp.json()["category"] == "task.update_fields"
    task = await _make_task(db_session, user)
    result = await _propose_fields(db_session, user, task, priority=5, execute_if_authorized=True)
    assert result.proposal.status is ProposalStatus.COMMITTED

    # revoke → 同类操作回退 proposal
    resp = await client.post("/api/v1/action-permissions/task.update_fields/revoke")
    assert resp.status_code == 200
    other = await _make_task(db_session, user)
    fallback = await _propose_fields(db_session, user, other, priority=6, execute_if_authorized=True)
    assert fallback.proposal.status is ProposalStatus.PENDING
    await client.aclose()


async def test_action_permission_api_rejects_unknown_category(db_session):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.api.deps import get_current_user, get_db
    from app.api.v1.action_permissions import router as permissions_router

    app = FastAPI()
    app.include_router(permissions_router, prefix="/api/v1")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    user = await _make_user(db_session)
    app.dependency_overrides[get_current_user] = lambda: user

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    resp = await client.post("/api/v1/action-permissions/no.such.category/grant")
    assert resp.status_code == 422
    resp = await client.post("/api/v1/action-permissions/task.create_batch/grant")
    assert resp.status_code == 422
    await client.aclose()


# ============================================================================
# 6. 红线：授权面服务级守卫（授权读取失败 → 保守按未授予处理）
# ============================================================================


async def test_allowlist_read_failure_fails_closed(db_session):
    """偏好行损坏（explicit 非 mapping 形态）→ fail-closed：按未授予处理，绝不放行 auto.

    场景即「存储层故障绝不放大成 auto」：即便总开关已开（甚至授权记录痕迹存在）、
    allowlist 段不可解析 → 判定一律 (False, None)，操作走 confirmation。
    """
    from app.models.user_preferences import UserPreferencesCenter
    from app.services.action_permission_service import ActionPermissionService

    user = await _make_user(db_session)
    await _grant_master_only(db_session, user)
    db_session.add(UserPreferencesCenter(user_id=user.id, explicit="corrupt-not-a-map"))
    await db_session.commit()

    allowed, granted_at = await ActionPermissionService(db_session).is_category_granted(
        user.id, "task.update_fields"
    )
    assert allowed is False
    assert granted_at is None


_ = uuid4  # 语义占位：保持 import 最小集与 X-03 测试同构
