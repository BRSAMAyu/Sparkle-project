from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache_service
from app.core.event_bus import event_bus
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.schemas.galaxy import GalaxyUserStats, NodeWithStatus, SectorCode, SparkEvent, SparkResult, UserStatusInfo
from app.services.expansion_service import ExpansionService
from app.services.galaxy.mastery_evidence import (
    REAL_EVIDENCE_TYPES,
    EvidenceHistoryEntry,
    EvidenceObservation,
    MasteryBelief,
    MasteryEvidenceType,
    capped_legacy_mastery,
    classify_audit_reason,
    encode_evidence_reason,
    encode_observation_payload,
    fuse_mastery,
    parse_observation_payload,
    recompute_evidence_state,
)
from app.services.node_sector_service import dominant_sector_from_weights, resolve_sector_weights


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# --- Spark outbox SQL (module-level so the exact statements are unit-testable) ---
# P1-A: never write ":param::type" PG casts inside sa_text() — the TextClause
# regex backtracks ":payload::jsonb" into a bogus "payloa" bind param and the
# asyncpg compiler leaves a literal ":payload" in the statement, so Postgres
# answers "syntax error at or near ':'" and aborts the whole transaction
# (task complete then 500s on the next SELECT). JSON columns need no cast:
# asyncpg infers jsonb from the prepared statement. The full-column form with
# the sequence-counter upsert mirrors GalaxyService._write_mastery_outbox_event;
# aggregate_type is NOT NULL without a default, and the gateway projector only
# delivers events with sequence_number > cursor, so both are mandatory.
SPARK_OUTBOX_SEQUENCE_SQL = """
    INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
    VALUES (:aggregate_type, :aggregate_id, 1)
    ON CONFLICT (aggregate_type, aggregate_id)
    DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
    RETURNING next_sequence
"""

SPARK_OUTBOX_INSERT_SQL = """
    INSERT INTO event_outbox
    (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
    VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
"""


