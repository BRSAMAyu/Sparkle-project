import time
from asyncio import iscoroutinefunction
from functools import wraps

from loguru import logger
from opentelemetry import trace
from prometheus_client import REGISTRY, Counter, Gauge, Histogram


def get_or_create_metric(metric_type, name, documentation, labelnames=(), **kwargs):
    """Safely get or create a prometheus metric."""
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_type(name, documentation, labelnames, **kwargs)


# 1. 基础请求指标
REQUEST_COUNT = get_or_create_metric(
    Counter, "sparkle_requests_total", "Total number of requests", ["module", "method", "status"]
)

REQUEST_LATENCY = get_or_create_metric(
    Histogram, "sparkle_request_latency_seconds", "Request latency in seconds", ["module", "method"]
)

# 2. LLM 与 Token 指标
TOKEN_USAGE = get_or_create_metric(
    Counter,
    "sparkle_tokens_total",
    "Total number of tokens used",
    ["model", "type"],  # Removed user_id to prevent cardinality explosion
)

LLM_CALL_DURATION = get_or_create_metric(
    Histogram, "sparkle_llm_call_duration_seconds", "LLM call duration in seconds", ["model", "provider"]
)

AI_RESPONSE_TOTAL_DURATION = get_or_create_metric(
    Histogram,
    "sparkle_ai_response_total_duration_seconds",
    "End-to-end AI response duration in seconds",
    ["chat_mode", "reasoning_mode", "model_tier"],
    buckets=[0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0, 55.0, 89.0],
)

AI_RESPONSE_FIRST_TOKEN_DURATION = get_or_create_metric(
    Histogram,
    "sparkle_ai_response_first_token_duration_seconds",
    "Time to first visible token/event for AI responses in seconds",
    ["chat_mode", "reasoning_mode"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0],
)

AI_RESPONSE_STREAM_DURATION = get_or_create_metric(
    Histogram,
    "sparkle_ai_response_stream_duration_seconds",
    "Streaming duration after first token/event in seconds",
    ["chat_mode", "reasoning_mode"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0],
)

AI_PREDICTION_DURATION = get_or_create_metric(
    Histogram,
    "sparkle_ai_prediction_duration_seconds",
    "Duration of AI/user-behavior prediction pipeline in seconds",
    ["source", "tier", "fallback"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0],
)

AI_PREDICTION_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_ai_prediction_fallback_total",
    "Prediction fallbacks by source transition",
    ["from_source", "to_source"],
)

# 3. 缓存指标
CACHE_HIT_COUNT = get_or_create_metric(
    Counter,
    "sparkle_cache_hits_total",
    "Total number of cache hits/misses",
    ["cache_name", "result"],  # result: hit, miss
)

SEMANTIC_CACHE_HIT_TOTAL = get_or_create_metric(
    Counter, "sparkle_semantic_cache_hit_total", "Total semantic cache hits"
)

SEMANTIC_CACHE_MISS_TOTAL = get_or_create_metric(
    Counter, "sparkle_semantic_cache_miss_total", "Total semantic cache misses"
)

SEMANTIC_CACHE_BYPASS_TOTAL = get_or_create_metric(
    Counter, "sparkle_semantic_cache_bypass_total", "Total semantic cache bypasses"
)

# 4. 工具执行指标
TOOL_EXECUTION_COUNT = get_or_create_metric(
    Counter, "sparkle_tool_executions_total", "Total number of tool executions", ["tool_name", "status"]
)

# 5. 系统指标
ACTIVE_SESSIONS = get_or_create_metric(Gauge, "sparkle_active_sessions_total", "Total number of active chat sessions")

KNOWLEDGE_NODE_UPDATES = get_or_create_metric(
    Counter,
    "sparkle_knowledge_node_updates_total",
    "Total number of knowledge node updates",
    ["reason"],  # Removed user_id
)

RAG_RETRIEVAL_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_rag_retrieval_seconds",
    "RAG retrieval latency",
    ["source", "stage"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

RETRIEVAL_TIMEOUT_TOTAL = get_or_create_metric(
    Counter, "sparkle_retrieval_timeout_total", "Total retrieval timeouts", ["source", "stage"]
)

RETRIEVAL_ERROR_TOTAL = get_or_create_metric(
    Counter, "sparkle_retrieval_error_total", "Total retrieval errors", ["source", "stage"]
)

ACTIVE_WEBSOCKET_CONNECTIONS = get_or_create_metric(
    Gauge, "sparkle_websocket_connections", "Number of active WebSocket connections"
)

OUTBOX_PENDING_EVENTS = get_or_create_metric(
    Gauge, "sparkle_outbox_pending_events", "Number of pending events in the outbox table"
)

INTERVENTION_DELIVERY_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_intervention_delivery_total",
    "Intervention delivery attempts by channel and result",
    ["channel", "result"],
)

