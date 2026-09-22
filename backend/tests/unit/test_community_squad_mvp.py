"""冲刺小队 MVP 回归（D-COMM-3 · 社群×exam_sprint 首联动）。

钉四条验收面：
1. CRUD 与约束：小队 = Group(type=SPRINT) 复用（3-8 人、deadline 必填且
   须为未来、加入/退出/成员列表照社群既有惯例——软删、群主先转让）；
2. 聚合口径：每成员完成率唯一来自 sprint_task_ledger（BP-4 单一事实源），
   跨 plan/无 plan 任务全可见、软删与他人任务不可见，空账本诚实语义
   （total=0/rate=0.0/has_ledger_data=False，不把 0 伪装成完成率）；
3. 防刷红线（D20）：XP/光子/榜单行为量禁入——AST 导入扫描（结构断言）
   + 改光子/火苗后聚合逐字节不变（行为断言）双钉；
4. 隐私：成员列表与完成度聚合仅小队成员可见（非成员服务层
   SquadPermissionError / API 层 403）；小队不存在/非 SPRINT 类型统一 404
   不泄露存在性；冲刺周期已过则列表不可见、加入被拒。
"""

from __future__ import annotations

import ast
import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.community_squad import SquadCreate
from app.services.community_squad_service import (
    SquadNotFoundError,
    SquadPermissionError,
    SquadService,
    SquadStateError,
    sprint_period_active,
)
from app.services.sprint_task_ledger import (
    build_ledger_task_stats,
    fetch_sprint_ledger_tasks,
)

SQUAD_ROUTER_PREFIX = "/api/v1/community/squads"

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_SQUAD_MODULES = (
    _BACKEND_ROOT / "app" / "services" / "community_squad_service.py",
    _BACKEND_ROOT / "app" / "api" / "v1" / "community_squad.py",
)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
async def _make_user(db: AsyncSession, prefix: str = "squad") -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_squad(
    db: AsyncSession,
    owner: User,
    *,
    deadline: datetime | None = None,
    max_members: int = 8,
) -> Group:
    """直接落库建 SPRINT 群（绕过 SquadCreate 的未来日期校验，便于造过期小队）。"""
    group = Group(
        name=f"squad-{uuid_mod.uuid4().hex[:8]}",
        type=GroupType.SPRINT,
        focus_tags=[],
        deadline=deadline or (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)),
        sprint_goal="期末周冲完计网",
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


async def _join(db: AsyncSession, group: Group, user: User, *, role: GroupRole = GroupRole.MEMBER) -> GroupMember:
    member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        role=role,
        joined_at=datetime.now(UTC).replace(tzinfo=None),
        last_active_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(member)
    await db.flush()
    return member


async def _add_task(
    db: AsyncSession,
    user: User,
    *,
    status: TaskStatus = TaskStatus.PENDING,
    deleted: bool = False,
) -> Task:
    task = Task(
        user_id=user.id,
        title=f"task-{uuid_mod.uuid4().hex[:8]}",
        type="LEARNING",
        estimated_minutes=25,
        status=status,
        deleted_at=datetime.now(UTC).replace(tzinfo=None) if deleted else None,
    )
    db.add(task)
    await db.flush()
    return task


# ---------------------------------------------------------------------------
# 1. 防刷红线：XP/光子/榜单行为量禁入（结构 + 行为双断言）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_path", _SQUAD_MODULES)
def test_squad_modules_import_scan_no_xp_photon_leaderboard(module_path):
    """AST 导入扫描：小队两模块不得 import photon/experience/leaderboard/xp 域。"""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    forbidden = ("photon", "experience", "leaderboard", "xp")
    hits = [m for m in imported_modules if any(f in m.lower() for f in forbidden)]
    assert hits == [], f"小队模块出现了禁入域导入（D20 红线）: {hits} in {module_path.name}"


