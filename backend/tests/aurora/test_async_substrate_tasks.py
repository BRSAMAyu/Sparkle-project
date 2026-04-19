from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from app.aurora.context import AuroraDecisionContext, AuroraTier
from app.aurora.tasks import _run_context_from_primitives
from app.aurora.schemas import SignalSnapshot


def _snapshot() -> SignalSnapshot:
    return SignalSnapshot(
        snapshot_hash="ss_async_substrate",
        user_id=uuid4(),
        collected_at=datetime(2026, 4, 19, 12, 0, 0),
        scenario_pack_id="stage4_async_substrate@v1",
        policy_version="aurora_policy@v1.0",
        core_signals={"user_message": "帮我记录这次会话结果，留给后面的 nearline。"},
        enhanced_signals={},
        optional_signals={},
        total_tokens=128,
        budget_limit=4000,
    )


def test_nearline_task_consumes_snapshot_ref_and_prior_outputs_only() -> None:
    context = AuroraDecisionContext(
        snapshot=_snapshot(),
        trigger_point="session_end",
        current_node="day3_schedule_lock",
        candidate_node="day4_deep_analysis",
        mode="shadow",
        prior_outputs={
            "pre_node_routing": {
                "decision_id": "tdr_123",
                "routing_mode": "workflow",
                "snapshot_ref": "ss_inline_123",
            }
        },
    ).with_tier(AuroraTier.NEARLINE)

    execution = _run_context_from_primitives(context)

    assert execution.status.value == "success"
    assert execution.payload == {
        "snapshot_ref": "ss_async_substrate",
        "policy_version": "aurora_policy@v1.0",
        "current_node": "day3_schedule_lock",
        "candidate_node": "day4_deep_analysis",
        "prior_output_keys": ["pre_node_routing"],
        "prior_outputs": {
            "pre_node_routing": {
                "decision_id": "tdr_123",
                "routing_mode": "workflow",
                "snapshot_ref": "ss_inline_123",
            }
        },
    }


def test_nearline_task_misses_cleanly_when_prior_outputs_are_absent() -> None:
    context = AuroraDecisionContext(
        snapshot=_snapshot(),
        trigger_point="session_end",
        current_node="day3_schedule_lock",
        mode="shadow",
        prior_outputs={},
    ).with_tier(AuroraTier.NEARLINE)

    execution = _run_context_from_primitives(context)

    assert execution.status.value == "miss"
    assert execution.reason == "missing_prior_outputs"
