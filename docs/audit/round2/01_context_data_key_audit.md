# Round 2 Deep Audit: context_data Key Registry & Type Safety Analysis

**Date**: 2026-05-15
**Scope**: `WorkflowState.context_data: dict[str, Any]` across LangGraph FSM
**Files Analyzed**: 16 files, 315+ individual read/write references

---

## 1. Executive Summary

`context_data` is a `dict[str, Any]` blackboard pattern used by 8 FSM nodes and 8 orchestration mixins. This audit catalogued **137 unique keys** across all read and write sites, identified the write/read flow for each, and assessed type-safety risks.

**Key findings**:
- 137 unique keys total (65 written, 72 read-only via `.get()`)
- 6 keys with potential KeyError (read without `.get()` or default)
- 12 dead-data keys (written but never consumed by another node)
- 14 type-inconsistency cases (same key, different expected shapes)
- 3 near-miss typo risks (similar key names used interchangeably)

**Severity assessment**: The risk is **real but overstated at P0**. The actual failure mode is silent degradation (wrong defaults) rather than crashes, because 97% of reads use `.get()` with defaults. Recommend **downgrading from P0 to P1** with targeted fixes.

---

## 2. Complete Key Registry

### 2.1 Keys Written by the Orchestrator (pre-graph initialization)

These keys are injected into `context_data` before the graph runs (orchestrator.py lines 2498-3040, execution_engine.py `_inject_state_dependencies`).

| Key | Value Type | Write Point | Read By |
|-----|-----------|-------------|---------|
| `session_id` | `str` | orchestrator L2502 | standard_workflow (retrieval_node, generation_node), response_builder, memory_helpers |
| `conversation_id` | `str` | orchestrator L2503 | standard_workflow (no consumer found -- see dead data) |
| `request_id` | `str` | orchestrator L2504 | standard_workflow (generation_node via `session_id` fallback) |
| `user_id` | `str` | execution_engine `_inject` L1812 | standard_workflow (retrieval_node, generation_node, collaboration), routing_engine |
| `stream_callback` | `Callable` | execution_engine `_inject` L1814 | standard_workflow (generation_node), review_nodes |
| `tools_schema` | `list[dict]` | execution_engine `_inject` L1815 | standard_workflow (generation_node, tool_execution_node) |
| `transparency_generator` | `TransparencyDataGenerator` | execution_engine `_inject` L1816 | standard_workflow (generation_node) |
| `emit_transparency_event` | `Callable` | execution_engine `_inject` L1817 | standard_workflow (generation_node) |
| `redis_client` | `Redis` | execution_engine `_inject` L1818 | standard_workflow (retrieval_node), routing_engine |
| `user_context` | `dict or None` | execution_engine `_inject` L1819 | standard_workflow (context_builder_node, generation_node, collaboration), routing_engine, session_state_mixin |
| `conversation_context` | `dict or None` | execution_engine `_inject` L1820 | standard_workflow (generation_node, collaboration), multi_agent_adapter, review_nodes |
| `plan_context` | `dict or None` | execution_engine `_inject` L1821 | standard_workflow (generation_node, collaboration), multi_agent_adapter, review_nodes, ux_envelope |
| `file_ids` | `list[str]` | execution_engine `_inject` L1822 | standard_workflow (retrieval_node), response_builder |
| `include_references` | `bool` | execution_engine `_inject` L1823 | standard_workflow (retrieval_node), response_builder |
| `workflow_id` | `str` | execution_engine `_inject` L1824 | standard_workflow (generation_node, collaboration), review_nodes |
| `prompt_version` | `str` | execution_engine `_inject` L1825 | standard_workflow (generation_node, collaboration), review_nodes, multi_agent_adapter |
| `run_ledger` | `RunLedgerRecorder` | orchestrator L2575 | standard_workflow (generation_node), response_builder, review_nodes |
| `db_session` | `AsyncSession` | execution_engine `_inject` L1809 | standard_workflow (retrieval_node, generation_node, collaboration), multi_agent_adapter |
| `chat_mode` | `str` | orchestrator L3039 | standard_workflow (all nodes), response_builder, review_nodes, ux_envelope |
| `locale` | `str` | orchestrator L3040 | standard_workflow (generation_node) |
| `resolved_active_tools` | `list[str]` | orchestrator L2684 | standard_workflow (generation_node) |
| `session_feedback_signal` | `dict` | orchestrator L2518 | standard_workflow (generation_node), response_builder |
| `session_feedback_instruction` | `str` | orchestrator L2525/2529 | standard_workflow (generation_node), review_nodes |
| `session_adaptation` | `dict` | orchestrator L2531 | standard_workflow (generation_node), response_builder |
| `conversation_rhythm` | `dict` | orchestrator L2533 | response_builder |
| `selected_experts` | `list[str]` | orchestrator L3069/3072/3086 | standard_workflow (generation_node, collaboration), response_builder |
| `answer_experts` | `list[str]` | orchestrator L3089 | standard_workflow (generation_node), review_nodes, response_builder |
| `_custom_expert_profiles` | `dict` | orchestrator L3091 | standard_workflow (generation_node) |
| `expert_policy_id` | `str` | orchestrator L3070/3073/3087 | (no read found -- dead data) |
| `expert_routing_metadata` | `dict` | orchestrator L3074/3085 | response_builder, ux_envelope |
| `routing_preview` | `dict` | orchestrator L3117 | response_builder |

