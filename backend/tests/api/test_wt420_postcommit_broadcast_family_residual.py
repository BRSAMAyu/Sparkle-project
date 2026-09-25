"""V3-FIX-87 · 社区面 post-commit 广播 500 同族残余（share/mute/status 面）best-effort 化.

wt408b（f0a16c0b ⑤）已把消息族五端点（send_message/send_private_message/
mark_group_messages_read/revoke_group_message/forward_message）的提交后
WS 广播/推送 best-effort 化；本卡把同族残余收口：

- share_file_to_user（POST /users/{id}/share-file）
- share_resource（POST /share）
- retract_shared_resource（POST /shared-resources/{id}/retract）
- mute_group_member（POST /groups/{gid}/members/{uid}/mute）
- unmute_group_member（DELETE /groups/{gid}/members/{uid}/mute）
- warn_group_member（POST /groups/{gid}/members/{uid}/warn）
- update_status（PUT /status）

口径与 wt408b 相同：成员行/消息行/资源行/状态行是权威事实（已提交），
提交后的 Redis publish（WS 广播/私信推送/presence 通知）瞬断失败不得把
已成功的结果变成 500——客户端重试会重复分享/禁言/状态写，或根本无法重试
（retract 重试会 404）。失败记日志不回滚语义。

红测（base 上红）：每端点 1 条，WS 推送通道全断 → 端点仍 200。
"""

from __future__ import annotations

import uuid as uuid_mod
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_db
from app.core.websocket import manager as global_ws_manager
from app.models.base import Base
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.file_storage import StoredFile
from app.models.task import Task, TaskType
from app.models.user import User

COMMUNITY_PREFIX = "/api/v1/community"


class _Env:
    def __init__(self, db: AsyncSession, app: FastAPI, current: dict):
        self.db = db
        self.app = app
        self.current = current

    async def client(self) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=self.app, raise_app_exceptions=False), base_url="http://test")


@pytest.fixture(name="family_env")
async def family_env_fixture(monkeypatch: pytest.MonkeyPatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        from app.api.v1.community import router as community_router

        app = FastAPI()
        app.include_router(community_router, prefix=COMMUNITY_PREFIX)

        current: dict = {"user": None}

        async def _override_get_db():
            yield db

        async def _override_get_current_user():
            return current["user"]

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_current_user] = _override_get_current_user

        import app.api.v1.community as community_api

        async def _no_op_streak(_user_id: UUID) -> None:
            return None

        community_api._refresh_streak_signals = _no_op_streak  # type: ignore[method-assign]

        # share-file 面的 MinIO 拷贝与异步加工在单测里替换为无副作用桩
        # （与 tests/api/test_community_group_file_sharing_api.py 先例同口径）。
        from app.services.group_file_service import GroupFileService

        monkeypatch.setattr(
            "app.services.group_file_service.document_upload_storage.copy_object",
            lambda **kwargs: None,
        )

        async def _fake_enqueue_processing(db, *, stored_file, effective_user_id):
            del db, stored_file, effective_user_id
            return f"job-{uuid4()}"

        monkeypatch.setattr(GroupFileService, "_enqueue_processing", _fake_enqueue_processing)

        yield _Env(db, app, current)

        app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture(name="failing_ws_manager")
def failing_ws_manager_fixture(monkeypatch: pytest.MonkeyPatch):
    """WS 推送通道全断（Redis 瞬断等价面）：广播/私信推送/presence 一律抛 ConnectionError。"""
    mgr = global_ws_manager
    mgr.redis = None
    mgr.pubsub = None
    mgr.active_connections.clear()
    mgr.user_connections.clear()

    def _boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise ConnectionError("simulated redis outage (V3-FIX-87 post-commit family residual)")

    monkeypatch.setattr(mgr, "broadcast", _boom)
    monkeypatch.setattr(mgr, "send_personal_message", _boom)
    monkeypatch.setattr(mgr, "notify_status_change", _boom)
    yield mgr
    mgr.active_connections.clear()
    mgr.user_connections.clear()
    mgr.redis = None
    mgr.pubsub = None


async def _make_user(db: AsyncSession, prefix: str) -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{prefix}_{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.commit()
    return user


async def _make_group_with_member(db: AsyncSession, owner: User, member: User | None = None) -> Group:
    group = Group(
        name=f"grp_{uuid_mod.uuid4().hex[:8]}",
        type=GroupType.SQUAD,
        focus_tags=[],
    )
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER))
    if member is not None:
        db.add(GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER))
    await db.commit()
    return group


# --- 红测 1：share_file_to_user 推送失败 → 仍 200 --------------------------------


@pytest.mark.asyncio
async def test_share_file_to_user_survives_push_failure(family_env: _Env, failing_ws_manager) -> None:
    owner = await _make_user(family_env.db, "sfowner")
    target = await _make_user(family_env.db, "sftarget")
    stored = StoredFile(
        user_id=owner.id,
        file_name="notes.pdf",
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"owner-{uuid4()}",
        status="uploaded",
        visibility="private",
        retention_policy="keep",
    )
    family_env.db.add(stored)
    await family_env.db.commit()

    family_env.current["user"] = owner
    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/users/{target.id}/share-file",
            json={"file_id": str(stored.id)},
        )

    assert (
        resp.status_code == 200
    ), f"文件拷贝已提交，推送失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("file_id"), f"拷贝结果必须返回，实际 keys: {list(body)}"


