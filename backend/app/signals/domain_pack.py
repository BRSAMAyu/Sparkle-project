"""
Core: execution
Phase: plan→adapt
Stage: Signal-to-Action Spine P3-2 DomainPack System

Per ruling Section 14: DomainPack encapsulates domain-specific config.
New goal domains don't require Spine rewrite — just add a DomainPack.

3 initial packs: exam_sprint, job_search_interview, project_delivery.
Each pack defines: node_schema, task_templates, feedback_taxonomy,
risk_patterns, checkpoint_rules, aurora_trigger_rules, skill_library.

PolicyEngine still uses same State/Policy/Directive mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeSchemaEntry:
    node_type: str
    required: bool = True
    default_status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_type": self.node_type,
            "required": self.required,
            "default_status": self.default_status,
        }


@dataclass
class FeedbackTaxonomyEntry:
    feedback_type: str
    label: str
    triggers_aurora: bool = False
    strategy_effect: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "feedback_type": self.feedback_type,
            "label": self.label,
            "triggers_aurora": self.triggers_aurora,
            "strategy_effect": self.strategy_effect,
        }


@dataclass
class RiskPatternEntry:
    risk_id: str
    label: str
    detection_signal: str
    mitigation_strategy: str
    severity: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_id": self.risk_id,
            "label": self.label,
            "detection_signal": self.detection_signal,
            "mitigation_strategy": self.mitigation_strategy,
            "severity": self.severity,
        }


@dataclass
class CheckpointRule:
    checkpoint_id: str
    trigger_after_tasks: int
    checks: list[str]
    user_visible: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "trigger_after_tasks": self.trigger_after_tasks,
            "checks": self.checks,
            "user_visible": self.user_visible,
        }


@dataclass
class AuroraTriggerRule:
    trigger_id: str
    condition: str  # e.g. "correction_frequency >= 3.0"
    quota_override: str = ""  # e.g. "sprint" for higher quota
    wake_reason_template: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_id": self.trigger_id,
            "condition": self.condition,
            "quota_override": self.quota_override,
            "wake_reason_template": self.wake_reason_template,
        }


@dataclass
class SkillTemplate:
    skill_id: str
    label: str
    applicable_contexts: list[str]
    success_criteria: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "label": self.label,
            "applicable_contexts": self.applicable_contexts,
            "success_criteria": self.success_criteria,
        }


@dataclass
class DomainPack:
    """Encapsulates domain-specific configuration for a goal type."""
    domain_pack_id: str
    domain: str
    supported_goal_modes: list[str]
    node_schema: list[NodeSchemaEntry]
    task_templates: list[dict[str, Any]] = field(default_factory=list)
    feedback_taxonomy: list[FeedbackTaxonomyEntry] = field(default_factory=list)
    risk_patterns: list[RiskPatternEntry] = field(default_factory=list)
    checkpoint_rules: list[CheckpointRule] = field(default_factory=list)
    aurora_trigger_rules: list[AuroraTriggerRule] = field(default_factory=list)
    skill_library: list[SkillTemplate] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)
    outcome_metrics: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain_pack_id": self.domain_pack_id,
            "domain": self.domain,
            "supported_goal_modes": self.supported_goal_modes,
            "node_schema": [s.to_dict() for s in self.node_schema],
            "task_templates": self.task_templates,
            "feedback_taxonomy": [f.to_dict() for f in self.feedback_taxonomy],
            "risk_patterns": [r.to_dict() for r in self.risk_patterns],
            "checkpoint_rules": [c.to_dict() for c in self.checkpoint_rules],
            "aurora_trigger_rules": [a.to_dict() for a in self.aurora_trigger_rules],
            "skill_library": [s.to_dict() for s in self.skill_library],
            "source_types": self.source_types,
            "outcome_metrics": self.outcome_metrics,
        }


# ── 3 Initial Domain Packs (ruling Section 14) ──────────────────────

EXAM_SPRINT_PACK = DomainPack(
    domain_pack_id="exam_sprint_pack_v1",
    domain="exam_sprint",
    supported_goal_modes=["exam_rescue", "exam_build"],
    node_schema=[
        NodeSchemaEntry("knowledge", required=True),
        NodeSchemaEntry("resource", required=False),
        NodeSchemaEntry("risk", required=False),
    ],
    task_templates=[
        {"task_type": "worked_example", "focus": "bottleneck_practice"},
        {"task_type": "drill", "focus": "high_frequency_errors"},
        {"task_type": "review", "focus": "high_yield_review"},
    ],
    feedback_taxonomy=[
        FeedbackTaxonomyEntry("transfer_failure", "同类题连续出错", triggers_aurora=True, strategy_effect="switch_to_worked_example"),
        FeedbackTaxonomyEntry("knowledge_gap", "不会做", strategy_effect="reduce_task_size"),
        FeedbackTaxonomyEntry("speed_issue", "做太慢", strategy_effect="add_time_constraint"),
    ],
    risk_patterns=[
        RiskPatternEntry("exam_eve_overload", "考前还开新坑", "task_count_on_last_day > 5", "freeze_new_chapters", "high"),
        RiskPatternEntry("burnout", "连续放弃", "task_abandoned_streak >= 3", "reduce_load_and_encourage", "high"),
        RiskPatternEntry("illusion_of_mastery", "只看不练", "review_count >> practice_count", "force_practice_task", "medium"),
    ],
    checkpoint_rules=[
        CheckpointRule("half_sprint", trigger_after_tasks=5, checks=["coverage >= 0.3", "no_critical_bottleneck"]),
        CheckpointRule("pre_exam_24h", trigger_after_tasks=999, checks=["only_high_yield", "no_new_material"], user_visible=True),
    ],
    aurora_trigger_rules=[
        AuroraTriggerRule("repeated_failure", "correction_frequency >= 3.0", quota_override="sprint", wake_reason_template="策略连续无效，需要校准"),
        AuroraTriggerRule("stake_mismatch", "motivation == 'must_pass' AND progress < 0.3 AND days_left <= 2", quota_override="crisis"),
    ],
    skill_library=[
        SkillTemplate("worked_example_practice", "做例题→归纳", ["transfer_failure", "knowledge_gap"], "3次同类题正确率 >= 0.67"),
        SkillTemplate("spaced_review", "间隔复习", ["illusion_of_mastery"], "复习间隔递增且正确率不降"),
    ],
    source_types=["course_slides", "past_exams", "textbook_sections", "video_lectures"],
    outcome_metrics=["mastery_delta", "task_completion_rate", "error_reduction_rate", "time_per_task"],
)

JOB_SEARCH_INTERVIEW_PACK = DomainPack(
    domain_pack_id="job_search_interview_pack_v1",
    domain="job_search_interview",
    supported_goal_modes=["interview_sprint", "resume_refinement", "portfolio_building"],
    node_schema=[
        NodeSchemaEntry("capability", required=True),
        NodeSchemaEntry("artifact", required=True),
        NodeSchemaEntry("milestone", required=False),
        NodeSchemaEntry("feedback", required=True),
        NodeSchemaEntry("risk", required=False),
    ],
    task_templates=[
        {"task_type": "learn", "focus": "close_skill_gap"},
        {"task_type": "draft", "focus": "produce_artifact"},
        {"task_type": "mock", "focus": "simulate_interview"},
        {"task_type": "apply", "focus": "ship_application"},
    ],
    feedback_taxonomy=[
        FeedbackTaxonomyEntry("interview_rejection", "面试未通过", triggers_aurora=True, strategy_effect="review_weak_signals"),
        FeedbackTaxonomyEntry("resume_gap", "简历缺关键经历", strategy_effect="add_experience_project"),
        FeedbackTaxonomyEntry("nervousness", "面试紧张", strategy_effect="more_mock_reps"),
    ],
    risk_patterns=[
        RiskPatternEntry("scatter", "投递太散无聚焦", "applications > 10 AND no_interview", "narrow_target_roles", "high"),
        RiskPatternEntry("stale_resume", "简历长期未更新", "days_since_resume_update > 30", "refresh_resume", "medium"),
    ],
    checkpoint_rules=[
        CheckpointRule("after_5_applications", trigger_after_tasks=5, checks=["resume_updated", "cover_template_ready"]),
    ],
    aurora_trigger_rules=[
        AuroraTriggerRule("prolonged_no_response", "applications_sent >= 5 AND interviews_received == 0", quota_override="sprint"),
    ],
    skill_library=[
        SkillTemplate("mock_interview_reps", "模拟面试练习", ["interview_rejection", "nervousness"], "3次模拟评分递增"),
        SkillTemplate("resume_tailoring", "针对性简历调整", ["resume_gap", "scatter"], "每个岗位定制版本"),
    ],
    source_types=["job_descriptions", "company_research", "interview_prep_materials", "resume_templates"],
    outcome_metrics=["applications_sent", "interview_rate", "resume_iteration_count", "mock_interview_score"],
)

PROJECT_DELIVERY_PACK = DomainPack(
    domain_pack_id="project_delivery_pack_v1",
    domain="project_delivery",
    supported_goal_modes=["mvp_sprint", "thesis_delivery", "feature_ship"],
    node_schema=[
        NodeSchemaEntry("artifact", required=True),
        NodeSchemaEntry("milestone", required=True),
        NodeSchemaEntry("risk", required=True),
        NodeSchemaEntry("constraint", required=False),
        NodeSchemaEntry("relationship", required=False),
    ],
    task_templates=[
        {"task_type": "outline", "focus": "clarify_scope"},
        {"task_type": "draft", "focus": "produce_working_version"},
        {"task_type": "review", "focus": "tighten_quality"},
        {"task_type": "submit", "focus": "final_delivery_check"},
    ],
    feedback_taxonomy=[
        FeedbackTaxonomyEntry("scope_creep", "范围不断膨胀", triggers_aurora=True, strategy_effect="freeze_scope"),
        FeedbackTaxonomyEntry("stuck_on_detail", "卡在细节", strategy_effect="move_to_next_and_return"),
        FeedbackTaxonomyEntry("quality_issue", "质量不达标", strategy_effect="add_review_pass"),
    ],
    risk_patterns=[
        RiskPatternEntry("scope_bloat", "范围膨胀", "task_count_growth_rate > 2x", "freeze_scope_and_prioritize", "high"),
        RiskPatternEntry("deadline_miss", "截止日期风险", "remaining_tasks > available_days * 2", "cut_scope_to_mvp", "high"),
        RiskPatternEntry("perfectionism", "过度打磨", "revision_count > 5 on single artifact", "ship_and_iterate", "medium"),
    ],
    checkpoint_rules=[
        CheckpointRule("midpoint", trigger_after_tasks=3, checks=["scope_frozen", "at_least_one_artifact"]),
        CheckpointRule("pre_delivery", trigger_after_tasks=999, checks=["all_artifacts_done", "no_critical_risk"], user_visible=True),
    ],
    aurora_trigger_rules=[
        AuroraTriggerRule("scope_crisis", "scope_creep_count >= 3", quota_override="sprint", wake_reason_template="项目范围失控，需要校准"),
    ],
    skill_library=[
        SkillTemplate("mvp_first", "先做最小可用版", ["scope_creep", "perfectionism"], "交付MVP后再迭代"),
        SkillTemplate("timebox", "时间盒工作法", ["stuck_on_detail"], "每个任务限时完成"),
    ],
    source_types=["project_requirements", "design_docs", "reference_implementations", "feedback_notes"],
    outcome_metrics=["artifacts_completed", "scope_deviation", "deadline_adherence", "stakeholder_satisfaction"],
)

FITNESS_PACK = DomainPack(
    domain_pack_id="fitness_pack_v1",
    domain="fitness",
    supported_goal_modes=["fitness_routine", "habit_formation", "milestone_training"],
    node_schema=[
        NodeSchemaEntry("habit", required=True),
        NodeSchemaEntry("metric", required=True),
        NodeSchemaEntry("milestone", required=False),
        NodeSchemaEntry("risk", required=False),
    ],
    task_templates=[
        {"task_type": "workout", "focus": "complete_session"},
        {"task_type": "track", "focus": "log_metrics"},
        {"task_type": "review", "focus": "weekly_progress"},
    ],
    feedback_taxonomy=[
        FeedbackTaxonomyEntry("plateau", "指标停滞", triggers_aurora=True, strategy_effect="vary_routine"),
        FeedbackTaxonomyEntry("injury", "受伤", strategy_effect="rest_and_recover"),
        FeedbackTaxonomyEntry("skip_streak", "连续跳过", strategy_effect="reduce_milestone_ambition"),
    ],
    risk_patterns=[
        RiskPatternEntry("burnout", "过度训练", "intensity_spike > 50% OR skip_count >= 4", "reduce_load", "high"),
        RiskPatternEntry("plateau", "平台期", "metric_flat_for >= 14_days", "cross_training_variation", "medium"),
    ],
    checkpoint_rules=[
        CheckpointRule("week_1", trigger_after_tasks=5, checks=["habit_adherence >= 0.7", "no_injury"]),
        CheckpointRule("milestone_check", trigger_after_tasks=20, checks=["metric_improvement > 0"], user_visible=True),
    ],
    aurora_trigger_rules=[
        AuroraTriggerRule("long_plateau", "metric_flat_for >= 21_days", quota_override="sprint"),
        AuroraTriggerRule("injury_risk", "skip_count >= 4 AND intensity_spike > 30%", quota_override="sprint"),
    ],
    skill_library=[
        SkillTemplate("progressive_overload", "渐进式增加负荷", ["plateau"], "连续2周指标提升"),
        SkillTemplate("habit_stacking", "习惯叠加法", ["skip_streak"], "连续21天不间断"),
    ],
    source_types=["workout_plans", "nutrition_guides", "recovery_protocols", "progress_logs"],
    outcome_metrics=["adherence_rate", "metric_improvement", "rest_days_adhered", "injury_free_days"],
)

RESEARCH_PACK = DomainPack(
    domain_pack_id="research_pack_v1",
    domain="research",
    supported_goal_modes=["literature_review", "experiment_design", "paper_writing", "defense_prep"],
    node_schema=[
        NodeSchemaEntry("hypothesis", required=True),
        NodeSchemaEntry("experiment", required=True),
        NodeSchemaEntry("dataset", required=False),
        NodeSchemaEntry("finding", required=True),
        NodeSchemaEntry("risk", required=False),
    ],
    task_templates=[
        {"task_type": "read", "focus": "literature_synthesis"},
        {"task_type": "design", "focus": "experiment_protocol"},
        {"task_type": "execute", "focus": "run_experiment"},
        {"task_type": "write", "focus": "draft_section"},
        {"task_type": "review", "focus": "peer_feedback"},
    ],
    feedback_taxonomy=[
        FeedbackTaxonomyEntry("null_result", "实验无显著结果", triggers_aurora=True, strategy_effect="refine_hypothesis"),
        FeedbackTaxonomyEntry("methodology_flaw", "方法有问题", strategy_effect="redesign_protocol"),
        FeedbackTaxonomyEntry("literature_gap", "文献遗漏", strategy_effect="expand_search_scope"),
    ],
    risk_patterns=[
        RiskPatternEntry("scope_creep", "研究范围膨胀", "hypothesis_count_growth > 3x", "freeze_scope", "high"),
        RiskPatternEntry("reading_loop", "只读不做", "read_count >> experiment_count", "force_experiment_step", "high"),
        RiskPatternEntry("writer_block", "写作停滞", "days_since_last_draft > 7", "outline_first_approach", "medium"),
    ],
    checkpoint_rules=[
        CheckpointRule("hypothesis_formed", trigger_after_tasks=10, checks=["hypothesis_written", "literature_synthesized"]),
        CheckpointRule("first_result", trigger_after_tasks=25, checks=["at_least_one_result", "methodology_documented"], user_visible=True),
    ],
    aurora_trigger_rules=[
        AuroraTriggerRule("prolonged_null", "null_result_count >= 3", quota_override="sprint"),
        AuroraTriggerRule("deadline_pressure", "days_until_submission <= 14 AND draft_progress < 0.5", quota_override="crisis"),
    ],
    skill_library=[
        SkillTemplate("systematic_review", "系统性文献阅读法", ["literature_gap"], "阅读量覆盖目标领域"),
        SkillTemplate("incremental_writing", "增量写作法", ["writer_block"], "每日产出至少200词"),
    ],
    source_types=["papers", "datasets", "experiment_logs", "reviewer_feedback", "methodology_guides"],
    outcome_metrics=["papers_read", "experiments_completed", "words_written", "findings_validated"],
)


# ── DomainPack Registry ──────────────────────────────────────────────

_PACK_REGISTRY: dict[str, DomainPack] = {
    "exam_sprint": EXAM_SPRINT_PACK,
    "exam_rescue": EXAM_SPRINT_PACK,
    "exam_build": EXAM_SPRINT_PACK,
    "job_search_interview": JOB_SEARCH_INTERVIEW_PACK,
    "interview_sprint": JOB_SEARCH_INTERVIEW_PACK,
    "resume_refinement": JOB_SEARCH_INTERVIEW_PACK,
    "portfolio_building": JOB_SEARCH_INTERVIEW_PACK,
    "project_delivery": PROJECT_DELIVERY_PACK,
    "mvp_sprint": PROJECT_DELIVERY_PACK,
    "thesis_delivery": PROJECT_DELIVERY_PACK,
    "feature_ship": PROJECT_DELIVERY_PACK,
    "fitness": FITNESS_PACK,
    "fitness_routine": FITNESS_PACK,
    "habit_formation": FITNESS_PACK,
    "milestone_training": FITNESS_PACK,
    "research": RESEARCH_PACK,
    "literature_review": RESEARCH_PACK,
    "experiment_design": RESEARCH_PACK,
    "paper_writing": RESEARCH_PACK,
    "defense_prep": RESEARCH_PACK,
}


def get_domain_pack(goal_type: str) -> DomainPack:
    """Look up the DomainPack for a goal type. Falls back to exam_sprint."""
    return _PACK_REGISTRY.get(goal_type, EXAM_SPRINT_PACK)


def list_domain_packs() -> list[DomainPack]:
    """Return unique DomainPacks."""
    seen_ids: set[str] = set()
    packs: list[DomainPack] = []
    for pack in _PACK_REGISTRY.values():
        if pack.domain_pack_id not in seen_ids:
            seen_ids.add(pack.domain_pack_id)
            packs.append(pack)
    return packs


def get_node_schema_for_goal(goal_type: str) -> list[str]:
    """Get required node types for a goal type."""
    pack = get_domain_pack(goal_type)
    return [entry.node_type for entry in pack.node_schema if entry.required]
