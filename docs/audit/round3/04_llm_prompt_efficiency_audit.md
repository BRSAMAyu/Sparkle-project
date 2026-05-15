# Round 3 Audit: LLM Prompt Assembly Efficiency

**Date**: 2026-05-15
**Auditor**: Deep Audit Agent (Round 3)
**Scope**: Token budget, prompt redundancy, Aurora decision loop, context pruning, LLM router strategy
**Files Audited**:
- `backend/app/orchestration/prompts.py` (4589 lines)
- `backend/app/aurora/runtime_v1/decision_loop.py` (1834 lines)
- `backend/app/orchestration/context_pruner.py` (342 lines)
- `backend/app/core/llm_router.py` (1232 lines)
- `backend/app/core/agent_profiles.py` (842 lines)
- `backend/app/core/complexity_analyzer.py` (168 lines)
- `backend/app/orchestration/aurora_language_principles.py` (264 lines)

---

## 1. Token Budget Audit

### 1.1 Tier-Based Budget Configuration

The system defines 6 model tiers with prompt token budgets (`_TIER_PROMPT_BUDGET`, lines 69-76):

| Tier | Budget (tokens) | Typical Context Window | Budget as % of Window |
|------|----------------|----------------------|----------------------|
| `free_fast` | 1,500 | 8K-32K | 4.7%-18.8% |
| `fast` | 2,000 | 32K-128K | 1.6%-6.3% |
| `standard` | 4,000 | 32K-128K | 3.1%-12.5% |
| `reasoning` | 4,000 | 64K-128K | 3.1%-6.3% |
| `free_reasoning` | 3,000 | 8K-32K | 9.4%-37.5% |
| `glm_batch` | 4,000 | 32K-128K | 3.1%-12.5% |

**Finding P1-01: Budgets are conservatively reasonable but lack dynamic scaling.**

- The budgets represent only 1.6%-12.5% of typical context windows, leaving ample room for conversation history and output. This is **safe** but potentially **wasteful** -- the system discards useful context that could fit.
- There is no dynamic scaling based on conversation length: a 5-message session and a 50-message session get the same prompt budget, even though the 5-message session has more spare context window.
- The `PROMPT_SECTION_SOFT_LIMIT_TOKENS` fallback of 4,000 applies when model_key cannot resolve a tier, which is reasonable.

**Finding P1-02: Section-level budget ratios are well-structured but may be too granular for low-budget tiers.**

The `_SECTION_BUDGET_RATIO` dict (lines 78-108) defines 28 sections with `(min_tokens, max_ratio)` pairs. At the `free_fast` tier (1,500 tokens):
- Each section's max allocation is `max(min_tokens, 1500 * ratio)`.
- For `user_context` (min 350, ratio 0.18): gets max(350, 270) = 350 tokens. That is reasonable.
- For `situation_brief_section` (min 140, ratio 0.12): gets max(140, 180) = 180 tokens. OK.
- For `seed_library_section` (min 40, ratio 0.04): gets max(40, 60) = 60 tokens. Very small.
- At 1,500 tokens total, the 28 sections average ~54 tokens each, which is extremely tight.

**Verdict**: The budget system is **well-designed** with 4-level priority (0-3) and progressive truncation. The main gap is the absence of context-window-aware dynamic budgeting.

### 1.3 Token Estimation Accuracy

`_estimate_prompt_tokens()` (lines 135-143) uses a heuristic:
- CJK characters: 1.5 tokens each
- Non-CJK characters: 0.25 tokens each (4 chars per token)

**Finding P1-03: The token estimation is directionally correct but systematically underestimates.**

- Real CJK tokenization is typically 1.0-2.0 tokens per character depending on the tokenizer. The 1.5 average is reasonable.
- For English text, modern tokenizers produce ~0.75 tokens per word (~4 chars), so 0.25 tokens/char is correct for English-dominated content.
- The estimator does not account for special tokens, formatting overhead (Markdown headers, bullet points), or structural markers like `##`, `- `, `**`, which add tokens disproportionately.
- **Risk**: Prompt may exceed budget by 10-20% in practice, since formatting overhead is not counted.

---

## 2. Prompt Redundancy Analysis

### 2.1 Section Inventory

The `build_system_prompt` function assembles **38+ named sections** (from `section_map` at lines 1279-1317):

