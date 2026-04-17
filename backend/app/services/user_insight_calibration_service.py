from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import OUTCOME_LEARNING_CONFLICTS_TOTAL, VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL
from app.core.profile_context import ProfileContext
from app.core.user_insight_state import UserInsightState
from app.models.card_protocol import InterventionOutcomeStatus
from app.models.intervention_strategy_outcome import InterventionStrategyOutcome
from app.models.memory import MemoryCorrection


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _strip(value: Any) -> str:
    return str(value or "").strip()


class UserInsightCalibrationService:
    """Calibrate the canonical insight state using outcomes, corrections, and evidence aging."""

    CORRECTION_WINDOW_DAYS = 90
    OUTCOME_WINDOW_DAYS = 60
    NON_EFFECTIVE_STATUSES = {"corrected", "scoped"}
    SIGNAL_TO_STABLE_PREFERENCE_KEYS = {
        "capsule_depth_preference": ["content_depth_preference"],
        "capsule_subject_affinity": ["content_subject_affinities"],
    }
    SIGNAL_TO_CURRENT_STATE_KEYS = {
        "calendar_density": ["calendar_density_level"],
        "workflow_tool_reliability": ["workflow_reliability"],
        "accountability_rhythm": ["accountability_rhythm"],
    }
    SIGNAL_TO_WORK_STYLE_KEYS = {
        "achievement_peak_hours": ["achievement_peak_hours"],
        "achievement_motivation_response": ["achievement_motivation_response"],
        "achievement_pace_style": ["achievement_pace_style"],
        "achievement_reward_sensitivity": ["achievement_reward_sensitivity"],
        "peak_focus_hours": ["peak_focus_hours"],
        "inactive_push_hours": ["inactive_push_hours"],
        "workflow_tool_affinity": ["preferred_tools"],
        "accountability_support": ["accountability_support"],
    }
    SIGNAL_TO_TEMPORAL_KEYS = {
        "achievement_peak_hours": [("achievement", "peak_hours")],
        "achievement_motivation_response": [("achievement", "motivation_response")],
        "achievement_pace_style": [("achievement", "pace_style")],
        "achievement_reward_sensitivity": [("achievement", "reward_sensitivity")],
        "calendar_density": [
            ("calendar", "density_level"),
            ("calendar", "avg_events_per_day"),
            ("calendar", "avg_minutes_per_day"),
        ],
        "calendar_recurring_windows": [("calendar", "recurring_windows")],
        "peak_focus_hours": [("calendar", "peak_focus_hours")],
        "inactive_push_hours": [("calendar", "inactive_push_hours")],
        "exam_urgency": [("calendar", "exam_urgency")],
        "workflow_tool_affinity": [("workflow", "preferred_tools"), ("workflow", "recent_tool_runs")],
        "workflow_tool_reliability": [("workflow", "reliability")],
        "capsule_subject_affinity": [("content", "top_subjects")],
        "accountability_support": [("community", "active_partnerships")],
        "accountability_rhythm": [("community", "recent_checkins"), ("community", "rhythm")],
    }
    SIGNAL_TO_CONSTRAINT_IDS = {
        "calendar_recurring_windows": {"calendar:recurring_windows"},
        "inactive_push_hours": {"calendar:inactive_push_hours"},
    }
    SIGNAL_TO_GOAL_IDS = {
        "exam_urgency": {"goal:exam_window", "goal:exam_pressure"},
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def calibrate(
        self,
        *,
        user_id: UUID,
        state: UserInsightState,
        profile_context: ProfileContext,
    ) -> dict[str, Any]:
        corrections = await self._load_recent_corrections(user_id)
        outcomes = await self._load_recent_strategy_outcomes(user_id)

        correction_summary = self._summarize_corrections(corrections)
        outcome_summary = self._summarize_outcomes(outcomes)
        scope_overrides = self._scope_overrides(profile_context)

        demoted_signals = self._apply_signal_calibration(
            state=state,
            correction_summary=correction_summary,
            scope_overrides=scope_overrides,
        )
        promotion_summary = self._apply_hypothesis_calibration(
            state=state,
            correction_summary=correction_summary,
            outcome_summary=outcome_summary,
        )
        stale_signals = self._apply_evidence_aging(
            state=state,
            correction_summary=correction_summary,
            outcome_summary=outcome_summary,
        )
        inactive_effective_signals = self._apply_effective_signal_pruning(
            state=state,
            stale_signals=stale_signals,
        )
        prediction_adjustments = self._apply_prediction_calibration(
            state=state,
            correction_summary=correction_summary,
            outcome_summary=outcome_summary,
        )

        if correction_summary["total"] >= 2:
            state.uncertainty_markers.append(
                {
                    "id": "uncertainty:user_corrections_active",
                    "description": "Recent user corrections are active, so Sparkle should state uncertainty more explicitly.",
                }
            )

        summary = {
            "correction_window_days": self.CORRECTION_WINDOW_DAYS,
            "outcome_window_days": self.OUTCOME_WINDOW_DAYS,
            "recent_correction_count": correction_summary["total"],
            "recent_corrections": correction_summary["recent_items"][:5],
            "correction_targets": correction_summary["targets"],
            "strategy_outcome_sample_count": outcome_summary["sample_count"],
            "strategy_effective_rate": outcome_summary["effective_rate"],
            "strategy_ineffective_rate": outcome_summary["ineffective_rate"],
            "acted_rate": outcome_summary["acted_rate"],
            "demoted_signals": demoted_signals,
            "promoted_hypotheses": promotion_summary["promoted"],
            "demoted_hypotheses": promotion_summary["demoted"],
            "stale_signals": stale_signals,
            "inactive_effective_signals": inactive_effective_signals,
            "prediction_adjustments": prediction_adjustments,
            "scope_overrides": scope_overrides,
            "calibration_posture": self._calibration_posture(
                correction_summary=correction_summary,
                outcome_summary=outcome_summary,
            ),
        }
        state.calibration_summary = summary
        return summary

    def reapply_prediction_adjustments(
        self,
        *,
        state: UserInsightState,
        calibration_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        correction_summary = {
            "total": int(calibration_summary.get("recent_correction_count") or 0),
        }
        outcome_summary = {
            "effective_rate": float(calibration_summary.get("strategy_effective_rate") or 0.0),
            "ineffective_rate": float(calibration_summary.get("strategy_ineffective_rate") or 0.0),
        }
        adjustments = self._apply_prediction_calibration(
            state=state,
            correction_summary=correction_summary,
            outcome_summary=outcome_summary,
        )
        calibration_summary["prediction_adjustments"] = adjustments
        return adjustments

    async def _load_recent_corrections(self, user_id: UUID) -> list[MemoryCorrection]:
        since = _utcnow() - timedelta(days=self.CORRECTION_WINDOW_DAYS)
        result = await self.db.execute(
            select(MemoryCorrection).where(
                MemoryCorrection.user_id == user_id,
                MemoryCorrection.deleted_at.is_(None),
                MemoryCorrection.created_at >= since,
            )
        )
        return list(result.scalars().all())

    async def _load_recent_strategy_outcomes(self, user_id: UUID) -> list[InterventionStrategyOutcome]:
        since = _utcnow() - timedelta(days=self.OUTCOME_WINDOW_DAYS)
        result = await self.db.execute(
            select(InterventionStrategyOutcome).where(
                InterventionStrategyOutcome.user_id == user_id,
                InterventionStrategyOutcome.deleted_at.is_(None),
                InterventionStrategyOutcome.created_at >= since,
            )
        )
        return list(result.scalars().all())

    def _summarize_corrections(self, corrections: list[MemoryCorrection]) -> dict[str, Any]:
        targets: dict[str, int] = {}
        recent_items: list[dict[str, Any]] = []
        for correction in corrections:
            payload = self._parse_correction_reason(correction.reason)
            target = _strip(payload.get("target_id") or payload.get("field_name") or correction.memory_type)
            if target:
                targets[target] = targets.get(target, 0) + 1
            recent_items.append(
                {
                    "action": _strip(correction.action),
                    "target": target,
                    "reason": _strip(payload.get("reason") or correction.reason),
                    "created_at": correction.created_at.isoformat() if correction.created_at else "",
                }
            )
        recent_items.sort(key=lambda item: item["created_at"], reverse=True)
        return {
            "total": len(corrections),
            "targets": targets,
            "recent_items": recent_items,
        }

    def _summarize_outcomes(self, outcomes: list[InterventionStrategyOutcome]) -> dict[str, Any]:
        sample_count = len(outcomes)
        if sample_count == 0:
            return {
                "sample_count": 0,
                "effective_rate": 0.0,
                "ineffective_rate": 0.0,
                "acted_rate": 0.0,
            }

        effective = sum(1 for item in outcomes if item.outcome == InterventionOutcomeStatus.EFFECTIVE)
        ineffective = sum(1 for item in outcomes if item.outcome == InterventionOutcomeStatus.INEFFECTIVE)
        acted = sum(1 for item in outcomes if _strip(item.acceptance_status.value) == "ACTED")
        return {
            "sample_count": sample_count,
            "effective_rate": round(effective / sample_count, 3),
            "ineffective_rate": round(ineffective / sample_count, 3),
            "acted_rate": round(acted / sample_count, 3),
        }

    def _scope_overrides(self, profile_context: ProfileContext) -> dict[str, Any]:
        value = (profile_context.preferences or {}).get("insight_scope_overrides")
        return dict(value) if isinstance(value, dict) else {}

    def _apply_signal_calibration(
        self,
        *,
        state: UserInsightState,
        correction_summary: dict[str, Any],
        scope_overrides: dict[str, Any],
    ) -> list[dict[str, Any]]:
        demoted: list[dict[str, Any]] = []
        targets = correction_summary["targets"]

        for evidence in state.signal_evidence:
            target_hits = targets.get(evidence.signal_id, 0)
            if target_hits <= 0:
                if evidence.signal_id in scope_overrides:
                    evidence.status = "scoped"
                continue

            original_confidence = float(state.confidence_metadata.get(evidence.signal_id, evidence.confidence or 0.0))
            new_confidence = max(0.2, round(original_confidence - min(0.3, target_hits * 0.12), 3))
            state.confidence_metadata[evidence.signal_id] = new_confidence
            evidence.confidence = new_confidence
            evidence.freshness = "low"
            evidence.status = "corrected"
            demoted.append(
                {
                    "signal_id": evidence.signal_id,
                    "reason": "user_correction",
                    "previous_confidence": original_confidence,
                    "new_confidence": new_confidence,
                }
            )
            OUTCOME_LEARNING_CONFLICTS_TOTAL.labels(layer="user_insight", reason="user_correction").inc()

        return demoted

    def _apply_hypothesis_calibration(
        self,
        *,
        state: UserInsightState,
        correction_summary: dict[str, Any],
        outcome_summary: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        promoted: list[dict[str, Any]] = []
        demoted: list[dict[str, Any]] = []

        corrected_targets = correction_summary["targets"]
        effective_rate = float(outcome_summary["effective_rate"] or 0.0)
        sample_count = int(outcome_summary["sample_count"] or 0)

        for hypothesis in state.evidence_backed_hypotheses:
            hypothesis_id = _strip(hypothesis.get("id"))
            source_signals = [_strip(item) for item in (hypothesis.get("source_signals") or []) if _strip(item)]
            has_corrected_source = any(corrected_targets.get(signal_id, 0) > 0 for signal_id in source_signals)
            confidence_bound = float(hypothesis.get("confidence_bound") or hypothesis.get("confidence") or 0.55)

            if has_corrected_source:
                hypothesis["status"] = "demoted"
                hypothesis["stability"] = "fragile"
                hypothesis["confidence_bound"] = max(0.2, round(confidence_bound - 0.2, 3))
                demoted.append({"id": hypothesis_id, "reason": "user_correction"})
                OUTCOME_LEARNING_CONFLICTS_TOTAL.labels(layer="user_insight", reason="hypothesis_demoted").inc()
                continue

            if sample_count >= 3 and effective_rate >= 0.66 and hypothesis.get("status") in {"provisional", "watch"}:
                hypothesis["status"] = "promoted"
                hypothesis["stability"] = "stable" if effective_rate >= 0.75 else "emerging"
                hypothesis["confidence_bound"] = min(0.95, round(confidence_bound + 0.1, 3))
                promoted.append({"id": hypothesis_id, "reason": "outcome_consistency"})
                VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL.labels(
                    layer="user_insight",
                    direction="hypothesis_promoted",
                ).inc()

        return {"promoted": promoted, "demoted": demoted}

    def _apply_evidence_aging(
        self,
        *,
        state: UserInsightState,
        correction_summary: dict[str, Any],
        outcome_summary: dict[str, Any],
    ) -> list[str]:
        stale: list[str] = []

        for signal_id, freshness in list(state.freshness_metadata.items()):
            if freshness == "low":
                stale.append(signal_id)
                continue
            if correction_summary["targets"].get(signal_id, 0) > 0:
                state.freshness_metadata[signal_id] = "low"
                stale.append(signal_id)

        return list(dict.fromkeys(stale))

    def _apply_prediction_calibration(
        self,
        *,
        state: UserInsightState,
        correction_summary: dict[str, Any],
        outcome_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        adjustments: list[dict[str, Any]] = []
        correction_total = int(correction_summary["total"] or 0)
        correction_penalty = min(0.24, correction_total * 0.06)
        outcome_bonus = 0.0
        if correction_total == 0 and float(outcome_summary["effective_rate"] or 0.0) >= 0.66:
            outcome_bonus = 0.06
        outcome_penalty = 0.08 if float(outcome_summary["ineffective_rate"] or 0.0) >= 0.5 else 0.0

        for key, payload in state.prediction_summaries.items():
            if not isinstance(payload, dict):
                continue
            current_confidence = float(payload.get("confidence") or 0.55)
            calibrated = max(0.2, min(0.92, round(current_confidence - correction_penalty - outcome_penalty + outcome_bonus, 3)))
            payload["calibrated_confidence"] = calibrated
            payload["calibration_status"] = (
                "supported"
                if calibrated >= current_confidence
                else "bounded_down"
            )
            adjustments.append(
                {
                    "prediction": key,
                    "previous_confidence": current_confidence,
                    "calibrated_confidence": calibrated,
                }
            )
        return adjustments

    def _apply_effective_signal_pruning(
        self,
        *,
        state: UserInsightState,
        stale_signals: list[str],
    ) -> list[str]:
        ineffective_signal_ids = self._ineffective_signal_ids(state=state, stale_signals=stale_signals)
        if not ineffective_signal_ids:
            return []

        self._prune_mapping(
            container=state.stable_preferences,
            mapping=self.SIGNAL_TO_STABLE_PREFERENCE_KEYS,
            ineffective_signal_ids=ineffective_signal_ids,
        )
        self._prune_mapping(
            container=state.current_state,
            mapping=self.SIGNAL_TO_CURRENT_STATE_KEYS,
            ineffective_signal_ids=ineffective_signal_ids,
        )
        self._prune_mapping(
            container=state.inferred_work_style,
            mapping=self.SIGNAL_TO_WORK_STYLE_KEYS,
            ineffective_signal_ids=ineffective_signal_ids,
        )
        self._prune_temporal_patterns(state=state, ineffective_signal_ids=ineffective_signal_ids)
        self._prune_constraints(state=state, ineffective_signal_ids=ineffective_signal_ids)
        self._prune_goals(state=state, ineffective_signal_ids=ineffective_signal_ids)
        self._prune_hypotheses(state=state, ineffective_signal_ids=ineffective_signal_ids)
        return sorted(ineffective_signal_ids)

    def _ineffective_signal_ids(self, *, state: UserInsightState, stale_signals: list[str]) -> set[str]:
        stale_signal_set = {_strip(item) for item in stale_signals if _strip(item)}
        ineffective_signal_ids: set[str] = set(stale_signal_set)
        for evidence in state.signal_evidence:
            status = _strip(evidence.status).lower()
            if status in self.NON_EFFECTIVE_STATUSES:
                ineffective_signal_ids.add(evidence.signal_id)
        return ineffective_signal_ids

    @staticmethod
    def _prune_mapping(
        *,
        container: dict[str, Any],
        mapping: dict[str, list[str]],
        ineffective_signal_ids: set[str],
    ) -> None:
        for signal_id in ineffective_signal_ids:
            for key in mapping.get(signal_id, []):
                container.pop(key, None)

    def _prune_temporal_patterns(self, *, state: UserInsightState, ineffective_signal_ids: set[str]) -> None:
        for signal_id in ineffective_signal_ids:
            for section, key in self.SIGNAL_TO_TEMPORAL_KEYS.get(signal_id, []):
                payload = state.temporal_patterns.get(section)
                if isinstance(payload, dict):
                    payload.pop(key, None)
                    if not payload:
                        state.temporal_patterns.pop(section, None)

    def _prune_constraints(self, *, state: UserInsightState, ineffective_signal_ids: set[str]) -> None:
        blocked_ids: set[str] = set()
        for signal_id in ineffective_signal_ids:
            blocked_ids.update(self.SIGNAL_TO_CONSTRAINT_IDS.get(signal_id, set()))
        if blocked_ids:
            state.constraints = [item for item in state.constraints if _strip(item.get("id")) not in blocked_ids]

    def _prune_goals(self, *, state: UserInsightState, ineffective_signal_ids: set[str]) -> None:
        blocked_ids: set[str] = set()
        for signal_id in ineffective_signal_ids:
            blocked_ids.update(self.SIGNAL_TO_GOAL_IDS.get(signal_id, set()))
        if blocked_ids:
            state.goals = [item for item in state.goals if _strip(item.get("id")) not in blocked_ids]

    @staticmethod
    def _prune_hypotheses(*, state: UserInsightState, ineffective_signal_ids: set[str]) -> None:
        state.evidence_backed_hypotheses = [
            hypothesis
            for hypothesis in state.evidence_backed_hypotheses
            if not any(
                _strip(signal_id) in ineffective_signal_ids
                for signal_id in (hypothesis.get("source_signals") or [])
            )
        ]

    @staticmethod
    def _calibration_posture(
        *,
        correction_summary: dict[str, Any],
        outcome_summary: dict[str, Any],
    ) -> str:
        if correction_summary["total"] >= 3:
            return "correction_heavy"
        if outcome_summary["sample_count"] >= 3 and outcome_summary["effective_rate"] >= 0.66:
            return "supported"
        if outcome_summary["sample_count"] == 0:
            return "uncalibrated"
        return "mixed"

    @staticmethod
    def _parse_correction_reason(value: str | None) -> dict[str, Any]:
        raw = _strip(value)
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}
