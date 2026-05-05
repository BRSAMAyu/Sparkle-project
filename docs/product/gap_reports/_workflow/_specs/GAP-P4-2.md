# GAP-P4-2: 成本预测框架 (Cost Prediction Framework) -- Implementation Spec

> **Mode**: spec→you | **Level**: L3 (Cross-Boundary) | **Effort**: L (6.5-9.5 days)
> **Source**: OBS-013 from 06_observability.md -- LLM/RAG/Aurora/P4 Cost Prediction Missing
> **Status**: Spec ready for user implementation

---

## 1. Objectives

### 1.1 Why This Exists

The OBS-013 audit found Sparkle has **strong post-hoc cost recording** but **zero pre-execution cost prediction**. Every AI operation (LLM call, RAG retrieval, Aurora inference, P4 evaluation) is tracked after the fact via `cost_controller.py`, but no code path estimates cost BEFORE execution. This means:

- A prompt change that doubles token usage is deployed without knowing it will cost 2x more.
- Aurora stage activation has no per-user cost projection.
- P4 counterfactual evaluation runs have unknown financial impact.
- RAG scaling (embedding volume, vector search count) has no cost forecast.

Furthermore, **pricing data is fragmented across 4+ files** with inconsistent values, making it impossible to get a single source of truth for cost estimation.

### 1.2 Core Goals

1. **Unified Pricing Registry** — Single source of truth for all AI pricing (LLM per provider/model, embedding, rerank, RAG operations, Aurora tiers, P4 evaluations).
2. **Pre-Execution Cost Predictor** — Given a model name and estimated token counts, return a predicted cost in USD before the API call.
3. **RAG Cost Estimator** — Predict cost of a RAG pipeline given: number of embeddings, vector search dimensions, rerank calls, graph retrieval depth.
4. **Aurora Cost Projector** — Predict per-user-per-day cost of each Aurora tier (L0-L4), given estimated invocation frequency.
5. **P4 Evaluation Cost Model** — Predict cost of a counterfactual evaluation given: number of variants, evaluation stages, model tiers.
6. **Budget-Aware Request Gate** — Optional pre-execution check that blocks or warns when a single request exceeds a configurable cost threshold.
7. **Prometheus Prediction Metrics** — New metrics tracking prediction-vs-actual accuracy.

### 1.3 Non-Goals

- Not building a per-user cost billing system (GAP-P4-3 scope).
- Not building a cost optimization router (separate routing concern).
- Not modifying existing `BudgetCircuitBreaker` logic.
- Not building a cost forecasting UI dashboard (metrics only).
- Not integrating with external billing/accounting systems.

---

## 2. Current State Assessment

### 2.1 What EXISTS (Post-Hoc Cost Recording)

| Component | File | Capability |
|-----------|------|-----------|
| Cost Controller | `backend/app/core/cost_controller.py` | Prometheus metrics, daily budget circuit breaker, hourly spend rate tracking, pricing tables for LLM/RAG/Aurora tiers |
| LLM Quota Guard | `backend/app/core/llm_quota.py` | User-level daily token quotas, Redis-based atomic quota reservation, hardcoded per-model pricing |
| LLM Monitor | `backend/app/core/llm_monitoring.py` | Prometheus cost Counter, latency histograms, security event tracking, CostSpike alert |
| Token Tracker | `backend/app/orchestration/token_tracker.py` | Per-request token recording to Redis, daily per-model aggregation |
| LLM Router | `backend/app/core/llm_router.py` | Per-model `cost_per_1k_tokens`, tier-based fallback ordering |
| LLM Service | `backend/app/services/llm_service.py` | `record_llm_cost()` at 3 integration points |
| Graph RAG | `backend/app/orchestration/graph_rag.py` | `record_rag_cost()` after retrieval |
| Spine Orchestrator | `backend/app/signals/spine_orchestrator.py` | `record_aurora_cost(tier="l3_full_core")` |
| L4 Async | `backend/app/aurora/runtime_v1/l4_async.py` | `record_aurora_cost(tier="l4_async")` |

### 2.2 What is MISSING

| # | Gap | Severity |
|---|-----|----------|
| G1 | No pre-execution cost estimate before LLM API calls | Critical |
| G2 | Fragmented pricing data across 4+ files with inconsistent values | Critical |
| G3 | No RAG cost estimation model | High |
| G4 | No Aurora per-user daily cost projection | High |
| G5 | No P4 evaluation cost model | High |
| G6 | No per-request cost gate (only daily aggregate breaker) | Medium |
| G7 | No prediction-vs-actual accuracy tracking | Medium |
| G8 | No CLI "what-if" cost tool | Low |

### 2.3 Pricing Inconsistency

Pricing for the same model/tier differs across files. `cost_controller.py` uses tier-based blended rates while `llm_router.py` uses per-model exact rates. These must be consolidated into a single source of truth.