| # | Section | Priority | Always Present? | Typical Size |
|---|---------|----------|-----------------|-------------|
| 1 | situation_brief_section | 0 (highest) | Conditional | ~140-200 |
| 2 | aurora_language_contract_section | 0 | Always | ~220 |
| 3 | decision_policy_section | 1 | Conditional | ~110 |
| 4 | planning_strategy_section | 1 | Conditional | ~110 |
| 5 | user_material_grounding_section | 1 | Conditional | ~120 |
| 6 | process_scaffolding_section | 1 | Conditional | ~90 |
| 7 | scaffolding_state_section | 1 | Conditional | ~90 |
| 8 | galaxy_snapshot_section | 2 | Conditional | ~120 |
| 9 | idiographic_section | 1 | Conditional | ~90 |
| 10 | intervention_language_contract_section | 1 | Conditional | ~90 |
| 11 | context_briefing_section | 0 | Conditional | ~80 |
| 12 | visible_intelligence_section | 1 | Conditional | ~120 |
| 13 | intent_section | 1 | Conditional (when injected) | ~100 |
| 14 | session_feedback_section | 1 | Conditional | ~60 |
| 15 | user_context | 3 (lowest) | Always | ~350 |
| 16 | preference_instructions | 3 | Always | ~60 |
| 17 | capsule_preference_section | 2 | Conditional | ~40 |
| 18 | plan_context_section | 2 | Conditional | ~200 |
| 19 | dual_core_section | 2 | Conditional | ~80 |
| 20 | understanding_depth_section | 2 | Conditional | ~60 |
| 21 | orchestration_context_section | 2 | Conditional | ~60 |
| 22 | collaboration_narrative_section | 2 | Conditional | ~60 |
| 23 | mode_strategy_section | 2 | Conditional | ~120 |
| 24 | persona_section | 2 | Conditional | ~40 |
| 25 | aurora_profile_section | 1 | Conditional | ~60 |
| 26 | companion_persona_section | 1 | Conditional | ~180 |
| 27 | constitution_guardrail_section | 1 | Conditional | ~60 |
| 28 | agent_persona_section | 2 | Conditional | ~40 |
| 29 | agent_memory_section | 2 | Conditional | ~40 |
| 30 | aurora_planning_sidecar_section | 2 | Conditional | ~100 |
| 31 | cognitive_prism_section | 2-3 | Conditional | ~120 |
| 32 | behavior_pattern_section | 2 | Conditional | ~80 |
| 33 | seed_library_section | 3 | Conditional | ~40 |
| 34 | conversation_history_section | 3 | Always | ~80+ |
| 35 | task_awareness_section | 3 | Always (standard mode) | ~500 |
| 36 | past_session_memory_section | N/A | Conditional | ~100 |
| 37 | output_format_constraints | N/A | Always | ~120 |
| 38 | core_principles (embedded in template) | N/A | Always | ~100 |

### 2.2 Redundancy Findings

**Finding P2-01: User preference information appears in at least 4 places.**

1. `user_context` section: Contains `learning preferences` (depth, curiosity, verbosity, tone)
2. `preference_instructions` section: Rendered preference instructions based on LLM profile
3. `capsule_preference_section`: Capsule-formatted preferences
4. `companion_persona_section`: Includes warmth/candor/challenge parameters derived from preferences
5. `persona_section`: persona_constraints_summary which may repeat preference info

The `_resolve_preference_instructions` function extracts preferences and formats them, but `user_context` already renders the same preference fields in `_render_user_context_content`. This creates redundancy of approximately 100-150 tokens per request.

**Finding P2-02: Task awareness section is always included in standard mode but rarely needed.**

`TASK_AWARENESS_SECTION` (lines 419-462) is a ~500-token static block that lists 22 tools with descriptions. It is appended at priority 3 (lowest) but still consumes significant budget. For a casual conversation ("how are you?"), this section wastes ~500 tokens.

**Recommendation**: Make `task_awareness_section` conditional on intent classification -- only include when the user's query is task/plan-related.

**Finding P2-03: "Core Principles" section is duplicated across all 4 MODE_SYSTEM_PROMPTS.**

The `## Core Principles` block (8 numbered items, ~100 tokens) appears verbatim in `standard`, `deep_analysis`, `study_plan`, and `error_diagnosis` modes. These are generic behavioral rules that could be injected once rather than embedded in each template.

**Finding P2-04: Output format constraints are always appended (line 1659-1666).**

