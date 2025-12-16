"""
知识星图核心服务 (Galaxy Service)
处理星图数据、节点点亮、语义搜索等核心功能
"""
from uuid import UUID
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.galaxy import KnowledgeNode, UserNodeStatus, NodeRelation, StudyRecord
from app.models.subject import Subject
from app.services.embedding_service import embedding_service
from app.services.expansion_service import ExpansionService
from app.schemas.galaxy import (
    GalaxyGraphResponse, NodeWithStatus, SparkEvent,
    SparkResult, SearchResultItem, GalaxyUserStats,
    NodeRelationInfo
)


class GalaxyService:
    """知识星图核心服务"""

    # 掌握度计算常量
    BASE_MASTERY_POINTS = 5.0
    MAX_MASTERY = 100.0

    # 遗忘曲线常量 (艾宾浩斯)
    MEMORY_HALF_LIFE_DAYS = 7.0  # 记忆半衰期
    DECAY_THRESHOLD = 10.0  # 低于此值星星变暗

    def __init__(self, db: AsyncSession):
        self.db = db
        self.expansion_service = ExpansionService(db)

    # ==========================================
    # 1. 获取星图数据
    # ==========================================
    async def get_galaxy_graph(
        self,
        user_id: UUID,
        sector_code: Optional[str] = None,
        include_locked: bool = True
    ) -> GalaxyGraphResponse:
        """
        获取用户的知识星图数据

        Args:
            user_id: 用户 ID
            sector_code: 可选，筛选特定星域
            include_locked: 是否包含未解锁的节点

        Returns:
            GalaxyGraphResponse: 包含节点、关系、用户状态的完整星图数据
        """
        # 1. 查询知识节点 (带用户状态)
        query = (
            select(KnowledgeNode, UserNodeStatus)
            .outerjoin(
                UserNodeStatus,
                and_(
                    UserNodeStatus.node_id == KnowledgeNode.id,
                    UserNodeStatus.user_id == user_id
                )
            )
            .outerjoin(Subject, KnowledgeNode.subject_id == Subject.id)
        )

        if sector_code:
            query = query.where(Subject.sector_code == sector_code)

        result = await self.db.execute(query)
        nodes_with_status = result.all()

        # 2. 过滤未解锁节点 (如果需要)
        if not include_locked:
            nodes_with_status = [
                (node, status) for node, status in nodes_with_status
                if status and status.is_unlocked
            ]

        # 3. 查询节点关系
        node_ids = [node.id for node, _ in nodes_with_status]
        if node_ids:
            relations_query = select(NodeRelation).where(
                and_(
                    NodeRelation.source_node_id.in_(node_ids),
                    NodeRelation.target_node_id.in_(node_ids)
                )
            )
            relations_result = await self.db.execute(relations_query)
            relations = relations_result.scalars().all()
        else:
            relations = []

        # 4. 组装响应
        return GalaxyGraphResponse(
            nodes=[
                NodeWithStatus.from_models(node, status)
                for node, status in nodes_with_status
            ],
            relations=[
                NodeRelationInfo(
                    source_node_id=rel.source_node_id,
                    target_node_id=rel.target_node_id,
                    relation_type=rel.relation_type,
                    strength=rel.strength
                )
                for rel in relations
            ],
            user_stats=await self._calculate_user_stats(user_id)
        )

    # ==========================================
    # 2. 点亮知识点 (Spark)
    # ==========================================
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

        Args:
            user_id: 用户 ID
            node_id: 知识节点 ID
            study_minutes: 学习时长 (分钟)
            task_id: 关联的任务 ID
            trigger_expansion: 是否触发 LLM 拓展

        Returns:
            SparkResult: 包含动画事件和拓展状态
        """
        # 1. 获取或创建用户节点状态
        status = await self._get_or_create_status(user_id, node_id)

        # 2. 计算掌握度增量
        node = await self.db.get(KnowledgeNode, node_id)
        mastery_delta = self._calculate_mastery_delta(study_minutes, node.importance_level)

        # 3. 记录旧状态 (用于判断是否首次点亮/升级)
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
        from app.schemas.galaxy import SectorCode
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

        return SparkResult(
            spark_event=spark_event,
            expansion_queued=expansion_queued,
            updated_status=status
        )

    # ==========================================
    # 3. 语义搜索
    # ==========================================
    async def semantic_search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 10,
        threshold: float = 0.3
    ) -> List[SearchResultItem]:
        """
        使用向量相似度搜索知识点

        Args:
            user_id: 用户 ID
            query: 搜索查询
            limit: 返回数量限制
            threshold: 相似度阈值 (越小越严格)

        Returns:
            List[SearchResultItem]: 匹配的知识点列表
        """
        # 1. 获取查询向量
        query_embedding = await embedding_service.get_embedding(query)

        # 2. 向量搜索 (使用 pgvector)
        from pgvector.sqlalchemy import Vector

        search_query = (
            select(
                KnowledgeNode,
                KnowledgeNode.embedding.cosine_distance(query_embedding).label('distance')
            )
            .where(KnowledgeNode.embedding.isnot(None))
            .order_by('distance')
            .limit(limit)
        )

        result = await self.db.execute(search_query)
        matches = result.all()

        # 3. 过滤并格式化结果
        search_results = []
        for node, distance in matches:
            if distance <= threshold:
                user_status = await self._get_user_status(user_id, node.id)

                from app.schemas.galaxy import NodeBase, UserStatusInfo

                # 构建 NodeBase
                sector_code_str = node.subject.sector_code if node.subject else 'VOID'
                from app.schemas.galaxy import SectorCode
                try:
                    sector_enum = SectorCode(sector_code_str)
                except ValueError:
                    sector_enum = SectorCode.VOID

                node_base = NodeBase(
                    id=node.id,
                    name=node.name,
                    name_en=node.name_en,
                    description=node.description,
                    importance_level=node.importance_level,
                    sector_code=sector_enum,
                    is_seed=node.is_seed
                )

                # 构建 UserStatusInfo
                user_status_info = None
                if user_status:
                    from app.schemas.galaxy import NodeStatus
                    visual_status = self._calculate_visual_status(user_status)
                    brightness = self._calculate_brightness(user_status)

                    user_status_info = UserStatusInfo(
                        mastery_score=user_status.mastery_score,
                        total_study_minutes=user_status.total_study_minutes,
                        study_count=user_status.study_count,
                        is_unlocked=user_status.is_unlocked,
                        is_collapsed=user_status.is_collapsed,
                        is_favorite=user_status.is_favorite,
                        last_study_at=user_status.last_study_at,
                        next_review_at=user_status.next_review_at,
                        decay_paused=user_status.decay_paused,
                        status=visual_status,
                        brightness=brightness
                    )

                search_results.append(SearchResultItem(
                    node=node_base,
                    similarity=1 - distance,  # 转换为相似度
                    user_status=user_status_info
                ))

        return search_results

    # ==========================================
    # 4. 任务自动归类
    # ==========================================
    async def auto_classify_task(
        self,
        task_title: str,
        task_description: Optional[str] = None
    ) -> Optional[UUID]:
        """
        根据任务标题自动匹配知识点

        Args:
            task_title: 任务标题
            task_description: 任务描述 (可选)

        Returns:
            Optional[UUID]: 匹配的知识节点 ID，无匹配返回 None
        """
        # 1. 构建搜索文本
        search_text = task_title
        if task_description:
            search_text += f" {task_description}"

        # 2. 尝试向量匹配
        try:
            embedding = await embedding_service.get_embedding(search_text)

            from pgvector.sqlalchemy import Vector

            query = (
                select(KnowledgeNode.id)
                .where(KnowledgeNode.embedding.isnot(None))
                .order_by(KnowledgeNode.embedding.cosine_distance(embedding))
                .limit(1)
            )

            result = await self.db.execute(query)
            node_id = result.scalar_one_or_none()

            return node_id

        except Exception as e:
            # 降级：关键词匹配
            return await self._fallback_keyword_match(search_text)

    async def _fallback_keyword_match(self, text: str) -> Optional[UUID]:
        """关键词匹配降级策略"""
        # 简化版本：直接通过名称模糊匹配
        keywords = text.split()
        if not keywords:
            return None

        query = (
            select(KnowledgeNode.id)
            .where(KnowledgeNode.name.ilike(f"%{keywords[0]}%"))
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ==========================================
    # 5. 私有辅助方法
    # ==========================================
    def _calculate_mastery_delta(self, study_minutes: int, importance_level: int) -> float:
        """计算掌握度增量"""
        # 基础分 * 时间系数 * 难度系数
        time_factor = min(study_minutes / 30.0, 2.0)  # 30 分钟为标准，最多 2 倍
        difficulty_factor = 1 + (importance_level - 1) * 0.1  # 重要性越高，增长越多

        return self.BASE_MASTERY_POINTS * time_factor * difficulty_factor

    def _check_level_up(self, old_mastery: float, new_mastery: float) -> bool:
        """检查是否升级 (跨越等级阈值)"""
        thresholds = [30, 60, 80, 95]  # 等级阈值
        for threshold in thresholds:
            if old_mastery < threshold <= new_mastery:
                return True
        return False

    def _calculate_next_review(self, mastery_score: float) -> datetime:
        """根据掌握度计算下次复习时间"""
        # 掌握度越高，复习间隔越长
        if mastery_score >= 80:
            days = 14
        elif mastery_score >= 60:
            days = 7
        elif mastery_score >= 30:
            days = 3
        else:
            days = 1

        return datetime.utcnow() + timedelta(days=days)

    async def _get_or_create_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
        """获取或创建用户节点状态"""
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
        """获取用户节点状态"""
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _calculate_user_stats(self, user_id: UUID) -> GalaxyUserStats:
        """计算用户统计数据"""
        # 统计各状态节点数量
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

        # 统计总节点数
        total_query = select(func.count()).select_from(KnowledgeNode)
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        return GalaxyUserStats(
            total_nodes=total_count,
            unlocked_count=row.unlocked_count or 0,
            mastered_count=row.mastered_count or 0,
            total_study_minutes=int(row.total_minutes or 0),
            sector_distribution={},  # 可以添加更详细的统计
            streak_days=0  # 可以添加连续学习天数计算
        )

    def _calculate_visual_status(self, status: UserNodeStatus):
        """计算视觉状态"""
        from app.schemas.galaxy import NodeStatus

        if status.is_collapsed:
            return NodeStatus.COLLAPSED
        if not status.is_unlocked:
            return NodeStatus.LOCKED

        score = status.mastery_score
        if score >= 95:
            return NodeStatus.MASTERED
        elif score >= 80:
            return NodeStatus.BRILLIANT
        elif score >= 30:
            return NodeStatus.SHINING
        elif score > 0:
            return NodeStatus.GLIMMER
        else:
            return NodeStatus.UNLIT

    def _calculate_brightness(self, status: UserNodeStatus) -> float:
        """计算亮度"""
        if not status.is_unlocked:
            return 0.2
        if status.is_collapsed:
            return 0.1
        return 0.3 + (status.mastery_score / 100.0) * 0.7
