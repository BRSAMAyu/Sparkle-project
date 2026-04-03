# Sparkle Growth System Roadmap

> Date: 2026-04-03
> Status: Active Plan
> Scope: From "37 features" to "one loop that closes, gets smarter, and the user feels it"
> Companion to: `SPARKLE_PRODUCT_CONSENSUS_2026-04-02.md`

---

## 0. Why This Plan Exists

Sparkle has 37 feature modules, 113 screens, 26 backend services, and 6 connected breakpoints. That is a lot of engineering.

But the AI at the center of it all receives ~500-600 tokens of user context. Memory injection is disabled by feature flags. Error analysis does not trigger plan replanning. Outcome verification does not feed back into strategy. The system records data about the user but does not learn from it.

This plan exists to close that gap.

It does not add new features. It takes the features that already exist and makes them actually work together — so that the more a user uses Sparkle, the smarter Sparkle gets for that specific user.

---

## 1. Current State: Honest Baseline

### What Actually Works

| System | Status | Evidence |
|--------|--------|----------|
| Chat streaming | Working | WebSocket → Go → gRPC → Python → LLM, full streaming |
| Plan creation & review | Working | Two-tier review (rule + LLM), approve/reject/modify |
| Focus mode | Working | Timer, breathing, persistence, local notifications |
| Error book CRUD | Working | OCR, knowledge linking, SM-2 review scheduling |
| Error → Mastery sync | Working | Error types map to mastery deltas, writes to UserNodeStatus |
| Adaptive replanner | Working | Evaluates plan health, generates adjustments |
| Plan adjustment applier | Working | Patches time/difficulty/inserts tasks, with rollback |
| Intervention delivery | Working | Event → record → notification center → push |
| Card protocol models | Working | Card, CardEdge, TaskOccurrence, PlanningArtifact in DB |
| Notification center | Working | Unified system + intervention notifications |

### What Exists But Is Disabled Or Incomplete

| System | Problem | Impact |
|--------|---------|--------|
| Memory injection | `ENABLE_CONTEXT_FOCUSING = False` | AI knows nothing about user's history |
| Context briefing | `ENABLE_CONTEXT_BRIEFING = False` | No contextual summary before each turn |
| pgvector memory search | Conditionally enabled, fails gracefully to None | Episodic memory never retrieved |
| Error → Plan replan | No event handler connecting them | Errors update mastery but never change plans |
| Outcome → Strategy learning | Verification exists but no feedback loop | System never learns what interventions work |
| Cognitive patterns → Dual-core | Patterns detected but not fed to router | Routing decisions are static |
| Galaxy as evidence surface | Galaxy is a visualization, not a diagnostic tool | Users can't see where they're stuck |

### What Doesn't Exist At All

| System | What's Missing |
|--------|---------------|
| User-typed error classification | Errors are classified by AI, not validated by user |
| Concept mastery dashboard | No single view showing "here's what you understand, here's where you're weak" |
| Growth evidence on home screen | Home shows feature cards, not growth evidence |
| Weekly learning digest | No automatic summary of what happened and what changed |
| Intervention A/B framework | No way to test which intervention tone works for which user |

---

## 2. Target State: One Loop That Closes

The target is not "all features work." The target is one loop:

```
User struggles with a concept
  → System detects it (error pattern, mastery drop, task stall)
  → System understands WHY (concept gap, not laziness)
  → System delivers help in a way the user accepts
  → User takes a different action
  → System verifies the action helped
  → System remembers this worked for this user
  → Next time, the system is better
```

When this loop closes once, Sparkle is better than a chatbot.
When this loop closes 100 times for the same user, Sparkle has a moat.

---

## 3. The Three Eras

```
ERA 1: FOUNDATION        ERA 2: INTELLIGENCE       ERA 3: EXPERIENCE
"Make the AI know you"   "Make the system learn"    "Make the user feel it"

Phase 1 ← Phase 2 ←     Phase 3 ← Phase 4 ←       Phase 5 ← Phase 6
  │                        │                          │
  └─ Memory & Context      └─ Feedback loops          └─ UX transformation
     Error→Plan               Outcome→Strategy           Home = Growth
     Prompt richness          Cognitive→Router           AI = Companion
```

