from __future__ import annotations

import time
from datetime import datetime
from uuid import uuid4

from app.aurora.engine import AuroraDecisionContext, AuroraEngine
from app.aurora.schemas import SignalSnapshot

from .stage4_eval_support import run_corpus_v1_with_runner


def _snapshot() -> SignalSnapshot:
    return SignalSnapshot(
        snapshot_hash="ss_perf_baseline",
        user_id=uuid4(),
        collected_at=datetime(2026, 4, 19, 12, 0, 0),
        scenario_pack_id="exam_prep_14d@v1.0",
        policy_version="aurora_policy@v1.0",
        core_signals={"user_message": "帮我把今天的复习拆成三个最小动作。"},
        enhanced_signals={"task_completion_7d": 0.75},
        optional_signals={},
        total_tokens=900,
        budget_limit=4000,
    )


def test_deterministic_aurora_baseline_remains_within_coarse_runtime_ceiling() -> None:
    """Coarse regression canary, not a micro-benchmark.

    This test intentionally uses a generous ceiling so it stays stable across
    local machines and CI noise while still catching accidental performance
    blowups in the deterministic `safe_route()` path.
    """

    engine = AuroraEngine()
    policy = engine.load_policy("v1.0")
    snapshot = _snapshot()

    iterations = 500
    start = time.perf_counter()
    decisions = [
        engine.safe_route(
            AuroraDecisionContext(
                snapshot=snapshot,
                trigger_point="pre-node-routing",
                current_node="day3_schedule_lock",
                candidate_node="day4_deep_analysis",
                policy_version=policy,
                mode="shadow",
            )
        )
        for _ in range(iterations)
    ]
    elapsed = time.perf_counter() - start

    assert all(decision.policy_version == "aurora_policy@v1.0" for decision in decisions)
    assert elapsed < 3.0, f"deterministic safe_route baseline regressed: {elapsed:.4f}s for {iterations} iterations"


def test_stage4_corpus_v1_inline_runner_remains_within_coarse_runtime_ceiling() -> None:
    """Hook Stage 4 Corpus V1 content into the current inline benchmark runner."""

    engine = AuroraEngine()
    policy = engine.load_policy("v1.0")

    def _runner(case):
        start = time.perf_counter()
        decision = engine.safe_route(
            AuroraDecisionContext(
                snapshot=case.snapshot,
                trigger_point=case.trigger_point,
                current_node=case.current_node,
                candidate_node=case.candidate_node,
                policy_version=policy,
                mode="shadow",
            )
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return {
            "case_id": case.case_id,
            "tier": "inline",
            "trigger_point": case.trigger_point,
            "routing_target": case.routing_target,
            "status": case.expected_status,
            "latency_ms": elapsed_ms,
            "decision_type": decision.decision_type,
            "metadata": {"policy_version": decision.policy_version},
        }

    iterations = 25  # 25 * 20 cases = 500 inline invocations, matching the coarse baseline volume above.
    start = time.perf_counter()
    events = [event for _ in range(iterations) for event in run_corpus_v1_with_runner(_runner)]
    elapsed = time.perf_counter() - start

    assert len(events) == iterations * 20
    assert all(event.tier == "inline" for event in events)
    assert all(event.metadata["policy_version"] == "aurora_policy@v1.0" for event in events)
    assert elapsed < 3.0, f"stage4 corpus v1 inline baseline regressed: {elapsed:.4f}s for {len(events)} events"