---

## 3. Cost Model

### 3.1 Unified Pricing Registry

Create `backend/app/core/cost_pricing.py` as the **single source of truth** for all AI pricing.

**LLM Pricing** (per 1K tokens, input and output separate):

| model_key | Provider | Input $/1K | Output $/1K | Tier |
|-----------|----------|-----------|-------------|------|
| xiaomi_chat | xiaomi | 0.0001 | 0.0001 | fast |
| xiaomi_standard_thinking | xiaomi | 0.0001 | 0.0002 | standard |
| mimo_pro | xiaomi | 0.0010 | 0.0020 | max |
| deepseek_fast | deepseek | 0.0001 | 0.0002 | fast |
| deepseek_chat | deepseek | 0.0002 | 0.0004 | standard |
| deepseek_reason | deepseek | 0.0020 | 0.0080 | max |
| glm_4_7_no_thinking | zhipu | 0.0005 | 0.0010 | glm_batch |
| glm_4_7_thinking | zhipu | 0.0010 | 0.0020 | glm_batch |
| glm_4_5_air_batch | zhipu | 0.0002 | 0.0004 | glm_batch |
| glm_4_6_batch | zhipu | 0.0003 | 0.0006 | glm_batch |
| glm_4_7_flash_no_thinking | zhipu | 0.0000 | 0.0001 | fast |
| glm_4_7_flash_thinking | zhipu | 0.0000 | 0.0005 | free_fast |
| glm_4_5_air_free | zhipu | 0.0000 | 0.0002 | free_fast |
| glm_5_max | zhipu | 0.0020 | 0.0040 | max |
| glm_4_7_plus | zhipu | 0.0004 | 0.0008 | plus |
| glm_4_7_pro | zhipu | 0.0010 | 0.0020 | pro |
| glm_5_1_top | zhipu | 0.0040 | 0.0080 | top |
| siliconflow_free | siliconflow | 0.0000 | 0.0000 | free |
| hunyuan_translation | hunyuan | 0.0001 | 0.0001 | fast |
| qwen3_max | dashscope | 0.0020 | 0.0060 | max |
| qwen3_plus | dashscope | 0.0008 | 0.0020 | plus |

**Tier-based fallback pricing** (used when exact model not matched):

| Tier | Input $/1K | Output $/1K |
|------|-----------|-------------|
| free | 0.0 | 0.0 |
| free_fast | 0.0 | 0.00005 |
| fast | 0.0001 | 0.0002 |
| standard | 0.0003 | 0.0005 |
| plus | 0.0008 | 0.0015 |
| pro | 0.0015 | 0.0030 |
| reasoning | 0.0030 | 0.0080 |
| max | 0.0050 | 0.0150 |
| top | 0.0080 | 0.0200 |

**RAG Pricing** (per operation):
- `embedding_generate`: $0.0001 per 1K tokens
- `pgvector_search`: $0.0001 per search
- `redis_hybrid_search`: $0.00005 per search
- `graphrag_retrieve`: $0.0002 per graph hop
- `rerank_call`: $0.00005 per rerank invocation
- `chunk_enrichment`: $0.00002 per contextual enrichment

**Aurora Pricing** (per tier invocation):
- `l0_rule`: $0.0 (free)
- `l1_light`: $0.0001
- `l2_mid`: $0.001
- `l3_full_core`: $0.005
- `l4_async`: $0.01

**P4 Evaluation Pricing** (per stage):
- `baseline_inference`: $0.0005 per variant
- `counterfactual_pass`: $0.002 per counterfactual pass
- `outcome_comparison`: $0.0002 per outcome pair
- `summary_generation`: $0.001 per report

---

## 4. Prediction Framework

### 4.1 Architecture

Create `backend/app/core/cost_predictor.py` with:

- `predict_llm_cost(model_key, prompt_tokens, max_output_tokens)` → float USD
- `estimate_rag_cost(embedding_tokens, vector_searches, graph_hops, rerank_calls, enrich_chunks)` → float USD
- `estimate_aurora_daily_cost(tier, daily_invocations, user_count)` → float USD
- `estimate_p4_cost(num_variants, num_counterfactuals, stages)` → float USD
- `estimate_tokens_from_text(text, is_chinese_heavy)` → int (token estimator with 1.2x safety margin)
- `track_prediction_accuracy(category, model_key, predicted, actual)` → None (records metrics)
- `CostPredictionGate(per_request_threshold_usd, mode)` → per-request gate (block/warn/off)

Prometheus metrics:
- `sparkle_cost_prediction_total` (Counter, by category/model)
- `sparkle_cost_prediction_accuracy_ratio` (Histogram)
- `sparkle_cost_prediction_over_estimate_total` (Counter)
- `sparkle_cost_prediction_under_estimate_total` (Counter)

