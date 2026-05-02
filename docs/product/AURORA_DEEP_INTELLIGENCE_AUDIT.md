# Aurora Deep Intelligence Audit

**Date**: 2026-05-02
**Scope**: Core intelligence quality of Aurora's AI behavior -- does it genuinely learn, differentiate, close loops, and remember?
**Method**: Static code analysis tracing data flow from signal capture to behavioral effect

---

## Dimension 1: Does Aurora Actually Learn From the User?

**Rating**: GOOD

### What Was Examined

| File | Purpose |
|------|---------|
| `backend/app/aurora/runtime_v1/self_model.py` | Redis-backed strategy calibration model |
| `backend/app/state_aggregator/service.py` | 20-field user state aggregator |
| `backend/app/aurora/runtime_v1/correction_feedback.py` | User correction feedback processor |
| `backend/app/aurora/runtime_v1/write_pipeline.py` | Inference claim lifecycle (observed -> candidate -> trial -> confirmed) |
| `backend/app/services/memory_service.py` | Episodic memory, preferences, goals, corrections |
| `backend/app/orchestration/session_state_mixin.py` | Context assembly with FocusedContextAssembler |

### Evidence of Learning

**1. Self-Model Tracks Real Behavioral Signals (self_model.py)**

The self-model is a Redis-backed document keyed per user (`aurora:self_model:{user_id}`) with 30-day TTL. It contains:

- `strategy_confidence`: A float [0,1] that drifts up (+0.02 on task success) and down (-0.04 on timeout, -0.03 on failure, extra -0.05 after 3 consecutive failures)
- `known_assumptions`: Three assumptions (`daily_available_time`, `task_duration_fit`, `task_difficulty_fit`) each with their own confidence and evidence trail
- `harness_effectiveness`: Context hit rate, task completion rate, user corrections count, task shape (working/partial/struggling)
- `failure_streak`, `timeout_count`: Cumulative counters with decay

The model updates atomically on every `record_task_outcome` and `record_user_correction` call, with idempotency via `processed_signal_ids` (capped at 100 entries).

**2. User Corrections Follow a Full Feedback Loop (correction_feedback.py)**

When a user clicks a disconfirming correction chip, `CorrectionFeedbackProcessor.process()`:

1. Lowers `StateRegister` confidence by 0.15 on affected state keys (lines 465-483)
2. Calls `SparkleSelfModelService.record_user_correction()` which:
   - Decrements `strategy_confidence` by 0.05
   - Detects correction topic via keyword matching (time vs. difficulty)
   - Adjusts matching assumption confidence (-0.08 for time, -0.06 for duration)
3. Persists correction via `AuroraSelfCorrector.apply_correction()`
4. Updates the routing profile via `RoutingProfileService.record_session_outcome()` so future routing behavior changes
5. Feeds the Bayesian learner (`AuroraBayesianLearner.record_correction()`)
6. Persists a calibration receipt to memory service AND working memory

**3. Inference Claims Have a Proper Lifecycle (write_pipeline.py)**

Claims progress through: `observed` -> `candidate` (confidence >= 0.7) -> `trial` (user confirms, 7-day window) -> `confirmed` (auto-promoted after trial period) or `revoked` (user denies).

Key property: `_promote_due_trials_in_memory()` automatically promotes claims that survive their trial window, boosting confidence to 0.9 minimum. Revoked claims are tracked by fingerprint to prevent re-injection.

**4. Self-Model Is Read at Conversation Start (self_model.py:97-116)**

`get_readout_summary()` is called to produce a readout that includes:
- `strategy_confidence` (merged with Bayesian calibration, 40/60 blend)
- `known_assumptions` with confidence and evidence
- `harness_effectiveness` metrics
- `needs_recalibration` flag and reasons
- `task_failure_streak`

This readout feeds into the user context payload consumed by the orchestrator and router.

### Gap Analysis

| Gap | Description | Fix Complexity |
|-----|-------------|----------------|
| **Self-model TTL is 30 days** | After 30 days of inactivity, the self-model resets to defaults. A student who returns after summer break loses all calibration. | S |
| **Correction topic detection is keyword-based** | Lines 241-246 use simple keyword matching (`_TIME_KEYWORDS`, `_DIFFICULTY_KEYWORDS`) to decide which assumption to adjust. If the user says "you're wrong about my stress level" in Chinese, none of the keywords match, so it defaults to adjusting time+duration instead of the actual dimension. | M |
| **No cross-session memory of calibration receipts in LLM prompt** | Calibration receipts are persisted to working memory and Redis list, but the context pruner treats them as regular messages. There is no dedicated "recent corrections" injection into the LLM prompt. | M |
| **Bayesian learner is opaque** | The Bayesian policy calibration blends with self-model confidence at 40/60 ratio (line 732), but the learner's internal model and its training data are not inspectable. | S |