Each phase builds on the previous one. No phase requires the next one to deliver value. You can stop after any phase and the system is better than before.

---

## ERA 1: FOUNDATION — "Make the AI Know the User"

The goal of Era 1 is simple: when a user opens Sparkle and says anything, the AI should know more about them than ChatGPT does. Not because the AI is smarter, but because Sparkle has data ChatGPT doesn't have — and actually uses it.

---

### Phase 1: Activate Memory and Rich Context

**Duration**: 5-7 days
**Goal**: The AI prompt goes from ~500 tokens of thin summaries to ~2000 tokens of rich, personalized context that includes the user's history, preferences, goals, and current struggles.

#### 1.1 Enable Context Focusing

**What**: Flip the feature flags that are already implemented.

**Files to change**:
- `backend/app/config/settings.py`: Set `ENABLE_CONTEXT_FOCUSING = True`
- `backend/app/config/settings.py`: Set `ENABLE_CONTEXT_BRIEFING = True`

**Why**: The context focusing system (`context_focus.py`) already has 6 focus profiles (plan_focus, task_focus, knowledge_focus, emotional_focus, cognitive_focus, general_focus) with per-section weights and caps. It's built. It's just turned off.

**Risk**: Low. The system has fallback modes and section caps. If context is too long, the pruner handles it.

**Acceptance**: After enabling, send 5 test messages as a user with history. Verify the system prompt now includes:
- User preferences (at least 3)
- Active goals
- Recent episodic memories (if any exist)
- Section weights matching the inferred focus mode

#### 1.2 Increase Memory Creation Touchpoints

**What**: Ensure that meaningful user interactions create memory entries.

**Current state**: MemoryService has full CRUD for preferences, goals, and episodic memories. But creation is sparse — only explicit events trigger it.

**What to add**:
1. After a plan is created → create goal memory
2. After a plan review is approved → update goal memory with plan link
3. After an error is analyzed → create episodic memory ("User struggled with [concept] on [date]")
4. After a focus session ends → create episodic memory ("User completed [duration] focus on [task]")
5. After task feedback → update preference ("User prefers morning study" / "User reports difficulty with [type]")

**Implementation**: Add memory creation calls in existing event consumers and services. No new infrastructure needed.

**Acceptance**: After 10 minutes of normal app usage (create plan, do a focus session, log an error), the user should have at least 5 new memory entries. Verify they appear in the memory panel screen.

#### 1.3 Fix pgvector Memory Retrieval

**What**: Ensure episodic memory retrieval works, not just gracefully degrades.

**Current state**: `create_episodic_memory()` accepts embeddings but pgvector may not be enabled in the database. When it fails, it returns None and the system continues without memory search.

**Steps**:
1. Verify pgvector extension is installed in the database: `SELECT * FROM pg_extension WHERE extname = 'vector';`
2. If not installed: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Verify the memory table has a vector column for embeddings
4. Ensure embedding generation works (check if embedding service is configured)
5. If embedding service is not available, implement a simpler keyword-based memory retrieval as fallback

**Acceptance**: Given a user with 10+ episodic memories, a relevant chat message should surface at least 1 related memory in the context pack. Verify by checking the assembled context in logs.

#### 1.4 Expand Context Budget for Standard Tier

**What**: Increase the token budget from 2800 to 4000 for the standard tier.

**Current state**: `_TIER_PROMPT_BUDGET["standard"] = 2800`. The system already has a "reasoning" tier at 4000 and "free_reasoning" at 3000.

**Why**: 2800 tokens is not enough to carry rich user context plus conversation history. Modern LLMs handle 4000 tokens of context without latency issues.

