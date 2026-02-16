from __future__ import annotations

from app.services.meta_rule_compiler_service import MetaRuleCompilerService


def test_meta_rule_compiler_builds_channel_patches_and_ordering() -> None:
    rules = [
        {
            "rule_id": "cr_routing",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "medium",
            "channel": "routing",
            "recommended_actions": ["degrade_parallelism"],
            "confidence": 0.81,
            "expected_delta_q": 0.04,
            "motif_graph_id": "motif_1",
            "scope_type": "cohort",
        },
        {
            "rule_id": "cr_prompt",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "medium",
            "channel": "prompt",
            "recommended_actions": ["require_minimal_clarification"],
            "confidence": 0.76,
            "expected_delta_q": 0.03,
            "motif_graph_id": "motif_1",
            "scope_type": "cohort",
        },
    ]
    result = MetaRuleCompilerService.compile(
        rules=rules,
        task_type="study_plan",
        complexity_tier="medium",
        guardrail_inputs={"negative_feedback_rate": 0.2, "fallback_rate": 0.05, "stable_cohort_q_gap": 0.04, "p95_latency_delta": 0.03},
    )
    assert result.rule_block_reason == ""
    assert "routing" in result.patches
    assert "prompt" in result.patches
    assert result.transfer_source in {"cohort", "composed"}
    assert result.meta_rule_ids


def test_meta_rule_compiler_blocks_under_guardrail_breach() -> None:
    rules = [
        {
            "rule_id": "cr_toolchain",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "unknown",
            "channel": "toolchain",
            "recommended_actions": ["timeout_rebudget"],
            "confidence": 0.74,
            "expected_delta_q": 0.02,
            "motif_graph_id": "motif_2",
        }
    ]
    result = MetaRuleCompilerService.compile(
        rules=rules,
        task_type="study_plan",
        complexity_tier="high",
        guardrail_inputs={"negative_feedback_rate": 0.8, "fallback_rate": 0.03, "stable_cohort_q_gap": 0.02, "p95_latency_delta": 0.02},
    )
    assert result.patches == {}
    assert result.rule_block_reason == "guardrail_negative_feedback"
    assert isinstance(result.rule_block_detail, dict)
    assert result.rule_block_detail.get("metric") == "negative_feedback_rate"
    assert result.rule_block_detail.get("source") == "heuristic"


def test_meta_rule_compiler_scope_selection_prefers_matching_scope() -> None:
    rules = [
        {
            "rule_id": "cr_global",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "unknown",
            "channel": "routing",
            "recommended_actions": ["degrade_parallelism"],
            "confidence": 0.7,
            "expected_delta_q": 0.02,
            "motif_graph_id": "motif_scope",
            "scope_type": "global",
            "scope_key": "all",
        },
        {
            "rule_id": "cr_cohort",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "unknown",
            "channel": "routing",
            "recommended_actions": ["tighten_dependency_order"],
            "confidence": 0.8,
            "expected_delta_q": 0.03,
            "motif_graph_id": "motif_scope",
            "scope_type": "cohort",
            "scope_key": "cohort::study::medium::high_engagement::rhythm_steady",
        },
        {
            "rule_id": "cr_personal",
            "status": "active",
            "task_type": "study_plan",
            "complexity_tier": "unknown",
            "channel": "toolchain",
            "recommended_actions": ["timeout_rebudget"],
            "confidence": 0.86,
            "expected_delta_q": 0.04,
            "motif_graph_id": "motif_scope",
            "scope_type": "personal",
            "scope_key": "usr::abc",
        },
    ]
    result = MetaRuleCompilerService.compile(
        rules=rules,
        task_type="study_plan",
        complexity_tier="medium",
        cohort_id="cohort::study::medium::high_engagement::rhythm_steady",
        user_scope="usr::abc",
        allow_personal=False,
        guardrail_inputs={"negative_feedback_rate": 0.2, "fallback_rate": 0.04, "stable_cohort_q_gap": 0.04, "p95_latency_delta": 0.03},
    )
    assert "cr_global" in result.meta_rule_ids
    assert "cr_cohort" in result.meta_rule_ids
    assert "cr_personal" not in result.meta_rule_ids