def test_squad_service_must_consume_ledger_ssot():
    """服务层必须显式消费 sprint_task_ledger（口径唯一定义点，禁止第二套聚合）。"""
    src = (_BACKEND_ROOT / "app" / "services" / "community_squad_service.py").read_text(encoding="utf-8")
    assert "from app.services.sprint_task_ledger import" in src
    assert "fetch_sprint_ledger_tasks" in src and "build_ledger_task_stats" in src


@pytest.mark.asyncio
async def test_progress_indifferent_to_photon_and_flame_mutations(db_session):
    """行为断言：光子余额/火苗等级任意改写，完成度聚合逐字段不变。"""
    owner = await _make_user(db_session, "owner")
    mate = await _make_user(db_session, "mate")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    for status in (TaskStatus.COMPLETED, TaskStatus.COMPLETED, TaskStatus.PENDING):
        await _add_task(db_session, owner, status=status)
    await db_session.commit()

    baseline = await SquadService.get_squad_sprint_progress(db_session, squad.id, owner.id)

    # 防刷扰动：光子拉满、火苗烧到顶——若聚合读了行为量，这里必然漂移
    owner.photon_balance = 999_999
    owner.flame_level = 99
    mate.photon_balance = 123_456
    mate.flame_level = 42
    db_session.add_all([owner, mate])
    await db_session.commit()

    after = await SquadService.get_squad_sprint_progress(db_session, squad.id, owner.id)
    assert [
        (m.user_id, m.task_total, m.task_completed, m.completion_rate, m.has_ledger_data) for m in baseline["members"]
    ] == [
        (m.user_id, m.task_total, m.task_completed, m.completion_rate, m.has_ledger_data) for m in after["members"]
    ], "完成度聚合对光子/火苗扰动不敏感（sprint-completion 口径，行为量禁入）"


# ---------------------------------------------------------------------------
# 2. CRUD 与约束（复用裁决的落地验证）
# ---------------------------------------------------------------------------
def test_squad_create_constraints_three_to_eight_and_deadline():
    """SquadCreate：人数 3-8 收敛；deadline 必填且不得在过去。"""
    future = datetime.now(UTC) + timedelta(days=7)
    base = {"name": "期末冲冲冲", "deadline": future}

    with pytest.raises(ValidationError):
        SquadCreate(**base, max_members=2)
    with pytest.raises(ValidationError):
        SquadCreate(**base, max_members=9)
    with pytest.raises(ValidationError):
        SquadCreate(**{**base, "deadline": None})
    with pytest.raises(ValidationError):
        SquadCreate(**{**base, "deadline": datetime.now(UTC) - timedelta(days=1)})

    payload = SquadCreate(**base, max_members=5)
    assert payload.max_members == 5


@pytest.mark.asyncio
async def test_create_squad_uses_group_type_sprint_and_owner_role(db_session):
    """复用裁决落地：不建新表，type=SPRINT，创建者即群主。"""
    owner = await _make_user(db_session)
    squad = await SquadService.create_squad(
        db_session,
        owner.id,
        SquadCreate(name="七日计网冲刺", deadline=datetime.now(UTC) + timedelta(days=7), max_members=6),
    )
    assert squad.type == GroupType.SPRINT
    assert squad.max_members == 6
    assert squad.deadline is not None and squad.sprint_goal is None

    detail = await SquadService.get_squad(db_session, squad.id, owner.id)
    assert detail["my_role"] == "owner"
    assert detail["member_count"] == 1


@pytest.mark.asyncio
async def test_join_full_squad_rejected_and_leave_soft_deletes(db_session):
    """人数上限（3-8）生效；退出=软删成员记录（社群既有惯例）；群主不可直接退出。"""
    owner = await _make_user(db_session)
    squad = await _make_squad(db_session, owner, max_members=3)
    mates = [await _make_user(db_session) for _ in range(2)]
    for mate in mates:
        await SquadService.join_squad(db_session, squad.id, mate.id)

    outsider = await _make_user(db_session)
    with pytest.raises(SquadStateError):
        await SquadService.join_squad(db_session, squad.id, outsider.id)

    # 成员退出：软删（deleted_at 置位），群组仍在
    await SquadService.leave_squad(db_session, squad.id, mates[0].id)
    await db_session.commit()
    detail = await SquadService.get_squad(db_session, squad.id, owner.id)
    assert detail["member_count"] == 2

    # 群主不能直接退出（既有惯例：先转让）
    with pytest.raises(SquadStateError):
        await SquadService.leave_squad(db_session, squad.id, owner.id)


