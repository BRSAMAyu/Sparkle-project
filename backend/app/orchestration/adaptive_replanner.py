"""
Core: <cognitive|execution|bridge|infra>
Phase: <sense|clarify|plan|execute|reflect|reinforce|adapt|none>
Stage: <首次引入 Stage 号>

AdaptiveReplanner - Automatic plan adjustments and replanning trigger.
"""

from __future__ import annotations

import uuid
import re
from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select, update

from app.core.business_metrics import ADAPTIVE_ADJUSTMENT_SKIPPED_TOTAL, ADAPTIVE_ROLLBACK_TOTAL
from app.core.event_bus import event_bus
from app.models.card_protocol import Card, CardType
from app.models.cognitive import BehaviorPattern
from app.models.plan import Plan
from app.models.task import SubTask, SubTaskStatus, Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.orchestration.dual_core_router import AdaptationRecord
from app.orchestration.plan_revision_summary import PlanRevisionSummary
from app.orchestration.plan_review_service import plan_review_service
from app.services.personalization.preference_service import PreferenceService
from app.services.plan_adjustment_applier import PlanAdjustmentApplier
from app.services.plan_health_signal_service import PlanHealthSignalService
from app.services.plan_progress_service import PlanHealthReport, PlanProgressService
from app.services.plan_state_service import PlanStateService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.services.card_protocol.replanner_bridge import ReplannerCardBridge
from app.services.task_service import _sync_task_card_projection