The ~120-token Markdown format constraint block is appended to every response regardless of mode. This is a static section that could be cached or injected conditionally based on model capability (stronger models may not need these constraints).

### 2.3 Section Necessity Analysis

| Category | Always Needed? | Notes |
|----------|---------------|-------|
| **Identity/Context** (user_context, preferences) | Yes | Core personalization |
| **Language Contract** (aurora_language_contract) | Yes | Voice consistency |
| **Task Tools** (task_awareness) | No | Only when tasks relevant |
| **Aurora Sections** (decision_policy, planning_strategy) | No | Only during planning |
| **Safety** (constitution_guardrail) | Yes | Safety enforcement |
| **History** (conversation_history) | Yes | Context continuity |
| **Formatting** (output_format_constraints) | Mostly | Could be conditional |
| **Mode-specific** (deep_analysis, study_plan instructions) | No | Only in respective mode |

---

## 3. Aurora Decision Loop Prompt Audit

### 3.1 System Prompt Analysis

The `AuroraDecisionLoop.build_prompt()` method (lines 862-1094) constructs a 2-message LLM call.

**System message** (lines 895-946): Approximately 850-1000 tokens. Contains:
- Role definition ("You are Aurora's cognitive decision loop")
- Action semantics explanation
- Forbidden domain rules (clinical diagnosis, personality pathology, etc.)
- Domain coverage instructions
- Teaching strategy instructions (7 boolean fields explained)
- Standard layer contract instructions
- Deep pattern alert handling
- Completion check rules
- Sprint Pack node ID rules

**User message** (JSON payload, lines 953-1093): Contains:
- `decision_schema`: JSON schema for output validation (~200 tokens)
- `dashboard_readout`: Slimmed readout payload (variable, ~200-500 tokens)
- `strategy_defaults`: Default strategy flags (~100 tokens)
- `current_strategy`: Current active strategy (~50 tokens)
- `wake_policy`: Wake/sleep policy (~50 tokens)
- `rules`: Dynamic rule list (variable, ~100-400 tokens)
- Conditional rules: achievement signals, deep patterns, sleep guard, stuck task, last-24h mode, spine signals

### 3.2 Redundancy in Decision Loop

**Finding P3-01: System prompt contains significant static instruction that could be split into cached and dynamic portions.**

The system message is ~950 tokens of which:
- ~400 tokens are **static** (role definition, action semantics, forbidden domains) -- never change between requests
- ~300 tokens are **semi-static** (teaching strategy explanations, standard layer contract rules) -- change rarely
- ~250 tokens are **dynamic** (sprint pack hints, recalibration rules) -- change per request

Modern LLMs support **prompt caching** (Anthropic, OpenAI, DeepSeek). The static ~400 tokens could benefit from caching, saving ~$0.0004/request at current pricing for the decision loop alone.

**Finding P3-02: Rule injection is comprehensive but duplicative with post-hoc validation.**

The `rules` array in the user message often contains 8-15 rules (lines 962-1090), many of which duplicate what the `validate_decision()` method (lines 1096-1147) enforces post-hoc:
- "Never request or infer forbidden psychological domains" -- also enforced by `_contains_forbidden_domain()` (line 1162)
- "Always return harness_updates.strategy with all seven boolean fields" -- also enforced by `_merge_strategy_harness_updates()` (line 1601)
- "Always return chat_directive.standard_layer_contract with all four fields" -- also enforced by `build_standard_layer_contract()` (line 785)

This double-enforcement (prompt + code validation) adds ~150-200 tokens to the prompt. While defense-in-depth is good, some rules could be moved to code-only enforcement for token savings.

**Finding P3-03: `max_tokens` for decision output is 320 (compact) or 600 (extended).**

This is tight for JSON output. A typical `AuroraDecision` payload with full `harness_updates.strategy` (7 booleans), `chat_directive` with `standard_layer_contract` (4 fields), and `state_updates` can easily reach 300-400 tokens of JSON. The 320 limit risks truncation.

**Recommendation**: Increase compact mode to 400, extended to 700.

### 3.3 Dynamic Injection Opportunities

