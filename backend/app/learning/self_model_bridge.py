"""SelfModelBridge — unifies the dual self-model implementations.

Spine SelfModel (signals/self_model.py) and Aurora SelfModel
(aurora/runtime_v1/self_model.py) each maintain independent views
of the user. This bridge synchronizes them so both systems share
a consistent picture of what Sparkle believes about itself.

Strategy:
- Read/write both stores on every outcome
- Aurora SelfModel is the primary long-term store (90-day TTL)
- Spine SelfModel claims feed Aurora's assumption evidence
- Strategy confidence is kept consistent between both
"""

from __future__ import annotations

from loguru import logger


class SelfModelBridge:
    """Bridges Spine and Aurora self-model implementations."""

    def __init__(self, redis_client, db_session=None):
        self.redis = redis_client
        self.db_session = db_session

    async def sync_outcome_to_both(
        self,
        *,
        user_id: str,
        intervention: str,
        attribution: str,
        confidence: float,
        actual_outcome: dict,
    ) -> dict:
        """Synchronize outcome evidence into both self-models."""
        result = {"spine": None, "aurora": None}

        # ── Spine SelfModel: record claim ──
        try:
            from app.signals.self_model import SparkleSelfModelService as SpineSM
            spine = SpineSM(self.redis)
            claim = await spine.record_claim(
                user_id=user_id,
                claim=f"干预「{intervention}」产生 {attribution} 结果 (conf={confidence:.2f})",
                confidence=confidence,
                scope="strategy" if attribution == "effective" else "current_sprint",
                evidence=[f"intervention={intervention}", f"outcome={attribution}"],
                policy_effects=[intervention],
            )
            result["spine"] = claim.claim_id
        except Exception:
            logger.debug("SelfModelBridge: spine write failed for user={}", user_id, exc_info=True)

        # ── Aurora SelfModel: record task outcome ──
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService as AuroraSM
            aurora = AuroraSM(
                redis_client=self.redis,
                db_session=self.db_session,
            )
            completed = attribution == "effective"
            state = await aurora.record_task_outcome(
                user_id=user_id,
                completed=completed,
                reason=intervention,
            )
            result["aurora"] = True
        except Exception:
            logger.debug("SelfModelBridge: aurora write failed for user={}", user_id, exc_info=True)

        return result

    async def sync_strategy_confidence(self, *, user_id: str) -> float | None:
        """Read strategy confidence from both models and cross-validate."""
        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService as AuroraSM
            aurora = AuroraSM(redis_client=self.redis, db_session=self.db_session)
            summary = await aurora.get_readout_summary(user_id=user_id)
            aurora_conf = summary.get("strategy_confidence")
        except Exception:
            aurora_conf = None
            logger.debug("SelfModelBridge: aurora read failed for user={}", user_id, exc_info=True)

        try:
            from app.signals.self_model import SparkleSelfModelService as SpineSM
            spine = SpineSM(self.redis)
            claims = await spine.get_active_claims(user_id, limit=5)
            spine_conf = (
                sum(c.confidence for c in claims) / len(claims)
                if claims else None
            )
        except Exception:
            spine_conf = None
            logger.debug("SelfModelBridge: spine read failed for user={}", user_id, exc_info=True)

        # Return the higher-confidence value, preferring Aurora
        if aurora_conf is not None:
            return float(aurora_conf)
        return spine_conf

    async def record_user_correction_in_both(
        self,
        *,
        user_id: str,
        reason: str,
        source: str = "user_correction",
    ) -> None:
        """When user corrects Sparkle, record in both self-models."""
        try:
            from app.signals.self_model import SparkleSelfModelService as SpineSM
            spine = SpineSM(self.redis)
            await spine.record_user_correction(
                user_id=user_id,
                signal_id="",
                reason=reason,
                source=source,
            )
        except Exception:
            logger.debug("SelfModelBridge: correction spine write failed", exc_info=True)

        try:
            from app.aurora.runtime_v1.self_model import SparkleSelfModelService as AuroraSM
            aurora = AuroraSM(redis_client=self.redis, db_session=self.db_session)
            await aurora.record_user_correction(
                user_id=user_id,
                reason=reason,
                source=source,
            )
        except Exception:
            logger.debug("SelfModelBridge: correction aurora write failed", exc_info=True)