if TYPE_CHECKING:
    from app.orchestration.step_feedback_collector import PlanExecutionFeedback


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        try:
            value = value.to_dict()
        except Exception:
            return {}
    return value if isinstance(value, dict) else {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _task_status_value(task: Task) -> str:
    return str(getattr(task.status, "value", task.status) or "")


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
        failed_adjustments: list[dict[str, Any]] | None = None,
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
                if self._matches_failed_adjustment(adjustment, failed_adjustments or []):
                    ADAPTIVE_ADJUSTMENT_SKIPPED_TOTAL.labels(reason="previously_failed").inc()
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

        if any(token in name for token in ["delegation aversion", "委派抗拒", "delegation_takeback"]):
            add("auto_delegate_suggestion", False, "检测到用户对 AI 委派存在明显抗拒")
            add("require_human_confirmation", True, "检测到用户对 AI 委派存在明显抗拒")

        if any(token in name for token in ["delegation trust building", "委派信任建立"]):
            add("auto_delegate_suggestion", True, "检测到用户已建立对 AI 委派的稳定信任")

        if any(token in name for token in ["execution time learning", "ai duration", "委派时长学习"]):
            multiplier_match = re.search(r"multiplier=([0-9]+(?:\.[0-9]+)?)", pattern.description or "")
            if multiplier_match:
                try:
                    multiplier = float(multiplier_match.group(1))
                except ValueError:
                    multiplier = None
                if multiplier is not None:
                    add("ai_duration_multiplier", round(multiplier, 2), "根据近期委派执行结果校准 AI 执行时长")

        if any(token in name for token in ["execution type preference", "类型偏好", "type preference"]):
            add("type_delegation_routing", "adaptive", "检测到用户对不同执行类型有不同委派偏好")

        if any(token in name for token in ["execution quality sensitivity", "质量敏感"]):
            add("execution_result_detail", "adaptive", "检测到用户对执行结果质量阈值更敏感")

        if any(token in name for token in ["execution safety concern", "安全顾虑"]):
            add("require_human_confirmation", True, "检测到用户对执行安全存在顾虑")
            add("auto_delegate_suggestion", False, "检测到用户对执行安全存在顾虑")

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

    @staticmethod
    def _direction(value: Any) -> str:
        if isinstance(value, bool):
            return "enable" if value else "disable"
        if isinstance(value, (int, float)):
            if value > 0:
                return "increase"
            if value < 0:
                return "decrease"
            return "stable"
        text = str(value or "").strip().lower()
        if text in {"lower", "lighter", "shorter", "finer", "good_enough", "eighty_percent"}:
            return "decrease"
        if text in {"higher", "more", "longer", "preserve"}:
            return "increase"
        return text or "unknown"

    @classmethod
    def _matches_failed_adjustment(
        cls,
        adjustment: PlanParameterAdjustment,
        failed_adjustments: list[dict[str, Any]],
    ) -> bool:
        parameter = str(adjustment.parameter or "").strip()
        direction = cls._direction(adjustment.value)
        for item in failed_adjustments:
            if not isinstance(item, dict):
                continue
            if str(item.get("constraint_key") or "").strip() != parameter:
                continue
            if str(item.get("direction") or "").strip() == direction:
                return True
        return False


class AdaptiveReplanner:
    """
    Evaluates plan health and triggers incremental adjustments or replanning.
    """

    AUTO_ADJUSTMENT_COOLDOWN = timedelta(hours=2)
    AUTO_REPLAN_COOLDOWN = timedelta(hours=12)
    STRUGGLE_COOLDOWN_BYPASS_THRESHOLD = 2
    SNAPSHOT_HISTORY_LIMIT = 3
    NEGATIVE_FEEDBACK_CATEGORIES = {"too_difficult", "too_long", "unclear", "irrelevant"}
    STRONG_COGNITIVE_STRUGGLE_MARKERS = (
        "不理解",
        "搞不懂",
        "看不懂",
        "不会",
        "没思路",
        "concept",
        "confus",
        "don't understand",
        "do not understand",
    )
    TIME_PRESSURE_MARKERS = ("没时间", "来不及", "时间不够", "太赶", "排不开", "没空")
    BEHIND_MARKERS = ("落后", "没完成", "没做完", "没跟上", "跑偏", "没搞定")
    REPEATED_FAILURE_MARKERS = ("连续", "又没", "还是没", "再次", "一直")

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
        self.plan_adjustment_applier = PlanAdjustmentApplier(db, redis)
        self.plan_health_signal_service = PlanHealthSignalService(db, redis)
        self.cognitive_pattern_trigger = CognitivePatternTrigger(db, redis)
        self._card_bridge: ReplannerCardBridge | None = None

    @classmethod
    def should_compress(cls, *, completion_rate: float | None, days_left: int | None) -> bool:
        """Trigger sprint compression only when the user is behind and time is short."""
        try:
            rate = float(completion_rate)
            days = int(float(days_left))
        except (TypeError, ValueError):
            return False
        if days < 0:
            return False
        return rate < 0.5 and days <= 5

    @classmethod
    def build_compressed_sprint_day_spec(
        cls,
        *,
        day_number: int,
        completion_rate: float,
        sprint_policy: dict[str, Any],
        source_daily_spec: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        policy = _as_dict(sprint_policy)
        retrieval_policy = _as_dict(policy.get("retrieval_policy"))
        fail_safe = _as_dict(policy.get("fail_safe") or retrieval_policy.get("fail_safe"))
        behind_rule = _strip(fail_safe.get("behind")) or "下一天只保留 1 个核心任务和 1 个最小输出。"
        minimum_output = (
            _strip(policy.get("minimum_output"))
            or _strip(retrieval_policy.get("minimum_output"))
            or "闭卷复述、3题小测或一道典型题独立完成"
        )
        source_spec = _as_dict(source_daily_spec)
        subject_strategy = _as_dict(source_spec.get("subject_strategy"))
        node_labels = [
            _strip(item)
            for item in list(subject_strategy.get("node_labels") or [])
            if _strip(item)
        ]
        primary_target = (
            _strip(subject_strategy.get("primary_node_label"))
            or (node_labels[0] if node_labels else "")
            or _strip(source_spec.get("primary_target"))
            or _strip(source_spec.get("title_focus"))
            or "最高收益核心点"
        )
        days_left = _safe_int(policy.get("days_left") or policy.get("actual_days_left") or policy.get("total_days"))
        if days_left is None:
            days_left = 5
        completion_pct = max(0, min(100, int(round(float(completion_rate) * 100))))
        day_number = max(1, int(day_number or 1))
        compression_reason = (
            f"前一天完成率只有 {completion_pct}%，低于 50%，而距离考试只剩 {days_left} 天；"
            f"所以 Day {day_number} 自动压缩为保底版：{behind_rule}"
        )
        objective = f"Day {day_number} 保底恢复：只拿下「{primary_target}」，并留下 1 个最小输出。"
        output_action = f"围绕「{primary_target}」完成 {minimum_output}。"
        success_criteria = f"只要完成「{primary_target}」的 {minimum_output}，今天就算把主线接回来了。"
        return {
            "day": day_number,
            "focus": objective,
            "title_focus": "压缩保底",
            "task_kind": "compressed_recovery",
            "estimated_minutes": 35,
            "minimum_output": minimum_output,
            "primary_target": primary_target,
            "optional_tasks": [],
            "compressed": True,
            "completion_rate": float(completion_rate),
            "compression_reason": compression_reason,
            "output_action": output_action,
            "success_criteria": success_criteria,
            "objective": objective,
            "method_steps": [
                f"先锁定 1 个核心点：{primary_target}。",
                f"只做 1 个最小输出：{minimum_output}。",
                "完成后写一句明天从哪里继续，不把今天扩成补完整章。",
            ],
            "fail_safe_rule": behind_rule,
            "daily_spec": {
                "day": day_number,
                "task_kind": "compressed_recovery",
                "compressed": True,
                "primary_target": primary_target,
                "minimum_output": minimum_output,
                "optional_tasks": [],
                "estimated_minutes": 35,
                "compression_reason": compression_reason,
            },
        }

    async def compress_sprint_day(
        self,
        *,
        plan_id: UUID | None = None,
        day_number: int = 1,
        completion_rate: float,
        sprint_policy: dict[str, Any],
        source_daily_spec: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Compress one sprint day to a single recovery task and persist it when possible."""
        compressed_spec = self.build_compressed_sprint_day_spec(
            day_number=day_number,
            completion_rate=completion_rate,
            sprint_policy=sprint_policy,
            source_daily_spec=source_daily_spec,
        )
        if plan_id is not None and getattr(self, "db", None) is not None:
            await self._write_compressed_sprint_day(
                plan_id=plan_id,
                day_number=day_number,
                compressed_spec=compressed_spec,
            )
        return [compressed_spec]

    async def _write_compressed_sprint_day(
        self,
        *,
        plan_id: UUID,
        day_number: int,
        compressed_spec: dict[str, Any],
    ) -> None:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id, Plan.not_deleted_filter()))
        plan = result.scalar_one_or_none()
        if plan is None:
            return

        day_number = max(1, int(day_number or 1))
        user_id = plan.user_id
        metadata = _as_dict(plan.source_metadata).copy()
        daily_specs = _as_dict(metadata.get("daily_specs")).copy()
        daily_specs[str(day_number)] = compressed_spec
        compressions = _as_dict(metadata.get("adaptive_compressions")).copy()
        compressions[str(day_number)] = {
            "day": day_number,
            "compressed": True,
            "compression_reason": compressed_spec["compression_reason"],
            "completion_rate": compressed_spec.get("completion_rate"),
            "task_kind": "compressed_recovery",
        }
        metadata["daily_specs"] = daily_specs
        metadata["adaptive_compressions"] = compressions
        plan.source_metadata = metadata
        self.db.add(plan)

        day_start = day_number * 1000
        day_end = (day_number + 1) * 1000
        task_result = await self.db.execute(
            select(Task)
            .where(Task.plan_id == plan_id, Task.not_deleted_filter())
            .where(Task.order_index >= day_start, Task.order_index < day_end)
            .order_by(Task.order_index.asc(), Task.created_at.asc())
        )
        day_tasks = list(task_result.scalars().all())
        kept_task = next(
            (task for task in day_tasks if _task_status_value(task) != TaskStatus.COMPLETED.value),
            day_tasks[0] if day_tasks else None,
        )

        if kept_task is not None:
            existing_guide = _as_dict(kept_task.guide_json).copy()
            kept_task.title = f"Day {day_number} · 压缩保底 - {_strip(compressed_spec.get('primary_target'))}"
            kept_task.estimated_minutes = min(_safe_int(compressed_spec.get("estimated_minutes")) or 35, 35)
            kept_task.difficulty = 1
            kept_task.energy_cost = 1
            kept_task.guide_content = _strip(compressed_spec.get("objective"))
            kept_task.success_criteria = _strip(compressed_spec.get("success_criteria"))
            kept_task.order_index = day_start
            kept_task.guide_json = {
                **existing_guide,
                **compressed_spec,
                "time_estimate_minutes": kept_task.estimated_minutes,
                "daily_spec": compressed_spec["daily_spec"],
            }
            tags = list(kept_task.tags or [])
            for tag in ("compressed_recovery", "sprint_fail_safe", "adaptive_compressed", f"day:{day_number}"):
                if tag not in tags:
                    tags.append(tag)
            kept_task.tags = tags
            self.db.add(kept_task)

        for task in day_tasks:
            if kept_task is not None and task.id == kept_task.id:
                continue
            if _task_status_value(task) == TaskStatus.COMPLETED.value:
                continue
            task.soft_delete()
            self.db.add(task)

        await self.db.commit()
        if kept_task is not None:
            await self.db.refresh(kept_task)
            await _sync_task_card_projection(self.db, kept_task)

        try:
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan.id,
                patch={
                    "facts": {
                        "daily_spec": {str(day_number): compressed_spec},
                        "adaptive_compressions": compressions,
                    }
                },
            )
        except Exception as exc:
            logger.warning("Failed to persist compressed daily_spec for plan {}: {}", plan_id, exc)

    async def on_task_completed(
        self,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        completion_rate: float | None = None,
    ) -> list[AdaptationRecord]:
        await self._maybe_record_breakdown_feedback(
            user_id=user_id,
            plan_id=plan_id,
            task_id=task_id,
            completion_status="completed",
        )
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
        feedback_text: str | None = None,
    ) -> list[AdaptationRecord]:
        await self._maybe_record_breakdown_feedback(
            user_id=user_id,
            plan_id=plan_id,
            task_id=task_id,
            completion_status="feedback",
            feedback_category=category,
        )
        rollback_records = await self._maybe_rollback_after_feedback(
            user_id=user_id,
            plan_id=plan_id,
            feedback_category=category,
            task_id=task_id,
        )
        if rollback_records:
            return rollback_records
        trigger = (
            "task_feedback_struggle"
            if self.is_strong_cognitive_struggle_feedback(category=category, feedback_text=feedback_text)
            else "task_feedback"
        )
        return await self.evaluate_plan_health_now(
            user_id=user_id,
            plan_id=plan_id,
            trigger=trigger,
            task_id=task_id,
            feedback_category=category,
            difficulty_delta=difficulty_delta,
        )

    async def adjust_for_checkpoint(
        self,
        user_id: UUID,
        plan_id: UUID,
        debrief_result: dict[str, Any],
    ) -> Task | None:
        """Insert one focused remedial task when checkpoint debrief shows the phase slipped."""
        if bool(debrief_result.get("goal_met", True)):
            return None

        result = await self.db.execute(
            select(Task)
            .where(Task.user_id == user_id, Task.plan_id == plan_id)
            .where(Task.status != TaskStatus.COMPLETED)
            .where(Task.title.not_like("[复盘补强]%"))
            .order_by(Task.order_index.asc(), Task.created_at.asc())
            .limit(1)
        )
        next_task = result.scalar_one_or_none()
        insert_order = int(next_task.order_index or 0) if next_task else 0
        if insert_order <= 0:
            insert_order = 1000

        await self.db.execute(
            update(Task)
            .where(Task.user_id == user_id, Task.plan_id == plan_id, Task.order_index >= insert_order)
            .values(order_index=Task.order_index + 1)
        )

        checkpoint_day = int(debrief_result.get("checkpoint_day") or 0)
        checkpoint_description = str(debrief_result.get("checkpoint_description") or "检查点内容").strip()
        recovery = self._checkpoint_recovery_contract(
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
            first_answer=str(debrief_result.get("first_answer") or ""),
            second_answer=str(debrief_result.get("second_answer") or ""),
        )
        title = f"[复盘补强] Day {checkpoint_day} 检查点回顾" if checkpoint_day else "[复盘补强] 检查点回顾"
        guide_json = {
            "objective": recovery["objective"],
            "method_steps": recovery["method_steps"],
            "time_estimate_minutes": recovery["time_estimate_minutes"],
            "output_action": recovery["output_action"],
            "success_criteria": recovery["success_criteria"],
            "key_points": [checkpoint_description, "优先补影响下一阶段的漏洞"],
            "common_mistakes": ["只承认落后，但没有定位到具体知识点或时间问题。"],
            "sprint_fail_safe": True,
            "density_adjustment": recovery["density_adjustment"],
            "scaffolding_mode": recovery["scaffolding_mode"],
            "micro_contract": recovery["micro_contract"],
            "fail_safe_rule": recovery["fail_safe_rule"],
        }
        task = Task(
            user_id=user_id,
            plan_id=plan_id,
            title=title,
            type=TaskType.REFLECTION,
            tags=[
                "checkpoint_remedial",
                "review",
                "scaffolded",
                "reduced_density",
                "sprint_fail_safe",
                *list(recovery["tags"]),
                f"checkpoint_day:{checkpoint_day}",
            ],
            estimated_minutes=recovery["time_estimate_minutes"],
            difficulty=recovery["difficulty"],
            energy_cost=recovery["energy_cost"],
            guide_content=guide_json["objective"],
            guide_json=guide_json,
            ai_prompt=(
                f"【背景】我正在做第 {checkpoint_day} 天检查点复盘。\n"
                f"【检查点】{checkpoint_description}\n"
                f"【我的状态】{recovery['state_summary']}\n"
                f"【输出动作】{recovery['output_action']}\n"
                f"【完成标准】{recovery['success_criteria']}\n"
                f"【请帮我】定位最影响后续计划的薄弱点，给我一个 {recovery['time_estimate_minutes']} 分钟内能完成的补强路径。"
            ),
            success_criteria=guide_json["success_criteria"],
            status=TaskStatus.PENDING,
            priority=1,
            order_index=insert_order,
            phase_index=getattr(next_task, "phase_index", None) if next_task else None,
            source_planning_session_id=getattr(next_task, "source_planning_session_id", None) if next_task else None,
            due_date=getattr(next_task, "due_date", None) if next_task else None,
        )
        self.db.add(task)
        await self.db.flush()
        await _sync_task_card_projection(self.db, task)
        return task

    async def break_down_single_task_for_too_hard(
        self,
        *,
        user_id: UUID,
        task_id: UUID,
        feedback_text: str | None = None,
    ) -> list[SubTask]:
        """
        Split one currently-too-hard task into smaller subtasks.

        This is intentionally task-local: it does not rewrite the plan or move
        neighboring tasks. The surrounding plan can still learn from the signal
        through PlanState feedback and normal health evaluation later.
        """
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if task is None:
            return []

        breakdown_items = await self._generate_too_hard_breakdown(
            task=task,
            feedback_text=feedback_text,
        )
        if not breakdown_items:
            breakdown_items = self._fallback_too_hard_breakdown(task)

        order_result = await self.db.execute(
            select(SubTask)
            .where(SubTask.parent_task_id == task.id)
            .order_by(desc(SubTask.order))
            .limit(1)
        )
        last_subtask = order_result.scalar_one_or_none()
        next_order = int(last_subtask.order + 1) if last_subtask else 0

        created: list[SubTask] = []
        for index, raw_item in enumerate(breakdown_items[:5]):
            normalized = self._normalize_too_hard_subtask(raw_item, index=index, parent_title=task.title)
            if not normalized:
                continue
            subtask = SubTask(
                parent_task_id=task.id,
                title=normalized["title"],
                description=normalized.get("description"),
                estimated_minutes=normalized["estimated_minutes"],
                guide_content=normalized.get("guide_content"),
                order=next_order,
                status=SubTaskStatus.PENDING,
                knowledge_node_id=task.knowledge_node_id,
            )
            self.db.add(subtask)
            created.append(subtask)
            next_order += 1

        if not created:
            return []

        tags = list(task.tags or [])
        for tag in ("too_hard", "adaptive_breakdown"):
            if tag not in tags:
                tags.append(tag)
        task.tags = tags
        task.difficulty = max(1, int(task.difficulty or 1) - 1)
        self.db.add(task)

        try:
            feedback = TaskFeedback(
                user_id=user_id,
                task_id=task.id,
                completion_quality=None,
                feedback_text=feedback_text or "用户在任务卡上标记：太难",
                category="too_difficult",
                task_difficulty_snapshot=task.difficulty,
                task_type_snapshot=task.type.value if task.type else None,
                actual_minutes_snapshot=task.actual_minutes,
            )
            self.db.add(feedback)
        except Exception as exc:
            logger.debug("Failed to attach too-hard feedback row: {}", exc)

        await self.db.flush()
        await self.db.refresh(
            task,
            attribute_names=["subtasks_total", "subtasks_completed"],
        )
        await _sync_task_card_projection(self.db, task)

        if task.plan_id:
            record = AdaptationRecord(
                what_changed=f"把「{task.title}」拆成了 {len(created)} 个更小的步骤",
                why="用户在任务卡上标记了太难，说明当前任务颗粒度超过了可启动范围。",
                expected_effect=(
                    "先把启动门槛降下来，避免因为一张任务卡过重而放弃整段计划。"
                ),
                user_facing_message=f"我把「{task.title}」拆小了，先做第一步就够。",
                source="adaptive_replanner.task_quick_action",
            )
            state = await self.plan_state_service.get_plan_state(user_id, task.plan_id)
            adaptive_meta = dict((((state.facts or {}) if state else {}).get("adaptive_meta")) or {})
            recent = list(adaptive_meta.get("recent_adaptations") or [])
            recent.append(record.to_dict())
            adaptive_meta["recent_adaptations"] = recent[-10:]
            adaptive_meta["last_task_too_hard_at"] = _utcnow().isoformat()
            feedback_entry = self._build_feedback_entry(
                feedback_type="task_quick_action_too_hard",
                content=f"用户将任务标记为太难，已拆成 {len(created)} 个子任务。",
                task_id=task.id,
                applied_adjustment={
                    "inserted_subtask_ids": [str(item.id) for item in created],
                    "difficulty_after": task.difficulty,
                },
            )
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=task.plan_id,
                patch={
                    "facts": {"adaptive_meta": adaptive_meta},
                    "feedback_log": feedback_entry,
                },
                bump_version=False,
            )

        return created

    async def _generate_too_hard_breakdown(
        self,
        *,
        task: Task,
        feedback_text: str | None,
    ) -> list[dict[str, Any]]:
        try:
            from app.services.focus_service import FocusService

            description_parts = [
                str(task.guide_content or "").strip(),
                str(task.success_criteria or "").strip(),
                self._format_task_guide_json(task.guide_json),
                str(feedback_text or "").strip(),
            ]
            description = "\n".join(part for part in description_parts if part)
            persona_prompt = (
                "用户刚刚主动标记这个任务太难。请把任务拆成 3-5 个更小的启动步骤，"
                "每一步控制在 5-20 分钟，第一步必须非常容易开始。"
            )
            result = await FocusService.breakdown_task_via_llm(
                task_title=task.title,
                task_description=description,
                persona_prompt=persona_prompt,
            )
            return [item for item in result if isinstance(item, dict)]
        except Exception as exc:
            logger.warning("Too-hard task breakdown LLM failed for {}: {}", task.id, exc)
            return []

    @staticmethod
    def _format_task_guide_json(guide_json: Any) -> str:
        if not isinstance(guide_json, dict):
            return ""
        parts: list[str] = []
        for key in (
            "objective",
            "method_steps",
            "success_criteria",
            "output_action",
            "if_stuck",
        ):
            value = guide_json.get(key)
            if value in (None, "", []):
                continue
            if isinstance(value, list):
                rendered = "；".join(str(item).strip() for item in value if str(item).strip())
            else:
                rendered = str(value).strip()
            if rendered:
                parts.append(f"{key}: {rendered}")
        return "\n".join(parts)

    @staticmethod
    def _normalize_too_hard_subtask(
        raw_item: dict[str, Any] | str,
        *,
        index: int,
        parent_title: str,
    ) -> dict[str, Any] | None:
        if isinstance(raw_item, str):
            item: dict[str, Any] = {"title": raw_item}
        else:
            item = dict(raw_item)

        title = str(
            item.get("title")
            or item.get("name")
            or item.get("step")
            or f"小步 {index + 1}: {parent_title}"
        ).strip()
        if not title:
            return None

        raw_minutes = (
            item.get("estimated_minutes")
            or item.get("minutes")
            or item.get("duration")
            or 15
        )
        try:
            estimated_minutes = int(float(raw_minutes))
        except (TypeError, ValueError):
            estimated_minutes = 15
        estimated_minutes = max(5, min(30, estimated_minutes))

        description = str(item.get("description") or item.get("detail") or "").strip() or None
        guide_content = str(item.get("guide_content") or item.get("guide") or "").strip()
        if not guide_content:
            guide_content = (
                "这是从“太难”快速操作里拆出来的小步。"
                "只需要完成这一小步，不要顺手加码。"
            )

        return {
            "title": title[:255],
            "description": description,
            "estimated_minutes": estimated_minutes,
            "guide_content": guide_content,
        }

    @staticmethod
    def _fallback_too_hard_breakdown(task: Task) -> list[dict[str, Any]]:
        base_minutes = max(5, min(15, int((task.estimated_minutes or 30) / 3)))
        return [
            {
                "title": f"圈出「{task.title}」里最卡的一点",
                "description": "只定位一个具体卡点，不解决整张任务卡。",
                "estimated_minutes": 5,
                "guide_content": "写下最卡的一句话、一道题或一个步骤。写清楚就算完成。",
            },
            {
                "title": "用自己的话复述这个卡点",
                "description": "把卡点讲成一句能听懂的话，再补一个例子或反例。",
                "estimated_minutes": base_minutes,
                "guide_content": "目标不是完整掌握，而是把最小理解断点补上。",
            },
            {
                "title": "完成一个最小检查动作",
                "description": "做一道最小题、写一个小结，或列出下一步需要问 AI 的问题。",
                "estimated_minutes": base_minutes,
                "guide_content": "只检查刚才那个卡点，不扩展到新的难点。",
            },
        ]

    @classmethod
    def _checkpoint_recovery_contract(
        cls,
        *,
        checkpoint_day: int,
        checkpoint_description: str,
        first_answer: str,
        second_answer: str,
    ) -> dict[str, Any]:
        combined = " ".join([checkpoint_description, first_answer, second_answer]).strip().lower()
        time_pressure = any(marker in combined for marker in cls.TIME_PRESSURE_MARKERS)
        repeated_failure = any(marker in combined for marker in cls.REPEATED_FAILURE_MARKERS)
        understanding_issue = any(marker in combined for marker in cls.STRONG_COGNITIVE_STRUGGLE_MARKERS)
        behind = any(marker in combined for marker in cls.BEHIND_MARKERS)

        if time_pressure:
            return {
                "objective": f"把 Day {checkpoint_day} 的落后内容压缩成一个 25 分钟保底回收动作。",
                "method_steps": [
                    "先写下最影响下一阶段的 1 个模块，不列长清单。",
                    "只保留这个模块的 3 个保底点或 1 道代表题，不追完整章。",
                    "最后写一句明天从哪里继续，避免下次重新启动成本。",
                ],
                "output_action": "留下 1 个可检查的保底产出，例如 3 个保底点、1 道代表题或 1 张错因卡。",
                "success_criteria": "有 1 个可检查的保底产出，并明确下次从哪里继续。",
                "time_estimate_minutes": 25,
                "difficulty": 1,
                "energy_cost": 1,
                "density_adjustment": "minimum_viable",
                "scaffolding_mode": "checkpoint_time_boxed_recovery",
                "micro_contract": "如果开始，就先锁定 1 个模块和 1 个保底输出，不再扩到第二个模块。",
                "fail_safe_rule": "今天只回收下一阶段最需要的最小产出，不继续加难。",
                "tags": ["time_boxed", "compressed_recovery"],
                "state_summary": "这次主要是时间不够，优先做最小保底回收，不继续堆任务。",
            }

        if understanding_issue:
            return {
                "objective": f"只补 Day {checkpoint_day} 检查点里最卡的 1 个概念，并做 1 个最小检查。",
                "method_steps": [
                    "先写出到底哪一句、哪一题或哪一个判断点没懂，只选 1 个卡点。",
                    "用自己的话重讲这个点，并补 1 个适用条件或反例。",
                    "立刻做 1 个最小检查题，确认不是只看懂答案。",
                ],
                "output_action": "补清 1 个最卡概念，并完成 1 个最小检查题。",
                "success_criteria": "能不用资料讲清 1 个最卡点，并完成 1 个最小检查题。",
                "time_estimate_minutes": 35,
                "difficulty": 1,
                "energy_cost": 1,
                "density_adjustment": "reduced",
                "scaffolding_mode": "checkpoint_single_gap_repair",
                "micro_contract": "如果开始，就只处理 1 个卡点；没讲清前，不切到第二个漏洞。",
                "fail_safe_rule": "今天不追整章补完，只修最影响后续的一处理解断点。",
                "tags": ["single_gap_focus"],
                "state_summary": "这次主要是没搞懂，先补清一个关键卡点，不继续堆更难任务。",
            }

        density_adjustment = "minimum_viable" if repeated_failure else "reduced"
        estimated_minutes = 20 if repeated_failure else 30
        return {
            "objective": f"回收 Day {checkpoint_day} 检查点的落后部分，并重新锁定下一阶段只保 1 个主线。",
            "method_steps": [
                "列出当前落后里最影响下一阶段的 2 项，不再继续展开。",
                "只选 1 项做最小补回动作，另一项放进稍后回收清单。",
                "用 1 次口头复述或小测确认主线已经重新接上。",
            ],
            "output_action": "完成 1 个最小补回动作，并写下下一阶段只保的 1 个主线。",
            "success_criteria": "明确 1 个下一阶段主线，完成 1 个最小补回动作，并留下 1 个稍后回收项。",
            "time_estimate_minutes": estimated_minutes,
            "difficulty": 1,
            "energy_cost": 1,
            "density_adjustment": density_adjustment,
            "scaffolding_mode": "checkpoint_backlog_triage",
            "micro_contract": "如果开始，就只补 1 个主线缺口；剩下的内容统一放到稍后回收。",
            "fail_safe_rule": "先把下一阶段能继续的主线接上，不为了补完而继续加码。",
            "tags": ["backlog_triage", "streak_fail_safe"] if repeated_failure or behind else ["backlog_triage"],
            "state_summary": "这次主要是进度落后，先降密度、接回主线，不继续并行补多个漏洞。",
        }

    async def evaluate_plan_health_now(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        trigger: str,
        task_id: UUID | None = None,
        completion_rate: float | None = None,
        feedback_category: str | None = None,
        difficulty_delta: float | None = None,
    ) -> list[AdaptationRecord]:
        """Run an immediate plan-health evaluation outside the periodic loop."""
        report = await self.progress_service.evaluate_progress(user_id, plan_id)
        return await self._handle_report(
            report,
            trigger=trigger,
            task_id=task_id,
            completion_rate=completion_rate,
            feedback_category=feedback_category,
            difficulty_delta=difficulty_delta,
        )

    @classmethod
    def is_strong_cognitive_struggle_feedback(
        cls,
        *,
        category: str | None,
        feedback_text: str | None,
    ) -> bool:
        normalized_category = str(category or "").strip().lower()
        if normalized_category == "unclear":
            return True
        haystack = str(feedback_text or "").strip().lower()
        if not haystack:
            return False
        return any(marker in haystack for marker in cls.STRONG_COGNITIVE_STRUGGLE_MARKERS)

    async def _maybe_record_breakdown_feedback(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        task_id: UUID,
        completion_status: str,
        feedback_category: str | None = None,
    ) -> None:
        if not self.db:
            return
        try:
            result = await self.db.execute(
                select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                return

            tags = list(task.tags or [])
            is_breakdown = any(str(tag).startswith("parent:") for tag in tags) or "micro" in tags
            if not is_breakdown:
                return

            parent_title = ""
            for tag in tags:
                tag_str = str(tag)
                if tag_str.startswith("parent:"):
                    parent_title = tag_str.split("parent:", 1)[-1].strip()
                    break

            actual_minutes = task.actual_minutes
            feedback_text = None
            if actual_minutes is None or feedback_category is None:
                feedback_result = await self.db.execute(
                    select(TaskFeedback)
                    .where(TaskFeedback.task_id == task_id)
                    .order_by(desc(TaskFeedback.created_at))
                    .limit(1)
                )
                feedback = feedback_result.scalar_one_or_none()
                if feedback:
                    actual_minutes = actual_minutes or feedback.actual_minutes_snapshot
                    feedback_text = feedback.feedback_text
                    if feedback_category is None:
                        feedback_category = feedback.category

            estimated_minutes = task.estimated_minutes
            time_accuracy = None
            if actual_minutes and estimated_minutes:
                time_accuracy = round(actual_minutes / max(estimated_minutes, 1), 2)

            entry = {
                "task_id": str(task.id),
                "plan_id": str(plan_id),
                "parent_title": parent_title or task.title,
                "task_title": task.title,
                "completion_status": completion_status,
                "feedback_category": feedback_category,
                "user_feedback": feedback_text,
                "estimated_minutes": estimated_minutes,
                "actual_minutes": actual_minutes,
                "time_accuracy": time_accuracy,
                "recorded_at": _utcnow().isoformat(),
            }

            state = await self.plan_state_service.get_plan_state(user_id, plan_id)
            existing: list[dict[str, Any]] = []
            if state and isinstance(state.facts, dict):
                raw = state.facts.get("breakdown_feedback")
                if isinstance(raw, list):
                    existing = [item for item in raw if isinstance(item, dict)]
            existing.append(entry)
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"breakdown_feedback": existing[-50:]}},
                bump_version=False,
            )
        except Exception as exc:
            logger.debug(f"Failed to record breakdown feedback: {exc}")

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
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        outcome_learning = self._extract_outcome_learning((state.facts or {}) if state else {})
        execution_summary = self._build_execution_revision_summary(
            feedback=feedback,
            outcome_learning=outcome_learning,
        )
        execution_delta = {
            "validation_status": feedback.validation_status,
            "quality_score": feedback.quality_score,
            "needs_replanning": feedback.needs_replanning,
            "slow_tools": list(feedback.slow_tools or []),
            "failed_tools": list(feedback.failed_tools or []),
            "unreliable_dependencies": list(feedback.unreliable_dependencies or []),
            "next_action": execution_summary.new_next_action,
            "what_changes": execution_summary.what_changes,
        }

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

        existing_meta = dict((((state.facts or {}) if state else {}).get("adaptive_meta")) or {})
        recent_execution_deltas = list(existing_meta.get("recent_execution_feedback_deltas", []) or [])
        recent_execution_deltas.append(execution_delta)
        existing_meta["recent_execution_feedback_deltas"] = recent_execution_deltas[-10:]
        existing_meta["last_execution_feedback_delta"] = execution_delta
        existing_meta = self._append_revision_summary(existing_meta, execution_summary)
        existing_meta["last_plan_revision_summary"] = execution_summary.to_dict()
        adaptive_facts["adaptive_meta"] = existing_meta

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
                adaptive_meta = dict(((state.facts or {}).get("adaptive_meta")) or {})
                adaptive_meta.update(
                    {
                        "last_replan_at": _utcnow().isoformat(),
                        "last_trigger": "plan_execution_feedback",
                        "last_replan_reason": [replan_reason],
                        "recent_adaptations": [record.to_dict()],
                        "last_execution_feedback_delta": execution_delta,
                        "last_plan_revision_summary": execution_summary.to_dict(),
                    }
                )
                await self.plan_state_service.upsert_plan_state(
                    user_id=user_id,
                    plan_id=plan_id,
                    patch={
                        "facts": {
                            "adaptive_meta": adaptive_meta,
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
        state = await self.plan_state_service.get_plan_state(report.user_id, report.plan_id)
        cognitive_records = await self._apply_cognitive_pattern_adjustments(
            user_id=report.user_id,
            plan_id=report.plan_id,
        )
        if not report.requires_adjustment:
            if state:
                observation_summary = self._build_observation_revision_summary(
                    report=report,
                    trigger=trigger,
                    task_id=task_id,
                    completion_rate=completion_rate,
                    feedback_category=feedback_category,
                    difficulty_delta=difficulty_delta,
                )
                adaptive_meta = dict(((state.facts or {}).get("adaptive_meta")) or {})
                adaptive_meta = self._append_revision_summary(adaptive_meta, observation_summary)
                adaptive_meta["last_plan_revision_summary"] = observation_summary.to_dict()
                await self.plan_state_service.upsert_plan_state(
                    user_id=report.user_id,
                    plan_id=report.plan_id,
                    patch={"facts": {"adaptive_meta": adaptive_meta}},
                    bump_version=False,
                )
            return cognitive_records

        if not state:
            return cognitive_records

        action_taken = "none"
        action_records: list[AdaptationRecord] = []

        if report.recommended_action == "replan":
            within_cooldown = self._recently_triggered(state.facts, "last_replan_at", self.AUTO_REPLAN_COOLDOWN)
            bypass_cooldown = False
            if within_cooldown and trigger == "task_feedback_struggle":
                new_streak = await self._increment_struggle_streak(report.user_id, report.plan_id, state)
                bypass_cooldown = new_streak >= self.STRUGGLE_COOLDOWN_BYPASS_THRESHOLD
            if within_cooldown and not bypass_cooldown:
                action_taken = "replan_cooldown_active"
            else:
                action_records = await self._trigger_full_replan(
                    report,
                    trigger=trigger,
                    task_id=task_id,
                    completion_rate=completion_rate,
                    feedback_category=feedback_category,
                )
                action_taken = "full_replan_triggered" if action_records else "no_replan_produced"
        else:
            if self._recently_triggered(state.facts, "last_adjustment_at", self.AUTO_ADJUSTMENT_COOLDOWN):
                action_taken = "adjustment_cooldown_active"
            else:
                action_records = await self._apply_incremental_adjustment(
                    report,
                    trigger=trigger,
                    task_id=task_id,
                    completion_rate=completion_rate,
                    difficulty_delta=difficulty_delta,
                    feedback_category=feedback_category,
                )
                action_taken = "incremental_adjustment_applied" if action_records else "no_adjustment_produced"

        # ---断点3: emit plan health signal ---
        try:
            await self.plan_health_signal_service.maybe_publish(
                report=report,
                trigger=trigger,
                task_id=task_id,
                feedback_category=feedback_category,
                action_taken=action_taken,
                adaptation_records=action_records,
                existing_facts=state.facts or {},
            )
        except Exception as exc:
            logger.warning("PlanHealthSignal emit failed (non-fatal): {}", exc)

        return cognitive_records + action_records

    @property
    def card_bridge(self) -> ReplannerCardBridge | None:
        """Lazy-init the card protocol bridge (graceful if protocol not yet migrated)."""
        if self._card_bridge is None:
            try:
                self._card_bridge = ReplannerCardBridge(self.db, event_bus)
            except Exception:
                logger.debug("Card protocol bridge not available (pre-migration)")
        return self._card_bridge

    async def _find_plan_card_id(
        self,
        user_id: UUID,
        plan_id: UUID,
    ) -> UUID | None:
        """Resolve the canonical PLAN card id for a legacy plan.

        Phase 3 compilation must target the canonical plan card, but the
        replanner still operates on legacy plan ids. Keep the lookup local and
        deterministic instead of reaching through bridge internals.
        """
        stmt = select(Card.id).where(
            Card.card_type == CardType.PLAN,
            Card.owner_id == user_id,
            Card.metadata_["legacy_plan_id"].as_string() == str(plan_id),
            Card.not_deleted_filter(),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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

        # Phase 3: Try ParameterCompiler first (requires GLOBAL_COMPASS + STRATEGY_MAP artifacts)
        compiled_result = None
        try:
            from app.services.card_protocol.parameter_compiler import ParameterCompiler

            compiler = ParameterCompiler(self.db, event_bus)
            # Find plan card for this legacy plan
            plan_card_id = await self._find_plan_card_id(report.user_id, report.plan_id)
            if plan_card_id and await compiler.can_compile(plan_card_id):
                compiled_result = await compiler.compile(
                    user_id=report.user_id,
                    plan_card_id=plan_card_id,
                    plan_id=report.plan_id,
                    trigger=trigger,
                    context={
                        "health_reasons": report.reasons,
                        "difficulty_delta": difficulty_delta,
                        "completion_rate": completion_rate,
                    },
                )
        except Exception as exc:
            logger.debug("ParameterCompiler skipped (non-fatal): {}", exc)

        if compiled_result and compiled_result.success:
            adjustments = {"adaptive_adjustments": compiled_result.adaptive_adjustments}
        else:
            # Fallback to legacy calculation when no artifacts available
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
        existing_adaptive = dict(((state.facts or {}).get("adaptive_adjustments")) or {})
        snapshots = list(adaptive_meta.get("adjustment_snapshots", []) or [])
        if not snapshots:
            snapshots.append(
                self._build_adjustment_snapshot(
                    adaptive_adjustments=existing_adaptive,
                    trigger="baseline",
                    reasons=[],
                )
            )
        current_adaptive = dict(adjustments.get("adaptive_adjustments", {}) or existing_adaptive)
        snapshot = self._build_adjustment_snapshot(
            adaptive_adjustments=current_adaptive,
            trigger=trigger,
            reasons=report.reasons,
        )
        snapshots.append(snapshot)
        adaptive_meta["adjustment_snapshots"] = snapshots[-self.SNAPSHOT_HISTORY_LIMIT :]
        adaptive_meta["active_snapshot_id"] = snapshot["id"]
        adaptive_meta["rollback_monitor"] = {
            "current_snapshot_id": snapshot["id"],
            "negative_feedback_streak": 0,
            "last_feedback_category": feedback_category or "",
        }
        revision_summary = self._build_revision_summary(
            report=report,
            feedback_category=feedback_category,
            what_changes=what_changed if (what_changed := record.what_changed) else "调整了当前计划的执行参数",
            new_next_action="按新的轻量节奏推进下一步任务。",
            outcome_learning=self._extract_outcome_learning(state.facts or {}),
        )
        adaptive_meta = self._append_revision_summary(adaptive_meta, revision_summary)
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
            patch={
                "facts": {
                    **adjustments,
                    "last_plan_revision_summary": revision_summary.to_dict(),
                },
                "feedback_log": feedback_entry,
            },
            bump_version=True,
        )

        logger.info(
            "Applied incremental adjustment for plan {}: {}",
            report.plan_id,
            adjustments,
        )

        # Apply adjustments to actual task entities (the critical bridge)
        patch_result = None
        try:
            patch_result = await self.plan_adjustment_applier.apply_incremental_changes(
                user_id=report.user_id,
                plan_id=report.plan_id,
                trigger=trigger,
            )
            task_level_change = bool(
                patch_result.applied
                and (
                    patch_result.affected_task_ids
                    or patch_result.inserted_task_ids
                    or patch_result.hidden_task_ids
                )
            )
            if task_level_change:
                logger.info(
                    "PlanAdjustmentApplier patched {} tasks, inserted {} reviews, hid {} tasks for plan {}",
                    len(patch_result.affected_task_ids),
                    len(patch_result.inserted_task_ids),
                    len(patch_result.hidden_task_ids),
                    report.plan_id,
                )
                # Enhance the adaptation record with task-level outcome
                record = AdaptationRecord(
                    what_changed=f"{record.what_changed}; tasks patched: {len(patch_result.affected_task_ids)}",
                    why=record.why,
                    expected_effect=record.expected_effect,
                    user_facing_message=patch_result.user_facing_summary or record.user_facing_message,
                    source="adaptive_replanner+plan_adjustment_applier",
                )
            else:
                logger.info(
                    "PlanAdjustmentApplier produced no task-level changes for plan {} despite parameter update",
                    report.plan_id,
                )
        except Exception as exc:
            logger.warning("PlanAdjustmentApplier failed (non-fatal): {}", exc)

        # --- Card protocol writeback (breakpoint fix 1) ---
        try:
            bridge = self.card_bridge
            if bridge:
                affected_ids = patch_result.affected_task_ids if patch_result else None
                inserted_ids = patch_result.inserted_task_ids if patch_result else None
                await bridge.on_incremental_adjustment(
                    user_id=report.user_id,
                    plan_id=report.plan_id,
                    adjustments=adjustments,
                    trigger=trigger,
                    affected_task_ids=affected_ids,
                    inserted_task_ids=inserted_ids,
                )
        except Exception as exc:
            logger.warning("Card protocol writeback failed (non-fatal): {}", exc)

        if not patch_result or not (
            patch_result.affected_task_ids
            or patch_result.inserted_task_ids
            or patch_result.hidden_task_ids
        ):
            await self._enqueue_adaptation_update(
                report.user_id,
                AdaptationRecord(
                    what_changed="评估了当前计划，但本轮没有生成需要落地的任务级调整。",
                    why="系统检测到了波动信号，但暂时只更新了内部参数和回顾记录。",
                    expected_effect="保留当前执行面不被频繁扰动，同时把这次评估结果纳入后续重规划依据。",
                    user_facing_message=(
                        "我已经重新检查了你的计划，这一轮先保留当前任务安排，"
                        "并把评估结果记入后续校准。"
                    ),
                    source="adaptive_replanner",
                ),
                update_type="plan_adaptation_evaluated",
            )
            return []

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
        state = await self.plan_state_service.get_plan_state(report.user_id, report.plan_id)
        revision_summary = self._build_revision_summary(
            report=report,
            feedback_category=feedback_category,
            what_changes="重新规划当前阶段的执行路径与任务顺序。",
            new_next_action="先按新的阶段起点重新启动，并完成新的第一步任务。",
            outcome_learning=self._extract_outcome_learning((state.facts or {}) if state else {}),
        )
        adaptive_facts = {
            "adaptive_meta": {
                "last_replan_at": now,
                "last_trigger": trigger,
                "last_replan_reason": report.reasons,
                "recent_adaptations": [record.to_dict()],
                "recent_revision_summaries": [revision_summary.to_dict()],
                "struggle_streak_since_last_replan": 0,
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
            patch={
                "facts": {
                    **adaptive_facts,
                    "last_plan_revision_summary": revision_summary.to_dict(),
                },
                "feedback_log": feedback_entry,
            },
            bump_version=True,
        )

        await plan_review_service.trigger_replanning(
            plan_id=str(report.plan_id),
            user_id=str(report.user_id),
            feedback=self._format_replan_message(report),
        )

        logger.info("Triggered auto-replan for plan {}", report.plan_id)

        # --- Card protocol writeback (breakpoint fix for full replan) ---
        try:
            bridge = self.card_bridge
            if bridge:
                await bridge.on_full_replan(
                    user_id=report.user_id,
                    plan_id=report.plan_id,
                    reasons=report.reasons,
                    severity=report.severity,
                )
        except Exception as exc:
            logger.warning("Card protocol writeback (full replan) failed (non-fatal): {}", exc)

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
        feedback_stats = dict((report.metrics or {}).get("feedback_stats") or {})
        too_difficult = int(feedback_stats.get("too_difficult", 0) or 0)
        too_long = int(feedback_stats.get("too_long", 0) or 0)

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

        if any(reason in {"progress_lag", "time_overrun"} for reason in report.reasons) or too_long >= 2:
            adaptive["max_concurrent_tasks"] = 1
            adaptive["task_density_mode"] = "reduced"
            adaptive["scaffolding_mode"] = "time_boxed_or_single_step"

        if "difficulty_too_hard" in report.reasons or too_difficult >= 2:
            adaptive["max_concurrent_tasks"] = 1
            adaptive["task_density_mode"] = "reduced"
            adaptive["scaffolding_mode"] = "single_gap_repair"
            adaptive["allow_new_hard_topics"] = False

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
            failed_adjustments=list((((state.facts or {}).get("adaptive_meta")) or {}).get("failed_adjustments") or []),
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

    async def _increment_struggle_streak(
        self,
        user_id: "UUID",
        plan_id: "UUID",
        state: Any,
    ) -> int:
        adaptive_meta = dict(((state.facts or {}).get("adaptive_meta")) or {})
        streak = int(adaptive_meta.get("struggle_streak_since_last_replan") or 0) + 1
        adaptive_meta["struggle_streak_since_last_replan"] = streak
        try:
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"adaptive_meta": adaptive_meta}},
                bump_version=False,
            )
        except Exception as exc:
            logger.warning("Failed to persist struggle streak: {}", exc)
        return streak

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
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        else:
            last_time = last_time.astimezone(timezone.utc)
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
        if adaptive.get("max_concurrent_tasks") == 1:
            change_parts.append("把同时推进的核心任务收紧到 1 个")
        if adaptive.get("scaffolding_mode"):
            change_parts.append(f"补上 {adaptive['scaffolding_mode']} 型脚手架")
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
        if adaptive.get("max_concurrent_tasks") == 1:
            expected_parts.append("降低任务密度")
        if "difficulty_shift" in adaptive and adaptive["difficulty_shift"] < 0:
            expected_parts.append("降低任务启动门槛")
        elif "difficulty_shift" in adaptive and adaptive["difficulty_shift"] > 0:
            expected_parts.append("适度提高挑战强度")
        if adaptive.get("scaffolding_mode"):
            expected_parts.append("先给更具体的补强脚手架")
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

    @staticmethod
    def _append_revision_summary(adaptive_meta: dict[str, Any], revision_summary: PlanRevisionSummary) -> dict[str, Any]:
        updated = dict(adaptive_meta)
        recent = list(updated.get("recent_revision_summaries", []) or [])
        recent.append(revision_summary.to_dict())
        updated["recent_revision_summaries"] = recent[-10:]
        return updated

    def _build_revision_summary(
        self,
        *,
        report: PlanHealthReport,
        feedback_category: str | None,
        what_changes: str,
        new_next_action: str,
        outcome_learning: dict[str, Any] | None = None,
    ) -> PlanRevisionSummary:
        reasons = ", ".join(report.reasons) if report.reasons else "plan health drift"
        assumption_failed = (
            feedback_category
            or (report.reasons[0] if report.reasons else "current plan assumptions no longer fit execution reality")
        )
        learning = outcome_learning if isinstance(outcome_learning, dict) else {}
        failure_rules = [
            str(item).strip()
            for item in list(learning.get("known_failure_avoidance_rules") or [])
            if str(item).strip()
        ]
        success_patterns = [
            str(item).strip()
            for item in list(learning.get("known_success_patterns") or [])
            if str(item).strip()
        ]
        why_text = f"Recent execution signals showed that the current plan drifted because: {reasons}."
        if failure_rules:
            why_text = (
                f"{why_text} This also matches validated learning: {failure_rules[0]}"
            )
        what_stays = "The main goal stays the same, and any progress already made should be preserved."
        if success_patterns:
            what_stays = f"{what_stays} Keep the validated success pattern: {success_patterns[0]}"
        return PlanRevisionSummary(
            why_plan_changed=why_text,
            what_assumption_failed=f"The assumption that '{assumption_failed}' would remain manageable did not hold.",
            what_stays=what_stays,
            what_changes=what_changes,
            new_next_action=new_next_action,
        )

    def _build_observation_revision_summary(
        self,
        *,
        report: PlanHealthReport,
        trigger: str,
        task_id: UUID | None,
        completion_rate: float | None,
        feedback_category: str | None,
        difficulty_delta: float | None,
    ) -> PlanRevisionSummary:
        signal_parts: list[str] = []
        if report.reasons:
            signal_parts.append(", ".join(report.reasons))
        if completion_rate is not None:
            signal_parts.append(f"completion_rate={completion_rate:.2f}")
        if feedback_category:
            signal_parts.append(f"feedback_category={feedback_category}")
        if difficulty_delta is not None:
            signal_parts.append(f"difficulty_delta={difficulty_delta:.2f}")
        if task_id:
            signal_parts.append(f"task_id={task_id}")
        signal_text = "；".join(signal_parts) if signal_parts else "execution stayed within the current plan bounds"

        if report.requires_adjustment:
            what_changes = "收紧当前计划中的卡点，并围绕新的约束继续推进。"
            new_next_action = "先处理最先暴露出来的执行卡点，再推进下一步。"
        elif trigger == "task_completed":
            what_changes = "保持当前计划结构不变，只继续推进下一步。"
            new_next_action = "沿用已验证的路径，继续执行下一步任务。"
        else:
            what_changes = "保持当前计划结构，只把最新反馈记入下一轮执行参考。"
            new_next_action = "根据最新反馈继续推进下一步。"

        what_stays = "已验证通过的步骤和已完成的成果保持不变。"
        if report.metrics.get("completion_rate") is not None:
            what_stays = f"{what_stays} 当前完成度记录为 {float(report.metrics['completion_rate']):.2f}。"

        return PlanRevisionSummary(
            why_plan_changed=f"Recent execution signals indicate the current path still needs a light revision: {signal_text}.",
            what_assumption_failed=(
                f"The assumption that the current execution rhythm would remain stable for trigger '{trigger}' did not hold."
            ),
            what_stays=what_stays,
            what_changes=what_changes,
            new_next_action=new_next_action,
        )

    def _build_execution_revision_summary(
        self,
        *,
        feedback: "PlanExecutionFeedback",
        outcome_learning: dict[str, Any] | None = None,
    ) -> PlanRevisionSummary:
        learning = outcome_learning if isinstance(outcome_learning, dict) else {}
        failure_rules = [
            str(item).strip()
            for item in list(learning.get("known_failure_avoidance_rules") or [])
            if str(item).strip()
        ]
        success_patterns = [
            str(item).strip()
            for item in list(learning.get("known_success_patterns") or [])
            if str(item).strip()
        ]

        signal_bits = [
            f"validation_status={feedback.validation_status}",
            f"quality_score={feedback.quality_score:.2f}",
        ]
        if feedback.aborted:
            signal_bits.append("aborted=True")
        if feedback.failed_tools:
            signal_bits.append(f"failed_tools={','.join(feedback.failed_tools[:3])}")
        if feedback.slow_tools:
            signal_bits.append(f"slow_tools={','.join(feedback.slow_tools[:3])}")
        if feedback.unreliable_dependencies:
            signal_bits.append(f"unreliable_dependencies={','.join(feedback.unreliable_dependencies[:3])}")

        if feedback.aborted or feedback.validation_status == "failed":
            what_changes = "先修复失败工具和不稳定依赖，再继续后续步骤。"
            new_next_action = "先从失败的关键步骤重新开始，只推进一小段验证路径。"
        elif feedback.validation_status == "partial" or feedback.slow_tools or feedback.unreliable_dependencies:
            what_changes = "保留已经通过的步骤，只围绕卡点做局部修正。"
            new_next_action = "先处理最慢或最不稳定的步骤，然后再推进剩余步骤。"
        else:
            what_changes = "保持当前执行结构，只沿用已验证的步骤继续推进。"
            new_next_action = "继续执行下一步，并沿用当前已验证的路径。"

        what_stays = "已通过的步骤和已验证的执行成果保持不变。"
        if success_patterns:
            what_stays = f"{what_stays} Keep the validated success pattern: {success_patterns[0]}"

        why_plan_changed = f"Recent execution signals show the current path should be revised slightly: {', '.join(signal_bits)}."
        if failure_rules:
            why_plan_changed = f"{why_plan_changed} This matches validated learning: {failure_rules[0]}"

        failed_tool = feedback.failed_tools[0] if feedback.failed_tools else feedback.validation_status
        return PlanRevisionSummary(
            why_plan_changed=why_plan_changed,
            what_assumption_failed=(
                f"The assumption that '{failed_tool}' would remain stable through execution did not hold."
            ),
            what_stays=what_stays,
            what_changes=what_changes,
            new_next_action=new_next_action,
        )

    @staticmethod
    def _extract_outcome_learning(facts: dict[str, Any]) -> dict[str, Any]:
        learning = facts.get("validated_outcome_learning")
        return dict(learning) if isinstance(learning, dict) else {}

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

    async def _maybe_rollback_after_feedback(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        feedback_category: str | None,
        task_id: UUID | None,
    ) -> list[AdaptationRecord]:
        state = await self.plan_state_service.get_plan_state(user_id, plan_id)
        if not state:
            return []
        facts = dict(state.facts or {})
        adaptive_meta = dict((facts.get("adaptive_meta") or {}))
        snapshots = list(adaptive_meta.get("adjustment_snapshots") or [])
        active_snapshot_id = str(adaptive_meta.get("active_snapshot_id") or "").strip()
        if not snapshots or not active_snapshot_id:
            return []

        rollback_monitor = dict(adaptive_meta.get("rollback_monitor") or {})
        category = str(feedback_category or "").strip().lower()
        is_negative = category in self.NEGATIVE_FEEDBACK_CATEGORIES
        current_snapshot_id = str(rollback_monitor.get("current_snapshot_id") or active_snapshot_id)
        negative_streak = int(rollback_monitor.get("negative_feedback_streak") or 0)

        if current_snapshot_id != active_snapshot_id:
            negative_streak = 0

        if not is_negative:
            adaptive_meta["rollback_monitor"] = {
                "current_snapshot_id": active_snapshot_id,
                "negative_feedback_streak": 0,
                "last_feedback_category": category,
            }
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"adaptive_meta": adaptive_meta}},
                bump_version=False,
            )
            return []

        negative_streak += 1
        adaptive_meta["rollback_monitor"] = {
            "current_snapshot_id": active_snapshot_id,
            "negative_feedback_streak": negative_streak,
            "last_feedback_category": category,
        }

        if negative_streak < 2:
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"adaptive_meta": adaptive_meta}},
                bump_version=False,
            )
            return []

        previous_snapshot = self._previous_snapshot(snapshots, active_snapshot_id)
        if not previous_snapshot:
            await self.plan_state_service.upsert_plan_state(
                user_id=user_id,
                plan_id=plan_id,
                patch={"facts": {"adaptive_meta": adaptive_meta}},
                bump_version=False,
            )
            return []

        current_snapshot = self._snapshot_by_id(snapshots, active_snapshot_id)

        rollback_adjustments = dict(previous_snapshot.get("adaptive_adjustments") or {})
        record = AdaptationRecord(
            what_changed="回滚到了上一版更稳定的执行策略",
            why=f"最近连续两次反馈「{feedback_category or '不匹配'}」，说明当前自适应调节开始偏离你的真实状态。",
            expected_effect="先恢复到上一版已验证更稳的节奏，避免系统继续沿着错误方向放大偏差。",
            user_facing_message="我发现这轮自动调节有点过头了，先帮你切回上一版更稳的节奏。",
            source="adaptive_replanner_rollback",
        )
        recent = list(adaptive_meta.get("recent_adaptations", []) or [])
        recent.append(record.to_dict())
        adaptive_meta["recent_adaptations"] = recent[-10:]
        failed_adjustments = list(adaptive_meta.get("failed_adjustments") or [])
        failed_adjustments.extend(
            self._diff_failed_adjustments(
                current_snapshot=current_snapshot or {},
                restored_snapshot=previous_snapshot,
                reason=feedback_category or "",
            )
        )
        adaptive_meta["failed_adjustments"] = failed_adjustments[-5:]
        adaptive_meta["active_snapshot_id"] = str(previous_snapshot.get("id") or "")
        adaptive_meta["last_rollback_at"] = _utcnow().isoformat()
        adaptive_meta["last_rollback_reason"] = feedback_category or ""
        adaptive_meta["rollback_learning_state"] = {
            "last_restored_snapshot_id": adaptive_meta["active_snapshot_id"],
            "last_failed_adjustment_count": len(adaptive_meta["failed_adjustments"]),
            "updated_at": _utcnow().isoformat(),
        }
        adaptive_meta["rollback_monitor"] = {
            "current_snapshot_id": adaptive_meta["active_snapshot_id"],
            "negative_feedback_streak": 0,
            "last_feedback_category": category,
        }

        feedback_entry = self._build_feedback_entry(
            feedback_type="adaptive_rollback",
            content=f"Rollback to previous adaptive snapshot due to repeated negative feedback: {feedback_category or 'unknown'}",
            task_id=task_id,
            applied_adjustment={
                "adaptive_adjustments": rollback_adjustments,
                "restored_snapshot_id": adaptive_meta["active_snapshot_id"],
            },
        )
        # ---断点1 Fix #1: Roll back actual Task entities, not just plan state ---
        try:
            await self.plan_adjustment_applier.rollback_last_patch(
                user_id=user_id,
                plan_id=plan_id,
            )
        except Exception as exc:
            logger.warning("Task-entity rollback failed (non-fatal): {}", exc)

        await self.plan_state_service.upsert_plan_state(
            user_id=user_id,
            plan_id=plan_id,
            patch={
                "facts": {
                    "adaptive_adjustments": rollback_adjustments,
                    "adaptive_meta": adaptive_meta,
                },
                "feedback_log": feedback_entry,
            },
            bump_version=True,
        )
        ADAPTIVE_ROLLBACK_TOTAL.inc()
        await self._enqueue_adaptation_update(user_id, record, update_type="plan_adaptation")
        return [record]

    def _build_adjustment_snapshot(
        self,
        *,
        adaptive_adjustments: dict[str, Any],
        trigger: str,
        reasons: list[str],
    ) -> dict[str, Any]:
        return {
            "id": f"as-{uuid.uuid4().hex[:10]}",
            "created_at": _utcnow().isoformat(),
            "adaptive_adjustments": dict(adaptive_adjustments or {}),
            "trigger": trigger,
            "reasons": list(reasons or [])[:3],
        }

    def _previous_snapshot(
        self,
        snapshots: list[dict[str, Any]],
        active_snapshot_id: str,
    ) -> dict[str, Any] | None:
        normalized = [item for item in snapshots if isinstance(item, dict)]
        if len(normalized) < 2:
            return None
        for index in range(len(normalized) - 1, -1, -1):
            snapshot = normalized[index]
            if str(snapshot.get("id") or "") != active_snapshot_id:
                continue
            for previous in range(index - 1, -1, -1):
                candidate = normalized[previous]
                if str(candidate.get("id") or "") != active_snapshot_id:
                    return candidate
            break
        return None

    @staticmethod
    def _snapshot_by_id(
        snapshots: list[dict[str, Any]],
        snapshot_id: str,
    ) -> dict[str, Any] | None:
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            if str(snapshot.get("id") or "") == snapshot_id:
                return snapshot
        return None

    def _diff_failed_adjustments(
        self,
        *,
        current_snapshot: dict[str, Any],
        restored_snapshot: dict[str, Any],
        reason: str,
    ) -> list[dict[str, Any]]:
        current = dict(current_snapshot.get("adaptive_adjustments") or {})
        restored = dict(restored_snapshot.get("adaptive_adjustments") or {})
        failed: list[dict[str, Any]] = []
        keys = sorted(set(current.keys()) | set(restored.keys()))
        for key in keys:
            current_value = current.get(key)
            restored_value = restored.get(key)
            if current_value == restored_value:
                continue
            failed.append(
                {
                    "constraint_key": key,
                    "direction": self.cognitive_pattern_trigger._direction(current_value),
                    "previous_value": current_value,
                    "rolled_back_value": restored_value,
                    "reason": reason,
                    "rolled_back_at": _utcnow().isoformat(),
                }
            )
        return failed

    async def check_proactive_intervention(
        self,
        *,
        user_id: str,
        plan_id: str,
        redis=None,
    ) -> dict | None:
        """
        主动干预检查。由 Celery beat 每6小时调用一次。

        返回 None：不需要干预
        返回 dict：{action, message_hint, struggle_context}
        """
        from app.services.struggle_signal_aggregator import struggle_signal_aggregator

        struggle_context = await struggle_signal_aggregator.get_struggle_context(
            self.db, user_id=user_id, plan_id=plan_id
        )
        score = float(struggle_context.get("struggle_score", 0.0) or 0.0)

        if score < 0.6:
            return None

        # 检查最近是否已经主动联系过（冷却期8h）
        last_proactive = self._coerce_meta_datetime(
            await self._get_meta_value(user_id, plan_id, "last_proactive_at")
        )
        if last_proactive and _utcnow() - last_proactive < timedelta(hours=8):
            return None

        # 构建主动干预上下文
        stuck_concepts = list(struggle_context.get("stuck_concepts") or [])

        if stuck_concepts:
            # 有具体卡点
            try:
                days_behind = float(struggle_context.get("days_behind", 1) or 1)
            except (TypeError, ValueError):
                days_behind = 1.0
            message_hint = (
                f"我注意到你在{stuck_concepts[0]}这块已经{max(days_behind, 1.0):.0f}天没有明显推进，"
                f"我们来看看是不是路径需要调整一下？"
            )
        else:
            # 通用挣扎
            message_hint = (
                "你最近学习节奏似乎遇到了一些阻力，这很正常——"
                "我们来看看是卡点的问题还是任务节奏需要调整？"
            )

        await self._set_meta_value(user_id, plan_id, "last_proactive_at", _utcnow())

        return {
            "action": "send_proactive_aurora_message",
            "message_hint": message_hint,
            "struggle_score": score,
            "struggle_context": struggle_context,
        }

    async def _get_meta_value(
        self,
        user_id: UUID | str,
        plan_id: UUID | str,
        key: str,
    ) -> Any:
        state = await self.plan_state_service.get_plan_state(
            UUID(str(user_id)),
            UUID(str(plan_id)),
        )
        adaptive_meta = dict(((state.facts or {}) if state else {}).get("adaptive_meta") or {})
        return adaptive_meta.get(key)

    async def _set_meta_value(
        self,
        user_id: UUID | str,
        plan_id: UUID | str,
        key: str,
        value: Any,
    ) -> None:
        user_uuid = UUID(str(user_id))
        plan_uuid = UUID(str(plan_id))
        state = await self.plan_state_service.get_plan_state(user_uuid, plan_uuid)
        adaptive_meta = dict(((state.facts or {}) if state else {}).get("adaptive_meta") or {})
        adaptive_meta[key] = value.isoformat() if isinstance(value, datetime) else value
        await self.plan_state_service.upsert_plan_state(
            user_id=user_uuid,
            plan_id=plan_uuid,
            patch={"facts": {"adaptive_meta": adaptive_meta}},
            bump_version=False,
        )

    @staticmethod
    def _coerce_meta_datetime(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

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
