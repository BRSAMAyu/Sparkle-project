"""SQUAD-REJOIN · 小队/群组退队-重加入债务收口 —— 软删残留占死全列唯一键.

债务真实形状（代码证据，见 v3-output/SQUAD-REJOIN/REPORT.md）：

- ``GroupService.leave_group`` / ``kick_member`` / ``dissolve_group`` 都是**软删**
  （``deleted_at``），成员行与 flame_contribution/tasks_completed/checkin_streak
  并不会丢——「退队=硬删白板」是卡面误判；
- 真正的债：``uq_group_member(group_id, user_id)`` 是**全列唯一约束**，软删行
  依然占着键位。退队/被踢后重加入时 ``join_group`` 的活跃门
  （``not_deleted_filter``）放行 → INSERT 撞全列唯一键 → IntegrityError 被
  误报为 ``ValueError("已是群组成员")``（HTTP 400）——**退出即永久无法回归**。

本卡收口（照 INTAKE-IDX 模型先例 + PHOTON-IDEM 迁移先例）：

- 模型/迁移：全列唯一约束 → 活跃行部分唯一索引
  ``uq_group_member_active(group_id, user_id) WHERE deleted_at IS NULL``
  （谓词与全仓 ``not_deleted_filter()`` 读口径严格同域）；
- 写侧：``join_group`` 先查任意状态成员行——活跃 → 拒（既有语义）；软删 →
  **复活原行**（清 deleted_at，继承本人累计统计；角色复位 MEMBER）。
  反刷分裁决：重加入不得清零连胜重刷、行键=user_id 不涉他人数据。

绿证钉四条面：退队后可重加入且继承本人统计；重加入连胜按日历诚实衰减；
并发首join/并发重入恰一行活跃；被踢管理员不带权回归。
"""

from __future__ import annotations

import asyncio
import sys
import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models.base import Base
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.user import User
from app.services.community_service import GroupService

# ---------------------------------------------------------------------------
# 串行面工具（conftest 的 sqlite in-memory db_session，模型元数据建库）
# ---------------------------------------------------------------------------