INTERVENTION_PUSH_HISTORY_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_intervention_push_history_total",
    "Intervention push history writes",
    ["status"],
)

INTERVENTION_PARAMETER_COMPILATION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_intervention_parameter_compilation_total",
    "Breakpoint 5 parameter compilation results for intervention delivery",
    ["result"],
)

SRL_EVENT_PUBLISHED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_srl_event_published_total",
    "Total SRL transition events published by trigger and mode",
    ["trigger_event_type", "mode"],
)

SRL_EVENT_CONSUMED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_srl_event_consumed_total",
    "Total SRL transition events consumed by trigger and status",
    ["trigger_event_type", "status"],
)

SRL_EVENT_LAG_P95 = get_or_create_metric(
    Gauge,
    "sparkle_srl_event_lag_p95_seconds",
    "Latest p95 lag for SRL transition events in seconds",
)

SRL_PHASE_TRANSITION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_srl_phase_transition_total",
    "SRL phase transitions by from/to phase and source",
    ["from_phase", "to_phase", "source"],
)

SRL_PHASE_UNKNOWN_RATE = get_or_create_metric(
    Gauge,
    "sparkle_srl_phase_unknown_rate",
    "Latest rate of users in UNKNOWN SRL phase",
)

SRL_SCAFFOLDING_ADJUSTED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_srl_scaffolding_adjusted_total",
    "Scaffolding support adjustments from SRL phase hints",
    ["phase", "mode", "applied"],
)

METACOG_BIAS_UPDATED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_metacognition_bias_updated_total",
    "Metacognition snapshot refresh results",
    ["result"],
)

METACOG_SAMPLE_BELOW_THRESHOLD_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_metacognition_sample_below_threshold_total",
    "Dimensions filtered because sample size is below threshold",
    ["dim"],
)

METACOG_PROCESS_SCAFFOLD_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_metacognition_process_scaffold_total",
    "Process scaffolding trigger and skip reasons",
    ["status", "reason"],
)

METACOG_DIAGNOSTIC_WORD_HIT_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_metacognition_diagnostic_word_hit_total",
    "Diagnostic label hits detected in metacognition text",
    ["source"],
)

METACOG_DASHBOARD_VIEW_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_metacognition_dashboard_view_total",
    "Dashboard payload exposures for the metacognition panel",
    ["visibility"],
)

METACOG_SCAFFOLDING_COMBINE_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_metacognition_scaffolding_combine_total",
    "Final combine states for SRL and metacognition scaffolding deltas",
    ["combine_state"],
)

SRL_ROUTER_ZERO_HIT = get_or_create_metric(
    Gauge,
    "sparkle_srl_router_zero_hit",
    "Stage 29 Rule AN router zero-hit status",
)

SRL_TRACKER_LOCK_CONTENTION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_srl_tracker_lock_contention_total",
    "SRL tracker lock contention count",
    ["mode"],
)

SRL_DLQ_SIZE = get_or_create_metric(
    Gauge,
    "sparkle_srl_dlq_size",
    "Current SRL DLQ size",
)

SPARKLE_PROMPT_FIELD_RENDER_COVERAGE_RATIO = get_or_create_metric(
    Gauge,
    "sparkle_prompt_field_render_coverage_ratio",
    "Prompt field render coverage ratio for normalized user-context fields",
)

SOURCE_STATE_ENCODER_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_source_state_encoder_seconds",
    "Source-state encoder latency in seconds",
    buckets=[0.001, 0.003, 0.005, 0.008, 0.01, 0.015, 0.03, 0.05],
)

ROUTING_OUTCOME_BACKFILL_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_routing_outcome_backfill_seconds",
    "Routing decision outcome backfill latency in seconds",
    ["outcome"],
    buckets=[1, 5, 15, 30, 60, 120, 300, 600, 1800],
)

BAYESIAN_RECOMMENDATION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_bayesian_recommendation_total",
    "Bayesian routing recommendations by event and mode",
    ["event", "mode"],
)