### 4.2 Integration Points

| Integration Point | File | What Changes |
|---|---|---|
| LLM chat (with tools) | `llm_service.py` ~L1080 | predict before API call, track accuracy after response |
| LLM stream chat | `llm_service.py` ~L1330 | same pattern |
| LLM tool results | `llm_service.py` ~L1190 | same pattern |
| GraphRAG retrieval | `graph_rag.py` ~L2220 | predict RAG cost before, track after |
| Aurora L3 core | `spine_orchestrator.py` ~L3648 | predict before, track after |
| Aurora L4 async | `l4_async.py` ~L206 | predict before, track after |

### 4.3 Prediction Uses Upper-Bound Output Tokens

`predict_llm_cost()` uses `max_output_tokens` (not estimated actual) for worst-case cost prediction. This is intentionally conservative for a cost guard. The accuracy metric tracks the conservatism ratio.

---

## 5. File Inventory

### Files to Create

| File | Purpose |
|------|---------|
| `backend/app/core/cost_pricing.py` | Unified pricing registry — single source of truth |
| `backend/app/core/cost_predictor.py` | Prediction framework with Prometheus metrics |
| `backend/tests/unit/core/test_cost_pricing.py` | Pricing registry completeness and consistency tests |
| `backend/tests/unit/core/test_cost_predictor.py` | Predictor unit tests |
| `backend/tests/integration/test_cost_prediction_integration.py` | Integration tests |

### Files to Modify

| File | Change |
|------|--------|
| `backend/app/core/cost_controller.py` | Replace inline pricing dicts with imports from `cost_pricing.py`. Add `track_prediction_accuracy()` call after each `record_*`. |
| `backend/app/core/llm_router.py` | Replace per-ModelConfig hardcoded prices with references to `cost_pricing.LLM_PRICING`. |
| `backend/app/core/llm_quota.py` | Replace inline `pricing` dict with import from `cost_pricing.py`. |
| `backend/app/core/llm_monitoring.py` | Replace inline `pricing` dict with import from `cost_pricing.py`. |
| `backend/app/services/llm_service.py` | Add `predict_llm_cost()` before API calls (3 points). Add `track_prediction_accuracy()` after `record_llm_cost()`. |
| `backend/app/orchestration/graph_rag.py` | Add `estimate_rag_cost()` before retrieval. Add `track_prediction_accuracy()` after `record_rag_cost()`. |
| `backend/app/signals/spine_orchestrator.py` | Add Aurora cost prediction before L3 execution. |
| `backend/app/aurora/runtime_v1/l4_async.py` | Add Aurora cost prediction before L4 execution. |
| `backend/app/config/settings.py` | Add `COST_PREDICTION_ENABLED`, `COST_PER_REQUEST_THRESHOLD_USD`, `COST_GATE_MODE` settings. |

---

## 6. Implementation Steps

### Phase 1: Unified Pricing Registry (1-2 days)
1. Create `cost_pricing.py` with full pricing registry
2. Update `cost_controller.py` to import from `cost_pricing.py`
3. Update `llm_router.py` to reference `cost_pricing.py`
4. Update `llm_quota.py` and `llm_monitoring.py`
5. Run all existing tests to verify no regression

### Phase 2: Cost Predictor Core (1-2 days)
1. Create `cost_predictor.py` with all prediction functions
2. Add settings (`COST_PREDICTION_ENABLED`, etc.)
3. Create unit tests for predictor and pricing registry

### Phase 3: Integration (1-2 days)
1. Wire prediction into `llm_service.py` (3 integration points)
2. Wire prediction into RAG, Aurora paths
3. Add prediction callback to `cost_controller.py`

### Phase 4: Dashboards & Alerts (1 day)
1. Add Prometheus recording rules for prediction accuracy
2. Add `CostPredictionDrift` alert rule

### Phase 5: Release Gate Integration (0.5 day)
1. Wire `CostPredictionGate` into release gate runner as P2 warning

---

## 7. Test Plan

### Unit Tests — `test_cost_pricing.py` (9 tests)
- All router models have pricing entries
- Tier pricing is monotonic (higher tier = higher price)
- Known model returns correct price
- Unknown model falls back to tier-based pricing
- RAG/Aurora/P4 pricing positive (except L0 free)
- No negative prices anywhere

### Unit Tests — `test_cost_predictor.py` (18 tests)
- LLM cost prediction for known/unknown models
- Free tier predicts $0.00
- Zero tokens predicts $0.00
- RAG/Aurora/P4 cost estimation with known inputs
- CostPredictionGate: block/warn/off modes
- Token estimation within 30% margin
- Prediction accuracy metric recording
- Zero actual cost skips recording (no division by zero)

