"""
Core: execution
Phase: plan→execute→adapt
Stage: Signal-to-Action Spine P3-1

GoalTypeAdapter — generalize GoalWorldGraph behavior beyond exam sprint goals.

The adapter keeps the exam-specific defaults intact while giving other goal
types their own labels, phase cadence, mastery interpretation, and recall copy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.signals.exam_sprint_policy import ExamSprintPolicyService

_logger = logging.getLogger(__name__)


@dataclass
class GoalTypeProfile:
    goal_type: str
    deadline_sensitive: bool
    mastery_trackable: bool
    has_knowledge_graph: bool
    default_phase_count: int
    default_sprint_duration_days: int
    node_label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "deadline_sensitive": self.deadline_sensitive,
            "mastery_trackable": self.mastery_trackable,
            "has_knowledge_graph": self.has_knowledge_graph,
            "default_phase_count": self.default_phase_count,
            "default_sprint_duration_days": self.default_sprint_duration_days,
            "node_label": self.node_label,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GoalTypeProfile:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    @classmethod
    def get_profile(cls, goal_type: str) -> GoalTypeProfile:
        normalized = _normalize_goal_type(goal_type)
        return GOAL_TYPE_PROFILES.get(normalized, GOAL_TYPE_PROFILES["general"])


GOAL_TYPE_PROFILES = {
    "exam": GoalTypeProfile(
        goal_type="exam",
        deadline_sensitive=True,
        mastery_trackable=True,
        has_knowledge_graph=True,
        default_phase_count=5,
        default_sprint_duration_days=7,
        node_label="知识点",
    ),
    "project": GoalTypeProfile(
        goal_type="project",
        deadline_sensitive=True,
        mastery_trackable=False,
        has_knowledge_graph=False,
        default_phase_count=4,
        default_sprint_duration_days=14,
        node_label="里程碑",
    ),
    "job_search": GoalTypeProfile(
        goal_type="job_search",
        deadline_sensitive=False,
        mastery_trackable=True,
        has_knowledge_graph=True,
        default_phase_count=5,
        default_sprint_duration_days=30,
        node_label="技能",
    ),
    "fitness": GoalTypeProfile(
        goal_type="fitness",
        deadline_sensitive=False,
        mastery_trackable=True,
        has_knowledge_graph=False,
        default_phase_count=3,
        default_sprint_duration_days=30,
        node_label="训练目标",
    ),
    "startup": GoalTypeProfile(
        goal_type="startup",
        deadline_sensitive=True,
        mastery_trackable=False,
        has_knowledge_graph=False,
        default_phase_count=6,
        default_sprint_duration_days=14,
        node_label="交付物",
    ),
    "general": GoalTypeProfile(
        goal_type="general",
        deadline_sensitive=False,
        mastery_trackable=False,
        has_knowledge_graph=False,
        default_phase_count=3,
        default_sprint_duration_days=7,
        node_label="步骤",
    ),
}

_GOAL_TYPE_ALIASES = {
    "exam_rescue": "exam",
    "exam_build": "exam",
    "test": "exam",
    "考试": "exam",
    "academic": "academic",
    "school": "academic",
    "study": "academic",
    "project_delivery": "project",
    "项目": "project",
    "career": "job_search",
    "job": "job_search",
    "求职": "job_search",
    "skill": "skill",
    "skills": "skill",
    "health": "fitness",
    "workout": "fitness",
    "健身": "fitness",
    "habit": "habit",
    "habits": "habit",
    "创业": "startup",
    "other": "other",
    "general": "general",
}

_MASTERY_BUCKETS = (
    (0.3, "low"),
    (0.55, "building"),
    (0.8, "solid"),
    (1.01, "ready"),
)

_GOAL_MASTERY_MAPPINGS: dict[str, dict[str, dict[str, Any]]] = {
    "project": {
        "low": {"task_type": "outline", "difficulty": 2, "focus": "clarify_scope"},
        "building": {"task_type": "draft", "difficulty": 3, "focus": "produce_working_version"},
        "solid": {"task_type": "review", "difficulty": 2, "focus": "tighten_quality"},
        "ready": {"task_type": "submit", "difficulty": 1, "focus": "final_delivery_check"},
    },
    "job_search": {
        "low": {"task_type": "learn", "difficulty": 3, "focus": "close_skill_gap"},
        "building": {"task_type": "practice", "difficulty": 3, "focus": "build_application_reps"},
        "solid": {"task_type": "mock", "difficulty": 2, "focus": "simulate_interview"},
        "ready": {"task_type": "apply", "difficulty": 1, "focus": "ship_applications"},
    },
    "fitness": {
        "low": {"task_type": "foundation_form", "difficulty": 2, "focus": "safe_baseline"},
        "building": {"task_type": "workout_block", "difficulty": 3, "focus": "consistent_execution"},
        "solid": {"task_type": "progressive_overload", "difficulty": 3, "focus": "measured_improvement"},
        "ready": {"task_type": "maintenance_check", "difficulty": 1, "focus": "sustain_rhythm"},
    },
    "startup": {
        "low": {"task_type": "validate", "difficulty": 3, "focus": "de_risk_assumption"},
        "building": {"task_type": "prototype", "difficulty": 4, "focus": "build_testable_artifact"},
        "solid": {"task_type": "launch", "difficulty": 3, "focus": "reach_real_users"},
        "ready": {"task_type": "iterate", "difficulty": 2, "focus": "learn_from_feedback"},
    },
    "general": {
        "low": {"task_type": "clarify", "difficulty": 2, "focus": "define_next_step"},
        "building": {"task_type": "execute", "difficulty": 3, "focus": "make_progress"},
        "solid": {"task_type": "review", "difficulty": 2, "focus": "improve_result"},
        "ready": {"task_type": "finish", "difficulty": 1, "focus": "close_loop"},
    },
}

_SPRINT_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "exam": [
        {"phase_id": "build_path", "focus": "minimum_passing_path", "task_type_bias": "mixed"},
        {"phase_id": "bottleneck_training", "focus": "main_bottleneck", "task_type_bias": "worked_example"},
        {"phase_id": "error_repair", "focus": "high_frequency_errors", "task_type_bias": "drill"},
        {"phase_id": "survival", "focus": "exam_survival_strategy", "task_type_bias": "review"},
        {"phase_id": "final_review", "focus": "high_yield_review_only", "task_type_bias": "review"},
    ],
    "project": [
        {"phase_id": "scope", "focus": "define_delivery_shape", "task_type_bias": "outline"},
        {"phase_id": "build", "focus": "create_working_draft", "task_type_bias": "draft"},
        {"phase_id": "review", "focus": "quality_and_risk_check", "task_type_bias": "review"},
        {"phase_id": "ship", "focus": "submit_or_publish", "task_type_bias": "submit"},
    ],
    "job_search": [
        {"phase_id": "positioning", "focus": "target_roles_and_gaps", "task_type_bias": "learn"},
        {"phase_id": "assets", "focus": "resume_and_portfolio", "task_type_bias": "draft"},
        {"phase_id": "practice", "focus": "interview_rehearsal", "task_type_bias": "practice"},
        {"phase_id": "apply", "focus": "send_applications", "task_type_bias": "apply"},
        {"phase_id": "follow_up", "focus": "follow_up_and_adjust", "task_type_bias": "review"},
    ],
    "fitness": [
        {"phase_id": "baseline", "focus": "safe_starting_point", "task_type_bias": "foundation_form"},
        {"phase_id": "build", "focus": "consistent_training", "task_type_bias": "workout_block"},
        {"phase_id": "sustain", "focus": "maintain_and_adjust", "task_type_bias": "maintenance_check"},
    ],
    "startup": [
        {"phase_id": "problem", "focus": "problem_clarity", "task_type_bias": "validate"},
        {"phase_id": "customer", "focus": "customer_discovery", "task_type_bias": "interview"},
        {"phase_id": "prototype", "focus": "testable_artifact", "task_type_bias": "prototype"},
        {"phase_id": "launch", "focus": "real_user_launch", "task_type_bias": "launch"},
        {"phase_id": "metrics", "focus": "measure_signal", "task_type_bias": "review"},
        {"phase_id": "iterate", "focus": "next_iteration", "task_type_bias": "iterate"},
    ],
    "general": [
        {"phase_id": "clarify", "focus": "define_next_step", "task_type_bias": "clarify"},
        {"phase_id": "execute", "focus": "make_visible_progress", "task_type_bias": "execute"},
        {"phase_id": "review", "focus": "close_loop", "task_type_bias": "review"},
    ],
}

_RECALL_COPY = {
    "exam": {
        "undigested_material": "还有资料没有转成考前复习动作，先抓一块最高频内容。",
        "task_not_started": "考前复习还没启动，先做一个 15 分钟的最小可过任务。",
        "task_missed": "刚才那步没完成，我们把它降到更短的复习动作。",
        "pre_exam_silence": "考前窗口很近了，先只看高收益知识点，不开新坑。",
    },
    "project": {
        "undigested_material": "还有资料没有转成交付前检查项，先抽一条直接推进里程碑。",
        "task_not_started": "项目任务还没启动，先做一个可见的小交付。",
        "task_missed": "刚才的里程碑没推进，我们把范围收窄到下一版草稿。",
        "pre_exam_silence": "截止前先做交付前检查，聚焦风险和缺口。",
    },
    "job_search": {
        "undigested_material": "还有求职资料没转成行动，先提炼一条简历或面试练习。",
        "task_not_started": "求职节奏还没启动，先完成一个可投递动作。",
        "task_missed": "刚才那步没完成，我们换成更短的练习或投递。",
        "pre_exam_silence": "先做一次投递前检查：岗位、材料、下一步。",
    },
    "fitness": {
        "undigested_material": "还有训练信息没转成动作，先选一个安全的小训练目标。",
        "task_not_started": "训练还没启动，先做一个低门槛动作。",
        "task_missed": "刚才的训练没完成，我们降到更容易开始的版本。",
        "pre_exam_silence": "先做一次训练前检查：状态、强度、安全边界。",
    },
    "startup": {
        "undigested_material": "还有信息没转成创业交付物，先验证一个关键假设。",
        "task_not_started": "推进还没启动，先做一个能拿到反馈的小交付。",
        "task_missed": "刚才那步没完成，我们把它改成更小的验证动作。",
        "pre_exam_silence": "交付前先检查假设、风险和下一次用户反馈。",
    },
    "general": {
        "undigested_material": "还有资料没有变成下一步，先挑一个最小动作。",
        "task_not_started": "任务还没启动，先做一个短到能开始的版本。",
        "task_missed": "刚才那步没完成，我们把它缩小一点再继续。",
        "pre_exam_silence": "先做一次开始前检查：目标、材料、下一步。",
    },
}


def _normalize_goal_type(goal_type: str) -> str:
    """Backward-compatible wrapper used by goal_type_adapter internals."""
    return normalize_goal_type(goal_type)


# ---------------------------------------------------------------------------
# Centralized goal-type canonical map (R1A3-Finding8)
# ---------------------------------------------------------------------------

# All known canonical types.
_CANONICAL_GOAL_TYPES = frozenset({
    "exam", "academic", "project", "job_search", "skill",
    "fitness", "habit", "startup", "other", "general",
})

GOAL_TYPE_CANONICAL_MAP: dict[str, str] = {
    # ---- exam / academic family ----
    "exam": "exam",
    "exam_rescue": "exam",
    "exam_build": "exam",
    "test": "exam",
    "考试": "exam",
    "academic": "academic",
    "school": "academic",
    "study": "academic",
    # ---- project family ----
    "project": "project",
    "project_delivery": "project",
    "项目": "project",
    # ---- job_search / skill family ----
    "job_search": "job_search",
    "career": "job_search",
    "job": "job_search",
    "求职": "job_search",
    "skill": "skill",
    "skills": "skill",
    # ---- fitness / habit family ----
    "fitness": "fitness",
    "health": "fitness",
    "workout": "fitness",
    "健身": "fitness",
    "habit": "habit",
    "habits": "habit",
    # ---- startup family ----
    "startup": "startup",
    "创业": "startup",
    # ---- other / general family ----
    "other": "other",
    "general": "general",
}


def normalize_goal_type(raw_type: str) -> str:
    """Canonicalize a goal type string using GOAL_TYPE_CANONICAL_MAP.

    Returns the canonical type.  If *raw_type* is unknown the value is
    returned unchanged and a warning is logged so that new types added
    on one side without updating the map are visible in logs.
    """
    normalized = str(raw_type or "other").strip().lower()
    canonical = GOAL_TYPE_CANONICAL_MAP.get(normalized)
    if canonical is not None:
        return canonical
    # Unknown type — log a warning and pass through as-is.
    _logger.warning("Unknown goal type %r (raw=%r); consider adding to GOAL_TYPE_CANONICAL_MAP", normalized, raw_type)
    return normalized


def _clamp_mastery(mastery: float) -> float:
    return max(0.0, min(1.0, float(mastery)))


def _mastery_bucket(mastery: float) -> str:
    score = _clamp_mastery(mastery)
    for threshold, bucket in _MASTERY_BUCKETS:
        if score < threshold:
            return bucket
    return "ready"


def _phase_day_ranges(days_to_deadline: int, phase_count: int) -> list[tuple[int, int]]:
    days = max(0, int(days_to_deadline))
    if phase_count <= 1:
        return [(0, days)]
    ranges: list[tuple[int, int]] = []
    for index in range(phase_count):
        high = round(days - (days * index / phase_count))
        low = round(days - (days * (index + 1) / phase_count))
        ranges.append((max(0, low), max(0, high)))
    return ranges


class GoalTypeAdapter:
    """Adapt spine policies to different goal types."""

    def adapt_mastery_mapping(self, mastery: float, goal_type: str) -> dict[str, Any]:
        profile = GoalTypeProfile.get_profile(goal_type)
        score = _clamp_mastery(mastery)
        if profile.goal_type == "exam":
            exam_policy = ExamSprintPolicyService()
            return {
                "goal_type": profile.goal_type,
                "node_label": profile.node_label,
                "mastery": score,
                "task_type": exam_policy.mastery_to_task_type(score),
                "difficulty": exam_policy.mastery_to_difficulty(score),
                "focus": "exam_mastery_gap",
                "mastery_trackable": profile.mastery_trackable,
            }

        bucket = _mastery_bucket(score)
        mapping = _GOAL_MASTERY_MAPPINGS.get(profile.goal_type, _GOAL_MASTERY_MAPPINGS["general"])[bucket]
        return {
            "goal_type": profile.goal_type,
            "node_label": profile.node_label,
            "mastery": score,
            "mastery_bucket": bucket,
            "task_type": mapping["task_type"],
            "difficulty": mapping["difficulty"],
            "focus": mapping["focus"],
            "mastery_trackable": profile.mastery_trackable,
        }

    def adapt_sprint_phases(self, days_to_deadline: int, goal_type: str) -> list[dict[str, Any]]:
        profile = GoalTypeProfile.get_profile(goal_type)
        templates = _SPRINT_TEMPLATES.get(profile.goal_type, _SPRINT_TEMPLATES["general"])
        ranges = _phase_day_ranges(days_to_deadline, len(templates))
        urgency = "deadline" if profile.deadline_sensitive and days_to_deadline <= profile.default_sprint_duration_days else "steady"

        phases = []
        for index, template in enumerate(templates):
            low, high = ranges[index]
            phases.append(
                {
                    "phase_id": template["phase_id"],
                    "goal_type": profile.goal_type,
                    "order": index + 1,
                    "days_range": (low, high),
                    "focus": template["focus"],
                    "task_type_bias": template["task_type_bias"],
                    "node_label": profile.node_label,
                    "urgency": urgency,
                    "retrieval_mode": "task_bound_graph_rag" if profile.has_knowledge_graph else "targeted_source_rag",
                    "mastery_trackable": profile.mastery_trackable,
                }
            )
        return phases

    def adapt_recall_message(self, trigger_type: str, goal_type: str, context: dict[str, Any]) -> str:
        profile = GoalTypeProfile.get_profile(goal_type)
        trigger_key = str(trigger_type or "").strip()
        templates = _RECALL_COPY.get(profile.goal_type, _RECALL_COPY["general"])
        message = templates.get(trigger_key, _RECALL_COPY["general"].get(trigger_key, "先把目标收束成一个下一步。"))

        subject = str(context.get("subject") or context.get("target") or "").strip()
        if subject:
            return f"{subject}：{message}"
        return message
