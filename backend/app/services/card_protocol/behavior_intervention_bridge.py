"""
Behavior Pattern → Intervention Record Bridge.

This fixes breakpoint 4 from the product consensus:
  "interventions are too time-driven"

Currently: BehaviorSignalCollector detects patterns and calls
AdaptiveReplanner.on_behavior_pattern_detected(), which applies plan
constraints but does NOT create tracked intervention records.

This bridge:
  1. Consumes behavior pattern events (procrastination, perfectionism, etc.)
  2. Maps high-confidence patterns to InterventionRecords
  3. Selects delivery strategy based on pattern type and user history
  4. Links to relevant plan/knowledge cards in the card protocol

Integration: Called from BehaviorSignalCollector.handle_behavior_pattern_event()
after the existing replanner call, or as a dedicated event consumer.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card_protocol import (
    Card,
    CardType,
    InterventionRecord,
    InterventionTriggerType,
    DeliveryStrategy,
    DeliveryChannel,
    InterventionOutcomeStatus,
)
from app.services.intervention_record_service import InterventionRecordService
from app.services.card_service import CardService
from app.services.intervention_strategy_learner import InterventionStrategyLearner
from app.core.event_bus import EventBus


# Map behavior pattern types to intervention trigger types
_PATTERN_TRIGGER_MAP = {
    "procrastination": InterventionTriggerType.STALL_PATTERN,
    "avoidance": InterventionTriggerType.STALL_PATTERN,
    "execution": InterventionTriggerType.STALL_PATTERN,
    "perfectionism": InterventionTriggerType.STALL_PATTERN,
    "planning_fallacy": InterventionTriggerType.OVERLOAD,
    "overload": InterventionTriggerType.OVERLOAD,
    "cognitive": InterventionTriggerType.CONCEPT_GAP,
    "emotional": InterventionTriggerType.STALL_PATTERN,
}

# Patterns that warrant MICRO_RESTART strategy
_MICRO_RESTART_PATTERNS = {"procrastination", "avoidance", "execution", "overload"}

# Minimum confidence to trigger an intervention record
_MIN_CONFIDENCE = 0.6


class BehaviorInterventionBridge:
    """Converts behavioral pattern detections into tracked intervention records.

    Usage:
        bridge = BehaviorInterventionBridge(db, event_bus)
        await bridge.on_behavior_pattern(
            user_id=user_id,
            pattern_name="procrastination",
            pattern_type="execution",
            confidence=0.85,
            plan_id=plan_id,
            description="User has deferred 3 consecutive tasks",
        )
    """

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.record_service = InterventionRecordService(db, event_bus)
        self.card_service = CardService(db, event_bus)
        self.strategy_learner = InterventionStrategyLearner(db)

    async def on_behavior_pattern(
        self,
        *,
        user_id: uuid.UUID,
        pattern_name: str,
        pattern_type: str,
        confidence: float,
        plan_id: uuid.UUID | None = None,
        description: str | None = None,
        solution_text: str | None = None,
        frequency: int = 1,
        evidence_ids: list[str] | None = None,
    ) -> InterventionRecord | None:
        """Create an InterventionRecord from a behavior pattern detection.

        Only creates a record if:
          1. Confidence meets minimum threshold
          2. Pattern maps to a known trigger type
          3. User doesn't have a recent similar intervention

        Returns the created record, or None if conditions not met.
        """

        # 1. Check confidence threshold
        if confidence < _MIN_CONFIDENCE:
            return None

        # 2. Map pattern to trigger type
        trigger_type = _PATTERN_TRIGGER_MAP.get(pattern_type)
        if not trigger_type:
            # Try matching by pattern name
            for key, mapped_type in _PATTERN_TRIGGER_MAP.items():
                if key in pattern_name.lower():
                    trigger_type = mapped_type
                    break
        if not trigger_type:
            trigger_type = InterventionTriggerType.STALL_PATTERN

        # 3. Find the plan card if available
        plan_card_id = None
        if plan_id:
            plan_card = await self._find_plan_card(plan_id)
            if plan_card:
                plan_card_id = plan_card.id

        # 4. Check for recent similar intervention (avoid spam)
        if plan_card_id:
            has_recent = await self._has_recent_similar(user_id, trigger_type, plan_card_id)
            if has_recent:
                logger.debug(
                    "BehaviorInterventionBridge: skipping duplicate {} intervention for user {}",
                    trigger_type.value,
                    user_id,
                )
                return None

        # 5. Select delivery strategy
        default_strategy = self._select_strategy(
            pattern_name=pattern_name,
            pattern_type=pattern_type,
            confidence=confidence,
            frequency=frequency,
            user_id=user_id,
        )
        cohort_profile = await self._get_cohort_profile(user_id)
        delivery_strategy = (
            await self.strategy_learner.get_best_strategy(
                user_id, trigger_type, cohort_profile=cohort_profile
            )
            or default_strategy
        )

        # 6. Build diagnosis
        diagnosis = {
            "pattern_name": pattern_name,
            "pattern_type": pattern_type,
            "confidence": confidence,
            "frequency": frequency,
            "description": description,
            "solution_text": solution_text,
            "evidence_ids": evidence_ids or [],
            "detected_at": datetime.utcnow().isoformat(),
            "default_delivery_strategy": default_strategy.value,
            "cohort_profile": cohort_profile or {},
        }

        # 7. Create the record
        record = await self.record_service.create_record(
            user_id=user_id,
            trigger_type=trigger_type,
            delivery_strategy=delivery_strategy,
            delivery_channel=self._select_channel(
                pattern_name=pattern_name,
                pattern_type=pattern_type,
                confidence=confidence,
                frequency=frequency,
            ),
            plan_card_id=plan_card_id,
            trigger_source_ref=f"behavior_pattern:{pattern_name}:{confidence:.2f}",
            diagnosis_payload=diagnosis,
            outcome_window_days=7 if frequency >= 3 else 14,
        )

        logger.info(
            "BehaviorInterventionBridge: created intervention record {} for pattern {} "
            "(type={}, confidence={:.2f}, strategy={}, channel={})",
            record.id,
            pattern_name,
            trigger_type.value,
            confidence,
            delivery_strategy.value,
            record.delivery_channel.value,
        )
        return record

    def _select_strategy(
        self,
        *,
        pattern_name: str,
        pattern_type: str,
        confidence: float,
        frequency: int,
        user_id: uuid.UUID,
    ) -> DeliveryStrategy:
        """Select delivery strategy based on pattern characteristics."""
        # Micro-restart for stall/overload patterns
        lowered_pattern_name = pattern_name.lower()
        if lowered_pattern_name in _MICRO_RESTART_PATTERNS or pattern_type.lower() in _MICRO_RESTART_PATTERNS:
            if frequency >= 3:
                return DeliveryStrategy.MICRO_RESTART
            return DeliveryStrategy.CURIOUS

        # High confidence + repeated → supportive
        if confidence >= 0.8 and frequency >= 2:
            return DeliveryStrategy.SUPPORTIVE

        # Default: curious (low-pressure)
        return DeliveryStrategy.CURIOUS

    def _select_channel(
        self,
        *,
        pattern_name: str,
        pattern_type: str,
        confidence: float,
        frequency: int,
    ) -> DeliveryChannel:
        lowered_pattern_name = pattern_name.lower()
        lowered_pattern_type = pattern_type.lower()
        if (
            confidence >= 0.8
            and frequency >= 3
            and (
                lowered_pattern_name in _MICRO_RESTART_PATTERNS
                or lowered_pattern_type in _MICRO_RESTART_PATTERNS
            )
        ):
            return DeliveryChannel.PUSH
        return DeliveryChannel.CHAT

    async def _get_cohort_profile(self, user_id: uuid.UUID) -> dict | None:
        """Fetch minimal profile fields needed for cohort-based strategy selection."""
        try:
            from app.models.user_preferences import UserPreferencesCenter
            result = await self.db.execute(
                select(UserPreferencesCenter).where(
                    UserPreferencesCenter.user_id == user_id
                )
            )
            prefs = result.scalar_one_or_none()
            if prefs is None:
                return None
            explicit = dict(getattr(prefs, "explicit", None) or getattr(prefs, "explicit_preferences", None) or {})
            goal_mem = dict(prefs.goal_memory or {}) if hasattr(prefs, "goal_memory") else {}
            return {
                "goal_type": goal_mem.get("learning_goal_type") or explicit.get("learning_goal_type"),
                "knowledge_level": explicit.get("knowledge_level"),
                "learning_style": explicit.get("learning_style"),
            }
        except Exception:
            return None

    async def _find_plan_card(self, legacy_plan_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .where(
                Card.card_type == CardType.PLAN,
                Card.metadata_["legacy_plan_id"].as_string() == str(legacy_plan_id),
                Card.not_deleted_filter(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _has_recent_similar(
        self,
        user_id: uuid.UUID,
        trigger_type: InterventionTriggerType,
        plan_card_id: uuid.UUID | None,
    ) -> bool:
        """Check if user has a recent intervention of the same trigger type for this plan."""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=48)
        conditions = [
            InterventionRecord.user_id == user_id,
            InterventionRecord.trigger_type == trigger_type,
            InterventionRecord.outcome_status == InterventionOutcomeStatus.PENDING,
            InterventionRecord.created_at >= cutoff,
            InterventionRecord.not_deleted_filter(),
        ]
        if plan_card_id is not None:
            conditions.append(InterventionRecord.plan_card_id == plan_card_id)

        stmt = (
            select(InterventionRecord)
            .where(*conditions)
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
