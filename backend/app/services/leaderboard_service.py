"""
排行榜服务
Leaderboard Service

支持多种类型的排行榜：
- GLOBAL: 全局综合排行榜
- FRIENDS: 好友排行榜
- GROUP: 群组排行榜
- SUBJECT: 学科排行榜
- WEEKLY: 本周学习排行榜
- STREAK: 连胜排行榜
- GROUP_FLAME: 群组火苗榜
"""
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta, date
from loguru import logger

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, case, literal_column

from app.schemas.leaderboard import (
    LeaderboardType,
    LeaderboardPeriod,
    LeaderboardEntry,
    GroupLeaderboardEntry,
    LeaderboardResponse,
    GroupLeaderboardResponse,
    LeaderboardRequest,
    MyRankResponse,
    LeaderboardSummary
)
from app.models.user import User
from app.models.community import (
    Friendship, FriendshipStatus,
    Group, GroupMember, GroupType
)
from app.models.achievement import UserStreakStats, UserAchievement
from app.models.galaxy import UserNodeStatus, KnowledgeNode


class LeaderboardService:
    """
    排行榜服务

    综合分数公式：
    全局排行 = 知识点数×1.0 + 打卡天数×0.5 + 成就数×2.0 + 最长连胜×1.5

    更新策略：
    - 实时计算（带缓存）
    - 定期快照保存
    """

    # 综合分数权重
    WEIGHT_KNOWLEDGE_NODES = 1.0
    WEIGHT_STUDY_DAYS = 0.5
    WEIGHT_ACHIEVEMENTS = 2.0
    WEIGHT_STREAK = 1.5

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """
        获取排行榜

        Args:
            request: 排行榜查询请求
            current_user_id: 当前用户ID

        Returns:
            LeaderboardResponse: 排行榜响应
        """
        if request.type == LeaderboardType.GLOBAL:
            return await self._get_global_leaderboard(request, current_user_id)
        elif request.type == LeaderboardType.FRIENDS:
            return await self._get_friends_leaderboard(request, current_user_id)
        elif request.type == LeaderboardType.GROUP:
            return await self._get_group_leaderboard(request, current_user_id)
        elif request.type == LeaderboardType.SUBJECT:
            return await self._get_subject_leaderboard(request, current_user_id)
        elif request.type == LeaderboardType.WEEKLY:
            return await self._get_weekly_leaderboard(request, current_user_id)
        elif request.type == LeaderboardType.STREAK:
            return await self._get_streak_leaderboard(request, current_user_id)
        else:
            return await self._get_global_leaderboard(request, current_user_id)

    async def get_my_rank(
        self,
        user_id: UUID,
        leaderboard_type: LeaderboardType,
        period: LeaderboardPeriod = LeaderboardPeriod.ALL_TIME
    ) -> MyRankResponse:
        """
        获取我的排名

        Args:
            user_id: 用户ID
            leaderboard_type: 排行榜类型
            period: 统计周期

        Returns:
            MyRankResponse: 我的排名响应
        """
        request = LeaderboardRequest(
            type=leaderboard_type,
            period=period,
            limit=1000  # 获取更多以计算排名
        )

        full_leaderboard = await self.get_leaderboard(request, user_id)

        # 查找我的排名
        my_entry = next(
            (e for e in full_leaderboard.entries if e.user_id == user_id),
            None
        )

        if not my_entry:
            return MyRankResponse(
                rank=0,
                score=0,
                score_label="0分",
                total_participants=full_leaderboard.total_participants,
                percentile=0,
                nearby_users=[]
            )

        # 获取附近用户
        my_idx = full_leaderboard.entries.index(my_entry)
        start = max(0, my_idx - 2)
        end = min(len(full_leaderboard.entries), my_idx + 3)
        nearby_users = full_leaderboard.entries[start:end]

        return MyRankResponse(
            rank=my_entry.rank,
            score=my_entry.score,
            score_label=my_entry.score_label,
            total_participants=full_leaderboard.total_participants,
            percentile=1.0 - (my_entry.rank / full_leaderboard.total_participants),
            nearby_users=nearby_users
        )

    async def get_summary(
        self,
        user_id: UUID
    ) -> LeaderboardSummary:
        """
        获取排行榜摘要

        Args:
            user_id: 用户ID

        Returns:
            LeaderboardSummary: 排行榜摘要
        """
        # 并发获取各类排行榜
        global_board, *_ = await self._get_global_leaderboard(
            LeaderboardRequest(type=LeaderboardType.GLOBAL, limit=10),
            user_id
        )
        friends_board, *_ = await self._get_friends_leaderboard(
            LeaderboardRequest(type=LeaderboardType.FRIENDS, limit=10),
            user_id
        )
        weekly_board, *_ = await self._get_weekly_leaderboard(
            LeaderboardRequest(type=LeaderboardType.WEEKLY, limit=10),
            user_id
        )
        streak_board, *_ = await self._get_streak_leaderboard(
            LeaderboardRequest(type=LeaderboardType.STREAK, limit=10),
            user_id
        )

        # 获取我的统计
        my_stats = await self._get_my_stats(user_id)

        return LeaderboardSummary(
            global=global_board,
            friends=friends_board,
            weekly=weekly_board,
            streak=streak_board,
            my_stats=my_stats
        )

    # ==================== 具体排行榜实现 ====================

    async def _get_global_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """全局综合排行榜"""
        # 计算综合分数
        # 全局排行 = 知识点数×1.0 + 打卡天数×0.5 + 成就数×2.0 + 最长连胜×1.5
        query = select(
            User.id,
            User.username,
            User.avatar_url,
            func.count(UserNodeStatus.id).label('node_count'),
            func.count(UserAchievement.id).label('achievement_count'),
            func.coalesce(UserStreakStats.longest_streak, 0).label('streak'),
            func.coalesce(UserStreakStats.total_checkin_days, 0).label('study_days')
        ).outerjoin(
            UserNodeStatus, and_(
                UserNodeStatus.user_id == User.id,
                UserNodeStatus.mastery_score >= 50  # 掌握度>=50%
            )
        ).outerjoin(
            UserAchievement, UserAchievement.user_id == User.id
        ).outerjoin(
            UserStreakStats, UserStreakStats.user_id == User.id
        ).where(
            User.is_active == True,
            User.not_deleted_filter()
        ).group_by(User.id, UserStreakStats.longest_streak, UserStreakStats.total_checkin_days)

        result = await self.db.execute(query)
        rows = result.all()

        # 计算分数并排序
        scored_users = []
        for row in rows:
            score = (
                row.node_count * self.WEIGHT_KNOWLEDGE_NODES +
                row.study_days * self.WEIGHT_STUDY_DAYS +
                row.achievement_count * self.WEIGHT_ACHIEVEMENTS +
                row.streak * self.WEIGHT_STREAK
            )
            scored_users.append((row, score))

        scored_users.sort(key=lambda x: x[1], reverse=True)

        # 构建排行榜条目
        entries = []
        for rank, (user_row, score) in enumerate(scored_users[:request.limit], 1):
            is_me = user_row.id == current_user_id

            entry = LeaderboardEntry(
                rank=rank,
                user_id=user_row.id,
                username=user_row.username,
                avatar_url=user_row.avatar_url,
                score=score,
                score_label=f"{int(score)}分",
                is_me=is_me,
                stats={
                    "knowledge_nodes": user_row.node_count,
                    "achievements": user_row.achievement_count,
                    "streak": user_row.streak,
                    "study_days": user_row.study_days
                },
                badge=self._get_badge_for_rank(rank)
            )
            entries.append(entry)

        # 获取我的排名
        my_rank = next(
            (i + 1 for i, (user_row, _) in enumerate(scored_users) if user_row.id == current_user_id),
            None
        )
        my_score = next(
            (score for user_row, score in scored_users if user_row.id == current_user_id),
            None
        )

        return LeaderboardResponse(
            type=LeaderboardType.GLOBAL,
            title="全局综合榜",
            entries=entries,
            my_rank=my_rank,
            my_score=my_score,
            last_updated=datetime.utcnow(),
            total_participants=len(scored_users),
            period=request.period
        )

    async def _get_friends_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """好友排行榜"""
        # 获取好友列表
        friends_query = select(Friendship).where(
            or_(
                Friendship.user_id == current_user_id,
                Friendship.friend_id == current_user_id
            ),
            Friendship.status == FriendshipStatus.ACCEPTED,
            Friendship.not_deleted_filter()
        )
        friends_result = await self.db.execute(friends_query)
        friends = friends_result.scalars().all()

        friend_ids = set()
        for f in friends:
            if f.user_id == current_user_id:
                friend_ids.add(f.friend_id)
            else:
                friend_ids.add(f.user_id)

        # 添加自己
        friend_ids.add(current_user_id)

        # 查询好友的学习数据
        query = select(
            User.id,
            User.username,
            User.avatar_url,
            func.count(UserNodeStatus.id).label('node_count'),
            func.count(UserAchievement.id).label('achievement_count'),
            func.coalesce(UserStreakStats.current_streak, 0).label('streak')
        ).outerjoin(
            UserNodeStatus, and_(
                UserNodeStatus.user_id == User.id,
                UserNodeStatus.mastery_score >= 50
            )
        ).outerjoin(
            UserAchievement, UserAchievement.user_id == User.id
        ).outerjoin(
            UserStreakStats, UserStreakStats.user_id == User.id
        ).where(
            User.id.in_(friend_ids),
            User.is_active == True,
            User.not_deleted_filter()
        ).group_by(User.id, UserStreakStats.current_streak)

        result = await self.db.execute(query)
        rows = result.all()

        # 计算分数
        scored_users = []
        for row in rows:
            score = (
                row.node_count * self.WEIGHT_KNOWLEDGE_NODES +
                row.achievement_count * self.WEIGHT_ACHIEVEMENTS +
                row.streak * self.WEIGHT_STREAK
            )
            scored_users.append((row, score))

        scored_users.sort(key=lambda x: x[1], reverse=True)

        # 构建条目
        entries = []
        for rank, (user_row, score) in enumerate(scored_users[:request.limit], 1):
            is_me = user_row.id == current_user_id

            entry = LeaderboardEntry(
                rank=rank,
                user_id=user_row.id,
                username=user_row.username,
                avatar_url=user_row.avatar_url,
                score=score,
                score_label=f"{int(score)}分",
                is_me=is_me,
                stats={
                    "knowledge_nodes": user_row.node_count,
                    "achievements": user_row.achievement_count,
                    "streak": user_row.streak
                },
                badge=self._get_badge_for_rank(rank)
            )
            entries.append(entry)

        my_rank = next(
            (i + 1 for i, (user_row, _) in enumerate(scored_users) if user_row.id == current_user_id),
            None
        )
        my_score = next(
            (score for user_row, score in scored_users if user_row.id == current_user_id),
            None
        )

        return LeaderboardResponse(
            type=LeaderboardType.FRIENDS,
            title="好友榜",
            entries=entries,
            my_rank=my_rank,
            my_score=my_score,
            last_updated=datetime.utcnow(),
            total_participants=len(scored_users),
            period=request.period
        )

    async def _get_group_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """群组排行榜"""
        if not request.group_id:
            # 返回用户所在的所有群组排行
            return await self._get_my_groups_leaderboard(request, current_user_id)

        # 获取群组成员
        members_query = select(GroupMember).where(
            GroupMember.group_id == request.group_id,
            GroupMember.not_deleted_filter()
        )
        members_result = await self.db.execute(members_query)
        members = members_result.scalars().all()

        member_ids = [m.user_id for m in members]

        # 基于火焰贡献值排序
        query = select(User).where(
            User.id.in_(member_ids),
            User.is_active == True
        ).options(
            selectinload(GroupMember)  # 需要加载成员信息获取 flame_contribution
        )

        result = await self.db.execute(query)
        users = result.scalars().all()

        # 获取成员的火焰贡献
        member_contributions = {m.user_id: m.flame_contribution for m in members}

        # 排序
        sorted_users = sorted(
            users,
            key=lambda u: member_contributions.get(u.id, 0),
            reverse=True
        )

        # 构建条目
        entries = []
        for rank, user in enumerate(sorted_users[:request.limit], 1):
            flame = member_contributions.get(user.id, 0)

            entry = LeaderboardEntry(
                rank=rank,
                user_id=user.id,
                username=user.username,
                avatar_url=user.avatar_url,
                score=float(flame),
                score_label=f"{flame}🔥",
                is_me=user.id == current_user_id,
                stats={"flame_contribution": flame},
                badge=self._get_badge_for_rank(rank)
            )
            entries.append(entry)

        my_rank = next(
            (i + 1 for i, user in enumerate(sorted_users) if user.id == current_user_id),
            None
        )
        my_score = member_contributions.get(current_user_id, 0)

        return LeaderboardResponse(
            type=LeaderboardType.GROUP,
            title="群组榜",
            entries=entries,
            my_rank=my_rank,
            my_score=float(my_score),
            last_updated=datetime.utcnow(),
            total_participants=len(sorted_users),
            period=request.period
        )

    async def _get_subject_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """学科排行榜"""
        subject_id = request.subject_id

        # 获取学科信息
        subject = await self.db.get(KnowledgeNode, subject_id)
        subject_name = subject.name if subject else "学科"

        # 查询该学科下的用户掌握情况
        query = select(
            User.id,
            User.username,
            User.avatar_url,
            func.count(UserNodeStatus.id).label('mastered_nodes'),
            func.avg(UserNodeStatus.mastery_score).label('avg_mastery')
        ).join(
            UserNodeStatus, UserNodeStatus.user_id == User.id
        ).join(
            KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id
        ).where(
            KnowledgeNode.subject_id == subject_id,
            UserNodeStatus.mastery_score >= 50,
            User.is_active == True,
            User.not_deleted_filter()
        ).group_by(User.id)

        result = await self.db.execute(query)
        rows = result.all()

        # 计算分数：掌握节点数 * 平均掌握度
        scored_users = []
        for row in rows:
            score = row.mastered_nodes * (row.avg_mastery / 100.0) * 100
            scored_users.append((row, score))

        scored_users.sort(key=lambda x: x[1], reverse=True)

        # 构建条目
        entries = []
        for rank, (user_row, score) in enumerate(scored_users[:request.limit], 1):
            is_me = user_row.id == current_user_id

            entry = LeaderboardEntry(
                rank=rank,
                user_id=user_row.id,
                username=user_row.username,
                avatar_url=user_row.avatar_url,
                score=score,
                score_label=f"{int(score)}分",
                is_me=is_me,
                stats={
                    "mastered_nodes": user_row.mastered_nodes,
                    "avg_mastery": float(user_row.avg_mastery) if user_row.avg_mastery else 0
                },
                badge=self._get_badge_for_rank(rank)
            )
            entries.append(entry)

        my_rank = next(
            (i + 1 for i, (user_row, _) in enumerate(scored_users) if user_row.id == current_user_id),
            None
        )
        my_score = next(
            (score for user_row, score in scored_users if user_row.id == current_user_id),
            None
        )

        return LeaderboardResponse(
            type=LeaderboardType.SUBJECT,
            title=f"{subject_name}榜",
            entries=entries,
            my_rank=my_rank,
            my_score=my_score,
            last_updated=datetime.utcnow(),
            total_participants=len(scored_users),
            period=request.period
        )

    async def _get_weekly_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """本周学习排行榜"""
        # 计算本周时间范围
        today = date.today()
        week_start = datetime(today.year, today.month, today.day - today.weekday())
        week_end = week_start + timedelta(days=7)

        # 查询本周活跃用户的学习数据
        # 这里简化处理，实际应该从学习记录表统计
        query = select(
            User.id,
            User.username,
            User.avatar_url,
            func.count(UserNodeStatus.id).label('nodes_this_week')
        ).join(
            UserNodeStatus, UserNodeStatus.user_id == User.id
        ).where(
            User.is_active == True,
            User.not_deleted_filter(),
            UserNodeStatus.last_study_at >= week_start,
            UserNodeStatus.last_study_at < week_end
        ).group_by(User.id)

        result = await self.db.execute(query)
        rows = result.all()

        # 按本周学习节点数排序
        scored_users = [(row, row.nodes_this_week) for row in rows]
        scored_users.sort(key=lambda x: x[1], reverse=True)

        # 构建条目
        entries = []
        for rank, (user_row, score) in enumerate(scored_users[:request.limit], 1):
            is_me = user_row.id == current_user_id

            entry = LeaderboardEntry(
                rank=rank,
                user_id=user_row.id,
                username=user_row.username,
                avatar_url=user_row.avatar_url,
                score=float(score),
                score_label=f"{score}个知识点",
                is_me=is_me,
                stats={"nodes_this_week": score},
                badge=self._get_badge_for_rank(rank)
            )
            entries.append(entry)

        my_rank = next(
            (i + 1 for i, (user_row, _) in enumerate(scored_users) if user_row.id == current_user_id),
            None
        )
        my_score = next(
            (score for user_row, score in scored_users if user_row.id == current_user_id),
            None
        )

        return LeaderboardResponse(
            type=LeaderboardType.WEEKLY,
            title="本周学习榜",
            entries=entries,
            my_rank=my_rank,
            my_score=float(my_score) if my_score else None,
            last_updated=datetime.utcnow(),
            total_participants=len(scored_users),
            period=request.period
        )

    async def _get_streak_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """连胜排行榜"""
        query = select(
            User.id,
            User.username,
            User.avatar_url,
            UserStreakStats.current_streak,
            UserStreakStats.max_streak,
            UserStreakStats.longest_streak
        ).join(
            UserStreakStats, UserStreakStats.user_id == User.id
        ).where(
            User.is_active == True,
            User.not_deleted_filter(),
            UserStreakStats.current_streak > 0
        ).order_by(desc(UserStreakStats.current_streak))

        result = await self.db.execute(query)
        rows = result.all()

        # 构建条目
        entries = []
        for rank, user_row in enumerate(rows[:request.limit], 1):
            is_me = user_row.id == current_user_id

            entry = LeaderboardEntry(
                rank=rank,
                user_id=user_row.id,
                username=user_row.username,
                avatar_url=user_row.avatar_url,
                score=float(user_row.current_streak),
                score_label=f"{user_row.current_streak}天",
                is_me=is_me,
                stats={
                    "current_streak": user_row.current_streak,
                    "max_streak": user_row.max_streak,
                    "longest_streak": user_row.longest_streak
                },
                badge=self._get_badge_for_rank(rank)
            )
            entries.append(entry)

        # 查找我的排名
        my_rank = next(
            (i + 1 for i, user_row in enumerate(rows) if user_row.id == current_user_id),
            None
        )

        # 获取我的连胜数据
        my_streak = await self.db.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == current_user_id)
        )
        my_streak_row = my_streak.scalar_one_or_none()
        my_score = my_streak_row.current_streak if my_streak_row else 0

        return LeaderboardResponse(
            type=LeaderboardType.STREAK,
            title="连胜榜",
            entries=entries,
            my_rank=my_rank,
            my_score=float(my_score),
            last_updated=datetime.utcnow(),
            total_participants=len(rows),
            period=request.period
        )

    # ==================== 辅助方法 ====================

    def _get_badge_for_rank(self, rank: int) -> Optional[str]:
        """获取排名徽章"""
        if rank == 1:
            return "🥇"
        elif rank == 2:
            return "🥈"
        elif rank == 3:
            return "🥉"
        return None

    async def _get_my_stats(self, user_id: UUID) -> Dict[str, Any]:
        """获取我的统计信息"""
        # 获取知识点数
        nodes_query = select(func.count(UserNodeStatus.id)).where(
            UserNodeStatus.user_id == user_id,
            UserNodeStatus.mastery_score >= 50
        )
        nodes_result = await self.db.execute(nodes_query)
        node_count = nodes_result.scalar() or 0

        # 获取成就数
        achievements_query = select(func.count(UserAchievement.id)).where(
            UserAchievement.user_id == user_id,
            UserAchievement.unlocked_at.isnot(None)
        )
        achievements_result = await self.db.execute(achievements_query)
        achievement_count = achievements_result.scalar() or 0

        # 获取连胜数据
        streak_row = await self.db.execute(
            select(UserStreakStats).where(UserStreakStats.user_id == user_id)
        )
        streak_data = streak_row.scalar_one_or_none()

        return {
            "knowledge_nodes": node_count,
            "achievements": achievement_count,
            "current_streak": streak_data.current_streak if streak_data else 0,
            "max_streak": streak_data.max_streak if streak_data else 0,
            "longest_streak": streak_data.longest_streak if streak_data else 0
        }

    async def _get_my_groups_leaderboard(
        self,
        request: LeaderboardRequest,
        current_user_id: UUID
    ) -> LeaderboardResponse:
        """获取我所在的所有群组排行"""
        # 获取用户所在的群组
        memberships_query = select(GroupMember).where(
            GroupMember.user_id == current_user_id,
            GroupMember.not_deleted_filter()
        )
        memberships_result = await self.db.execute(memberships_query)
        memberships = memberships_result.scalars().all()

        group_ids = [m.group_id for m in memberships]

        # 获取群组信息并排序
        groups_query = select(Group).where(
            Group.id.in_(group_ids),
            Group.not_deleted_filter()
        ).order_by(desc(Group.total_flame_power))

        groups_result = await self.db.execute(groups_query)
        groups = groups_result.scalars().all()

        # 为群组榜创建特殊条目
        entries = []
        for rank, group in enumerate(groups[:request.limit], 1):
            entries.append(LeaderboardEntry(
                rank=rank,
                user_id=group.id,  # 这里用 group_id
                username=group.name,
                avatar_url=group.avatar_url,
                score=float(group.total_flame_power),
                score_label=f"{group.total_flame_power}🔥",
                is_me=False,
                stats={
                    "member_count": 0,  # 需要单独查询
                    "total_flame_power": group.total_flame_power
                }
            ))

        return LeaderboardResponse(
            type=LeaderboardType.GROUP,
            title="我的群组",
            entries=entries,
            my_rank=None,
            my_score=None,
            last_updated=datetime.utcnow(),
            total_participants=len(groups),
            period=request.period
        )


# 便捷函数
async def get_leaderboard(
    db: AsyncSession,
    user_id: UUID,
    leaderboard_type: LeaderboardType = LeaderboardType.GLOBAL,
    limit: int = 50
) -> LeaderboardResponse:
    """获取排行榜的便捷函数"""
    service = LeaderboardService(db)
    request = LeaderboardRequest(
        type=leaderboard_type,
        limit=limit
    )
    return await service.get_leaderboard(request, user_id)