async def _make_user(db, prefix: str = "rejoin") -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_group(db, owner: User, *, max_members: int = 8, type_=GroupType.SQUAD) -> Group:
    group = Group(
        name=f"grp-{uuid_mod.uuid4().hex[:8]}",
        type=type_,
        focus_tags=[],
        max_members=max_members,
        is_public=True,
        join_requires_approval=False,
    )
    db.add(group)
    await db.flush()
    db.add(
        GroupMember(
            group_id=group.id,
            user_id=owner.id,
            role=GroupRole.OWNER,
            joined_at=datetime.now(UTC).replace(tzinfo=None),
            last_active_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )
    await db.flush()
    return group


async def _active_member(db, group_id, user_id) -> GroupMember | None:
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


# ===========================================================================
# 1. 退队 → 重加入（修复前红：ValueError("已是群组成员")——退出即永久锁死）
# ===========================================================================


@pytest.mark.asyncio
async def test_leave_then_rejoin_succeeds_and_inherits_own_stats(db_session):
    owner = await _make_user(db_session, "owner")
    member_user = await _make_user(db_session, "member")
    group = await _make_group(db_session, owner)

    joined = await GroupService.join_group(db_session, group.id, member_user.id)
    # 本人累计统计（真实语义列；来源打卡/群任务，直接置值即可钉「行继承」）
    joined.flame_contribution = 42
    joined.checkin_streak = 5
    joined.tasks_completed = 3
    await db_session.flush()

    assert await GroupService.leave_group(db_session, group.id, member_user.id) is True

    # 债务形状证据：leave 是软删，行还在、统计还在——只是键被占死
    leftover = await _active_member(db_session, group.id, member_user.id)
    assert leftover is not None and leftover.deleted_at is not None
    assert leftover.flame_contribution == 42

    rejoined = await GroupService.join_group(db_session, group.id, member_user.id)
    assert rejoined.deleted_at is None, "重加入必须复活为活跃成员"
    assert rejoined.id == joined.id, "复活原行：不是新建白板行"
    assert rejoined.flame_contribution == 42, "本人历史贡献必须继承（不得清零重刷）"
    assert rejoined.checkin_streak == 5
    assert rejoined.tasks_completed == 3
    assert rejoined.role == GroupRole.MEMBER, "重加入不得带原角色特权回归"

    members = await GroupService.get_group_members(db_session, group.id, owner.id)
    assert {m.user_id for m in members} == {owner.id, member_user.id}


@pytest.mark.asyncio
async def test_kick_then_rejoin_resets_role_to_member(db_session):
    owner = await _make_user(db_session, "owner")
    admin_user = await _make_user(db_session, "admin")
    group = await _make_group(db_session, owner)

    await GroupService.join_group(db_session, group.id, admin_user.id)
    await GroupService.promote_member(db_session, group.id, owner.id, admin_user.id)
    assert await GroupService.kick_member(db_session, group.id, owner.id, admin_user.id) is True

    rejoined = await GroupService.join_group(db_session, group.id, admin_user.id)
    assert rejoined.deleted_at is None
    assert rejoined.role == GroupRole.MEMBER, "被踢管理员重加入必须复位 MEMBER"


@pytest.mark.asyncio
async def test_double_join_still_rejected(db_session):
    owner = await _make_user(db_session, "owner")
    member_user = await _make_user(db_session, "member")
    group = await _make_group(db_session, owner)
    await GroupService.join_group(db_session, group.id, member_user.id)
    with pytest.raises(ValueError, match="已是群组成员"):
        await GroupService.join_group(db_session, group.id, member_user.id)


@pytest.mark.asyncio
async def test_rejoin_respects_capacity(db_session):
    owner = await _make_user(db_session, "owner")
    member_user = await _make_user(db_session, "member")
    group = await _make_group(db_session, owner, max_members=2)  # owner+1 满员
    await GroupService.join_group(db_session, group.id, member_user.id)
    await GroupService.leave_group(db_session, group.id, member_user.id)

    outsider = await _make_user(db_session, "outsider")
    await GroupService.join_group(db_session, group.id, outsider.id)  # 补位占满
    with pytest.raises(ValueError, match="群组已满"):
        await GroupService.join_group(db_session, group.id, member_user.id)


@pytest.mark.asyncio
async def test_rejoined_member_streak_follows_calendar(db_session):
    """重加入不清零连胜，但连胜只按日历延续：断签者下一次打卡如实归 1。"""
    from datetime import datetime as _dt

    owner = await _make_user(db_session, "owner")
    member_user = await _make_user(db_session, "member")
    group = await _make_group(db_session, owner)
    joined = await GroupService.join_group(db_session, group.id, member_user.id)
    joined.checkin_streak = 9
    joined.last_checkin_date = _dt.now(UTC).replace(tzinfo=None) - timedelta(days=3)
    await db_session.flush()

    await GroupService.leave_group(db_session, group.id, member_user.id)
    rejoined = await GroupService.join_group(db_session, group.id, member_user.id)
    assert rejoined.checkin_streak == 9

    from app.schemas.community import CheckinRequest
    from app.services.community_service import CheckinService

    outcome = await CheckinService.checkin(
        db_session,
        member_user.id,
        CheckinRequest(group_id=group.id, today_duration_minutes=30),
    )
    assert outcome["new_streak"] == 1, "断签 3 天后连胜必须按日历归 1（复活不清零≠连胜造假）"


# ===========================================================================
# 2. 并发面（sqlite 文件库多连接 + Barrier，PHOTON-IDEM harness 同款）
# ---------------------------------------------------------------------------

# 并发台需真实唯一索引仲裁：模型元数据声明 uq_group_member_active
# （postgresql_where/sqlite_where 双 where），create_all 即带索引。
RIG_DDL_CHECK = "SELECT name FROM sqlite_master WHERE type='index' AND name='uq_group_member_active'"


class _Rig:
    def __init__(self, engine):
        self.engine = engine

    def session_factory(self):
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

        return async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def rig(tmp_path):
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'squad_rejoin.db'}",
        connect_args={"timeout": 15.0},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield _Rig(engine)
    await engine.dispose()


def _install_gate_barrier(barrier: asyncio.Barrier):
    """门屏障上下文：patch 期间每个 session 的首次成员门查询后等齐（单人一次、
    全员到齐），把「彼此都还没写入」的毫秒窗口放大成确定性交错点。
    PHOTON-IDEM 同款思路；patch 必须走 __dict__ 描述子保真存取——
    ``mock.patch.object`` 对 staticmethod 退出恢复时会以普通函数写回类属性，
    破坏 staticmethod 语义并泄漏到后续测试（本卡实测教训）。"""
    from contextlib import contextmanager

    @contextmanager
    def patched():
        saved = GroupService.__dict__.get("_find_any_membership")
        original = saved.__func__ if isinstance(saved, staticmethod) else saved
        armed_sessions: set[int] = set()

        async def gated(db, group_id, user_id):
            member = await original(db, group_id, user_id)
            if id(db) not in armed_sessions:
                armed_sessions.add(id(db))
                await barrier.wait()
            return member

        GroupService._find_any_membership = staticmethod(gated)
        try:
            yield
        finally:
            if saved is None:
                del GroupService._find_any_membership
            else:
                GroupService._find_any_membership = saved

    return patched()