**Implementation**:
- Change `backend/app/orchestration/prompts.py` line with `_TIER_PROMPT_BUDGET["standard"]` to 4000
- Adjust section ratios proportionally, especially:
  - `user_context`: 220 → 350 tokens (the biggest win)
  - `episodic_memories`: increase cap from 2 to 5
  - `plan_context`: 100 → 200 tokens
  - `cognitive_prism_section`: 60 → 100 tokens

**Acceptance**: After the change, the assembled context for a standard-tier request should be 3000-4000 tokens with user context making up 25-30% of the budget.

---

### Phase 2: Connect Error Signals to Plan Decisions

**Duration**: 5-7 days
**Goal**: When a user makes errors that reveal a conceptual gap, the system not only updates mastery but actually changes the user's upcoming plan — inserting review tasks, adjusting difficulty, or flagging the plan as at-risk.

#### 2.1 Build the Error → Replan Event Bridge

**What**: Create an event handler that connects error creation to the adaptive replanner.

**Current state**: `AdaptiveReplanner` is triggered by task feedback and task completion. It is NOT triggered by error creation. Errors update mastery but the replanner never hears about it.

**Implementation**:

Create `backend/app/services/error_replan_bridge.py`:

```
ErrorCreated event
  → Check: does user have an active plan?
  → Check: is the error linked to knowledge nodes relevant to the plan?
  → Check: error severity (concept_confusion or knowledge_gap with mastery < 0.5)
  → If all true: call adaptive_replanner.on_error_signal(
      user_id, plan_id, affected_node_ids, error_type, severity
    )
```

The replanner should respond by:
- If severity is medium: flag the plan as "concept risk" in PlanState
- If severity is high: insert a review task for the affected concept into the next 3 days
- If severity is critical + multiple errors on same concept: trigger plan health evaluation

**Acceptance**: Create 3 errors for the same concept in rapid succession. Verify that:
1. The plan's PlanState gets updated with concept risk
2. A review task is inserted into the plan
3. A plan health evaluation is triggered after the 3rd error

#### 2.2 Make Error Classification User-Validatable

**What**: After the AI classifies an error, show the classification to the user and let them confirm or correct it.

**Current state**: Errors are classified by AI into types (concept_confusion, knowledge_gap, method_wrong, etc.) but the user never sees or validates this classification. If the AI is wrong about the error type, the downstream mastery updates are wrong too.

**Implementation** (Flutter):
- In `error_detail_screen.dart`, add a section showing the AI's classification:
  - Error type with confidence
  - Linked knowledge nodes
  - Suggested root cause
- Add two buttons: "Looks right" / "Not quite right"
- If user corrects: update the error type and re-trigger mastery sync with corrected weights

**Why this matters**: This is the first moment where the system asks the user "am I right about you?" It builds trust, and it makes the data quality dramatically better.

**Acceptance**: Log an error, view it in the error detail screen, correct the classification from "calculation_error" to "concept_confusion". Verify the mastery sync uses the corrected weights (-8 instead of -3).

#### 2.3 Surface Mastery State in Galaxy

**What**: The knowledge graph visualization should clearly show which nodes are strong, which are weak, and which are at-risk — not just which ones exist.

**Current state**: Galaxy has rich visualization (92KB painter, 15+ components) but node colors don't clearly communicate mastery state.

**Implementation**:
- Map mastery score ranges to visual states:
  - `mastery >= 0.8`: Bright/glowing (mastered)
  - `0.5 <= mastery < 0.8`: Normal (learning)
  - `0.3 <= mastery < 0.5`: Dim/warning (weak)
  - `mastery < 0.3`: Red flag / pulsing (at-risk)
- Add a legend to the galaxy screen
- Add a filter toggle: "Show only weak/at-risk nodes"

**Acceptance**: After logging errors that drop mastery on specific nodes, open the galaxy. The affected nodes should visually stand out. A user should be able to see "these are the nodes I'm struggling with" at a glance.

---

## ERA 2: INTELLIGENCE — "Make the System Learn"

