"""
Core: execution
Phase: plan→execute
Stage: Signal-to-Action Spine P0-6

ExamSprintPolicy — Deadline-phase adaptive strategy.

Maps days-to-deadline (D-30→D-0) to progressive constraints per Final Spec Section 6.4:
  D-30 to D-8: Foundation building (broad study, new chapters ok)
  D-7 to D-5: Build minimum passing path
  D-4 to D-3: Main bottleneck training
  D-2:        High-frequency error repair
  D-1:        Exam survival strategy
  D-0:        Only high-yield review, no new ground
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class ExamSprintPhase:
    phase_id: str                 # foundation / build_path / bottleneck_training / error_repair / survival / final_review
    days_range: tuple[int, int]   # (days_left, days_left) inclusive
    max_task_duration_min: int
    allow_new_chapters: bool
    prefer_high_yield_review: bool
    retrieval_mode: str           # graph_summary_or_exam_pack / targeted_source_rag / task_bound_graph_rag
    difficulty_cap: int           # 1-5
    tone: str
    task_type_bias: str           # worked_example / drill / review / mixed

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "days_range": self.days_range,
            "max_task_duration_min": self.max_task_duration_min,
            "allow_new_chapters": self.allow_new_chapters,
            "prefer_high_yield_review": self.prefer_high_yield_review,
            "retrieval_mode": self.retrieval_mode,
            "difficulty_cap": self.difficulty_cap,
            "tone": self.tone,
            "task_type_bias": self.task_type_bias,
        }


@dataclass
class ExamSprintDirective:
    directive_id: str
    phase: ExamSprintPhase
    days_to_deadline: int
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "phase": self.phase.to_dict(),
            "days_to_deadline": self.days_to_deadline,
            "constraints": self.constraints,
        }


# ── Phase definitions per Final Spec Section 6.4 ────────────────────────

_PHASE_TABLE: list[ExamSprintPhase] = [
    ExamSprintPhase(
        phase_id="foundation",
        days_range=(8, 30),
        max_task_duration_min=60,
        allow_new_chapters=True,
        prefer_high_yield_review=False,
        retrieval_mode="targeted_source_rag",
        difficulty_cap=4,
        tone="calm_direct",
        task_type_bias="mixed",
    ),
    ExamSprintPhase(
        phase_id="build_path",
        days_range=(5, 7),
        max_task_duration_min=45,
        allow_new_chapters=True,
        prefer_high_yield_review=False,
        retrieval_mode="targeted_source_rag",
        difficulty_cap=3,
        tone="calm_direct",
        task_type_bias="mixed",
    ),
    ExamSprintPhase(
        phase_id="bottleneck_training",
        days_range=(3, 4),
        max_task_duration_min=35,
        allow_new_chapters=False,
        prefer_high_yield_review=False,
        retrieval_mode="task_bound_graph_rag",
        difficulty_cap=3,
        tone="calm_direct",
        task_type_bias="worked_example",
    ),
    ExamSprintPhase(
        phase_id="error_repair",
        days_range=(2, 2),
        max_task_duration_min=25,
        allow_new_chapters=False,
        prefer_high_yield_review=True,
        retrieval_mode="task_bound_graph_rag",
        difficulty_cap=2,
        tone="calm_urgent",
        task_type_bias="drill",
    ),
    ExamSprintPhase(
        phase_id="survival",
        days_range=(1, 1),
        max_task_duration_min=20,
        allow_new_chapters=False,
        prefer_high_yield_review=True,
        retrieval_mode="graph_summary_or_exam_pack",
        difficulty_cap=2,
        tone="calm_urgent",
        task_type_bias="review",
    ),
    ExamSprintPhase(
        phase_id="final_review",
        days_range=(0, 0),
        max_task_duration_min=15,
        allow_new_chapters=False,
        prefer_high_yield_review=True,
        retrieval_mode="graph_summary_or_exam_pack",
        difficulty_cap=1,
        tone="calm_urgent",
        task_type_bias="review",
    ),
]


def _compute_phase(days_to_deadline: int) -> ExamSprintPhase:
    """Map days-to-deadline to the correct ExamSprintPhase."""
    if days_to_deadline < 0:
        return _PHASE_TABLE[-1]  # past deadline = final_review
    for phase in _PHASE_TABLE:
        lo, hi = phase.days_range
        if lo <= days_to_deadline <= hi:
            return phase
    # Fallback for days > 7
    return _PHASE_TABLE[0]


class ExamSprintPolicyService:
    """
    Computes Exam Sprint strategy constraints based on deadline proximity.

    Used by SpineOrchestrator to generate phase-appropriate directives
    when goal_mode is exam_rescue.
    """

    def compute(
        self,
        *,
        days_to_deadline: int,
        subject: str = "",
    ) -> ExamSprintDirective:
        phase = _compute_phase(days_to_deadline)
        constraints = {
            "max_task_duration_min": phase.max_task_duration_min,
            "allow_new_chapters": phase.allow_new_chapters,
            "prefer_high_yield_review": phase.prefer_high_yield_review,
            "retrieval_mode": phase.retrieval_mode,
            "difficulty_cap": phase.difficulty_cap,
            "task_type_bias": phase.task_type_bias,
        }
        logger.info(
            "ExamSprintPolicy: days_left={} phase={} max_dur={} allow_new={}",
            days_to_deadline, phase.phase_id,
            phase.max_task_duration_min, phase.allow_new_chapters,
        )
        from app.signals.types import _uid
        return ExamSprintDirective(
            directive_id=_uid("esp"),
            phase=phase,
            days_to_deadline=days_to_deadline,
            constraints=constraints,
        )

    @staticmethod
    def should_activate(
        *,
        goal_mode: str,
        days_to_deadline: int | None,
    ) -> bool:
        """Check if ExamSprintPolicy should be active."""
        if days_to_deadline is None:
            return False
        return goal_mode == "exam_rescue" and days_to_deadline <= 30

    # ── Galaxy 掌握度 → 任务难度映射 (v1.1 Section 8.3) ─────────────

    @staticmethod
    def mastery_to_task_type(mastery: float) -> str:
        """Map per-node mastery to recommended task type."""
        mastery = max(0.0, min(1.0, mastery))
        if mastery < 0.3:
            return "concept_compression"
        elif mastery < 0.5:
            return "worked_example_guided_drill"
        elif mastery < 0.7:
            return "drill_mistake_check"
        return "mixed_practice_exam_simulation"

    @staticmethod
    def mastery_to_difficulty(mastery: float) -> int:
        """
        Map per-node mastery to task difficulty (1-5).

        mastery 0-30% → difficulty 4-5 (hard, needs foundation)
        mastery 30-60% → difficulty 2-3 (medium, practice)
        mastery 60%+ → difficulty 1 (light review)
        """
        mastery = max(0.0, min(1.0, mastery))
        if mastery < 0.3:
            return 5
        elif mastery < 0.5:
            return 3
        elif mastery < 0.7:
            return 2
        return 1

    def score_node_priorities(
        self,
        node_masteries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Score and sort nodes by exam priority.

        Each input: {"node_id": str, "label": str, "mastery": float, "exam_weight": float}

        Priority = (1 - mastery) * exam_weight
        Lower mastery + higher exam weight = higher priority.
        """
        scored = []
        for node in node_masteries:
            mastery = max(0.0, min(1.0, float(node.get("mastery", 0.5))))
            exam_weight = float(node.get("exam_weight", 1.0))
            priority_score = round((1.0 - mastery) * exam_weight, 2)
            scored.append({
                **node,
                "mastery": mastery,
                "priority_score": priority_score,
                "recommended_task_type": self.mastery_to_task_type(mastery),
                "recommended_difficulty": self.mastery_to_difficulty(mastery),
            })
        scored.sort(key=lambda n: n["priority_score"], reverse=True)
        return scored