| Rule Set | Current | Could Be Dynamic? | Token Savings |
|----------|---------|------------------|---------------|
| Sleep guard rules | Always in rules list | Only when `sleep_guard_active=true` | Already conditional (good) |
| Strategy recalibration | Always appended to system | Only when recalibration needed | Already conditional (good) |
| Last-24h exam mode | Always in rules | Only when sprint_mode=last_24h_cram | Already conditional (good) |
| Achievement signal rules | Always computed | Only when streak/gap/momentum is relevant | Partial -- empty list when no signals |
| Spine signal rules | Always computed | Only when spine signals exist | Already conditional (good) |
| Deep pattern alert rules | Always computed | Only when alerts exist | Already conditional (good) |
| Teaching strategy explanations | Always in system prompt | Only when strategy changes | **Opportunity**: ~200 tokens |

**Verdict**: The decision loop already does good conditional injection. The main savings opportunity is splitting the static system prompt for caching.

---

## 4. Context Pruning Audit

### 4.1 Three-Tier Pruning Strategy

`ContextPruner` (context_pruner.py) implements a 3-tier strategy:

| Tier | Threshold | Strategy | Trigger |
|------|-----------|----------|---------|
| 1 | <= 10 messages | Keep all | Short conversations |
| 2 | <= 30 messages | Importance compression | Medium conversations |
| 3 | > 30 messages | LLM summarization + anchor retention | Long conversations |

### 4.2 Effectiveness Analysis

**Finding P4-01: Tier 2 compression is rule-based and efficient, but keyword lists may miss important context.**

The `_is_high_importance_message()` method (lines 219-230) uses keyword matching with 30+ Chinese keywords. This is fast (<1ms) but:
- Misses important context that doesn't contain these specific keywords
- May retain messages with false positive matches (e.g., "我不觉得焦虑" matches "焦虑" keyword)
- No semantic understanding of message importance

**Finding P4-02: Tier 3 summarization uses a FAST model, which is a good cost/performance trade-off.**

The `_summarize_sync()` method (lines 147-173) uses `AgentRole.RETRIEVAL` + `ModelTier.FAST` for summarization, with:
- Temperature 0.2 (deterministic)
- 100-char limit (tight, good for cost)
- 4-point summary structure (goal, completed, stage, decisions)

This is well-designed. The summary captures the essential information in a compact form.

**Finding P4-03: Redis-based caching prevents re-summarization, but cache invalidation is time-based only.**

Cache key is `sha1(messages_json)[:16]` with 1-hour TTL. This means:
- If the same messages appear in a different session, they get the same summary (correct behavior)
- If messages change (e.g., a message is edited), the cache key changes (correct)
- TTL of 1 hour is reasonable for session-level caching

**Finding P4-04: Anchor message retention is important but the keyword list is narrow.**

`_is_anchor_message()` (lines 232-237) preserves messages containing keywords like "计划已创建", "任务完成", "阶段", "里程碑". This is good for task-oriented conversations but misses:
- User's emotional turning points that don't contain specific keywords
- Important tool results that have non-standard format
- User corrections ("不对，我说的是...")

**Finding P4-05: The `_compress_message()` method may lose nuance.**

For non-high-importance messages:
- Low signal messages (e.g., "好的") are compressed to `"[{role}简述] {content[:40]}..."`
- Messages > 150 chars are truncated to 150 chars + "..."

The 150-char limit is aggressive. A message like "我今天复习了微积分的导数部分，感觉链式法则还不太理解，但是基本求导公式已经记住了" is 35 chars in Chinese but contains both progress and a gap -- truncation might lose the gap.

### 4.3 Critical Context Loss Risk

**Finding P4-06: No mechanism to preserve user-stated constraints across pruning.**

When a user says something like "我这周只有周二周四有时间学习", this is an important scheduling constraint. The current pruning system does not have a "constraint extraction" step -- it relies on keyword matching for importance. If this constraint appears in an older message without keywords like "计划" or "目标", it may be compressed or summarized away.

---

## 5. LLM Router Strategy Audit

### 5.1 Model Tier Architecture

The system defines 12 tiers (agent_profiles.py, ModelTier enum):

```
FREE < FREE_FAST < FREE_REASONING < FAST < STANDARD < PLUS < PRO < REASONING < MAX < TOP < GLM_BATCH < SPECIALIST
```

With 22 registered model configs across 6 providers:
- Xiaomi (3 models: FAST, STANDARD, MAX)
- DeepSeek (3 models: FAST, STANDARD, MAX)
- Zhipu/GLM (8 models: GLM_BATCH, FAST, FREE_FAST, PLUS, PRO, TOP, MAX)
- DashScope/Qwen (4 models: FAST, STANDARD, PLUS, PRO)
- SiliconFlow (3 models: FREE, SPECIALIST)
- Hunyuan (1 model: SPECIALIST)

