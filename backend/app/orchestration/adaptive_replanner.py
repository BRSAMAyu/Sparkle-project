"""
AdaptiveReplanner - Automatic plan adjustments and replanning trigger.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger

from app.orchestration.plan_review_service import plan_review_service
from app.services.plan_progress_service import PlanHealthReport, PlanProgressService
from app.services.plan_state_service import PlanStateService


class AdaptiveReplanner:
    """
    Evaluates plan health and triggers incremental adjustments or replanning.
    """

    AUTO_ADJUSTMENT_COOLDOWN = timedelta(hours=2)
    AUTO_REPLAN_COOLDOWN = timedelta(hours=12)

    def __init__(
        self,
        db,
        redis=None,
        progress_service: PlanProgressService | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.progress_service = progress_service or PlanProgressService(db, redis)
        self.plan_state_service = PlanStateService(db, redis)

    async def on_task_completed(
        self,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        completion_rate: float | None = None,
    ) -> None:
        report = await self.progress_service.evaluate_progress(user_id, plan_id)
        await self._handle_report(
            report,
            trigger="task_completed",
            task_id=task_id,
            completion_rate=completion_rate,
        )

    async def on_task_feedback(
        self,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        category: str | None = None,
        difficulty_delta: float | None = None,
    ) -> None:
        report = await self.progress_service.evaluate_progress(user_id, plan_id)
        await self._handle_report(
            report,
            trigger="task_feedback",
            task_id=task_id,
            feedback_category=category,
            difficulty_delta=difficulty_delta,
        )

    async def _handle_report(
        self,
        report: PlanHealthReport,
        trigger: str,
        task_id: UUID | None = None,
        completion_rate: float | None = None,
        feedback_category: str | None = None,
        difficulty_delta: float | None = None,
    ) -> None:
        if not report.requires_adjustment:
            return

        state = await self.plan_state_service.get_plan_state(report.user_id, report.plan_id)
        if not state:
            return

        if report.recommended_action == "replan":
            if self._recently_triggered(state.facts, "last_replan_at", self.AUTO_REPLAN_COOLDOWN):
                return
            await self._trigger_full_replan(
                report,
                trigger=trigger,
                task_id=task_id,
                completion_rate=completion_rate,
                feedback_category=feedback_category,
            )
        else:
            if self._recently_triggered(state.facts, "last_adjustment_at", self.AUTO_ADJUSTMENT_COOLDOWN):
                return
            await self._apply_incremental_adjustment(
                report,
                trigger=trigger,
                task_id=task_id,
                completion_rate=completion_rate,
                difficulty_delta=difficulty_delta,
                feedback_category=feedback_category,
            )

    async def _apply_incremental_adjustment(
        self,
        report: PlanHealthReport,
        trigger: str,
        task_id: UUID | None = None,
        completion_rate: float | None = None,
        difficulty_delta: float | None = None,
        feedback_category: str | None = None,
    ) -> None:
        state = await self.plan_state_service.get_plan_state(report.user_id, report.plan_id)
        if not state:
            return

        adjustments = self._calculate_adjustments(state.facts or {}, report, difficulty_delta)
        if not adjustments:
            return

        now = datetime.utcnow().isoformat()
        existing_meta = (state.facts or {}).get("adaptive_meta", {})
        adaptive_meta = dict(existing_meta)
        adaptive_meta["last_adjustment_at"] = now
        adaptive_meta["last_trigger"] = trigger
        adjustments["adaptive_meta"] = adaptive_meta

        feedback_entry = self._build_feedback_entry(
            feedback_type="auto_adjustment",
            content=self._format_adjustment_message(report),
            task_id=task_id,
            applied_adjustment=adjustments,
        )

        await self.plan_state_service.upsert_plan_state(
            user_id=report.user_id,
            plan_id=report.plan_id,
            patch={"facts": adjustments, "feedback_log": feedback_entry},
            bump_version=True,
        )

        logger.info(
            "Applied incremental adjustment for plan {}: {}",
            report.plan_id,
            adjustments,
        )

    async def _trigger_full_replan(
        self,
        report: PlanHealthReport,
        trigger: str,
        task_id: UUID | None = None,
        completion_rate: float | None = None,
        feedback_category: str | None = None,
    ) -> None:
        now = datetime.utcnow().isoformat()
        adaptive_facts = {
            "adaptive_meta": {
                "last_replan_at": now,
                "last_trigger": trigger,
                "last_replan_reason": report.reasons,
            }
        }

        feedback_entry = self._build_feedback_entry(
            feedback_type="auto_replan",
            content=self._format_replan_message(report),
            task_id=task_id,
            applied_adjustment={
                "replan_reason": report.reasons,
                "completion_rate": completion_rate,
                "feedback_category": feedback_category,
                "severity": report.severity,
            },
        )

        await self.plan_state_service.upsert_plan_state(
            user_id=report.user_id,
            plan_id=report.plan_id,
            patch={"facts": adaptive_facts, "feedback_log": feedback_entry},
            bump_version=True,
        )

        await plan_review_service.trigger_replanning(
            plan_id=str(report.plan_id),
            user_id=str(report.user_id),
            feedback=self._format_replan_message(report),
        )

        logger.info("Triggered auto-replan for plan {}", report.plan_id)

    def _calculate_adjustments(
        self,
        facts: dict[str, Any],
        report: PlanHealthReport,
        difficulty_delta: float | None,
    ) -> dict[str, Any]:
        adjustments: dict[str, Any] = {}
        adaptive = dict(facts.get("adaptive_adjustments", {}))

        time_multiplier = adaptive.get("time_multiplier", 1.0)
        difficulty_shift = adaptive.get("difficulty_shift", 0.0)

        if "time_overrun" in report.reasons:
            time_multiplier = min(2.0, round(time_multiplier + 0.15, 2))

        if "difficulty_too_hard" in report.reasons:
            difficulty_shift = max(-0.5, round(difficulty_shift - 0.1, 2))

        if "difficulty_too_easy" in report.reasons:
            difficulty_shift = min(0.5, round(difficulty_shift + 0.1, 2))

        if difficulty_delta:
            difficulty_shift = max(-0.5, min(0.5, round(difficulty_shift + difficulty_delta * 0.1, 2)))

        if time_multiplier != adaptive.get("time_multiplier", 1.0):
            adaptive["time_multiplier"] = time_multiplier
        if difficulty_shift != adaptive.get("difficulty_shift", 0.0):
            adaptive["difficulty_shift"] = difficulty_shift

        if adaptive:
            adjustments["adaptive_adjustments"] = adaptive

        return adjustments

    def _recently_triggered(
        self,
        facts: dict[str, Any],
        key: str,
        cooldown: timedelta,
    ) -> bool:
        adaptive_meta = (facts or {}).get("adaptive_meta", {})
        last_str = adaptive_meta.get(key)
        if not last_str:
            return False
        try:
            last_time = datetime.fromisoformat(last_str)
        except Exception:
            return False
        return datetime.utcnow() - last_time < cooldown

    def _build_feedback_entry(
        self,
        feedback_type: str,
        content: str,
        task_id: UUID | None,
        applied_adjustment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "id": f"fb-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.utcnow().isoformat(),
            "type": feedback_type,
            "content": content,
        }
        if task_id:
            entry["task_id"] = str(task_id)
        if applied_adjustment:
            entry["applied_adjustment"] = applied_adjustment
        return entry

    def _format_adjustment_message(self, report: PlanHealthReport) -> str:
        return f"Auto adjustment applied based on: {', '.join(report.reasons)}"

    def _format_replan_message(self, report: PlanHealthReport) -> str:
        return f"Auto replan triggered due to: {', '.join(report.reasons)}"
