"""
Core: execution
Phase: execute
Stage: P1-17 Low-Yield Gentle Block

Prevents users from engaging in low-yield activities under deadline pressure.
Instead of hard blocking, provides gentle suggestions with high-yield alternatives.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

# Activity types mapped to their yield profiles under deadline pressure
# Higher yield_score = more valuable when time is constrained
_ACTIVITY_YIELD_PROFILE: dict[str, dict[str, Any]] = {
    "review_notes": {"yield_score": 0.8, "time_cost": "medium"},
    "practice_problems": {"yield_score": 0.9, "time_cost": "high"},
    "worked_examples": {"yield_score": 0.85, "time_cost": "medium"},
    "flashcards": {"yield_score": 0.5, "time_cost": "medium"},
    "re_read_textbook": {"yield_score": 0.3, "time_cost": "high"},
    "make_pretty_notes": {"yield_score": 0.15, "time_cost": "high"},
    "watch_lecture_video": {"yield_score": 0.4, "time_cost": "high"},
    "organize_files": {"yield_score": 0.1, "time_cost": "low"},
    "browse_supplementary": {"yield_score": 0.2, "time_cost": "high"},
    "drill": {"yield_score": 0.85, "time_cost": "high"},
    "mock_exam": {"yield_score": 0.95, "time_cost": "high"},
    "error_review": {"yield_score": 0.9, "time_cost": "medium"},
}

_HIGH_YIELD_ALTERNATIVES: dict[str, list[str]] = {
    "re_read_textbook": ["practice_problems", "worked_examples"],
    "make_pretty_notes": ["error_review", "drill"],
    "watch_lecture_video": ["practice_problems", "flashcards"],
    "organize_files": ["drill", "mock_exam"],
    "browse_supplementary": ["worked_examples", "error_review"],
    "flashcards": ["practice_problems", "worked_examples"],
}

_LOW_YIELD_THRESHOLD = 0.35

# P4-9 / MAGIC-005: Learning style → activity type → yield_score adjustment.
# Users learn differently; a visual learner benefits more from videos than a reading learner.
# Adjustments are capped at ±0.25 so personalization nudges but doesn't override base profiles.
_LEARNING_STYLE_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "visual": {
        "watch_lecture_video": 0.18,
        "browse_supplementary": 0.12,
        "make_pretty_notes": 0.10,
        "re_read_textbook": -0.05,
    },
    "auditory": {
        "watch_lecture_video": 0.15,
        "review_notes": 0.10,
        "re_read_textbook": -0.05,
    },
    "reading": {
        "re_read_textbook": 0.18,
        "review_notes": 0.12,
        "worked_examples": 0.08,
        "watch_lecture_video": -0.05,
    },
    "kinesthetic": {
        "practice_problems": 0.20,
        "drill": 0.18,
        "mock_exam": 0.15,
        "flashcards": 0.10,
        "watch_lecture_video": -0.10,
        "re_read_textbook": -0.10,
    },
    "balanced": {
        "practice_problems": 0.05,
        "error_review": 0.05,
        "drill": 0.05,
    },
}

_MAX_ADJUSTMENT = 0.25


@dataclass
class YieldCheckResult:
    passed: bool
    activity_type: str = ""
    yield_score: float = 1.0
    recommendation: str = ""
    alternatives: list[str] = field(default_factory=list)
    block_reason: str = ""


class LowYieldGuard:
    """Detects and gently blocks low-yield behavior suggestions.

    P1-17: Under deadline pressure (exam within 3 days), low-yield activities
    are intercepted and replaced with high-yield alternatives.

    P4-9 / MAGIC-005: Yield scores personalized via user's learning_style
    (read from Redis cache key user:prefs:center:{user_id}).
    """

    def __init__(self, redis_client: Any = None):
        self.redis = redis_client

    async def _get_personalized_adjustment(
        self,
        user_id: str,
        activity_type: str,
    ) -> float:
        """Read user's learning_style from Redis and return yield adjustment.

        Returns 0.0 if Redis unavailable, user not cached, or no adjustment defined.
        """
        if not self.redis or not user_id:
            return 0.0
        try:
            raw = await self.redis.get(f"user:prefs:center:{user_id}")
            if not raw:
                return 0.0
            data = json.loads(raw)
            explicit = data.get("explicit", {}) if isinstance(data, dict) else {}
            learning_style = explicit.get("learning_style", "balanced")
            adjustments = _LEARNING_STYLE_ADJUSTMENTS.get(learning_style, {})
            adj = adjustments.get(activity_type, 0.0)
            if adj:
                logger.debug(
                    "LowYieldGuard: personalization user=%s style=%s activity=%s adj=%+.2f",
                    user_id, learning_style, activity_type, adj,
                )
            return adj
        except Exception:
            logger.debug("LowYieldGuard: personalization lookup failed user=%s", user_id, exc_info=True)
            return 0.0

    async def check_activity(
        self,
        activity_type: str,
        *,
        deadline_hours: float | None = None,
        is_exam_context: bool = False,
        user_id: str = "",
    ) -> YieldCheckResult:
        """Check if an activity type is appropriate given current context.

        Args:
            activity_type: Type of activity being suggested (e.g. 're_read_textbook')
            deadline_hours: Hours until the nearest deadline (None = no deadline pressure)
            is_exam_context: Whether user is in exam preparation mode
            user_id: Optional user ID for personalized yield adjustment (P4-9)
        """
        profile = _ACTIVITY_YIELD_PROFILE.get(
            activity_type,
            {"yield_score": 0.5, "time_cost": "medium"},
        )
        base_yield = profile["yield_score"]

        # P4-9: Apply personalization adjustment (clamped to ±_MAX_ADJUSTMENT)
        adj = await self._get_personalized_adjustment(user_id, activity_type) if user_id else 0.0
        adj = max(-_MAX_ADJUSTMENT, min(_MAX_ADJUSTMENT, adj))
        yield_score = round(base_yield + adj, 2)

        # No deadline pressure → no blocking needed
        if deadline_hours is None or deadline_hours > 72:
            return YieldCheckResult(passed=True, activity_type=activity_type, yield_score=yield_score)

        # Under deadline pressure, check yield score
        if yield_score >= _LOW_YIELD_THRESHOLD:
            return YieldCheckResult(passed=True, activity_type=activity_type, yield_score=yield_score)

        # Low yield detected — provide gentle redirection
        alternatives = _HIGH_YIELD_ALTERNATIVES.get(activity_type, ["practice_problems", "error_review"])

        urgency = "critical" if deadline_hours <= 24 else "high" if deadline_hours <= 72 else "moderate"
        recommendation = (
            f"'{activity_type.replace('_', ' ')}' has low yield under deadline pressure "
            f"({deadline_hours:.0f}h remaining). Consider switching to high-yield activities."
        )

        logger.info(
            "LowYieldGuard: blocked activity=%s yield=%.2f (base=%.2f adj=%+.2f) deadline_hours=%.0f",
            activity_type, yield_score, base_yield, adj, deadline_hours,
        )

        return YieldCheckResult(
            passed=False,
            activity_type=activity_type,
            yield_score=yield_score,
            recommendation=recommendation,
            alternatives=alternatives,
            block_reason=f"low_yield_under_{urgency}_deadline",
        )

    def get_best_alternative(
        self,
        activity_type: str,
        available_time_minutes: int = 30,
    ) -> str:
        """Get the best high-yield alternative for a blocked activity."""
        alternatives = _HIGH_YIELD_ALTERNATIVES.get(
            activity_type, ["practice_problems", "error_review"],
        )
        for alt in alternatives:
            profile = _ACTIVITY_YIELD_PROFILE.get(alt, {})
            time_cost = profile.get("time_cost", "medium")
            if time_cost == "low" or available_time_minutes >= 20:
                return alt
        return alternatives[0] if alternatives else "practice_problems"
