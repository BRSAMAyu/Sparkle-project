from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.profile_context import ProfileContext
from app.core.user_insight_state import UserInsightState
from app.models.task import Task, TaskStatus


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _hours_for_preference(value: str) -> set[int]:
    normalized = value.strip().lower()
    mapping = {
        "morning": set(range(5, 12)),
        "上午": set(range(5, 12)),
        "afternoon": set(range(12, 18)),
        "下午": set(range(12, 18)),
        "evening": set(range(18, 23)),
        "晚上": set(range(18, 23)),
        "night": {23, 0, 1, 2, 3, 4},
        "late_night": {23, 0, 1, 2, 3, 4},
        "夜间": {23, 0, 1, 2, 3, 4},
    }
    return mapping.get(normalized, set())


class UserInsightAnalysisService:
    """Derive temporal and contradiction-aware analysis from the canonical state."""

    TASK_WINDOW_DAYS = 14
    SHORT_SPAN_DAYS = 1

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze(
        self,
        *,
        user_id: UUID,
        state: UserInsightState,
        profile_context: ProfileContext,
        turn_signals: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        tasks = await self._load_recent_tasks(user_id)
        short_span = self._build_short_span(state=state, tasks=tasks, turn_signals=turn_signals or {})
        medium_span = self._build_medium_span(state=state, tasks=tasks)
        contradictions = self._build_contradictions(
            state=state,
            profile_context=profile_context,
            short_span=short_span,
            medium_span=medium_span,
        )
        state.active_contradictions = list(contradictions)
        confidence_decay = self._build_confidence_decay(state)
        long_span = self._build_long_span(state=state, confidence_decay=confidence_decay)

        self._annotate_hypotheses(state=state, confidence_decay=confidence_decay)
        self._apply_analysis_side_effects(
            state=state,
            short_span=short_span,
            medium_span=medium_span,
            confidence_decay=confidence_decay,
        )

        return {
            "short_span": short_span,
            "medium_span": medium_span,
            "long_span": long_span,
            "contradictions": contradictions,
            "confidence_decay": confidence_decay,
        }

    async def _load_recent_tasks(self, user_id: UUID) -> list[Task]:
        since = _utcnow() - timedelta(days=self.TASK_WINDOW_DAYS)
        result = await self.db.execute(
            select(Task).where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.created_at >= since,
            )
        )
        return list(result.scalars().all())

    def _build_short_span(
        self,
        *,
        state: UserInsightState,
        tasks: list[Task],
        turn_signals: dict[str, Any],
    ) -> dict[str, Any]:
        since = _utcnow() - timedelta(days=self.SHORT_SPAN_DAYS)
        recent_started = sum(
            1
            for task in tasks
            if (task.started_at and task.started_at >= since) or task.created_at >= since
        )
        recent_completed = sum(1 for task in tasks if task.completed_at and task.completed_at >= since)
        pain_count = len(state.recent_pain_points)
        win_count = len(state.recent_wins)
        support_level = _strip(state.inferred_work_style.get("accountability_support") or "self_guided")
        calendar_density = _strip(state.current_state.get("calendar_density_level") or "unknown")
        bottleneck_count = len(state.active_bottlenecks)

        overload_score = 0
        if calendar_density == "high":
            overload_score += 2
        elif calendar_density == "medium":
            overload_score += 1
        if bottleneck_count >= 4:
            overload_score += 1
        if pain_count > win_count:
            overload_score += 1
        if turn_signals.get("low_capacity_language"):
            overload_score += 1
        if _strip(turn_signals.get("requested_difficulty")).lower() in {"hard", "challenging", "high"} and pain_count:
            overload_score += 1

        overload_pressure = "high" if overload_score >= 4 else ("medium" if overload_score >= 2 else "low")

        traction_score = 0
        if recent_completed > 0:
            traction_score += 2
        elif recent_started > 0:
            traction_score += 1
        if win_count > 0:
            traction_score += 1
        if support_level in {"active", "available"}:
            traction_score += 1
        if overload_pressure == "high":
            traction_score -= 2

        current_traction = "high" if traction_score >= 3 else ("medium" if traction_score >= 1 else "low")

        focus_hours = state.inferred_work_style.get("peak_focus_hours") or state.inferred_work_style.get(
            "achievement_peak_hours"
        )
        if isinstance(focus_hours, list) and focus_hours:
            focus_alignment = "constrained" if calendar_density == "high" else "supported"
        else:
            focus_alignment = "unclear"

        return {
            "current_traction": current_traction,
            "overload_pressure": overload_pressure,
            "focus_alignment": focus_alignment,
            "recent_started_tasks": recent_started,
            "recent_completed_tasks": recent_completed,
            "support_level": support_level,
        }

    def _build_medium_span(self, *, state: UserInsightState, tasks: list[Task]) -> dict[str, Any]:
        completion_anchor = [task.completed_at or task.started_at or task.created_at for task in tasks]
        weekday_count = sum(1 for item in completion_anchor if item.weekday() < 5)
        weekend_count = sum(1 for item in completion_anchor if item.weekday() >= 5)
        if weekday_count > weekend_count + 1:
            rhythm = "weekday_weighted"
        elif weekend_count > weekday_count + 1:
            rhythm = "weekend_weighted"
        else:
            rhythm = "balanced"

        started_count = sum(1 for task in tasks if task.started_at or task.created_at)
        completed_count = sum(1 for task in tasks if task.status == TaskStatus.COMPLETED or task.completed_at is not None)
        completion_ratio = round(completed_count / max(started_count, 1), 3)
        if completion_ratio >= 0.8:
            drift_label = "completion_keeps_up"
        elif completion_ratio >= 0.5:
            drift_label = "moderate_drift"
        else:
            drift_label = "high_drift"

        due_soon = sum(1 for task in tasks if task.due_date and (task.due_date - _utcnow().date()).days <= 7)
        calendar_density = _strip(state.current_state.get("calendar_density_level") or "low")
        exam_days_left = _as_int(_extract_exam_urgency(state).get("days_left"))
        deadline_pressure = "low"
        if (exam_days_left is not None and exam_days_left <= 7) or due_soon >= 3:
            deadline_pressure = "high"
        elif calendar_density == "high" or (exam_days_left is not None and exam_days_left <= 14) or due_soon >= 1:
            deadline_pressure = "medium"

        recurring_windows = []
        calendar_patterns = state.temporal_patterns.get("calendar")
        if isinstance(calendar_patterns, dict):
            recurring_windows = list(calendar_patterns.get("recurring_windows") or [])

        return {
            "weekday_vs_weekend": rhythm,
            "deadline_pressure": deadline_pressure,
            "task_start_completion_drift": {
                "label": drift_label,
                "started": started_count,
                "completed": completed_count,
                "completion_ratio": completion_ratio,
            },
            "recurring_windows": recurring_windows[:4],
        }

    def _build_long_span(self, *, state: UserInsightState, confidence_decay: dict[str, Any]) -> dict[str, Any]:
        tendencies: list[dict[str, Any]] = []

        for key in (
            "learning_style",
            "knowledge_level",
            "study_time_preference",
            "content_depth_preference",
        ):
            value = state.stable_preferences.get(key)
            if value not in (None, "", [], {}):
                tendencies.append({"label": key, "value": value, "source": "stable_preferences"})

        for key in (
            "achievement_pace_style",
            "achievement_motivation_response",
            "accountability_support",
            "preferred_tools",
        ):
            value = state.inferred_work_style.get(key)
            if value not in (None, "", [], {}):
                tendencies.append({"label": key, "value": value, "source": "inferred_work_style"})

        overall_posture = _strip(confidence_decay.get("overall_posture") or "mixed")
        revision_risk = "high" if len(state.active_contradictions) >= 2 else ("medium" if overall_posture == "mixed" else "low")

        return {
            "stable_tendencies": tendencies[:8],
            "hypothesis_status": [
                {
                    "id": hypothesis.get("id"),
                    "status": hypothesis.get("status"),
                    "stability": hypothesis.get("stability"),
                }
                for hypothesis in state.evidence_backed_hypotheses[:6]
            ],
            "overall_confidence_posture": overall_posture,
            "profile_revision_risk": revision_risk,
        }

    def _build_confidence_decay(self, state: UserInsightState) -> dict[str, Any]:
        stable_signals: list[str] = []
        provisional_signals: list[str] = []
        stale_signals: list[str] = []

        for evidence in state.signal_evidence:
            signal_id = evidence.signal_id
            freshness = _strip(evidence.freshness or "medium")
            confidence = float(evidence.confidence or 0.0)
            if freshness == "low" or confidence < 0.55:
                stale_signals.append(signal_id)
            elif freshness == "high" and confidence >= 0.75:
                stable_signals.append(signal_id)
            else:
                provisional_signals.append(signal_id)

        overall_posture = "mixed"
        if stale_signals and len(stale_signals) >= len(stable_signals):
            overall_posture = "provisional"
        elif stable_signals and not stale_signals:
            overall_posture = "stable"

        return {
            "stable_signals": stable_signals,
            "provisional_signals": provisional_signals,
            "stale_signals": stale_signals,
            "overall_posture": overall_posture,
        }

    def _build_contradictions(
        self,
        *,
        state: UserInsightState,
        profile_context: ProfileContext,
        short_span: dict[str, Any],
        medium_span: dict[str, Any],
    ) -> list[dict[str, Any]]:
        contradictions: list[dict[str, Any]] = []
        prefs = dict(profile_context.preferences or {})

        explicit_time = _strip(prefs.get("study_time_preference"))
        observed_hours = state.inferred_work_style.get("peak_focus_hours") or state.inferred_work_style.get(
            "achievement_peak_hours"
        )
        explicit_hours = _hours_for_preference(explicit_time)
        observed_hour_set = {int(item) for item in observed_hours} if isinstance(observed_hours, list) else set()
        if explicit_hours and observed_hour_set and explicit_hours.isdisjoint(observed_hour_set):
            contradictions.append(
                {
                    "id": "conflict:time_preference_vs_observed_peak_hours",
                    "severity": "medium",
                    "description": "Declared study-time preference does not match the hours where recent focus evidence clusters.",
                    "evidence": [
                        {"source": "preferences.study_time_preference", "detail": explicit_time},
                        {
                            "source": "signals.peak_focus_hours",
                            "detail": ",".join(str(item) for item in sorted(observed_hour_set)),
                        },
                    ],
                }
            )

        daily_cap = _as_int(prefs.get("daily_cap"))
        if daily_cap is not None and daily_cap <= 45:
            deadline_pressure = _strip(medium_span.get("deadline_pressure"))
            overload_pressure = _strip(short_span.get("overload_pressure"))
            if deadline_pressure == "high" or overload_pressure == "high":
                contradictions.append(
                    {
                        "id": "conflict:declared_capacity_vs_current_pressure",
                        "severity": "high" if deadline_pressure == "high" else "medium",
                        "description": "Declared daily capacity is light, but current deadline and overload signals point to a heavier pressure window.",
                        "evidence": [
                            {"source": "preferences.daily_cap", "detail": str(daily_cap)},
                            {"source": "analysis.deadline_pressure", "detail": deadline_pressure},
                            {"source": "analysis.overload_pressure", "detail": overload_pressure},
                        ],
                    }
                )

        response_style = _strip(prefs.get("response_style"))
        content_depth = _strip(state.stable_preferences.get("content_depth_preference"))
        if response_style == "concise" and content_depth == "deep":
            contradictions.append(
                {
                    "id": "conflict:concise_response_vs_deep_content_behavior",
                    "severity": "low",
                    "description": "The user asks for concise responses but repeatedly saves deeper content, so brevity may need to stay compact without becoming shallow.",
                    "evidence": [
                        {"source": "preferences.response_style", "detail": response_style},
                        {"source": "signals.capsule_depth_preference", "detail": content_depth},
                    ],
                }
            )

        return contradictions

    def _annotate_hypotheses(self, *, state: UserInsightState, confidence_decay: dict[str, Any]) -> None:
        stable_signals = set(confidence_decay.get("stable_signals") or [])
        stale_signals = set(confidence_decay.get("stale_signals") or [])

        for hypothesis in state.evidence_backed_hypotheses:
            source_signals = [
                _strip(item)
                for item in hypothesis.get("source_signals", [])
                if _strip(item)
            ]
            confidences = [
                float(state.confidence_metadata.get(signal_id, 0.0))
                for signal_id in source_signals
                if signal_id in state.confidence_metadata
            ]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.55
            has_stale_support = any(signal_id in stale_signals for signal_id in source_signals)
            stable_support_count = sum(1 for signal_id in source_signals if signal_id in stable_signals)

            if avg_confidence >= 0.78 and stable_support_count >= 1 and not has_stale_support:
                status = "promoted"
                stability = "stable"
            elif avg_confidence >= 0.62 and not has_stale_support:
                status = "provisional"
                stability = "emerging"
            else:
                status = "watch"
                stability = "fragile"

            hypothesis["status"] = status
            hypothesis["stability"] = stability
            hypothesis["confidence_bound"] = round(avg_confidence, 3)
            hypothesis["supporting_signal_count"] = len(source_signals)

    def _apply_analysis_side_effects(
        self,
        *,
        state: UserInsightState,
        short_span: dict[str, Any],
        medium_span: dict[str, Any],
        confidence_decay: dict[str, Any],
    ) -> None:
        state.current_state["current_traction"] = short_span.get("current_traction")
        state.current_state["overload_pressure"] = short_span.get("overload_pressure")
        state.current_state["focus_alignment"] = short_span.get("focus_alignment")
        state.current_state["task_drift_label"] = _strip(
            (medium_span.get("task_start_completion_drift") or {}).get("label")
        )
        state.current_state["insight_confidence_posture"] = confidence_decay.get("overall_posture")

        if confidence_decay.get("stale_signals"):
            for signal_id in confidence_decay["stale_signals"][:3]:
                marker = f"refresh:{signal_id}"
                if marker not in state.missing_information:
                    state.missing_information.append(marker)


def _extract_exam_urgency(state: UserInsightState) -> dict[str, Any]:
    calendar = state.temporal_patterns.get("calendar")
    if isinstance(calendar, dict):
        urgency = calendar.get("exam_urgency")
        if isinstance(urgency, dict):
            return urgency
    return {}
