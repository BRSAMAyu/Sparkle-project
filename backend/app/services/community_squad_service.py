"""冲刺小队服务（D-COMM-3 · 社群×exam_sprint 首联动）。

复用裁决（vs 新表）：小队 = 既有 Group(type=SPRINT)。模型层
``models/community.py::GroupType.SPRINT`` 与 deadline/sprint_goal 字段、
PG 基线迁移（cc9383c4c29f，grouptype 枚举含 'SPRINT'）均早已存在——社群
设计与 schema（GroupTypeEnum.SPRINT）同已支持。因此**不建新表、零迁移**；
本服务只做冲刺场景约束（3-8 人、deadline 必填、仅冲刺周期可见/可加入）
与跨用户聚合，群组通用行为（软删、成员上限、角色惯例、群主转让语义）
一律委托 GroupService，不复制第二套群组逻辑。

完成度口径（防刷红线，D20）：每成员完成率唯一来自
``sprint_task_ledger.fetch_sprint_ledger_tasks`` + ``build_ledger_task_stats``
（sprint-completion 单一事实源，BP-4 裁决：禁止消费面自写第二套聚合）。
本模块**禁止**读取 XP/经验/光子/榜单行为量——它们可被刷，完成度只认任务
账本；tests/unit/test_community_squad_mvp.py 以源码导入扫描 + 行为双断言
钉死该边界。

隐私（设计卡验收②）：成员列表与完成度聚合仅小队成员可见（非成员
SquadPermissionError → API 403）；小队本身仅冲刺周期内可见/可加入
（deadline 已过即关闭，list/join 双向拦）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import _utcnow
from app.models.community import Group, GroupMember, GroupRole, GroupType
from app.schemas.community import GroupCreate
from app.schemas.community_squad import (
    SQUAD_MAX_MEMBERS,
    SQUAD_MIN_MEMBERS,
    SquadCreate,
    SquadMemberSprintProgress,
)
from app.services.community_service import GroupService
from app.services.sprint_task_ledger import build_ledger_task_stats, fetch_sprint_ledger_tasks


class SquadNotFoundError(LookupError):
    """小队不存在，或目标群组不是冲刺小队（统一 404，不泄露存在性）。"""


class SquadPermissionError(PermissionError):
    """请求者不是该小队的在册成员（API 层映射 403）。"""


class SquadStateError(ValueError):
    """小队状态不允许该操作（已满/冲刺周期已结束/群主不能直接退出等，API 层映射 400）。"""


def sprint_period_active(group: Group, *, now: datetime | None = None) -> bool:
    """冲刺周期是否仍然开放（deadline 未过）。deadline 缺失按开放处理（防御）。"""
    deadline = group.deadline
    if deadline is None:
        return True
    if deadline.tzinfo is not None:
        deadline = deadline.replace(tzinfo=None)
    return deadline >= (now or _utcnow())


class SquadService:
    """冲刺小队：复用 Group(type=SPRINT) 的场景化门面。"""

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    @staticmethod
    async def _get_active_squad(db: AsyncSession, group_id: UUID) -> Group:
        """取一个存活的冲刺小队；群组不存在、已软删或非 SPRINT 类型一律同错。"""
        group = await Group.get_by_id(db, group_id)
        if not group or group.is_deleted or group.type != GroupType.SPRINT:
            raise SquadNotFoundError("冲刺小队不存在")
        return group

    @staticmethod
    async def _require_active_member(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember:
        member = await GroupService._get_active_member(db, group_id, user_id)
        if not member:
            raise SquadPermissionError("仅小队成员可见")
        return member

    @staticmethod
    async def _member_count(db: AsyncSession, group_id: UUID) -> int:
        result = await db.execute(
            select(func.count(GroupMember.id)).where(
                GroupMember.group_id == group_id,
                GroupMember.not_deleted_filter(),
            )
        )
        return int(result.scalar() or 0)

    @staticmethod
    def _days_remaining(group: Group, *, now: datetime | None = None) -> int | None:
        if group.deadline is None:
            return None
        deadline = group.deadline.replace(tzinfo=None) if group.deadline.tzinfo else group.deadline
        return max(0, (deadline - (now or _utcnow())).days)

    # ------------------------------------------------------------------
    # CRUD（创建/加入/退出走 GroupService 既有惯例）
    # ------------------------------------------------------------------
    @staticmethod
    async def create_squad(db: AsyncSession, creator_id: UUID, data: SquadCreate) -> Group:
        """创建冲刺小队：type 固定 SPRINT，人数上限收敛到 3-8，创建者为群主。"""
        if not (SQUAD_MIN_MEMBERS <= data.max_members <= SQUAD_MAX_MEMBERS):
            raise SquadStateError(f"小队人数上限须在 {SQUAD_MIN_MEMBERS}-{SQUAD_MAX_MEMBERS} 人之间")
        group_create = GroupCreate(
            name=data.name,
            description=data.description,
            type=GroupType.SPRINT,
            focus_tags=data.focus_tags,
            deadline=data.deadline,
            sprint_goal=data.sprint_goal,
            max_members=data.max_members,
            is_public=data.is_public,
            # MVP：小队直接加入，不开审批流（社群既有字段默认 False，保持一致）
            join_requires_approval=False,
        )
        return await GroupService.create_group(db, creator_id, group_create)

    @staticmethod
    async def get_squad(db: AsyncSession, group_id: UUID, user_id: UUID) -> dict[str, Any]:
        """小队详情：公开小队对登录用户可见，私密小队仅成员可见。"""
        group = await SquadService._get_active_squad(db, group_id)
        my_role: GroupRole | None = None
        member = await GroupService._get_active_member(db, group_id, user_id)
        if member:
            my_role = member.role
        elif not group.is_public:
            raise SquadPermissionError("仅小队成员可见")

        return {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "focus_tags": group.focus_tags or [],
            "deadline": group.deadline,
            "sprint_goal": group.sprint_goal,
            "max_members": group.max_members,
            "is_public": group.is_public,
            "member_count": await SquadService._member_count(db, group_id),
            "days_remaining": SquadService._days_remaining(group),
            "my_role": str(my_role.value) if my_role else None,
            "created_at": group.created_at,
        }

    @staticmethod
    async def list_my_squads(db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
        """「我的小队」列表——仅冲刺周期内可见（deadline 已过即从列表消失）。"""
        result = await db.execute(
            select(Group, GroupMember)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(
                GroupMember.user_id == user_id,
                GroupMember.not_deleted_filter(),
                Group.not_deleted_filter(),
                Group.type == GroupType.SPRINT,
            )
            .order_by(Group.deadline.asc())
        )
        squads: list[dict[str, Any]] = []
        now = _utcnow()
        for group, membership in result.all():
            if not sprint_period_active(group, now=now):
                continue
            squads.append(
                {
                    "id": group.id,
                    "name": group.name,
                    "sprint_goal": group.sprint_goal,
                    "deadline": group.deadline,
                    "days_remaining": SquadService._days_remaining(group, now=now),
                    "member_count": await SquadService._member_count(db, group.id),
                    "max_members": group.max_members,
                    "my_role": str(membership.role.value),
                }
            )
        return squads

    @staticmethod
    async def join_squad(db: AsyncSession, group_id: UUID, user_id: UUID) -> GroupMember:
        """加入小队：仅冲刺周期内；人数上限（3-8）由 GroupService.join_group 既有锁语义执行。"""
        group = await SquadService._get_active_squad(db, group_id)
        if not sprint_period_active(group):
            raise SquadStateError("冲刺周期已结束，小队不再接受加入")
        try:
            return await GroupService.join_group(db, group_id, user_id)
        except ValueError as exc:
            # 群组已满 / 已是成员等既有语义原样上抛（API 400）
            raise SquadStateError(str(exc)) from exc

    @staticmethod
    async def leave_squad(db: AsyncSession, group_id: UUID, user_id: UUID) -> bool:
        """退出小队：软删成员记录（社群既有惯例）；群主须先转让（既有语义）。"""
        await SquadService._get_active_squad(db, group_id)
        try:
            return await GroupService.leave_group(db, group_id, user_id)
        except ValueError as exc:
            raise SquadStateError(str(exc)) from exc

    @staticmethod
    async def get_squad_members(db: AsyncSession, group_id: UUID, requester_id: UUID) -> list[GroupMember]:
        """成员列表：仅小队成员可见（复用 GroupService 既有排序与鉴权）。"""
        await SquadService._get_active_squad(db, group_id)
        await SquadService._require_active_member(db, group_id, requester_id)
        return await GroupService.get_group_members(db, group_id, requester_id)

    # ------------------------------------------------------------------
    # 冲刺完成度聚合（本卡核心新面：跨用户只读，口径唯一来自 sprint_task_ledger）
    # ------------------------------------------------------------------
    @staticmethod
    async def get_squad_sprint_progress(db: AsyncSession, group_id: UUID, requester_id: UUID) -> dict[str, Any]:
        """每成员的当前 sprint 完成率（sprint-completion 口径）。

        - 鉴权：仅小队成员（非成员 SquadPermissionError → 403）；
        - 口径：fetch_sprint_ledger_tasks + build_ledger_task_stats（BP-4
          单一事实源），账本 = 该成员全部未删除任务，completed = 其中
          status==COMPLETED；跨 plan 与无 plan 挂靠任务全可见；
        - 红线：不读 XP/经验/光子/榜单行为量（D20）；
        - 空数据诚实：账本为空的成员 total=0/rate=0.0/has_ledger_data=False。
        """
        group = await SquadService._get_active_squad(db, group_id)
        await SquadService._require_active_member(db, group_id, requester_id)

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

        progress: list[SquadMemberSprintProgress] = []
        for member in members:
            ledger = await fetch_sprint_ledger_tasks(db, user_id=member.user_id)
            stats = build_ledger_task_stats(ledger)
            user = member.user
            display_name = (user.nickname if user else None) or (user.username if user else None)
            progress.append(
                SquadMemberSprintProgress(
                    user_id=member.user_id,
                    display_name=display_name,
                    role=str(member.role.value),
                    task_total=stats.total,
                    task_completed=stats.completed,
                    completion_rate=stats.completion_rate,
                    has_ledger_data=stats.total > 0,
                    stats=stats,
                )
            )

        return {
            "squad_id": group.id,
            "member_count": len(members),
            "sprint_active": sprint_period_active(group),
            "generated_at": _utcnow(),
            "members": progress,
        }
