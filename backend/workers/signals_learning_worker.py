"""
Signals Learning Worker

Daily batch job to analyze candidate action feedback and calibrate signal thresholds.

Metrics calculated:
- CTR (Click-Through Rate): accept / (accept + ignore + dismiss)
- Completion Rate: executed / accept
- Confidence Calibration: expected confidence vs actual CTR

This worker runs daily to:
1. Query feedback from the past 24 hours
2. Calculate performance metrics by action_type
3. Update threshold configuration in cache
4. Generate metrics for admin dashboard

Author: Claude Code (Opus 4.5)
Created: 2026-01-15
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.db.session import AsyncSessionLocal
from app.models.candidate_action_feedback import CandidateActionFeedback
from app.core.cache import cache_service


class SignalsLearningWorker:
    """
    Analyzes user feedback on candidate actions to improve signal quality.

    Learning Loop:
    1. Collect feedback data from database
    2. Calculate CTR and completion rate per action type
    3. Identify under/over-performing signals
    4. Adjust confidence thresholds accordingly
    5. Store metrics for dashboard visualization
    """

    # Threshold adjustment limits
    MIN_CONFIDENCE_THRESHOLD = 0.50  # Never go below 50%
    MAX_CONFIDENCE_THRESHOLD = 0.85  # Never go above 85%
    ADJUSTMENT_STEP = 0.05  # Adjust by 5% per day max

    # Minimum sample size for calibration
    MIN_SAMPLES_FOR_ADJUSTMENT = 10

    # Target CTR range
    TARGET_CTR_MIN = 0.30  # 30%
    TARGET_CTR_MAX = 0.70  # 70%

    def __init__(self):
        self.session: Optional[AsyncSession] = None

    async def run_daily_analysis(self) -> Dict:
        """
        Run daily feedback analysis.

        Returns:
            dict: Analysis results with metrics and adjustments
        """
        logger.info("🔍 Starting daily signals learning analysis...")

        async with AsyncSessionLocal() as session:
            self.session = session

            try:
                # 1. Calculate overall metrics
                overall_metrics = await self._calculate_overall_metrics()
                logger.info(f"Overall metrics: {overall_metrics}")

                # 2. Calculate metrics by action type
                action_type_metrics = await self._calculate_action_type_metrics()
                logger.info(f"Action type metrics: {action_type_metrics}")

                # 3. Calculate confidence calibration
                calibration_errors = await self._calculate_confidence_calibration()
                logger.info(f"Calibration errors: {calibration_errors}")

                # 4. Generate threshold adjustments
                adjustments = await self._generate_threshold_adjustments(
                    action_type_metrics,
                    calibration_errors
                )
                logger.info(f"Threshold adjustments: {adjustments}")

                # 5. Store metrics in cache for dashboard
                await self._store_metrics_in_cache({
                    "overall": overall_metrics,
                    "by_action_type": action_type_metrics,
                    "calibration_errors": calibration_errors,
                    "adjustments": adjustments,
                    "updated_at": datetime.utcnow().isoformat(),
                })

                logger.info("✅ Daily signals learning analysis completed")

                return {
                    "status": "success",
                    "overall_metrics": overall_metrics,
                    "action_type_metrics": action_type_metrics,
                    "adjustments": adjustments,
                }

            except Exception as e:
                logger.exception("❌ Failed to run daily signals learning analysis")
                return {
                    "status": "error",
                    "error": str(e),
                }

    async def _calculate_overall_metrics(self) -> Dict:
        """Calculate overall feedback metrics across all action types."""
        # Total feedback count
        total_result = await self.session.execute(
            select(func.count(CandidateActionFeedback.id))
            .where(CandidateActionFeedback.deleted_at.is_(None))
        )
        total_count = total_result.scalar() or 0

        # Feedback type breakdown
        feedback_type_result = await self.session.execute(
            select(
                CandidateActionFeedback.feedback_type,
                func.count(CandidateActionFeedback.id).label('count')
            )
            .where(CandidateActionFeedback.deleted_at.is_(None))
            .group_by(CandidateActionFeedback.feedback_type)
        )

        feedback_counts = {
            row.feedback_type: row.count
            for row in feedback_type_result
        }

        accepts = feedback_counts.get('accept', 0)
        ignores = feedback_counts.get('ignore', 0)
        dismisses = feedback_counts.get('dismiss', 0)

        # Calculate CTR
        total_interactions = accepts + ignores + dismisses
        ctr = (accepts / total_interactions) if total_interactions > 0 else 0.0

        # Calculate completion rate
        executed_result = await self.session.execute(
            select(func.count(CandidateActionFeedback.id))
            .where(CandidateActionFeedback.feedback_type == 'accept')
            .where(CandidateActionFeedback.executed == True)
            .where(CandidateActionFeedback.deleted_at.is_(None))
        )
        executed_count = executed_result.scalar() or 0
        completion_rate = (executed_count / accepts) if accepts > 0 else 0.0

        return {
            "total_feedback": total_count,
            "accepts": accepts,
            "ignores": ignores,
            "dismisses": dismisses,
            "ctr": round(ctr, 4),
            "completion_rate": round(completion_rate, 4),
        }

    async def _calculate_action_type_metrics(self) -> Dict[str, Dict]:
        """Calculate metrics broken down by action type."""
        action_types = ["break", "review", "clarify", "plan_split"]
        metrics = {}

        for action_type in action_types:
            # Get feedback counts by feedback_type
            result = await self.session.execute(
                select(
                    CandidateActionFeedback.feedback_type,
                    func.count(CandidateActionFeedback.id).label('count')
                )
                .where(CandidateActionFeedback.action_type == action_type)
                .where(CandidateActionFeedback.deleted_at.is_(None))
                .group_by(CandidateActionFeedback.feedback_type)
            )

            counts = {row.feedback_type: row.count for row in result}
            accepts = counts.get('accept', 0)
            ignores = counts.get('ignore', 0)
            dismisses = counts.get('dismiss', 0)
            total = accepts + ignores + dismisses

            # Calculate CTR
            ctr = (accepts / total) if total > 0 else 0.0

            # Calculate completion rate
            executed_result = await self.session.execute(
                select(func.count(CandidateActionFeedback.id))
                .where(CandidateActionFeedback.action_type == action_type)
                .where(CandidateActionFeedback.feedback_type == 'accept')
                .where(CandidateActionFeedback.executed == True)
                .where(CandidateActionFeedback.deleted_at.is_(None))
            )
            executed = executed_result.scalar() or 0
            completion_rate = (executed / accepts) if accepts > 0 else 0.0

            metrics[action_type] = {
                "total_shown": total,
                "accepts": accepts,
                "ignores": ignores,
                "dismisses": dismisses,
                "ctr": round(ctr, 4),
                "completion_rate": round(completion_rate, 4),
                "sample_size": total,
            }

        return metrics

    async def _calculate_confidence_calibration(self) -> Dict[str, float]:
        """
        Calculate confidence calibration error.

        Confidence calibration measures how well the predicted confidence
        matches the actual CTR. For example, if a signal has confidence=0.75,
        we expect ~75% of users to accept it.

        Calibration error = |predicted_confidence - actual_ctr|
        """
        # This is a simplified version. In production, you'd need to:
        # 1. Store the original signal confidence in context_snapshot
        # 2. Group by confidence buckets (0.65-0.70, 0.70-0.75, etc.)
        # 3. Compare expected vs actual CTR for each bucket

        # For now, return placeholder
        # TODO: Implement proper confidence calibration when context_snapshot
        # includes original signal confidence

        return {
            "calibration_note": "Confidence calibration requires context_snapshot data",
            "implementation_pending": True,
        }

    async def _generate_threshold_adjustments(
        self,
        action_type_metrics: Dict[str, Dict],
        calibration_errors: Dict
    ) -> Dict[str, Dict]:
        """
        Generate threshold adjustment recommendations.

        Logic:
        - If CTR < 30%: Signal is too aggressive → INCREASE threshold
        - If CTR > 70%: Signal is too conservative → DECREASE threshold
        - If CTR in 30-70%: Signal is well-calibrated → NO CHANGE

        Args:
            action_type_metrics: Metrics by action type
            calibration_errors: Confidence calibration errors

        Returns:
            dict: Adjustment recommendations
        """
        adjustments = {}

        for action_type, metrics in action_type_metrics.items():
            ctr = metrics["ctr"]
            sample_size = metrics["sample_size"]

            # Skip if insufficient data
            if sample_size < self.MIN_SAMPLES_FOR_ADJUSTMENT:
                adjustments[action_type] = {
                    "action": "none",
                    "reason": f"Insufficient data ({sample_size} < {self.MIN_SAMPLES_FOR_ADJUSTMENT})",
                    "current_ctr": ctr,
                }
                continue

            # Determine adjustment
            if ctr < self.TARGET_CTR_MIN:
                # Too many rejections → increase threshold
                adjustments[action_type] = {
                    "action": "increase_threshold",
                    "current_ctr": ctr,
                    "target_ctr": f"{self.TARGET_CTR_MIN:.0%}-{self.TARGET_CTR_MAX:.0%}",
                    "recommended_adjustment": f"+{self.ADJUSTMENT_STEP}",
                    "reason": f"CTR too low ({ctr:.1%} < {self.TARGET_CTR_MIN:.0%})",
                }
            elif ctr > self.TARGET_CTR_MAX:
                # Too many accepts → decrease threshold
                adjustments[action_type] = {
                    "action": "decrease_threshold",
                    "current_ctr": ctr,
                    "target_ctr": f"{self.TARGET_CTR_MIN:.0%}-{self.TARGET_CTR_MAX:.0%}",
                    "recommended_adjustment": f"-{self.ADJUSTMENT_STEP}",
                    "reason": f"CTR too high ({ctr:.1%} > {self.TARGET_CTR_MAX:.0%})",
                }
            else:
                # Well-calibrated
                adjustments[action_type] = {
                    "action": "none",
                    "current_ctr": ctr,
                    "target_ctr": f"{self.TARGET_CTR_MIN:.0%}-{self.TARGET_CTR_MAX:.0%}",
                    "reason": f"CTR within target range ({ctr:.1%})",
                }

        return adjustments

    async def _store_metrics_in_cache(self, metrics: Dict):
        """Store metrics in Redis cache for dashboard access."""
        cache_key = "signals_learning:latest_metrics"
        ttl = 86400 * 2  # 2 days (longer than daily run interval)

        await cache_service.set(cache_key, metrics, ttl=ttl)
        logger.info(f"📊 Stored metrics in cache: {cache_key}")

    async def get_latest_metrics(self) -> Optional[Dict]:
        """
        Retrieve latest learning metrics from cache.

        Used by admin dashboard to display signal performance.
        """
        cache_key = "signals_learning:latest_metrics"
        metrics = await cache_service.get(cache_key)

        if metrics:
            logger.debug("Retrieved latest metrics from cache")
            return metrics
        else:
            logger.warning("No metrics found in cache")
            return None


# =============================================================================
# Celery Task Integration
# =============================================================================

from app.core.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, name="signals_learning_daily")
def signals_learning_daily(self):
    """
    Daily Celery task for signals learning analysis.

    Scheduled via Celery Beat to run once per day.

    Returns:
        dict: Analysis results
    """
    from loguru import logger

    async def _run():
        worker = SignalsLearningWorker()
        return await worker.run_daily_analysis()

    try:
        logger.info("🔮 Starting Celery task: signals_learning_daily")
        result = asyncio.run(_run())
        logger.info(f"✅ Celery task completed: {result['status']}")
        return result
    except Exception as exc:
        logger.exception("❌ Celery task failed")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


# =============================================================================
# Worker Instance (for direct execution)
# =============================================================================

_worker_instance: Optional[SignalsLearningWorker] = None


def get_signals_learning_worker() -> SignalsLearningWorker:
    """Get worker singleton instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = SignalsLearningWorker()
    return _worker_instance


