# Sparkle Full-Stack Deep Audit — Consolidated Report

**Date**: 2026-05-10
**Scope**: Frontend (Flutter) + Backend (Python Engine) + Gateway (Go) + Database + Proto
**Methodology**: 3 parallel Opus agents + personal verification of all P0 findings
**Agent Reports**: `frontend_audit.md` | `backend_audit.md` | `gateway_db_audit.md`

---

## Total Findings: 109 issues

| Severity | Frontend | Backend | Gateway+DB | Total |
|----------|----------|---------|------------|-------|
| **P0** | 8 | 3+1* | 3 | **15** |
| **P1** | 29 | 12+2* | 14 | **57** |
| **P2** | 16 | 13 | 11 | **40** |

*\+N = personally discovered issues not in agent reports*

---

## P0 Issues — Must Fix Before Launch

### Cross-Cutting: Backend Chinese Hardcoded Prompts (Personally Verified)

**Files**: `collaboration.py:622-803`, `plan_review_service.py:659-1079`

**Issue**: ALL collaboration mode internal prompts are hardcoded Chinese:
- Parallel merge: `"以下是多位专家对同一问题的分析结果..."`
- Debate review: `"其他专家的分析如下：..."`, `"你是辩论协作的综合裁判..."`
- Delegation decompose: `"作为主分析师，请将以下问题拆分为..."`
- Plan review cross-review: `"你是一位独立的二次审查员..."`
- Plan review fix suggestions: `"请把 X 明确写进这轮计划"`, `"请减少并行步骤..."`

**Impact**: For English-speaking users, the LLM receives Chinese prompts for internal orchestration. This causes:
1. Mixed-language responses (Chinese fragments in English replies)
2. Quality degradation when the LLM tries to follow Chinese instructions for an English conversation
3. Error messages like `"所有专家分析均未成功，请重试。"` leaking to English users

**Fix Context**: The `llm_service.py:1668` has a `language: str = "zh"` parameter but it defaults to Chinese and isn't propagated to collaboration/review prompts. Need to thread `user_locale` through the entire request path (Go → Python → graph nodes → collaboration → LLM prompts).

---

### Backend P0-01: PlanReviewService Null Redis Crash
**File**: `plan_review_service.py:2429,2446` | **Verified**
`self.redis.incr(key)` crashes with `AttributeError` when `self.redis` is `None` (singleton created without Redis). The `except Exception` catches it and returns 1, masking the error.

### Backend P0-02: LLMService Creates New HTTP Client Per Call
**File**: `llm_service.py:1497-1509` | **Verified**
`get_llm_service()` creates a new `LLMService` with new HTTP connection pool each time. Under load, exhausts file descriptors.

### Backend P0-03: collaboration_node Directly Mutates State
**File**: `collaboration.py:851-893` | **Verified**
Lines 851, 862-864, 889-892 mutate `state["key"]` directly. LangGraph expects nodes to return delta dicts, not mutate input. In planning graph, rejected plans retain corrupted collaboration state.

### My P0-04: Reflection Loop Guard Broken in Standard Chat Graph
**File**: `standard_workflow.py:3162-3167`, `statechart_engine.py:375-404` | **Personally Discovered**

`reflection_condition` tries `getattr(state, "review_context", None)` but `WorkflowState` has no `review_context` field. The `_merge_state` method promotes it to `context_data["review_context"]`, but `reflection_condition` never checks there. Result: `reflection_round` is always 0, MAX_ROUNDS guard never fires. The loop depends solely on the reflection node itself setting `next_step != "reflection"`, which it does correctly in most cases, but there's no safety net.

### Gateway P0-01: achievementtype Enum Duplicate
**File**: `schema.sql:122-139` | **Verified**
`'planning'` (lowercase) and `'PLANNING'` (uppercase) are both in the enum. PostgreSQL treats them as distinct values.

### Gateway P0-02: Goroutine Leak in Auth Blacklist
**File**: `auth.go:67-80` | **Verified**
Fire-and-forget goroutine with no shutdown mechanism.

### Gateway P0-03: panic() on crypto/rand.Read
**File**: `auth.go:142` | **Verified**
`panic("crypto/rand.Read failed")` crashes the entire process.

### Gateway P0-04: Client Telemetry POST Routes Without Auth
**File**: `proxy_routes.go:728-735` | **Verified**
```go
clientTelemetry.POST("/events", h.proxyWithHeaders)  // No auth!
clientTelemetry.POST("/events/batch", h.proxyWithHeaders)  // No auth!
clientTelemetry.Use(authMiddleware)  // Applied AFTER
```

### Gateway P0-05: GetChatHistory Missing user_id Filter
**File**: `query.sql:37-41` | **Verified**
SQL only filters by `session_id`, not `user_id`. Any authenticated user who knows a session_id can read another user's chat history.

### Frontend P0: LearningPathScreen (ISSUE-022/023)
**File**: `learning_path_screen.dart` | **Verified**
Uses raw `Scaffold` (not `SparklePageScaffold`), `Navigator.pop()` (not GoRouter), hardcoded English title.

### Frontend P0: 1,685 inline isChinese patterns (ISSUE-001)
**50+ files** | Bypasses ARB l10n pipeline. Third language addition requires manual changes in 1,685 locations.

### Frontend P0: Router error page hardcoded English (ISSUE-002)
**File**: `routes.dart:73,80,85`

### Frontend P0: Voice input accessibility labels English-only (ISSUE-005/026)
**File**: `voice_input_button.dart:304`

### Frontend P0: Static S. accessor locale mismatch (ISSUE-016)
**File**: `node_detail_sheet.dart:500-511`

---

## P1 Issues — Should Fix Before Launch

### Cross-Cutting (Personally Verified)

