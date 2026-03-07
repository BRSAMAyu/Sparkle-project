"""
AdaptiveReplanner - Automatic plan adjustments and replanning trigger.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select

from app.models.cognitive import BehaviorPattern
from app.orchestration.dual_core_router import AdaptationRecord
from app.orchestration.plan_review_service import plan_review_service
from app.services.personalization.preference_service import PreferenceService
from app.services.plan_progress_service import PlanHealthReport, PlanProgressService
from app.services.plan_state_service import PlanStateService
from app.services.system_update_service import SystemUpdateService, build_system_update

if TYPE_CHECKING:
    from app.orchestration.step_feedback_collector import PlanExecutionFeedback


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass
class PlanParameterAdjustment:
    parameter: str
    value: Any
    reason: str
    pattern_name: str
    confidence_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "value": self.value,
            "reason": self.reason,
            "pattern_name": self.pattern_name,
            "confidence_score": self.confidence_score,
        }


class CognitivePatternTrigger:
    """
    Map high-confidence cognitive patterns to deterministic plan constraints.
    """

    MAX_ADJUSTMENTS_PER_RUN = 3
    MIN_CONFIDENCE = 0.7

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.preference_service = PreferenceService(db, redis)

    async def build_adjustments(
        self,
        *,
        user_id: UUID,
        existing_constraints: dict[str, Any] | None,
        limit: int | None = None,
        pattern_name: str | None = None,
    ) -> list[PlanParameterAdjustment]:
        result = await self.db.execute(
            select(BehaviorPattern)
            .where(BehaviorPattern.user_id == user_id)
            .where(BehaviorPattern.is_archived.is_(False))
            .where(BehaviorPattern.confidence_score >= self.MIN_CONFIDENCE)
            .order_by(desc(BehaviorPattern.confidence_score), desc(BehaviorPattern.frequency))
            .limit(12)
        )
        patterns = list(result.scalars().all())
        if pattern_name:
            filtered = [pattern for pattern in patterns if pattern_name.lower() in str(pattern.pattern_name or "").lower()]
            if filtered:
                patterns = filtered

        prefs = await self.preference_service.get_preferences(user_id)
        explicit = getattr(prefs, "explicit", {}) or {}
        constraints = dict(existing_constraints or {})
        locked = ((constraints.get("_meta") or {}).get("locked_parameters") or [])
        sources = ((constraints.get("_meta") or {}).get("constraint_sources") or {})

        adjustments: list[PlanParameterAdjustment] = []
        seen_parameters: set[str] = set()
        for pattern in patterns:
            for adjustment in self._map_pattern(pattern):
                if adjustment.parameter in seen_parameters:
                    continue
                if self._is_locked(
                    adjustment=adjustment,
                    explicit_preferences=explicit,
                    existing_constraints=constraints,
                    locked_parameters=locked,
                    sources=sources,
                ):
                    continue
                adjustments.append(adjustment)
                seen_parameters.add(adjustment.parameter)
                if len(adjustments) >= (limit or self.MAX_ADJUSTMENTS_PER_RUN):
                    return adjustments
        return adjustments

    def _map_pattern(self, pattern: BehaviorPattern) -> list[PlanParameterAdjustment]:
        name = str(pattern.pattern_name or "").lower()
        description = str(pattern.description or "").lower()
        confidence = float(pattern.confidence_score or 0.0)
        adjustments: list[PlanParameterAdjustment] = []

        def add(parameter: str, value: Any, reason: str) -> None:
            adjustments.append(
                PlanParameterAdjustment(
                    parameter=parameter,
                    value=value,
                    reason=f"{reason}（检测到 {pattern.pattern_name}，置信度 {confidence:.2f}）",
                    pattern_name=str(pattern.pattern_name or ""),
                    confidence_score=confidence,
                )
            )

        if any(token in name for token in ["planning optimism", "乐观偏差", "低估", "underestimate"]) or "planning.underestimate" in description:
            add("task_duration_multiplier", 1.3, "检测到计划乐观偏差")
            add("phase_count_delta", 1, "检测到计划乐观偏差")

        if any(token in name for token in ["番茄钟逃避", "pomodoro", "启动困难", "task resistance"]):
            add("max_session_minutes", 20, "检测到执行启动阻力")
            add("require_start_ritual_micro_task", True, "检测到执行启动阻力")

        if any(token in name for token in ["放弃", "abandon", "连续放弃", "stall", "inactive"]):
            add("difficulty_shift_delta", -1, "检测到连续放弃或停滞模式")
            add("require_min_completion_unit", True, "检测到连续放弃或停滞模式")

        if any(token in name for token in ["过度规划", "overplanning", "焦虑"]) and pattern.pattern_type == "emotional":
            add("max_concurrent_tasks", 3, "检测到焦虑驱动的过度规划")
            add("hide_distant_phases", True, "检测到焦虑驱动的过度规划")

        if any(token in name for token in ["完美主义", "perfection"]) or "80分" in description:
            add("quality_bar", "eighty_percent", "检测到完美主义阻塞")
            add("guidance_style", "good_enough", "检测到完美主义阻塞")

        if (
            any(token in name for token in ["blindspot", "前置知识不足", "基础不足", "知识缺口"])
            or "前置" in description
            or "prerequisite" in description
        ):
            add("insert_prerequisite_review", True, "检测到前置知识不足")
            weak_nodes = [item for item in (pattern.evidence_ids or []) if isinstance(item, str)]
            if weak_nodes:
                add("weak_knowledge_node_ids", weak_nodes[:5], "检测到前置知识不足")

        return adjustments

    @staticmethod
    def _is_locked(
        *,
        adjustment: PlanParameterAdjustment,
        explicit_preferences: dict[str, Any],
        existing_constraints: dict[str, Any],
        locked_parameters: list[str],
        sources: dict[str, Any],
    ) -> bool:
        if adjustment.parameter in locked_parameters:
            return True
        if adjustment.parameter in existing_constraints and str(sources.get(adjustment.parameter) or "").startswith("user"):
            return True
        if adjustment.parameter == "max_session_minutes" and explicit_preferences.get("focus_duration_preference") not in (None, ""):
            return True
        return False


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
        self.cognitive_pattern_trigger = CognitivePatternTrigger(db, redis)

    async def on_task_completed(
        self,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        completion_rate: float | None = None,
    ) -> list[AdaptationRecord]:
        report = await self.progress_service.evaluate_progress(user_id, plan_id)
        return await self._handle_report(
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
    ) -> list[AdaptationRecord]:
        report = await self.progress_service.evaluate_progress(user_id, plan_id)
        return await self._handle_report(
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
    ) -> list[AdaptationRecord]:
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

        patch: dict[str, Any] = {"feedback_log": feedback_entry}
        if adaptive_facts:
            patch["facts"] = adaptive_facts

        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch=patch,
            bump_version=False,
        )

        # 2. Trigger replanning if execution feedback warrants it
        if feedback.needs_replanning:
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
                record = AdaptationRecord(
                    what_changed="触发了当前计划的自动重规划",
                    why=(
                        f"执行反馈显示质量状态为 {feedback.validation_status}，"
                        f"失败工具={feedback.failed_tools}"
                    ),
                    expected_effect="下一轮计划会重新评估失败步骤和依赖，降低重复卡住的概率。",
                    user_facing_message="我发现这轮执行里有关键步骤卡住了，下一轮会重新帮你收紧计划。",
                    source="adaptive_replanner",
                )
                await self._enqueue_adaptation_update(user_id, record, update_type="plan_adaptation")
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
                                "recent_adaptations": [record.to_dict()],
                            }
                        }
                    },
                    bump_version=True,
                )
                logger.info(
                    "Triggered replan from execution feedback: plan={}, severity={}",
                    plan_id, feedback.severity,
                )
                return [record]
        cognitive_records = await self._apply_cognitive_pattern_adjustments(user_id=user_id, plan_id=plan_id)
        return cognitive_records

    async def on_behavior_pattern_detected(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        pattern_name: str | None = None,
    ) -> list[AdaptationRecord]:
        return await self._apply_cognitive_pattern_adjustments(
            user_id=user_id,
            plan_id=plan_id,
            pattern_name=pattern_name,
        )

    async def _handle_report(
        self,
        report: PlanHealthReport,
        trigger: str,
        task_id: UUID | None = None,
        completion_rate: float | None = None,
        feedback_category: str | None = None,
        difficulty_delta: float | None = None,
    ) -> list[AdaptationRecord]:
        cognitive_records = await self._apply_cognitive_pattern_adjustments(
            user_id=report.user_id,
            plan_id=report.plan_id,
        )
        if not report.requires_adjustment:
            return cognitive_records

        state = await self.plan_state_service.get_plan_state(report.user_id, report.plan_id)
        if not state:
            return cognitive_records

        if report.recommended_action == "replan":
            if self._recently_triggered(state.facts, "last_replan_at", self.AUTO_REPLAN_COOLDOWN):
                return cognitive_records
            return cognitive_records + await self._trigger_full_replan(
                report,
                trigger=trigger,
                task_id=task_id,
                completion_rate=completion_rate,
                feedback_category=feedback_category,
            )
        else:
            if self._recently_triggered(state.facts, "last_adjustment_at", self.AUTO_ADJUSTMENT_COOLDOWN):
                return cognitive_records
            return cognitive_records + await self._apply_incremental_adjustment(
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
    ) -> list[AdaptationRecord]:
        state = await self.plan_state_service.get_plan_state(report.user_id, report.plan_id)
        if not state:
            return []

        adjustments = self._calculate_adjustments(state.facts or {}, report, difficulty_delta)
        if not adjustments:
            return []

        now = _utcnow().isoformat()
        existing_meta = (state.facts or {}).get("adaptive_meta", {})
        adaptive_meta = dict(existing_meta)
        adaptive_meta["last_adjustment_at"] = now
        adaptive_meta["last_trigger"] = trigger
        record = self._build_adjustment_record(report, adjustments, feedback_category)
        recent = list(adaptive_meta.get("recent_adaptations", []) or [])
        recent.append(record.to_dict())
        adaptive_meta["recent_adaptations"] = recent[-10:]
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
        await self._enqueue_adaptation_update(report.user_id, record, update_type="plan_adaptation")
        return [record]

    async def _trigger_full_replan(
        self,
        report: PlanHealthReport,
        trigger: str,
        task_id: UUID | None = None,
        completion_rate: float | None = None,
        feedback_category: str | None = None,
    ) -> list[AdaptationRecord]:
        now = _utcnow().isoformat()
        record = self._build_replan_record(report, feedback_category)
        adaptive_facts = {
            "adaptive_meta": {
                "last_replan_at": now,
                "last_trigger": trigger,
                "last_replan_reason": report.reasons,
                "recent_adaptations": [record.to_dict()],
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
        await self._enqueue_adaptation_update(report.user_id, record, update_type="plan_adaptation")
        return [record]

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

    async def _apply_cognitive_pattern_adjustments(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        pattern_name: str | None = None,
    ) -> list[AdaptationRecord]:
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        if not state:
            return []

        adjustments = await self.cognitive_pattern_trigger.build_adjustments(
            user_id=user_id,
            existing_constraints=state.constraints or {},
            pattern_name=pattern_name,
        )
        if not adjustments:
            return []

        current_constraints = dict(state.constraints or {})
        meta = dict(current_constraints.get("_meta") or {})
        sources = dict(meta.get("constraint_sources") or {})
        history = list(current_constraints.get("cognitive_pattern_adjustments") or [])

        applied_records: list[AdaptationRecord] = []
        applied_patch: dict[str, Any] = {}

        for adjustment in adjustments:
            current_value = current_constraints.get(adjustment.parameter)
            if current_value == adjustment.value:
                continue
            applied_patch[adjustment.parameter] = adjustment.value
            sources[adjustment.parameter] = f"cognitive_pattern:{adjustment.pattern_name}"
            history.append(adjustment.to_dict())
            applied_records.append(self._build_pattern_adaptation_record(adjustment))

        if not applied_patch:
            return []

        meta["constraint_sources"] = sources
        current_constraints.update(applied_patch)
        current_constraints["cognitive_pattern_adjustments"] = history[-10:]
        current_constraints["_meta"] = meta

        feedback_entry = self._build_feedback_entry(
            feedback_type="cognitive_pattern_adjustment",
            content="Applied plan constraints from high-confidence cognitive patterns",
            task_id=None,
            applied_adjustment={"constraints": current_constraints.get("cognitive_pattern_adjustments", [])[-len(applied_records):]},
        )

        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"constraints": current_constraints, "feedback_log": feedback_entry},
            bump_version=True,
        )

        adaptive_meta = dict(((state.facts or {}).get("adaptive_meta")) or {})
        recent = list(adaptive_meta.get("recent_adaptations", []) or [])
        recent.extend([record.to_dict() for record in applied_records])
        adaptive_meta["recent_adaptations"] = recent[-10:]
        adaptive_meta["last_pattern_adjustment_at"] = _utcnow().isoformat()
        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={"facts": {"adaptive_meta": adaptive_meta}},
            bump_version=False,
        )

        for record in applied_records:
            await self._enqueue_adaptation_update(user_id, record, update_type="plan_adaptation")

        logger.info(
            "Applied {} cognitive-pattern constraints for plan {}",
            len(applied_records),
            plan_id,
        )
        return applied_records

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

    def _build_adjustment_record(
        self,
        report: PlanHealthReport,
        adjustments: dict[str, Any],
        feedback_category: str | None,
    ) -> AdaptationRecord:
        adaptive = adjustments.get("adaptive_adjustments", {}) if isinstance(adjustments, dict) else {}
        change_parts: list[str] = []
        if "difficulty_shift" in adaptive:
            change_parts.append(f"把任务难度偏移调整为 {adaptive['difficulty_shift']}")
        if "time_multiplier" in adaptive:
            change_parts.append(f"把任务时长预算系数调整为 {adaptive['time_multiplier']}")
        what_changed = "；".join(change_parts) or "调整了当前计划的执行参数"

        metrics = report.metrics or {}
        evidence_parts: list[str] = []
        if metrics.get("overrun_count"):
            evidence_parts.append(f"最近 {metrics['overrun_count']} 次任务出现超时")
        too_difficult = ((metrics.get("feedback_stats") or {}).get("too_difficult", 0))
        if too_difficult:
            evidence_parts.append(f"最近有 {too_difficult} 次反馈“太难”")
        if feedback_category:
            evidence_parts.append(f"最近一次反馈分类是 {feedback_category}")
        why = "，且".join(evidence_parts) if evidence_parts else f"计划健康度触发了 {', '.join(report.reasons)}"

        expected_parts: list[str] = []
        if "time_multiplier" in adaptive:
            expected_parts.append("给每步任务更多缓冲时间")
        if "difficulty_shift" in adaptive and adaptive["difficulty_shift"] < 0:
            expected_parts.append("降低任务启动门槛")
        elif "difficulty_shift" in adaptive and adaptive["difficulty_shift"] > 0:
            expected_parts.append("适度提高挑战强度")
        expected_effect = "，".join(expected_parts) if expected_parts else "让后续任务更贴近你当前的执行状态。"

        if "difficulty_too_hard" in report.reasons or too_difficult >= 2:
            message = "我发现你最近的任务偏难了，帮你调轻了一些。"
        elif "time_overrun" in report.reasons:
            message = "我发现你最近的任务经常超时，帮你把节奏放宽了一点。"
        else:
            message = "我根据你最近的执行反馈，微调了当前计划。"

        return AdaptationRecord(
            what_changed=what_changed,
            why=why,
            expected_effect=expected_effect,
            user_facing_message=message,
            source="adaptive_replanner",
        )

    def _build_replan_record(
        self,
        report: PlanHealthReport,
        feedback_category: str | None,
    ) -> AdaptationRecord:
        why_parts = [f"计划健康度达到 {report.severity}"]
        if report.reasons:
            why_parts.append(f"触发原因：{', '.join(report.reasons)}")
        if feedback_category:
            why_parts.append(f"最新反馈：{feedback_category}")
        return AdaptationRecord(
            what_changed="重新规划了当前阶段的执行路径",
            why="；".join(why_parts),
            expected_effect="重新收紧阶段目标与任务节奏，避免沿着当前失效路径继续推进。",
            user_facing_message="我发现原来的推进方式已经不够合适，准备帮你重新收紧这段计划。",
            source="adaptive_replanner",
        )

    def _build_pattern_adaptation_record(self, adjustment: PlanParameterAdjustment) -> AdaptationRecord:
        effect_map = {
            "task_duration_multiplier": "预计后续任务会预留更多缓冲时间。",
            "phase_count_delta": "计划会拆成更细的阶段，降低每段落差。",
            "max_session_minutes": "单次任务会更短，更容易启动。",
            "require_start_ritual_micro_task": "开始执行前会先安排启动仪式型微任务。",
            "difficulty_shift_delta": "后续任务难度会临时下调一档。",
            "require_min_completion_unit": "我会优先给你最小可完成单元。",
            "max_concurrent_tasks": "同时推进的任务数量会被收紧。",
            "hide_distant_phases": "先聚焦眼前阶段，减少远期噪音。",
            "quality_bar": "质量门槛会放到更容易启动的水平。",
            "guidance_style": "后续表达会更强调先完成再打磨。",
            "insert_prerequisite_review": "当前任务前会补上必要的前置复习。",
            "weak_knowledge_node_ids": "我会把薄弱知识点纳入下一轮计划。",
        }
        message_map = {
            "task_duration_multiplier": "我发现你的计划总是偏乐观，帮你预留了更多缓冲时间。",
            "phase_count_delta": "我把这段计划拆得更细了一些，方便你稳步推进。",
            "max_session_minutes": "我发现你更容易卡在启动阶段，先把单次任务压短一些。",
            "require_start_ritual_micro_task": "我给你补了一个更容易起步的启动动作。",
            "difficulty_shift_delta": "我发现你最近阻力偏大，先把难度调轻了一档。",
            "require_min_completion_unit": "我把目标拆成了更小的完成单元，先让你更容易做完。",
            "max_concurrent_tasks": "我注意到你在反复调整计划，先帮你锁定最重要的 3 件事。",
            "hide_distant_phases": "我先把远期阶段收起来，避免你被过多规划压住。",
            "quality_bar": "我先把完成标准放到更现实的水平，避免你被完美主义卡住。",
            "guidance_style": "我会提醒你先做到 80 分，再考虑继续打磨。",
            "insert_prerequisite_review": "我发现这块前置基础还不稳，先补一层再往前推进。",
            "weak_knowledge_node_ids": "我把你当前的薄弱知识点也纳入后续计划了。",
        }
        return AdaptationRecord(
            what_changed=f"将约束 {adjustment.parameter} 调整为 {adjustment.value}",
            why=adjustment.reason,
            expected_effect=effect_map.get(adjustment.parameter, "让计划更贴近你当前的执行状态。"),
            user_facing_message=message_map.get(adjustment.parameter, "我根据你的行为模式，微调了当前计划。"),
            source="cognitive_pattern_trigger",
        )

    async def _enqueue_adaptation_update(
        self,
        user_id: UUID,
        record: AdaptationRecord,
        *,
        update_type: str,
    ) -> None:
        await SystemUpdateService(self.redis).enqueue(
            user_id,
            build_system_update(
                update_type=update_type,
                category="evolution",
                title="系统已根据你的状态调整",
                description=record.user_facing_message,
                priority="low",
                metadata={
                    "evolution_kind": "adaptation_record",
                    "adaptation_record": record.to_dict(),
                },
            ),
        )