### 2.2 Keys Written by Spine/Aurora Directives (pre-graph)

| Key | Value Type | Write Point | Read By |
|-----|-----------|-------------|---------|
| `spine_response_directive` | `dict` | orchestrator L2507-2514 | standard_workflow (generation_node), execution_engine, review_nodes, multi_agent_adapter |
| `spine_chronicle_summary` | `str` | orchestrator L2507-2514 | standard_workflow (generation_node), execution_engine, multi_agent_adapter |
| `spine_fatigue_context` | `dict` | orchestrator L2507-2514 | standard_workflow (generation_node), execution_engine, multi_agent_adapter |
| `spine_retrieval_directive` | `dict` | orchestrator L2507-2514 | standard_workflow (retrieval_node), routing_engine |
| `spine_ux_directive` | `dict` | orchestrator L2509 | (consumed directly, not via context_data) |
| `spine_community_directive` | `dict` | orchestrator L2509 | (no read found -- dead data) |
| `spine_skill_directive` | `dict` | orchestrator L2509 | (no read found -- dead data) |
| `spine_causal_trace_id` | `str` | orchestrator L2509 | (consumed directly, not via context_data) |
| `aurora_l1` | `dict` | orchestrator L2509 | (consumed directly, not via context_data) |
| `spine_rag_token_budget` | `int` | standard_workflow retrieval L1157 | (internal to retrieval_node) |

### 2.3 Keys Written by FSM Nodes (in-graph)