# --- 红测 2：share_resource 广播失败 → 仍 200 ------------------------------------


@pytest.mark.asyncio
async def test_share_resource_survives_broadcast_failure(family_env: _Env, failing_ws_manager) -> None:
    owner = await _make_user(family_env.db, "srowner")
    group = await _make_group_with_member(family_env.db, owner)
    task = Task(user_id=owner.id, title="待分享任务", type=TaskType.LEARNING, estimated_minutes=30)
    family_env.db.add(task)
    await family_env.db.commit()

    family_env.current["user"] = owner
    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task.id),
                "target_group_id": str(group.id),
                "permission": "view",
            },
        )

    assert (
        resp.status_code == 200
    ), f"共享资源行已提交，广播失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("id"), f"共享资源本体必须返回，实际 keys: {list(body)}"


# --- 红测 3：retract_shared_resource 广播失败 → 仍 200 ---------------------------


@pytest.mark.asyncio
async def test_retract_shared_resource_survives_broadcast_failure(family_env: _Env, failing_ws_manager) -> None:
    from app.models.community import SharedResource

    owner = await _make_user(family_env.db, "rtowner")
    target = await _make_user(family_env.db, "rttarget")
    task = Task(user_id=owner.id, title="待撤回任务", type=TaskType.LEARNING, estimated_minutes=15)
    family_env.db.add(task)
    await family_env.db.flush()
    shared = SharedResource(shared_by=owner.id, target_user_id=target.id, task_id=task.id, permission="view")
    family_env.db.add(shared)
    await family_env.db.commit()

    family_env.current["user"] = owner
    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared.id}/retract",
        )

    assert (
        resp.status_code == 200
    ), f"撤回已提交（重试已不可能：重试即 404），广播失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("success") is True, f"撤回结果必须返回，实际 keys: {list(body)}"


# --- 红测 4：mute_group_member 推送失败 → 仍 200 ----------------------------------


@pytest.mark.asyncio
async def test_mute_group_member_survives_push_failure(family_env: _Env, failing_ws_manager) -> None:
    owner = await _make_user(family_env.db, "mtowner")
    member = await _make_user(family_env.db, "mtmember")
    group = await _make_group_with_member(family_env.db, owner, member)

    family_env.current["user"] = owner
    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/members/{member.id}/mute",
            json={"user_id": str(member.id), "duration_minutes": 30, "reason": "红测禁言"},
        )

    assert (
        resp.status_code == 200
    ), f"禁言成员行已提交，通知失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("success") is True, f"禁言结果必须返回，实际 keys: {list(body)}"


# --- 红测 5a：unmute_group_member 推送失败 → 仍 200 -------------------------------


@pytest.mark.asyncio
async def test_unmute_group_member_survives_push_failure(family_env: _Env, failing_ws_manager) -> None:
    owner = await _make_user(family_env.db, "umowner")
    member = await _make_user(family_env.db, "ummember")
    group = await _make_group_with_member(family_env.db, owner, member)

    family_env.current["user"] = owner
    async with await family_env.client() as client:
        resp = await client.delete(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/members/{member.id}/mute",
        )

    assert (
        resp.status_code == 200
    ), f"解除禁言成员行已提交，通知失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    assert resp.json().get("success") is True


# --- 红测 5b：warn_group_member 推送失败 → 仍 200 ---------------------------------


@pytest.mark.asyncio
async def test_warn_group_member_survives_push_failure(family_env: _Env, failing_ws_manager) -> None:
    owner = await _make_user(family_env.db, "wnowner")
    member = await _make_user(family_env.db, "wnmember")
    group = await _make_group_with_member(family_env.db, owner, member)

    family_env.current["user"] = owner
    async with await family_env.client() as client:
        resp = await client.post(
            f"{COMMUNITY_PREFIX}/groups/{group.id}/members/{member.id}/warn",
            json={"user_id": str(member.id), "reason": "红测警告"},
        )

    assert (
        resp.status_code == 200
    ), f"警告计数行已提交，通知失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    assert resp.json().get("success") is True


# --- 红测 6：update_status presence 通知失败 → 仍 200 -----------------------------


@pytest.mark.asyncio
async def test_update_status_survives_notify_failure(family_env: _Env, failing_ws_manager) -> None:
    user = await _make_user(family_env.db, "stuser")
    family_env.current["user"] = user

    async with await family_env.client() as client:
        resp = await client.put(
            f"{COMMUNITY_PREFIX}/status",
            json={"status": "online"},
        )

    assert (
        resp.status_code == 200
    ), f"状态行已提交，presence 通知失败必须 best-effort（base 500：红），实际 {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("success") is True, f"状态结果必须返回，实际 keys: {list(body)}"
