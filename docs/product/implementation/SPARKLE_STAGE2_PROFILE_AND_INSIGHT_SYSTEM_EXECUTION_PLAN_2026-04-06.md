# Sparkle Stage 2 Profile And Insight System Execution Plan

**Date**: 2026-04-06  
**Status**: Active execution plan  
**Scope**: Stage 2 core moat-building for `user profile` and `user insight`

## 1. Why This Plan Exists

Sparkle has already built a strong internal organism:
- Phase A gave us a readiness-aware understanding layer
- Phase B gave us a planning contract and benchmark
- Phase C gave us an outcome-learning loop
- Phase D gave us first body-awareness
- Phase E gave us governed five-layer learning

But after the architecture freeze, the next truth is sharper:

**Sparkle still does not use user data as effectively as it should at the exact moment the AI needs to reason.**

The product moat is not:
- how many tables we have
- how many signals we store
- how many services exist

The moat is:

1. `understanding the user better than they can easily see alone`
2. `turning that understanding into better plans than raw AI use`

This plan exists to make the first moat truly strong.

## 2. Ground Truth From Real Code Inspection

This plan is based on direct inspection of the current code, not only on the analysis report.

### 2.1 Confirmed Critical Problems

1. `Prompt pipeline leakage is real`
   - `CognitiveContext` in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/context_manager.py` collects:
     - `error_summary`
     - `recent_errors`
     - `recent_mastery_changes`
   - `context_builder` carries the full `cognitive_context` into the assembled context in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_builder.py`
   - but `_normalize_user_context()` and `format_user_context()` in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py` do not surface those signals to the model
   - result: the AI often does not see the user's most recent pain points or growth moments

2. `Achievement data is still mostly one-way`
   - unlock flow is real in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/achievement_engine.py`
   - event consumer creates a positive cognitive fragment in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/achievement_event_consumer.py`
   - but achievement behavior still does not compile into durable user insight fields such as:
     - time-of-day tendency
     - motivation response style
     - reward sensitivity
     - pace preference

3. `Calendar intelligence is still weak`
   - calendar CRUD is real in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/calendar.py`
   - `SmartScheduleService` in `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/smart_schedule_service.py` reads events mainly to avoid direct time conflicts
   - scoring still depends on generic time windows and weak optional pattern hints
   - Sparkle still does not deeply understand busy periods, class blocks, exam proximity, or post-event energy patterns

4. `Intervention learning still has a real cohort bug`
   - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/card_protocol/outcome_verifier.py` passes `_strategy_context_snapshot(...)`
   - that snapshot does not include `goal_type`, `knowledge_level`, or `learning_style`
   - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/intervention_strategy_learner.py` is built to use those fields when available
   - result: intervention learning convergence is weaker than it should be

### 2.2 Important Corrections To Keep Us Honest

Not every signal family is dead. Some subsystems are already alive and must be reused, not rebuilt.

These are already meaningfully working:

1. `push feedback -> inferred preferences`
   - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/push_feedback_service.py`
   - updates fields like:
     - `push_receptivity`
     - `inactive_push_hours`
     - `curiosity_push_receptivity`
   - these are consumed by `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/personalization/engine.py`

2. `tool history -> preferred tools`
   - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/tool_history_service.py`
   - used by routing and also injected into user context in:
     - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_builder.py`
     - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py`

3. `task / focus / streak / behavior signals`
   - already feed inferred preferences and cognitive fragments through:
     - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/task_feedback_service.py`
     - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/focus_signal_processor.py`
     - `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/behavior_signal_collector.py`
     - streak processors and personalization services

So the right Stage 2 move is **not** “rebuild everything.”
It is:

**close the dead-data leaks, expand the missing signal families, unify insight compilation, and prove that the AI actually consumes the resulting profile better.**

## 3. Stage 2 Goal

Build a `market-leading user profile and insight system` that:

1. gathers the highest-value in-app user signals
2. stores them in a reusable and evidence-bearing form
3. analyzes them across multiple time spans and layers
4. turns them into useful predictions and planning constraints
5. updates them from real outcomes without drifting
6. presents them to both the AI and the user in a transparent, controllable way

## 4. Definition Of Done

Stage 2 profile/insight work is done when all of the following are true:

1. High-value signals no longer die between collection and prompt/runtime use.
2. Sparkle can explain recent pain points, recent growth, readiness, and likely bottlenecks using real in-app evidence.
3. Achievements, calendar, and neglected behavioral surfaces are no longer second-class citizens.
4. There is one canonical compiled insight state for orchestration and product surfaces.
5. Prediction and planning layers consume that state in a measurable way.
6. Users can see, inspect, and correct meaningful parts of their profile.
7. Human evaluation and benchmark evidence show better understanding quality than before.

## 5. Non-Goals

This plan does **not** aim to:

1. collect data from external apps
2. build unlimited memory or unrestricted self-modification
3. redesign the whole AI system again
4. add new product loops that do not improve understanding quality
5. create profile theater without measurable planning benefit

## 6. Design Principles

### 6.1 No Collection Without Consumption

If a signal is collected, we should know:
- where it is stored
- how it becomes evidence
- where it reaches the model or runtime
- how it changes behavior
- how it is shown or hidden to the user

### 6.2 No Inference Without Evidence

Every durable insight should carry:
- source family
- confidence
- recency
- sample size where applicable
- contradiction state
- user-correctable explanation

### 6.3 One Canonical Insight State

We should stop scattering profile meaning across:
- prompt-only fields
- service-local heuristics
- ad-hoc UI summaries
- duplicated context aliases

There should be one compiled `UserInsightState` used by orchestration, planning, prediction, and transparency.

### 6.4 Multi-Span, Not Flat

The user model must operate across:
- turn/session
- day/week
- multi-week / cross-session
- stable profile

### 6.5 Transparency Is Part Of The Moat

Users should be able to see:
- what Sparkle thinks is true
- why it thinks that
- what is uncertain
- what changed recently
- how to correct it

## 7. Existing Systems To Reuse

Do **not** rebuild these from scratch:

1. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_context_service.py`
2. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_write_service.py`
3. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/personalization/preference_service.py`
4. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/context_manager.py`
5. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/context_pack.py`
6. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_builder.py`
7. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py`
8. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/focus_signal_processor.py`
9. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/behavior_signal_collector.py`
10. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/task_feedback_service.py`
11. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/push_feedback_service.py`
12. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/tool_history_service.py`

Stage 2 should be a `recomposition and strengthening` pass, not another full reinvention.

## 8. Multi-Phase Execution Plan

## Phase S2-I0: Dataflow Truth And Dead-Data Closure

### Purpose

Close the gap between collected user data and model-visible user understanding.

### Why first

Because this is the highest-ROI work and the current biggest moat leak.

### Deliverables

1. A signal inventory that maps:
   - source
   - storage
   - profile compiler
   - context dict
   - prompt/runtime consumer
   - user-facing transparency surface

2. Prompt/runtime closure for the currently dead high-value fields:
   - `error_summary`
   - `recent_errors`
   - `recent_mastery_changes`

3. Consumption telemetry:
   - collected high-value fields
   - compiled fields
   - prompt-visible fields
   - model-facing section sizes
   - high-value fields dropped by budget or normalization

4. Contract tests that assert these fields appear in:
   - normalized user context
   - prompt rendering
   - situation brief where appropriate

### Code Targets

1. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py`
2. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/context_builder.py`
3. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/context_manager.py`
4. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py`

### Acceptance Criteria

1. Sparkle can reference a recent error cluster in prompt-visible context.
2. Sparkle can reference a recent mastery win in prompt-visible context.
3. No high-priority profile field is collected and then silently dropped without telemetry.
4. A regression test fails if these fields disappear again.

### Handoff Packs

1. `S2-I0A`: source-to-consumer signal map
2. `S2-I0B`: prompt leakage repair
3. `S2-I0C`: consumption telemetry and regression tests

## Phase S2-I1: Canonical User Insight State

### Purpose

Create one canonical compiled state that all AI/runtime layers can trust.

### New Artifact

`UserInsightState`

It should include:
- goals
- constraints
- readiness
- recent pain points
- recent wins
- stable preferences
- inferred work style
- active contradictions
- evidence-backed hypotheses
- temporal patterns
- uncertainty markers
- confidence and freshness metadata

### Deliverables

1. `user_insight_state.py` schema
2. `user_insight_compiler.py`
3. evidence-bearing `insight_signal_registry.py`
4. migration of major downstream consumers to the canonical state

### Must Reuse

- `ProfileContextService`
- `ProfileWriteService`
- current Phase A truth/gap/readiness logic

### Must Avoid

- building another duplicate shadow profile dict
- embedding raw internal field names straight into prompts