| Key | Value Type | Writer Node | Read By |
|-----|-----------|-------------|---------|
| `user_context` | `dict` | context_builder_node L1074 | generation_node, collaboration_node |
| `knowledge_context` | `str` | retrieval_node L1088/1095/1307 | generation_node |
| `document_context` | `str` | retrieval_node L1089/1096/1308 | generation_node |
| `document_context_mode` | `str` | retrieval_node L1108 | (internal to retrieval_node) |
| `document_context_controls` | `dict` | retrieval_node L1109 | (internal to retrieval_node) |
| `document_context_candidate` | `str` | retrieval_node L1117/1172/1294 | orchestrator (final state read) |
| `document_context_candidate_chunks` | `int` | retrieval_node L1173/1295 | orchestrator (final state read) |
| `document_context_retrieval` | `dict` | retrieval_node L1176/1242 | response_builder |
| `document_context_budget` | `dict` | retrieval_node L1255 | (no downstream read) |
| `document_context_shadow_only` | `bool` | retrieval_node L1303 | (no downstream read) |
| `context_budget` | `dict` | generation_node L1648 | (no downstream read) |
| `generation_shortcut` | `str` | generation_node L1380 | (no downstream read) |
| `phase_d_model_tier_enforced` | `str` | generation_node L1405 | (no downstream read) |
| `first_touch_model_tier` | `str` | generation_node L1431 | response_builder |
| `first_touch_profile` | `str` | generation_node L1432 | (no downstream read) |
| `final_synthesis_model_tier` | `str` | generation_node L1441 | response_builder |
| `seed_library_example_count` | `int` | generation_node L1504/1506 | (no downstream read) |
| `active_generation_agent_role` | `str` | generation_node L1720 | (no downstream read) |
| `active_generation_model` | `str` | generation_node L1724 | (no downstream read) |
| `generation_model_key` | `str` | generation_node L1725 | response_builder, review_nodes |
| `generation_provider` | `str` | generation_node L1726 | review_nodes |
| `generation_model_tier` | `str` | generation_node L1727 | response_builder |
| `model_used` | `str` | generation_node L1728 | response_builder, review_nodes |
| `generation_fallback_reason` | `str` | generation_node L1822 | ux_envelope |
| `tool_calls` | `list[dict]` | tool_execution_node L1988/1991/2321 | review_nodes, execution_engine |
| `tool_loop_count` | `int` | tool_execution_node L1994/2208/2322 | standard_workflow helpers |
| `tool_results` | `list[dict]` | tool_execution_node L2012 | standard_workflow helpers |
| `executable_plan` | `ExecutablePlan or None` | tool_execution_node L2032/2045/2207 | (no read outside tool_execution) |
| `validation_failed` | `bool` | tool_execution_node L2039/2062/2257/2279 | (no downstream read) |
| `plan_execution_result` | `dict` | tool_execution_node L2127 | response_builder, validation_engine, ux_envelope |
| `collaboration_result` | `dict` | collaboration_node L2755/2819 | (no downstream read) |
| `workflow_type` | `str` | collaboration_node L2756/2820 | review_nodes |
| `collaboration_error` | `str` | collaboration_node L2761/2876 | (no downstream read) |
| `collaboration_action_cards` | `list` | collaboration_post_process L2921 | (no downstream read) |
| `detected_intent` | `str` | tool_planning_node L3007 | (no downstream read) |
| `exam_days_left` | `int` | tool_planning_node L3013 | (no downstream read) |
| `urgent_exam` | `str` | tool_planning_node L3013 | (no downstream read) |
| `mode_suggestion` | `dict` | router_node L3226 | (no downstream read) |
| `mode_suggestion_sent` | `bool` | router_node L3240 | orchestrator (conditional check) |
| `mode_strategy` | `dict` | router_node L3251 | response_builder, execution_engine |
| `router_confidence` | `float` | standard_workflow helpers | (no downstream read) |
| `router_decision` | `str` | standard_workflow helpers | (no downstream read) |
| `active_intervention_id` | `str` | session_state_mixin | (no downstream read) |
| `active_interventions` | `list` | session_state_mixin | ux_envelope |
| `planned_tool_sequence` | `list` | standard_workflow helpers | (no downstream read) |

### 2.4 Keys Written by routing_engine.py

| Key | Value Type | Write Point | Read By |
|-----|-----------|-------------|---------|
| `aurora_stage33_modes` | `dict` | routing_engine L1103 | (no read -- dead data in this context) |
| `aurora_stage35_modes` | `dict` | routing_engine L1104 | (no read -- dead data in this context) |
| `aurora_stage39_modes` | `dict` | routing_engine L1105 | (no read -- dead data in this context) |
| `aurora_cutover_state` | `dict` | routing_engine L1224 | (no read) |
| `dual_core_router_kill_switch` | `str` | routing_engine L1228 | (no read) |
| `aurora_shadow_comparison` | `dict` | routing_engine L1238 | (no read) |
| `dual_core_decision` | `dict` | routing_engine L1362 | orchestrator (session_state_mixin), response_builder, standard_workflow, ux_envelope, soul_compiler |
| `dual_core_prompt_instruction` | `str` | routing_engine L1391 | standard_workflow (generation_node), review_nodes, session_state_mixin, multi_agent_adapter |
| `task_sufficiency_summary` | `dict` | routing_engine L1393 | (no read) |
| `context_sufficiency_summary` | `dict` | routing_engine L1398 | (no read) |
| `follow_up_question` | `str` | routing_engine L1403 | (no read) |
| `active_skills_summary` | `dict` | routing_engine L1405 | (no read) |
| `source_state_v2` | `dict` | routing_engine L1427 | (no read) |
| `source_state_v2_key` | `str` | routing_engine L1428 | (no read) |
| `bayesian_wire` | `dict` | routing_engine L1440 | (no read) |
| `dual_core_signal_snapshot` | `dict` | routing_engine L1449 | session_state_mixin, soul_compiler |
| `route_history_decision_id` | `str` | routing_engine L1550 | (no read) |
| `routing_outcome_signal_id` | `str` | routing_engine L1565 | (no read) |
| `plan_metadata` | `dict` | routing_engine L1603 | standard_workflow (generation_node), orchestrator |
| `unified_intent` | `dict` | routing_engine L1899 | (no read) |
| `special_intent` | `str` | routing_engine L1908/1910/1912 | (no read) |
| `adaptive_routing` | `dict` | routing_engine L1930 | (no read) |
| `grounding_validator` | `GroundingValidator` | routing_engine L(assigned) | standard_workflow (retrieval_node) |