### Integration Tests (5 tests)
- Full predict → execute → record → accuracy track flow
- Prometheus metric emission
- Existing cost recording still works after migration
- Pricing consistency across all files
- BudgetCircuitBreaker integration

### Existing Tests Must Pass
```bash
cd backend && pytest tests/unit/test_cost_prediction_accuracy.py -v
cd backend && pytest tests/ -k "llm" -v
cd backend && pytest tests/unit/core/ -v --timeout=30
```

---

## 8. Acceptance Criteria

### P0 — Must Have (Blocking)
- [ ] `cost_pricing.py` exists with unified pricing for all 18+ LLM models, RAG ops, Aurora tiers, P4 stages
- [ ] `cost_controller.py`, `llm_router.py`, `llm_quota.py`, `llm_monitoring.py` all import from `cost_pricing.py`
- [ ] `predict_llm_cost()` returns cost within 20% of actual for known models
- [ ] `estimate_rag_cost()` covers all RAG operations
- [ ] `estimate_aurora_daily_cost()` projects daily cost per tier
- [ ] `track_prediction_accuracy()` called after every `record_llm_cost()`
- [ ] All existing tests pass after pricing migration

### P1 — Should Have
- [ ] `CostPredictionGate` with block/warn/off modes
- [ ] Integration tests verify prediction → execution → accuracy tracking flow
- [ ] Prediction accuracy Prometheus metrics emitted
- [ ] Cost prediction alert fires when accuracy ratio exceeds 2.0x for 1 hour

### P2 — Nice to Have
- [ ] CLI "what-if" script: `python3 scripts/cost_what_if.py --model deepseek_chat --prompt "..." --max-tokens 2048`
- [ ] Prediction data used in release gate as P2 warning
- [ ] Grafana dashboard panel for prediction accuracy

---

## 9. Design Decisions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| DD1 | Separate pricing registry from cost controller | New `cost_pricing.py` file | Pricing is static config; cost controller is budget enforcement. Separating eliminates 4-file drift. |
| DD2 | No dynamic pricing from provider APIs | Static registry in file | Most providers don't expose pricing APIs. Static file is auditable in version control. |
| DD3 | Pre-execution prediction uses upper-bound output tokens | Use `max_output_tokens` | Safety: predict worst-case cost. Accuracy metric tracks conservatism ratio. |
| DD4 | CostPredictionGate is warn-by-default | `COST_GATE_MODE = "warn"` | Avoids blocking legitimate high-value calls. Gather data first, tune thresholds later. |
| DD5 | Prediction inside llm_service, not orchestrator | llm_service has model config and prompt | Avoids duplicating model resolution logic in orchestrator. |
| DD6 | Token tracker stays separate from cost predictor | Different concerns, different Redis keys | TokenTracker records actuals; CostPredictor estimates. Different data flows. |
| DD7 | Feature-flagged with kill switch | `COST_PREDICTION_ENABLED` setting | Setting to `False` restores pre-prediction behavior with zero code changes. |

---

## 10. Dependencies

### Internal
- `cost_controller.py` — must import from `cost_pricing.py` (low risk, identical values)
- `llm_router.py` — per-model prices must match (verify in tests)
- `llm_service.py` — add prediction call before API request (medium risk, must not break flow)
- `graph_rag.py`, `spine_orchestrator.py`, `l4_async.py` — same prediction pattern
- GAP-P4-1 (Release Gate) — cost prediction gate as P2 warning check

### External
None. No new pip packages, no new services. All stdlib + existing Prometheus client.

---

## 11. Open Questions

1. **How to source per-model pricing initially?** Use existing `cost_per_1k_tokens` values from `llm_router.py` as baseline (most recently maintained). Cross-reference with provider docs. Mark uncertain prices with confidence notes.
2. **Fetch pricing from provider APIs at startup?** Not in Phase 1. Add `refresh_pricing()` later if provider APIs become available.
3. **Acceptable prediction error threshold?** 50% for warning, 200% for alert. Uses upper-bound tokens so predictions are conservative by design.
4. **Predict cost at orchestrator level for model selection?** Not in this spec. Cost-aware routing is a separate optimization feature.
5. **Streaming cost prediction?** Use `max_tokens` for pre-stream prediction. Accuracy ratio will be higher for streaming — expected and acceptable.
6. **Feature flag for cost prediction?** Yes — `COST_PREDICTION_ENABLED: bool = True` in settings.
7. **Historical prediction data storage?** Prometheus metrics only in Phase 1. Add Postgres `cost_prediction_log` table later if needed.
8. **Embedding/rerank token mapping?** Use `estimate_tokens_from_text()` on input text. Track actual token counts if provider API returns them.

---

*Spec generated 2026-05-06 by Claude Opus Plan Agent*
*GAP-P4-2: 成本预测框架 -- OBS-013*