### Acceptance Criteria

1. Orchestration, planning, and transparency can all consume the same compiled state.
2. Contradictions and uncertainty are explicit, not implicit.
3. Stable preference and transient state are distinguishable.

### Handoff Packs

1. `S2-I1A`: schema and compiler
2. `S2-I1B`: service integration
3. `S2-I1C`: contract freeze and tests

## Phase S2-I2: Signal Coverage Expansion

### Purpose

Turn neglected but high-value behavioral surfaces into usable profile signals.

### Priority Signal Families

1. `achievement signals`
   - early bird / night study
   - consistency and pace
   - milestone responsiveness
   - reward sensitivity

2. `calendar signals`
   - event density
   - busy windows
   - class/exam proximity
   - recurring schedule patterns
   - post-event energy drop hypotheses

3. `capsule and content preference signals`
   - favorites
   - revisits
   - save/share behavior

4. `workflow and tool signals`
   - existing tool history should be strengthened as profile evidence
   - not just routing hint

5. `community depth signals`
   - helping others
   - accountability responsiveness
   - knowledge-sharing quality
   - not only aggregate engagement level

6. `economy and aesthetic signals`
   - photon spending patterns
   - visual element choices
   - use only if they help real profile understanding

### Deliverables

1. New processors or bridges for truly dead signal families
2. Unified evidence-writing path into profile/insight state
3. Signal provenance and confidence policy

### Immediate Must-Fix Targets

1. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/achievement_event_consumer.py`
2. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/achievement_engine.py`
3. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/api/v1/calendar.py`
4. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/smart_schedule_service.py`
5. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capsule_favorite_service.py`
6. `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/community_signal_bridge.py`

### Acceptance Criteria

1. Achievement behavior changes profile or insight state in a durable way.
2. Calendar contributes more than conflict avoidance.
3. At least three previously neglected signal families now affect user understanding.

### Handoff Packs

1. `S2-I2A`: achievement intelligence
2. `S2-I2B`: calendar intelligence
3. `S2-I2C`: content/workflow/community signals

## Phase S2-I3: Multi-Span Analysis Engine

### Purpose

Analyze users across `width` and `depth`, not as a flat list of preferences.

### What to build

1. short-span analysis
   - turn/session
   - today
   - current overload / current traction

2. medium-span analysis
   - 7-day and 14-day rhythms
   - weekday vs weekend
   - deadline compression patterns
   - task start vs completion drift

3. long-span analysis
   - stable tendencies
   - confidence-updated hypotheses
   - trait-like but revisable patterns

4. contradiction analysis
   - what the user says vs what they do
   - explicit preference vs performance evidence
   - short-term mood vs long-term profile

### Deliverables

1. temporal pattern miner
2. contradiction/hypothesis resolver
3. insight confidence and decay rules

### Acceptance Criteria

1. Sparkle can describe not only what is true, but how stable or uncertain it is.
2. Sparkle can identify when the user’s self-report and evidence conflict.
3. Temporal reasoning is no longer limited to hour-of-day.

### Handoff Packs

1. `S2-I3A`: temporal patterns
2. `S2-I3B`: contradiction engine
3. `S2-I3C`: confidence/decay policy

## Phase S2-I4: Prediction Layer

### Purpose

Turn profile and insight into useful forward-looking guidance.

### Predictions that matter

1. planning readiness
2. overload risk
3. schedule fit
4. likely task failure modes
5. seed effectiveness likelihood
6. intervention receptivity
7. likely plan slippage under current constraints

### Deliverables

1. `insight_prediction_service.py`
2. feature extraction from `UserInsightState`
3. prediction summaries consumable by:
   - Phase A
   - Phase B
   - dashboard
   - transparency surfaces

### Acceptance Criteria

1. Predictions are evidence-backed and confidence-bounded.
2. Predictions change planning or follow-up behavior in useful ways.
3. Sparkle can explain a prediction in user-safe language.

### Handoff Packs

1. `S2-I4A`: readiness and overload
2. `S2-I4B`: planning/slippage and schedule fit
3. `S2-I4C`: intervention/seed effectiveness

## Phase S2-I5: Outcome Calibration And Anti-Drift

### Purpose

Make the profile system improve over time without turning into confident nonsense.

### Deliverables

1. outcome-linked profile calibration
2. hypothesis promotion and demotion
3. correction-aware profile hit-rate tracking
4. evidence aging / staleness policy
5. intervention learner cohort bug fix

### Must-Fix Runtime Bug In This Phase

Repair:
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/card_protocol/outcome_verifier.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/intervention_strategy_learner.py`

