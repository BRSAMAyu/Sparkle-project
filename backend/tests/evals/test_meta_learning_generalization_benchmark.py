from __future__ import annotations

from app.services.meta_rule_compiler_service import MetaRuleCompilerService


def test_meta_learning_generalization_benchmark_guardrail() -> None:
    # old-user trained rules (simulated)
    rules = [
        {
            "rule_id": "cr_old_1",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "medium",
            "channel": "routing",
            "recommended_actions": ["degrade_parallelism"],
            "confidence": 0.82,
            "expected_delta_q": 0.05,
            "motif_graph_id": "motif_old_1",
            "scope_type": "global",
        },
        {
            "rule_id": "cr_old_2",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "high",
            "channel": "toolchain",
            "recommended_actions": ["timeout_rebudget"],
            "confidence": 0.78,
            "expected_delta_q": 0.04,
            "motif_graph_id": "motif_old_1",
            "scope_type": "cohort",
        },
    ]

    # new-user validation windows
    result_medium = MetaRuleCompilerService.compile(
        rules=rules,
        task_type="study_plan",
        complexity_tier="medium",
        guardrail_inputs={"negative_feedback_rate": 0.35, "fallback_rate": 0.07, "stable_cohort_q_gap": 0.05, "p95_latency_delta": 0.08},
    )
    result_high = MetaRuleCompilerService.compile(
        rules=rules,
        task_type="study_plan",
        complexity_tier="high",
        guardrail_inputs={"negative_feedback_rate": 0.33, "fallback_rate": 0.08, "stable_cohort_q_gap": 0.06, "p95_latency_delta": 0.08},
    )

    assert result_medium.rule_block_reason == ""
    assert result_high.rule_block_reason == ""
    assert result_medium.meta_rule_ids
    assert result_high.meta_rule_ids
    assert result_medium.transfer_source in {"global", "cohort", "composed"}
