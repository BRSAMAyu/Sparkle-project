from __future__ import annotations

from app.orchestration.exam_sprint_policy import (
    PRODUCT_MODELING_ALLOWED,
    PRODUCT_MODELING_FORBIDDEN,
    SOCIAL_ROLE_MODEL_POLICY,
    STABLE_TRAITS_POLICY,
    ExamSprintPolicyEngine,
    ExamSprintPolicyInput,
)


def test_seven_day_policy_prioritizes_survival_triage_and_retrieval() -> None:
    policy = ExamSprintPolicyEngine.build(
        ExamSprintPolicyInput(
            total_days=7,
            subject="计算机网络",
            exam_scope="传输层、网络层、应用层",
            knowledge_baseline="完全没学过",
            daily_available_hours=2,
            materials=("真题", "课件"),
        )
    )

    assert policy.sprint_mode == "seven_day_survival"
    assert policy.triage_level == "high"
    assert policy.retrieval_policy["daily_retrieval_required"] is True
    assert policy.retrieval_policy["allow_deep_learn"] is False
    assert policy.retrieval_policy["density_mode"] == "reduced_for_survival"
    assert policy.retrieval_policy["max_primary_targets_per_day"] == 1
    assert policy.retrieval_policy["output_gate"] == "every_day_requires_visible_output"
    assert "只保留 1 个核心任务" in policy.retrieval_policy["fail_safe"]["behind"]
    assert "defer_or_skip" in policy.retrieval_policy["defer_or_skip_rule"]
    assert any("低 ROI" in note or "defer_or_skip" in note for note in policy.strategy_notes)
    assert any("每天至少留下一个看得见的产出" in note for note in policy.strategy_notes)


def test_fourteen_day_policy_allows_spaced_retrieval_and_deep_learn() -> None:
    policy = ExamSprintPolicyEngine.build(
        ExamSprintPolicyInput(
            total_days=14,
            subject="操作系统",
            exam_scope="进程、内存、文件系统",
            knowledge_baseline="学过一些",
            daily_available_hours=3,
            materials=("课件",),
        )
    )

    assert policy.sprint_mode == "fourteen_day_build_and_retrieve"
    assert policy.retrieval_policy["spaced_retrieval"] == "multi_day_successive_relearning"
    assert policy.retrieval_policy["allow_deep_learn"] is True
    assert policy.retrieval_policy["review_rounds"] == 2
    assert policy.retrieval_policy["deep_learn_budget"] == "limited_high_weight_topics_only"
    assert policy.retrieval_policy["deep_learn_quota_per_cycle"] == 1
    assert policy.retrieval_policy["density_mode"] == "moderate_with_spacing"
    assert "暂停 deep learn" in policy.retrieval_policy["fail_safe"]["consecutive_failures"]


def test_user_modeling_boundary_is_task_level_and_explicit_only() -> None:
    policy = ExamSprintPolicyEngine.build(ExamSprintPolicyInput(total_days=7, subject="计网"))
    boundary = policy.user_modeling_boundary

    assert "dynamic_state" in PRODUCT_MODELING_ALLOWED
    assert "clinical_diagnosis" in PRODUCT_MODELING_FORBIDDEN
    assert boundary["social_role_model"] == SOCIAL_ROLE_MODEL_POLICY
    assert boundary["stable_traits"] == STABLE_TRAITS_POLICY
    assert "inferred_social_identity" in boundary["forbidden"]
