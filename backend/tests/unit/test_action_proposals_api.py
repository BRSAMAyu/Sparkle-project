"""X-03 · /action-proposals API 契约测试（receipt 端点 / 错误码映射 / 入口面）.

App kill/reopen 语义（X-05 test_runs_api 同构）：proposal/receipt 状态持久于
DB，新客户端实例按 proposal_id 查询得到同一权威回执，不依赖内存/WS 状态。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api.deps import get_current_active_superuser, get_current_user, get_db
from app.api.v1.action_proposals import router
from app.models.action_proposal import ActionProposal
from app.models.task import TaskStatus
from app.models.user import User
from app.schemas.task import TaskUpdate
from app.services.task_service import TaskService
from tests.unit.test_action_command_service import _OUTBOX_DDL, _make_task, _make_user

app = FastAPI()
app.include_router(router, prefix="/api/v1")


@pytest.fixture(name="outbox_tables")
async def outbox_tables_fixture(db_session):
    for ddl in _OUTBOX_DDL:
        await db_session.execute(text(ddl))
    await db_session.commit()
    yield


@pytest.fixture(name="db_override")
async def db_override_fixture(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(name="client")
async def client_fixture(db_session, db_override):
    yield AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _auth_as(user: User):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_superuser] = lambda: user


def _clear_auth():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_active_superuser, None)


def _forbid_superuser():
    def _raise():
        raise HTTPException(status_code=403, detail="forbidden")

    app.dependency_overrides[get_current_active_superuser] = _raise


@pytest.fixture(autouse=True)
def _reset_auth_after_each_test():
    yield
    _clear_auth()


async def _create_task_and_proposal(client, db_session, user, *, command=None, payload=None):
    task = await _make_task(db_session, user)
    body = {
        "command_type": command or "task.update_status",
        "payload": payload or {"task_id": str(task.id), "to_status": "COMPLETED"},
        "source": "aurora",
    }
    resp = await client.post("/api/v1/action-proposals", json=body)
    assert resp.status_code == 201, resp.text
    return task, resp.json()["proposal"]


# ============================================================================
# 统一入口 → 确认 → 权威回执（全链）
# ============================================================================


async def test_full_lifecycle_create_approve_receipt(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    task, proposal = await _create_task_and_proposal(client, db_session, user)

    assert proposal["status"] == "PENDING"
    assert proposal["source"] == "aurora"
    assert proposal["diff"]["before"]["status"] == "IN_PROGRESS"
    assert proposal["diff"]["after"]["status"] == "COMPLETED"
    assert "status" in proposal["diff"]["changed_fields"]
    assert proposal["expires_at"]  # 过期时刻对 UI 明确

    # 确认（= 用户确认行为 + 版本/权限验证 + commit）
    approve = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/approve", json={})
    assert approve.status_code == 200, approve.text
    body = approve.json()
    assert body["applied"] is True
    assert body["already_committed"] is False
    assert body["proposal"]["status"] == "COMMITTED"
    assert body["proposal"]["receipt"]["receipt_id"]

    # 重复确认：不重复写（重放标志 + 同一 receipt）
    replay = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/approve", json={})
    assert replay.status_code == 200
    replay_body = replay.json()
    assert replay_body["already_committed"] is True
    assert replay_body["applied"] is False
    assert replay_body["proposal"]["receipt"]["receipt_id"] == body["proposal"]["receipt"]["receipt_id"]

    # UI 权威回执端点（App kill/reopen 后按 id 查询）
    receipt = await client.get(f"/api/v1/action-proposals/{proposal['proposal_id']}/receipt")
    assert receipt.status_code == 200
    receipt_body = receipt.json()
    assert receipt_body["receipt_id"] == body["proposal"]["receipt"]["receipt_id"]
    assert receipt_body["command_type"] == "task.update_status"
    assert receipt_body["subject"]["id"] == str(task.id)
    assert receipt_body["authorization"]["confirmed_by"] == "user"

    # 领域效果恰一次
    await db_session.refresh(task)
    assert task.status is TaskStatus.COMPLETED

    # 审计轨迹
    transitions = await client.get(f"/api/v1/action-proposals/{proposal['proposal_id']}/transitions")
    assert transitions.status_code == 200
    items = transitions.json()["items"]
    assert [t["to_status"] for t in items] == ["PENDING", "COMMITTED"]
    assert items[0]["event_name"] == "action.proposed"
    assert items[1]["event_name"] == "action.accepted"


async def test_receipt_endpoint_before_commit_409(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    _, proposal = await _create_task_and_proposal(client, db_session, user)
    resp = await client.get(f"/api/v1/action-proposals/{proposal['proposal_id']}/receipt")
    assert resp.status_code == 409
    assert resp.json()["detail"]["error_code"] == "ACTION_NOT_PENDING"


# ============================================================================
# 版本冲突 → 409 + 明确错误码（不覆盖）
# ============================================================================


async def test_version_conflict_maps_to_409_with_error_code(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    user_id = user.id
    _auth_as(user)
    task, proposal = await _create_task_and_proposal(client, db_session, user)

    # 中间写（权威路径）使 proposal 版本过期
    await TaskService.update(db_session, task, TaskUpdate(priority=7))
    await db_session.refresh(task)

    resp = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/approve", json={})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["error_code"] == "ACTION_VERSION_CONFLICT"
    assert detail["details"]["proposal_version_token"] == proposal["subject_version_token"]
    assert detail["details"]["current_version_token"] != proposal["subject_version_token"]

    # 不覆盖：任务保持中间写状态
    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS
    assert task.priority == 7

    # proposal 仍可查询且为 PENDING
    detail_resp = await client.get(f"/api/v1/action-proposals/{proposal['proposal_id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["proposal"]["status"] == "PENDING"
    _ = user_id


# ============================================================================
# expiry → 410 + 显式 EXPIRED
# ============================================================================


async def test_expired_approve_maps_to_410_and_state_explicit(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    user_id = user.id
    _auth_as(user)
    task, proposal = await _create_task_and_proposal(client, db_session, user)

    row = await db_session.get(ActionProposal, proposal["proposal_id"])
    row.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    await db_session.commit()

    resp = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/approve", json={})
    assert resp.status_code == 410
    assert resp.json()["detail"]["error_code"] == "ACTION_EXPIRED"

    state = await client.get(f"/api/v1/action-proposals/{proposal['proposal_id']}")
    assert state.json()["proposal"]["status"] == "EXPIRED"
    assert state.json()["proposal"]["terminal_reason"] == "expired"

    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS  # 未执行
    _ = user_id


async def test_expiry_sweep_requires_superuser(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    _forbid_superuser()
    resp = await client.post("/api/v1/action-proposals/expire", json={"limit": 10})
    assert resp.status_code == 403


# ============================================================================
# cancel / reject API 面
# ============================================================================


async def test_cancel_then_approve_409(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    user_id = user.id
    _auth_as(user)
    task, proposal = await _create_task_and_proposal(client, db_session, user)

    cancel = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/cancel", json={})
    assert cancel.status_code == 200
    assert cancel.json()["proposal"]["status"] == "CANCELLED"
    assert cancel.json()["proposal"]["terminal_reason"] == "user_cancelled"

    approve = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/approve", json={})
    assert approve.status_code == 409
    assert approve.json()["detail"]["error_code"] == "ACTION_NOT_PENDING"

    # 取消幂等
    cancel_again = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/cancel", json={})
    assert cancel_again.status_code == 200
    assert cancel_again.json()["applied"] is False

    await db_session.refresh(task)
    assert task.status is TaskStatus.IN_PROGRESS  # 取消传播：领域零写入
    _ = user_id


async def test_reject_endpoint(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    _, proposal = await _create_task_and_proposal(client, db_session, user)
    resp = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/reject", json={"reason": "不想要"})
    assert resp.status_code == 200
    assert resp.json()["proposal"]["status"] == "REJECTED"
    assert resp.json()["proposal"]["terminal_reason"] == "user_rejected"


# ============================================================================
# 创建幂等 / 校验 / 隔离
# ============================================================================


async def test_create_idempotent_replay_via_api(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    task = await _make_task(db_session, user)
    body = {
        "command_type": "task.update_status",
        "payload": {"task_id": str(task.id), "to_status": "COMPLETED"},
        "idempotency_key": "mobile-double-tap-1",
    }
    first = await client.post("/api/v1/action-proposals", json=body)
    assert first.status_code == 201
    second = await client.post("/api/v1/action-proposals", json=body)
    assert second.status_code == 201
    assert second.json()["created"] is False
    assert second.json()["proposal"]["proposal_id"] == first.json()["proposal"]["proposal_id"]


async def test_invalid_command_422(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    resp = await client.post(
        "/api/v1/action-proposals",
        json={"command_type": "tasks.explode", "payload": {}},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["error_code"] == "ACTION_INVALID_COMMAND"


async def test_cross_user_404(client, db_session, outbox_tables):
    user_a = await _make_user(db_session)
    user_b = await _make_user(db_session)
    _auth_as(user_a)
    task = await _make_task(db_session, user_a)
    created = await client.post(
        "/api/v1/action-proposals",
        json={"command_type": "task.update_status", "payload": {"task_id": str(task.id), "to_status": "COMPLETED"}},
    )
    proposal_id = created.json()["proposal"]["proposal_id"]

    _auth_as(user_b)
    for method, path in (
        ("get", f"/api/v1/action-proposals/{proposal_id}"),
        ("get", f"/api/v1/action-proposals/{proposal_id}/receipt"),
        ("post", f"/api/v1/action-proposals/{proposal_id}/approve"),
        ("post", f"/api/v1/action-proposals/{proposal_id}/cancel"),
    ):
        if method == "post":
            resp = await client.post(path, json={})
        else:
            resp = await client.get(path)
        assert resp.status_code == 404, (method, resp.status_code)


async def test_list_proposals_inbox(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    _, p1 = await _create_task_and_proposal(client, db_session, user)
    resp = await client.get("/api/v1/action-proposals", params={"status": "PENDING"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert any(item["proposal_id"] == p1["proposal_id"] for item in body["items"])
    # 过期标志即时计算（读不写库）
    assert body["items"][0]["expired"] is False


# ============================================================================
# auto 直通路径（低风险已授权；ACTION §3）——授权真源=服务端 settings（R2 P2-3）
# ============================================================================


async def test_auto_grant_executes_inline_via_api(client, db_session, outbox_tables):
    """低风险+可逆+服务端已授权（settings 行）+ 请求直通 → 创建即落账."""
    from tests.unit.test_action_command_service import _grant_low_risk_auto

    user = await _make_user(db_session)
    await _grant_low_risk_auto(db_session, user)
    _auth_as(user)
    task = await _make_task(db_session, user)
    resp = await client.post(
        "/api/v1/action-proposals",
        json={
            "command_type": "task.update_fields",
            "payload": {"task_id": str(task.id), "fields": {"priority": 3}},
            "execute_if_authorized": True,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["proposal"]["status"] == "COMMITTED"
    assert body["proposal"]["authorization"]["mode"] == "auto"
    assert body["proposal"]["receipt"] is not None
    await db_session.refresh(task)
    assert task.priority == 3


async def test_execute_flag_without_grant_stays_pending(client, db_session, outbox_tables):
    """无授权（无 settings 行）时执行旗标无效 → PENDING 等确认，领域零写."""
    user = await _make_user(db_session)
    _auth_as(user)
    task = await _make_task(db_session, user)
    resp = await client.post(
        "/api/v1/action-proposals",
        json={
            "command_type": "task.update_fields",
            "payload": {"task_id": str(task.id), "fields": {"priority": 3}},
            "execute_if_authorized": True,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["proposal"]["status"] == "PENDING"  # 未授权不执行
    await db_session.refresh(task)
    assert task.priority == 1 or task.priority == 0  # 未写（默认值未动）


async def test_client_self_grant_rejected_422(client, db_session, outbox_tables):
    """R2 P2-3：客户端自授 user_auto_grant → 422 显式拒收（信任边界）.

    变异必红锚点：若服务端重新接受客户端授权值（自授→auto 直通），本测试
    与 test_auto_grant_truth_source_is_user_settings 共同失效。
    """
    user = await _make_user(db_session)
    _auth_as(user)
    task = await _make_task(db_session, user)
    resp = await client.post(
        "/api/v1/action-proposals",
        json={
            "command_type": "task.update_fields",
            "payload": {"task_id": str(task.id), "fields": {"priority": 3}},
            "user_auto_grant": True,  # 自授
            "execute_if_authorized": True,
        },
    )
    assert resp.status_code == 422
    assert "user_auto_grant" in resp.text
    # 领域零写：任务未被触碰，也没有 proposal 行落账
    await db_session.refresh(task)
    assert task.priority != 3
    rows = await db_session.execute(text("SELECT COUNT(*) FROM action_proposals"))
    assert int(rows.scalar_one()) == 0


async def test_client_approval_flag_rejected_422(client, db_session, outbox_tables):
    """R2 P2-3：客户端携带 requires_human_approval → 422（审批标记只认服务端推导）."""
    user = await _make_user(db_session)
    _auth_as(user)
    task = await _make_task(db_session, user)
    resp = await client.post(
        "/api/v1/action-proposals",
        json={
            "command_type": "task.update_status",
            "payload": {"task_id": str(task.id), "to_status": "COMPLETED"},
            "requires_human_approval": False,
        },
    )
    assert resp.status_code == 422
    assert "requires_human_approval" in resp.text


# ============================================================================
# kill/reopen 权威性（新客户端实例 = 新 App 进程）
# ============================================================================


async def test_receipt_survives_client_restart(client, db_session, outbox_tables):
    user = await _make_user(db_session)
    _auth_as(user)
    task, proposal = await _create_task_and_proposal(client, db_session, user)
    approve = await client.post(f"/api/v1/action-proposals/{proposal['proposal_id']}/approve", json={})
    original_receipt = approve.json()["proposal"]["receipt"]

    # 模拟 App 重启：清空依赖覆盖后重装（同一持久 DB）
    app.dependency_overrides.pop(get_db, None)

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    fresh = await client.get(f"/api/v1/action-proposals/{proposal['proposal_id']}/receipt")
    assert fresh.status_code == 200
    assert fresh.json() == original_receipt
