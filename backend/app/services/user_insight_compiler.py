from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.profile_context import ProfileContext
from app.core.user_insight_state import UserInsightState
from app.models.accountability import AccountabilityCheckin, AccountabilityPartnership, AccountabilityStatus
from app.models.calendar_event import CalendarEvent
from app.models.capsule_favorite import CapsuleFavorite
from app.models.curiosity_capsule import CuriosityCapsule
from app.models.tool_history import UserToolHistory
from app.profile.projection_contract import UserProjectionContract
from app.services.insight_prediction_service import InsightPredictionService
from app.services.insight_signal_registry import build_signal_evidence
from app.services.user_insight_analysis_service import UserInsightAnalysisService
from app.services.user_insight_calibration_service import UserInsightCalibrationService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_hours(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    hours: list[int] = []
    for raw in value:
        try:
            hour = int(raw)
        except (TypeError, ValueError):
            continue
        if 0 <= hour <= 23 and hour not in hours:
            hours.append(hour)
    return hours


def _confidence_from_sample(sample_size: int, *, base: float = 0.6, ceil: float = 0.9) -> float:
    if sample_size <= 0:
        return base
    return round(min(ceil, base + min(sample_size, 8) * 0.035), 3)


class UserInsightCompiler:
    """Compile a canonical insight state from profile context plus high-value side signals."""

    CALENDAR_WINDOW_DAYS = 28
    TOOL_WINDOW_DAYS = 30
    CAPSULE_WINDOW_DAYS = 90
    ACCOUNTABILITY_WINDOW_DAYS = 21

    STABLE_PREFERENCE_KEYS = {
        "depth_preference",
        "curiosity_preference",
        "feedback_style",
        "persona_type",
        "learning_goal_type",
        "learning_style",
        "knowledge_level",
        "response_style",
        "study_time_preference",
        "timezone",
        "daily_cap",
        "weekly_hours",
        "available_hours",
    }

    ANTI_PATTERN_MARKERS = (
        "avoid",
        "avoidance",
        "paralysis",
        "friction",
        "stuck",
        "freeze",
        "loop",
        "回避",
        "拖延",
        "启动困难",
        "卡住",
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compile(
        self,
        *,
        user_id: UUID,
        profile_context: ProfileContext,
        user_strategy_state: dict[str, Any] | None = None,
        companion_state: dict[str, Any] | None = None,
        turn_signals: dict[str, Any] | None = None,
    ) -> UserProjectionContract:
        state = self._build_base_state(profile_context=profile_context, user_strategy_state=user_strategy_state)
        analysis_service = UserInsightAnalysisService(self.db)
        prediction_service = InsightPredictionService()
        calibration_service = UserInsightCalibrationService(self.db)

        self._apply_m1_quality_overlays(state, profile_context)
        self._apply_error_signals(state, profile_context)
        self._apply_learning_progress(state, profile_context)
        self._apply_achievement_signals(state, profile_context.preferences or {})
        await self._apply_calendar_signals(user_id, state, profile_context.preferences or {})
        await self._apply_workflow_signals(user_id, state)
        await self._apply_content_signals(user_id, state)
        await self._apply_accountability_signals(user_id, state)
        state.multi_span_analysis = await analysis_service.analyze(
            user_id=user_id,
            state=state,
            profile_context=profile_context,
            turn_signals=turn_signals,
        )
        state.prediction_summaries = prediction_service.compile_predictions(
            state=state,
            turn_signals=turn_signals,
        )
        self._apply_prediction_projection(state)
        state.calibration_summary = await calibration_service.calibrate(
            user_id=user_id,
            state=state,
            profile_context=profile_context,
        )
        if self._needs_post_calibration_refresh(state.calibration_summary):
            state.multi_span_analysis = await analysis_service.analyze(
                user_id=user_id,
                state=state,
                profile_context=profile_context,
                turn_signals=turn_signals,
            )
            state.prediction_summaries = prediction_service.compile_predictions(
                state=state,
                turn_signals=turn_signals,
            )
            self._apply_prediction_projection(state)
            calibration_service.reapply_prediction_adjustments(
                state=state,
                calibration_summary=state.calibration_summary,
            )
        self._apply_uncertainty_markers(state)

        if companion_state:
            state.current_state["companion_state"] = dict(companion_state)
        if turn_signals:
            compact_turn_signals = {
                key: value
                for key, value in turn_signals.items()
                if value not in (None, "", [], {})
            }
            if compact_turn_signals:
                state.current_state["turn_signals"] = compact_turn_signals

        return UserProjectionContract.from_compiled_state(
            state=state,
            merged_preferences=dict(profile_context.preferences or {}),
        )

    @staticmethod
    def _needs_post_calibration_refresh(calibration_summary: dict[str, Any]) -> bool:
        return bool(
            calibration_summary.get("inactive_effective_signals")
            or calibration_summary.get("demoted_signals")
            or calibration_summary.get("stale_signals")
        )

    def _apply_prediction_projection(self, state: UserInsightState) -> None:
        planning = state.prediction_summaries.get("planning_readiness")
        overload = state.prediction_summaries.get("overload_risk")
        schedule_fit = state.prediction_summaries.get("schedule_fit")
        slippage = state.prediction_summaries.get("plan_slippage_risk")

        if isinstance(planning, dict):
            state.readiness = {
                "predicted_level": planning.get("level"),
                "predicted_score": planning.get("score"),
                "recommended_action": planning.get("recommended_action"),
            }
        if isinstance(overload, dict):
            state.readiness["overload_risk"] = overload.get("level")
            state.current_state["predicted_overload_risk"] = overload.get("level")
        if isinstance(schedule_fit, dict):
            state.readiness["schedule_fit"] = schedule_fit.get("level")
            state.current_state["predicted_schedule_fit"] = schedule_fit.get("level")
        if isinstance(slippage, dict):
            state.readiness["plan_slippage_risk"] = slippage.get("level")
            state.current_state["predicted_plan_slippage_risk"] = slippage.get("level")

    def _build_base_state(
        self,
        *,
        profile_context: ProfileContext,
        user_strategy_state: dict[str, Any] | None = None,
    ) -> UserInsightState:
        prefs = dict(profile_context.preferences or {})

        stable_preferences = {
            key: prefs[key]
            for key in self.STABLE_PREFERENCE_KEYS
            if prefs.get(key) not in (None, "", [], {})
        }
        current_state = {
            "overall_mastery": float(profile_context.knowledge_summary.overall_mastery or 0.0),
            "active_subjects": list(profile_context.knowledge_summary.active_learning_subjects or []),
            "dominant_pattern_type": profile_context.cognitive_summary.dominant_pattern_type,
            "risk_signals": list(profile_context.cognitive_summary.risk_signals or []),
        }

        if user_strategy_state:
            for source_key, target_key in (
                ("session_mode", "strategy_mode"),
                ("active_mode", "strategy_mode"),
                ("push_vs_support", "push_vs_support"),
                ("intervention_intensity", "intervention_intensity"),
                ("explanation_style", "explanation_style"),
                ("retrieval_emphasis", "retrieval_emphasis"),
            ):
                value = user_strategy_state.get(source_key)
                if value is not None:
                    current_state[target_key] = value

        goals: list[dict[str, Any]] = []
        goal_type = str(prefs.get("learning_goal_type") or prefs.get("goal_type") or "").strip()
        if goal_type:
            goals.append(
                {
                    "id": "goal:primary",
                    "type": goal_type,
                    "label": goal_type,
                    "source": "preferences",
                }
            )
        exam_urgency = prefs.get("exam_urgency")
        if isinstance(exam_urgency, dict) and exam_urgency.get("days_left") is not None:
            goals.append(
                {
                    "id": "goal:exam_window",
                    "type": "exam_window",
                    "label": f"{int(exam_urgency['days_left'])} days left",
                    "source": "preferences",
                    "urgency": exam_urgency.get("urgency", "high"),
                }
            )
        if not goals and current_state["active_subjects"]:
            goals.append(
                {
                    "id": "goal:active_subjects",
                    "type": "learning_scope",
                    "label": " / ".join(str(item) for item in current_state["active_subjects"][:3]),
                    "source": "knowledge_summary",
                }
            )

        constraints: list[dict[str, Any]] = []
        confidence_metadata: dict[str, float] = {}
        freshness_metadata: dict[str, str] = {
            "preferences": "high" if stable_preferences else "low",
            "knowledge": "high" if profile_context.knowledge_summary.recent_mastery_changes else "medium",
            "cognitive": "medium" if profile_context.cognitive_summary.active_patterns else "low",
        }
        for pattern in profile_context.cognitive_summary.active_patterns:
            confidence_val = float(pattern.confidence or 0.0)
            if confidence_val < 0.7:
                continue
            constraint = {
                "id": f"cognitive:{pattern.pattern_name}",
                "label": pattern.pattern_name,
                "type": "behavioral",
                "origin": "cognitive_summary",
                "policy_signals": list(pattern.policy_signals or []),
            }
            constraints.append(constraint)
            confidence_metadata[constraint["id"]] = confidence_val

        active_bottlenecks = [
            {
                "id": f"knowledge:{spot.node_id}",
                "label": spot.node_name,
                "type": "knowledge_gap",
                "mastery": float(spot.mastery or 0.0),
            }
            for spot in profile_context.knowledge_summary.weak_spots
        ]
        active_bottlenecks.extend(
            {
                "id": f"risk:{signal}",
                "label": signal,
                "type": "behavioral_risk",
            }
            for signal in profile_context.cognitive_summary.risk_signals
        )

        return UserInsightState(
            goals=goals,
            constraints=constraints,
            stable_preferences=stable_preferences,
            current_state=current_state,
            active_bottlenecks=active_bottlenecks,
            confidence_metadata=confidence_metadata,
            freshness_metadata=freshness_metadata,
        )

    def _append_signal(
        self,
        state: UserInsightState,
        signal_id: str,
        *,
        value: Any,
        confidence: float | None = None,
        freshness: str | None = None,
        explanation: str | None = None,
    ) -> None:
        state.signal_evidence.append(
            build_signal_evidence(
                signal_id,
                value=value,
                confidence=confidence,
                freshness=freshness,
                explanation=explanation,
            )
        )
        if confidence is not None:
            state.confidence_metadata[signal_id] = float(confidence)
        if freshness:
            state.freshness_metadata[signal_id] = str(freshness)

    def _apply_m1_quality_overlays(self, state: UserInsightState, profile_context: ProfileContext) -> None:
        prefs = dict(profile_context.preferences or {})
        motivation_type = str(prefs.get("motivation_type") or "").strip()
        if motivation_type:
            state.inferred_work_style["motivation_type"] = motivation_type
            self._append_signal(
                state,
                "motivation_type",
                value=motivation_type,
                confidence=0.72,
                freshness="medium",
            )

        high_conf_patterns = [
            pattern
            for pattern in list(profile_context.cognitive_summary.active_patterns or [])
            if float(pattern.confidence or 0.0) >= 0.6
        ]
        if not high_conf_patterns:
            return

        cognitive_tendencies = [
            {
                "pattern_name": pattern.pattern_name,
                "pattern_type": pattern.pattern_type,
                "confidence": float(pattern.confidence or 0.0),
                "policy_signals": list(pattern.policy_signals or []),
            }
            for pattern in high_conf_patterns[:5]
        ]
        state.temporal_patterns["cognitive_tendencies"] = cognitive_tendencies
        self._append_signal(
            state,
            "cognitive_tendencies",
            value=cognitive_tendencies,
            confidence=_confidence_from_sample(len(cognitive_tendencies), base=0.7, ceil=0.86),
            freshness="medium",
        )

        anti_patterns = [
            item
            for item in cognitive_tendencies
            if self._looks_like_anti_pattern(item)
        ]
        if anti_patterns:
            state.temporal_patterns["anti_patterns"] = anti_patterns[:4]
            self._append_signal(
                state,
                "anti_patterns",
                value=anti_patterns[:4],
                confidence=_confidence_from_sample(len(anti_patterns), base=0.68, ceil=0.84),
                freshness="medium",
            )

    def _looks_like_anti_pattern(self, pattern: dict[str, Any]) -> bool:
        label = str(pattern.get("pattern_name") or "").strip().lower()
        policy_signals = [
            str(item).strip().lower()
            for item in list(pattern.get("policy_signals") or [])
            if str(item).strip()
        ]
        if any(marker in label for marker in self.ANTI_PATTERN_MARKERS):
            return True
        return any(
            signal.endswith("start_easy")
            or signal.endswith("reduce_friction")
            or signal.endswith("decompose")
            for signal in policy_signals
        )

    def _apply_error_signals(self, state: UserInsightState, profile_context: ProfileContext) -> None:
        if profile_context.error_summary:
            state.recent_pain_points.append(
                {
                    "id": "pain:error_summary",
                    "type": "error_pressure",
                    "label": "Recent error pressure remains elevated.",
                    "details": dict(profile_context.error_summary),
                }
            )
            self._append_signal(
                state,
                "error_summary",
                value=dict(profile_context.error_summary),
                confidence=0.92,
                freshness="high",
            )

        if profile_context.recent_errors:
            state.recent_pain_points.extend(
                {
                    "id": f"pain:error:{index}",
                    "type": "recent_error",
                    "label": str(item.get("question_preview") or item.get("title") or "Recent blocking error"),
                    "details": dict(item),
                }
                for index, item in enumerate(profile_context.recent_errors[:3])
                if isinstance(item, dict)
            )
            self._append_signal(
                state,
                "recent_errors",
                value=[dict(item) for item in profile_context.recent_errors[:3] if isinstance(item, dict)],
                confidence=_confidence_from_sample(len(profile_context.recent_errors), base=0.72, ceil=0.92),
                freshness="high",
            )

    def _apply_learning_progress(self, state: UserInsightState, profile_context: ProfileContext) -> None:
        mastery_changes = list(profile_context.knowledge_summary.recent_mastery_changes or [])
        if mastery_changes:
            state.recent_wins.extend(
                {
                    "id": f"win:mastery:{item.node_id}",
                    "type": "mastery_gain",
                    "label": item.node_name,
                    "old_mastery": float(item.old_mastery or 0.0),
                    "new_mastery": float(item.new_mastery or 0.0),
                    "changed_at": item.changed_at,
                }
                for item in mastery_changes[:3]
            )
            self._append_signal(
                state,
                "recent_mastery_changes",
                value=[
                    {
                        "node_name": item.node_name,
                        "old_mastery": float(item.old_mastery or 0.0),
                        "new_mastery": float(item.new_mastery or 0.0),
                    }
                    for item in mastery_changes[:3]
                ],
                confidence=_confidence_from_sample(len(mastery_changes), base=0.74, ceil=0.9),
                freshness="high",
            )

    def _apply_achievement_signals(self, state: UserInsightState, prefs: dict[str, Any]) -> None:
        peak_hours = _normalize_hours(prefs.get("achievement_peak_hours"))
        motivation = str(prefs.get("achievement_motivation_response") or "").strip()
        pace_style = str(prefs.get("achievement_pace_style") or "").strip()
        reward_sensitivity = str(prefs.get("achievement_reward_sensitivity") or "").strip()

        achievement_patterns: dict[str, Any] = {}
        if peak_hours:
            achievement_patterns["peak_hours"] = peak_hours
            state.inferred_work_style["achievement_peak_hours"] = peak_hours
            self._append_signal(
                state,
                "achievement_peak_hours",
                value=peak_hours,
                confidence=_confidence_from_sample(len(peak_hours), base=0.68, ceil=0.83),
                freshness="medium",
            )
            state.evidence_backed_hypotheses.append(
                {
                    "id": "hypothesis:achievement_energy_window",
                    "description": f"Visible momentum tends to show up around {peak_hours[:3]}.",
                    "confidence": 0.72,
                    "source_signals": ["achievement_peak_hours"],
                }
            )

        if motivation:
            achievement_patterns["motivation_response"] = motivation
            state.inferred_work_style["achievement_motivation_response"] = motivation
            self._append_signal(
                state,
                "achievement_motivation_response",
                value=motivation,
                confidence=0.78,
                freshness="medium",
            )

        if pace_style:
            achievement_patterns["pace_style"] = pace_style
            state.inferred_work_style["achievement_pace_style"] = pace_style
            self._append_signal(
                state,
                "achievement_pace_style",
                value=pace_style,
                confidence=0.76,
                freshness="medium",
            )

        if reward_sensitivity:
            achievement_patterns["reward_sensitivity"] = reward_sensitivity
            state.inferred_work_style["achievement_reward_sensitivity"] = reward_sensitivity
            self._append_signal(
                state,
                "achievement_reward_sensitivity",
                value=reward_sensitivity,
                confidence=0.73,
                freshness="medium",
            )

        if achievement_patterns:
            state.temporal_patterns["achievement"] = achievement_patterns

    async def _apply_calendar_signals(self, user_id: UUID, state: UserInsightState, prefs: dict[str, Any]) -> None:
        since = _utcnow() - timedelta(days=self.CALENDAR_WINDOW_DAYS)
        result = await self.db.execute(
            select(CalendarEvent).where(
                CalendarEvent.user_id == user_id,
                CalendarEvent.deleted_at.is_(None),
                CalendarEvent.start_time >= since,
            )
        )
        events = list(result.scalars().all())
        if not events and not any(
            prefs.get(key) not in (None, "", [], {})
            for key in ("peak_focus_hours", "inactive_push_hours", "exam_urgency")
        ):
            return

        day_counts: defaultdict[date, int] = defaultdict(int)
        total_minutes = 0
        recurring_counts: Counter[tuple[int, int, int]] = Counter()
        for event in events:
            event_date = event.start_time.date()
            day_counts[event_date] += 1
            total_minutes += max(0, int((event.end_time - event.start_time).total_seconds() / 60))
            end_hour = min(23, int(event.end_time.hour) + (1 if event.end_time.minute > 0 else 0))
            recurring_counts[(event.start_time.weekday(), event.start_time.hour, end_hour)] += 1

        active_days = max(len(day_counts), 1)
        avg_events_per_day = (sum(day_counts.values()) / active_days) if day_counts else 0.0
        avg_minutes_per_day = total_minutes / active_days if active_days else 0.0
        density_level = "low"
        if avg_events_per_day >= 4 or avg_minutes_per_day >= 240:
            density_level = "high"
        elif avg_events_per_day >= 2 or avg_minutes_per_day >= 120:
            density_level = "medium"

        recurring_windows = [
            {
                "weekday": weekday,
                "start_hour": start_hour,
                "end_hour": end_hour,
            }
            for (weekday, start_hour, end_hour), count in recurring_counts.items()
            if count >= 2
        ]
        recurring_windows.sort(key=lambda item: (item["weekday"], item["start_hour"], item["end_hour"]))

        peak_focus_hours = _normalize_hours(prefs.get("peak_focus_hours"))
        inactive_push_hours = _normalize_hours(prefs.get("inactive_push_hours"))
        exam_urgency = prefs.get("exam_urgency") if isinstance(prefs.get("exam_urgency"), dict) else None

        state.temporal_patterns["calendar"] = {
            "density_level": density_level,
            "avg_events_per_day": round(avg_events_per_day, 2),
            "avg_minutes_per_day": round(avg_minutes_per_day, 1),
            "recurring_windows": recurring_windows[:4],
            "peak_focus_hours": peak_focus_hours[:3],
            "inactive_push_hours": inactive_push_hours[:3],
            "exam_urgency": exam_urgency or {},
        }

        state.current_state["calendar_density_level"] = density_level
        if recurring_windows:
            state.constraints.append(
                {
                    "id": "calendar:recurring_windows",
                    "label": "Recurring structured calendar windows",
                    "type": "schedule",
                    "origin": "calendar",
                    "windows": recurring_windows[:4],
                }
            )
            self._append_signal(
                state,
                "calendar_recurring_windows",
                value=recurring_windows[:4],
                confidence=_confidence_from_sample(len(recurring_windows), base=0.7, ceil=0.86),
                freshness="medium",
            )
        self._append_signal(
            state,
            "calendar_density",
            value={"density_level": density_level, "avg_events_per_day": round(avg_events_per_day, 2)},
            confidence=_confidence_from_sample(len(events), base=0.68, ceil=0.85),
            freshness="medium" if events else "low",
        )

        if peak_focus_hours:
            state.inferred_work_style["peak_focus_hours"] = peak_focus_hours[:3]
            self._append_signal(
                state,
                "peak_focus_hours",
                value=peak_focus_hours[:3],
                confidence=0.84,
                freshness="medium",
            )

        if inactive_push_hours:
            state.inferred_work_style["inactive_push_hours"] = inactive_push_hours[:3]
            state.constraints.append(
                {
                    "id": "calendar:inactive_push_hours",
                    "label": "Low-response hours should stay quieter",
                    "type": "timing",
                    "origin": "push_feedback",
                    "hours": inactive_push_hours[:3],
                }
            )
            self._append_signal(
                state,
                "inactive_push_hours",
                value=inactive_push_hours[:3],
                confidence=0.8,
                freshness="medium",
            )

        if exam_urgency and exam_urgency.get("days_left") is not None:
            days_left = int(exam_urgency.get("days_left") or 0)
            state.goals.append(
                {
                    "id": "goal:exam_pressure",
                    "type": "exam_window",
                    "label": f"Exam in {days_left} days",
                    "source": "exam_urgency",
                    "urgency": exam_urgency.get("urgency", "high"),
                }
            )
            state.evidence_backed_hypotheses.append(
                {
                    "id": "hypothesis:calendar_exam_pressure",
                    "description": "Planning should bias toward earlier viable slots because exam pressure is active.",
                    "confidence": 0.8,
                    "source_signals": ["exam_urgency", "calendar_density"],
                }
            )
            self._append_signal(
                state,
                "exam_urgency",
                value=dict(exam_urgency),
                confidence=0.82,
                freshness="high",
            )

    async def _apply_workflow_signals(self, user_id: UUID, state: UserInsightState) -> None:
        since = _utcnow() - timedelta(days=self.TOOL_WINDOW_DAYS)
        result = await self.db.execute(
            select(UserToolHistory).where(
                UserToolHistory.user_id == user_id,
                UserToolHistory.created_at >= since,
            )
        )
        rows = list(result.scalars().all())
        if not rows:
            return

        per_tool: defaultdict[str, dict[str, Any]] = defaultdict(lambda: {"count": 0, "success": 0, "times": []})
        for row in rows:
            bucket = per_tool[row.tool_name]
            bucket["count"] += 1
            bucket["success"] += 1 if row.success else 0
            if row.execution_time_ms is not None:
                bucket["times"].append(int(row.execution_time_ms))

        ranked_tools: list[tuple[str, float, int]] = []
        for tool_name, bucket in per_tool.items():
            count = int(bucket["count"])
            success_rate = (bucket["success"] / count) if count else 0.0
            score = (success_rate * 0.7) + (min(count, 5) / 5 * 0.3)
            ranked_tools.append((tool_name, score, count))
        ranked_tools.sort(key=lambda item: (-item[1], -item[2], item[0]))

        preferred_tools = [tool_name for tool_name, _score, count in ranked_tools if count >= 2][:3]
        overall_success = sum(1 for row in rows if row.success) / max(len(rows), 1)
        reliability = "high" if overall_success >= 0.8 else ("medium" if overall_success >= 0.55 else "low")

        if preferred_tools:
            state.inferred_work_style["preferred_tools"] = preferred_tools
            state.current_state["workflow_reliability"] = reliability
            state.temporal_patterns["workflow"] = {
                "preferred_tools": preferred_tools,
                "reliability": reliability,
                "recent_tool_runs": len(rows),
            }
            state.evidence_backed_hypotheses.append(
                {
                    "id": "hypothesis:workflow_tool_affinity",
                    "description": "The user tends to trust and repeat a small set of tools that have worked recently.",
                    "confidence": _confidence_from_sample(len(rows), base=0.62, ceil=0.82),
                    "source_signals": ["workflow_tool_affinity", "workflow_tool_reliability"],
                }
            )
            self._append_signal(
                state,
                "workflow_tool_affinity",
                value=preferred_tools,
                confidence=_confidence_from_sample(len(rows), base=0.64, ceil=0.84),
                freshness="medium",
            )

        self._append_signal(
            state,
            "workflow_tool_reliability",
            value={"reliability": reliability, "success_rate": round(overall_success, 3)},
            confidence=_confidence_from_sample(len(rows), base=0.6, ceil=0.8),
            freshness="medium",
        )

    async def _apply_content_signals(self, user_id: UUID, state: UserInsightState) -> None:
        since = _utcnow() - timedelta(days=self.CAPSULE_WINDOW_DAYS)
        result = await self.db.execute(
            select(CapsuleFavorite, CuriosityCapsule)
            .join(CuriosityCapsule, CuriosityCapsule.id == CapsuleFavorite.capsule_id)
            .where(
                CapsuleFavorite.user_id == user_id,
                CapsuleFavorite.created_at >= since,
                CuriosityCapsule.deleted_at.is_(None),
            )
        )
        rows = list(result.all())
        if not rows:
            return

        depth_counts: Counter[str] = Counter()
        subject_counts: Counter[str] = Counter()
        shared_count = 0
        for _favorite, capsule in rows:
            depth = getattr(capsule.depth_level, "value", capsule.depth_level) or "unknown"
            depth_counts[str(depth)] += 1
            subject = str(capsule.related_subject or "").strip()
            if subject:
                subject_counts[subject] += 1
            shared_count += int(capsule.share_count or 0)

        top_depth = depth_counts.most_common(1)[0][0] if depth_counts else ""
        top_subjects = [subject for subject, _count in subject_counts.most_common(3)]
        sample_size = len(rows)

        if top_depth and top_depth != "unknown":
            state.stable_preferences["content_depth_preference"] = top_depth
            self._append_signal(
                state,
                "capsule_depth_preference",
                value=top_depth,
                confidence=_confidence_from_sample(sample_size, base=0.6, ceil=0.78),
                freshness="medium",
            )

        if top_subjects:
            state.stable_preferences["content_subject_affinities"] = top_subjects
            self._append_signal(
                state,
                "capsule_subject_affinity",
                value=top_subjects,
                confidence=_confidence_from_sample(sample_size, base=0.62, ceil=0.8),
                freshness="medium",
            )

        state.temporal_patterns["content"] = {
            "favorite_capsule_count": sample_size,
            "top_subjects": top_subjects,
            "shared_capsule_count": shared_count,
        }
        state.evidence_backed_hypotheses.append(
            {
                "id": "hypothesis:content_revisit_preference",
                "description": "Saved capsule patterns suggest the user benefits from revisitable, curated content slices.",
                "confidence": _confidence_from_sample(sample_size, base=0.58, ceil=0.76),
                "source_signals": ["capsule_depth_preference", "capsule_subject_affinity"],
            }
        )

    async def _apply_accountability_signals(self, user_id: UUID, state: UserInsightState) -> None:
        partnership_result = await self.db.execute(
            select(AccountabilityPartnership).where(
                AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
                or_(
                    AccountabilityPartnership.initiator_id == user_id,
                    AccountabilityPartnership.partner_id == user_id,
                ),
            )
        )
        partnerships = list(partnership_result.scalars().all())

        since = _utcnow() - timedelta(days=self.ACCOUNTABILITY_WINDOW_DAYS)
        checkin_result = await self.db.execute(
            select(AccountabilityCheckin).where(
                AccountabilityCheckin.user_id == user_id,
                AccountabilityCheckin.created_at >= since,
            )
        )
        checkins = list(checkin_result.scalars().all())

        if not partnerships and not checkins:
            return

        support_level = "active" if partnerships else "self_guided"
        if partnerships and not checkins:
            support_level = "available"
        rhythm = "steady" if len(checkins) >= 3 else ("light" if checkins else "inactive")

        state.inferred_work_style["accountability_support"] = support_level
        state.current_state["accountability_rhythm"] = rhythm
        state.temporal_patterns["community"] = {
            "active_partnerships": len(partnerships),
            "recent_checkins": len(checkins),
            "rhythm": rhythm,
        }
        state.evidence_backed_hypotheses.append(
            {
                "id": "hypothesis:accountability_loop",
                "description": "A live accountability loop can be used as gentle external structure.",
                "confidence": _confidence_from_sample(len(partnerships) + len(checkins), base=0.6, ceil=0.8),
                "source_signals": ["accountability_support", "accountability_rhythm"],
            }
        )
        self._append_signal(
            state,
            "accountability_support",
            value={"support_level": support_level, "active_partnerships": len(partnerships)},
            confidence=_confidence_from_sample(len(partnerships), base=0.66, ceil=0.82),
            freshness="medium",
        )
        self._append_signal(
            state,
            "accountability_rhythm",
            value={"rhythm": rhythm, "recent_checkins": len(checkins)},
            confidence=_confidence_from_sample(len(checkins), base=0.58, ceil=0.76),
            freshness="medium" if checkins else "low",
        )

    def _apply_uncertainty_markers(self, state: UserInsightState) -> None:
        if not state.goals:
            state.uncertainty_markers.append(
                {
                    "id": "uncertainty:goal_shape",
                    "description": "Goal shape is still thin and may need explicit confirmation.",
                }
            )
        if not state.current_state.get("active_subjects"):
            state.uncertainty_markers.append(
                {
                    "id": "uncertainty:active_subjects",
                    "description": "Current active learning scope is still sparse.",
                }
            )
        if not any(
            state.stable_preferences.get(key) is not None
            for key in ("daily_cap", "weekly_hours", "available_hours")
        ):
            state.uncertainty_markers.append(
                {
                    "id": "uncertainty:capacity_hours",
                    "description": "Reliable time-capacity data is still missing.",
                }
            )
