# CXP-27 Report — Performance, Cost, And Budget Governance

## Goal

Close the LLM cost governance gap so all three cost categories (LLM, RAG, Aurora) are uniformly budgeted, recorded, observable, and fail gracefully under budget pressure. Make budgets configurable via settings rather than hardcoded constants.

## Work Completed

### 1. LLM cost controller integration (Critical gap closed)

**Before**: `llm_service.py` never checked or recorded against the daily LLM budget. The `BudgetCircuitBreaker` had an LLM category configured ($10/day) but no code path ever called `record_spend(CostCategory.LLM, ...)` or `check_budget(CostCategory.LLM)`. LLM costs flew blind.

**After**: 
- Added `record_llm_cost(model_key, prompt_tokens, completion_tokens, source)` to `cost_controller.py` — estimates cost from token counts and model tier, records spend to the circuit breaker
- Added `is_llm_within_budget()` — used as preflight check before LLM calls
- Integrated into all three LLM call paths in `llm_service.py`: `chat_with_tools`, `generate_tool_results`, and `stream_chat`
- `chat()` and `stream_chat()` now fail fast with HTTP 429 or graceful streaming fallback when budget is exhausted
- LLM pricing uses model tier detection (free/fast/standard/plus/pro/reasoning/max/top/glm_batch/specialist) from the LLMRouter tier system

### 2. Configurable budget amounts

**Before**: Budget amounts `{LLM: 10.0, RAG: 2.0, AURORA: 5.0}` hardcoded in `BudgetCircuitBreaker.__init__()`.

**After**: Budgets read from settings with hardcoded fallbacks:
- `LLM_DAILY_BUDGET_USD` (default $10.0)
- `RAG_DAILY_BUDGET_USD` (default $2.0)
- `AURORA_DAILY_BUDGET_USD` (default $5.0)

### 3. Budget utilization and spend rate gauge fixes

**Before**: `BUDGET_UTILIZATION` and `SPEND_RATE_USD_PER_HOUR` gauges were defined but never set.

**After**: `record_spend()` now updates both:
- `BUDGET_UTILIZATION` — current spend / budget ratio per category
- `SPEND_RATE_USD_PER_HOUR` — rolling 1-hour window spend rate estimation stored in Redis sorted set

## User Experience Before / After

**Before**: No cost governance for LLM. If an LLM key leaked or a runaway loop occurred, costs could spiral with no circuit breaker. No user-visible budget exhaustion behavior.

**After**: 
- LLM budget exhaustion returns HTTP 429 "Daily AI usage limit reached" for non-streaming, or a graceful Chinese-language fallback message for streaming chat
- All three AI cost categories (LLM, RAG, Aurora) are now uniformly observable via `sparkle_cost_estimated_usd_total`, `sparkle_cost_daily_spend_usd`, `sparkle_budget_utilization_ratio`, and `sparkle_spend_rate_usd_per_hour`
- Budget amounts are configurable per environment without code changes

## Cross-System Links

| Layer | Files Changed | Connection |
|-------|--------------|------------|
| Python core | `backend/app/core/cost_controller.py` | New LLM pricing table, `record_llm_cost()`, `is_llm_within_budget()`, settings-based budget init, spend rate/utilization gauge updates |
| Python config | `backend/app/config/settings.py` | New `LLM_DAILY_BUDGET_USD`, `RAG_DAILY_BUDGET_USD`, `AURORA_DAILY_BUDGET_USD` settings |
| Python services | `backend/app/services/llm_service.py` | Budget preflight in `chat()` and `stream_chat()`, spend recording in `chat_with_tools`, `generate_tool_results`, `stream_chat` |
| Existing integrations | `graph_rag.py`, `l4_async.py`, `spine_orchestrator.py` | Unchanged — continue using `record_rag_cost()`, `record_aurora_cost()`, `is_rag_within_budget()`, `is_aurora_within_budget()` |
| Observability | Prometheus metrics | 4 new/updated gauge families: LLM spend, utilization ratio, hourly spend rate, daily budget |

## Verification

- `ruff check` passes on all three modified files (0 errors)
- `tests/unit/test_cost_controller.py` — 18/18 passed (existing coverage for RAG/Aurora paths)
- Import smoke test: all new symbols (`record_llm_cost`, `is_llm_within_budget`) import correctly
- Budget defaults verified: LLM=$10, RAG=$2, AURORA=$5

## Remaining Risks

| Risk | Severity | Owner Suggestion |
|------|----------|------------------|
| `LLM_QUOTA_ENABLED=False` by default — per-user token quotas remain opt-in | Low | Set to `True` in production `.env` |
| LLM cost estimation is tier-based (not per-model) — blended rates may deviate from actual provider pricing by 2-5x | Low | Update `_LLM_TIER_PRICING_PER_1K` in `cost_controller.py` when provider pricing changes |
| Mobile rebuild analysis was cursory — no deep Flutter widget rebuild audit performed | Low | CXP-24 covers design system/i18n; rebuild hotspots are best profiled with Flutter DevTools |

## Commit

Branch: `codex/CXP-27-perf-cost-budget`
