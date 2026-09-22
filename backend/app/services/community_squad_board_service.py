"""小队榜服务（D-COMM-4 · 冲刺完成度口径，排序 + 分页包装）。

**零新口径裁决**：榜分唯一消费 D-COMM-3 的完成度聚合面
``SquadService.get_squad_sprint_progress``（其口径唯一来自
sprint_task_ledger，BP-4 单一事实源）。本服务只做：
1. 排序（完成率降序 → 完成数降序 → 有账本者优先 → user_id 定序）；
2. 并列名次（排序键全同同名次）+ percentile 区间（完成度严格更低者占比，
   D21「默认展示区间而非赤裸名次」）；
3. 分页包装（limit/offset，名次在全集上计算后再切片）；
4. <3 人降级（设计裁决：小队不足 SQUAD_MIN_MEMBERS 人榜单不成立，
   board_valid=False / self_view_only=True，客户端切自我锚）。

红线（D20 防刷）：不读 XP/经验/光子/榜单行为量——时长（自习室在场）
同样禁入榜分，本模块连 study_room 模型都不 import。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.community_squad import SQUAD_MIN_MEMBERS, SquadMemberSprintProgress
from app.schemas.community_squad_board import LeaderboardEntry, SquadLeaderboardResponse
from app.services.community_squad_service import SquadService

# 分页上限：小队本身 3-8 人（SquadCreate 收敛），默认值已覆盖全集；
# 上限只作 API 形状防御，不做业务语义。
BOARD_DEFAULT_LIMIT = 50
BOARD_MAX_LIMIT = 100


def _sort_key(member: SquadMemberSprintProgress) -> tuple[float, int, bool, str]:
    # 完成率降序、完成数降序、有账本者优先（空数据诚实标记不与 0 完成率混排）、
    # user_id 升序保证确定性（UUID 转字符串定序即可）。
    return (-member.completion_rate, -member.task_completed, not member.has_ledger_data, str(member.user_id))


def _score(member: SquadMemberSprintProgress) -> tuple[float, int]:
    """未取反的完成度口径（percentile 的「严格更低」比较基准）。"""
    return (member.completion_rate, member.task_completed)


class SquadBoardService:
    """小队榜：D-COMM-3 聚合面的只读视图包装（零第二套口径）。"""

    @staticmethod
    async def get_squad_leaderboard(
        db: AsyncSession,
        group_id: UUID,
        requester_id: UUID,
        *,
        limit: int = BOARD_DEFAULT_LIMIT,
        offset: int = 0,
    ) -> SquadLeaderboardResponse:
        limit = max(1, min(int(limit), BOARD_MAX_LIMIT))
        offset = max(0, int(offset))

        # SSOT：聚合（含鉴权：非成员 SquadPermissionError → API 403；
        # 小队不存在/非 SPRINT → SquadNotFoundError → 404）全部委托 D-COMM-3。
        progress = await SquadService.get_squad_sprint_progress(db, group_id, requester_id)
        members: list[SquadMemberSprintProgress] = list(progress["members"])
        member_count = len(members)

        ordered = sorted(members, key=_sort_key)

        # 并列名次：完成度口径（完成率/完成数/有账本）全同 → 同名次（竞赛
        # 排名 1,1,3；user_id 仅作确定性排序，不参与并列判定）；
        # percentile = 完成度严格低于该成员的队员占比（区间展示，D21）。
        entries: list[LeaderboardEntry] = []
        ranks: dict[UUID, int] = {}
        for position, member in enumerate(ordered):
            rank = position + 1
            ranks[member.user_id] = rank
            if entries and _sort_key(member)[:3] == _sort_key(ordered[position - 1])[:3]:
                rank = entries[-1].rank
                ranks[member.user_id] = rank
            strictly_behind = sum(1 for other in ordered if _score(other) < _score(member))
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    user_id=member.user_id,
                    display_name=member.display_name,
                    role=member.role,
                    task_total=member.task_total,
                    task_completed=member.task_completed,
                    completion_rate=member.completion_rate,
                    has_ledger_data=member.has_ledger_data,
                    percentile=round(100 * strictly_behind / member_count) if member_count else 0,
                    stats=member.stats,
                )
            )

        board_valid = member_count >= SQUAD_MIN_MEMBERS
        return SquadLeaderboardResponse(
            squad_id=progress["squad_id"],
            member_count=member_count,
            sprint_active=progress["sprint_active"],
            board_valid=board_valid,
            self_view_only=not board_valid,
            generated_at=progress["generated_at"],
            my_rank=ranks.get(requester_id),
            total=member_count,
            limit=limit,
            offset=offset,
            entries=entries[offset : offset + limit],
        )