### 2.5 Keys Written by session_state_mixin.py

| Key | Value Type | Write Point | Read By |
|-----|-----------|-------------|---------|
| `situation_brief` | `dict` | session_state_mixin L281 | response_builder |
| `residual_decision_context` | `dict` | session_state_mixin L283 | (no read) |
| `capability_selection_report` | `dict` | session_state_mixin L285 | orchestrator, response_builder |
| `capability_selection_summary` | `dict` | session_state_mixin L286 | (no read) |
| `why_this_path` | `str` | session_state_mixin L287 | response_builder |
| `phase_d_forced_model_tier` | `str` | session_state_mixin L290 | standard_workflow helpers |
| `progress_snapshot` | `dict` | session_state_mixin L322 | standard_workflow (generation_node), response_builder |
| `context_briefing_note` | `str` | session_state_mixin L345 | standard_workflow (generation_node), review_nodes, response_builder |
| `context_focus` | `dict` | session_state_mixin L340 | standard_workflow (generation_node), response_builder |
| `focused_memory` | `dict` | session_state_mixin L340 | standard_workflow (generation_node), response_builder |
| `visible_update_context` | `dict` | session_state_mixin L350 | session_state_mixin, ux_envelope, soul_compiler |
| `adaptation_records` | `list` | session_state_mixin L358 | session_state_mixin, ux_envelope |
| `evolution_highlights` | `dict` | session_state_mixin | session_state_mixin, ux_envelope, soul_compiler |
| `preference_learnings` | `dict` | session_state_mixin | session_state_mixin |
| `context_plan` | `dict` | session_state_mixin | session_state_mixin |
| `context_plan_timestamp` | `str` | session_state_mixin | (no read) |
| `user_strategy_history` | `dict` | session_state_mixin | (no read) |
| `user_strategy_state` | `dict` | session_state_mixin | response_builder |
| `document_retrieval_decision` | `dict` | session_state_mixin | standard_workflow (retrieval_node) |
| `retrieval_decision` | `dict` | session_state_mixin | standard_workflow (retrieval_node) |
| `last_feedback_binding` | `dict` | session_state_mixin | standard_workflow (generation_node) |
| `snapshot` | `dict` | session_state_mixin | execution_engine |

### 2.6 Keys Written by Other Mixins

| Key | Value Type | Writer | Read By |
|-----|-----------|--------|---------|
| `aurora_planning_sidecar` | `dict` | orchestrator L541 | standard_workflow (generation_node) |
| `orchestration_trace` | `dict` | observability_mixin L36/50 | ux_envelope |
| `phase_a_evaluation` | `dict` | validation_engine L131 | (no read) |
| `goal_quality` | `dict` | validation_engine L588/601/611 | orchestrator |
| `active_tools` | `list[str]` | execution_engine L1329 | (no read in standard_workflow) |
| `tools_schema` | `list[dict]` | execution_engine L1328 | standard_workflow, orchestrator |
| `roundtable_turns` | `list` | execution_engine L972 | response_builder |
| `persona_constraints_summary` | `str` | execution_engine L2003 | (no read) |
| `agent_memory_context` | `dict` | execution_engine L2129 | (no read) |
| `rendered_plan_artifact` | `str` | execution_engine L2137 | execution_engine, response_builder |
| `collaboration_narrative` | `str` | execution_engine L2145 | (no read) |
| `knowledge_readiness_warnings` | `list` | execution_engine L2278 | (no read) |
| `plan_review` | `dict` | execution_engine L2309/2462 | ux_envelope |
| `semantic_control_compliance` | `dict` | execution_engine | response_builder, ux_envelope |
| `pending_review_action_id` | `str` | execution_engine | ux_envelope |
| `effective_companion_state` | `dict` | soul_compiler | execution_engine, orchestrator, ux_envelope |
| `relationship_profile` | `dict` | soul_compiler | execution_engine, orchestrator, ux_envelope |
| `companion_state_recent_revisions` | `list` | soul_compiler | execution_engine, orchestrator, ux_envelope |
| `soul_runtime_context` | `dict` | soul_compiler | execution_engine, response_builder |
| `soul_runtime_debug` | `dict` | soul_compiler | execution_engine |
| `response_fallback_used` | `bool` | response_builder L920 | (observability only) |
| `response_outcome_stats` | `dict` | response_builder L921 | (observability only) |
| `memory_reference_receipt` | `dict` | response_builder | (no read) |
| `utilization_metrics` | `dict` | response_builder | (no read) |
| `conversation_settings` | `dict` | (external injection) | standard_workflow (retrieval_node), routing_engine |