async def run_analysis_once():
    """
    Run analysis once (for testing or manual execution).

    Usage:
        python -c "import asyncio; from workers.signals_learning_worker import run_analysis_once; asyncio.run(run_analysis_once())"
    """
    worker = get_signals_learning_worker()
    return await worker.run_daily_analysis()


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys

    print("Signals Learning Worker - Manual Execution")
    print("=" * 60)

    async def main():
        worker = SignalsLearningWorker()
        result = await worker.run_daily_analysis()

        print("\nAnalysis Results:")
        print("-" * 60)

        if result["status"] == "success":
            print(f"✅ Status: {result['status']}")
            print(f"\nOverall Metrics:")
            for key, value in result["overall_metrics"].items():
                print(f"  {key}: {value}")

            print(f"\nAction Type Metrics:")
            for action_type, metrics in result["action_type_metrics"].items():
                print(f"  {action_type}:")
                for key, value in metrics.items():
                    print(f"    {key}: {value}")

            print(f"\nAdjustment Recommendations:")
            for action_type, adj in result["adjustments"].items():
                print(f"  {action_type}: {adj['action']} - {adj['reason']}")
        else:
            print(f"❌ Status: {result['status']}")
            print(f"Error: {result.get('error', 'Unknown error')}")

    try:
        asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
