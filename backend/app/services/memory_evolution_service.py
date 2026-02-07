"""
Memory Evolution Service
记忆演化追踪服务

Tracks and manages memory evolution history, predictions, and analysis.
"""
import inspect
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryPreference
from app.models.memory_evolution import EvolutionPrediction, MemoryEvolution


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class MemoryEvolutionService:
    """Memory evolution tracking service"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    async def _extract_scalars(result: Any) -> list[Any]:
        scalars_obj = result.scalars()
        if inspect.isawaitable(scalars_obj):
            scalars_obj = await scalars_obj
        rows = scalars_obj.all()
        if inspect.isawaitable(rows):
            rows = await rows
        return list(rows)

    async def track_memory_change(
        self,
        memory_id: str,
        memory_type: str,
        old_value: dict[str, Any],
        new_value: dict[str, Any],
        change_reason: str,
        trigger_event: str | None = None,
        trigger_source: str | None = None,
        workflow_id: str | None = None,
    ) -> MemoryEvolution:
        """
        记录记忆变化

        Args:
            memory_id: 记忆ID
            memory_type: 记忆类型 (preference, goal, episodic)
            old_value: 旧值
            new_value: 新值
            change_reason: 变化原因
            trigger_event: 触发事件
            trigger_source: 触发来源
            workflow_id: 工作流ID

        Returns:
            MemoryEvolution: 演化记录
        """
        # 1. Detect change type
        change_type = self._detect_change_type(old_value, new_value)

        # 2. Calculate confidence delta
        confidence_before = old_value.get('confidence', 0.0)
        confidence_after = new_value.get('confidence', 0.0)
        confidence_delta = confidence_after - confidence_before

        # 3. Evidence count changes
        evidence_count_before = old_value.get('evidence_count', 0)
        evidence_count_after = new_value.get('evidence_count', 0)
        new_evidence_ids = self._extract_evidence_ids(new_value.get('evidence_refs', []))

        # 4. Analyze impact
        impact_score = await self._calculate_impact_score(
            memory_id, old_value, new_value
        )
        affected_decisions = await self._find_affected_decisions(memory_id)
        affected_memories = await self._find_related_memories(memory_id)

        # 5. Create evolution record
        evolution = MemoryEvolution(
            memory_id=memory_id,
            memory_type=memory_type,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            change_reason=change_reason,
            confidence_delta=confidence_delta,
            confidence_before=confidence_before,
            confidence_after=confidence_after,
            evidence_count_before=evidence_count_before,
            evidence_count_after=evidence_count_after,
            new_evidence_ids=new_evidence_ids,
            impact_score=impact_score,
            affected_decisions=affected_decisions,
            affected_memories=affected_memories,
            trigger_event=trigger_event,
            trigger_source=trigger_source or self._identify_trigger_source(workflow_id),
            workflow_id=workflow_id,
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )

        self.db.add(evolution)
        await self.db.commit()
        await self.db.refresh(evolution)

        # 6. Trigger prediction update
        await self._update_predictions(memory_id, evolution)

        logger.info(
            f"Tracked memory evolution: {memory_id} ({change_reason}), "
            f"confidence_delta={confidence_delta:.3f}, impact={impact_score:.3f}"
        )

        return evolution

    @staticmethod
    def _extract_evidence_ids(evidence_refs: Any) -> list:
        """Extract UUIDs from evidence refs, skipping non-UUID values."""
        refs = evidence_refs or []
        ids = []
        for ref in refs:
            ref_id = None
            if isinstance(ref, dict):
                ref_id = ref.get("id")
            else:
                ref_id = getattr(ref, "id", None)
            if not ref_id:
                continue
            try:
                ids.append(UUID(str(ref_id)))
            except (ValueError, TypeError):
                continue
        return ids

    async def get_evolution_history(
        self,
        memory_id: str,
        limit: int = 50,
        include_predictions: bool = True,
    ) -> list[dict[str, Any]]:
        """
        获取记忆演化历史

        Args:
            memory_id: 记忆ID
            limit: 返回数量限制
            include_predictions: 是否包含预测

        Returns:
            List[Dict]: 演化历史记录
        """
        # 1. Query evolution history
        result = await self.db.execute(
            select(MemoryEvolution)
            .where(MemoryEvolution.memory_id == memory_id)
            .order_by(MemoryEvolution.created_at.desc())
            .limit(limit)
        )
        evolutions = await self._extract_scalars(result)

        # 2. Build timeline
        timeline = []
        for evo in evolutions:
            timeline.append({
                'timestamp': evo.created_at.isoformat(),
                'change_type': evo.change_type,
                'change_reason': evo.change_reason,
                'old_value': evo.old_value,
                'new_value': evo.new_value,
                'confidence_delta': evo.confidence_delta,
                'impact_score': evo.impact_score,
                'trigger': {
                    'event': evo.trigger_event,
                    'source': evo.trigger_source,
                    'workflow': evo.workflow_id,
                },
                'id': str(evo.id),
            })

        # 3. Include predictions if requested
        if include_predictions:
            predictions = await self._get_predictions(memory_id)
            for pred in predictions:
                timeline.append({
                    'timestamp': pred.created_at.isoformat(),
                    'type': 'prediction',
                    'prediction_type': pred.prediction_type,
                    'probability': pred.probability,
                    'predicted_value': pred.predicted_value,
                    'time_horizon': pred.time_horizon,
                    'id': str(pred.id),
                })

        # 4. Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'], reverse=True)

        return timeline

    async def compare_memory_versions(
        self,
        evolution_id: str,
    ) -> dict[str, Any]:
        """
        对比记忆版本

        Args:
            evolution_id: 演化记录ID

        Returns:
            Dict: 版本对比结果
        """
        evolution = await self.db.get(MemoryEvolution, evolution_id)
        if not isinstance(getattr(evolution, "old_value", None), dict):
            result = await self.db.execute(
                select(MemoryEvolution).where(MemoryEvolution.id == evolution_id)
            )
            evolution = result.scalar_one_or_none()
        if not evolution:
            raise ValueError(f"Evolution {evolution_id} not found")

        # 1. Field-level comparison
        field_changes = self._compare_fields(
            evolution.old_value,
            evolution.new_value
        )

        # 2. Semantic change analysis
        semantic_changes = await self._analyze_semantic_changes(
            evolution.old_value,
            evolution.new_value
        )

        # 3. Impact analysis
        impact_analysis = {
            'impact_score': evolution.impact_score,
            'affected_decisions': evolution.affected_decisions or [],
            'affected_memories': evolution.affected_memories or [],
            'estimated_impact_duration': await self._estimate_impact_duration(evolution),
        }

        return {
            'evolution_id': str(evolution.id),
            'timestamp': evolution.created_at.isoformat(),
            'change_reason': evolution.change_reason,
            'field_changes': field_changes,
            'semantic_changes': semantic_changes,
            'impact_analysis': impact_analysis,
            'confidence_change': {
                'before': evolution.confidence_before,
                'after': evolution.confidence_after,
                'delta': evolution.confidence_delta,
            },
        }

    async def visualize_evolution(
        self,
        memory_id: str,
        time_range_days: int = 30,
    ) -> dict[str, Any]:
        """
        演化可视化数据

        Args:
            memory_id: 记忆ID
            time_range_days: 时间范围（天）

        Returns:
            Dict: 可视化数据
        """
        start_date = _utcnow() - timedelta(days=time_range_days)

        # 1. Get evolutions in time range
        result = await self.db.execute(
            select(MemoryEvolution)
            .where(
                and_(
                    MemoryEvolution.memory_id == memory_id,
                    MemoryEvolution.created_at >= start_date
                )
            )
            .order_by(MemoryEvolution.created_at.asc())
        )
        evolutions = await self._extract_scalars(result)

        if not evolutions:
            return {
                'memory_id': memory_id,
                'time_range_days': time_range_days,
                'total_changes': 0,
                'timeline': [],
                'visualization_ready': True,
            }

        # 2. Build time series
        timestamps = []
        confidence_scores = []
        impact_scores = []
        evidence_counts = []

        for evo in evolutions:
            timestamps.append(evo.created_at.isoformat())
            confidence_scores.append(evo.confidence_after)
            impact_scores.append(evo.impact_score)
            evidence_counts.append(evo.evidence_count_after)

        # 3. Change type distribution
        from collections import Counter
        change_types = Counter([evo.change_type for evo in evolutions])

        # 4. Change reason distribution
        change_reasons = Counter([evo.change_reason for evo in evolutions])

        # 5. Impact trend
        impact_trend = self._calculate_impact_trend(evolutions)

        return {
            'memory_id': memory_id,
            'time_range_days': time_range_days,
            'total_changes': len(evolutions),
            'timeline': {
                'timestamps': timestamps,
                'confidence_scores': confidence_scores,
                'impact_scores': impact_scores,
                'evidence_counts': evidence_counts,
            },
            'change_type_distribution': dict(change_types),
            'change_reason_distribution': dict(change_reasons),
            'impact_trend': impact_trend,
            'visualization_ready': True,
        }

    async def predict_evolution(
        self,
        memory_id: str,
        time_horizon_days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        预测记忆演化

        Args:
            memory_id: 记忆ID
            time_horizon_days: 预测时间范围（天）

        Returns:
            List[Dict]: 预测结果
        """
        # 1. Get memory
        memory = await self.db.get(MemoryPreference, memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")

        # 2. Get evolution history
        result = await self.db.execute(
            select(MemoryEvolution)
            .where(MemoryEvolution.memory_id == memory_id)
            .order_by(MemoryEvolution.created_at.desc())
            .limit(100)
        )
        evolutions = await self._extract_scalars(result)

        if not evolutions:
            logger.warning(f"No evolution history for {memory_id}, skipping prediction")
            return []

        # 3. Analyze evolution patterns
        self._analyze_evolution_patterns(evolutions)

        predictions = []

        # 4. Predict decay (for episodic memories)
        if memory.memory_type == 'episodic':
            decay_prediction = await self._predict_decay(
                memory, evolutions, time_horizon_days
            )
            if decay_prediction:
                predictions.append(decay_prediction)

        # 5. Predict strengthening
        strengthen_prediction = await self._predict_strengthening(
            memory, evolutions, time_horizon_days
        )
        if strengthen_prediction:
            predictions.append(strengthen_prediction)

        # 6. Predict conflicts
        conflict_prediction = await self._predict_conflicts(
            memory, evolutions, time_horizon_days
        )
        if conflict_prediction:
            predictions.append(conflict_prediction)

        # 7. Save predictions
        for pred in predictions:
            prediction_record = EvolutionPrediction(
                memory_id=memory_id,
                prediction_type=pred['type'],
                probability=pred['probability'],
                time_horizon=time_horizon_days,
                predicted_value=pred.get('predicted_value'),
                predicted_confidence=pred.get('predicted_confidence'),
                factors=pred.get('factors'),
                similar_evolutions=pred.get('similar_evolutions', []),
                created_at=_utcnow(),
                updated_at=_utcnow(),
            )
            self.db.add(prediction_record)

        await self.db.commit()

        return predictions

    # ============ Helper Methods ============

    def _detect_change_type(self, old_value: dict, new_value: dict) -> str:
        """Detect the type of change"""
        if not old_value or old_value == {}:
            return 'create'
        if not new_value or new_value == {}:
            return 'delete'

        # Check for merge (both have substantial content)
        if old_value.get('content') and new_value.get('content'):
            if len(old_value['content']) > 50 and len(new_value['content']) > 50:
                return 'merge'

        return 'update'

    async def _calculate_impact_score(
        self,
        memory_id: str,
        old_value: dict,
        new_value: dict,
    ) -> float:
        """Calculate the impact score of a change"""
        # Simple heuristic based on confidence change and content change
        confidence_delta = abs(new_value.get('confidence', 0) - old_value.get('confidence', 0))

        # Content change (if text content)
        content_change = 0.0
        if 'content' in old_value and 'content' in new_value:
            old_content = old_value['content'] or ''
            new_content = new_value['content'] or ''
            if old_content != new_content:
                # Calculate word-level difference
                old_words = set(old_content.split())
                new_words = set(new_content.split())
                if old_words or new_words:
                    content_change = 1.0 - len(old_words & new_words) / len(old_words | new_words)

        # Combined impact score
        impact = (confidence_delta * 0.6) + (content_change * 0.4)
        return min(1.0, max(0.0, impact))

    async def _find_affected_decisions(self, memory_id: str) -> list[str]:
        """Find decisions affected by this memory change"""
        # Placeholder: In a full implementation, query decision records
        # that reference this memory
        return []

    async def _find_related_memories(self, memory_id: str) -> list[str]:
        """Find memories related to this one"""
        # Placeholder: In a full implementation, use semantic similarity
        # or graph relationships to find related memories
        return []

    def _identify_trigger_source(self, workflow_id: str | None) -> str:
        """Identify the source of the trigger"""
        if workflow_id:
            if 'agent' in workflow_id.lower():
                return 'agent'
            elif 'tool' in workflow_id.lower():
                return 'tool'
        return 'user'

    async def _update_predictions(
        self,
        memory_id: str,
        evolution: MemoryEvolution,
    ):
        """Update predictions based on new evolution"""
        # Mark old predictions as actualized if they match
        pass

    async def _get_predictions(
        self,
        memory_id: str,
        limit: int = 10,
    ) -> list[EvolutionPrediction]:
        """Get predictions for a memory"""
        result = await self.db.execute(
            select(EvolutionPrediction)
            .where(EvolutionPrediction.memory_id == memory_id)
            .where(EvolutionPrediction.actualized_at.is_(None))
            .order_by(EvolutionPrediction.created_at.desc())
            .limit(limit)
        )
        return await self._extract_scalars(result)

    def _compare_fields(
        self,
        old_value: dict,
        new_value: dict,
    ) -> list[dict[str, Any]]:
        """Compare fields between old and new values"""
        if not isinstance(old_value, dict):
            old_value = {}
        if not isinstance(new_value, dict):
            new_value = {}
        changes = []

        all_keys = set(old_value.keys()) | set(new_value.keys())
        for key in all_keys:
            old_val = old_value.get(key)
            new_val = new_value.get(key)

            if old_val != new_val:
                changes.append({
                    'field': key,
                    'old': old_val,
                    'new': new_val,
                })

        return changes

    async def _analyze_semantic_changes(
        self,
        old_value: dict,
        new_value: dict,
    ) -> dict[str, Any]:
        """Analyze semantic changes"""
        # Placeholder: In a full implementation, use NLP to analyze
        # the semantic difference between old and new values
        return {
            'magnitude': 'medium',
            'category': 'content_update',
        }

    async def _estimate_impact_duration(
        self,
        evolution: MemoryEvolution,
    ) -> int:
        """Estimate how long the impact will last"""
        # Based on change type and impact score
        if evolution.change_type == 'create':
            return 30  # New memories typically have lasting impact
        elif evolution.impact_score > 0.7:
            return 14
        else:
            return 7

    def _calculate_impact_trend(
        self,
        evolutions: list[MemoryEvolution],
    ) -> dict[str, Any]:
        """Calculate impact trend over time"""
        if len(evolutions) < 2:
            return {'trend': 'insufficient_data'}

        recent_impacts = [evo.impact_score for evo in evolutions[-5:]]
        avg_impact = sum(recent_impacts) / len(recent_impacts)

        if avg_impact > 0.7:
            return {'trend': 'increasing', 'avg_impact': avg_impact}
        elif avg_impact < 0.3:
            return {'trend': 'decreasing', 'avg_impact': avg_impact}
        else:
            return {'trend': 'stable', 'avg_impact': avg_impact}

    def _analyze_evolution_patterns(
        self,
        evolutions: list[MemoryEvolution],
    ) -> dict[str, Any]:
        """Analyze evolution patterns"""
        change_reasons = [evo.change_reason for evo in evolutions]

        from collections import Counter
        reason_counts = Counter(change_reasons)

        return {
            'most_common_reason': reason_counts.most_common(1)[0][0] if reason_counts else None,
            'total_evolutions': len(evolutions),
        }

    async def _predict_decay(
        self,
        memory,
        evolutions: list[MemoryEvolution],
        time_horizon: int,
    ) -> dict | None:
        """Predict memory decay"""
        # Simple heuristic based on age and access patterns
        # In a full implementation, use ML model trained on historical data
        return None  # Placeholder

    async def _predict_strengthening(
        self,
        memory,
        evolutions: list[MemoryEvolution],
        time_horizon: int,
    ) -> dict | None:
        """Predict memory strengthening"""
        # Check if memory has been consistently reinforced
        recent_evolutions = [evo for evo in evolutions if evo.confidence_delta > 0]

        if len(recent_evolutions) >= 3:
            return {
                'type': 'strengthen',
                'probability': 0.6,
                'predicted_value': {'confidence': memory.confidence + 0.1},
                'predicted_confidence': memory.confidence + 0.1,
            }

        return None

    async def _predict_conflicts(
        self,
        memory,
        evolutions: list[MemoryEvolution],
        time_horizon: int,
    ) -> dict | None:
        """Predict memory conflicts"""
        # Check for contradictory changes
        has_corrections = any(
            evo.change_reason == 'conflict_resolution'
            for evo in evolutions
        )

        if has_corrections:
            return {
                'type': 'conflict',
                'probability': 0.3,
                'predicted_confidence': 0.5,
            }

        return None