@pytest.mark.asyncio
async def test_non_sprint_group_not_visible_via_squad_surface(db_session):
    """非 SPRINT 群组走小队面 → 统一 SquadNotFoundError（不泄露存在性）。"""
    owner = await _make_user(db_session)
    plain = Group(name="普通学习小队", type=GroupType.SQUAD, focus_tags=[], max_members=50)
    db_session.add(plain)
    await db_session.flush()
    db_session.add(GroupMember(group_id=plain.id, user_id=owner.id, role=GroupRole.OWNER))
    await db_session.flush()

    with pytest.raises(SquadNotFoundError):
        await SquadService.get_squad(db_session, plain.id, owner.id)
    with pytest.raises(SquadNotFoundError):
        await SquadService.join_squad(db_session, plain.id, owner.id)
    with pytest.raises(SquadNotFoundError):
        await SquadService.get_squad_sprint_progress(db_session, plain.id, owner.id)


# ---------------------------------------------------------------------------
# 3. 冲刺周期：仅周期内可见/可加入
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_expired_squad_hidden_from_list_and_join_blocked(db_session):
    owner = await _make_user(db_session)
    mate = await _make_user(db_session)
    expired = await _make_squad(db_session, owner, deadline=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=1))
    assert not sprint_period_active(expired)

    squads = await SquadService.list_my_squads(db_session, owner.id)
    assert all(s["id"] != expired.id for s in squads), "冲刺周期已过的小队不得出现在列表"

    with pytest.raises(SquadStateError):
        await SquadService.join_squad(db_session, expired.id, mate.id)

    active = await _make_squad(db_session, owner)
    await _join(db_session, active, mate)
    await db_session.commit()
    squads = await SquadService.list_my_squads(db_session, mate.id)
    assert [s["id"] for s in squads] == [active.id]


# ---------------------------------------------------------------------------
# 4. 隐私：成员列表/完成度仅小队成员可见
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_members_and_progress_member_only(db_session):
    owner = await _make_user(db_session)
    mate = await _make_user(db_session)
    outsider = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    await db_session.commit()

    with pytest.raises(SquadPermissionError):
        await SquadService.get_squad_members(db_session, squad.id, outsider.id)
    with pytest.raises(SquadPermissionError):
        await SquadService.get_squad_sprint_progress(db_session, squad.id, outsider.id)

    members = await SquadService.get_squad_members(db_session, squad.id, mate.id)
    assert {m.user_id for m in members} == {owner.id, mate.id}

    progress = await SquadService.get_squad_sprint_progress(db_session, squad.id, mate.id)
    assert {m.user_id for m in progress["members"]} == {owner.id, mate.id}
    assert progress["sprint_active"] is True