BAYESIAN_SHADOW_DIVERGENCE_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_bayesian_shadow_divergence_total",
    "Bayesian shadow divergences from fallback routing",
    ["mode"],
)

# 5b. Proto v2 Migration Metrics
PROTO_FIELD_READ_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_proto_field_read_total",
    "Total protocol field reads by source during v1/v2 migration",
    ["service", "field", "source"],
)

PROTO_DUAL_WRITE_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_proto_dual_write_total",
    "Total dual-write operations for legacy compatibility fields",
    ["service", "field"],
)

PROTO_ERROR_CODE_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_proto_error_code_fallback_total",
    "Total error code fallback operations during v1/v2 migration",
    ["service", "direction"],
)

# 6. Response Feedback & Bandit
RESPONSE_FEEDBACK_INGESTED = get_or_create_metric(
    Counter,
    "sparkle_response_feedback_ingested_total",
    "Total response feedback ingested",
    ["feedback_type"],  # values: up, down
)

RESPONSE_FEEDBACK_DEDUPE_TOTAL = get_or_create_metric(
    Counter, "sparkle_response_feedback_dedup_total", "Total response feedback deduplicated"
)

PROMPT_BANDIT_UPDATES_TOTAL = get_or_create_metric(
    Counter, "sparkle_prompt_bandit_updates_total", "Total prompt bandit updates", ["workflow_id"]
)

PROMPT_BANDIT_STATE_MISSING_TOTAL = get_or_create_metric(
    Counter, "sparkle_prompt_bandit_state_missing_total", "Total prompt bandit state misses", ["workflow_id"]
)

FEEDBACK_TO_EFFECT_SECONDS = get_or_create_metric(
    Histogram,
    "sparkle_feedback_to_effect_seconds",
    "Time from feedback ingestion to prompt selection effect",
    ["workflow_id", "prompt_version"],
    buckets=[60, 300, 900, 1800, 3600, 14400, 86400],
)

SESSION_FEEDBACK_DETECTED_TOTAL = get_or_create_metric(
    Counter, "sparkle_session_feedback_detected_total", "Total detected in-session feedback signals", ["signal_type"]
)

SESSION_FEEDBACK_APPLIED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_session_feedback_applied_total",
    "Total in-session feedback signals that changed the current-turn strategy",
    ["signal_type"],
)

SESSION_FEEDBACK_VISIBLE_HINT_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_session_feedback_visible_hint_total",
    "Total visible session adaptation hints surfaced to the user",
    ["signal_type"],
)

SESSION_FEEDBACK_IGNORED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_session_feedback_ignored_total",
    "Total in-session feedback signals ignored or bypassed",
    ["reason"],
)

SESSION_FEEDBACK_CONFIDENCE_BUCKET = get_or_create_metric(
    Counter,
    "sparkle_session_feedback_confidence_bucket",
    "Confidence buckets for detected in-session feedback signals",
    ["signal_type", "bucket"],
)

PHASE_A_DECISION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_phase_a_decision_total",
    "Phase A planning readiness decisions by action",
    ["action"],
)

PHASE_A_GAP_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_phase_a_gap_total",
    "Phase A missing planning gaps by gap id",
    ["gap_id"],
)

PHASE_A_CONTRADICTION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_phase_a_contradiction_total",
    "Phase A contradiction frequency by id and severity",
    ["contradiction_id", "severity"],
)

PHASE_A_PLANNING_LIKE_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_phase_a_planning_like_total",
    "Phase A planning-like turn evaluations by detection source",
    ["source"],
)

AGENT_PERFORMANCE_RECORDED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_agent_performance_recorded_total",
    "Total recorded agent performance samples",
    ["agent_id", "success"],
)

AGENT_FEEDBACK_LINKED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_agent_feedback_linked_total",
    "Total response feedback events linked back to participating agents",
    ["feedback_type"],
)

AGENT_ROUTING_QUALITY_PROMPT_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_agent_routing_quality_prompt_total",
    "Total routing prompts enriched with agent quality summaries",
    ["layer"],
)

AGENT_COLLAB_DECISION_TOTAL = get_or_create_metric(
    Counter, "sparkle_agent_collab_decision_total", "Total collaboration decisions by source", ["source", "intent_type"]
)

AGENT_COMBINATION_EXPLORATION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_agent_combination_exploration_total",
    "Total exploratory agent-combination selections",
    ["intent_type"],
)

