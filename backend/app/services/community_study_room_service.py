"""共学自习室服务（D-COMM-4 · beacon 式在场证明，纯在场、零音视频）。

复用裁决（vs 既有结构）：社群域**无** presence/session 类模型可复用——
``GroupMember.last_active_at`` 是成员级单时间戳（无会话边界、算不出时长）、
``models/focus.py::FocusSession`` 是个人番茄钟结算记录（写入即要求
end_time/duration_minutes，无群组归属）、``User.status`` 是全局在线状态
（非小队作用域）。故按设计卡 §3.3「落库最小记录」立最小新表
``study_room_sessions``（一条记录 = 一次进出场；迁移 dc4room_20260922
挂唯一 head）。小队与成员鉴权全部委托 D-COMM-3 的 SquadService
（Group(type=SPRINT) 场景门面），不复制第二套成员语义。

在场语义（设计裁决逐条落地）：
- 显式进出为主（enter/exit），心跳只兜底崩溃恢复（陈旧仅标记 is_stale）；
- 离开**不惩罚**（无 Forest 枯死机制）：时长如实记录，stale 会话不强制
  结算、不伪造 exited_at；
- enter 幂等：已有开放会话（含 stale）→ 刷新心跳并原样返回，不建重复
  记录（sqlite 测试路径无部分唯一索引，幂等语义即唯一性保证）；
- 「今日累计」按成员本地日界（复用督促域时区惯例：push_preference.timezone
  默认 Asia/Shanghai，naive-UTC 存储）；跨日会话只计入今日重叠部分；
- 时长仅展示，**不进任何榜分**（小队榜口径唯一是 sprint 完成度，见
  community_squad_board_service.py；防「挂机刷时长」——设计卡 §3.3 风险条）。

红线：本模块不读 XP/经验/光子/榜单行为量（D20）。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import _utcnow
from app.models.community import GroupMember
from app.models.study_room import StudyRoomSession
from app.models.user import PushPreference
from app.schemas.community_study_room import STUDY_ROOM_STALE_MINUTES, StudyRoomPresenceEntry
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
            end = session.exited_at or now
            total += overlap_minutes(session.entered_at, end, start_utc, end_utc)
        return total

    # ------------------------------------------------------------------
    # 进出/心跳（beacon：显式进出为主，心跳兜底）
    # ------------------------------------------------------------------
    @staticmethod
    async def enter_room(db: AsyncSession, group_id: UUID, user_id: UUID) -> dict:
        """进入自习室。幂等：已有开放会话 → 刷新心跳并返回（reentered=True）。"""
        await StudyRoomService._squad_and_member(db, group_id, user_id)
        now = _utcnow()
        session = await StudyRoomService._get_open_session(db, group_id, user_id)
        reentered = session is not None
        if reentered:
            session.last_heartbeat_at = now  # type: ignore[union-attr]
        else:
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
        """退出自习室。幂等诚实：无开放会话 → already_out=True（不报错、不造记录）。"""
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
        # 防御：时钟回拨等极端情况下 exited_at 不得早于 entered_at。
        exited_at = max(_naive_utc(now), _naive_utc(session.entered_at))
        session.exited_at = exited_at
        session.last_heartbeat_at = exited_at
        await db.flush()
        today_minutes = await StudyRoomService._today_minutes_for(db, group_id, user_id, now=now)
        return {
            "session_id": session.id,
            "exited_at": session.exited_at,
            "session_minutes": int((exited_at - _naive_utc(session.entered_at)).total_seconds() // 60),
            "already_out": False,
            "today_minutes": today_minutes,
        }

    @staticmethod
    async def heartbeat(db: AsyncSession, group_id: UUID, user_id: UUID) -> dict:
        """心跳兜底：在场则刷新 last_heartbeat_at；不在场诚实上报（不自动重开）。"""
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

        - in_room：有开放会话；is_stale：在场但心跳超过 STUDY_ROOM_STALE_MINUTES；
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
            in_room = session is not None
            if in_room:
                in_room_count += 1
            is_stale = bool(
                in_room
                and (now - _naive_utc(session.last_heartbeat_at)).total_seconds() > STUDY_ROOM_STALE_MINUTES * 60
            )
            today_minutes = await StudyRoomService._today_minutes_for(db, group_id, member.user_id, now=now)
            entries.append(
                StudyRoomPresenceEntry(
                    user_id=member.user_id,
                    display_name=display_name,
                    role=str(member.role.value),
                    in_room=in_room,
                    is_stale=is_stale,
                    entered_at=session.entered_at if session else None,
                    current_session_minutes=(
                        overlap_minutes(session.entered_at, now, session.entered_at, now) if session else 0
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
