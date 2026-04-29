import time
from functools import wraps
from typing import Any

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


def get_or_create_metric(metric_type, name, documentation, labelnames=(), **kwargs):
    """Safely get or create a prometheus metric."""
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_type(name, documentation, labelnames, **kwargs)


def snapshot_metric(metric: Any) -> dict[str, float]:
    """Return a best-effort snapshot of a Prometheus metric's current values."""
    def _read_value(collector: Any) -> float:
        value_ref = getattr(getattr(collector, "_value", None), "get", None)
        if callable(value_ref):
            return float(value_ref())
        sum_ref = getattr(getattr(collector, "_sum", None), "get", None)
        if callable(sum_ref):
            return float(sum_ref())
        return 0.0

    labelled = getattr(metric, "_metrics", None)
    if isinstance(labelled, dict) and labelled:
        payload: dict[str, float] = {}
        label_names = list(getattr(metric, "_labelnames", ()) or ())
        for labels, child in labelled.items():
            if isinstance(labels, dict):
                label_pairs = sorted(labels.items())
                label_key = ",".join(f"{key}={value}" for key, value in label_pairs) or "default"
            elif isinstance(labels, tuple) and label_names and len(labels) == len(label_names):
                label_key = ",".join(f"{key}={value}" for key, value in zip(label_names, labels, strict=False)) or "default"
            else:
                label_key = str(labels) or "default"
            payload[label_key] = _read_value(child)
        return payload
    return {"default": _read_value(metric)}

# ========== Routing Metrics ==========
ROUTING_DECISIONS = get_or_create_metric(
    Counter,
    'sparkle_routing_decisions_total',
    'Total routing decisions by method',
    ['source', 'target', 'method']
)

ROUTING_SUCCESS = get_or_create_metric(
    Counter,
    'sparkle_routing_success_total',
    'Successful routing executions',
    ['source', 'target']
)

ROUTING_FAILURE = get_or_create_metric(
    Counter,
    'sparkle_routing_failure_total',
    'Failed routing executions',
    ['source', 'target', 'reason']
)

ROUTING_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_routing_latency_seconds',
    'Routing decision latency',
    ['method']
)

ROUTING_CONFIDENCE = get_or_create_metric(
    Histogram,
    'sparkle_routing_confidence',
    'Routing confidence distribution',
    ['method']
)

# ========== Learning Metrics ==========
LEARNING_UPDATES = get_or_create_metric(
    Counter,
    'sparkle_learning_updates_total',
    'Bayesian learning updates',
    ['source', 'target', 'outcome']
)

PROBABILITY_DISTRIBUTION = get_or_create_metric(
    Gauge,
    'sparkle_route_probability',
    'Current probability of route',
    ['source', 'target']
)

LEARNER_STATE_SIZE = get_or_create_metric(
    Gauge,
    'sparkle_learner_state_size',
    'Number of routes in learner',
    ['user_id']
)

# ========== Collaboration Metrics ==========
COLLABORATION_SUCCESS = get_or_create_metric(
    Counter,
    'sparkle_collaboration_success_total',
    'Successful multi-agent collaborations',
    ['workflow_type', 'agents_used', 'outcome']
)

COLLABORATION_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_collaboration_latency_seconds',
    'Full collaboration workflow latency',
    ['workflow_type']
)

# ========== HITL Metrics ==========
HITL_REQUESTED = get_or_create_metric(
    Counter,
    'sparkle_hitl_requested_total',
    'HITL approvals requested',
    ['reason']
)

HITL_APPROVED = get_or_create_metric(
    Counter,
    'sparkle_hitl_approved_total',
    'HITL approvals approved',
    ['reason']
)

HITL_REJECTED = get_or_create_metric(
    Counter,
    'sparkle_hitl_rejected_total',
    'HITL approvals rejected',
    ['reason']
)

# ========== Task Loop Metrics ==========
TASK_LOOP_COMPLETED = get_or_create_metric(
    Counter,
    'sparkle_task_loop_completed_total',
    'Completed task execution loops',
    ['source']
)

COMPENSATION_TRIGGERED = get_or_create_metric(
    Counter,
    'sparkle_compensation_triggered_total',
    'Compensation triggers',
    ['reason']
)

AGENT_INTERACTION_COUNT = get_or_create_metric(
    Counter,
    'sparkle_agent_interactions_total',
    'Number of agent-to-agent interactions',
    ['from_agent', 'to_agent', 'type']
)

