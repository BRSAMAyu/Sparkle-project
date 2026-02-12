from __future__ import annotations

import hashlib
from typing import Any


class LearningCohortService:
    """Derive cohort/user scopes with non-sensitive behavioral signals only."""

    @classmethod
    def resolve_cohort_id(
        cls,
        *,
        user_id: str = "",
        message: str = "",
        chat_mode: str = "standard",
        task_type: str = "",
        complexity_tier: str = "unknown",
        user_context: dict[str, Any] | None = None,
    ) -> str:
        _ = user_id
        ctx = user_context if isinstance(user_context, dict) else {}
        domain = cls._task_domain(task_type=task_type or chat_mode, message=message)
        tier = cls._normalize_complexity_tier(complexity_tier)
        engagement = cls._engagement_band(ctx)
        execution = cls._execution_rhythm_band(ctx)
        return f"cohort::{domain}::{tier}::{engagement}::{execution}"

    @staticmethod
    def user_scope_key(user_id: str) -> str:
        if not user_id:
            return "usr::anon"
        digest = hashlib.sha1(str(user_id).encode("utf-8", errors="ignore")).hexdigest()[:12]
        return f"usr::{digest}"

    @staticmethod
    def _normalize_complexity_tier(value: str) -> str:
        tier = str(value or "").strip().lower()
        if tier in {"low", "medium", "high"}:
            return tier
        return "unknown"

    @classmethod
    def _task_domain(cls, *, task_type: str, message: str) -> str:
        text = f"{task_type} {message}".lower()
        if any(token in text for token in ("study", "学习", "复习", "考试", "exam", "plan")):
            return "study"
        if any(token in text for token in ("error", "诊断", "根因", "debug", "错题")):
            return "diagnosis"
        if any(token in text for token in ("code", "编程", "python", "java", "sql")):
            return "code"
        if any(token in text for token in ("math", "数学", "方程", "积分")):
            return "math"
        if any(token in text for token in ("writing", "写作", "表达", "essay")):
            return "writing"
        return "general"

    @staticmethod
    def _engagement_band(user_context: dict[str, Any]) -> str:
        profile = user_context.get("profile") if isinstance(user_context.get("profile"), dict) else {}
        analytics = user_context.get("analytics_summary") if isinstance(user_context.get("analytics_summary"), dict) else {}
        focus = user_context.get("focus_stats") if isinstance(user_context.get("focus_stats"), dict) else {}
        progress_score = 0.0

        for source in (profile, analytics, focus):
            for key in ("engagement_score", "engagement", "activity_score"):
                raw = source.get(key)
                if isinstance(raw, (int, float)):
                    progress_score = max(progress_score, float(raw))
                    break
            if progress_score > 0:
                break

        if progress_score >= 0.75:
            return "high_engagement"
        if progress_score >= 0.45:
            return "medium_engagement"
        return "low_engagement"

    @staticmethod
    def _execution_rhythm_band(user_context: dict[str, Any]) -> str:
        decomposition = user_context.get("decomposition_signals")
        if not isinstance(decomposition, dict):
            plan_context = user_context.get("plan_context")
            if isinstance(plan_context, dict) and isinstance(plan_context.get("decomposition_signals"), dict):
                decomposition = plan_context.get("decomposition_signals")
        if not isinstance(decomposition, dict):
            return "rhythm_unknown"

        rhythm = decomposition.get("historical_execution_rhythm")
        if not isinstance(rhythm, (int, float)):
            return "rhythm_unknown"
        val = float(rhythm)
        if val >= 0.75:
            return "rhythm_fast"
        if val >= 0.45:
            return "rhythm_steady"
        return "rhythm_fragile"
