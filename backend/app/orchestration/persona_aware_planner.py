from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from loguru import logger

from app.services.plan_state_service import PlanStateService


@dataclass
class PersonaPlanningConstraints:
    overall_mastery: float = 0.0
    weak_knowledge_nodes: list[str] = field(default_factory=list)
    active_subjects: list[str] = field(default_factory=list)
    time_multiplier: float = 1.0
    max_session_minutes: int = 45
    preferred_task_size: str = "medium"
    require_warmup_task: bool = False
    depth_preference: float = 0.5
    difficulty_preference: float = 0.5
    recent_completion_rate: float = 1.0
    recent_abandonment_reasons: list[str] = field(default_factory=list)
    active_adjustments: dict[str, Any] = field(default_factory=dict)
    hard_constraints: dict[str, Any] = field(default_factory=dict)
    soft_constraints: dict[str, Any] = field(default_factory=dict)
    review_feedback_log: list[dict[str, Any]] = field(default_factory=list)

    def to_planning_constraints(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["hard_constraints"] = dict(self.hard_constraints)
        payload["soft_constraints"] = dict(self.soft_constraints)
        return payload

    def to_prompt_lines(self) -> list[str]:
        lines = [
            f"- overall_mastery: {self.overall_mastery:.2f}",
            f"- recent_completion_rate: {self.recent_completion_rate:.2f}",
            f"- max_session_minutes: {self.max_session_minutes}",
            f"- preferred_task_size: {self.preferred_task_size}",
            f"- time_multiplier: {self.time_multiplier:.2f}",
            f"- require_warmup_task: {self.require_warmup_task}",
        ]
        if self.weak_knowledge_nodes:
            lines.append(f"- weak_knowledge_nodes: {', '.join(self.weak_knowledge_nodes[:5])}")
        if self.active_subjects:
            lines.append(f"- active_subjects: {', '.join(self.active_subjects[:5])}")
        if self.recent_abandonment_reasons:
            lines.append(f"- recent_abandonment_reasons: {'; '.join(self.recent_abandonment_reasons[:3])}")
        if self.active_adjustments:
            lines.append(f"- active_adjustments: {self.active_adjustments}")
        if self.hard_constraints:
            lines.append(f"- hard_constraints: {self.hard_constraints}")
        if self.soft_constraints:
            lines.append(f"- soft_constraints: {self.soft_constraints}")
        return lines

    def to_prompt_block(self) -> str:
        return "Persona-aware planning constraints:\n" + "\n".join(self.to_prompt_lines())


class PersonaAwarePlanner:
    """Translate user/profile/plan state signals into planning constraints."""

    def __init__(self, db_session, redis=None):
        self.db = db_session
        self.redis = redis

    async def build_constraints(
        self,
        *,
        user_id: str,
        user_context_payload: dict[str, Any] | None,
        plan_context: dict[str, Any] | None,
        plan_id: str | None,
    ) -> PersonaPlanningConstraints:
        constraints = PersonaPlanningConstraints()
        user_context_payload = user_context_payload if isinstance(user_context_payload, dict) else {}
        plan_context = plan_context if isinstance(plan_context, dict) else {}

        profile_context = user_context_payload.get("profile_context")
        if isinstance(profile_context, dict):
            knowledge_summary = profile_context.get("knowledge_summary")
            if isinstance(knowledge_summary, dict):
                constraints.overall_mastery = self._safe_float(
                    knowledge_summary.get("overall_mastery"),
                    default=constraints.overall_mastery,
                )
                active_subjects = knowledge_summary.get("active_learning_subjects")
                if isinstance(active_subjects, list):
                    constraints.active_subjects = [
                        str(item).strip() for item in active_subjects if str(item).strip()
                    ][:5]

        user_profile = plan_context.get("user_profile")
        user_profile = user_profile if isinstance(user_profile, dict) else {}
        behavior_patterns = user_profile.get("behavior_patterns")
        behavior_patterns = behavior_patterns if isinstance(behavior_patterns, list) else []
        derived_insights = user_profile.get("derived_insights")
        derived_insights = derived_insights if isinstance(derived_insights, dict) else {}
        preferences_snapshot = user_profile.get("preferences_snapshot")
        preferences_snapshot = preferences_snapshot if isinstance(preferences_snapshot, dict) else {}
        preferences = user_context_payload.get("preferences")
        preferences = preferences if isinstance(preferences, dict) else {}
        facts = plan_context.get("facts")
        facts = facts if isinstance(facts, dict) else {}
        task_summary = plan_context.get("task_summary")
        task_summary = task_summary if isinstance(task_summary, dict) else {}

        constraints.max_session_minutes = max(
            10,
            min(
                90,
                int(
                    self._safe_float(
                        facts.get("session_length_preference")
                        or preferences.get("session_length_preference")
                        or preferences.get("focus_duration_preference")
                        or preferences_snapshot.get("focus_duration_preference")
                        or preferences_snapshot.get("inferred_session_length"),
                        default=45,
                    )
                ),
            ),
        )

        constraints.depth_preference = self._normalize_preference(
            preferences.get("depth_preference") or preferences.get("curiosity_preference"),
            default=0.5,
        )
        constraints.difficulty_preference = self._normalize_preference(
            facts.get("difficulty_preference")
            or preferences.get("difficulty_preference")
            or preferences_snapshot.get("inferred_difficulty"),
            default=0.5,
        )
        constraints.recent_completion_rate = self._safe_float(
            task_summary.get("avg_completion_rate"),
            default=1.0,
        )

        weak_nodes = plan_context.get("weak_knowledge_nodes") or facts.get("weak_knowledge_nodes") or []
        if isinstance(weak_nodes, list):
            constraints.weak_knowledge_nodes = [
                str(item.get("name") or item).strip()
                for item in weak_nodes
                if str(item.get("name") if isinstance(item, dict) else item).strip()
            ][:5]

        active_adjustments = facts.get("adaptive_adjustments")
        if isinstance(active_adjustments, dict):
            constraints.active_adjustments = dict(active_adjustments)

        constraints.time_multiplier = 1.0
        if derived_insights.get("planning_tendency") == "optimistic":
            constraints.time_multiplier = 1.25
        elif derived_insights.get("planning_tendency") == "conservative":
            constraints.time_multiplier = 0.95

        pattern_text = " ".join(
            f"{str(item.get('pattern_name') or '')} {str(item.get('description') or '')}".lower()
            for item in behavior_patterns
            if isinstance(item, dict)
        )
        if any(keyword in pattern_text for keyword in ("低估", "optimistic", "拖延", "overrun")):
            constraints.time_multiplier = max(constraints.time_multiplier, 1.2)
        if any(keyword in pattern_text for keyword in ("分心", "distract", "启动困难", "warmup")):
            constraints.require_warmup_task = True
        if constraints.active_adjustments.get("require_start_ritual_micro_task"):
            constraints.require_warmup_task = True

        if constraints.max_session_minutes <= 20:
            constraints.preferred_task_size = "micro"
        elif constraints.max_session_minutes <= 35:
            constraints.preferred_task_size = "small"
        else:
            constraints.preferred_task_size = "medium"

        if plan_id and self.db is not None:
            await self._merge_plan_state_feedback(
                constraints=constraints,
                user_id=user_id,
                plan_id=plan_id,
            )

        constraints.hard_constraints = {
            **dict(constraints.hard_constraints or {}),
            "max_session_minutes": constraints.max_session_minutes,
            "time_multiplier": round(constraints.time_multiplier, 2),
            "weak_knowledge_nodes": constraints.weak_knowledge_nodes,
            "require_prerequisite_coverage": bool(constraints.weak_knowledge_nodes),
        }
        if constraints.require_warmup_task:
            constraints.soft_constraints["require_warmup_task"] = True
        constraints.soft_constraints.update(
            {
                "preferred_task_size": constraints.preferred_task_size,
                "depth_preference": round(constraints.depth_preference, 2),
                "difficulty_preference": round(constraints.difficulty_preference, 2),
                "recent_completion_rate": round(constraints.recent_completion_rate, 2),
                "active_subjects": constraints.active_subjects,
            }
        )
        return constraints

    async def _merge_plan_state_feedback(
        self,
        *,
        constraints: PersonaPlanningConstraints,
        user_id: str,
        plan_id: str,
    ) -> None:
        try:
            state = await PlanStateService(self.db, self.redis).get_plan_state(
                UUID(str(user_id)),
                UUID(str(plan_id)),
            )
        except Exception as exc:
            logger.warning(f"Failed to load plan state for persona constraints: {exc}")
            return

        if state is None:
            return

        facts = state.facts or {}
        constraints.active_adjustments = dict(facts.get("adaptive_adjustments") or constraints.active_adjustments or {})

        breakdown_feedback = facts.get("breakdown_feedback")
        if isinstance(breakdown_feedback, list):
            ratios = [
                float(item.get("time_accuracy"))
                for item in breakdown_feedback
                if isinstance(item, dict) and isinstance(item.get("time_accuracy"), (int, float))
            ]
            if ratios:
                avg_ratio = sum(ratios) / max(len(ratios), 1)
                if avg_ratio > 1.3:
                    constraints.time_multiplier = max(
                        constraints.time_multiplier,
                        min(1.6, round(avg_ratio, 2)),
                    )

        feedback_log = list(state.feedback_log or [])
        stored_review_log = list((facts.get("review_feedback_log") or []))
        review_log = [item for item in [*stored_review_log, *feedback_log] if isinstance(item, dict)]
        constraints.review_feedback_log = review_log[-8:]

        reasons: list[str] = []
        for item in reversed(constraints.review_feedback_log):
            category = str(item.get("category") or item.get("decision") or "").strip().lower()
            message = str(item.get("message") or item.get("content") or "").strip()
            if not message:
                continue
            if any(token in category for token in ("reject", "abandon", "difficulty", "feasibility")):
                reasons.append(message)
            if len(reasons) >= 3:
                break
        constraints.recent_abandonment_reasons = reasons

        for item in reversed(constraints.review_feedback_log):
            message = str(item.get("message") or item.get("content") or "").lower()
            category = str(item.get("category") or "").lower()
            if "difficulty too high" in message or "难度偏高" in message or "too_difficult" in category:
                constraints.difficulty_preference = max(0.2, round(constraints.difficulty_preference - 0.1, 2))
                constraints.hard_constraints["difficulty_bias"] = "lower"
                break
            if "alignment" in category:
                score = self._safe_float(item.get("alignment_score"), default=1.0)
                if score < 0.55:
                    constraint_key = str(item.get("bias_constraint") or "").strip()
                    if constraint_key:
                        constraints.hard_constraints[f"alignment_bias:{constraint_key}"] = True
                break

    @staticmethod
    def _normalize_preference(value: Any, *, default: float) -> float:
        try:
            normalized = float(value)
        except Exception:
            return default
        return max(0.0, min(normalized, 1.0))

    @staticmethod
    def _safe_float(value: Any, *, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default