# ========== System Health Metrics ==========
ACTIVE_LEARNERS = get_or_create_metric(
    Gauge,
    'sparkle_active_learners_total',
    'Number of active Bayesian learners'
)

ACTIVE_SESSIONS = get_or_create_metric(
    Gauge,
    'sparkle_active_sessions_total',
    'Number of active chat sessions'
)

CACHE_EFFECTIVENESS = get_or_create_metric(
    Counter,
    'sparkle_cache_effectiveness',
    'Cache hit/miss for routing',
    ['cache_type', 'result']
)

GRAPH_COMPLEXITY = get_or_create_metric(
    Gauge,
    'sparkle_graph_complexity',
    'Graph complexity (nodes + edges)',
    ['graph_name']
)

STATE_SIZE = get_or_create_metric(
    Gauge,
    'sparkle_state_size_bytes',
    'Size of the workflow state in bytes',
    ['session_id']
)

# ========== Event Pipeline Metrics ==========
EVENT_INGEST_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_event_ingest_total',
    'Event ingestion outcomes',
    ['status']
)

EVENT_INGEST_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_event_ingest_latency_seconds',
    'Event ingestion latency',
    ['source']
)

EVENT_DEDUPE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_event_dedupe_total',
    'Event dedupe hits',
    ['source']
)

# ========== Memory Metrics ==========
MEMORY_WRITE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_write_total',
    'Memory write outcomes',
    ['type', 'status']
)

EVIDENCE_MISSING_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_evidence_missing_total',
    'Evidence missing count',
    ['type']
)

MEMORY_JOB_RUNS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_job_runs_total',
    'Memory job run outcomes',
    ['job', 'status']
)

EVIDENCE_MISSING_CURRENT = get_or_create_metric(
    Gauge,
    'sparkle_evidence_missing_current',
    'Current evidence missing counts',
    ['type']
)

REPAIR_SUCCESS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_evidence_repair_success_total',
    'Evidence repair success count',
)

MEMORY_RETRACTION_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_retraction_total',
    'Memory retraction count',
    ['type']
)

MEMORY_CORRECTION_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_correction_total',
    'Memory correction count',
    ['type', 'action']
)

MEMORY_SETTINGS_UPDATE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_settings_update_total',
    'Memory settings update count',
)

MEMORY_INFERRED_EXTRACT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_inferred_extract_total',
    'Inferred episodic extraction outcomes',
    ['mode', 'status']
)

MEMORY_INFERRED_WRITE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_inferred_write_total',
    'Inferred episodic write outcomes',
    ['status']
)

MEMORY_INFERRED_REVOKE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_memory_inferred_revoke_total',
    'Inferred episodic revoke outcomes',
    ['scope']
)

# ========== Phase C Outcome Metrics ==========
OUTCOME_RECORDS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_outcome_records_total',
    'Outcome records persisted by evidence level and layer',
    ['evidence_level', 'layer', 'source_family']
)

VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_validated_outcome_learning_promotions_total',
    'Validated outcome learning promotions by layer and direction',
    ['layer', 'direction']
)

OUTCOME_LEARNING_CONFLICTS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_outcome_learning_conflicts_total',
    'Outcome learning conflicts and demotions by layer and reason',
    ['layer', 'reason']
)

PROFILE_LEDGER_PENDING_SYNTHESIS = get_or_create_metric(
    Gauge,
    'sparkle_profile_ledger_pending_synthesis',
    'Current number of profile-ledger records waiting for synthesis'
)

OUTCOME_LEARNING_PLANNING_CONSTRAINTS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_outcome_learning_planning_constraints_total',
    'Planning constraints emitted from outcome learning',
    ['constraint_key', 'constraint_value']
)

HUMAN_EVAL_REPEATED_FAILURE_TAGS_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_human_eval_repeated_failure_tags_total',
    'Repeated human-eval failure tags observed in operations reports',
    ['tag']
)

# ========== Context Pack Metrics ==========
CONTEXT_PACK_BUILD = get_or_create_metric(
    Counter,
    'sparkle_context_pack_build_total',
    'Context pack build count',
    ['intent']
)

CONTEXT_PACK_OVER_BUDGET = get_or_create_metric(
    Counter,
    'sparkle_context_pack_over_budget_total',
    'Context pack over budget count',
    ['intent', 'section']
)

CONTEXT_BUDGET_UTILIZATION = get_or_create_metric(
    Gauge,
    'sparkle_context_budget_utilization',
    'Context budget utilization ratio by source type',
    ['type']
)

