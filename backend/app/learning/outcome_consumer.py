"""
AUR-005: OutcomeConsumingService — closes the Outcome → ModelUpdate feedback loop.

Reads PolicyEffectLedger entries produced by OutcomeRecorder, builds
AttributionSignalBundles, triggers the continuous learning pipeline,
and feeds distilled strategies + updated beliefs back into the system.

This is what makes Sparkle "越用越懂你" — every effective outcome
becomes a learning signal that adjusts future behavior.
"""

from __future__ import annotations

from uuid import UUID

from loguru import logger

from app.learning.attributor import AttributionSignalBundle
from app.learning.pipeline import run_continuous_learning_pipeline
from app.learning.strategy_store import DistilledStrategyStore


class OutcomeConsumingService:
    """Consumes outcome records and drives the continuous learning loop."""

    def __init__(self, redis_client, db_session_factory=None):
        self.redis = redis_client
        self._strategy_store = DistilledStrategyStore(session_factory=db_session_factory)

    async def consume_effective_outcome(
        self,
        *,
        user_id: str,
        outcome_id: str,
        intervention: str,
        attribution: str,
        confidence: float,
        actual_outcome: dict,
        trace_id: str = "",
    ) -> dict:
        """Feed an effective outcome into the continuous learning pipeline.

        Called after OutcomeRecorder produces an effective/insufficient
        outcome that passes the LearningGuard threshold.
        """
        if attribution not in ("effective", "insufficient"):
            return {"status": "skipped", "reason": f"attribution={attribution}"}

        try:
            uid = UUID(user_id)
        except (ValueError, TypeError):
            return {"status": "skipped", "reason": "invalid_user_id"}

        # Build attribution bundle from the outcome
        completion_streak = 3 if attribution == "effective" else 0
        bundle = AttributionSignalBundle(
            user_id=uid,
            scenario_pack_id=actual_outcome.get("scenario_pack_id", "default"),
            goal_achieved=attribution == "effective",
            task_completion_streak=completion_streak,
            positive_feedback_score=confidence,
            behavioral_improvement_score=confidence * 0.8,
            outcome_summary=actual_outcome.get("summary", f"outcome_{outcome_id}"),
            interventions=[intervention] if intervention else [],
            context_excerpt=actual_outcome.get("context", ""),
            subject_tags=actual_outcome.get("tags", []),
            source_refs=[outcome_id, trace_id] if trace_id else [outcome_id],
        )

        # Run the continuous learning pipeline
        result = await run_continuous_learning_pipeline(bundle, self._strategy_store)

        logger.info(
            "OutcomeConsumingService: outcome={} attribution={} pipeline_status={}",
            outcome_id, attribution, result.status,
        )

        # Record application if a strategy was created
        if result.strategy is not None:
            try:
                await self._strategy_store.record_application(
                    result.strategy.id,
                    satisfaction=confidence,
                )
            except Exception:
                logger.debug(
                    "OutcomeConsumingService: record_application failed for strategy={}",
                    result.strategy.id, exc_info=True,
                )

        # Synchronize outcome to both self-models via the bridge
        try:
            from app.learning.self_model_bridge import SelfModelBridge
            bridge = SelfModelBridge(self.redis)
            await bridge.sync_outcome_to_both(
                user_id=user_id,
                intervention=intervention,
                attribution=attribution,
                confidence=confidence,
                actual_outcome=actual_outcome,
            )
        except Exception:
            logger.debug(
                "OutcomeConsumingService: self_model bridge sync failed for user={}",
                user_id, exc_info=True,
            )

        return {
            "status": result.status,
            "strategy_id": str(result.strategy.id) if result.strategy else None,
            "reasons": list(result.reasons),
        }

    async def consume_insufficient_streak(
        self,
        *,
        user_id: str,
        policy_key: str,
        streak_count: int,
    ) -> dict:
        """Handle a streak of insufficient outcomes — trigger policy downgrade."""
        if streak_count < 3:
            return {"status": "skipped", "reason": f"streak_count={streak_count}"}

        logger.warning(
            "OutcomeConsumingService: policy {} insufficient for {} times for user {}",
            policy_key, streak_count, user_id,
        )

        await self._record_policy_downgrade(user_id, policy_key, streak_count)
        return {
            "status": "policy_downgraded",
            "policy_key": policy_key,
            "streak_count": streak_count,
        }

    async def _feed_self_model(
        self,
        *,
        user_id: str,
        intervention: str,
        attribution: str,
        confidence: float,
        actual_outcome: dict,
    ) -> None:
        """Feed outcome evidence into the spine self-model."""
        try:
            from app.signals.self_model import SparkleSelfModelService

            sm = SparkleSelfModelService(self.redis)
            evidence = [
                f"source=outcome_consumer",
                f"intervention={intervention}",
                f"attribution={attribution}",
                f"confidence={confidence:.2f}",
            ]
            await sm.record_claim(
                user_id=user_id,
                claim=f"干预 {intervention} 产生 {attribution} 结果",
                confidence=confidence,
                scope="strategy" if attribution == "effective" else "current_sprint",
                evidence=evidence,
                policy_effects=[intervention],
            )
        except Exception:
            logger.debug("OutcomeConsumingService: _feed_self_model failed", exc_info=True)

    async def _record_policy_downgrade(
        self,
        user_id: str,
        policy_key: str,
        streak_count: int,
    ) -> None:
        """Persist that a policy was downgraded due to repeated failures."""
        import json

        record = {
            "user_id": user_id,
            "policy_key": policy_key,
            "streak_count": streak_count,
            "action": "downgraded",
        }
        try:
            await self.redis.lpush(
                f"spine:policy_downgrades:{user_id}",
                json.dumps(record),
            )
            await self.redis.ltrim(f"spine:policy_downgrades:{user_id}", 0, 49)
        except Exception:
            logger.debug("OutcomeConsumingService: downgrade record failed", exc_info=True)

    async def get_distilled_strategies_for_user(
        self,
        user_id: str,
        limit: int = 10,
    ):
        """Get distilled strategies applicable to a user."""
        from app.learning.strategy_store import StrategyQuery
        from app.aurora.schemas import DistilledStrategyLifecycle

        query = StrategyQuery(
            statuses=(DistilledStrategyLifecycle.USER_REVIEWED,),
        )
        strategies = await self._strategy_store.list(query)
        return strategies[:limit]

    @property
    def strategy_store(self):
        return self._strategy_store