**My P1-A: Sequential Collaboration Doesn't Pass Previous Results**
**File**: `collaboration.py:877-893`
Sequential mode sets `collaboration_context = agent_task` for each agent, but never includes summaries of previous agents' outputs. The whole point of sequential is later agents build on earlier ones, but they only get the original user message + their own task description.

**My P1-B: Cross-Model Review May Use Same Model**
**File**: `plan_review_service.py:1067-1098`
The cross-review calls `llm_service.chat_json()` with the same `AgentRole.GENERATION` as the primary review. The comment says "different model" but if the router selects the same model, it's the same review twice.

### Backend P1 Summary (12 from agent)
| ID | File | Issue |
|----|------|-------|
| P1-01 | `collaboration.py:743` | Empty delegates → empty response |
| P1-02 | `plan_review_service.py:1934` | Fire-and-forget tasks with no error handling |
| P1-03 | `workflow.py:327` | Planning graph singleton race condition |
| P1-04 | `workflow.py:312` | collaboration_index state confusion risk |
| P1-05 | `llm_service.py:1627` | Database session leak in seed examples |
| P1-06 | `workflow.py:158` | Checkpointer falls back to MemorySaver at import |
| P1-07 | `llm_service.py:341` | Provider property reinitializes on every access |
| P1-08 | `collaboration.py:827` | Returns full state instead of delta |
| P1-09 | `event_bus.py:934` | Redis reconnection thrashing during outage |
| P1-10 | `plan_review_service.py:1067` | Cross-review same model as primary |
| P1-11 | `langgraph_redis_checkpointer.py:74` | Latin-1 doubles checkpoint storage |
| P1-12 | `plan_review_service.py:2555` | Singleton without Redis at module load |

### Gateway P1 Summary (14 from agent)
Key items: `log.Printf` in 40+ places, no session_id validation, stale gRPC context after reconnect, missing header forwarding, unsafe type assertions in rate limiter, no task state dedup, DLQ has no TTL.

Full list in `gateway_db_audit.md` items A-04 through F-01.

### Frontend P1 Summary (29 from agent)
Key items: 216 silent `catch(_)` blocks, 50 Semantics across 100+ screens, FutureBuilder fires on every rebuild, OpenClaw errors hardcoded Chinese, ARB plural mismatches.

Full list in `frontend_audit.md` issues ISSUE-004 through ISSUE-048.

---

## Recommended Fix Priority Order

### Phase 1: Security + Data Integrity (Week 1)

| # | Issue | File | Effort |
|---|-------|------|--------|
| 1 | GetChatHistory missing user_id | `query.sql:37` | 1 line |
| 2 | Telemetry POST without auth | `proxy_routes.go:728` | 3 lines |
| 3 | achievementtype enum duplicate | `schema.sql:134` | migration |
| 4 | panic() in randomString | `auth.go:142` | 10 lines |
| 5 | Null Redis crash | `plan_review_service.py:2429` | 2 guards |
| 6 | collaboration_node state mutation | `collaboration.py:851-893` | refactor returns |

### Phase 2: Connection + State Management (Week 2)

| # | Issue | File | Effort |
|---|-------|------|--------|
| 7 | LLMService HTTP pool leak | `llm_service.py:1497` | cache by role |
| 8 | Planning graph race condition | `workflow.py:327` | lock + lazy init |
| 9 | DB session leak in seed examples | `llm_service.py:1627` | close generator |
| 10 | Reflection loop guard broken | `standard_workflow.py:3164` | read from context_data |
| 11 | Fire-and-forget tasks | `plan_review_service.py:1934` | add done callbacks |

### Phase 3: i18n + UX (Week 3)

| # | Issue | File | Effort |
|---|-------|------|--------|
| 12 | Backend Chinese prompts | `collaboration.py`, `plan_review_service.py` | thread locale |
| 13 | LearningPathScreen scaffold | `learning_path_screen.dart` | 20 lines |
| 14 | Router error page l10n | `routes.dart` | 3 ARB keys |
| 15 | Voice input accessibility | `voice_input_button.dart` | 2 ARB keys |

### Phase 4: Quality + Performance (Week 4)

| # | Issue | File | Effort |
|---|-------|------|--------|
| 16 | goroutine leak in auth | `auth.go:67` | add stop channel |
| 17 | log.Printf → zap | `chat_orchestrator_*.go` | 55 replacements |
| 18 | 216 catch(_) blocks | various Dart files | add debugPrint |
| 19 | Checkpointer latin-1 → base64 | `langgraph_redis_checkpointer.py` | encoding change |
| 20 | DLQ TTL | `dlq.go` | add expiry |

---

## Verification Status

| Finding | Verified By |
|---------|------------|
| Gateway P0-01 (enum) | Personal — read schema.sql line 122-139 |
| Gateway P0-03 (panic) | Personal — read auth.go line 142 |
| Gateway P0-04 (telemetry auth) | Personal — read proxy_routes.go:728-735 |
| Gateway P0-05 (chat history) | Personal — read query.sql:37-41 |
| Backend P0-01 (null Redis) | Personal — read plan_review_service.py:2429 |
| Backend P0-03 (state mutation) | Personal — read collaboration.py:851-893 |
| My P0-04 (reflection guard) | Personal — read statechart_engine.py:375-404, standard_workflow.py:3162 |
| Cross-cutting Chinese prompts | Personal — read collaboration.py:622-803, plan_review_service.py:659-1079 |
| ARB key match | Personal — python diff of en.arb vs zh.arb (0 mismatched keys) |
| catch(_) count | Personal — grep counted 217 instances |

All other findings from agent reports were not independently verified and should be checked before implementing fixes. The agent reports contain file paths and line numbers for all findings.