Era 1 made the AI know the user. Era 2 makes the system learn from what happens. The key shift: from "the system records outcomes" to "the system changes its behavior based on outcomes."

---

### Phase 3: Close the Outcome → Strategy Loop

**Duration**: 7-10 days
**Goal**: After every intervention, the system tracks whether it worked, and uses that information to choose better interventions next time.

#### 3.1 Implement Strategy Effect Tracking

**What**: Create a persistent record of which intervention strategies work for which users.

**Current state**: `InterventionOutcomeVerifier` evaluates whether an intervention was effective (EFFECTIVE/INEFFECTIVE). But this evaluation doesn't feed back into strategy selection. The system always picks strategies the same way.

**Implementation**:

Create `backend/app/services/intervention_strategy_learner.py`:

```python
class InterventionStrategyLearner:
    """Tracks which intervention strategies work for which users."""

    async def record_outcome(self, user_id, intervention_id, outcome):
        """Record intervention outcome with full context."""
        # Store: trigger_type, delivery_tone, delivery_channel,
        #        user_state_at_time, outcome, time_to_action

    async def get_best_strategy(self, user_id, trigger_type):
        """Return the best strategy for this user based on history."""
        # Look up past interventions with same trigger_type
        # Calculate effectiveness rate per tone/channel combination
        # Return highest-effectiveness strategy, or default if insufficient data

    async def get_user_response_profile(self, user_id):
        """Return a profile of how this user responds to interventions."""
        # Accepts curiously-toned interventions: 80% of the time
        # Accepts directly-toned: 40% of the time
        # Responds to chat delivery: 70%
        # Responds to push delivery: 30%
        # Average time to action: 2.3 hours
```

**Storage**: Use a new table `intervention_strategy_outcomes` with columns:
- `user_id`, `intervention_id`, `trigger_type`, `delivery_tone`, `delivery_channel`
- `user_state` (JSON: plan_health, mastery_avg, streak, recent_errors)
- `outcome` (effectiveness rating), `time_to_action`
- `created_at`

**Acceptance**: After 10 interventions with varying outcomes, `get_best_strategy()` should return different strategies for different users based on their history.

#### 3.2 Wire Outcome Verifier to Strategy Learner

**What**: When the outcome verifier finishes evaluating an intervention, it should feed the result to the strategy learner.

**Implementation**:
- In `outcome_verifier.py`, after computing outcome (EFFECTIVE/INEFFECTIVE), call `strategy_learner.record_outcome()`
- In `intervention_event_consumer.py`, before creating a new intervention, call `strategy_learner.get_best_strategy()` to select tone and channel

**Acceptance**: Create an intervention, let the user accept and act on it. Verify the outcome is recorded in `intervention_strategy_outcomes`. Create a second similar intervention for the same user. Verify the strategy selection considers the first outcome.

#### 3.3 Add Outcome-Based Strategy Adjustment to Card Protocol

**What**: The card protocol's planning artifacts should evolve based on intervention outcomes.

**Current state**: `GlobalCompassManager` and `StrategyMapManager` create artifacts but don't update them based on results.

**Implementation**:
- After an intervention outcome is recorded, if the outcome was INEFFECTIVE:
  - Add a `risk_register` entry: "Strategy X was ineffective for user Y in context Z"
  - Update the active `ACTIVE_PHASE_PACK` with adjusted intervention policy
- After an intervention outcome was EFFECTIVE:
  - Record in `decision_log`: "Strategy X worked for user Y"
  - Use as evidence when refreshing the next `REFLECTION_REPORT`

**Acceptance**: After a confirmed ineffective intervention, verify a risk register entry is created and the next active phase pack reflects adjusted intervention policies.

---

### Phase 4: Connect Cognitive Signals to Routing

**Duration**: 7-10 days
**Goal**: The dual-core router and the cognitive pattern system actually talk to each other. The system's routing decisions improve based on accumulated user understanding.