### Key Question Answer

**"If a user tells Aurora 'you're wrong about my stress level' and returns 3 days later, does Aurora remember?"**

Partially yes. The correction flows through `CorrectionFeedbackProcessor` -> `SparkleSelfModelService.record_user_correction()` -> strategy confidence drops by 0.05. However, the correction targets assumptions via keyword matching, and "stress level" does not match any keyword in `_TIME_KEYWORDS` or `_DIFFICULTY_KEYWORDS`, so it defaults to adjusting the `daily_available_time` and `task_duration_fit` assumptions -- not a stress-specific dimension. The self-model TTL of 30 days means the correction persists for 3 days. The calibration receipt is written to working memory and Redis, but whether it surfaces in the next conversation depends on the `FocusedContextAssembler` and context pruner, which have no special handling for calibration receipts.

---

## Dimension 2: Does the Dual-Core Router Make Genuinely Different Decisions?

**Rating**: GOOD

### What Was Examined

| File | Lines | Purpose |
|------|-------|---------|
| `backend/app/orchestration/dual_core_router.py` | 883 lines | Full routing logic |
| `backend/app/orchestration/ux_envelope.py` | 1907 lines | UX presentation layer |

### Routing Architecture

The router produces one of three modes: `execution_first`, `cognitive_first`, or `balanced`. The decision is based on an explicit precedence scoring system (lines 208-217):

| Signal | Precedence Score | Effect |
|--------|-----------------|--------|
| Emotional block | 9.0 | Forces cognitive_first |
| Procrastination pattern | 8.0 | Forces cognitive_first |
| Cognitive mode suggested | 7.0 | Forces cognitive_first |
| Low metacognition accuracy | 6.0 | Forces cognitive_first |
| High cognitive load | 5.0 | Forces cognitive_first |
| Spine fatigue | 4.0 | Can force cognitive_first |
| Reflection phase | 3.0 | Can force cognitive_first |
| Goal clarity | 0.0-1.0 | Supports execution_first |

The router also generates:
- `cognitive_adjustments`: Up to 5 Chinese-language instructions injected into the LLM prompt
- `execution_constraints`: Up to 5 constraints on plan/task generation
- `strategy_adjustments`: Up to 5 structured recommendations (session_mode, explanation_style, difficulty_level, etc.)
- `structured_adjustments`: Typed CognitiveAdjustment objects with dimension/value/reason/evidence

### Scoring Logic Per Dimension

**Emotional Block** (lines 675-691):
- Score based on ratio of negative sentiments in recent distribution
- Boosted to 0.75 if `primary_challenge_area == "emotional"`
- Boosted to 0.6 if >= 2 negative sentiment events
- Boosted to 0.7 if behavior patterns include overload/burnout/anxiety
- Threshold: configurable via `emotional_sensitivity` in routing profile (default 0.5)
- Not binary: continuous score compared to continuous threshold

**Procrastination** (lines 702-722):
- Score based on weighted friction signals (too_long, unclear, irrelevant feedback)
- Boosted to 0.72 if >= 3 "too_difficult" feedbacks
- Boosted to 0.68 if plan health is "critical"
- Boosted to 0.78-0.8 if behavior patterns match procrastination keywords
- Threshold: configurable via `procrastination_threshold` (default 0.6)

**Goal Clarity** (lines 654-663):
- Continuous score based on intent confidence
- Reduced by 30% if intent is not in CLEAR_INTENTS set
- Reduced by 0.1 if procrastination pattern detected
- Reduced by 0.08 if cognitive mode suggested

**Three Distinct Outcomes**: Yes, the router produces genuinely different behavior:
1. `execution_first` (lines 587-609): Only when goal is clear, info is sufficient, AND no blocking signals. Strategy: reduce interruptions, give executable next steps.
2. `cognitive_first` (lines 612-636): When any blocking signal fires. Strategy: handle emotion/procrastination first, calibrate before planning.
3. `balanced` (lines 638-652): When goal is clear but some friction exists. Strategy: advance execution while simultaneously modulating state.

### How Router Output Changes What Users See (ux_envelope.py)

The `DualCoreDecision.prompt_instruction` property (lines 127-143) generates a structured text block that is injected into the LLM system prompt with two sections:
- "## 双核心认知调制" (cognitive adjustments)
- "## 结构化认知调整" (structured adjustments)
- "## 双核心执行约束" (execution constraints)

