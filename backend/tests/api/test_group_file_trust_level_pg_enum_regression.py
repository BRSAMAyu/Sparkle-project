"""V3-FIX-149 回归：GroupFileTrustLevel ORM 枚举映射必须对齐 DB 小写枚举值。

病史（wt452 真栈发现，登记于 v3 DYNAMIC_ISSUES #149）：
``app/models/group_files.py`` 的 ``trust_level`` 列声明 ``Enum(GroupFileTrustLevel)``
无 ``values_callable`` → SQLAlchemy 按枚举**名**（OFFICIAL/VERIFIED/MEMBER）读写；
而 gkb001 迁移（及全量基线后 ``ALTER``/``CREATE TYPE``）建的 PG 枚举
``groupfiletrustlevel`` 为小写**值** {official, verified, member}，列默认 'member'。
后果（真栈 500，全簇不可用）：

- 写路径 share：flush 报 ``InvalidTextRepresentationError: invalid input value
  for enum groupfiletrustlevel: "MEMBER"`` → HTTP 500；
- 读路径 list / copy-to-library：任何含默认 'member' 的行 ORM 读取即
  ``LookupError: 'member' is not among the defined enum values`` → HTTP 500。

为什么需要真 PostgreSQL：sqlite 内存库没有 PG 枚举校验，且既有单测 fixture 走
``Base.metadata.create_all``（按 ORM 映射建表，"建出来的库"与 ORM 永远自洽）——
两道屏障都复现不了名值错位。本文件只在**真实迁移产物 schema** 上运行：

- 显式 ``DATABASE_URL`` 指向 postgres 且非演示库（TEST-DBGUARD 判定），否则整文件
  skip（与 tests/test_migrations.py 同形制的真库门）；
- 表结构来自 alembic 迁移链产物（本机对齐仓内形制：
  ``alembic upgrade head`` 于专用测试库 sparkle_test_fix149），非 create_all。

修法（一行，零迁移）：``Enum(GroupFileTrustLevel, values_callable=lambda obj:
[e.value for e in obj])``——只改 ORM 枚举映射方向，Python 侧枚举名语义不变。
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
import sqlalchemy as sa
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.file_storage import StoredFile
from app.models.user import User
from app.services.group_file_service import GroupFileService
from tests import _dbguard

# ---------------------------------------------------------------------------
# 真库门：仅 postgres 非演示库运行（同 tests/test_migrations.py 形制）
# ---------------------------------------------------------------------------


def _require_real_pg_database_url() -> str:
    database_url = getattr(settings, "DATABASE_URL", "") or ""
    if not database_url.startswith(("postgresql", "postgres")):
        pytest.skip(
            "V3-FIX-149 回归需要真实 PostgreSQL（显式 DATABASE_URL 指向 *_test 库），"
            f"当前 {database_url!r}（sqlite 内存库无 PG 枚举校验，复现不了名值错位）"
        )
    if _dbguard.is_demo_db_url(database_url):
        pytest.skip(
            "TEST-DBGUARD: 拒绝在演示库(sparkle)上运行 "
            + _dbguard.demo_guard_message(database_url, "trust_level_pg_enum_regression")
        )
    return database_url


@pytest_asyncio.fixture
async def pg_session():
    """真实迁移产物库上的 async session；行级清理用 raw SQL（修前 ORM 读会炸）。"""
    database_url = _require_real_pg_database_url()
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
    except Exception as exc:
        await engine.dispose()
        pytest.skip(f"V3-FIX-149 回归需要可达的真 PostgreSQL：{exc}")

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def pg_family(pg_session):
    """owner + member + 群 + 成员资格 + 群可见 stored_file；raw SQL 清理（反序）。"""
    suffix = uuid4().hex[:8]
    owner = User(
        username=f"fix149_owner_{suffix}",
        email=f"fix149_owner_{suffix}@example.com",
        hashed_password="hashed",
        nickname="fix149-owner",
        registration_source="email",
        is_active=True,
    )
    member = User(
        username=f"fix149_member_{suffix}",
        email=f"fix149_member_{suffix}@example.com",
        hashed_password="hashed",
        nickname="fix149-member",
        registration_source="email",
        is_active=True,
    )
    pg_session.add_all([owner, member])
    await pg_session.flush()
    group = Group(name=f"fix149-group-{suffix}", type=GroupType.SQUAD, max_members=10)
    pg_session.add(group)
    await pg_session.flush()
    pg_session.add_all(
        [
            GroupMember(group_id=group.id, user_id=owner.id, role=GroupRole.OWNER),
            GroupMember(group_id=group.id, user_id=member.id, role=GroupRole.MEMBER),
        ]
    )
    source_file = StoredFile(
        user_id=owner.id,
        file_name=f"fix149-{suffix}.pdf",
        mime_type="application/pdf",
        file_size=4096,
        bucket="test",
        object_key=f"fix149-{uuid4()}",
        status="processed",
        visibility="group",
        retention_policy="standard",
    )
    pg_session.add(source_file)
    await pg_session.flush()

    tracked = {
        "user_ids": [owner.id, member.id],
        "group_ids": [group.id],
        "stored_file_ids": [source_file.id],
    }
    yield {"owner": owner, "member": member, "group": group, "source_file": source_file}

    # 反序 raw SQL 清理：group_files/group_members 随群级联；stored_files 与 users 手工删。
    # 不走 ORM——修前状态 ORM 读取 trust_level 即 LookupError，teardown 不能被它二次污染。
    await pg_session.rollback()
    for gid in tracked["group_ids"]:
        await pg_session.execute(sa.text("DELETE FROM group_files WHERE group_id = :gid"), {"gid": gid})
        await pg_session.execute(sa.text("DELETE FROM group_members WHERE group_id = :gid"), {"gid": gid})
        await pg_session.execute(sa.text("DELETE FROM groups WHERE id = :gid"), {"gid": gid})
    for fid in tracked["stored_file_ids"]:
        await pg_session.execute(sa.text("DELETE FROM stored_files WHERE id = :fid"), {"fid": fid})
        await pg_session.execute(sa.text("DELETE FROM stored_files WHERE source_file_id = :fid"), {"fid": fid})
    for uid in tracked["user_ids"]:
        await pg_session.execute(sa.text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
    await pg_session.commit()


def _seed_group_file_row_raw(
    *,
    group_id,
    file_id,
    shared_by_id,
):
    """绕开 ORM 直插一条 trust_level 落 DB 默认 'member' 的群文件行。

    gkb001 给 trust_level 设了 server_default 'member'——线上既有数据正是这个形态；
    显式不带 trust_level 列，让默认值生效（修前 ORM 读它 = LookupError 500）。
    """
    return (
        "INSERT INTO group_files "
        "(group_id, file_id, shared_by_id, tags, view_role, download_role, manage_role, id, created_at, updated_at) "
        "VALUES (:gid, :fid, :sid, '[]'::json, 'MEMBER', 'MEMBER', 'ADMIN', :pk, now(), now())"
    ), {"gid": group_id, "fid": file_id, "sid": shared_by_id, "pk": uuid4()}


@pytest_asyncio.fixture
async def community_client(pg_session, monkeypatch):
    """挂 community 路由的最小 ASGI app（真路由→真服务→真 ORM→真 PG）。

    只 stub 非本缺陷的边界：MinIO 复制/presign、Celery 投递、WS 广播、推送。
    枚举读写路径（本缺陷主场）全部走真。
    """
    from app.api.deps import get_current_user, get_current_user_id, get_db
    from app.api.v1.community import router as community_router

    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    state = {"current_user": None}

    async def _override_get_db():
        yield pg_session

    def _override_get_current_user():
        return state["current_user"]

    def _override_get_current_user_id():
        return str(state["current_user"].id)

    async def _fake_enqueue_processing(db, *, stored_file, effective_user_id):
        del db, stored_file, effective_user_id
        return f"job-{uuid4()}"

    monkeypatch.setattr(GroupFileService, "_enqueue_processing", _fake_enqueue_processing)
    monkeypatch.setattr(
        "app.services.group_file_service.document_upload_storage.copy_object",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.group_file_service.event_bus.publish",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "app.api.v1.community.manager.broadcast",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.api.v1.community.manager.send_personal_message",
        AsyncMock(),
    )
    from app.services.notification_push_service import NotificationPushService

    monkeypatch.setattr(NotificationPushService, "create_and_push", AsyncMock(return_value=None))

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_current_user_id] = _override_get_current_user_id

    # raise_app_exceptions=False：未捕获异常按真栈语义呈现为 HTTP 500（修前红 = 500）
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        yield client, state

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_share_group_file_200_and_persists_db_enum_label(
    community_client,
    pg_family,
    pg_session,
):
    """写路径（share）：trust_level 落库必须是 DB 枚举小写 label（默认 member）。

    修前：flush 报 InvalidTextRepresentationError "MEMBER" → HTTP 500。
    """
    client, state = community_client
    owner, group, source_file = pg_family["owner"], pg_family["group"], pg_family["source_file"]
    state["current_user"] = owner

    response = await client.post(
        f"/community/groups/{group.id}/files/{source_file.id}/share",
        json={"send_message": False, "category": "notes"},
    )
    assert response.status_code == 200, f"share 应 200（修前 500）：{response.text}"

    row = await pg_session.execute(
        sa.text("SELECT trust_level::text FROM group_files WHERE group_id = :gid"),
        {"gid": group.id},
    )
    label = row.scalar_one()
    assert label == "member", f"DB 枚举 label 应为小写 member（gkb001 契约），实际 {label!r}"


@pytest.mark.asyncio
async def test_list_group_files_200_reads_server_default_member_row(
    community_client,
    pg_family,
    pg_session,
):
    """读路径（list）：DB 默认 'member' 行经 ORM 读取必须 200 且还原 MEMBER。

    修前：任何含默认 'member' 的行 ORM 读取即 LookupError → HTTP 500。
    """
    client, state = community_client
    owner, group, source_file = pg_family["owner"], pg_family["group"], pg_family["source_file"]
    state["current_user"] = owner

    stmt, params = _seed_group_file_row_raw(
        group_id=group.id,
        file_id=source_file.id,
        shared_by_id=owner.id,
    )
    await pg_session.execute(sa.text(stmt), params)
    await pg_session.commit()

    response = await client.get(
        f"/community/groups/{group.id}/files",
        params={"page": 1, "page_size": 20},
    )
    assert response.status_code == 200, f"list 应 200（修前 500）：{response.text}"
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["trust_level"] == "member"
    assert payload[0]["file_id"] == str(source_file.id)


@pytest.mark.asyncio
async def test_copy_to_library_200_from_server_default_member_row(
    community_client,
    pg_family,
    pg_session,
):
    """读路径（copy-to-library）：member 默认行复制到个人库必须 200。

    修前：_get_group_file 读取 trust_level='member' 行即 LookupError → HTTP 500。
    """
    client, state = community_client
    member, group, source_file = pg_family["member"], pg_family["group"], pg_family["source_file"]
    state["current_user"] = member

    stmt, params = _seed_group_file_row_raw(
        group_id=group.id,
        file_id=source_file.id,
        shared_by_id=pg_family["owner"].id,
    )
    await pg_session.execute(sa.text(stmt), params)
    await pg_session.commit()

    response = await client.post(
        f"/community/groups/{group.id}/files/{source_file.id}/copy-to-library",
    )
    assert response.status_code == 200, f"copy-to-library 应 200（修前 500）：{response.text}"
    payload = response.json()
    assert payload["already_in_library"] is False
    assert payload["file_id"]


@pytest.mark.asyncio
async def test_orm_trust_level_roundtrip_matches_migration_enum(
    pg_session,
    pg_family,
):
    """ORM 双向 roundtrip 钉死异常语义（HTTP 层 500 的根因）：

    - 写 MEMBER → 落库小写 'member'（修前 InvalidTextRepresentationError "MEMBER"）；
    - 读 DB 默认 'member' 行 → GroupFileTrustLevel.MEMBER（修前 LookupError
      "'member' is not among the defined enum values"，即 list/copy 500 的直接根因）。
    """
    from app.models.group_files import GroupFile, GroupFileTrustLevel

    owner, group, source_file = pg_family["owner"], pg_family["group"], pg_family["source_file"]

    # --- 写方向 ---
    row = GroupFile(
        group_id=group.id,
        file_id=source_file.id,
        shared_by_id=owner.id,
        tags=[],
        trust_level=GroupFileTrustLevel.MEMBER,
        view_role=GroupRole.MEMBER,
        download_role=GroupRole.MEMBER,
        manage_role=GroupRole.ADMIN,
    )
    pg_session.add(row)
    await pg_session.flush()

    label = (
        await pg_session.execute(sa.text("SELECT trust_level::text FROM group_files WHERE id = :pid"), {"pid": row.id})
    ).scalar_one()
    assert label == "member"

    await pg_session.refresh(row)
    assert row.trust_level is GroupFileTrustLevel.MEMBER

    # --- 读方向：绕开 ORM 直插 server_default 'member' 行，再走 ORM 读取 ---
    # （独立用例 test_orm_reads_server_default_member_row 同向钉死；此处写方向已红即止）
    stmt, params = _seed_group_file_row_raw(
        group_id=group.id,
        file_id=source_file.id,
        shared_by_id=owner.id,
    )
    await pg_session.execute(sa.text("DELETE FROM group_files WHERE id = :pid"), {"pid": row.id})
    await pg_session.execute(sa.text(stmt), params)
    await pg_session.commit()


@pytest.mark.asyncio
async def test_orm_reads_server_default_member_row(
    pg_session,
    pg_family,
):
    """读方向钉死：DB server_default 'member' 行经 ORM 读取必须还原 MEMBER。

    修前即 list/copy 全簇 500 的直接根因：
    ``LookupError: 'member' is not among the defined enum values``。
    """
    from sqlalchemy import select as sa_select

    from app.models.group_files import GroupFile, GroupFileTrustLevel

    owner, group, source_file = pg_family["owner"], pg_family["group"], pg_family["source_file"]
    stmt, params = _seed_group_file_row_raw(
        group_id=group.id,
        file_id=source_file.id,
        shared_by_id=owner.id,
    )
    await pg_session.execute(sa.text(stmt), params)
    await pg_session.commit()

    await pg_session.rollback()
    row_id = (
        await pg_session.execute(sa.text("SELECT id FROM group_files WHERE group_id = :gid"), {"gid": group.id})
    ).scalar_one()
    orm_row = (await pg_session.execute(sa_select(GroupFile).where(GroupFile.id == row_id))).scalar_one()
    assert orm_row.trust_level is GroupFileTrustLevel.MEMBER
