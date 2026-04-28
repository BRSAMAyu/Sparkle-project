"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine — Policy Analytics

PolicyAnalytics — analyzes PolicyEffectLedger patterns for asynchronous review.
This module never mutates policy rules; it only summarizes effectiveness signals.
"""

from __future__ import annotations

from statistics import median, pstdev
from typing import Any

from loguru import logger

from app.signals.types import PolicyEffectEntry

_POSITIVE_FEEDBACK = {"completed", "positive"}


class PolicyAnalytics:
    """Analyze policy effectiveness patterns from PolicyEffectLedger."""

    def __init__(self, redis_client: Any) -> None:
        self.redis = redis_client

    def compute_strategy_accuracy(
        self,
        effects: list[PolicyEffectEntry],
    ) -> dict[str, float]:
        """Compute effective attribution ratio per policy_key."""
        grouped = self._group_by_policy(effects)
        return {
            policy_key: self._accuracy(entries)
            for policy_key, entries in grouped.items()
            if entries
        }

    def detect_degrading_strategies(
        self,
        effects: list[PolicyEffectEntry],
        window: int = 10,
    ) -> list[str]:
        """Find policies where the latest window is less accurate than history."""
        if window <= 0:
            return []

        degrading: list[str] = []
        for policy_key, entries in self._group_by_policy(effects).items():
            if len(entries) <= window:
                continue

            recent = entries[-window:]
            recent_accuracy = self._accuracy(recent)
            historical_accuracy = self._accuracy(entries)
            if recent_accuracy < historical_accuracy:
                degrading.append(policy_key)

        return degrading

    def compute_confidence_distribution(
        self,
        effects: list[PolicyEffectEntry],
    ) -> dict[str, Any]:
        """Compute distribution statistics for attribution_confidence."""
        values = [entry.attribution_confidence for entry in effects]
        if not values:
            return {
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "count": 0,
            }

        mean_value = sum(values) / len(values)
        std_value = pstdev(values) if len(values) > 1 else 0.0
        return {
            "mean": round(mean_value, 4),
            "median": round(float(median(values)), 4),
            "std": round(std_value, 4),
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

    def suggest_policy_review(
        self,
        effects: list[PolicyEffectEntry],
    ) -> list[dict[str, Any]]:
        """Suggest policies that need human review due to weak or noisy signals."""
        suggestions: list[dict[str, Any]] = []

        for policy_key, entries in self._group_by_policy(effects).items():
            accuracy = self._accuracy(entries)
            reasons: list[str] = []

            if accuracy < 0.5:
                reasons.append("low_accuracy")

            if self._confidence_is_declining(entries):
                reasons.append("confidence_declining")

            feedback_summary = self._feedback_summary(entries)
            if feedback_summary["has_mixed_feedback"]:
                reasons.append("mixed_user_feedback")

            if not reasons:
                continue

            suggestions.append({
                "policy_key": policy_key,
                "accuracy": accuracy,
                "reasons": reasons,
                "confidence_trend": (
                    "declining" if "confidence_declining" in reasons else "stable"
                ),
                "feedback_summary": feedback_summary,
                "recommendation": self._recommendation_for(reasons),
            })

        logger.debug("PolicyAnalytics review suggestions={}", len(suggestions))
        return suggestions

    def build_analytics_snapshot(
        self,
        user_id: str,
        effects: list[PolicyEffectEntry],
    ) -> dict[str, Any]:
        """Build a complete analytics snapshot for a user's policy effects."""
        return {
            "user_id": user_id,
            "total_effects": len(effects),
            "accuracy_by_policy": self.compute_strategy_accuracy(effects),
            "degrading": self.detect_degrading_strategies(effects),
            "confidence_stats": self.compute_confidence_distribution(effects),
            "review_suggestions": self.suggest_policy_review(effects),
        }

    @staticmethod
    def _group_by_policy(
        effects: list[PolicyEffectEntry],
    ) -> dict[str, list[PolicyEffectEntry]]:
        grouped: dict[str, list[PolicyEffectEntry]] = {}
        for entry in effects:
            grouped.setdefault(entry.policy_key, []).append(entry)
        return grouped

    @staticmethod
    def _accuracy(entries: list[PolicyEffectEntry]) -> float:
        if not entries:
            return 0.0
        effective_count = sum(1 for entry in entries if entry.attribution == "effective")
        return round(effective_count / len(entries), 4)

    @staticmethod
    def _confidence_is_declining(entries: list[PolicyEffectEntry]) -> bool:
        if len(entries) < 4:
            return False

        midpoint = len(entries) // 2
        early = entries[:midpoint]
        recent = entries[midpoint:]
        early_mean = sum(entry.attribution_confidence for entry in early) / len(early)
        recent_mean = sum(entry.attribution_confidence for entry in recent) / len(recent)
        return recent_mean < early_mean - 0.05

    @staticmethod
    def _feedback_summary(entries: list[PolicyEffectEntry]) -> dict[str, Any]:
        positive_count = 0
        negative_count = 0
        signals: dict[str, int] = {}

        for entry in entries:
            signal = entry.user_feedback_signal
            if not signal:
                continue

            signals[signal] = signals.get(signal, 0) + 1
            if signal in _POSITIVE_FEEDBACK:
                positive_count += 1
            else:
                negative_count += 1

        return {
            "positive_count": positive_count,
            "negative_count": negative_count,
            "signals": signals,
            "has_mixed_feedback": positive_count > 0 and negative_count > 0,
        }

    @staticmethod
    def _recommendation_for(reasons: list[str]) -> str:
        if "low_accuracy" in reasons:
            return "review_policy_constraints"
        if "confidence_declining" in reasons:
            return "inspect_recent_context_shift"
        return "review_user_feedback_variance"