CONTEXT_BUDGET_OVER_LIMIT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_context_budget_over_limit_total',
    'Context budget over-limit events by source type',
    ['type']
)

CONTEXT_PACK_INTENT = get_or_create_metric(
    Counter,
    'sparkle_context_pack_intent_total',
    'Context pack intent distribution',
    ['intent']
)

CONTEXT_FOCUS_DECISION_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_context_focus_decision_total',
    'Context focus decisions by focus mode and route intent',
    ['focus_mode', 'route_intent']
)

CONTEXT_SEMANTIC_GATING_APPLIED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_context_semantic_gating_applied_total',
    'Semantic gating applied by section',
    ['section']
)

CONTEXT_SEMANTIC_GATING_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_context_semantic_gating_fallback_total',
    'Semantic gating fallbacks by reason',
    ['reason']
)

CONTEXT_BRIEFING_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_context_briefing_generated_total',
    'Generated context briefing notes by focus mode',
    ['focus_mode']
)

CONTEXT_FOCUS_PROMPT_SECTION_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_context_focus_prompt_section_total',
    'Prompt section usage under context focus',
    ['focus_mode', 'section', 'detail_level']
)

UX_PRESENTATION_STYLE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ux_presentation_style_total',
    'Adaptive presentation style decisions',
    ['style_variant', 'tone_variant', 'chat_mode']
)

UX_STAGE_DETECTED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ux_stage_detected_total',
    'Detected UX conversation stages',
    ['stage', 'chat_mode']
)

UX_NEXT_ACTION_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ux_next_action_generated_total',
    'Generated UX next actions',
    ['stage', 'action_type']
)

UX_NEXT_ACTION_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ux_next_action_fallback_total',
    'Fallbacks while generating UX next actions',
    ['reason']
)

UX_BLOCKED_TEMPERATURE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ux_blocked_temperature_total',
    'Blocked presentation temperatures',
    ['failure_kind', 'temperature']
)

UX_BLOCKED_HISTORY_HIT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ux_blocked_history_hit_total',
    'Blocked presentation history hits',
    ['failure_kind']
)

PERCEPTIBLE_INSIGHT_CANDIDATE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_perceptible_insight_candidate_total',
    'Perceptible insight candidates by scenario',
    ['scenario']
)

PERCEPTIBLE_INSIGHT_SENT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_perceptible_insight_sent_total',
    'Sent perceptible insights by pattern type',
    ['pattern_type']
)

PERCEPTIBLE_INSIGHT_SKIPPED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_perceptible_insight_skipped_total',
    'Skipped perceptible insights by reason',
    ['reason']
)

PLAN_REASONING_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_plan_reasoning_generated_total',
    'Generated plan reasoning summaries by decision',
    ['decision']
)

WEEKLY_LEARNING_REPORT_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_weekly_learning_report_generated_total',
    'Generated weekly learning reports',
    []
)

WEEKLY_LEARNING_REPORT_SKIPPED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_weekly_learning_report_skipped_total',
    'Skipped weekly learning reports by reason',
    ['reason']
)

PROGRESS_COMPARISON_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_progress_comparison_generated_total',
    'Generated progress comparisons by source',
    ['source']
)

PROGRESS_COMPARISON_SKIPPED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_progress_comparison_skipped_total',
    'Skipped progress comparisons by reason',
    ['reason']
)

EVIDENCE_BACKED_VISIBLE_UPDATE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_evidence_backed_visible_update_total',
    'Visible user updates with evidence payloads',
    ['kind']
)

PLAN_REASONING_SOURCE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_plan_reasoning_source_total',
    'Generated plan reasoning summaries by source',
    ['source']
)

PHASE4_OPERATION_DURATION_SECONDS = get_or_create_metric(
    Histogram,
    'sparkle_phase4_operation_duration_seconds',
    'Latency for critical phase 4 operations',
    ['operation']
)

ADAPTIVE_ROLLBACK_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_adaptive_rollback_total',
    'Adaptive strategy rollbacks after repeated negative feedback',
    []
)

ADAPTIVE_ADJUSTMENT_SKIPPED_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_adaptive_adjustment_skipped_total',
    'Adaptive adjustments skipped before apply',
    ['reason']
)

# ========== LTM Eval Metrics ==========
LTM_EVAL_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ltm_eval_total',
    'LTM evaluation runs',
    ['status']
)

LTM_EVAL_CASE_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_ltm_eval_case_total',
    'LTM evaluation cases',
    ['case_id', 'status']
)

