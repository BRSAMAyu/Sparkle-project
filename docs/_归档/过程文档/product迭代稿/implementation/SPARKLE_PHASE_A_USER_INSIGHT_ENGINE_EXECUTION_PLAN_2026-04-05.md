# Sparkle Phase A User Insight Engine Execution Plan

> Date: 2026-04-05  
> Status: Active execution plan  
> Audience: Founder, chief designer, implementation Codex runs, backend, mobile, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05.md`
> - `docs/product/SPARKLE_NEXT_PHASE_MASTER_PLAN_2026-04-04.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`

---

## 0. Why This Phase Exists

Sparkle’s current wedge is no longer ambiguous:

> **understand the user deeply, then turn that understanding plus their data into the best plan**

That means the first moat we must strengthen is:

> **user understanding quality**

Right now Sparkle already has many signals:

- preferences
- weak spots
- mastery changes
- behavior patterns
- companion state
- strategy state
- active interventions
- semantic primitives
- situation brief

But the current system is still stronger at `assembling signals` than at `discovering decisive missing information`.

Phase A exists to change that.

This phase should turn Sparkle’s profile layer from a smart read model into a true:

> **User Insight Engine**

---

## 1. Phase A Goal

Phase A goal:

> **Make Sparkle significantly better at knowing what it still needs to learn about a user, what is truly blocking that user, and whether it has enough truth to build a strong plan.**

If Phase A succeeds, Sparkle should become better at:

1. asking for the right missing information
2. distinguishing stable traits from temporary state
3. identifying the real bottleneck
4. fusing scattered signals into one coherent user model
5. knowing when it is ready to plan and when it is not

---

## 2. Definition of Done

Phase A is done only when all of the following are true:

1. Sparkle can produce a runtime `insight state` that clearly separates:
   - known truths
   - suspected truths
   - missing information
   - stale information
   - contradictory information

2. Sparkle can explicitly answer:
   - what do I still need to know before planning?
   - what is the likeliest bottleneck?
   - how confident am I?
   - what evidence supports that?

3. Sparkle can choose whether to:
   - ask a clarifying question
   - plan now
   - plan provisionally with uncertainty acknowledged

4. The `SituationBrief` and planning loop use this new insight state, not just raw profile aggregation.

5. There is a benchmark showing Sparkle asks for better missing information than the previous system baseline in cold-start and low-context scenarios.

6. Human reviewers judge the inferred bottleneck as recognizably true in a meaningful share of test cases.

---

## 3. Non-Goals

Phase A is not for:

- broad new agent creation
- decorative dashboard work
- full execution autonomy
- major UI redesign
- broad domain expansion
- making Sparkle “feel smarter” without better user understanding

This phase is specifically about `user understanding quality`.

---

## 4. Design Principles

### 4.1 Reuse the Existing Organism

We should connect and strengthen current infrastructure, not replace it.

### 4.2 Insight Must Be Evidence-Bearing

Every important insight should expose:

- source
- freshness
- confidence
- contradiction risk

### 4.3 Missing Information Is First-Class

Sparkle should not merely summarize what it knows.
It should model what it does **not** know.

### 4.4 Planning Readiness Must Be Explicit

Sparkle must know whether it is ready to generate a strong plan.

### 4.5 Clarification Must Be Strategic

Clarifying questions are not generic.
They should be the minimum high-value questions needed to unlock better planning.

---

## 5. What We Must Reuse

Phase A should be built on top of current working components:

- [ProfileContextService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_context_service.py)
- [PreferenceService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/personalization/preference_service.py)
- [CognitiveService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/cognitive_service.py)
- [SituationBriefBuilder](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [ResidualDiagnosisRuntime](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/residual_diagnosis.py)
- [UserStrategyStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_strategy_state_service.py)
- [StudyDomainSemanticAdapter](/Users/brsama/code/GitHub/Sparkle-project/backend/app/semantic/state_primitives.py)
- [ChatOrchestrator](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py)
- [HumanEvalReviewService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/human_eval_review_service.py)

We should not rebuild these as parallel systems.

---

## 6. Target Architecture for Phase A

Phase A should add three major runtime artifacts and one evaluation layer.

### 6.1 Artifact A: Profile Truth Compiler

Purpose:

- merge preference, cognitive, progress, plan, strategy, companion, and intervention signals into one coherent truth state

Core outputs:

- `stable_traits`
- `current_state`
- `active_constraints`
- `active_bottlenecks`
- `confidence_map`
- `freshness_map`
- `conflict_map`

This is not a new user-profile database.
It is a compiled runtime truth layer.

### 6.2 Artifact B: Insight Gap Detector

Purpose:

- explicitly model what Sparkle still needs to know in order to plan well

Core outputs:

- `missing_information_items`
- `question_candidates`
- `information_value_rank`
- `clarification_priority`

This is the layer that lets Sparkle ask better questions than raw AI use.

### 6.3 Artifact C: Planning Readiness Gate

Purpose:

- decide whether the system should:
  - plan now
  - ask first
  - plan provisionally with uncertainty

Core outputs:

- `readiness_score`
- `readiness_level`
- `blocking_unknowns`
- `allowed_plan_scope`

### 6.4 Artifact D: Insight Evaluation Harness

Purpose:

- measure whether Sparkle’s insight behavior is actually improving

Core outputs:

- clarification quality score
- bottleneck accuracy score
- planning readiness calibration score
- human-recognized truth score

---

## 7. Runtime Data Model

Phase A should introduce a compact read model, likely under orchestration or services, such as:

`CompiledInsightState`

Suggested shape:

```text
CompiledInsightState
  stable_traits
  current_state
  active_constraints
  active_bottlenecks
  key_uncertainties
  missing_information
  confidence_map
  freshness_map
  contradiction_map
  planning_readiness
  recommended_clarification
