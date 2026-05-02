"""
Core: execution
Phase: execute
Stage: P1-17 Low-Yield Gentle Block

Prevents users from engaging in low-yield activities under deadline pressure.
Instead of hard blocking, provides gentle suggestions with high-yield alternatives.
"""

from __future__ import annotations

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
    """

    def __init__(self, redis_client: Any = None):
        self.redis = redis_client

    def check_activity(
        self,
        activity_type: str,
        *,
        deadline_hours: float | None = None,
        is_exam_context: bool = False,
    ) -> YieldCheckResult:
        """Check if an activity type is appropriate given current context.

        Args:
            activity_type: Type of activity being suggested (e.g. 're_read_textbook')
            deadline_hours: Hours until the nearest deadline (None = no deadline pressure)
            is_exam_context: Whether user is in exam preparation mode
        """
        profile = _ACTIVITY_YIELD_PROFILE.get(
            activity_type,
            {"yield_score": 0.5, "time_cost": "medium"},
        )
        yield_score = profile["yield_score"]

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
            "LowYieldGuard: blocked activity={} yield={:.2f} deadline_hours={:.0f}",
            activity_type, yield_score, deadline_hours,
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
