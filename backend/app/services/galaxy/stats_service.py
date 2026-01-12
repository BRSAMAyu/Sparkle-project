from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus, StudyRecord, NodeRelation
from app.services.expansion_service import ExpansionService
from app.schemas.galaxy import SparkResult, SparkEvent, GalaxyUserStats, SectorCode, NodeWithStatus
from app.core.cache import cache_service
from app.config import settings

class GalaxyStatsService:
    # 掌握度计算常量
    BASE_MASTERY_POINTS = 5.0
    MAX_MASTERY = 100.0

    def __init__(self, db: AsyncSession):
        self.db = db
        self.expansion_service = ExpansionService(db)

    async def spark_node(
        self,
        user_id: UUID,
        node_id: UUID,
        study_minutes: int,
        task_id: Optional[UUID] = None,
        trigger_expansion: bool = True
    ) -> SparkResult:
        """
        点亮/增强知识点 (任务完成时调用)
        """
        # 1. 获取或创建用户节点状态
        status = await self._get_or_create_status(user_id, node_id)

        # 2. 计算掌握度增量
        node = await self.db.get(KnowledgeNode, node_id)
        mastery_delta = self._calculate_mastery_delta(study_minutes, node.importance_level)

        # 3. 记录旧状态
        old_mastery = status.mastery_score
        is_first_unlock = not status.is_unlocked

        # 4. 更新状态
        status.mastery_score = min(status.mastery_score + mastery_delta, self.MAX_MASTERY)
        status.total_study_minutes += study_minutes
        status.study_count += 1
        status.last_study_at = datetime.utcnow()
        status.is_unlocked = True

        if is_first_unlock:
            status.first_unlock_at = datetime.utcnow()

        # 计算下次复习时间
        status.next_review_at = self._calculate_next_review(status.mastery_score)

        # 5. 记录学习历史
        record = StudyRecord(
            user_id=user_id,
            node_id=node_id,
            task_id=task_id,
            study_minutes=study_minutes,
            mastery_delta=mastery_delta,
            record_type='task_complete'
        )
        self.db.add(record)

        await self.db.commit()

        # 6. 获取星域信息
        sector_code = 'VOID'
        if node.subject:
            sector_code = node.subject.sector_code

        # 7. 生成动画事件
        try:
            sector_enum = SectorCode(sector_code)
        except ValueError:
            sector_enum = SectorCode.VOID

        spark_event = SparkEvent(
            node_id=node_id,
            node_name=node.name,
            sector_code=sector_enum,
            old_mastery=old_mastery,
            new_mastery=status.mastery_score,
            is_first_unlock=is_first_unlock,
            is_level_up=self._check_level_up(old_mastery, status.mastery_score)
        )

        # 8. 触发 LLM 拓展 (异步)
        expansion_queued = False
        if trigger_expansion and status.study_count >= 2:  # 学习 2 次后开始拓展
            expansion_queued = await self.expansion_service.queue_expansion(
                trigger_node_id=node_id,
                trigger_task_id=task_id,
                user_id=user_id
            )

        # 9. Invalidate Cache
        pattern = f"{settings.APP_NAME}:view:get_galaxy_graph:{user_id}:*"
        await cache_service.delete_pattern(pattern)

        return SparkResult(
            spark_event=spark_event,
            expansion_queued=expansion_queued,
            updated_status=status
        )

    async def calculate_user_stats(self, user_id: UUID) -> GalaxyUserStats:
        """计算用户统计数据"""
        query = (
            select(
                func.count().filter(UserNodeStatus.is_unlocked == True).label('unlocked_count'),
                func.count().filter(UserNodeStatus.mastery_score >= 80).label('mastered_count'),
                func.sum(UserNodeStatus.total_study_minutes).label('total_minutes')
            )
            .where(UserNodeStatus.user_id == user_id)
        )
        result = await self.db.execute(query)
        row = result.one()

        total_query = select(func.count()).select_from(KnowledgeNode)
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        return GalaxyUserStats(
            total_nodes=total_count,
            unlocked_count=row.unlocked_count or 0,
            mastered_count=row.mastered_count or 0,
            total_study_minutes=int(row.total_minutes or 0),
            sector_distribution={},
            streak_days=0
        )

    async def predict_next_node(self, user_id: UUID) -> Optional[NodeWithStatus]:
        """
        预测下一个最佳学习节点
        """
        stmt = (
            select(UserNodeStatus)
            .where(UserNodeStatus.user_id == user_id)
            .order_by(UserNodeStatus.last_study_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        last_status = result.scalar_one_or_none()

        target_node_id = None

        if last_status:
            relations_query = (
                select(NodeRelation)
                .where(NodeRelation.source_node_id == last_status.node_id)
                .order_by(NodeRelation.strength.desc())
            )
            rel_result = await self.db.execute(relations_query)
            relations = rel_result.scalars().all()

            best_candidate = None
            best_score = -1.0

            for rel in relations:
                target_status = await self._get_user_status(user_id, rel.target_node_id)
                
                score = 0.0
                if not target_status or not target_status.is_unlocked:
                    score = 10.0
                elif target_status.mastery_score < 80:
                    score = 5.0 + (100 - target_status.mastery_score) / 10.0
                else:
                    continue

                score *= rel.strength
                
                if score > best_score:
                    best_score = score
                    best_candidate = rel.target_node_id
            
            target_node_id = best_candidate

        if not target_node_id:
            fallback_query = (
                select(KnowledgeNode)
                .where(KnowledgeNode.importance_level >= 4)
                .limit(10)
            )
            fallback_result = await self.db.execute(fallback_query)
            candidates = fallback_result.scalars().all()
            
            for node in candidates:
                st = await self._get_user_status(user_id, node.id)
                if not st or st.mastery_score < 90:
                    target_node_id = node.id
                    break

        if target_node_id:
            node = await self.db.get(KnowledgeNode, target_node_id)
            status = await self._get_user_status(user_id, target_node_id)
            return NodeWithStatus.from_models(node, status)
        
        return None

    async def get_heatmap_data(self, user_id: UUID) -> List[dict]:
        """
        Phase 4.2: Get Heatmap Data for MiniMap.
        Returns list of {x, y, intensity} based on decay/review status.
        Intensity: 1.0 = Urgent Review (Red), 0.0 = Fresh (Green/Invisible).
        Requires x,y coordinates from KnowledgeNode.
        """
        stmt = (
            select(KnowledgeNode.position_x, KnowledgeNode.position_y, UserNodeStatus.next_review_at, UserNodeStatus.mastery_score)
            .join(UserNodeStatus, KnowledgeNode.id == UserNodeStatus.node_id)
            .where(
                and_(
                    UserNodeStatus.user_id == user_id,
                    KnowledgeNode.position_x.isnot(None),
                    UserNodeStatus.is_unlocked == True
                )
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        heatmap = []
        now = datetime.utcnow()
        
        for px, py, next_review, mastery in rows:
            intensity = 0.0
            if next_review:
                if now >= next_review:
                    # Overdue: High intensity
                    intensity = 1.0
                else:
                    # Approaching: 0.0 to 1.0
                    delta = (next_review - now).total_seconds() / 3600 # hours
                    if delta < 24:
                        intensity = 0.5
            
            # Low mastery also adds to "heat" (needs attention)
            if mastery < 50:
                intensity = max(intensity, 0.3)
                
            if intensity > 0:
                heatmap.append({
                    "x": px,
                    "y": py,
                    "intensity": intensity
                })
                
        return heatmap

    # --- Helpers ---
    def _calculate_mastery_delta(self, study_minutes: int, importance_level: int) -> float:
        time_factor = min(study_minutes / 30.0, 2.0)
        difficulty_factor = 1 + (importance_level - 1) * 0.1
        return self.BASE_MASTERY_POINTS * time_factor * difficulty_factor

    def _check_level_up(self, old_mastery: float, new_mastery: float) -> bool:
        thresholds = [30, 60, 80, 95]
        for threshold in thresholds:
            if old_mastery < threshold <= new_mastery:
                return True
        return False

    def _calculate_next_review(self, mastery_score: float) -> datetime:
        if mastery_score >= 80: days = 14
        elif mastery_score >= 60: days = 7
        elif mastery_score >= 30: days = 3
        else: days = 1
        return datetime.utcnow() + timedelta(days=days)

    async def _get_or_create_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        result = await self.db.execute(query)
        status = result.scalar_one_or_none()

        if not status:
            status = UserNodeStatus(user_id=user_id, node_id=node_id)
            self.db.add(status)
            await self.db.flush()

        return status

    async def _get_user_status(self, user_id: UUID, node_id: UUID) -> Optional[UserNodeStatus]:
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
