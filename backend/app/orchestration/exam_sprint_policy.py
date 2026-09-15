from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PRODUCT_MODELING_ALLOWED = (
    "dynamic_state",
    "srl_phase",
    "metacognitive_delta",
    "task_self_efficacy",
    "behavior_pattern",
    "context_constraint",
    "explicit_social_role",
)

PRODUCT_MODELING_FORBIDDEN = (
    "clinical_diagnosis",
    "personality_pathology",
    "unconscious_interpretation",
    "inferred_social_identity",
    "trauma_attribution",
)

SOCIAL_ROLE_MODEL_POLICY = "explicit_or_user_confirmed_only"
STABLE_TRAITS_POLICY = "weak_prior_low_confidence_not_user_visible"


@dataclass(frozen=True)
class ExamSprintPolicyInput:
    total_days: int
    subject: str
    exam_scope: str = ""
    knowledge_baseline: str = ""
    time_available: str = ""
    daily_available_hours: int = 2
    materials: tuple[str, ...] = ()
    cold_start_context: dict[str, Any] = field(default_factory=dict)
    existing_signals: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExamSprintPolicy:
    sprint_mode: str
    triage_level: str
    retrieval_policy: dict[str, Any]
    task_density_hint: float
    sleep_guard_hint: str
    strategy_notes: list[str]
    user_modeling_boundary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def is_seven_day_survival(self) -> bool:
        return self.sprint_mode == "seven_day_survival"

    @property
    def is_fourteen_day_mode(self) -> bool:
        return self.sprint_mode == "fourteen_day_build_and_retrieve"


