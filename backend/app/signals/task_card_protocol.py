"""
P3-5 Generalized Task Protocol — task cards that bind to GoalWorldGraph nodes
and support 6 task types across all goal domains.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.signals.types import (
    TASK_TYPES,
    MaterialsProtocol,
    StuckProtocol,
    TaskCardProtocol,
    WhyThisTask,
)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


class TaskCardBuilder:
    """Constructs TaskCardProtocol instances with domain-appropriate defaults."""

    @staticmethod
    def for_study(
        goal_id: str,
        bound_nodes: list[str],
        why: WhyThisTask | None = None,
        steps: list[str] | None = None,
        stuck_protocol: StuckProtocol | None = None,
    ) -> TaskCardProtocol:
        return TaskCardProtocol(
            task_id=TaskCardBuilder._new_id(),
            goal_id=goal_id,
            bound_nodes=bound_nodes,
            task_type="study",
            why_this_task=why or WhyThisTask(),
            materials_protocol=MaterialsProtocol(
                retrieval_mode="task_bound_graph_rag",
                must_load_node_ids=bound_nodes,
            ),
            steps=steps or [],
            stuck_protocol=stuck_protocol or StuckProtocol(
                escalation_after_min=15,
                hint_strategy="worked_example",
            ),
            success_criteria=["Correctly answers 80%+ of practice questions on target nodes"],
            minimum_output="Brief summary of what was covered",
            updates_after_completion=["knowledge_mastery"],
            fallback_if_failed=[],
        )

    @staticmethod
    def for_practice(
        goal_id: str,
        bound_nodes: list[str],
        why: WhyThisTask | None = None,
        steps: list[str] | None = None,
    ) -> TaskCardProtocol:
        return TaskCardProtocol(
            task_id=TaskCardBuilder._new_id(),
            goal_id=goal_id,
            bound_nodes=bound_nodes,
            task_type="practice",
            why_this_task=why or WhyThisTask(),
            materials_protocol=MaterialsProtocol(
                retrieval_mode="task_bound_graph_rag",
                must_load_node_ids=bound_nodes,
            ),
            steps=steps or [],
            stuck_protocol=StuckProtocol(
                escalation_after_min=10,
                hint_strategy="simplify",
                aurora_wake_on_stuck=True,
            ),
            success_criteria=["Completes practice set with >=70% accuracy"],
            minimum_output="Answers submitted for all practice items",
            updates_after_completion=["capability_mastery", "knowledge_mastery"],
            fallback_if_failed=[],
        )

    @staticmethod
    def for_artifact_build(
        goal_id: str,
        bound_nodes: list[str],
        why: WhyThisTask | None = None,
        steps: list[str] | None = None,
        minimum_output: str = "",
    ) -> TaskCardProtocol:
        return TaskCardProtocol(
            task_id=TaskCardBuilder._new_id(),
            goal_id=goal_id,
            bound_nodes=bound_nodes,
            task_type="artifact_build",
            why_this_task=why or WhyThisTask(),
            materials_protocol=MaterialsProtocol(
                retrieval_mode="task_bound_graph_rag",
                may_load_node_ids=bound_nodes,
            ),
            steps=steps or [],
            stuck_protocol=StuckProtocol(
                escalation_after_min=20,
                hint_strategy="simplify",
            ),
            success_criteria=["Artifact is produced and meets minimum_output spec"],
            minimum_output=minimum_output,
            updates_after_completion=["artifact_status", "milestone_progress"],
            fallback_if_failed=[],
        )

    @staticmethod
    def for_habit_action(
        goal_id: str,
        bound_nodes: list[str],
        why: WhyThisTask | None = None,
        steps: list[str] | None = None,
    ) -> TaskCardProtocol:
        return TaskCardProtocol(
            task_id=TaskCardBuilder._new_id(),
            goal_id=goal_id,
            bound_nodes=bound_nodes,
            task_type="habit_action",
            why_this_task=why or WhyThisTask(),
            materials_protocol=MaterialsProtocol(retrieval_mode="none"),
            steps=steps or [],
            stuck_protocol=StuckProtocol(
                escalation_after_min=5,
                hint_strategy="simplify",
                fallback_task_type="habit_action",
            ),
            success_criteria=["Habit action is performed"],
            minimum_output="Check-in recorded",
            updates_after_completion=["habit_streak"],
            fallback_if_failed=[],
        )

    @staticmethod
    def for_review(
        goal_id: str,
        bound_nodes: list[str],
        why: WhyThisTask | None = None,
        steps: list[str] | None = None,
    ) -> TaskCardProtocol:
        return TaskCardProtocol(
            task_id=TaskCardBuilder._new_id(),
            goal_id=goal_id,
            bound_nodes=bound_nodes,
            task_type="review",
            why_this_task=why or WhyThisTask(),
            materials_protocol=MaterialsProtocol(
                retrieval_mode="task_bound_graph_rag",
                must_load_node_ids=bound_nodes,
            ),
            steps=steps or [],
            stuck_protocol=StuckProtocol(
                escalation_after_min=10,
                hint_strategy="simplify",
            ),
            success_criteria=["Previously learned material is recalled and refreshed"],
            minimum_output="Summary of reviewed nodes",
            updates_after_completion=["knowledge_retention"],
            fallback_if_failed=[],
        )

    @staticmethod
    def for_feedback_collection(
        goal_id: str,
        bound_nodes: list[str],
        why: WhyThisTask | None = None,
        steps: list[str] | None = None,
    ) -> TaskCardProtocol:
        return TaskCardProtocol(
            task_id=TaskCardBuilder._new_id(),
            goal_id=goal_id,
            bound_nodes=bound_nodes,
            task_type="feedback_collection",
            why_this_task=why or WhyThisTask(),
            materials_protocol=MaterialsProtocol(retrieval_mode="none"),
            steps=steps or [],
            stuck_protocol=StuckProtocol(
                escalation_after_min=15,
                hint_strategy="ask_peer",
            ),
            success_criteria=["Feedback is collected from target sources"],
            minimum_output="Feedback summary",
            updates_after_completion=["feedback_data", "relationship_trust"],
            fallback_if_failed=[],
        )

    @staticmethod
    def from_goal_type(goal_type: str, **overrides: Any) -> TaskCardProtocol:
        """Build a default task card from a goal type (exam_sprint, job_search, etc.)."""
        defaults: dict[str, Any] = {
            "exam_sprint": {"task_type": "study", "stuck_hint": "worked_example"},
            "job_search_interview": {"task_type": "practice", "stuck_hint": "simplify"},
            "project_delivery": {"task_type": "artifact_build", "stuck_hint": "simplify"},
            "fitness": {"task_type": "habit_action", "stuck_hint": "simplify"},
            "startup": {"task_type": "artifact_build", "stuck_hint": "simplify"},
            "general": {"task_type": "study", "stuck_hint": "worked_example"},
        }
        cfg = defaults.get(goal_type, defaults["general"])
        task_type = overrides.get("task_type", cfg["task_type"])

        builder_map = {
            "study": TaskCardBuilder.for_study,
            "practice": TaskCardBuilder.for_practice,
            "artifact_build": TaskCardBuilder.for_artifact_build,
            "habit_action": TaskCardBuilder.for_habit_action,
            "review": TaskCardBuilder.for_review,
            "feedback_collection": TaskCardBuilder.for_feedback_collection,
        }
        builder = builder_map.get(task_type, TaskCardBuilder.for_study)
        card = builder(
            goal_id=overrides.get("goal_id", ""),
            bound_nodes=overrides.get("bound_nodes", []),
        )
        for k, v in overrides.items():
            if hasattr(card, k) and k not in ("goal_id", "bound_nodes", "task_type"):
                setattr(card, k, v)
        return card

    @staticmethod
    def _new_id() -> str:
        return f"tcp_{uuid.uuid4().hex[:12]}"


class TaskCardBridge:
    """Converts between the existing planning_workflow guide_json format and TaskCardProtocol."""

    @staticmethod
    def from_guide_json(
        guide_json: dict[str, Any],
        goal_id: str = "",
        task_id: str = "",
    ) -> TaskCardProtocol:
        """Build a TaskCardProtocol from a planning_workflow guide_json dict.

        Bridges the existing exam-sprint dict format to the typed protocol.
        Used for validation and audit trail — does not replace guide_json generation.
        """
        why_raw = guide_json.get("why_this_task")
        why: WhyThisTask
        if isinstance(why_raw, dict):
            why = WhyThisTask(
                signal_ids=why_raw.get("signal_ids", []),
                policy_decision_id=why_raw.get("policy_decision_id"),
                bottleneck_node_id=why_raw.get("bottleneck_node_id"),
                reasoning_summary=why_raw.get("reasoning_summary", ""),
            )
        else:
            why = WhyThisTask(reasoning_summary=str(why_raw or ""))

        mp_raw = guide_json.get("materials_protocol", {})
        if isinstance(mp_raw, dict):
            mp = MaterialsProtocol(
                retrieval_mode=mp_raw.get("retrieval_mode", "task_bound_graph_rag"),
                must_load_node_ids=mp_raw.get("must_load_node_ids", []),
                may_load_node_ids=mp_raw.get("may_load_node_ids", []),
                source_tray_selection=mp_raw.get("source_tray_selection", []),
            )
        else:
            mp = MaterialsProtocol()

        sp_raw = guide_json.get("stuck_protocol", {})
        sp = StuckProtocol(
            escalation_after_min=int(guide_json.get("time_estimate_minutes", 25) // 2),
            hint_strategy="worked_example",
        )
        if isinstance(sp_raw, dict) and "knows_rules_cant_solve" in sp_raw:
            sp.hint_strategy = "worked_example"
        elif isinstance(sp_raw, dict) and "cant_understand_rules" in sp_raw:
            sp.hint_strategy = "simplify"

        raw_task_kind = guide_json.get("task_kind", "retrieval_drill")
        task_type_map = {
            "retrieval_drill": "practice",
            "diagnostic_triage": "study",
            "worked_example": "practice",
            "artifact_build": "artifact_build",
            "habit_action": "habit_action",
            "review": "review",
            "feedback_collection": "feedback_collection",
        }
        task_type = task_type_map.get(raw_task_kind, "study")

        success_raw = guide_json.get("success_criteria", "")
        success_criteria = [success_raw] if isinstance(success_raw, str) and success_raw else (
            success_raw if isinstance(success_raw, list) else []
        )

        updates_raw = guide_json.get("updates_after_completion", [])
        updates = updates_raw if isinstance(updates_raw, list) else []

        return TaskCardProtocol(
            task_id=task_id or TaskCardBuilder._new_id(),
            goal_id=goal_id,
            task_type=task_type,
            bound_nodes=[],
            why_this_task=why,
            materials_protocol=mp,
            steps=list(guide_json.get("method_steps", [])),
            stuck_protocol=sp,
            success_criteria=success_criteria,
            minimum_output=guide_json.get("minimum_output", ""),
            updates_after_completion=updates,
            fallback_if_failed=[],
        )

    @staticmethod
    def validate_guide_json(
        guide_json: dict[str, Any],
        goal_id: str = "",
        task_id: str = "",
    ) -> list[str]:
        """Convenience: bridge to TaskCardProtocol and validate. Returns issue list."""
        card = TaskCardBridge.from_guide_json(guide_json, goal_id=goal_id, task_id=task_id)
        return TaskCardValidator.validate(card)


class TaskCardValidator:
    """Validates TaskCardProtocol instances for completeness and correctness."""

    REQUIRED_FIELDS = [
        "task_id", "goal_id", "task_type", "success_criteria", "minimum_output",
    ]

    @staticmethod
    def validate(card: TaskCardProtocol) -> list[str]:
        issues: list[str] = []

        if card.task_type not in TASK_TYPES:
            issues.append(f"Invalid task_type: {card.task_type}")

        if not card.goal_id:
            issues.append("goal_id is required")

        if not card.success_criteria:
            issues.append("At least one success_criterion is required")

        if not card.minimum_output:
            issues.append("minimum_output is required")

        # Validate node bindings
        if card.bound_nodes:
            for _node_id in card.bound_nodes:
                pass  # Node existence checked by GoalWorldGraph at runtime

        # Domain-specific rules
        if card.is_artifact_task() and not card.minimum_output:
            issues.append("artifact_build tasks must define minimum_output")

        if card.is_habit_task() and card.materials_protocol.retrieval_mode != "none":
            issues.append("habit_action tasks should not load materials (soft warning)")

        return issues

    @staticmethod
    def outcome_fields_for_type(task_type: str) -> list[str]:
        """Return the state keys that a completed task of this type should update."""
        outcome_map: dict[str, list[str]] = {
            "study":               ["knowledge_mastery"],
            "practice":            ["capability_mastery", "knowledge_mastery"],
            "artifact_build":      ["artifact_status", "milestone_progress"],
            "habit_action":        ["habit_streak"],
            "review":              ["knowledge_retention"],
            "feedback_collection": ["feedback_data", "relationship_trust"],
        }
        return outcome_map.get(task_type, [])
