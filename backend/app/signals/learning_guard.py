"""
Core: execution
Phase: adapt
Stage: Signal-to-Action Spine P1-4 Learning Guard

学习守卫 — 防止系统从未验证或有害结果中错误学习。

核心原则:
- 只有 attribution=effective 且 confidence>=0.7 的结果才允许写入长期策略
- attribution=harmful 的结果触发立即撤回
- 连续 insufficient >= 3 次触发策略降级
- inconclusive 不学习，不惩罚
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.outcome_recorder import OutcomeRecorder
from app.signals.types import OutcomeRecord


# 学习准入阈值
_EFFECTIVE_CONFIDENCE_THRESHOLD = 0.7
_INSUFFICIENT_STREAK_LIMIT = 3
_HARMFUL_RETRACTION_KEYS = [
    "immediate_retraction_and_apology",
    "retract_and_reduce",
]


class LearningGuard:
    """
    Guards against bad learning from unverified outcomes.

    Called after OutcomeRecorder produces an OutcomeRecord.
    Decides whether the outcome should be written to long-term policy.
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    def should_learn(self, record: OutcomeRecord) -> bool:
        """Check if this outcome should be written to long-term policy."""
        if record.attribution == "effective":
            return record.attribution_confidence >= _EFFECTIVE_CONFIDENCE_THRESHOLD

        if record.attribution == "harmful":
            return False  # Never learn from harmful — only retract

        if record.attribution == "insufficient":
            return False  # Don't learn from insufficient — trigger downgrade check

        if record.attribution in ("inconclusive", "needs_confirmation"):
            return False

        return False

    def should_retract(self, record: OutcomeRecord) -> bool:
        """Check if this outcome should trigger immediate policy retraction."""
        if record.attribution == "harmful":
            return True
        if record.next_policy_suggestion in _HARMFUL_RETRACTION_KEYS:
            return True
        return False

    async def check_insufficient_streak(
        self,
        user_id: str,
        policy_key: str,
    ) -> bool:
        """
        Check if a policy has been insufficient too many times in a row.
        Returns True if the policy should be downgraded.
        """
        recorder = OutcomeRecorder(self.redis)
        count = await recorder.get_insufficient_count_for_policy(user_id, policy_key)
        return count >= _INSUFFICIENT_STREAK_LIMIT

    def get_guard_verdict(self, record: OutcomeRecord) -> dict[str, Any]:
        """
        Get the complete learning guard verdict for an outcome record.

        Returns a dict with: should_learn, should_retract, action, reason.
        """
        if self.should_retract(record):
            receipt = OutcomeRecorder.build_self_correction_receipt(record)
            return {
                "should_learn": False,
                "should_retract": True,
                "action": "retract_and_apologize",
                "reason": f"Outcome {record.outcome_id} attribution={record.attribution}",
                "self_correction_receipt": receipt,
            }

        if self.should_learn(record):
            return {
                "should_learn": True,
                "should_retract": False,
                "action": "write_to_policy",
                "reason": (
                    f"Outcome {record.outcome_id} effective "
                    f"confidence={record.attribution_confidence:.2f}"
                ),
            }

        return {
            "should_learn": False,
            "should_retract": False,
            "action": "skip",
            "reason": (
                f"Outcome {record.outcome_id} attribution={record.attribution} "
                f"does not meet learning threshold"
            ),
        }
