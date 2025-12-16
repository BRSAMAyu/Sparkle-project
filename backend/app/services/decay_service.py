"""
遗忘衰减服务 (Decay Service)
实现艾宾浩斯遗忘曲线，让知识点随时间逐渐暗淡
"""
import math
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import UserNodeStatus, KnowledgeNode


class DecayService:
    """
    遗忘曲线衰减服务

    基于艾宾浩斯遗忘曲线：
    Retention = e^(-t/S)
    其中 t 为时间间隔，S 为记忆稳定性 (与掌握度相关)
    """

    # 衰减参数
    BASE_HALF_LIFE_DAYS = 7.0  # 基础半衰期 (天)
    MIN_MASTERY = 5.0  # 最低掌握度 (不会降到 0)
    DECAY_CHECK_INTERVAL = 1  # 检查间隔 (天)

    # 掌握度阈值
    THRESHOLD_DIM = 20.0  # 低于此值星星变暗
    THRESHOLD_COLLAPSE = 10.0  # 低于此值可能坍缩

    def __init__(self, db: AsyncSession):
        self.db = db

    async def apply_daily_decay(self) -> Dict[str, int]:
        """
        每日遗忘衰减任务

        Returns:
            dict: 衰减统计 {processed: int, dimmed: int, collapsed: int}
        """
        stats = {'processed': 0, 'dimmed': 0, 'collapsed': 0}
        now = datetime.utcnow()

        # 1. 查询需要衰减的节点状态
        # 条件：已解锁 + 未暂停衰减 + 上次学习超过 1 天
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.is_unlocked == True,
                UserNodeStatus.decay_paused == False,
                UserNodeStatus.last_study_at < now - timedelta(days=self.DECAY_CHECK_INTERVAL),
                UserNodeStatus.mastery_score > self.MIN_MASTERY
            )
        )

        result = await self.db.execute(query)
        statuses = result.scalars().all()

        # 2. 逐个应用衰减
        for status in statuses:
            old_mastery = status.mastery_score

            # 计算衰减
            days_elapsed = (now - status.last_study_at).days
            new_mastery = self._calculate_decay(
                current_mastery=status.mastery_score,
                days_elapsed=days_elapsed
            )

            # 更新状态
            status.mastery_score = new_mastery
            stats['processed'] += 1

            # 检查状态变化
            if old_mastery >= self.THRESHOLD_DIM > new_mastery:
                stats['dimmed'] += 1

            if new_mastery < self.THRESHOLD_COLLAPSE and not status.is_collapsed:
                # 标记坍缩风险 (但不自动坍缩)
                stats['collapsed'] += 1

        await self.db.commit()

        return stats

    def _calculate_decay(self, current_mastery: float, days_elapsed: int) -> float:
        """
        计算衰减后的掌握度

        使用修改的艾宾浩斯公式：
        - 高掌握度节点衰减更慢 (更稳定的记忆)
        - 最低不会降到 MIN_MASTERY
        """
        # 动态半衰期：掌握度越高，半衰期越长
        stability_factor = 1 + (current_mastery / 100) * 2  # 1-3 倍
        effective_half_life = self.BASE_HALF_LIFE_DAYS * stability_factor

        # 指数衰减
        decay_rate = math.log(2) / effective_half_life
        retention = math.exp(-decay_rate * days_elapsed)

        # 计算新掌握度
        decayed_mastery = current_mastery * retention

        return max(decayed_mastery, self.MIN_MASTERY)

    async def get_review_suggestions(self, user_id: UUID, limit: int = 5) -> List[Dict]:
        """
        获取复习建议

        Returns:
            List[dict]: 建议复习的知识点列表
        """
        now = datetime.utcnow()

        query = (
            select(UserNodeStatus, KnowledgeNode)
            .join(KnowledgeNode, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    UserNodeStatus.is_unlocked == True,
                    UserNodeStatus.next_review_at <= now
                )
            )
            .order_by(UserNodeStatus.mastery_score.asc())  # 优先复习低掌握度
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        suggestions = []
        for status, node in rows:
            # 获取星域信息
            sector_code = 'VOID'
            if node.subject:
                sector_code = node.subject.sector_code

            suggestions.append({
                'node_id': node.id,
                'node_name': node.name,
                'sector_code': sector_code,
                'current_mastery': status.mastery_score,
                'days_since_study': (now - status.last_study_at).days if status.last_study_at else 0,
                'urgency': 'high' if status.mastery_score < self.THRESHOLD_DIM else 'normal'
            })

        return suggestions

    async def pause_decay(self, user_id: UUID, node_id: UUID, pause: bool = True):
        """暂停/恢复特定节点的衰减"""
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        result = await self.db.execute(query)
        status = result.scalar_one_or_none()

        if status:
            status.decay_paused = pause
            await self.db.commit()

    async def get_decay_stats(self, user_id: UUID) -> Dict[str, any]:
        """
        获取用户的衰减统计信息

        Returns:
            dict: 包含需要复习的节点数、暗淡节点数等
        """
        now = datetime.utcnow()

        # 统计需要复习的节点
        review_query = select(func.count()).select_from(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.is_unlocked == True,
                UserNodeStatus.next_review_at <= now
            )
        )
        review_result = await self.db.execute(review_query)
        review_count = review_result.scalar() or 0

        # 统计暗淡节点
        dim_query = select(func.count()).select_from(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.is_unlocked == True,
                UserNodeStatus.mastery_score < self.THRESHOLD_DIM
            )
        )
        dim_result = await self.db.execute(dim_query)
        dim_count = dim_result.scalar() or 0

        # 统计坍缩风险节点
        collapse_query = select(func.count()).select_from(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.is_unlocked == True,
                UserNodeStatus.mastery_score < self.THRESHOLD_COLLAPSE
            )
        )
        collapse_result = await self.db.execute(collapse_query)
        collapse_count = collapse_result.scalar() or 0

        return {
            'review_due_count': review_count,
            'dim_nodes_count': dim_count,
            'collapse_risk_count': collapse_count
        }