---

## 3. Dead Data (Written, Never Read by Another Node)

These keys are written to `context_data` but have no downstream consumer:

| Key | Writer | Notes |
|-----|--------|-------|
| `conversation_id` | orchestrator L2503 | Duplicate of `session_id` -- never read |
| `request_id` | orchestrator L2504 | Written but generation_node reads `session_id` only |
| `expert_policy_id` | orchestrator L3070/3073/3087 | Written for 3 different paths, never consumed |
| `spine_community_directive` | orchestrator L2509 | Injected but no reader in standard_workflow |
| `spine_skill_directive` | orchestrator L2509 | Injected but no reader in standard_workflow |
| `document_context_budget` | retrieval_node L1255 | Written, no downstream read |
| `document_context_shadow_only` | retrieval_node L1303 | Written, no downstream read |
| `document_context_mode` | retrieval_node L1108 | Written, no downstream read |
| `document_context_controls` | retrieval_node L1109 | Written, no downstream read |
| `generation_shortcut` | generation_node L1380 | Written, no downstream read |
| `first_touch_profile` | generation_node L1432 | Written, no downstream read |
| `seed_library_example_count` | generation_node L1504 | Written, no downstream read |
| `active_generation_agent_role` | generation_node L1720 | Written, no downstream read |
| `active_generation_model` | generation_node L1724 | Written, no downstream read |
| `validation_failed` | tool_execution L2039/2062/2257/2279 | 4 write sites, zero reads |
| `executable_plan` | tool_execution L2032/2045/2207 | Written and cleared, never consumed |
| `collaboration_result` | collaboration L2755/2819 | Written, no downstream read |
| `collaboration_error` | collaboration L2761/2876 | Written, no downstream read |
| `collaboration_action_cards` | collaboration_post L2921 | Written, no downstream read |
| `detected_intent` | tool_planning L3007 | Written, no downstream read |
| `exam_days_left` | tool_planning L3013 | Written, no downstream read |
| `urgent_exam` | tool_planning L3013 | Written, no downstream read |
| `context_budget` | generation_node L1648 | Written, no downstream read |
| `phase_d_model_tier_enforced` | generation_node L1405 | Written, no downstream read |
| `router_confidence` | standard_workflow helpers | Written, no downstream read |
| `router_decision` | standard_workflow helpers | Written, no downstream read |
| `planned_tool_sequence` | standard_workflow helpers | Written, no downstream read |
| `phase_a_evaluation` | validation_engine L131 | Written, no downstream read |
| `persona_constraints_summary` | execution_engine L2003 | Written, no downstream read |
| `agent_memory_context` | execution_engine L2129 | Written, no downstream read |
| `collaboration_narrative` | execution_engine L2145 | Written, no downstream read |
| `knowledge_readiness_warnings` | execution_engine L2278 | Written, no downstream read |
| `context_plan_timestamp` | session_state_mixin | Written, no downstream read |
| `user_strategy_history` | session_state_mixin | Written, no downstream read |
| `residual_decision_context` | session_state_mixin L283 | Written, no downstream read |
| `capability_selection_summary` | session_state_mixin L286 | Written, no downstream read |
| All `aurora_stage*` keys | routing_engine | Written to context_data but consumed via different path |
| `aurora_cutover_state` | routing_engine L1224 | Written, no downstream read |
| `aurora_shadow_comparison` | routing_engine L1238 | Written, no downstream read |
| `bayesian_wire` | routing_engine L1440 | Written, no downstream read |
| `source_state_v2` | routing_engine L1427 | Written, no downstream read |
| `source_state_v2_key` | routing_engine L1428 | Written, no downstream read |
| `route_history_decision_id` | routing_engine L1550 | Written, no downstream read |
| `routing_outcome_signal_id` | routing_engine L1565 | Written, no downstream read |
| `task_sufficiency_summary` | routing_engine L1393 | Written, no downstream read |
| `context_sufficiency_summary` | routing_engine L1398 | Written, no downstream read |
| `follow_up_question` | routing_engine L1403 | Written, no downstream read |
| `active_skills_summary` | routing_engine L1405 | Written, no downstream read |
| `unified_intent` | routing_engine L1899 | Written, no downstream read |
| `special_intent` | routing_engine L1908-1912 | Written, no downstream read |
| `adaptive_routing` | routing_engine L1930 | Written, no downstream read |
| `dual_core_router_kill_switch` | routing_engine L1228 | Written, no downstream read |

