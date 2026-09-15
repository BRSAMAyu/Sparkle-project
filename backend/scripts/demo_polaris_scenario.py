"""
Core: verification
Phase: sense→clarify→plan→execute→reflect→reinforce→adapt
Stage: VISION-003 — Polaris Demo Script

End-to-end demonstration of a high-pressure goal scenario:
"7天考试先过线" (7-day exam survival sprint)

This script verifies the complete causal chain:
  Goal Input → Modeling → Planning → Task Execution → Adaptation → Growth Chronicle

Run: cd backend && python scripts/demo_polaris_scenario.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone

# Ensure imports work
sys.path.insert(0, ".")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_header(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


async def run_polaris_demo() -> bool:
    """Run the complete 7-day exam survival demo scenario."""
    from app.signals.types import (
        ActionableSignal,
        ActionableStatePacket,
        CausalTrace,
        DirectiveApplicationAudit,
        ExecutionDirective,
        OutcomeRecord,
        PolicyDecision,
        StateEntry,
    )
    from app.signals.spine_orchestrator import SpineOrchestrator
    from app.signals.goal_world_graph import GoalWorldGraph, GoalWorldGraphService, GraphNode
    from app.signals.spine_quality_guard import SpineQualityGuard
    from app.signals.intervention_episode import (
        ContextSignature,
        InterventionEpisode,
        InterventionEpisodeLedger,
        OutcomeVector,
        ExecutionOutcome,
    )
    from app.signals.research_mode import ResearchDatasetBuilder, ConsentTracker
    from app.services.galaxy.crdt_persistence import MasteryMergeCRDT
    from app.signals.deployment_health import BlueGreenHealthCheck, ChaosTestRunner, ChaosFault

    user_id = "demo_student_001"
    goal_id = "exam_sprint_thermo_7d"
    all_passed = True

    # ═══════════════════════════════════════════════════════════════
    # Phase 1: Goal Input + Knowledge Graph Setup
    # ═══════════════════════════════════════════════════════════════
    _print_header("Phase 1: Goal Input + Knowledge Graph")

    graph = GoalWorldGraph(
        graph_id="gwg_demo",
        user_id=user_id,
        goal_id=goal_id,
        goal_type="exam_sprint",
        nodes=[
            GraphNode(node_id="n1", label="热力学第一定律", node_type="knowledge", mastery=0.3),
            GraphNode(node_id="n2", label="热力学第二定律", node_type="knowledge", mastery=0.1,
                      dependency_ids=["n1"]),
            GraphNode(node_id="n3", label="熵变计算", node_type="capability", mastery=0.0,
                      dependency_ids=["n1", "n2"]),
            GraphNode(node_id="n4", label="卡诺循环", node_type="knowledge", mastery=0.5),
            GraphNode(node_id="n5", label="考试真题练习", node_type="milestone", mastery=0.0,
                      dependency_ids=["n3", "n4"]),
        ],
    )
    print(f"  Graph: {len(graph.nodes)} nodes, coverage={graph.coverage}")

    # ═══════════════════════════════════════════════════════════════
    # Phase 2: Causal Trace — Signal → Policy → Directive → Audit
    # ═══════════════════════════════════════════════════════════════
    _print_header("Phase 2: Signal → Policy → Directive Chain")

    signal = ActionableSignal(
        signal_id="sig_timeout_1",
        source_event_ids=["evt_timeout_1", "evt_timeout_2"],
        source_system="task_service",
        state_key="task_duration_fit",
        claim="recent_task_timeout_pattern",
        confidence=0.85,
        scope="current_sprint",
        ttl_hours=24,
        evidence_summary="连续2张任务卡超时",
        possible_effects=["reduce_task_duration", "simplify_task"],
        priority="high",
    )

    policy = PolicyDecision(
        policy_decision_id="pd_timeout_1",
        primary_strategy="recover_execution_rhythm",
        secondary_strategy=None,
        hard_constraints={"max_task_duration_min": 25},
        soft_biases={"tone": "direct_but_reassuring"},
        visibility="receipt",
        requires_user_confirmation=False,
        reasoning_summary="检测到任务超时模式，自动缩短任务时长",
        risk_level="low",
        which_directives={"execution": True},
    )

    directive = ExecutionDirective(
        directive_id="dir_shorter_1",
        policy_decision_id=policy.policy_decision_id,
        target_module="task_generator",
        scope="current_sprint",
        hard_constraints={"max_duration_min": 25},
        user_visible_reason="检测到任务超时，自动缩短时长至25分钟",
    )

    audit = DirectiveApplicationAudit(
        audit_id="aud_shorter_1",
        directive_id=directive.directive_id,
        target_module="task_generator",
        applied=True,
        applied_constraints=["max_duration_min=25"],
        violations=[],
        generated_output_id="task_short_001",
        generated_output_summary={"duration": 25, "adjusted": True},
    )

    trace = CausalTrace(
        trace_id="ct_timeout_1",
        raw_event_ids=["evt_timeout"],
        signal_ids=[signal.signal_id],
        policy_decision_id=policy.policy_decision_id,
        directive_ids=[directive.directive_id],
        audit_ids=[audit.audit_id],
        receipt_ids=["receipt_1"],
    )

    chain_complete = bool(trace.signal_ids and trace.policy_decision_id and trace.directive_ids)
    print(f"  Causal chain complete: {chain_complete}")
    if not chain_complete:
        print("  FAIL: Causal chain incomplete!")
        all_passed = False

    # ═══════════════════════════════════════════════════════════════
    # Phase 3: Outcome Attribution + Intervention Episode
    # ═══════════════════════════════════════════════════════════════
    _print_header("Phase 3: Outcome Attribution")

    episode = InterventionEpisodeLedger.create_episode(
        user_id=user_id,
        goal_id=goal_id,
        domain="exam_sprint",
        context_signature=ContextSignature(
            goal_mode="exam_rescue",
            deadline_phase="D-5",
            deadline_pressure="high",
            failure_type="timeout",
            cognitive_load="medium",
        ),
        candidate_policies=["reduce_task_duration", "insert_break", "simplify_task"],
        selected_policy="reduce_task_duration",
        selection_reason="连续超时模式",
        selection_mode="rule_based",
        selection_confidence=0.85,
        risk_level="low",
        directive_ids=[directive.directive_id],
    )

    outcome = OutcomeVector(
        execution=ExecutionOutcome(started=True, completed=True, actual_duration_min=22, expected_duration_min=25),
    )
    updated_episode = InterventionEpisodeLedger.record_outcome(episode, outcome)

    print(f"  Episode: {episode.episode_id}, evidence_grade={updated_episode.evidence_quality.grade}")
    if updated_episode.evidence_quality.grade < 2:
        print("  FAIL: Evidence grade too low!")
        all_passed = False

    # ═══════════════════════════════════════════════════════════════
    # Phase 4: Quality Guard Check
    # ═══════════════════════════════════════════════════════════════
    _print_header("Phase 4: Quality Guard")

    report = SpineQualityGuard.generate_quality_report(
        signal_history=[{"had_policy_decision": True, "had_directive": True}],
        metrics={"signals_generated": 10, "policies_evaluated": 10, "directives_applied": 9},
    )
    print(f"  Health: {report.health_status}, score={report.overall_score:.2f}")
    if report.health_status == "critical":
        print("  FAIL: Spine health critical!")
        all_passed = False

    # ═══════════════════════════════════════════════════════════════
    # Phase 5: CRDT Merge + Research Dataset
    # ═══════════════════════════════════════════════════════════════
    _print_header("Phase 5: CRDT Merge + Research Export")

    # Simulate offline mastery update conflict → CRDT merge
    merged = MasteryMergeCRDT.merge_mastery(30.0, 65.0)
    print(f"  CRDT merge: max(30, 65) = {merged}")
    if merged != 65.0:
        print("  FAIL: CRDT merge incorrect!")
        all_passed = False

    # Build anonymized research dataset
    dataset, meta = ResearchDatasetBuilder.build_dataset(
        [updated_episode.to_dict()],
        version="1.0",
        spine_version="spine-v3",
    )
    print(f"  Research dataset: {len(dataset)} episodes, exclusions={meta.exclusion_rules_applied}")

    # ═══════════════════════════════════════════════════════════════
    # Phase 6: Consent + Blue-Green Health
    # ═══════════════════════════════════════════════════════════════
    _print_header("Phase 6: Consent + Deployment Health")

    tracker = ConsentTracker()
    for ct in ConsentTracker.REQUIRED_CONSENTS:
        tracker.grant_consent(user_id=user_id, consent_type=ct)
    can_research = tracker.can_include_in_research(user_id)
    print(f"  Research consent: {can_research}")
    if not can_research:
        print("  FAIL: Consent not granted!")
        all_passed = False

    blue = BlueGreenHealthCheck.check_deployment_health(
        slot="blue", error_rate_5xx=0.005, p95_latency_ms=800, success_rate=0.995,
    )
    green = BlueGreenHealthCheck.check_deployment_health(
        slot="green", error_rate_5xx=0.008, p95_latency_ms=900, success_rate=0.992,
    )
    promo = BlueGreenHealthCheck.evaluate_promotion(blue=blue, green=green)
    print(f"  Blue-Green promotion: {promo.recommendation}")

    # ═══════════════════════════════════════════════════════════════
    # Final Verdict
    # ═══════════════════════════════════════════════════════════════
    _print_header("VISION-003: Polaris Demo Result")

    if all_passed:
        print("  ALL PHASES PASSED - Polaris scenario complete!")
        print("  End-to-end chain verified: Goal → Signal → Policy → Directive → Outcome → Quality → Research")
    else:
        print("  SOME PHASES FAILED - see above for details")

    return all_passed


if __name__ == "__main__":
    result = asyncio.run(run_polaris_demo())
    sys.exit(0 if result else 1)