# ---------------------------------------------------------------------------
# 5. 聚合口径：唯一来自 sprint_task_ledger + 空数据诚实语义
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_progress_matches_ledger_ssot_across_plans_and_honest_empty(db_session):
    owner = await _make_user(db_session)
    busy = await _make_user(db_session)
    empty = await _make_user(db_session)
    foreign = await _make_user(db_session)  # 非成员，其任务绝不可入账
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, busy)
    await _join(db_session, squad, empty)

    # owner：3 任务 2 完成（跨 plan + 无 plan 挂靠 + 软删各一）
    await _add_task(db_session, owner, status=TaskStatus.COMPLETED)
    await _add_task(db_session, owner, status=TaskStatus.COMPLETED)
    await _add_task(db_session, owner, status=TaskStatus.PENDING)
    await _add_task(db_session, owner, status=TaskStatus.COMPLETED, deleted=True)
    # busy：1 任务已完成
    await _add_task(db_session, busy, status=TaskStatus.COMPLETED)
    # foreign：非成员的高完成率不得泄露进小队面
    for _ in range(5):
        await _add_task(db_session, foreign, status=TaskStatus.COMPLETED)
    await db_session.commit()

    progress = await SquadService.get_squad_sprint_progress(db_session, squad.id, owner.id)
    by_user = {m.user_id: m for m in progress["members"]}
    assert set(by_user) == {owner.id, busy.id, empty.id}, "聚合必须只覆盖在册成员"

    owner_stats = by_user[owner.id]
    assert (owner_stats.task_total, owner_stats.task_completed) == (3, 2), "软删任务不计入账本全集"
    assert owner_stats.completion_rate == round(2 / 3, 4)
    assert owner_stats.has_ledger_data is True

    # 口径与 SSOT 纯构造逐字段一致（同源证明）
    ledger = await fetch_sprint_ledger_tasks(db_session, user_id=owner.id)
    assert owner_stats.stats == build_ledger_task_stats(ledger)

    busy_stats = by_user[busy.id]
    assert (busy_stats.task_total, busy_stats.task_completed, busy_stats.completion_rate) == (1, 1, 1.0)

    # 空数据诚实语义：不是 0 完成率伪装，而是显式无账本数据
    empty_stats = by_user[empty.id]
    assert (empty_stats.task_total, empty_stats.task_completed) == (0, 0)
    assert empty_stats.completion_rate == 0.0
    assert empty_stats.has_ledger_data is False
    assert empty_stats.display_name is None or isinstance(empty_stats.display_name, str)


# ---------------------------------------------------------------------------
# 6. API 层：201/200/403/404 映射与端到端回路
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_squad_api_round_trip_with_permission_mapping(db_session):
    owner = await _make_user(db_session, "api_owner")
    mate = await _make_user(db_session, "api_mate")
    outsider = await _make_user(db_session, "api_out")
    await _add_task(db_session, owner, status=TaskStatus.COMPLETED)
    await db_session.commit()

    current = {"user": owner}

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return current["user"]

    from app.api.v1.community_squad import router as squad_router

    app = FastAPI()
    app.include_router(squad_router, prefix="/api/v1/community")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 创建（201）
        create_resp = await ac.post(
            SQUAD_ROUTER_PREFIX,
            json={
                "name": "七日高数冲刺",
                "deadline": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
                "max_members": 4,
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        squad_id = create_resp.json()["id"]
        assert create_resp.json()["my_role"] == "owner"

        # 我的列表（200）
        list_resp = await ac.get(SQUAD_ROUTER_PREFIX)
        assert list_resp.status_code == 200
        assert [s["id"] for s in list_resp.json()] == [squad_id]

        # 非成员读成员列表/完成度 → 403
        current["user"] = outsider
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad_id}/members")).status_code == 403
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad_id}/sprint-progress")).status_code == 403

        # 加入后可读
        current["user"] = mate
        join_resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad_id}/join")
        assert join_resp.status_code == 200

        progress_resp = await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad_id}/sprint-progress")
        assert progress_resp.status_code == 200
        payload = progress_resp.json()
        assert payload["squad_id"] == squad_id and payload["sprint_active"] is True
        assert len(payload["members"]) == 2

        members_resp = await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad_id}/members")
        assert members_resp.status_code == 200
        assert len(members_resp.json()) == 2

        # 不存在/非小队 → 404（不泄露存在性）
        missing = await ac.get(f"{SQUAD_ROUTER_PREFIX}/{uuid4()}/sprint-progress")
        assert missing.status_code == 404

        # 退出（200）
        leave_resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad_id}/leave")
        assert leave_resp.status_code == 200
