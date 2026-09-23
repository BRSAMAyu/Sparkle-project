"""共学自习室（在场证明）+ 小队榜回归（D-COMM-4）。

钉六条验收面：
1. 在场进出/时长：显式进出为主（enter/exit），会话时长与「今日累计」
   如实结算（跨日会话只计入今日重叠部分，本地日界照督促域时区惯例；
   时长按最后活性证明 + TTL 诚实封顶，decay 不虚增）；
   enter 幂等（重复进入不建重复会话）、exit 幂等诚实（already_out）；
2. 在室视图（ROOM-PRESENCE 服务端 TTL 真源）：读路径只认未过期——
   in_room = 开放会话且心跳在 TTL（90s）内，TTL 过期=诚实离场（杀进程
   后最多 TTL 内残留）；is_stale = 有开放会话但已过期（崩溃恢复线索）；
   未入场成员如实为 0（不缺席惩罚）；心跳是显式续期信号（前台房间
   轮询拍，绝不要求后台 Timer）；
3. 小队榜：榜分零新口径——唯一消费 D-COMM-3 聚合面（get_squad_sprint_progress
   → sprint_task_ledger，BP-4 SSOT），排序正确（并列同名次）、percentile
   区间、分页包装；成员 <3 人 board_valid=False / self_view_only=True
   （设计裁决：榜不成立，客户端切自我锚）；
4. 隐私：自习室与榜单仅小队成员可见（非成员 SquadPermissionError / API 403）；
   非 SPRINT 群组统一 404 不泄露存在性；
5. 防刷红线（D20）：XP/光子/榜单行为量禁入——AST 导入扫描（结构断言）
   + 改光子/火苗后榜分与在场时长逐字段不变（行为断言）双钉；
6. 网关代理照 D-COMM-3 先例（见 proxy_routes_dcomm4_test.go）。
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.models.study_room import StudyRoomSession
from app.models.task import Task, TaskStatus
from app.models.user import PushPreference, User
from app.services.community_squad_board_service import SquadBoardService
from app.services.community_squad_service import (
    SquadNotFoundError,
    SquadPermissionError,
)
from app.services.community_study_room_service import StudyRoomService

SQUAD_ROUTER_PREFIX = "/api/v1/community/squads"

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_DCOMM4_MODULES = (
    _BACKEND_ROOT / "app" / "services" / "community_study_room_service.py",
    _BACKEND_ROOT / "app" / "services" / "community_squad_board_service.py",
    _BACKEND_ROOT / "app" / "api" / "v1" / "community_study_room.py",
    _BACKEND_ROOT / "app" / "api" / "v1" / "community_squad_board.py",
)


# ---------------------------------------------------------------------------
# 工具（与 D-COMM-3 测试同款造数惯例）
# ---------------------------------------------------------------------------
async def _make_user(db: AsyncSession, prefix: str = "room") -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_squad(db: AsyncSession, owner: User, *, max_members: int = 8) -> Group:
    group = Group(
        name=f"squad-{uuid_mod.uuid4().hex[:8]}",
        type=GroupType.SPRINT,
        focus_tags=[],
        deadline=(datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)),
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


async def _join(db: AsyncSession, group: Group, user: User) -> GroupMember:
    member = GroupMember(
        group_id=group.id,
        user_id=user.id,
        role=GroupRole.MEMBER,
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
) -> Task:
    task = Task(
        user_id=user.id,
        title=f"task-{uuid_mod.uuid4().hex[:8]}",
        type="LEARNING",
        estimated_minutes=25,
        status=status,
    )
    db.add(task)
    await db.flush()
    return task


def _freeze_now(monkeypatch: pytest.MonkeyPatch, frozen: datetime) -> None:
    """冻结自习室服务的时钟（服务内部统一走模块级 _utcnow）。"""
    from app.services import community_study_room_service as room_module

    monkeypatch.setattr(room_module, "_utcnow", lambda: frozen)


# ---------------------------------------------------------------------------
# 1. 防刷红线：XP/光子/榜单行为量禁入（结构 + 行为双断言）
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module_path", _DCOMM4_MODULES)
def test_dcomm4_modules_import_scan_no_xp_photon_leaderboard(module_path):
    """AST 导入扫描：自习室/小队榜四模块不得 import photon/experience/leaderboard/xp 域。"""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
    forbidden = ("photon", "experience", "leaderboard", "xp")
    hits = [m for m in imported_modules if any(f in m.lower() for f in forbidden)]
    assert hits == [], f"D-COMM-4 模块出现了禁入域导入（D20 红线）: {hits} in {module_path.name}"


def test_board_service_must_consume_dcomm3_aggregation_ssot():
    """小队榜必须消费 D-COMM-3 聚合面（零第二套口径）；在场时长模型禁入榜模块。"""
    board_path = _BACKEND_ROOT / "app" / "services" / "community_squad_board_service.py"
    src = board_path.read_text(encoding="utf-8")
    assert "from app.services.community_squad_service import" in src
    assert "get_squad_sprint_progress" in src, "小队榜必须复用 D-COMM-3 聚合面（BP-4 SSOT）"
    tree = ast.parse(src)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    hits = [m for m in imported if "study_room" in m]
    assert hits == [], f"在场时长禁入榜分（挂机刷时长防线，设计卡 §3.3 风险条）: {hits}"


@pytest.mark.asyncio
async def test_leaderboard_and_presence_indifferent_to_photon_flame_mutations(db_session):
    """行为断言：光子/火苗任意改写，小队榜与在场时长逐字段不变。"""
    owner = await _make_user(db_session, "owner")
    mate = await _make_user(db_session, "mate")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    await _add_task(db_session, owner, status=TaskStatus.COMPLETED)
    await _add_task(db_session, mate, status=TaskStatus.PENDING)
    board_before = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    presence_before = await StudyRoomService.get_presence(db_session, squad.id, owner.id)

    owner.photon_balance = 999_999
    owner.flame_level = 99
    mate.photon_balance = 123_456
    mate.flame_level = 42
    db_session.add_all([owner, mate])
    await db_session.commit()

    board_after = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    presence_after = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    assert [(e.user_id, e.rank, e.task_total, e.task_completed, e.completion_rate) for e in board_before.entries] == [
        (e.user_id, e.rank, e.task_total, e.task_completed, e.completion_rate) for e in board_after.entries
    ], "小队榜对光子/火苗扰动不敏感（sprint-completion 口径，行为量禁入）"
    assert [(m.user_id, m.in_room, m.today_minutes) for m in presence_before["members"]] == [
        (m.user_id, m.in_room, m.today_minutes) for m in presence_after["members"]
    ], "在场时长对光子/火苗扰动不敏感（beacon 式如实记录）"


# ---------------------------------------------------------------------------
# 2. 在场进出 / 时长结算
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_enter_exit_round_trip_duration_and_reenter(db_session, monkeypatch):
    owner = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    frozen = datetime(2026, 9, 23, 8, 0, 0)  # naive UTC
    _freeze_now(monkeypatch, frozen)

    entered = await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    assert entered["reentered"] is False
    assert entered["entered_at"] == frozen

    # 回拨进入时刻 90 分钟后退出：session_minutes=90
    session_row = (
        await db_session.execute(select(StudyRoomSession).where(StudyRoomSession.user_id == owner.id))
    ).scalar_one()
    session_row.entered_at = frozen - timedelta(minutes=90)
    await db_session.flush()

    exited = await StudyRoomService.exit_room(db_session, squad.id, owner.id)
    assert exited["already_out"] is False
    assert exited["session_minutes"] == 90
    assert exited["today_minutes"] == 90

    # 重复退出：诚实上报 already_out（不报错、不造记录）
    repeat_exit = await StudyRoomService.exit_room(db_session, squad.id, owner.id)
    assert repeat_exit["already_out"] is True and repeat_exit["session_minutes"] == 0

    # 再进入：新会话；重复进入幂等（不建重复记录）
    again = await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    assert again["reentered"] is False and again["session_id"] != exited["session_id"]
    twice = await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    assert twice["reentered"] is True and twice["session_id"] == again["session_id"]
    open_count = len(
        (
            await db_session.execute(
                select(StudyRoomSession).where(
                    StudyRoomSession.user_id == owner.id,
                    StudyRoomSession.exited_at.is_(None),
                )
            )
        ).all()
    )
    assert open_count == 1, "重复进入不得产生第二个开放会话"


@pytest.mark.asyncio
async def test_today_minutes_local_day_window_and_cross_midnight_overlap(db_session, monkeypatch):
    """「今日」按成员本地日界（Asia/Shanghai 默认）；跨日会话只计入今日重叠。"""
    owner = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    # 冻结在 2026-09-23 01:30 UTC（上海 09:23→09:30，本地日界 2026-09-23 00:00 = 2026-09-22 16:00 UTC）
    frozen = datetime(2026, 9, 23, 1, 30, 0)
    _freeze_now(monkeypatch, frozen)
    db_session.add(PushPreference(user_id=owner.id, timezone="Asia/Shanghai"))
    await db_session.flush()

    # 会话 A：上海今天 01:00-02:00（17:00-18:00 UTC 前一日）→ 今日重叠 60 分钟
    session_a = StudyRoomSession(
        group_id=squad.id,
        user_id=owner.id,
        entered_at=datetime(2026, 9, 22, 17, 0, 0),
        exited_at=datetime(2026, 9, 22, 18, 0, 0),
        last_heartbeat_at=datetime(2026, 9, 22, 18, 0, 0),
    )
    # 会话 B：上海今天 04:00 起至今仍在场（20:00 UTC 前一日 → 01:30 UTC）→ 330 分钟
    session_b = StudyRoomSession(
        group_id=squad.id,
        user_id=owner.id,
        entered_at=datetime(2026, 9, 22, 20, 0, 0),
        exited_at=None,
        last_heartbeat_at=frozen,
    )
    # 会话 C：昨天白天（上海昨天 10:00-11:00）→ 完全在今日窗口外，不计
    session_c = StudyRoomSession(
        group_id=squad.id,
        user_id=owner.id,
        entered_at=datetime(2026, 9, 22, 2, 0, 0),
        exited_at=datetime(2026, 9, 22, 3, 0, 0),
        last_heartbeat_at=datetime(2026, 9, 22, 3, 0, 0),
    )
    db_session.add_all([session_a, session_b, session_c])
    await db_session.flush()

    entered = await StudyRoomService.enter_room(db_session, squad.id, owner.id)  # 幂等命中 B
    assert entered["reentered"] is True
    assert entered["today_minutes"] == 60 + 330, "今日累计=本地日界窗口内的重叠分钟之和（跨日裁剪、昨日不计）"


@pytest.mark.asyncio
async def test_presence_lists_members_with_ttl_and_stale_flag(db_session, monkeypatch):
    """在室视图（ROOM-PRESENCE TTL 语义）：读路径只认未过期——
    在场=A 新鲜心跳；TTL 过期=B 诚实离场+is_stale（崩溃恢复线索）；
    显式退出=C 立即清档（连 is_stale 都不留）；未入场=D 如实为 0。"""
    from app.schemas.community_study_room import STUDY_ROOM_PRESENCE_TTL_SECONDS

    owner = await _make_user(db_session, "pown")
    insider = await _make_user(db_session, "pins")
    lapsed = await _make_user(db_session, "plap")
    leaver = await _make_user(db_session, "pleave")
    stranger = await _make_user(db_session, "str")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, insider)
    await _join(db_session, squad, lapsed)
    await _join(db_session, squad, leaver)
    await db_session.commit()

    frozen = datetime(2026, 9, 23, 6, 0, 0)
    _freeze_now(monkeypatch, frozen)
    await StudyRoomService.enter_room(db_session, squad.id, insider.id)  # 在场（心跳新鲜）
    await StudyRoomService.enter_room(db_session, squad.id, lapsed.id)
    lapsed_row = (
        await db_session.execute(select(StudyRoomSession).where(StudyRoomSession.user_id == lapsed.id))
    ).scalar_one()
    # 心跳拨回 TTL+1s 前 → 过期：读路径诚实判离场（旧语义只标 is_stale 仍算在场）
    lapsed_row.last_heartbeat_at = frozen - timedelta(seconds=STUDY_ROOM_PRESENCE_TTL_SECONDS + 1)
    await db_session.flush()
    await StudyRoomService.enter_room(db_session, squad.id, leaver.id)
    exited = await StudyRoomService.exit_room(db_session, squad.id, leaver.id)
    assert exited["already_out"] is False

    presence = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    assert presence["member_count"] == 4 and presence["in_room_count"] == 1
    by_user = {m.user_id: m for m in presence["members"]}
    assert set(by_user) == {owner.id, insider.id, lapsed.id, leaver.id}, "非成员不得出现在在室视图"

    assert by_user[owner.id].in_room is False and by_user[owner.id].today_minutes == 0, "未入场成员如实为 0"
    assert by_user[insider.id].in_room is True and by_user[insider.id].is_stale is False
    assert by_user[lapsed.id].in_room is False and by_user[lapsed.id].is_stale is True, "TTL 过期=诚实离场"
    assert by_user[lapsed.id].entered_at is None and by_user[lapsed.id].current_session_minutes == 0
    assert by_user[leaver.id].in_room is False and by_user[leaver.id].is_stale is False, "显式退出立即清、无残留"

    # 心跳续期：房间 UI 的活性证明把 decayed 开放记录续命回在场（非自动重开）
    beat = await StudyRoomService.heartbeat(db_session, squad.id, lapsed.id)
    assert beat["in_room"] is True and beat["last_heartbeat_at"] == frozen
    renewed = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    by_user2 = {m.user_id: m for m in renewed["members"]}
    assert by_user2[lapsed.id].in_room is True and by_user2[lapsed.id].is_stale is False

    # 无开放会话的心跳：诚实上报（不自动重开）
    beat_out = await StudyRoomService.heartbeat(db_session, squad.id, owner.id)
    assert beat_out["in_room"] is False and beat_out["today_minutes"] == 0

    await db_session.commit()
    with pytest.raises(SquadPermissionError):
        await StudyRoomService.get_presence(db_session, squad.id, stranger.id)


# ---------------------------------------------------------------------------
# 2.5 TTL 真源：过期=诚实离场 / exit 即清 / 续期信号 / decay 收档（ROOM-PRESENCE）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ttl_expiry_is_honest_departure_and_minutes_stop_accruing(db_session, monkeypatch):
    """红证：enter 后 TTL 过期 → 读路径不再判在场（杀进程后最多 TTL 内残留，
    TTL 后诚实消失）；今日累计同步封顶于最后活性证明 + TTL（decay 不虚增）。"""
    from app.schemas.community_study_room import STUDY_ROOM_PRESENCE_TTL_SECONDS

    owner = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    t0 = datetime(2026, 9, 23, 8, 0, 0)
    _freeze_now(monkeypatch, t0)
    entered = await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    assert entered["reentered"] is False

    # 回拨进入时刻 10 分钟（模拟在场已 10 分钟的稳态），心跳仍为 t0
    row = (await db_session.execute(select(StudyRoomSession).where(StudyRoomSession.user_id == owner.id))).scalar_one()
    row.entered_at = t0 - timedelta(minutes=10)
    await db_session.flush()

    # 恰在 TTL 边界（age == TTL）仍算在场：今日累计 = 10min + 90s → 地板 11 分钟
    boundary = t0 + timedelta(seconds=STUDY_ROOM_PRESENCE_TTL_SECONDS)
    _freeze_now(monkeypatch, boundary)
    at_edge = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    assert at_edge["members"][0].in_room is True and at_edge["in_room_count"] == 1
    assert at_edge["members"][0].today_minutes == 10 + STUDY_ROOM_PRESENCE_TTL_SECONDS // 60

    # 越界 1 秒：诚实离场 + 今日累计封顶不再虚增（失联期不算自习时长）
    _freeze_now(monkeypatch, boundary + timedelta(seconds=1))
    after = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    entry = after["members"][0]
    assert entry.in_room is False and entry.is_stale is True
    assert entry.entered_at is None and entry.current_session_minutes == 0
    assert entry.today_minutes == 10 + STUDY_ROOM_PRESENCE_TTL_SECONDS // 60, "decay 后时长封顶、不随墙钟虚增"
    assert after["in_room_count"] == 0


@pytest.mark.asyncio
async def test_heartbeat_renews_ttl_for_active_only(db_session, monkeypatch):
    """续期信号续命：前台房间轮询（心跳）给活跃者续命——总 120s > TTL 仍在场；
    同一小队无续期的队友在同一时刻诚实衰减为离场（对照组）。"""
    owner = await _make_user(db_session, "renew")
    mate = await _make_user(db_session, "quiet")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    t0 = datetime(2026, 9, 23, 8, 0, 0)
    _freeze_now(monkeypatch, t0)
    await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    await StudyRoomService.enter_room(db_session, squad.id, mate.id)

    # +60s：只有 owner 发心跳（前台轮询拍）
    _freeze_now(monkeypatch, t0 + timedelta(seconds=60))
    beat = await StudyRoomService.heartbeat(db_session, squad.id, owner.id)
    assert beat["in_room"] is True

    # +120s（> TTL）：owner 被续命仍在场；mate 无续期诚实衰减
    _freeze_now(monkeypatch, t0 + timedelta(seconds=120))
    presence = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    by_user = {m.user_id: m for m in presence["members"]}
    assert by_user[owner.id].in_room is True and by_user[owner.id].is_stale is False
    assert by_user[mate.id].in_room is False and by_user[mate.id].is_stale is True
    assert presence["in_room_count"] == 1


@pytest.mark.asyncio
async def test_exit_clears_presence_immediately_even_fresh(db_session, monkeypatch):
    """exit 立即清：刚 enter（TTL 远未过期）即退出 → 读路径立即不在场，
    无 is_stale 残留、无时长时间（诚实为 0 分钟）。"""
    owner = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    t0 = datetime(2026, 9, 23, 8, 0, 0)
    _freeze_now(monkeypatch, t0)
    await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    fresh = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    assert fresh["members"][0].in_room is True

    exited = await StudyRoomService.exit_room(db_session, squad.id, owner.id)
    assert exited["already_out"] is False and exited["session_minutes"] == 0
    presence = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    entry = presence["members"][0]
    assert entry.in_room is False and entry.is_stale is False, "显式退出立即清档、零残留"
    assert entry.today_minutes == 0 and presence["in_room_count"] == 0


@pytest.mark.asyncio
async def test_enter_after_ttl_decay_rearchives_and_preserves_proven_minutes(db_session, monkeypatch):
    """decay 后 re-enter：旧档按诚实离场时刻（最后活性证明 + TTL）收档，
    新档从现在起算——「一记录一进出场」不变，已证明的今日时长保留。"""
    from app.schemas.community_study_room import STUDY_ROOM_PRESENCE_TTL_SECONDS

    owner = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    t0 = datetime(2026, 9, 23, 8, 0, 0)
    _freeze_now(monkeypatch, t0)
    first = await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    row = (await db_session.execute(select(StudyRoomSession).where(StudyRoomSession.user_id == owner.id))).scalar_one()
    row.entered_at = t0 - timedelta(minutes=30)  # 已自习 30 分钟的稳态（心跳 t0）
    await db_session.flush()

    # 失联超过 TTL：诚实衰减
    t1 = t0 + timedelta(minutes=10)
    _freeze_now(monkeypatch, t1)
    decayed = await StudyRoomService.get_presence(db_session, squad.id, owner.id)
    assert decayed["members"][0].in_room is False and decayed["members"][0].is_stale is True

    # 回来自动重新进场：不要求用户先手动退出；旧档收档于 hb+TTL，新档 now 起算
    second = await StudyRoomService.enter_room(db_session, squad.id, owner.id)
    assert second["reentered"] is False and second["session_id"] != first["session_id"]
    assert second["entered_at"] == t1
    # 今日累计 = 旧档已证明部分 [t0-30m, t0+90s] → 地板 31 分钟（不因收档丢失）
    assert second["today_minutes"] == 30 + STUDY_ROOM_PRESENCE_TTL_SECONDS // 60

    rows = (
        (
            await db_session.execute(
                select(StudyRoomSession)
                .where(StudyRoomSession.user_id == owner.id)
                .order_by(StudyRoomSession.entered_at.asc())
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
    assert rows[0].id == first["session_id"] and rows[0].exited_at == t0 + timedelta(
        seconds=STUDY_ROOM_PRESENCE_TTL_SECONDS
    ), "旧档收档于诚实离场时刻（最后活性证明 + TTL）"
    assert rows[1].id == second["session_id"] and rows[1].exited_at is None
    open_count = sum(1 for r in rows if r.exited_at is None)
    assert open_count == 1, "decay 收档后仍只有一个开放会话"


# ---------------------------------------------------------------------------
# 3. 小队榜：排序 / 并列名次 / 分页 / <3 人降级
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_leaderboard_sorting_ties_percentile_and_pagination(db_session):
    owner = await _make_user(db_session, "lown")  # B 档 2/3
    ace = await _make_user(db_session, "ace")  # A 档 2/2
    mid = await _make_user(db_session, "mid")  # C 档 0/4（有账本）
    empty = await _make_user(db_session, "empty")  # D 档无账本
    squad = await _make_squad(db_session, owner)
    for mate in (ace, mid, empty):
        await _join(db_session, squad, mate)

    for _ in range(2):
        await _add_task(db_session, owner, status=TaskStatus.COMPLETED)
    await _add_task(db_session, owner, status=TaskStatus.PENDING)
    for _ in range(2):
        await _add_task(db_session, ace, status=TaskStatus.COMPLETED)
    for _ in range(4):
        await _add_task(db_session, mid, status=TaskStatus.PENDING)
    await db_session.commit()

    board = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    assert board.total == 4 and board.board_valid is True and board.self_view_only is False
    assert [e.user_id for e in board.entries] == [
        ace.id,
        owner.id,
        mid.id,
        empty.id,
    ], "完成率降序，空账本（诚实无数据）排在 0% 有账本之后"
    assert [e.rank for e in board.entries] == [1, 2, 3, 4]
    assert board.my_rank == 2 and board.entries[1].percentile == 50
    assert board.entries[0].percentile == 75 and board.entries[2].percentile == 0

    # 并列名次（竞赛排名 1,1,3）：mid 与 empty 同为 0%——把 empty 改成 0/4 有账本
    await _add_task(db_session, empty, status=TaskStatus.PENDING)
    await db_session.commit()
    board2 = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, ace.id)
    rates = [e.completion_rate for e in board2.entries]
    assert rates[2] == rates[3] == 0.0
    assert board2.entries[2].rank == board2.entries[3].rank == 3, "排序键全同 → 并列名次"
    assert board2.my_rank == 1  # ace 2/2

    # 分页包装：名次在全集上计算后切片
    page = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, ace.id, limit=2, offset=1)
    assert page.total == 4 and len(page.entries) == 2
    assert [e.rank for e in page.entries] == [2, 3]
    assert page.entries[0].user_id == owner.id


@pytest.mark.asyncio
async def test_leaderboard_self_view_degradation_under_three_members(db_session):
    owner = await _make_user(db_session)
    mate = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    await _add_task(db_session, owner, status=TaskStatus.COMPLETED)
    await db_session.commit()

    board = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    assert board.member_count == 2
    assert board.board_valid is False and board.self_view_only is True, "<3 人榜不成立，客户端切自我锚（设计裁决）"
    assert board.my_rank == 1  # 自我锚仍给出本人相对位置

    third = await _make_user(db_session)
    await _join(db_session, squad, third)
    board3 = await SquadBoardService.get_squad_leaderboard(db_session, squad.id, owner.id)
    assert board3.board_valid is True and board3.self_view_only is False


# ---------------------------------------------------------------------------
# 4. 隐私与 404：非成员 403 / 非 SPRINT 404
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_room_and_board_reject_nonmember_and_non_sprint_group(db_session):
    owner = await _make_user(db_session)
    outsider = await _make_user(db_session)
    squad = await _make_squad(db_session, owner)
    await db_session.commit()

    for call in (
        StudyRoomService.enter_room,
        StudyRoomService.exit_room,
        StudyRoomService.heartbeat,
    ):
        with pytest.raises(SquadPermissionError):
            await call(db_session, squad.id, outsider.id)
    with pytest.raises(SquadPermissionError):
        await StudyRoomService.get_presence(db_session, squad.id, outsider.id)
    with pytest.raises(SquadPermissionError):
        await SquadBoardService.get_squad_leaderboard(db_session, squad.id, outsider.id)

    plain = Group(name="普通学习小队", type=GroupType.SQUAD, focus_tags=[], max_members=50)
    db_session.add(plain)
    await db_session.flush()
    db_session.add(GroupMember(group_id=plain.id, user_id=owner.id, role=GroupRole.OWNER))
    await db_session.flush()
    for call in (StudyRoomService.enter_room, StudyRoomService.get_presence):
        with pytest.raises(SquadNotFoundError):
            await call(db_session, plain.id, owner.id)
    with pytest.raises(SquadNotFoundError):
        await SquadBoardService.get_squad_leaderboard(db_session, plain.id, owner.id)


# ---------------------------------------------------------------------------
# 5. API 层：映射与端到端回路（403/404/200）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_room_and_board_api_round_trip_with_permission_mapping(db_session):
    owner = await _make_user(db_session, "api_owner")
    mate = await _make_user(db_session, "api_mate")
    outsider = await _make_user(db_session, "api_out")
    squad = await _make_squad(db_session, owner)
    await _join(db_session, squad, mate)
    await db_session.commit()

    current = {"user": owner}

    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return current["user"]

    from app.api.v1.community_squad_board import router as board_router
    from app.api.v1.community_study_room import router as room_router

    app = FastAPI()
    app.include_router(room_router, prefix="/api/v1/community")
    app.include_router(board_router, prefix="/api/v1/community")
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        enter_resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/study-room/enter")
        assert enter_resp.status_code == 200, enter_resp.text
        assert enter_resp.json()["reentered"] is False

        presence_resp = await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/study-room/presence")
        assert presence_resp.status_code == 200
        presence = presence_resp.json()
        assert presence["in_room_count"] == 1 and presence["member_count"] == 2

        board_resp = await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/leaderboard")
        assert board_resp.status_code == 200
        board = board_resp.json()
        assert board["self_view_only"] is True and board["total"] == 2, "<3 人自我视图标记"
        assert board["my_rank"] is not None

        beat_resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/study-room/heartbeat")
        assert beat_resp.status_code == 200 and beat_resp.json()["in_room"] is True

        exit_resp = await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/study-room/exit")
        assert exit_resp.status_code == 200
        payload = exit_resp.json()
        assert payload["already_out"] is False and payload["session_minutes"] == 0

        # 非成员：403
        current["user"] = outsider
        assert (await ac.post(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/study-room/enter")).status_code == 403
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/study-room/presence")).status_code == 403
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{squad.id}/leaderboard")).status_code == 403

        # 不存在/非小队：404（不泄露存在性）
        missing_id = uuid4()
        assert (await ac.post(f"{SQUAD_ROUTER_PREFIX}/{missing_id}/study-room/enter")).status_code == 404
        assert (await ac.get(f"{SQUAD_ROUTER_PREFIX}/{missing_id}/leaderboard")).status_code == 404
