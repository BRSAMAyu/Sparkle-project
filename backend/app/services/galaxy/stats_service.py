from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.event_bus import event_bus
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.schemas.galaxy import GalaxyUserStats, NodeWithStatus, SectorCode, SparkEvent, SparkResult, UserStatusInfo
from app.services.expansion_service import ExpansionService
from app.services.node_sector_service import dominant_sector_from_weights, resolve_sector_weights


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
        task_id: UUID | None = None,
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
        status.last_study_at = _utcnow()
        status.is_unlocked = True

        if is_first_unlock:
            status.first_unlock_at = _utcnow()

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

        # 5.1. Audit log (align with update_node_mastery pipeline)
        try:
            from sqlalchemy import text as sa_text
            await self.db.execute(
                sa_text(
                    "INSERT INTO mastery_audit_log (node_id, user_id, old_mastery, new_mastery, reason, request_id, revision) "
                    "VALUES (:node_id, :user_id, :old_mastery, :new_mastery, :reason, :request_id, :revision)"
                ),
                {
                    "node_id": node_id,
                    "user_id": user_id,
                    "old_mastery": int(old_mastery),
                    "new_mastery": int(status.mastery_score),
                    "reason": "task_complete",
                    "request_id": str(task_id) if task_id else None,
                    "revision": getattr(status, "revision", 0),
                },
            )
            await self.db.commit()
        except Exception as e:
            logger.warning(f"Failed to write mastery audit log for spark_node: {e}")

        # 5.2. Outbox event (align with update_node_mastery pipeline)
        try:
            await self._write_spark_outbox_event(
                user_id=user_id,
                node_id=node_id,
                new_mastery=int(status.mastery_score),
                revision=getattr(status, "revision", 0),
            )
        except Exception as e:
            logger.warning(f"Failed to write spark outbox event: {e}")

        # 5.5. 发布掌握度更新事件
        try:
            from app.core.event_bus import NodeMasteryUpdatedEvent
            await event_bus.publish(
                "node_mastery_updated",
                NodeMasteryUpdatedEvent(
                    user_id=str(user_id),
                    node_id=str(node_id),
                    old_mastery=int(old_mastery),
                    new_mastery=int(status.mastery_score),
                    reason="task_complete"
                ).to_dict()
            )
        except Exception as e:
            logger.warning(f"Failed to publish mastery update event: {e}")

        # 6. 获取星域信息
        sector_code = dominant_sector_from_weights(resolve_sector_weights(node)).value

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

        # ========== Achievement Integration ==========
        try:
            from app.services.achievement_engine import AchievementEngine, AchievementEvent

            achievement_engine = AchievementEngine(self.db)

            # Node unlock event
            await achievement_engine.process_event(
                user_id=str(user_id),
                event_type=AchievementEvent.NODE_UNLOCKED,
                node_id=str(node_id),
                mastery_score=status.mastery_score,
                study_minutes=study_minutes,
            )

            # Node mastered event (when mastery reaches 80%+)
            if status.mastery_score >= 80:
                await achievement_engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.NODE_MASTERED,
                    node_id=str(node_id),
                    mastery_score=status.mastery_score,
                )

            # Perfectionist achievement (100% mastery) — use HIDDEN_TRIGGER so
            # AchievementEventConsumer._handle_node_updated can reach PERFECTIONIST
            if status.mastery_score >= 100:
                await achievement_engine.process_event(
                    user_id=str(user_id),
                    event_type=AchievementEvent.HIDDEN_TRIGGER,
                    node_id=str(node_id),
                    mastery_score=status.mastery_score,
                    hidden_trigger_code="PERFECTIONIST",
                )
        except Exception as e:
            logger.warning(f"Achievement processing failed in spark_node: {e}")
        # ============================================

        # ========== WebSocket Streaming Integration ==========
        try:
            from app.services.galaxy.streaming_service import get_galaxy_streaming_service
            streaming_service = get_galaxy_streaming_service()

            if streaming_service:
                # 如果有升级，发送升级通知
                if spark_event.is_level_up:
                    old_level = int(old_mastery // 10)
                    new_level = int(status.mastery_score // 10)
                    await streaming_service.broadcast_level_up(
                        user_id=user_id,
                        node_id=node_id,
                        old_level=old_level,
                        new_level=new_level
                    )

                # 如果是首次解锁，发送解锁通知
                if is_first_unlock:
                    await streaming_service.broadcast_node_unlocked(
                        user_id=user_id,
                        node_id=node_id,
                        node_name=node.name
                    )

                # 发送掌握度更新
                await streaming_service.broadcast_mastery_update(
                    user_id=user_id,
                    node_id=node_id,
                    old_mastery=int(old_mastery),
                    new_mastery=int(status.mastery_score),
                    reason="task_complete"
                )
        except Exception as e:
            logger.warning(f"WebSocket streaming failed in spark_node: {e}")
        # ============================================

        updated_status = UserStatusInfo(
            mastery_score=status.mastery_score,
            total_study_minutes=status.total_study_minutes,
            study_count=status.study_count,
            is_unlocked=status.is_unlocked,
            is_collapsed=status.is_collapsed,
            is_favorite=status.is_favorite,
            first_unlock_at=status.first_unlock_at,
            last_study_at=status.last_study_at,
            next_review_at=status.next_review_at,
            decay_paused=status.decay_paused,
            status=NodeWithStatus._calculate_status(status),
            brightness=NodeWithStatus._calculate_brightness(status),
        )

        return SparkResult(
            spark_event=spark_event,
            expansion_queued=expansion_queued,
            updated_status=updated_status,
        )

    async def calculate_user_stats(self, user_id: UUID) -> GalaxyUserStats:
        """计算用户统计数据"""
        query = (
            select(
                func.count().filter(UserNodeStatus.is_unlocked).label('unlocked_count'),
                func.count().filter(UserNodeStatus.mastery_score >= 80).label('mastered_count'),
                func.sum(UserNodeStatus.total_study_minutes).label('total_minutes')
            )
            .join(KnowledgeNode, KnowledgeNode.id == UserNodeStatus.node_id)
            .where(UserNodeStatus.user_id == user_id)
            .where((KnowledgeNode.status.is_(None)) | (KnowledgeNode.status == "published"))
        )
        result = await self.db.execute(query)
        row = result.one()

        total_query = (
            select(func.count())
            .select_from(KnowledgeNode)
            .where((KnowledgeNode.status.is_(None)) | (KnowledgeNode.status == "published"))
        )
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

    async def predict_next_node(self, user_id: UUID) -> NodeWithStatus | None:
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
            from sqlalchemy import or_
            relations_query = (
                select(NodeRelation)
                .where(or_(
                    NodeRelation.source_node_id == last_status.node_id,
                    NodeRelation.target_node_id == last_status.node_id
                ))
                .order_by(NodeRelation.strength.desc())
            )
            rel_result = await self.db.execute(relations_query)
            relations = rel_result.scalars().all()

            best_candidate = None
            best_score = -1.0

            for rel in relations:
                # Bidirectional: if current node is source, target is candidate; if current node is target, source is candidate
                candidate_id = rel.target_node_id if rel.source_node_id == last_status.node_id else rel.source_node_id
                target_status = await self._get_user_status(user_id, candidate_id)

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
                    target_node_id = candidate_id

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

    async def get_heatmap_data(self, user_id: UUID) -> list[dict]:
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
                    UserNodeStatus.is_unlocked
                )
            )
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        heatmap = []
        now = _utcnow()

        for px, py, next_review, mastery in rows:
            intensity = 0.0
            if next_review:
                if now >= next_review:
                    # Overdue: graduated intensity based on days overdue
                    days_overdue = (now - next_review).total_seconds() / 86400
                    intensity = min(1.0, 0.5 + min(days_overdue, 14) / 28)
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

    async def _write_spark_outbox_event(
        self,
        user_id: UUID,
        node_id: UUID,
        new_mastery: int,
        revision: int,
    ) -> None:
        """Write mastery outbox event for spark_node, mirroring update_node_mastery pipeline."""
        from sqlalchemy import text as sa_text

        payload = {
            "user_id": str(user_id),
            "node_id": str(node_id),
            "mastery_score": new_mastery,
            "revision": revision,
            "timestamp": _utcnow().isoformat(),
        }
        await self.db.execute(
            sa_text(
                "INSERT INTO event_outbox (aggregate_id, event_type, payload, created_at) "
                "VALUES (:aggregate_id, :event_type, :payload::jsonb, :created_at)"
            ),
            {
                "aggregate_id": str(user_id),
                "event_type": "galaxy.node.mastery_updated",
                "payload": json.dumps(payload),
                "created_at": _utcnow(),
            },
        )
        await self.db.commit()

    def _calculate_mastery_delta(self, study_minutes: int, importance_level: int) -> float:
        time_factor = min(study_minutes / 30.0, 2.0)
        difficulty_factor = 1 + (importance_level - 1) * 0.1
        return self.BASE_MASTERY_POINTS * time_factor * difficulty_factor

    def _check_level_up(self, old_mastery: float, new_mastery: float) -> bool:
        thresholds = [30, 60, 80, 95]
        return any(old_mastery < threshold <= new_mastery for threshold in thresholds)

    def _calculate_next_review(self, mastery_score: float) -> datetime:
        if mastery_score >= 80: days = 14
        elif mastery_score >= 60: days = 7
        elif mastery_score >= 30: days = 3
        else: days = 1
        return _utcnow() + timedelta(days=days)

    async def _get_or_create_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus:
        # P1-9 fix: use INSERT ... ON CONFLICT DO NOTHING to avoid race condition
        # instead of read-then-write which can cause IntegrityError on concurrent inserts
        try:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            stmt = pg_insert(UserNodeStatus).values(
                user_id=user_id, node_id=node_id, bkt_mastery_prob=0.0
            ).on_conflict_do_nothing(
                index_elements=['user_id', 'node_id']
            )
            await self.db.execute(stmt)
            await self.db.flush()
        except Exception:
            pass  # Already exists, will be fetched below

        # Re-read after insert attempt
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        result = await self.db.execute(query)
        status = result.scalar_one_or_none()

        if not status:
            # Fallback: create new status (should not reach here normally)
            status = UserNodeStatus(user_id=user_id, node_id=node_id, bkt_mastery_prob=0.0)
            self.db.add(status)
            await self.db.flush()

        return status

    async def _get_user_status(self, user_id: UUID, node_id: UUID) -> UserNodeStatus | None:
        query = select(UserNodeStatus).where(
            and_(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.node_id == node_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