```

Important rule:

This should be `read-first` and `non-destructive`.
Do not migrate or rewrite existing persistence for Phase A.

---

## 8. Multi-Stage Execution Plan

## Stage 0: Truth Audit and Baseline

### Purpose

Create a baseline of how Sparkle currently understands users before changing runtime behavior.

### Deliverables

1. A `current insight source map`:
   - what profile signals exist
   - where they come from
   - how fresh they are
   - what runtime consumers use them

2. A `cold-start planning audit`:
   - what Sparkle asks when user data is sparse
   - what it misses
   - what low-quality plans result

3. A `truth-gap benchmark set`:
   - exam prep under deadline
   - weak self-knowledge case
   - overloaded user with fragmented data
   - contradictory signals across sessions

### Reuse

- current orchestrator metadata
- human-eval tools
- north-star journey fixtures

### Acceptance

- we have a benchmark set and a written list of the most damaging current insight failures

### Codex Pack

`Pack A0: User Insight Baseline Audit`

---

## Stage 1: Profile Truth Compiler Shadow Path

### Purpose

Build a compiled truth layer without changing plan behavior yet.

### Deliverables

1. New runtime compiler service:
   - likely `profile_truth_compiler.py`

2. Shadow artifact attached into runtime context:
   - `compiled_insight_state`

3. Source annotations:
   - source
   - freshness
   - confidence
   - contradiction

### Recommended Touch Points

- [backend/app/services/profile_context_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_context_service.py)
- [backend/app/orchestration/situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [backend/app/orchestration/session_state_mixin.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/session_state_mixin.py)
- [backend/app/orchestration/orchestrator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py)

### Key Rule

Do not break existing `ProfileContext`.
Compile above it.

### Acceptance

- runtime can emit `compiled_insight_state`
- no prompt or planner behavior change yet
- tests show stable compilation from current profile sources

### Codex Pack

`Pack A1: Profile Truth Compiler Shadow Runtime`

---

## Stage 2: Insight Gap Detector

### Purpose

Teach Sparkle to identify what crucial information is still missing.

### Deliverables

1. New detector service:
   - likely `insight_gap_detector.py`

2. Ranked missing-information outputs:
   - goal ambiguity
   - deadline ambiguity
   - baseline ambiguity
   - material insufficiency
   - capacity uncertainty
   - constraint uncertainty
   - motivation/risk uncertainty

3. Candidate clarification questions:
   - natural-language
   - minimal
   - high-value

### Recommended Touch Points

- [backend/app/orchestration/situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [backend/app/orchestration/residual_diagnosis.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/residual_diagnosis.py)
- [backend/app/orchestration/decision_policy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/decision_policy.py)

### Key Rule

Clarification should be planning-driven, not generic chatbot curiosity.

### Acceptance

- Sparkle can name top missing information items
- Sparkle can produce ranked clarification prompts
- cold-start scenarios show improved clarification choice

### Codex Pack

`Pack A2: Insight Gap Detector`

---

## Stage 3: Planning Readiness Gate

### Purpose

Make Sparkle explicitly decide when it has enough truth to plan.

### Deliverables

1. New readiness service:
   - likely `planning_readiness_gate.py`

2. Runtime outputs:
   - `readiness_score`
   - `readiness_level`
   - `blocking_unknowns`
   - `allowed_plan_scope`

3. Decision integration:
   - ask first
   - partial plan
   - full plan

### Recommended Touch Points

- [backend/app/orchestration/decision_policy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/decision_policy.py)
- [backend/app/orchestration/situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [backend/app/orchestration/prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py)
- [backend/app/orchestration/orchestrator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py)

### Key Rule

Sparkle should sometimes refuse to pretend it knows enough.

### Acceptance

- the planning loop can choose ask/provisional/full-plan paths
- readiness levels are exposed in runtime metadata
- tests cover under-informed and well-informed cases

### Codex Pack

`Pack A3: Planning Readiness Gate`

---

## Stage 4: SituationBrief Integration and Clarification Behavior

### Purpose

Make the new insight engine affect the actual experience.

### Deliverables

1. `SituationBrief` upgraded to include:
   - compiled insight state summary
   - missing-information summary
   - readiness summary

2. Prompt guidance upgraded so Sparkle:
   - asks fewer but better questions
   - explains why it needs them when appropriate
   - does not over-question when readiness is already high

3. Visible user-facing adaptation:
   - “before I plan, I need to pin down X”
   - “I can give you a first version now, but Y is still uncertain”

### Recommended Touch Points

- [backend/app/orchestration/situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [backend/app/orchestration/prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py)
- [backend/app/orchestration/ux_envelope.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/ux_envelope.py)
- mobile chat surfaces only if needed for visible clarification summaries

### Acceptance

- clarification quality is improved in orchestrator-backed scenarios
- the user can feel why Sparkle asked
- Sparkle stops asking redundant low-value questions

### Codex Pack

`Pack A4: SituationBrief and Clarification UX Integration`

---

## Stage 5: Evaluation and Benchmarking

### Purpose

Prove that the insight engine is actually better.

### Deliverables

1. Insight benchmark fixture set
2. Automated evaluator for:
   - missing-information quality
   - bottleneck accuracy
   - readiness calibration
3. Human review rubric updates:
   - wrong question asked
   - missed critical unknown
   - over-questioning
   - false certainty
   - correct bottleneck surfaced

### Recommended Touch Points

- [backend/app/services/experience_phase_evaluator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/experience_phase_evaluator.py)
- [backend/app/services/human_eval_review_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/human_eval_review_service.py)
- new fixtures under `backend/tests/fixtures`

### Acceptance

- benchmark exists
- baseline vs improved runs are comparable
- human reviewers can judge clarification quality and bottleneck truth

### Codex Pack

`Pack A5: Insight Benchmark and Evaluation Harness`

---

## Stage 6: Promote to Primary Planning Path

### Purpose

Make the insight engine part of the real planning moat.

### Deliverables

1. Shadow mode removed or narrowed
2. Planning/runtime paths now depend on:
   - compiled insight state
   - gap detector
   - readiness gate

3. Safety and fallback rules:
   - if compiler fails, current path still works
   - if readiness state is absent, default to bounded current behavior

### Acceptance

- the primary planning path uses Phase A artifacts by default
- side failures remain non-fatal
- orchestrator-backed acceptance remains stable

### Codex Pack

`Pack A6: Production Promotion`

---

## 9. File-by-File Reuse Strategy

### Reuse as Main Inputs

- [backend/app/services/profile_context_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/profile_context_service.py)
- [backend/app/services/personalization/preference_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/personalization/engine.py)
- [backend/app/services/cognitive_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/cognitive_service.py)
- [backend/app/services/companion_state_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/companion_state_service.py)
- [backend/app/services/user_strategy_state_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_strategy_state_service.py)
- [backend/app/semantic/state_primitives.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/semantic/state_primitives.py)

### Reuse as Main Runtime Insertion Points

- [backend/app/orchestration/session_state_mixin.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/session_state_mixin.py)
- [backend/app/orchestration/situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [backend/app/orchestration/residual_diagnosis.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/residual_diagnosis.py)
- [backend/app/orchestration/decision_policy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/decision_policy.py)
- [backend/app/orchestration/prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py)
- [backend/app/orchestration/orchestrator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py)

### Reuse as Evaluation Layer

- [backend/app/services/experience_phase_evaluator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/experience_phase_evaluator.py)
- [backend/app/services/human_eval_review_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/human_eval_review_service.py)

### Do Not Rebuild

- a new profile persistence system
- a second memory stack
- a parallel planning router
- a second strategy state store

---

## 10. Acceptance Matrix

Phase A should be tested on at least these scenario classes:

1. `Cold-start exam prep`
   User has a deadline and materials but little structured self-description.

2. `Goal-known / baseline-unknown`
   User knows what they want but cannot describe current level.

3. `Overwhelmed user with fragmented signals`
   System must detect missing clarity before planning too deeply.

4. `Contradictory profile`
   Recent behavior and stored preference disagree.

5. `High-readiness user`
   Sparkle should avoid unnecessary questions and plan directly.

6. `Identity-fragile user`
   Sparkle must distinguish emotional collapse from lack of planning data.

---

## 11. Metrics

### Primary Metrics

- clarification precision
- critical-unknown recall
- bottleneck truth score
- planning readiness calibration
- reduced redundant question rate

### Product Metrics

- user agreement with inferred bottleneck
- user trust after clarification
- plan usefulness after clarification
- drop-off during cold start

### Failure Metrics

- over-questioning
- false certainty
- wrong bottleneck
- stale insight use
- contradictory profile not detected

---

## 12. What to Postpone

Do not fold these into Phase A unless clearly needed:

- broad execution delegation redesign
- community-driven insight loops
- achievement redesign
- major body-awareness runtime control
- large UI redesign beyond clarification visibility

---

## 13. Recommended Handoff Order

The best execution order for another Codex is:

1. `Pack A0: User Insight Baseline Audit`
2. `Pack A1: Profile Truth Compiler Shadow Runtime`
3. `Pack A2: Insight Gap Detector`
4. `Pack A3: Planning Readiness Gate`
5. `Pack A4: SituationBrief and Clarification UX Integration`
6. `Pack A5: Insight Benchmark and Evaluation Harness`
7. `Pack A6: Production Promotion`

This should be executed sequentially, with review between packs.

---

## 14. Final Rule

Phase A should always be judged by this question:

> **Did Sparkle become better at knowing what it needed to know about the user before making the plan?**

If yes, the phase is working.

If not, we are only adding architecture.