LLM_ROUTER_SELECTION_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_llm_router_selection_total",
    "Total model-routing selections made by the unified LLM router",
    ["agent_role", "model_key", "provider", "tier", "task_type", "complexity", "fallback"],
)

LLM_ROUTER_ESTIMATED_COST_PER_1K = get_or_create_metric(
    Histogram,
    "sparkle_llm_router_estimated_cost_per_1k",
    "Estimated cost-per-1k tokens for router selections",
    ["agent_role", "provider", "tier"],
    buckets=[0.0, 0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01],
)

RUN_LEDGER_EVENT_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_run_ledger_event_total",
    "Total unified run-ledger events recorded",
    ["event_type", "workflow_stage"],
)

RUN_LEDGER_REVIEW_SCORE = get_or_create_metric(
    Histogram,
    "sparkle_run_ledger_review_score",
    "Review scores captured by the unified run ledger",
    ["target_type", "decision"],
    buckets=[0.0, 0.25, 0.5, 0.65, 0.75, 0.85, 0.95, 1.0],
)

RUN_LEDGER_FEEDBACK_EFFECT_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_run_ledger_feedback_effect_total",
    "Total feedback-to-strategy effects captured by the unified run ledger",
    ["effect_target", "status"],
)


# 装饰器：用于测量函数执行时间并记录指标
def track_latency(module, method):
    """Decorator to track function execution latency and record metrics."""

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            span = trace.get_current_span()
            trace_id = format(span.get_span_context().trace_id, "032x") if span else "n/a"

            try:
                result = await func(*args, **kwargs)
                REQUEST_COUNT.labels(module=module, method=method, status="success").inc()
                return result
            except Exception as e:
                # Log with TraceID for correlation
                logger.error(f"[TraceID: {trace_id}] Error in {module}.{method}: {e}")
                REQUEST_COUNT.labels(module=module, method=method, status="error").inc()
                raise
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module=module, method=method).observe(latency)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                REQUEST_COUNT.labels(module=module, method=method, status="success").inc()
                return result
            except Exception as e:
                logger.error(f"Error in {module}.{method}: {e}")
                REQUEST_COUNT.labels(module=module, method=method, status="error").inc()
                raise
            finally:
                latency = time.time() - start_time
                REQUEST_LATENCY.labels(module=module, method=method).observe(latency)

        # Return async wrapper if func is async, else sync wrapper
        if iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============ Phase 3: Circuit Breaker & Collaboration Metrics ============

LANGGRAPH_PLANNING_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_langgraph_planning_total",
    "Total number of LangGraph planning operations",
    ["collaboration_mode", "agents_count"],
)

LANGGRAPH_PLANNING_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_langgraph_planning_latency_seconds",
    "LangGraph planning latency in seconds",
    ["collaboration_mode"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

CIRCUIT_BREAKER_TRIPS = get_or_create_metric(
    Counter, "sparkle_circuit_breaker_trips_total", "Total number of circuit breaker trips", ["circuit_name"]
)

CIRCUIT_BREAKER_RESETS = get_or_create_metric(
    Counter, "sparkle_circuit_breaker_resets_total", "Total number of circuit breaker resets", ["circuit_name"]
)

COLLABORATION_SUCCESS = get_or_create_metric(
    Counter,
    "sparkle_collaboration_total",
    "Total number of collaboration operations",
    ["workflow_type", "agents_used", "outcome"],
)

COLLABORATION_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_collaboration_latency_seconds",
    "Collaboration latency in seconds",
    ["workflow_type"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

EXPERT_SELECTED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_expert_selected_total",
    "Total expert selections by strategy and source",
    ["expert_id", "strategy", "entry_source"],
)

EXPERT_INVOKED_TOTAL = get_or_create_metric(
    Counter, "sparkle_expert_invoked_total", "Total expert invocations", ["expert_id", "workflow_id"]
)

EXPERT_FALLBACK_TOTAL = get_or_create_metric(
    Counter, "sparkle_expert_fallback_total", "Total expert fallbacks", ["reason", "from_mode"]
)

EXPERT_OVERRIDDEN_TOTAL = get_or_create_metric(
    Counter, "sparkle_expert_overridden_total", "Total explicit expert overrides", ["requested_expert", "used_expert"]
)

USER_FEEDBACK_BOUND_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_user_feedback_bound_total",
    "Total feedback events bound to expert routing context",
    ["workflow_id"],
)