#### 4.1 Build Cognitive Pattern → Dual-Core Router Bridge

**What**: Feed detected cognitive patterns into the dual-core routing decision.

**Current state**: `DualCoreRouter.route()` takes `DualCoreRoutingInput` which includes `emotional_block_detected` and `procrastination_pattern` fields. But these are set from simple keyword matching in the current turn, not from accumulated cognitive patterns.

**Implementation**:
- In the context builder, before calling `dual_core_router.route()`:
  - Fetch the user's top cognitive patterns from the cognitive service
  - Map patterns to routing signals:
    - Chronic procrastination pattern → `procrastination_pattern = True`, lower `goal_clarity`
    - Repeated concept confusion → `emotional_block_detected = True`, suggest cognitive mode
    - Perfectionism pattern → adjust `suggested_verbosity` to supportive
  - Include pattern confidence in the routing input

**Acceptance**: For a user with a detected procrastination pattern (confidence ≥ 0.7), the dual-core router should route to cognitive mode more often than for a user without such patterns.

#### 4.2 Make Dual-Core Router Thresholds Adaptive

**What**: Replace hardcoded thresholds (0.72, 0.6, 0.5, 0.4) with user-specific learned thresholds.

**Current state**: Routing decisions use fixed thresholds for goal_clarity, emotional_block, etc. Every user gets the same thresholds.

**Implementation**:
- Add a `user_routing_profile` table or field:
  - `procrastination_sensitivity`: how quickly to detect procrastination (default 0.6)
  - `emotional_sensitivity`: how quickly to shift to cognitive mode (default 0.5)
  - `directness_preference`: how directly to communicate (default 0.5)
- After each routing decision, if the user's subsequent behavior suggests the routing was wrong (e.g., routed to execution but user didn't execute), adjust the threshold slightly
- Use a simple Bayesian update: `threshold = threshold * 0.9 + observed_signal * 0.1`

**Acceptance**: After 20+ sessions, a user who consistently ignores execution-mode suggestions should have their routing profile shifted toward cognitive mode. Verify the thresholds have moved from defaults.

#### 4.3 Connect Task Feedback to Plan Health in Real-Time

**What**: When a user gives negative feedback on a task ("this is too hard", "I don't understand"), immediately evaluate plan health rather than waiting for the periodic check.

**Current state**: `task_feedback_service.py` calls `adaptive_replanner.on_task_feedback()`, but the replanner's periodic evaluation may not catch the signal fast enough.

**Implementation**:
- In `on_task_feedback()`, if feedback indicates cognitive struggle (difficulty rating ≥ 4, or "don't understand" tag):
  - Immediately trigger `evaluate_progress()` for the current plan
  - If plan health drops to "warning" or below, emit a `PLAN_HEALTH_ALERTED` event immediately
  - Do not wait for the next scheduled evaluation cycle

**Acceptance**: Submit negative task feedback indicating confusion. Verify that plan health is evaluated within seconds (not minutes), and an alert event is emitted if warranted.

---

## ERA 3: EXPERIENCE — "Make the User Feel It"

Era 1 gave the AI memory. Era 2 gave the system learning. Era 3 makes the user actually experience the difference. This is where Sparkle stops feeling like a tool with an AI chatbot bolted on, and starts feeling like a system that genuinely understands you.

---

### Phase 5: Transform the Home Screen and AI Presence

**Duration**: 7-10 days
**Goal**: The home screen becomes a growth evidence dashboard. The AI feels like it knows you. The first thing a user sees when they open the app is proof that the system is paying attention.

#### 5.1 Redesign Home Screen as Growth Dashboard

**What**: Replace the feature-card bento grid with a growth-evidence-first layout.

**Current state**: The dashboard shows 28+ card types — task board, focus card, plan card, weather header, cognitive tool hub, curiosity capsule, OpenClaw hub, intent predictions, etc. It's overwhelming and feature-centric.

**New home screen structure** (top to bottom):

