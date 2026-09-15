from __future__ import annotations

import json

from app.orchestration.utilization_metrics import (
    build_inference_utilization_record,
    build_prompt_utilization_record,
)


def test_build_prompt_utilization_record_uses_frozen_snapshot() -> None:
    record = build_prompt_utilization_record(
        {
            "utilization": {
                "selected_signal_block_count": 5,
                "rendered_signal_block_count": 4,
                "selected_signal_blocks": ["situation_brief", "decision_policy", "plan_context"],
                "rendered_signal_blocks": ["situation_brief", "decision_policy"],
                "selected_high_value_fields": ["recent_errors"],
                "prompt_visible_high_value_fields": ["recent_errors"],
            }
        }
    )

    assert record["status"] == "known"
    assert record["numerator"] == 4
    assert record["denominator"] == 5
    assert record["ratio"] == 0.8
    assert "recent_errors" in record["prompt_visible_high_value_fields"]


def test_build_inference_utilization_record_tracks_traceable_signal_families() -> None:
    user_context_payload = {
        "prompt_signal_telemetry": {
            "prompt_visible_high_value_fields": ["recent_errors", "recent_mastery_changes"],
        }
    }
    context_data = {
        "situation_brief": {
            "summary": "热力学最近反复卡在熵增方向判断，但热机效率有一点回升。",
            "focus_question": "这轮最该先补哪块？",
            "evidence": {
                "freshest_items": [
                    "近期痛点：熵增方向判断",
                    "近期进展：热机效率掌握度回升",
                ],
                "recent_wins": ["热机效率掌握度回升"],
            },
            "decision_context": {
                "what_matters_now": "先补熵增方向判断",
                "planning_blocking_unknowns": ["还不清楚熵增方向判断为何总反"],
            },
            "semantic_control": {
                "rendered_doctrine_summary": {
                    "summary": "先承接卡点，再给一个最小可行动作。",
                }
            },
            "insight_state": {
                "blocking_unknowns": ["还不清楚熵增方向判断为何总反"],
            },
        }
    }
    response_metadata = {
        "situation_brief": json.dumps(context_data["situation_brief"], ensure_ascii=False),
        "residual_decision_context": json.dumps(
            context_data["situation_brief"]["decision_context"],
            ensure_ascii=False,
        ),
        "semantic_control_trace": json.dumps(
            context_data["situation_brief"]["semantic_control"],
            ensure_ascii=False,
        ),
    }

    record = build_inference_utilization_record(
        user_context_payload=user_context_payload,
        context_data=context_data,
        response_metadata=response_metadata,
        full_response="我现在最在意的是你在熵增方向判断这里持续卡住，但热机效率已经有一点回升。先别铺大计划，先把这个判断题型稳住。",
    )

    assert record["status"] == "known"
    assert "situation_brief" in record["eligible_signal_families"]
    assert "decision_context" in record["traceable_signal_families"]
    assert "semantic_control" in record["traceable_signal_families"]
    assert record["ratio"] is not None