### 5.2 Routing Strategy Analysis

**Finding P5-01: The Orchestrator uses STANDARD tier for decision loop -- this is appropriate.**

The `_default_llm_factory()` in decision_loop.py (line 1798-1801):
```python
return await get_configured_llm_service(AgentRole.ORCHESTRATOR, TaskType.QUICK_QUERY)
```

`AgentRole.ORCHESTRATOR` maps to `ModelTier.STANDARD` with policy preferring `dashscope_chat`. The `TaskType.QUICK_QUERY` further hints at using a faster model. This is correct -- the decision loop produces structured JSON, not complex prose, so STANDARD is sufficient.

**Finding P5-02: GENERATION agent uses STANDARD tier -- potential overuse for simple responses.**

`AgentRole.GENERATION` uses `ModelTier.STANDARD` for all generation tasks. However, `SIMPLE_CHAT` tasks map to `ModelTier.FAST` via `TASK_TO_AGENT_PROFILE`. The routing correctly differentiates:
- Simple chat / quick queries -> FAST
- Standard responses -> STANDARD
- Deep reasoning / error diagnosis -> PRO

This is well-designed.

**Finding P5-03: EXAM_ORACLE, ERROR_ANALYST, and SCIENCE_AGENT all use PRO tier -- appropriate for their complexity.**

These agents handle exam prediction, root-cause diagnosis, and scientific reasoning. PRO tier (dashscope_reason, deepseek_reason) is appropriate.

**Finding P5-04: STUDY_BUDDY uses FREE_FAST tier -- cost-effective but may produce lower quality.**

Study buddy handles emotional support and light chat. FREE_FAST tier (glm_4_7_flash_thinking, glm_4_5_air_free, siliconflow_free) is appropriate for this role. However, the `glm_4_7_flash_thinking` model has `avg_latency_ms=1200` which is slower than some FAST models. Consider reordering to prefer truly fast models.

**Finding P5-05: Complexity analyzer provides tier delta adjustment but has limited signal coverage.**

`complexity_analyzer.py` assesses message complexity using regex patterns:
- Greetings -> TRIVIAL (delta -2)
- Confirmations -> SIMPLE (delta -1)
- Questions -> MODERATE (delta 0)
- Math/code/science terms -> COMPLEX (delta +1)
- Multi-step indicators -> EXPERT (delta +2)

This is effective for obvious cases but misses:
- Contextual complexity: "帮我看看这道题" is classified SIMPLE but could be COMPLEX depending on the problem
- Emotional complexity: "我又搞砸了" is classified SIMPLE but may require PRO-level emotional intelligence
- Multi-turn complexity: a series of simple messages may build into a complex scenario

### 5.3 Over-Use of High-Tier Models

**Finding P5-06: REVIEWER uses PRO tier for all reviews -- may be overkill for simple content checks.**

The REVIEWER agent always uses PRO tier (deepseek_reason, dashscope_reason). For simple content quality checks (formatting, basic safety), STANDARD or PLUS would suffice. Consider adding complexity-based tier selection for review tasks.

**Finding P5-07: No model tier tracking or budget enforcement at the session level.**

The router selects models per-request but does not track cumulative cost within a session. A user in a long conversation could accumulate significant costs through repeated PRO/MAX tier calls without any budget alert.

---

## 6. Cross-Cutting Findings

### 6.1 Hot Path Token Budget Estimate

For a typical STANDARD tier chat session (4,000 token prompt budget):

| Component | Estimated Tokens | % of Budget |
|-----------|-----------------|-------------|
| Aurora language contract | 220 | 5.5% |
| User context (identity, preferences, knowledge) | 350 | 8.8% |
| Preference instructions | 60 | 1.5% |
| Conversation history | 200 | 5.0% |
| Task awareness section | 500 | 12.5% |
| Output format constraints | 120 | 3.0% |
| Core principles | 100 | 2.5% |
| Mode-specific instructions | 120 | 3.0% |
| Situation brief | 140 | 3.5% |
| Companion persona | 180 | 4.5% |
| Plan context | 200 | 5.0% |
| All other sections (avg) | 500 | 12.5% |
| Template overhead (headers, formatting) | 200 | 5.0% |
| **Total (typical)** | **~2,890** | **72.3%** |
| **Remaining budget** | **~1,110** | **27.8%** |