class ExamSprintPolicyEngine:
    """Translate sprint constraints into a compact strategy policy.

    V1 intentionally stays deterministic: this layer is a product policy guardrail,
    not another model trying to infer private psychology.
    """

    @classmethod
    def build(cls, payload: ExamSprintPolicyInput) -> ExamSprintPolicy:
        days = max(1, int(payload.total_days or 1))
        hours = max(1, int(payload.daily_available_hours or 1))
        boundary = {
            "allowed": list(PRODUCT_MODELING_ALLOWED),
            "forbidden": list(PRODUCT_MODELING_FORBIDDEN),
            "social_role_model": SOCIAL_ROLE_MODEL_POLICY,
            "stable_traits": STABLE_TRAITS_POLICY,
        }

        if days <= 1:
            density = 0.45 if hours <= 2 else 0.55
            return ExamSprintPolicy(
                sprint_mode="last_24h_cram",
                triage_level="emergency",
                retrieval_policy={
                    "daily_retrieval_required": True,
                    "default_task_shape": "high_yield_review_error_book_short_mock",
                    "spaced_retrieval": "same_day_compact_refresh",
                    "allow_deep_learn": False,
                    "deep_learn_budget": "none",
                    "output_gate": "every_block_requires_visible_output",
                    "success_gate": "no_new_topics_visible_output_required",
                    "density_mode": "final_day_compact",
                    "max_primary_targets_per_day": 3,
                    "minimum_output": "高频速览、错题回看或 30 分钟短模拟",
                    "new_topic_allowed": False,
                },
                task_density_hint=density,
                sleep_guard_hint="最后一天以稳定输出为先，停止新章节，避免熬夜。",
                strategy_notes=[
                    "今天不再开新坑，只做高频高收益节点速览、错题回看和短模拟。",
                    "低 ROI、新章节、长耗时题全部暂停，先保住最容易拿到的分数。",
                    "任何复习块都必须留下可见输出，例如闭卷页、错因清单或短模拟结果。",
                ],
                user_modeling_boundary=boundary,
            )

        if days <= 7:
            density = 0.55 if hours <= 2 else 0.65
            return ExamSprintPolicy(
                sprint_mode="seven_day_survival",
                triage_level="emergency" if days <= 4 else "high",
                retrieval_policy={
                    "daily_retrieval_required": True,
                    "default_task_shape": "closed_book_recall_then_targeted_drill",
                    "spaced_retrieval": "compressed_same_day",
                    "allow_deep_learn": False,
                    "deep_learn_budget": "none",
                    "output_gate": "every_day_requires_visible_output",
                    "success_gate": "every_day_requires_checkable_success_criterion",
                    "density_mode": "reduced_for_survival",
                    "max_primary_targets_per_day": 1 if hours <= 2 else 2,
                    "diagnostic_priority": "past_papers_scope_and_high_frequency_items_first",
                    "fallback_task_shape": "single_gap_scaffold_or_time_boxed_recovery",
                    "defer_or_skip_rule": "低频、全新、耗时高的内容先标记为 defer_or_skip，优先保住高频基础分。",
                    "minimum_output": "闭卷复述、3题小测或一道典型题独立完成",
                    "fail_safe": {
                        "unclear": "切到单知识点补强 + 1 个最小检查题，不继续加新难点。",
                        "behind": "下一天只保留 1 个核心任务和 1 个输出动作，先稳住保底线。",
                        "no_time": "压缩成 15–25 分钟保底版，只留下闭卷提取和最小检查。",
                        "consecutive_failures": "继续下调难度和任务密度，只修最高收益漏洞，不扩范围。",
                    },
                },
                task_density_hint=density,
                sleep_guard_hint="保留睡眠和低负荷收尾窗口；晚间不追加新难点。",
                strategy_notes=[
                    "先用诊断题和考纲材料确定高频范围，避免从第一页线性复习。",
                    "每天至少安排一次闭卷输出或小测，用结果决定第二天补哪里，不能只停留在阅读完成。",
                    "低 ROI 内容进入 defer_or_skip 池，等保底线稳定后再决定是否回看。",
                    "每天至少留下一个看得见的产出，例如三栏清单、闭卷页、3 题结果或最后 24 小时清单。",
                ],
                user_modeling_boundary=boundary,
            )

        if days <= 14:
            return ExamSprintPolicy(
                sprint_mode="fourteen_day_build_and_retrieve",
                triage_level="balanced",
                retrieval_policy={
                    "daily_retrieval_required": True,
                    "default_task_shape": "learn_recall_space_relearn",
                    "spaced_retrieval": "multi_day_successive_relearning",
                    "allow_deep_learn": True,
                    "deep_learn_budget": "limited_high_weight_topics_only",
                    "review_rounds": 2,
                    "mock_checkpoints": 2 if days >= 10 else 1,
                    "output_gate": "every_day_requires_visible_output",
                    "success_gate": "every_day_requires_checkable_success_criterion",
                    "density_mode": "moderate_with_spacing",
                    "max_primary_targets_per_day": 2,
                    "deep_learn_quota_per_cycle": 1,
                    "minimum_output": "闭卷复述、间隔复测或阶段模拟",
                    "fail_safe": {
                        "unclear": "先回到上一轮旧点复测，再只深挖 1 个高权重难点。",
                        "behind": "砍掉并行任务，改成 1 个主线输出 + 1 个补测动作。",
                        "no_time": "当天改成压缩版复测，不牺牲检索闭环。",
                        "consecutive_failures": "暂停 deep learn，回到 spaced retrieval + scaffold repair。",
                    },
                },
                task_density_hint=0.75,
                sleep_guard_hint="允许两轮复习，但每天保留恢复窗口，避免靠熬夜换覆盖率。",
                strategy_notes=[
                    "第一轮建立结构，第二轮用间隔检索确认是否真的能提取，每天先检索再决定是否继续读。",
                    "高权重且串联性强的内容允许少量 deep learn，低权重内容只做识别和保底。",
                    "阶段模拟用来校准范围和节奏，不把所有时间压到最后两天。",
                    "每天都要留一个可检查产出，例如知识图、复测结果、错因卡或阶段模拟记录。",
                ],
                user_modeling_boundary=boundary,
            )

        return ExamSprintPolicy(
            sprint_mode="standard_exam_sprint",
            triage_level="balanced",
            retrieval_policy={
                "daily_retrieval_required": True,
                "default_task_shape": "learn_recall_review",
                "spaced_retrieval": "weekly_then_daily_near_exam",
                "allow_deep_learn": True,
                "output_gate": "every_day_requires_visible_output",
                "success_gate": "every_day_requires_checkable_success_criterion",
                "density_mode": "steady",
                "minimum_output": "闭卷复述或练习测试",
            },
            task_density_hint=0.7,
            sleep_guard_hint="保持稳定复习节律，临近考试再提高检索密度。",
            strategy_notes=[
                "保持诊断、检索、反馈三件事循环，不用一次性把所有内容排死。",
                "优先处理高分值和高不确定模块，低价值内容延后。",
            ],
            user_modeling_boundary=boundary,
        )