def _mastery_evidence_info(
    prior_belief: MasteryBelief,
    outcome: EvidenceObservation | None = None,
):
    """Build the evidence provenance payload for a spark response.

    The prior belief already reflects the persisted ledger; if a fresh outcome
    was just fused, the flag clears immediately (not only on next read).
    """
    from app.schemas.galaxy import MasteryEvidenceInfo as _Info

    breakdown = dict(prior_belief.breakdown)
    evidence_count = prior_belief.evidence_count
    if outcome is not None and outcome.evidence_type is not MasteryEvidenceType.SELF_REPORT:
        breakdown[outcome.evidence_type.value] = breakdown.get(outcome.evidence_type.value, 0) + 1
        evidence_count += 1
    real_values = {t.value for t in REAL_EVIDENCE_TYPES}
    has_real = any(k in real_values for k in breakdown)
    last_type = outcome.evidence_type.value if outcome is not None else (
        next((k for k in ("quiz", "task_outcome", "chat_signal", "material_ref") if k in breakdown), None)
    )
    return _Info(
        is_legacy_estimate=not has_real,
        evidence_count=evidence_count,
        self_report_count=prior_belief.self_report_count,
        breakdown=breakdown,
        last_evidence_type=last_type,
    )


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
        trigger_expansion: bool = True,
        outcome: EvidenceObservation | None = None,
    ) -> SparkResult:
        """
        点亮/增强知识点 (任务完成时调用)

        G-01 evidence-aware: 当提供 outcome evidence（测验/任务质量）时，
        mastery 由贝叶斯证据融合产生；否则走 legacy 时间公式，但被
        LEGACY_TIME_MASTERY_CAP 封顶——纯时长永远无法凭空推到"已掌握"。
        """
        # 1. 获取或创建用户节点状态
        status = await self._get_or_create_status(user_id, node_id)

        # 2. 计算掌握度
        node = await self.db.get(KnowledgeNode, node_id)
        old_mastery = status.mastery_score
        is_first_unlock = not status.is_unlocked

        # 2.1 G-01: 重放该节点的证据账本，得到当前先验信念
        prior_belief = await self._load_prior_belief(user_id, node_id, old_mastery)

        if outcome is not None:
            # 证据融合路径：outcome（quiz/task 质量）驱动 mastery
            fused = fuse_mastery(prior_belief.mean, prior_belief.variance, [outcome])
            new_mastery = min(max(fused.mean, 0.0), self.MAX_MASTERY)
            mastery_delta = new_mastery - old_mastery
        else:
            # Legacy 时间路径：有界（时间不再点亮高段掌握度）
            raw_delta = self._calculate_mastery_delta(study_minutes, node.importance_level)
            new_mastery = capped_legacy_mastery(old_mastery, raw_delta)
            mastery_delta = new_mastery - old_mastery

        # 4. 更新状态
        status.mastery_score = new_mastery
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
            # G-01: outcome evidence gets its own audit row so the evidence
            # ledger (replayed by _load_prior_belief) stays append-only.
            if outcome is not None:
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
                        "reason": encode_evidence_reason(outcome.evidence_type),
                        "request_id": encode_observation_payload(outcome.value, outcome.confidence),
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
                task_id=task_id,
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
            mastery_evidence=_mastery_evidence_info(prior_belief, outcome),
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
                .order_by(func.random())
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

    async def _load_prior_belief(self, user_id: UUID, node_id: UUID, current_mastery: float) -> MasteryBelief:
        """G-01: replay the mastery_audit_log evidence ledger for this node.

        Rows written by the spark evidence path carry `evidence:<type>` reasons
        with an observation payload; quiz-grade rows written by other flows
        (error book / exam sprint) are recognized via classify_audit_reason.
        Falls back to the stored mastery as an unvalidated legacy prior when
        the ledger is unreadable.
        """
        from sqlalchemy import text as sa_text

        try:
            result = await self.db.execute(
                sa_text(
                    "SELECT reason, request_id, created_at FROM mastery_audit_log "
                    "WHERE user_id = :user_id AND node_id = :node_id ORDER BY created_at ASC"
                ),
                {"user_id": user_id, "node_id": node_id},
            )
            fetched = result.fetchall()
            if inspect.iscoroutine(fetched):
                fetched = await fetched
            try:
                rows = list(fetched or [])
            except TypeError:
                rows = []
        except Exception as e:
            logger.warning(f"Failed to load evidence ledger for node {node_id}: {e}")
            return MasteryBelief(mean=current_mastery)

        history: list[EvidenceHistoryEntry] = []
        presence_only: list[MasteryEvidenceType] = []
        for reason, request_id, created_at in rows:
            evidence_type = classify_audit_reason(reason)
            if evidence_type is None:
                continue
            parsed = parse_observation_payload(request_id)
            if parsed is None:
                # Quiz-grade rows from other flows (error book / exam sprint)
                # carry no observation payload; their effect is already baked
                # into the stored mastery, so they count as evidence presence
                # (they clear the legacy flag) but are not re-fused.
                presence_only.append(evidence_type)
                continue
            value, confidence = parsed
            history.append(
                EvidenceHistoryEntry(
                    evidence_type=evidence_type,
                    value=float(value),
                    confidence=float(confidence),
                    observed_at=created_at,
                )
            )
        if not history and not presence_only:
            return MasteryBelief(mean=current_mastery)
        belief = recompute_evidence_state(current_mastery, history)
        for evidence_type in presence_only:
            belief.breakdown[evidence_type.value] = belief.breakdown.get(evidence_type.value, 0) + 1
        return belief

    async def get_evidence_counts_by_node(self, user_id: UUID) -> dict[UUID, int]:
        """G-01: per-node count of real evidence rows (graph read path).

        Powers the `legacy_estimate` flag in Galaxy graph responses: a node
        with zero real-evidence audit rows is rendering a legacy estimate.
        """
        from sqlalchemy import text as sa_text

        from app.services.galaxy.mastery_evidence import QUIZ_EVIDENCE_REASONS

        quiz_reasons = sorted(QUIZ_EVIDENCE_REASONS)
        placeholders = ", ".join(f":reason_{i}" for i in range(len(quiz_reasons)))
        params: dict[str, object] = {"user_id": user_id}
        for i, reason in enumerate(quiz_reasons):
            params[f"reason_{i}"] = reason
        try:
            result = await self.db.execute(
                sa_text(
                    f"SELECT node_id, COUNT(*) AS n FROM mastery_audit_log "
                    f"WHERE user_id = :user_id AND (reason LIKE 'evidence:%' OR reason IN ({placeholders})) "
                    f"GROUP BY node_id"
                ),
                params,
            )
            rows = result.fetchall()
        except Exception as e:
            logger.warning(f"Failed to load evidence counts for user {user_id}: {e}")
            return {}
        return {row[0]: int(row[1]) for row in rows if row[0] is not None}


    async def _write_spark_outbox_event(
        self,
        user_id: UUID,
        node_id: UUID,
        new_mastery: int,
        revision: int,
        task_id: UUID | None = None,
    ) -> None:
        """Write mastery outbox event for spark_node, mirroring update_node_mastery pipeline.

        D-01: metadata is built by the shared-field contract (event_registry) and
        carries the causal task_id so a GJ trace can walk UI action (task
        completion) -> outbox event -> user_node_status state update by ids.
        """
        from sqlalchemy import text as sa_text

        from app.core.event_registry import build_event_metadata

        payload = {
            "user_id": str(user_id),
            "node_id": str(node_id),
            "task_id": str(task_id) if task_id else None,
            "mastery_score": new_mastery,
            "revision": revision,
            "timestamp": _utcnow().isoformat(),
        }
        seq_result = await self.db.execute(
            sa_text(SPARK_OUTBOX_SEQUENCE_SQL),
            {"aggregate_type": "galaxy_node_mastery", "aggregate_id": str(user_id)},
        )
        sequence_number = seq_result.scalar_one()
        metadata = build_event_metadata(
            user_id=user_id,
            source="server_service",
            service="galaxy_stats_service",
            event_name="galaxy.node.mastery_updated",
            aggregate_type="galaxy_node_mastery",
            aggregate_id=user_id,
            sequence_number=sequence_number,
            correlation={"task_id": task_id, "node_id": node_id},
        )
        await self.db.execute(
            sa_text(SPARK_OUTBOX_INSERT_SQL),
            {
                "aggregate_type": "galaxy_node_mastery",
                "aggregate_id": str(user_id),
                "event_type": "galaxy.node.mastery_updated",
                "sequence_number": sequence_number,
                "payload": json.dumps(payload),
                "metadata": json.dumps(metadata),
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