```
┌─────────────────────────────────────┐
│  Growth Status Header               │
│  "You're on track this week"        │
│  [streak] [tasks done] [focus time] │
├─────────────────────────────────────┤
│  Today's Focus                      │
│  1-2 cards: what matters most today │
│  (based on plan health + mastery)   │
├─────────────────────────────────────┤
│  Growth Signal                      │
│  "Your thermodynamics mastery went  │
│   from 0.4 → 0.6 this week"        │
│  [proof: 3 errors → 3 reviews]     │
├─────────────────────────────────────┤
│  AI Insight                         │
│  One contextual insight from the AI │
│  (not generic, based on real data)  │
├─────────────────────────────────────┤
│  Quick Actions                      │
│  [Focus] [Today's Tasks] [Chat]     │
└─────────────────────────────────────┘
```

**Key principles**:
- Growth Signal section shows evidence of real change, not just activity counts
- "Today's Focus" is algorithmically determined (plan health risk × mastery gap × deadline pressure)
- AI Insight is generated from the user's actual data, not generic advice
- Everything below the fold is accessible but not competing for attention

**Implementation approach**:
- Create a new `GrowthDashboardService` that computes growth signals
- Modify `dashboard_screen.dart` to use the new layout
- Reuse existing card widgets where possible (focus card, task card)
- Deprecate cards that don't serve the growth narrative (weather, openclaw, etc. — keep them accessible via navigation, but not on home)

**Acceptance**: Open the app after a week of usage. The home screen should show:
1. A meaningful growth signal (e.g., mastery change, plan progress)
2. 1-2 cards that are actually the most important things for today
3. One AI insight that references specific user data

#### 5.2 Make AI Chat Feel Personal

**What**: The AI's responses should reference specific things it knows about the user, creating a "this AI actually knows me" feeling.

**Current state**: The prompt includes user context but the base persona is generic: "你是 Sparkle（星火），一个智能学习助手。" The AI responds helpfully but generically.

**Implementation**:

Enhance the system prompt to include personalized framing:

```
After the base persona, add:
- User's name and current goals
- "Things you know about this user:" (top 5 preferences from memory)
- "Recent patterns:" (top 2-3 cognitive/behavioral patterns)
- "Current focus:" (active plan + nearest deadline)
- "What to pay attention to:" (at-risk knowledge nodes, struggling tasks)
```

This is not about making the prompt longer — it's about making the existing context slots actually contain rich, specific information. Phase 1 enabled the pipes; Phase 5 makes the water taste good.

**Acceptance**: As a returning user, ask the AI "what should I work on today?" The response should reference your specific goals, current progress, and at-risk areas — not give generic advice.

#### 5.3 Build Weekly Growth Digest

**What**: Every Monday (or configurable), generate and deliver a summary of the user's growth that week.

**Content**:
- What you learned (mastery changes on knowledge nodes)
- What you struggled with (error patterns, repeated concepts)
- What changed (plan adjustments, interventions received)
- What's next (upcoming focus areas for the coming week)
- One thing the system learned about you

**Implementation**:
- Create `backend/app/services/weekly_digest_service.py`
- Use existing data: mastery history, error records, plan adjustments, intervention outcomes
- Generate using LLM with structured output (not free-form)
- Deliver as a rich notification + dedicated screen in the app

**Acceptance**: After a user has 7+ days of activity, trigger the digest generation. Verify it contains specific, accurate data — not generic platitudes.

---

### Phase 6: Polish the Demo Story

**Duration**: 5-7 days
**Goal**: The end-to-end thermodynamics scenario runs flawlessly. Not just technically — the experience feels compelling enough that a judge or investor says "I want this."

#### 6.1 Script and Validate the Demo Scenario

**What**: Walk through the thermodynamics review scenario end-to-end and fix every friction point.

