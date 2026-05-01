"""
Core: execution
Phase: plan→execute
Stage: Signal-to-Action Spine M1-Step3+4

Directive Applier — 将 ExecutionDirective 硬约束注入任务生成。
Audit — 验证输出是否满足 directive。

Directive 不是 prompt 片段，下游模块必须以结构化参数消费。
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.signals.types import DirectiveApplicationAudit, ExecutionDirective, _uid


class DirectiveApplier:
    """将 ExecutionDirective 的 hard_constraints 应用到任务生成参数。"""

    @staticmethod
    def apply_soft_difficulty(
        *,
        soft_biases: dict[str, Any] | None,
        current_difficulty: int,
    ) -> tuple[int, bool]:
        """
        Apply soft difficulty adjustments from PolicyDecision.soft_biases.

        Returns:
            (adjusted_difficulty, was_adjusted)
        """
        if not soft_biases:
            return current_difficulty, False

        difficulty_hint = soft_biases.get("difficulty")
        challenge = soft_biases.get("challenge")

        adjusted = current_difficulty
        if difficulty_hint == "low":
            adjusted = max(1, min(adjusted, 2))
        elif difficulty_hint == "medium_low" or difficulty_hint == "low_medium":
            adjusted = max(1, min(adjusted, 3))

        if challenge == "slight_increase":
            adjusted = min(5, adjusted + 1)

        if adjusted != current_difficulty:
            logger.info(
                "Soft difficulty adjustment: {} → {} (hint={}, challenge={})",
                current_difficulty, adjusted, difficulty_hint, challenge,
            )
        return adjusted, adjusted != current_difficulty

    @staticmethod
    def apply_duration_cap(
        *,
        directive: ExecutionDirective | None,
        estimated_minutes: int,
        task_kind: str | None = None,
    ) -> tuple[int, bool]:
        """
        应用 max_task_duration_min 约束。

        Returns:
            (capped_minutes, was_applied)
        """
        if not directive:
            return estimated_minutes, False

        cap = directive.hard_constraints.get("max_task_duration_min")
        if cap is None:
            return estimated_minutes, False

        if estimated_minutes <= cap:
            return estimated_minutes, True

        capped = min(estimated_minutes, cap)
        logger.info(
            "Directive {} capped task duration: {} → {} (cap={})",
            directive.directive_id, estimated_minutes, capped, cap,
        )
        return capped, True

    @staticmethod
    def should_avoid_new_chapter(directive: ExecutionDirective | None) -> bool:
        """检查 directive 是否要求避免新章节。"""
        if not directive:
            return False
        return bool(directive.hard_constraints.get("avoid_new_chapter", False))

    @staticmethod
    def get_required_task_type(directive: ExecutionDirective | None) -> str | None:
        """获取 directive 要求的任务类型。"""
        if not directive:
            return None
        return directive.hard_constraints.get("required_task_type")

    @staticmethod
    def apply_to_task_spec(
        *,
        directive: ExecutionDirective | None,
        task_spec: dict[str, Any],
    ) -> dict[str, Any]:
        """
        将 directive 所有约束应用到任务 spec dict。
        返回修改后的 spec（原地修改 + 返回引用）。
        """
        if not directive:
            return task_spec

        # 1. Duration cap
        original_minutes = task_spec.get("estimated_minutes", 30)
        capped_minutes, _ = DirectiveApplier.apply_duration_cap(
            directive=directive,
            estimated_minutes=original_minutes,
            task_kind=task_spec.get("task_kind"),
        )
        task_spec["estimated_minutes"] = capped_minutes

        # 2. Task type override
        required_type = DirectiveApplier.get_required_task_type(directive)
        if required_type:
            task_spec["task_kind"] = required_type

        # 3. Prefer easy wins (from momentum_stalled)
        if directive.hard_constraints.get("prefer_easy_wins"):
            task_spec["difficulty"] = min(task_spec.get("difficulty", 3), 2)
            task_spec["_easy_win_mode"] = True

        # 4. Mark directive application
        task_spec["_directive_id"] = directive.directive_id
        task_spec["_directive_reason"] = directive.user_visible_reason

        return task_spec


class DirectiveAuditor:
    """验证任务生成输出是否满足 directive 约束。"""

    @staticmethod
    def audit(
        *,
        directive: ExecutionDirective,
        generated_task: dict[str, Any],
    ) -> DirectiveApplicationAudit:
        """
        Audit：验证输出是否满足 directive。
        不满足则记录 violation。
        """
        violations: list[dict[str, Any]] = []
        applied_constraints: list[str] = []

        # 1. Check duration
        cap = directive.hard_constraints.get("max_task_duration_min")
        actual_duration = generated_task.get("estimated_minutes", 0)
        if cap is not None:
            applied_constraints.append("max_task_duration_min")
            if actual_duration > cap:
                violations.append({
                    "constraint": "max_task_duration_min",
                    "required": f"<={cap}",
                    "actual": actual_duration,
                    "severity": "hard",
                })

        # 2. Check task type
        required_type = directive.hard_constraints.get("required_task_type")
        actual_type = generated_task.get("task_kind")
        if required_type:
            applied_constraints.append("required_task_type")
            if actual_type != required_type:
                violations.append({
                    "constraint": "required_task_type",
                    "required": required_type,
                    "actual": actual_type,
                    "severity": "hard",
                })

        # 3. Check avoid_new_chapter
        avoid_new = directive.hard_constraints.get("avoid_new_chapter", False)
        if avoid_new:
            applied_constraints.append("avoid_new_chapter")
            is_new_chapter = generated_task.get("is_new_chapter", False)
            if is_new_chapter:
                violations.append({
                    "constraint": "avoid_new_chapter",
                    "required": False,
                    "actual": True,
                    "severity": "hard",
                })

        applied = len(violations) == 0
        if not applied:
            logger.warning(
                "Directive violations: {} violations in task {}",
                len(violations), generated_task.get("task_id", "?"),
            )

        audit = DirectiveApplicationAudit(
            audit_id=_uid("audit"),
            directive_id=directive.directive_id,
            target_module="task_generator",
            applied=applied,
            applied_constraints=applied_constraints,
            violations=violations,
            generated_output_id=generated_task.get("task_id"),
            generated_output_summary={
                "duration_min": actual_duration,
                "task_kind": actual_type,
                "is_new_chapter": generated_task.get("is_new_chapter", False),
            },
        )
        logger.info("Audit {}: applied={} violations={}", audit.audit_id, applied, len(violations))
        return audit
