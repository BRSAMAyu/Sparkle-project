"""
AdaptiveReplanner - Automatic plan adjustments and replanning trigger.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger

from app.config import settings
from app.orchestration.plan_review_service import plan_review_service
from app.services.plan_progress_service import PlanHealthReport, PlanProgressService
from app.services.plan_state_service import PlanStateService
from app.services.learning_event_service import LearningEventService

if TYPE_CHECKING:
    from app.orchestration.step_feedback_collector import PlanExecutionFeedback


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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

    async def on_plan_execution_completed(
        self,
        user_id: UUID,
        plan_id: UUID,
        feedback: "PlanExecutionFeedback",
    ) -> dict[str, Any]:
        """Handle feedback from DAG plan execution.

        Persists step-level feedback to PlanState and triggers
        replanning if the execution signals warrant it.
        """
        # 1. Persist execution feedback to PlanState.feedback_log
        feedback_entry = self._build_feedback_entry(
            feedback_type="plan_execution",
            content=(
                f"Plan execution completed: {feedback.validation_status}, "
                f"score={feedback.quality_score:.2f}, "
                f"{feedback.steps_passed}/{feedback.total_steps} steps passed"
            ),
            task_id=None,
            applied_adjustment={
                "quality_score": feedback.quality_score,
                "slow_tools": feedback.slow_tools,
                "failed_tools": feedback.failed_tools,
                "unreliable_dependencies": feedback.unreliable_dependencies,
                "failed_step_types": feedback.failed_step_types,
                "aborted": feedback.aborted,
            },
        )

        adaptive_facts: dict[str, Any] = {}
        if feedback.slow_tools:
            adaptive_facts["known_slow_tools"] = feedback.slow_tools
        if feedback.failed_tools:
            adaptive_facts["recently_failed_tools"] = feedback.failed_tools
        if feedback.unreliable_dependencies:
            adaptive_facts["unreliable_dep_steps"] = feedback.unreliable_dependencies
        if feedback.failed_step_types:
            adaptive_facts["failed_step_types"] = feedback.failed_step_types

        patch: dict[str, Any] = {"feedback_log": feedback_entry}
        if adaptive_facts:
            patch["facts"] = adaptive_facts

        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch=patch,
            bump_version=False,
        )

        local_repair_result: dict[str, Any] = {
            "applied": False,
            "repair_actions": [],
            "triggered_replan": False,
        }

        # 2. Trigger replanning if execution feedback warrants it
        if feedback.needs_replanning:
            if bool(getattr(settings, "ENABLE_PLAN_REPAIR_V1", False)):
                local_repair_result = await self._attempt_local_repair(
                    user_id=user_id,
                    plan_id=plan_id,
                    feedback=feedback,
                )
                if local_repair_result.get("applied"):
                    return local_repair_result

            state = await self.plan_state_service.get_plan_state(user_id, plan_id)
            if state and not self._recently_triggered(
                state.facts or {}, "last_replan_at", self.AUTO_REPLAN_COOLDOWN,
            ):
                replan_reason = (
                    f"Execution feedback: {feedback.validation_status}, "
                    f"failed_tools={feedback.failed_tools}"
                )
                await plan_review_service.trigger_replanning(
                    plan_id=str(plan_id),
                    user_id=str(user_id),
                    feedback=replan_reason,
                )
                # Mark replan timestamp
                await self.plan_state_service.upsert_plan_state(
                    user_id=user_id,
                    plan_id=plan_id,
                    patch={
                        "facts": {
                            "adaptive_meta": {
                                "last_replan_at": _utcnow().isoformat(),
                                "last_trigger": "plan_execution_feedback",
                                "last_replan_reason": [replan_reason],
                            }
                        }
                    },
                    bump_version=True,
                )
                logger.info(
                    "Triggered replan from execution feedback: plan={}, severity={}",
                    plan_id, feedback.severity,
                )
                local_repair_result["triggered_replan"] = True
        return local_repair_result

    async def _attempt_local_repair(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        feedback: "PlanExecutionFeedback",
    ) -> dict[str, Any]:
        repair_actions = self._derive_repair_actions(feedback)
        if not repair_actions:
            return {"applied": False, "repair_actions": [], "triggered_replan": False}

        event_service = LearningEventService(redis_client=self.redis)
        await event_service.emit(
            event_type="plan_repair_triggered",
            user_id=str(user_id),
            workflow_id=str(plan_id),
            data={
                "repair_actions": repair_actions,
                "failed_tools": list(feedback.failed_tools),
                "failed_step_types": dict(feedback.failed_step_types or {}),
                "quality_score": float(feedback.quality_score),
            },
        )

        patch = {
            "facts": {
                "adaptive_meta": {
                    "last_local_repair_at": _utcnow().isoformat(),
                    "last_local_repair_actions": repair_actions,
                },
                "local_repair_actions": repair_actions,
            },
            "feedback_log": self._build_feedback_entry(
                feedback_type="plan_repair",
                content=f"Local repair actions applied: {', '.join(repair_actions)}",
                task_id=None,
                applied_adjustment={
                    "repair_actions": repair_actions,
                    "failed_tools": list(feedback.failed_tools),
                    "failed_step_types": dict(feedback.failed_step_types or {}),
                },
            ),
        }
        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch=patch,
            bump_version=True,
        )

        await event_service.emit(
            event_type="plan_repair_succeeded",
            user_id=str(user_id),
            workflow_id=str(plan_id),
            data={
                "repair_actions": repair_actions,
                "quality_score": float(feedback.quality_score),
            },
        )
        return {
            "applied": True,
            "repair_actions": repair_actions,
            "triggered_replan": False,
        }

    @staticmethod
    def _derive_repair_actions(feedback: "PlanExecutionFeedback") -> list[str]:
        actions: list[str] = []
        if feedback.failed_tools:
            actions.append("replace_failed_tools")
        if feedback.slow_tools:
            actions.append("degrade_parallelism")
        if feedback.unreliable_dependencies:
            actions.append("strengthen_dependency_order")
        if feedback.failed_step_types.get("timeout", 0) > 0:
            actions.append("increase_timeout_budget")
        if feedback.failed_step_types.get("missing_output", 0) > 0:
            actions.append("tighten_output_schema")
        return actions[:5]

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

        now = _utcnow().isoformat()
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
        now = _utcnow().isoformat()
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
        return _utcnow() - last_time < cooldown

    def _build_feedback_entry(
        self,
        feedback_type: str,
        content: str,
        task_id: UUID | None,
        applied_adjustment: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "id": f"fb-{uuid.uuid4().hex[:8]}",
            "timestamp": _utcnow().isoformat(),
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
