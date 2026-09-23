"""共学自习室服务（D-COMM-4 · beacon 式在场证明，服务端 TTL 真源）。

复用裁决（vs 既有结构）：社群域**无** presence/session 类模型可复用——
``GroupMember.last_active_at`` 是成员级单时间戳（无会话边界、算不出时长）、
``models/focus.py::FocusSession`` 是个人番茄钟结算记录（写入即要求
end_time/duration_minutes，无群组归属）、``User.status`` 是全局在线状态
（非小队作用域）。故按设计卡 §3.3「落库最小记录」立最小新表
``study_room_sessions``（一条记录 = 一次进出场；迁移 dc4room_20260922
挂唯一 head）。小队与成员鉴权全部委托 D-COMM-3 的 SquadService
（Group(type=SPRINT) 场景门面），不复制第二套成员语义。

在场语义（ROOM-PRESENCE 修订：服务端 TTL 真源，读路径只认未过期）：
- **在场判定** = 开放会话（exited_at IS NULL）且 ``last_heartbeat_at``
  在 ``STUDY_ROOM_PRESENCE_TTL_SECONDS``（90s）内；TTL 过期 = 诚实离场
  （读路径惰性判定，无需后台清理任务）——杀进程/切后台后最多 TTL 内
  残留，过期后其他成员看到的是如实缺席，绝不造假在场；
- **续期信号 = 前台房间轮询**（详情屏可见 + app 前台时 30s 一拍心跳，
  移动端轻配合；绝不要求后台 Timer——前台 Timer 在 AppLifecycleState
  paused 即停，后台期间在场如实衰减）。备选否决：学习活动（语义最弱，
  在 A 队聊天不该续 B 队自习室在场，且要挂多个写路径不省）、WS 帧
  （自习室屏不持 WS，为此建连接更重）；
- 显式进出为主：enter 建档/续命、exit 立即清档；心跳端点是显式续期
  （房间 UI 发来的活性证明，对 decayed 开放记录也续命——不是自动重开，
  无开放会话时仍诚实上报不建档）；
- enter 撞上 decayed 开放会话：按模型定义的诚实离场时刻收档
  （exited_at = last_heartbeat_at + TTL），再建新记录重新进场——
  「一记录一进出场」历史不变，已证明的今日时长保留；
- 离开**不惩罚**（无 Forest 枯死机制）：时长如实记录，stale 会话不强制
  结算、不伪造用户发出的 exit；
- **时长诚实封顶**：会话计入终点不得晚于 ``last_heartbeat_at + TTL``
  （开放会话 decay 后今日累计不再虚增；显式退出的会话按退出前最后
  活性证明封顶，不把失联期算成自习时长）；
- 「今日累计」按成员本地日界（复用督促域时区惯例：push_preference.timezone
  默认 Asia/Shanghai，naive-UTC 存储）；跨日会话只计入今日重叠部分；
- 时长仅展示，**不进任何榜分**（小队榜口径唯一是 sprint 完成度，见
  community_squad_board_service.py；防「挂机刷时长」——设计卡 §3.3 风险条）。

红线：本模块不读 XP/经验/光子/榜单行为量（D20）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import _utcnow
from app.models.community import GroupMember
from app.models.study_room import StudyRoomSession
from app.models.user import PushPreference
from app.schemas.community_study_room import STUDY_ROOM_PRESENCE_TTL_SECONDS, StudyRoomPresenceEntry
from app.services.community_squad_service import SquadService

DEFAULT_USER_TIMEZONE = "Asia/Shanghai"


def _naive_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


async def get_user_timezone(db: AsyncSession, user_id: UUID) -> str:
    """成员本地时区（与 api/v1/accountability.py::_user_timezone 同一口径：
    push_preference.timezone，缺省/非法回落 Asia/Shanghai）。以直查
    PushPreference 实现而非 import：accountability 是 API 层模块（反向
    分层依赖），且其传递 import 图恰含 leaderboard_service——本卡红线
    钉死的禁入域，不把它拉进自习室的 import 闭包；直查同时避免 async
    会话里的关系惰性加载。
    """
    result = await db.execute(select(PushPreference.timezone).where(PushPreference.user_id == user_id))
    name = result.scalar_one_or_none() or DEFAULT_USER_TIMEZONE
    try:
        ZoneInfo(name)
    except Exception:
        return DEFAULT_USER_TIMEZONE
    return name


def local_day_window_utc(timezone_name: str, *, now: datetime) -> tuple[datetime, datetime]:
    """成员「今日」的 naive-UTC 窗口（镜像 accountability._day_range_for_timezone 的口径）。"""
    zone = ZoneInfo(timezone_name)
    now_local = now.replace(tzinfo=UTC).astimezone(zone)
    local_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = local_start.astimezone(UTC).replace(tzinfo=None)
    return start_utc, _naive_utc(now)


def overlap_minutes(start: datetime, end: datetime, window_start: datetime, window_end: datetime) -> int:
    """[start, end] 与 [window_start, window_end] 的重叠分钟数（地板取整，负重叠为 0）。"""
    s = max(_naive_utc(start), window_start)
    e = min(_naive_utc(end), window_end)
    return max(0, int((e - s).total_seconds() // 60))


def _is_alive(session: StudyRoomSession, now: datetime) -> bool:
    """TTL 在场判定：最后活性证明距今不超过 TTL（naive UTC 入参）。"""
    age = (_naive_utc(now) - _naive_utc(session.last_heartbeat_at)).total_seconds()
    return age <= STUDY_ROOM_PRESENCE_TTL_SECONDS


def _effective_end(session: StudyRoomSession, now: datetime) -> datetime:
    """会话的诚实计入终点：min(退出时刻或现在, 最后活性证明 + TTL)。

    开放会话 decay 后不再虚增时长；显式退出的会话按退出前最后活性证明
    封顶（失联期不算自习时长）。时钟回拨防御：终点不早于进入时刻。
    """
    wall_end = session.exited_at if session.exited_at is not None else _naive_utc(now)
    ttl_cap = _naive_utc(session.last_heartbeat_at) + timedelta(seconds=STUDY_ROOM_PRESENCE_TTL_SECONDS)
    return max(min(_naive_utc(wall_end), ttl_cap), _naive_utc(session.entered_at))


class StudyRoomService:
    """小队自习室：在场证明的进出/心跳/聚合门面（鉴权委托 SquadService）。"""

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    async def _squad_and_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember:
        """统一鉴权：小队须存在且为 SPRINT；请求者须在册成员（非成员 403）。"""
        await SquadService._get_active_squad(db, group_id)
        return await SquadService._require_active_member(db, group_id, user_id)

    @staticmethod
    async def _get_open_session(db: AsyncSession, group_id: UUID, user_id: UUID) -> StudyRoomSession | None:
        result = await db.execute(
            select(StudyRoomSession)
            .where(
                StudyRoomSession.group_id == group_id,
                StudyRoomSession.user_id == user_id,
                StudyRoomSession.exited_at.is_(None),
                StudyRoomSession.not_deleted_filter(),
            )
            .order_by(StudyRoomSession.entered_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _today_minutes_for(db: AsyncSession, group_id: UUID, user_id: UUID, *, now: datetime) -> int:
        """成员今日累计自习分钟数：所有与今日窗口重叠的会话求重叠部分。"""
        start_utc, end_utc = local_day_window_utc(await get_user_timezone(db, user_id), now=now)
        result = await db.execute(
            select(StudyRoomSession).where(
                StudyRoomSession.group_id == group_id,
                StudyRoomSession.user_id == user_id,
                StudyRoomSession.not_deleted_filter(),
                # 粗筛：会话开始于今日窗口结束后不可能重叠；在场的开放会话
                # （exited_at IS NULL）保留由重叠计算精确裁剪。
                StudyRoomSession.entered_at <= end_utc,
                (StudyRoomSession.exited_at.is_(None)) | (StudyRoomSession.exited_at >= start_utc),
            )
        )
        total = 0
        for session in result.scalars().all():
            # TTL 诚实封顶：decay 的开放会话停算于最后活性证明 + TTL，
            # 显式退出的会话停算于 min(退出时刻, 活性证明 + TTL)。
            end = _effective_end(session, now)
            total += overlap_minutes(session.entered_at, end, start_utc, end_utc)
        return total

    # ------------------------------------------------------------------
    # 进出/心跳（beacon：显式进出为主，TTL 过期=诚实离场）
    # ------------------------------------------------------------------
    @staticmethod
    async def enter_room(db: AsyncSession, group_id: UUID, user_id: UUID) -> dict:
        """进入自习室。幂等：命中 TTL 内的开放会话 → 刷新心跳原样返回（reentered=True）；
        撞上 decayed 开放会话 → 按诚实离场时刻收档并新建记录（reentered=False）。"""
        await StudyRoomService._squad_and_member(db, group_id, user_id)
        now = _utcnow()
        session = await StudyRoomService._get_open_session(db, group_id, user_id)
        reentered = False
        if session is not None and _is_alive(session, now):
            session.last_heartbeat_at = now
            reentered = True
        else:
            if session is not None:
                # decayed 开放记录：按模型定义的诚实离场时刻收档（最后一次
                # 活性证明 + TTL），已证明的时长保留在历史里、不虚报不丢失。
                session.exited_at = _effective_end(session, now)
            session = StudyRoomSession(
                group_id=group_id,
                user_id=user_id,
                entered_at=now,
                exited_at=None,
                last_heartbeat_at=now,
            )
            db.add(session)
        await db.flush()
        today_minutes = await StudyRoomService._today_minutes_for(db, group_id, user_id, now=now)
        return {
            "session_id": session.id,
            "group_id": group_id,
            "user_id": user_id,
            "entered_at": session.entered_at,
            "reentered": reentered,
            "today_minutes": today_minutes,
        }

    @staticmethod
    async def exit_room(db: AsyncSession, group_id: UUID, user_id: UUID) -> dict:
        """退出自习室。幂等诚实：无开放会话 → already_out=True（不报错、不造记录）。
        显式退出立即清档（含 decayed 记录的回收）；时长按退出前最后活性证明封顶。"""
        await StudyRoomService._squad_and_member(db, group_id, user_id)
        now = _utcnow()
        session = await StudyRoomService._get_open_session(db, group_id, user_id)
        if session is None:
            today_minutes = await StudyRoomService._today_minutes_for(db, group_id, user_id, now=now)
            return {
                "session_id": None,
                "exited_at": None,
                "session_minutes": 0,
                "already_out": True,
                "today_minutes": today_minutes,
            }
        # 防御：时钟回拨等极端情况下 exited_at 不得早于 entered_at；
        # 时长按退出前最后活性证明 + TTL 封顶（失联期不算自习时长）。
        entered_at = _naive_utc(session.entered_at)
        exited_at = max(_naive_utc(now), entered_at)
        session_minutes = overlap_minutes(entered_at, _effective_end(session, now), entered_at, exited_at)
        session.exited_at = exited_at
        session.last_heartbeat_at = exited_at
        await db.flush()
        today_minutes = await StudyRoomService._today_minutes_for(db, group_id, user_id, now=now)
        return {
            "session_id": session.id,
            "exited_at": session.exited_at,
            "session_minutes": session_minutes,
            "already_out": False,
            "today_minutes": today_minutes,
        }

    @staticmethod
    async def heartbeat(db: AsyncSession, group_id: UUID, user_id: UUID) -> dict:
        """续期信号（前台房间轮询/显式心跳）：有开放会话（含 decayed）即刷新
        last_heartbeat_at 续命并如实上报在场；无开放会话诚实上报（不自动重开）。"""
        await StudyRoomService._squad_and_member(db, group_id, user_id)
        now = _utcnow()
        session = await StudyRoomService._get_open_session(db, group_id, user_id)
        if session is None:
            return {"in_room": False, "last_heartbeat_at": None, "today_minutes": 0}
        session.last_heartbeat_at = now
        await db.flush()
        today_minutes = await StudyRoomService._today_minutes_for(db, group_id, user_id, now=now)
        return {"in_room": True, "last_heartbeat_at": session.last_heartbeat_at, "today_minutes": today_minutes}

    # ------------------------------------------------------------------
    # 在场聚合（谁在自习 + 今日累计时长；仅小队成员可见）
    # ------------------------------------------------------------------
    @staticmethod
    async def get_presence(db: AsyncSession, group_id: UUID, requester_id: UUID) -> dict:
        """小队在室视图：全部在册成员 + 各自在场状态与今日累计（非成员 403）。

        - in_room：开放会话且心跳在 TTL 内（TTL 过期=诚实离场，读路径只认
          未过期——杀进程/切后台后最多 TTL 内残留，过期如实判缺席）；
        - is_stale：有开放会话但 TTL 已过期（异常退出待回收的崩溃恢复线索）；
        - 「今日」按各成员本地日界（跨时区小队各自如实）；
        - 未入场成员照常列出（today_minutes=0）——如实记录、不缺席惩罚。
        """
        await StudyRoomService._squad_and_member(db, group_id, requester_id)
        now = _utcnow()

        result = await db.execute(
            select(GroupMember)
            .options(selectinload(GroupMember.user))
            .where(
                GroupMember.group_id == group_id,
                GroupMember.not_deleted_filter(),
            )
            .order_by(GroupMember.joined_at.asc())
        )
        members = list(result.scalars().all())

        entries: list[StudyRoomPresenceEntry] = []
        in_room_count = 0
        for member in members:
            user = member.user
            display_name = (user.nickname if user else None) or (user.username if user else None)
            session = await StudyRoomService._get_open_session(db, group_id, member.user_id)
            in_room = session is not None and _is_alive(session, now)
            # decayed 开放记录：不在场（诚实）但标 stale（崩溃恢复线索，
            # 下次显式 enter/exit 会回收该记录）。
            is_stale = session is not None and not in_room
            if in_room:
                in_room_count += 1
            today_minutes = await StudyRoomService._today_minutes_for(db, group_id, member.user_id, now=now)
            entries.append(
                StudyRoomPresenceEntry(
                    user_id=member.user_id,
                    display_name=display_name,
                    role=str(member.role.value),
                    in_room=in_room,
                    is_stale=is_stale,
                    entered_at=session.entered_at if in_room else None,
                    current_session_minutes=(
                        overlap_minutes(
                            session.entered_at,
                            _effective_end(session, now),
                            session.entered_at,
                            now,
                        )
                        if in_room
                        else 0
                    ),
                    today_minutes=today_minutes,
                )
            )

        return {
            "group_id": group_id,
            "member_count": len(members),
            "in_room_count": in_room_count,
            "generated_at": now,
            "members": entries,
        }