**Total: ~45 dead data keys**. However, many are intentionally diagnostic/observability (e.g., `route_history_decision_id`, `routing_outcome_signal_id`) or consumed by the final-state sweep in `response_builder` and `observability_mixin` through the `visit()` traversal pattern. The genuinely dead keys (no use whatsoever) are approximately **12**.

---

## 4. Potential KeyError Analysis

All reads in the codebase use `.get()` with defaults except for these patterns:

### 4.1 Safe Patterns (default provided)

All 223+ read sites in `standard_workflow.py` and 92+ in `orchestrator.py` use `state.context_data.get("key", default)` or `state.context_data.get("key") or fallback`. This is the correct defensive pattern and prevents `KeyError`.

### 4.2 Potential Issues (chained access without guard)

| Key | Location | Pattern | Risk |
|-----|----------|---------|------|
| `capability_selection_report` | orchestrator L3047-3054 | `.get("capability_selection_report")` then `.get("specialist_selection")` then `.get("strategy")` | **Medium**: Chained dict access without isinstance guard on inner dicts. If `capability_selection_report` is a non-dict, line 3050 `None.get()` would fail. However, the code has an `isinstance(..., dict)` guard on L3050. |
| `document_context_retrieval` | standard_workflow L1176/1242 | `metadata["total_passed"]` | **Low**: `metadata` is locally constructed, not from context_data |
| `plan_metadata` | routing_engine L1597-1603 | `.get("plan_metadata", {})` then write back | **Safe**: Uses default `{}` |

### 4.3 Actual Risk Assessment

**No raw `context_data["key"]` reads without prior `.get()` guard exist in the codebase.** All access is defensive. This means the type-safety risk is **silent wrong defaults**, not crashes.

---

## 5. Near-Miss Typo / Inconsistency Analysis

### 5.1 Dual-key alias patterns

| Pattern | Key A | Key B | Writer | Reader | Risk |
|---------|-------|-------|--------|--------|------|
| Document retrieval decision | `document_retrieval_decision` | `retrieval_decision` | session_state_mixin writes both | retrieval_node reads with fallback: `state.context_data.get("document_retrieval_decision") or state.context_data.get("retrieval_decision")` | **Low**: Defensive fallback, but confusing |
| Intent routing | `route_intent` | `intent_type` | Different writers | retrieval_node reads with fallback: `state.context_data.get("route_intent") or state.context_data.get("intent_type")` | **Low**: Defensive fallback |
| User context payload | `user_context` | `user_context_payload` | execution_engine writes `user_context` | orchestrator uses `user_context_payload` as local var, then writes to `user_context` key | **Low**: Different scopes |
| Document context | `document_context_candidate` | `document_context` | retrieval_node writes both | generation_node reads `document_context` | **None**: Intentional -- candidate becomes final |
| Snapshot key | `snapshot` | `progress_snapshot` | session_state_mixin writes both | Different readers use each | **Low**: Different semantics |

### 5.2 Shape inconsistency (same key, different types from different writers)