async def _seed_group_with_member(rig, *, soft_deleted_user: User | None = None):
    """建群+群主；可选把某成员置为软删（重加入竞态的前置状态）。"""
    factory = rig.session_factory()
    async with factory() as session:
        owner = User(
            username=f"rejoin_owner_{uuid4().hex[:8]}",
            email=f"rejoin_{uuid4().hex[:8]}@t.example",
            hashed_password="x",
            photon_balance=0,
        )
        session.add(owner)
        await session.flush()
        group = Group(
            name=f"grp-{uuid4().hex[:8]}",
            type=GroupType.SQUAD,
            focus_tags=[],
            max_members=8,
            is_public=True,
            join_requires_approval=False,
        )
        session.add(group)
        await session.flush()
        session.add(
            GroupMember(
                group_id=group.id,
                user_id=owner.id,
                role=GroupRole.OWNER,
                joined_at=datetime.now(UTC).replace(tzinfo=None),
                last_active_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        member: GroupMember | None = None
        if soft_deleted_user is not None:
            session.add(soft_deleted_user)
            await session.flush()
            member = GroupMember(
                group_id=group.id,
                user_id=soft_deleted_user.id,
                role=GroupRole.MEMBER,
                flame_contribution=7,
                joined_at=datetime.now(UTC).replace(tzinfo=None),
                last_active_at=datetime.now(UTC).replace(tzinfo=None),
                deleted_at=datetime.now(UTC).replace(tzinfo=None),
            )
            session.add(member)
        await session.commit()
        return str(group.id), str(owner.id), (str(member.id) if member else None)


async def _seed_rig_user(rig, prefix: str) -> str:
    factory = rig.session_factory()
    async with factory() as session:
        user = User(
            username=f"{prefix}_{uuid4().hex[:8]}",
            email=f"rejoin_{uuid4().hex[:8]}@t.example",
            hashed_password="x",
            photon_balance=0,
        )
        session.add(user)
        await session.commit()
        return str(user.id)


def _make_user_obj(prefix: str) -> User:
    return User(
        username=f"{prefix}_{uuid4().hex[:8]}",
        email=f"rejoin_{uuid4().hex[:8]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )


async def _run_join(rig, group_id: str, user_id: str, barrier: asyncio.Barrier | None):
    factory = rig.session_factory()
    async with factory() as session:
        member = await GroupService.join_group(session, _uuid(group_id), _uuid(user_id))
        await session.commit()
        return member


def _uuid(s: str):
    from uuid import UUID

    return UUID(s)


async def _member_rows(rig, group_id: str, user_id: str | None = None) -> list[GroupMember]:
    factory = rig.session_factory()
    async with factory() as session:
        stmt = select(GroupMember).where(GroupMember.group_id == _uuid(group_id))
        if user_id is not None:
            stmt = stmt.where(GroupMember.user_id == _uuid(user_id))
        result = await session.execute(stmt)
        return list(result.scalars().all())


@pytest.mark.asyncio
async def test_concurrent_fresh_join_exactly_one_active_row(rig, tmp_path):
    """并发首 join（门后 barrier 放大毫秒窗口）→ 唯一部分索引仲裁恰一活跃行。"""
    group_id, _owner_id, _ = await _seed_group_with_member(rig)
    joiner = _make_user_obj("joiner")
    # joiner 需先落库拿 id
    factory = rig.session_factory()
    async with factory() as session:
        session.add(joiner)
        await session.commit()
        joiner_id = str(joiner.id)

    barrier = asyncio.Barrier(2)
    with _install_gate_barrier(barrier):
        results = await asyncio.wait_for(
            asyncio.gather(
                _run_join(rig, group_id, joiner_id, barrier),
                _run_join(rig, group_id, joiner_id, barrier),
                return_exceptions=True,
            ),
            timeout=45,
        )
    ok = [r for r in results if isinstance(r, GroupMember)]
    rejected = [r for r in results if isinstance(r, ValueError)]
    assert len(ok) == 1, f"并发首 join 必须恰一生效，实际 {len(ok)}：{results!r}"
    assert len(rejected) == 1 and "已是群组成员" in str(rejected[0])

    rows = await _member_rows(rig, group_id, joiner_id)
    active = [r for r in rows if r.deleted_at is None]
    assert len(rows) == 1 and len(active) == 1, (
        f"joiner 必须恰一行活跃行，实际 {len(rows)} 行（活跃 {len(active)}）"
    )


@pytest.mark.asyncio
async def test_concurrent_rejoin_lands_on_same_single_active_row(rig):
    """并发重入（软删行已存在）→ 双方都复活同一行 → 恰一行活跃、统计继承。"""
    rejoiner = _make_user_obj("rejoiner")
    group_id, _owner_id, member_id = await _seed_group_with_member(rig, soft_deleted_user=rejoiner)
    rejoiner_id = str(rejoiner.id)

    barrier = asyncio.Barrier(2)
    with _install_gate_barrier(barrier):
        results = await asyncio.wait_for(
            asyncio.gather(
                _run_join(rig, group_id, rejoiner_id, barrier),
                _run_join(rig, group_id, rejoiner_id, barrier),
                return_exceptions=True,
            ),
            timeout=45,
        )
    ok = [r for r in results if isinstance(r, GroupMember)]
    assert len(ok) == 2, f"同 row 复活是幂等 UPDATE，两请求都应成功：{results!r}"
    assert len({str(r.id) for r in ok}) == 1, "必须落在同一行（复活语义）"

    rows = await _member_rows(rig, group_id, rejoiner_id)
    assert len(rows) == 1, f"并发重入不得产生第二行，实际 {len(rows)} 行"
    assert rows[0].deleted_at is None
    assert rows[0].flame_contribution == 7, "并发重入同样继承本人统计"