The UX envelope (lines 320-330) also propagates:
- `dual_core_mode` label to Flutter
- `mode_reason` explanation to Flutter
- `structured_cognitive_adjustments` that are user-visible
- `adaptation_summary` with visible changes
- `session_adaptation` with applied strategy

### Gap Analysis

| Gap | Description | Fix Complexity |
|-----|-------------|---------------|
| **Scoring is additive, not weighted** | The emotional_block_score and procrastination_score are max() operations rather than weighted combinations. Two weak negative sentiments (ratio 0.4) that individually don't trigger emotional_block still don't combine with a procrastination signal to produce a stronger routing shift. | M |
| **No gradient between modes** | The three modes are discrete. There is no "mild cognitive_first" vs "strong cognitive_first". The cognitive_adjustments list varies, but the mode label is binary within each category. | L |
| **Router has no per-user learning** | The routing profile (`procrastination_threshold`, `emotional_sensitivity`, `directness_preference`) is set but the router itself does not adjust these based on outcomes. The Bayesian learner adjusts `strategy_confidence` but not the routing thresholds directly. | M |
| **Max 5 cognitive adjustments** | Hard cap at line 605/635/649. Complex multi-signal situations may drop important adjustments. | XS |

### Key Question Answer

**"If two users have identical messages but different emotional states, does Aurora respond differently?"**

Yes, substantially. If User A has `emotional_block_detected=True` (from emotion_hint aggregator detecting dominant sentiment = "anxious") while User B does not, the router will:
- Route User A to `cognitive_first` (precedence 9.0) vs User B potentially to `execution_first`
- Inject "先处理用户当前的情绪阻力，再进入计划讨论" into User A's LLM prompt
- Recommend `session_mode=recovery`, `intervention_intensity=low` for User A
- The UX envelope will use `companion_frame_variant="warm"` for User A vs default for User B
- User A sees "gentle" blocked_temperature while User B sees "guided"

---

## Dimension 3: Is the 7-Phase Growth Loop Actually Closing?

**Rating**: ADEQUATE

### Phase-by-Phase Service Mapping

| Phase | Primary Service(s) | What It Produces |
|-------|-------------------|------------------|
| **Sense** | `StateAggregatorService` (20 fields), `BehaviorSignalCollectorService`, `ContextFocus.FocusedContextAssembler` | UserStateV1, behavior patterns, focused context |
| **Clarify** | `SufficiencyJudgeService`, `FocusedContextAssembler`, `GoalQualityEvaluator` | Sufficiency score, goal quality assessment |
| **Plan** | `PlanReviewService`, `AdaptiveReplanner`, `CognitivePatternTrigger` | Executable plans with 2-tier review |
| **Execute** | `TaskService`, `ExecutionEngine`, `OpenClaw` adapter | Task CRUD, tool execution |
| **Reflect** | `TaskReflectionService` | LLM-generated reflections, episodic memories |
| **Reinforce** | `AchievementEngine`, `AchievementEventConsumer` | 19 event types, photon rewards, streaks |
| **Adapt** | `AdaptiveReplanner`, `CognitivePatternTrigger`, self-model updates | Plan adjustments, parameter changes |

### Reflect Phase Deep Dive

**Trigger**: `TaskReflectionService` (lines 86-100) triggers reflection when:
- Task feedback categories: TOO_DIFFICULT, UNCLEAR, "abandoned", "intervention_ineffective", "plan_stall", "overload"
- 24-hour cooldown between triggers per plan
- Kill switch controlled (Aurora Stage 25)

**What it produces**:
- LLM-generated reflection prompt via `reflection_agent`
- Episodic memory write via `MemoryInferredWriteLaneService`
- SRL phase event published to event bus
- Rule Y validation before writing
- Task feedback categorized and stored

**Is it automatic?** Partially. Task feedback triggers reflection automatically, but there is no scheduled automatic reflection (e.g., end-of-day reflection without user action). The user must complete or abandon a task first.

### Adapt Phase Deep Dive

**What changes as a result of reflection?**

1. `AdaptiveReplanner` reads behavior patterns, task feedback, and plan health to produce `PlanParameterAdjustment` objects
2. `CognitivePatternTrigger` maps high-confidence cognitive patterns to deterministic plan constraints (max 3 per run, min confidence 0.7)
3. Adjustments are applied via `PlanAdjustmentApplier` which modifies plan parameters
4. Self-model receives task outcome updates (`record_task_outcome`) that change strategy confidence and assumption confidence
5. Inference write pipeline may create new claims from reflection insights