**The scenario**:
1. User says: "我热力学完全不会，考试两周后"
2. System asks clarifying questions (not like a form — like a conversation)
3. System generates a 14-day review plan with phases
4. Day 1-2: User completes tasks, logs errors on thermodynamic processes
5. Day 3: System detects repeated errors on "reversible vs irreversible processes"
6. System delivers intervention: "我发现一个有趣的现象——你在可逆和不可逆过程之间总是更容易选前者。我们来试个东西？"
7. User accepts, spends 15 minutes on a targeted concept review
8. System inserts review task, adjusts remaining plan difficulty
9. Day 5: Mastery on affected nodes improves from 0.3 → 0.5
10. System records: "curious-tone intervention was effective for this user"
11. Day 7: Weekly digest shows progress and next focus areas

**For each step**, verify:
- The data flows correctly between systems
- The user sees a clear, polished UI
- The AI response feels natural and specific
- The timing feels right (not too fast, not too slow)

**Acceptance**: A person unfamiliar with the app can follow this scenario without confusion and reach the end feeling that the system genuinely helped.

#### 6.2 Fix the Intervention Tone in Practice

**What**: Review all intervention templates and AI prompts that generate intervention text. Ensure they consistently follow the intervention language system.

**Current state**: The intervention language system document (`SPARKLE_INTERVENTION_LANGUAGE_SYSTEM_2026-04-02.md`) defines 6 hard principles and 3 style principles. But the actual template rendering in `intervention_event_consumer.py` may not fully embody these.

**Steps**:
1. Audit every intervention template against the 6 hard principles
2. Rewrite any template that uses judgmental, shaming, or failure-announcing language
3. Add template tests: given a trigger, the rendered text should not contain forbidden patterns ("你又", "你没有", "你偏离了", etc.)
4. Ensure the tone adapts based on strategy learner results from Phase 3

**Acceptance**: Generate 20 interventions of different types. Read every one. None should feel judgmental or anxiety-inducing. At least half should genuinely make you curious to engage.

#### 6.3 Performance and Reliability Pass

**What**: Ensure the demo scenario runs without errors, timeouts, or UI glitches.

**Steps**:
1. End-to-end latency: AI first token < 2s, intervention delivery < 5s
2. Galaxy rendering: smooth 60fps with 50+ nodes
3. No crashes during the full scenario walkthrough
4. Offline resilience: if network drops mid-scenario, the app recovers gracefully
5. Memory usage stays within bounds during extended use

**Acceptance**: Run the full demo scenario 5 times without a single error or noticeable lag.

---

## 4. What We Are NOT Doing

This plan is defined as much by what it excludes as by what it includes.

### Explicitly Out of Scope

| Item | Why excluded |
|------|-------------|
| New feature modules | 37 modules is more than enough. Fix what exists. |
| Community expansion | Community is an amplifier, not the core loop. It can wait. |
| OpenClaw expansion | Digital task execution is not the growth loop. |
| Poster studio / visual elements | Cosmetic. Not growth evidence. |
| Leaderboard / competitive features | Motivation ≠ understanding. Not the moat. |
| Translation / dictionary | Useful tool, not the core value proposition. |
| Theme customization | Polish, not foundation. |
| Multi-scene expansion (fitness, skills) | Too early. Nail learning first. |
| New proto changes | No API contract changes needed for this plan. |
| Database schema redesign | Card protocol tables exist. Work with what's there. |

### The One Exception