# ============ Strategy Optimization Metrics ============

ADAPTIVE_ROUTING_ADJUSTMENTS_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_adaptive_routing_adjustments_total",
    "Adaptive routing adjustments by trigger and mode change",
    ["action", "trigger", "from_mode", "to_mode"],
)

ROUTING_SUMMARY_CONTEXT_TOTAL = get_or_create_metric(
    Counter, "sparkle_routing_summary_context_total", "Summary context usage in routing", ["phase"]
)

AURORA_STAGE33_FALLBACK_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_stage33_fallback_total",
    "Stage33 fallbacks by feature and reason",
    ["feature", "reason"],
)

RESPONSE_FALLBACK_GENERATED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_response_fallback_generated_total",
    "Fallback responses generated to avoid empty output",
    ["source"],
)

# ============ Phase 4: Preference Inference Metrics ============

PREFERENCE_INFERENCE_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_preference_inference_total",
    "Total number of preference inferences from feedback",
    ["preference_key", "direction", "source"],  # source: feedback, behavior
)

PREFERENCE_INFERENCE_CONFIDENCE = get_or_create_metric(
    Gauge,
    "sparkle_preference_inference_confidence",
    "Current confidence level for inferred preferences",
    ["preference_key"],
)

PREFERENCE_DECAY_APPLIED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_preference_decay_applied_total",
    "Total number of preference decay operations",
    ["preference_key", "action"],  # action: decay, reset
)

# ============ Phase 4: Preference Event Latency Metrics ============

PREFERENCE_EVENT_E2E_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_preference_event_e2e_latency_seconds",
    "End-to-end latency from preference update to cache invalidation",
    ["event_type", "source"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

PREFERENCE_EVENT_CONSUME_LAG = get_or_create_metric(
    Gauge,
    "sparkle_preference_event_consume_lag_seconds",
    "Time lag between event publish and consumer processing",
    ["consumer_group"],
)

PREFERENCE_EVENT_STREAM_LENGTH = get_or_create_metric(
    Gauge, "sparkle_preference_event_stream_length", "Number of pending events in Redis Stream", ["stream_key"]
)

CACHE_INVALIDATION_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_cache_invalidation_latency_seconds",
    "Time from cache invalidation call to completion",
    ["cache_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)

PREFERENCE_EVENT_ERRORS_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_preference_event_errors_total",
    "Total preference event processing errors",
    ["error_type", "consumer_group"],
)

# ============ Phase 3: Event Bus Health Metrics ============

EVENT_BUS_DLQ_MESSAGES = get_or_create_metric(
    Gauge, "sparkle_event_bus_dlq_messages", "Number of messages in the Dead Letter Queue", ["stream"]
)

EVENT_BUS_CONSUMER_LAG_MESSAGES = get_or_create_metric(
    Gauge,
    "sparkle_event_bus_consumer_lag_messages",
    "Number of pending messages behind the stream head for a consumer group",
    ["stream", "consumer_group"],
)

EVENT_BUS_CONSUMER_LAG_SECONDS = get_or_create_metric(
    Gauge,
    "sparkle_event_bus_consumer_lag_seconds",
    "Time lag in seconds between stream head and consumer group position",
    ["stream", "consumer_group"],
)

SPARKLE_SKILL_COUNT_PER_USER = get_or_create_metric(
    Histogram,
    "sparkle_skill_count_per_user",
    "Observed skill counts per user against the Stage 21 cap",
    buckets=[0, 1, 3, 5, 10, 20, 30, 40, 50],
)

SPARKLE_SKILL_EXTRACT_DRAFT_ACCEPT_RATE = get_or_create_metric(
    Gauge,
    "sparkle_skill_extract_draft_accept_rate",
    "Acceptance ratio for Stage 21 skill drafts",
)

SPARKLE_SKILL_SELECTION_ACTIVATION_RATE = get_or_create_metric(
    Histogram,
    "sparkle_skill_selection_activation_rate",
    "Distribution of how many skills activate per routing turn",
    buckets=[0, 1, 2, 3],
)

SPARKLE_SKILL_SHARE_PIPELINE_LATENCY_SECONDS = get_or_create_metric(
    Histogram,
    "sparkle_skill_share_pipeline_latency_seconds",
    "End-to-end latency for the Stage 21 skill share pipeline",
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)