**Does each plan start from scratch?** No. The `AdaptiveReplanner` explicitly reads the existing plan and modifies it. The `CognitivePatternTrigger` reads the user's behavior patterns to constrain new plans. The self-model's assumptions about time/duration/difficulty carry across plans.

### Reinforce Phase Deep Dive

**Is reinforcement just badges?** No. The `AchievementEngine` processes 19 event types including:
- `TaskCompleted` -> photon reward + achievement check
- `TaskAbandoned` -> reflection trigger + pattern analysis (not just a negative signal)
- Achievements have rarity tiers (Common/Rare/Epic/Legendary) with weighted scoring

However, reinforcement does NOT change Aurora's behavior directly. Achievement unlock events do not feed back into the router or prompt assembly. They produce notifications and visual elements but do not adjust cognitive_adjustments or execution_constraints.

### Gap Analysis

| Gap | Description | Fix Complexity |
|-----|-------------|---------------|
| **No automatic reflection without user action** | Reflection requires task feedback or explicit user trigger. There is no end-of-day or end-of-session automatic reflection mechanism. | M |
| **Reinforcement does not close back to routing** | Achievement unlocks and streaks are displayed but do not influence dual-core routing or prompt assembly. A user on a 7-day streak gets the same routing as a user on day 1. | M |
| **Reflect -> Adapt is fire-and-forget for non-plan signals** | Reflection on emotional or cognitive patterns writes episodic memory, but there is no explicit mechanism to check whether the adaptation actually resolved the pattern. | L |
| **SRL phase transitions are not automatic** | The SRL phase tracker records phases but does not automatically trigger phase-appropriate interventions (e.g., transitioning from "forethought" to "performance" does not generate a "start your first task" nudge). | M |

### Key Question Answer

**"After a user completes a task, does the system actually generate learning that affects future plans?"**

Yes, through multiple channels: (1) Self-model updates with task outcome (success/failure/timeout), (2) AdaptiveReplanner reads task feedback patterns to adjust plan parameters, (3) Task reflection generates episodic memories stored with source_type="reflection", (4) Behavior patterns detected from task outcomes feed into the router. However, the reinforcement layer (achievements/streaks) does not feed back into the intelligence layer.

---

## Dimension 4: Is Aurora's Memory Genuinely Useful?

**Rating**: ADEQUATE

### What Was Examined

| File | Purpose |
|------|---------|
| `backend/app/services/memory_service.py` | Core memory operations |
| `backend/app/orchestration/context_pruner.py` | LLM context window management |
| `backend/app/orchestration/context_focus.py` | FocusedContextAssembler for memory retrieval |
| `backend/app/orchestration/session_state_mixin.py` | Context assembly pipeline |

### How Memories Are Stored

MemoryService stores four types:
1. **EpisodicMemory**: Stored in PostgreSQL with optional pgvector embedding. Fields: summary, source_type, source_lane, subject_type, importance_score, confidence, tags, evidence_refs, embedding, semantic_key, decay_policy.
2. **MemoryPreference**: Versioned preferences with evidence scoring and replacement tracking.
3. **MemoryGoal**: Status-tracked goals with evidence and metadata.
4. **SessionMood**: Redis-backed mood per session (7-day TTL).

### How Memories Are Retrieved

The `FocusedContextAssembler` (context_focus.py) is the primary retrieval mechanism. It:
1. Classifies user intent via keyword matching (emotional/task/plan/knowledge)
2. Routes to different retrieval strategies based on intent
3. Uses `cosine_similarity` for embedding-based matching when available
4. Applies a focus mode (emotional_focus, task_focus, etc.) that biases retrieval

Memory retrieval uses both semantic similarity (via pgvector embeddings) and structured queries (by subject_type, source_type, time window). The `list_recent_episodic` method queries by time window (7 days default) and subject_type filter.

### Forgetting Mechanisms

1. **TTL-based**: Self-model has 30-day TTL, session mood has 7-day TTL, working memory has session-scoped TTL
2. **Confidence decay**: `record_memory_reference_outcome` lowers confidence by 0.1 on "denied" or "corrected" outcomes
3. **Retraction**: `retract_memory` marks memories as retracted with reason tracking
4. **Revocation**: Inferred memories have a separate `revoked_at` field
5. **Decay policy**: `decay_policy` field exists on EpisodicMemory but there is no background job implementing decay

### Context Pruner Behavior (context_pruner.py)

The context pruner has a three-tier strategy:
1. Tier 1 (<=10 messages): Keep all messages intact
2. Tier 2 (<=30 messages): Importance-based compression -- keep tool calls and messages with keywords like "计划/任务/目标/记住" intact, compress low-signal messages
3. Tier 3 (>30 messages): LLM-based summarization of earlier messages, preserve anchor messages