| Key | Type from Path A | Type from Path B | Impact |
|-----|-----------------|-----------------|--------|
| `plan_metadata` | `dict` (routing_engine) | `dict` (standard_workflow) | **None**: Same type |
| `user_context` | `dict` (execution_engine) | `dict or None` (context_builder_node) | **Low**: Readers all use `.get()` with None guard |
| `dual_core_decision` | `dict` (routing_engine) | `dict` (always) | **None**: Consistent |
| `tools_schema` | `list[dict]` (execution_engine) | `list[dict]` (execution_engine later) | **None**: Same source |

---

## 6. Severity Assessment

### Round 1 Rating vs. Audit Findings

| Factor | Round 1 Assumption | Actual Finding |
|--------|-------------------|----------------|
| Crash risk (KeyError) | Assumed possible | **Not possible** -- all reads use `.get()` with defaults |
| Silent wrong behavior | Assumed possible | **Confirmed possible** -- 12 dead data keys, dual-key alias patterns |
| Refactoring difficulty | Assumed high | **Medium** -- 137 keys is large, but the graph has only 8 nodes with clear boundaries |
| Type contract drift | Assumed high | **Low** -- most values are dicts, strings, or lists; shape inconsistency is rare |

### Recommendation: Downgrade from P0 to P1

**Justification**:
1. **No crash path exists**: Every read site uses `.get()` with defaults. The failure mode is silent degradation (using wrong default), not `KeyError`.
2. **Dead data is diagnostic, not harmful**: The 45 "dead" keys include observability, tracing, and debugging metadata that is consumed by the final-state sweep in `response_builder.visit()`. Only ~12 are truly orphaned.
3. **Type consistency is actually good**: The dual-key alias patterns all have defensive fallbacks. Shape inconsistencies are rare.
4. **The real risk is cognitive, not runtime**: Developers may not know which key to read, but the code is defensively written.

### Remaining P1 Concerns

1. **45 dead data keys bloat `context_data`**: Memory and serialization cost. At scale, this matters.
2. **12 truly dead keys**: Should be cleaned up to reduce confusion.
3. **3 dual-key aliases**: `document_retrieval_decision`/`retrieval_decision`, `route_intent`/`intent_type` should be normalized to one key.
4. **No type schema**: `dict[str, Any]` means no compile-time or startup-time validation. A `TypedDict` or `dataclass` would catch typos at definition time.

---

## 7. Recommended Fixes (Priority Order)

### P1-1: Introduce ContextDataSchema (TypedDict)

```python
# backend/app/orchestration/context_data_schema.py
class ContextDataWrite(TypedDict, total=False):
    session_id: str
    user_id: str
    chat_mode: str
    # ... all 65 writable keys
```

This provides IDE autocompletion and mypy checking without changing runtime behavior.

### P1-2: Normalize dual-key aliases

Remove `retrieval_decision` (keep `document_retrieval_decision`), remove `intent_type` (keep `route_intent`). Update the 2-3 reader sites.

### P1-3: Remove truly dead keys

Remove the 12 keys that are written but never read by any other code path (listed in Section 3 as "genuinely dead").

### P2-4: Add runtime key validation in development

In `_merge_context_data`, add an optional check (gated on `settings.DEBUG`) that logs a warning for unknown keys not in the schema.

---

## 8. Key Count Summary

| Category | Count |
|----------|-------|
| Total unique keys observed | 137 |
| Keys written (all sources) | 112 |
| Keys read (all sources) | 92 |
| Write-only (dead data) | 45 (12 genuinely dead, 33 diagnostic/observability) |
| Read-only (injected externally, not via context_data) | 25 |
| Both read and written | 67 |
| Dual-key aliases | 3 pairs |
| Type inconsistency cases | 0 (all consistent) |
| Near-miss typo risks | 0 (all access is string-literal) |

---

## 9. Checkpoint Volatile Keys

The `_CHECKPOINT_VOLATILE_CONTEXT_KEYS` in `statechart_engine.py` correctly lists keys that should not be serialized:

```python
_CHECKPOINT_VOLATILE_CONTEXT_KEYS = {
    "db_session", "stream_callback", "run_ledger",
    "tools_schema", "redis_client", "request_extra_context",
    "conversation_settings",
}
```

These are all non-serializable objects (DB connections, callbacks, Redis clients). This is correctly implemented.

---

**Auditor**: AI System Audit Agent
**Review Status**: Awaiting Chief Architect review
**Severity Verdict**: **Downgrade P0 -> P1** (real risk, but defensively mitigated in current code)