LTM_EVAL_AVG_SCORE = get_or_create_metric(
    Gauge,
    'sparkle_ltm_eval_avg_score',
    'Average LTM evaluation score',
    []
)

EVENT_STREAM_LAG = get_or_create_metric(
    Gauge,
    'sparkle_event_stream_lag_seconds',
    'Stream processing lag in seconds',
    ['stream']
)

STATE_ESTIMATOR_RUNS = get_or_create_metric(
    Counter,
    'sparkle_state_estimator_runs_total',
    'State estimator runs',
    ['result']
)

STATE_ESTIMATOR_LATENCY = get_or_create_metric(
    Histogram,
    'sparkle_state_estimator_latency_seconds',
    'State estimator latency',
    []
)

# ========== Spine Outcome Metrics ==========
SPINE_OUTCOME_ATTRIBUTION_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_spine_outcome_attribution_total',
    'Spine outcome attributions by type',
    ['directive_type', 'attribution']
)

SPINE_OUTCOME_LEARNING_GUARD_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_spine_outcome_learning_guard_total',
    'Learning guard verdicts',
    ['action']
)

SPINE_DIRECTIVE_AUDIT_TOTAL = get_or_create_metric(
    Counter,
    'sparkle_spine_directive_audit_total',
    'Directive audit outcomes',
    ['directive_type', 'compliant']
)

# ========== Decorators and Tools ==========
def track_routing_decision(method: str):
    """Routing decision tracking decorator"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            # Try to extract source/target from args or kwargs if possible
            # This is a best-effort extraction depending on signature
            source = kwargs.get('current', 'unknown')

            try:
                result = await func(*args, **kwargs)
                latency = time.time() - start_time

                target = result if isinstance(result, str) else 'unknown'

                # Confidence tracking if available in kwargs
                confidence = kwargs.get('confidence', 0.5)

                if result:
                    ROUTING_SUCCESS.labels(source=source, target=target).inc()
                    ROUTING_CONFIDENCE.labels(method=method).observe(confidence)

                ROUTING_LATENCY.labels(method=method).observe(latency)
                ROUTING_DECISIONS.labels(source=source, target=target, method=method).inc()

                return result

            except Exception as e:
                ROUTING_FAILURE.labels(source=source, target='error', reason=str(e)).inc()
                raise

        return wrapper
    return decorator

def track_collaboration(workflow_type: str, agents: list[str]):
    """Collaboration process tracking"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                latency = time.time() - start_time

                agents_used = ",".join(sorted(agents))
                outcome = "success" if result else "failure"

                COLLABORATION_SUCCESS.labels(
                    workflow_type=workflow_type,
                    agents_used=agents_used,
                    outcome=outcome
                ).inc()

                COLLABORATION_LATENCY.labels(workflow_type=workflow_type).observe(latency)

                return result

            except Exception:
                COLLABORATION_SUCCESS.labels(
                    workflow_type=workflow_type,
                    agents_used=",".join(sorted(agents)),
                    outcome="error"
                ).inc()
                raise

        return wrapper
    return decorator

# ========== Metrics Collector ==========
class BusinessMetricsCollector:
    """Business metrics collector"""

    def __init__(self):
        self._cache = {}

    def update_route_probability(self, source: str, target: str, probability: float):
        """Update route probability"""
        PROBABILITY_DISTRIBUTION.labels(source=source, target=target).set(probability)

    def update_learner_state_size(self, user_id: str, size: int):
        """Update learner state size"""
        LEARNER_STATE_SIZE.labels(user_id=user_id).set(size)

    def record_cache_hit(self, cache_type: str, hit: bool):
        """Record cache hit"""
        result = "hit" if hit else "miss"
        CACHE_EFFECTIVENESS.labels(cache_type=cache_type, result=result).inc()

    def update_graph_complexity(self, graph_name: str, nodes: int, edges: int):
        """Update graph complexity"""
        GRAPH_COMPLEXITY.labels(graph_name=graph_name).set(nodes + edges)

    def record_agent_interaction(self, from_agent: str, to_agent: str, interaction_type: str):
        """Record agent interaction"""
        AGENT_INTERACTION_COUNT.labels(
            from_agent=from_agent,
            to_agent=to_agent,
            type=interaction_type
        ).inc()

    def update_state_size(self, session_id: str, state: Any):
        """Update state size"""
        import sys
        # Rough estimation
        size = sys.getsizeof(state.messages) + sys.getsizeof(state.context_data)
        STATE_SIZE.labels(session_id=session_id).set(size)

# Global Instance
metrics_collector = BusinessMetricsCollector()