**Does the pruner preserve memory references?** The pruner operates on raw chat history, not on the memory store. It preserves messages with tool calls and high-priority keywords, but it does not have special handling for memory references. If a memory was injected as part of the system prompt, it is not part of the pruned history (system prompts are managed separately). If a memory reference appeared in an assistant message, it could be compressed away in Tier 2.

### Calibration Receipts in Memory

Calibration receipts from user corrections are:
1. Persisted to `MemoryService.record_calibration_receipt()` (Redis list, 7-day TTL, max 10 items)
2. Written to `WorkingMemoryService` with salience_score=0.82 and subject_type="aurora_correction"
3. The `StateAggregatorService` does NOT have a field for "recent_calibration_receipts" -- this data is not aggregated into UserStateV1

### Gap Analysis

| Gap | Description | Fix Complexity |
|-----|-------------|---------------|
| **No semantic retrieval in main chat path** | The `FocusedContextAssembler` does keyword-based intent routing, then falls through to structured queries. Semantic search (pgvector cosine similarity) is implemented in the code but it is unclear whether it is called in the hot path for every conversation turn. | M |
| **Memory relevance is not validated** | There is no mechanism to check whether a retrieved memory was actually relevant to the current conversation before injecting it. The system relies on the retrieval strategy's quality, but there is no "was this memory useful?" feedback loop. | M |
| **Decay policy is declared but not enforced** | The `decay_policy` field exists on EpisodicMemory but no background job implements it. Memories accumulate indefinitely unless explicitly retracted. | S |
| **Calibration receipts are not in UserStateV1** | Recent corrections are stored in Redis but not aggregated into the state that feeds the router. The router cannot see "this user corrected me 3 times recently" as a routing signal. | S |
| **Context pruner is keyword-based** | High-importance detection (lines 219-224) uses a static keyword list. Nuanced content like "I've been feeling overwhelmed" would be compressed away unless it contains one of the 8 hardcoded keywords. | S |

### Key Question Answer

**"When Aurora says 'I remember you mentioned X', is X actually relevant?"**

The retrieval is mixed. For structured queries (by subject_type, time window), the results are by construction recent and type-appropriate. For semantic search, cosine similarity on embeddings should produce relevant results, but the quality depends on embedding quality and query formulation. The `FocusedContextAssembler` does intent-based routing first, which narrows the retrieval scope appropriately. The main risk is that without a feedback loop on memory relevance, noisy retrievals can accumulate and dilute the context.

---

## Summary Scorecard

| Dimension | Rating | One-Line Assessment |
|-----------|--------|---------------------|
| **Learning** | GOOD | Corrections flow through a complete feedback loop (4 subsystems), but keyword-based topic detection limits precision and 30-day TTL loses long-term calibration |
| **Routing** | GOOD | Explicit precedence scoring with 9+ signal dimensions produces genuinely different 3-mode outcomes with per-signal cognitive adjustments, but no per-user learning of routing thresholds |
| **Growth Loop** | ADEQUATE | 7 phases have service coverage and data flow, but Reflect requires manual triggers, Reinforce does not feed back to routing, and Adapt is partially fire-and-forget |
| **Memory** | ADEQUATE | Storage and retrieval infrastructure is mature with embedding support, versioning, and correction tracking, but decay is not enforced, calibration receipts are invisible to the router, and relevance feedback is missing |

---

## Top 5 Recommendations (Ranked by Impact)

1. **Bridge calibration receipts into UserStateV1** -- Add a `recent_corrections_summary` field to the aggregator so the router can see "this user corrected me 3 times this week" as a routing signal. This closes the most obvious intelligence gap. (S)

2. **Make reflection automatic** -- Add an end-of-session or end-of-day reflection trigger that runs when the user's session ends or when a time-based policy fires. This closes the Reflect phase without requiring user action. (M)

3. **Feed reinforcement back into routing** -- After achievement unlock or streak milestone, inject a signal into the router that adjusts `push_vs_support` strategy. A 7-day streak user should get different routing than day 1. (M)

4. **Implement memory decay** -- Add a background Celery task that lowers importance_score and confidence on episodic memories older than 30 days, respecting the declared `decay_policy` field. (S)

5. **Upgrade correction topic detection from keywords to embeddings** -- Replace the keyword-based topic matching in `record_user_correction` with a small classifier that maps the correction text to the correct assumption dimension. (M)

---

*Audit conducted via static code analysis of production source files. No runtime testing was performed. All file paths and line numbers reference the codebase as of 2026-05-02.*