The system typically uses ~72% of the budget, leaving 28% headroom. This is a healthy margin.

### 6.2 Decision Loop Token Estimate

For a single Aurora decision loop call:

| Component | Estimated Tokens |
|-----------|-----------------|
| System message | ~950 |
| User message (JSON payload) | ~400-800 |
| **Total input** | **~1,350-1,750** |
| Output (decision JSON) | ~300-400 |
| **Total per decision** | **~1,650-2,150** |

At $0.0004/1K tokens (STANDARD tier), each decision loop call costs approximately $0.0007-$0.0009. For a 10-message session with ~3 Aurora decisions, this is ~$0.003.

### 6.3 Full Session Token Flow

For a typical 10-message study session:

| Step | Model | Estimated Tokens | Cost/1K | Est. Cost |
|------|-------|-----------------|---------|-----------|
| Context pruning (if needed) | FAST | 200 in + 100 out | $0.0001 | $0.00003 |
| Aurora decision (x3) | STANDARD | 1,500 in + 350 out | $0.0004 | $0.0022 |
| Main chat response (x10) | STANDARD | 3,000 in + 500 out | $0.0004 | $0.0140 |
| **Session total** | | **~44,000** | | **~$0.016** |

---

## 7. Recommendations

### Priority 1 (High Impact, Low Effort)

| # | Finding | Recommendation | Estimated Savings |
|---|---------|----------------|------------------|
| R1 | P2-02: Task awareness always included | Make `task_awareness_section` conditional on intent classification | ~500 tokens/request for non-task conversations |
| R2 | P3-03: Decision output max_tokens too tight | Increase to 400/700 (compact/extended) | Prevents truncation errors |
| R3 | P1-03: Token estimation undercounts formatting | Add +15% overhead factor to `_estimate_prompt_tokens` | Prevents budget overruns |

### Priority 2 (Medium Impact, Medium Effort)

| # | Finding | Recommendation | Estimated Savings |
|---|---------|----------------|------------------|
| R4 | P2-01: Preference info duplicated 4x | Consolidate preference rendering into single canonical section | ~100-150 tokens/request |
| R5 | P3-01: Decision loop system prompt mostly static | Split into cached prefix + dynamic suffix for prompt caching | ~400 tokens cached (latency + cost) |
| R6 | P4-06: No constraint preservation across pruning | Add constraint extraction step before Tier 3 summarization | Prevents critical context loss |
| R7 | P5-07: No session-level cost tracking | Add session cost accumulator with configurable budget cap | Cost control |

### Priority 3 (Lower Impact, Higher Effort)

| # | Finding | Recommendation | Estimated Savings |
|---|---------|----------------|------------------|
| R8 | P1-01: No dynamic budget scaling | Scale prompt budget based on (context_window - history_tokens) | Better context utilization |
| R9 | P4-01: Keyword-only importance detection | Add simple semantic scoring (e.g., sentence embedding similarity to recent topic) | Better retention decisions |
| R10 | P5-06: REVIEWER always uses PRO | Add task-based tier selection for review tasks | ~50% cost reduction for simple reviews |
| R11 | P2-04: Format constraints always appended | Make conditional on model tier (skip for TOP/MAX models) | ~120 tokens for high-tier models |

---

## 8. Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| **Token Budget Design** | GOOD | 4-tier priority + per-section ratio caps + progressive truncation. Well-structured. |
| **Redundancy** | MODERATE | User preference info duplicated across 4 sections. Task awareness section wasteful for non-task conversations. |
| **Aurora Decision Loop** | GOOD | Conditional rule injection is well-implemented. Main savings from prompt caching and output token limit adjustment. |
| **Context Pruning** | GOOD with gaps | 3-tier strategy is sound. Keyword-based importance detection is limited. Missing constraint preservation. |
| **LLM Router** | GOOD | Tier differentiation is appropriate. Complexity analyzer provides basic routing. Missing session-level budget tracking. |
| **Overall Efficiency** | 72/100 | System is well-designed overall. Main improvements are in conditional section inclusion and prompt caching adoption. |

### Critical Metrics

- **Average prompt utilization**: ~72% of budget (healthy headroom)
- **Estimated cost per 10-message session**: ~$0.016
- **Estimated waste from unconditional sections**: ~500-700 tokens/session
- **Potential savings from recommendations**: ~15-20% token reduction, ~10% cost reduction