If any of the above becomes a blocker for the main loop (e.g., the notification system can't deliver a specific card type), then minimal changes are allowed. But the bar is: "does this unblock the main loop?" not "would this be nice to have?"

---

## 5. Success Metrics by Phase

### Phase 1 (Memory & Context)
- **Primary**: Average context tokens reaching LLM increases from ~500 to ~2500+
- **Secondary**: Memory panel shows 10+ entries after 30 minutes of normal usage
- **Guardrail**: AI response latency does not increase by more than 500ms

### Phase 2 (Error → Plan)
- **Primary**: Logging 3+ errors on the same concept triggers a plan adjustment
- **Secondary**: Galaxy screen clearly shows at-risk nodes with visual distinction
- **Guardrail**: Error classification accuracy (user validation) ≥ 70%

### Phase 3 (Outcome → Strategy)
- **Primary**: After 10 interventions, the system selects different strategies for different users
- **Secondary**: Intervention acceptance rate improves over time for individual users
- **Guardrail**: No user receives more than 2 interventions per day

### Phase 4 (Cognitive → Routing)
- **Primary**: Users with detected procrastination patterns are routed to cognitive mode more often
- **Secondary**: Routing thresholds shift from defaults after 20+ sessions
- **Guardrail**: Routing decisions are explainable (log the signals that drove each decision)

### Phase 5 (Experience)
- **Primary**: Home screen shows specific growth evidence (not generic metrics)
- **Secondary**: AI chat references user-specific history in ≥ 50% of substantive responses
- **Guardrail**: Home screen load time < 1s

### Phase 6 (Demo)
- **Primary**: Thermodynamics scenario completes end-to-end without errors
- **Secondary**: External observer rates the experience as "genuinely helpful" (not just "technically impressive")
- **Guardrail**: Demo runs reliably 5/5 times

---

## 6. Dependency Map

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
  │                        │              │
  │                        │              │
  └────────────────────────┴──────────────┘
               │
               ▼
            Phase 5 ──→ Phase 6
```

- Phase 1 and 2 can partially overlap (first week: enable memory + build error bridge)
- Phase 3 and 4 can partially overlap (both are feedback loop wiring)
- Phase 5 depends on Phases 1-4 being complete (can't show growth evidence if the data isn't there)
- Phase 6 depends on Phase 5 (demo needs the polished experience)

### Suggested Timeline

```
Week 1-2:  Phase 1 (memory & context) + Phase 2 start (error bridge)
Week 3-4:  Phase 2 complete + Phase 3 start (strategy learning)
Week 5-6:  Phase 3 complete + Phase 4 start (cognitive routing)
Week 7-8:  Phase 4 complete + Phase 5 start (experience)
Week 9-10: Phase 5 complete + Phase 6 (demo polish)
```

**Total: ~10 weeks.** But value is delivered continuously — every phase makes the product measurably better.

---

## 7. Moat Trajectory

After this plan, Sparkle's moat looks like this:

**After Phase 1-2** (Week 4):
- The AI knows more about each user than any generic chatbot
- Error patterns drive real plan changes
- This is already hard to replicate — it requires the data pipeline + the plan system + the error analysis working together

**After Phase 3-4** (Week 8):
- The system genuinely learns what works for each user
- Intervention strategies personalize over time
- Cognitive patterns inform routing decisions
- This is very hard to replicate — it requires longitudinal outcome data per user

**After Phase 5-6** (Week 10):
- Users feel the system getting smarter
- Growth evidence is visible, not hidden
- The demo tells a story no other product can tell
- This is the moat. A competitor can copy features. They can't copy 100 closed learning loops per user.

---

## 8. How to Use This Plan

1. **Start with Phase 1, Step 1.1.** Flip the feature flags. See what happens. This alone will be a significant improvement.

2. **After each phase, run the acceptance criteria.** If they pass, move on. If they don't, fix before proceeding.

3. **Don't skip phases.** Each phase depends on the previous one's data and infrastructure. Skipping means building on sand.

4. **Track the metrics.** If a phase's primary metric isn't moving, stop and investigate before continuing.

5. **Use the dependency map.** Phases that can overlap should overlap. Phases that can't shouldn't.

6. **Refer back to the consensus document.** If you're unsure whether something is in scope, check: "Does it help the user see where they're stuck, accept help, and actually change?" If not, it's out of scope for now.

---

## 9. The North Star

Everything in this plan serves one sentence:

> **Sparkle is not an AI that answers questions. It's an AI that notices when you're stuck, figures out why, helps you get unstuck, and remembers what worked.**

When this sentence is true for every user, Sparkle has a moat that no amount of feature copying can break.