So intervention learning gets:
- `goal_type`
- `knowledge_level`
- `learning_style`

### Acceptance Criteria

1. Incorrect or stale insight can be demoted.
2. User corrections and outcome evidence override weak guesses.
3. We can measure insight quality over time.

### Handoff Packs

1. `S2-I5A`: cohort bug and calibration primitives
2. `S2-I5B`: promotion/demotion rules
3. `S2-I5C`: metrics and observability

## Phase S2-I6: Transparency And User Control

### Purpose

Make the profile system legible and trustworthy to the user.

### Deliverables

1. profile transparency surfaces that show:
   - current inferred truths
   - confidence
   - supporting signals
   - recent changes
   - unknowns

2. correction actions:
   - “this is wrong”
   - “this used to be true”
   - “this is only true for exam mode”

3. elegant presentation of:
   - profile
   - insights
   - predictions
   - what changed and why

### Must Reuse

- existing profile transparency APIs and memory correction patterns

### Acceptance Criteria

1. Users can inspect and correct meaningful profile claims.
2. Transparency improves trust without exposing internal machinery.
3. Product surfaces show profile evolution, not just raw settings.

### Handoff Packs

1. `S2-I6A`: backend transparency expansion
2. `S2-I6B`: mobile profile/insight surfaces
3. `S2-I6C`: correction and explanation UX

## Phase S2-I7: Understanding Benchmark And Product Proof

### Purpose

Prove that the stronger profile/insight system actually creates a better product.

### Core Benchmarks

1. `cold-start understanding`
   - what does Sparkle ask first?
   - what does it infer correctly?

2. `14-day exam planning`
   - can Sparkle form a better understanding and better plan than raw AI?

3. `continuity understanding`
   - does Sparkle recognize stable patterns and recent changes?

4. `trust and recognition`
   - do users say “yes, that feels true”?

### Required Evaluations

1. deterministic regression harness
2. human transcript review
3. founder/mentor evaluation
4. raw frontier-model comparison

### Acceptance Criteria

1. Understanding quality is measurably better than before.
2. The improved insight system produces better planning outcomes.
3. Users can recognize themselves in Sparkle’s profile and guidance.

### Handoff Packs

1. `S2-I7A`: benchmark harness
2. `S2-I7B`: transcript and human-eval loop
3. `S2-I7C`: raw-model comparison study

## 9. Execution Order

Do the phases in this order:

1. `S2-I0` Dataflow Truth And Dead-Data Closure
2. `S2-I1` Canonical User Insight State
3. `S2-I2` Signal Coverage Expansion
4. `S2-I3` Multi-Span Analysis Engine
5. `S2-I4` Prediction Layer
6. `S2-I5` Outcome Calibration And Anti-Drift
7. `S2-I6` Transparency And User Control
8. `S2-I7` Understanding Benchmark And Product Proof

## 10. What To Fix Immediately Before Broader Expansion

These are the first concrete repair items. Do not postpone them.

1. prompt leakage for:
   - errors
   - recent mistakes
   - recent mastery changes

2. achievement behavior into durable profile signals

3. calendar from CRUD/conflict-avoidance into real profile intelligence

4. intervention learner cohort bug

These four repairs should happen before any broader “AI knows the user deeply” claim.

## 11. What To Postpone

Do not spend Stage 2 energy on:

1. collecting external app data
2. adding many new social/game systems
3. new major architecture layers unrelated to user understanding
4. broad prediction theater without calibration
5. profile decoration without behavioral impact

## 12. The Chief-Designer Rule

From this point on, every profile or insight change must answer all four:

1. What new truth about the user becomes available?
2. Where does that truth actually reach the AI/runtime?
3. How does it improve planning or adaptation?
4. How can the user inspect or correct it?

If a proposed change cannot answer those, it is not the next priority.

## 13. First Pack To Execute

Start with:

`Pack S2-I0A: Dataflow Truth And Dead-Data Closure Audit`

Its mission is:
- produce the real signal map
- fix the prompt leakage for errors and mastery changes
- add telemetry for collected vs consumed profile data
- lock regression tests around those fixes

That is the best first move because it improves the moat immediately and clarifies everything that follows.
