# Sparkle Phase C Feedback and Growth Engine Execution Plan

> Date: 2026-04-05  
> Status: Active execution plan  
> Audience: Founder, chief designer, implementation Codex runs, backend, product, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_A_USER_INSIGHT_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_B_PLANNING_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`

---

## 0. Why This Phase Exists

Phase A made Sparkle better at understanding.

Phase B made Sparkle better at planning.

Phase C exists to answer the next decisive question:

> **Does Sparkle actually get better over time because of what happened, or does it only look adaptive within a single turn?**

This phase is about building the real:

> **Feedback Loop and Growth System**

The goal is not to collect more feedback for its own sake.
The goal is to make:

- future user understanding better
- future plans better
- future adaptations more accurate

without creating silent drift, permanent overfitting, or fake “learning.”

---

## 1. Phase C Goal

Phase C goal:

> **Make outcomes, repeated evidence, and human transcript review improve future understanding and future plan quality across sessions.**

If Phase C succeeds, Sparkle should become better at:

1. distinguishing one-turn noise from repeated evidence
2. learning whether a plan actually worked, not just whether the answer felt good
3. promoting only well-supported learning into episode and profile state
4. feeding validated outcomes back into future plan generation
5. turning human-eval findings into real product changes

---

## 2. Definition of Done

Phase C is done only when all of the following are true:

1. Sparkle has a canonical `plan outcome record` that can represent:
   - the plan or intervention that was tried
   - what outcome was observed
   - how strong the evidence is
   - whether the signal should stay session-local or promote upward

2. The system can distinguish:
   - turn-level feedback
   - short-horizon behavioral outcome
   - plan-level outcome
   - human-review product finding

3. Episode/profile promotion is governed by clear evidence thresholds and conflict checks.

4. Future planning can consume validated outcome learning, not just preferences or tone history.

5. Human transcript review has a real operational loop:
   - issue tags
   - repeated-failure detection
   - backlog feed
   - release gating for serious repeated failures

6. There is proof that later cycles get better because of earlier evidence, not just because the prompts changed.

---

## 3. Non-Goals

Phase C is not for:

- broad autonomous self-modification
- permanent learning from weak single-turn sentiment
- decorative “growth metrics”
- full system-layer self-governance
- inventing a second memory architecture
- replacing the current intervention or companion stack

This phase is specifically about:

> **feedback that improves future understanding and future plans**

---

## 4. Design Principles

### 4.1 Outcome Learning Beats Satisfaction Logging

The key question is not only “did the user like this?”

It is:

- did the user actually progress?
- did the plan fit reality?
- did the next cycle improve because of that?

### 4.2 Promotion Must Be Conservative

Do not let weak evidence become durable truth.

Session is cheap.
Episode is more expensive.
Profile is expensive.

### 4.3 Learning Must Stay Reversible

If evidence weakens or conflicts later, Sparkle must be able to demote or override earlier learning.

### 4.4 Human Review Is Part of the Product Loop

Transcript review is not side work.
It is part of the learning engine.

### 4.5 Phase C Must Improve Phase A and Phase B

If the growth system does not make:

- insight better
- planning better

then it is not doing its real job.

### 4.6 No Silent Drift

Phase C must preserve:

- bounded learning
- auditability
- conflict visibility
- constitutional stability

---

## 5. What We Must Reuse

Phase C should be built on top of current working components:

- [InterventionFeedbackBindingService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/intervention_feedback_binding_service.py)
- [BehavioralOutcomeTracker](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/behavioral_outcome_tracker.py)
- [ExperiencePhaseEvaluator](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/experience_phase_evaluator.py)
- [HumanEvalReviewService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/human_eval_review_service.py)
- [CompanionStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/companion_state_service.py)
- [UserStrategyStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_strategy_state_service.py)
- [SelfRevisionService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/self_revision_service.py)
- [RelationshipProfileService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/relationship_profile_service.py)
- [PlanStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_state_service.py)
- [PlanService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_service.py)
- [ExperienceActuator](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/experience_actuator.py)
- [GrowthDashboardService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/growth_dashboard_service.py)
- [SPARKLE_NORTH_STAR_HUMAN_EVALUATION_PROTOCOL_2026-04-04.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/evaluation/SPARKLE_NORTH_STAR_HUMAN_EVALUATION_PROTOCOL_2026-04-04.md)

We should not rebuild these as parallel systems.

---

## 6. Target Architecture for Phase C

Phase C should add four major runtime artifacts and one operating loop.

### 6.1 Artifact A: Plan Outcome Record

Purpose:

- represent what happened after a plan, plan revision, or intervention

Core outputs:

- `target_object`
- `target_layer`
- `target_hypothesis`
- `observed_outcome`
- `evidence_strength`
- `time_horizon`
- `promotion_recommendation`
- `reversal_candidate`

This is the core unit of Phase C learning.

### 6.2 Artifact B: Outcome Learning Layer

Purpose:

- convert repeated validated outcomes into future planning improvements

Core outputs:

- `validated_plan_learnings`
- `validated_insight_learnings`
- `rejected_learnings`
- `promotion_candidates`
- `demotion_candidates`

This is where feedback stops being local and starts affecting future cycles.

### 6.3 Artifact C: Promotion and Conflict Governor

Purpose:

- govern when learning can move from:
  - session -> episode
  - episode -> profile

Core outputs:

- `promotion_decision`
- `conflict_report`
- `evidence_threshold_result`
- `expiry_or_review_window`

### 6.4 Artifact D: Human-Eval Operations Loop

Purpose:

- convert evaluator transcript findings into product truth and backlog signals

Core outputs:

- normalized issue tags
- repeated failure clusters
- product-priority candidates
- release blockers

### 6.5 Artifact E: Outcome-to-Planning Bridge

Purpose:

- make future planning actually use validated learning

Core outputs:

- `planning_bias_constraints`
- `known_failure_avoidance_rules`
- `known_success_patterns`
- `plan_generation_hints_from_outcomes`

---

## 7. Canonical Learning Standard

Phase C should distinguish four evidence levels:

1. `Turn Reaction`
   The user said something felt helpful or unhelpful.

2. `Behavioral Signal`
   The user started, completed, avoided, delayed, or overloaded after a change.

3. `Plan Outcome`
   The plan or revision measurably improved or worsened progress.

4. `Human Truth`
   Transcript review shows a repeated diagnosis, timing, grounding, continuity, or adaptation issue.

Only levels 2 to 4 should meaningfully influence durable learning.

And no level should be promoted without:

- evidence source
- confidence
- freshness
- conflict check
- reversibility

---

## 8. Runtime Data Model

Phase C should add compact read models such as:

`PlanOutcomeRecord`

Suggested shape:

```text
PlanOutcomeRecord
  plan_id
  session_id
  intervention_id
  target_type
  outcome_type
  outcome_window
  outcome_signal
  evidence_sources
  confidence
  promotion_candidate
  reversal_candidate
```

`OutcomeLearningReport`

Suggested shape:

```text
OutcomeLearningReport
  validated_plan_learnings
  validated_insight_learnings
  promotion_candidates
  demotion_candidates
  ignored_noise
  conflict_report
```

Important rule:

Phase C should remain audit-first and evidence-first.
Do not allow silent durable writes from weak signals.

---

## 9. Multi-Stage Execution Plan

## Stage 0: Outcome Baseline Audit

### Purpose

Establish what feedback and outcome signals already exist and where the loop is still broken.

### Work

- audit current sources:
  - turn feedback
  - intervention acceptance
  - behavioral outcomes
  - plan progress
  - execution misses
  - human evaluation findings
- map which signals are:
  - session-only
  - promotable
  - currently unused
- define the first outcome taxonomy

### Outputs

- signal inventory
- current blind spots
- outcome taxonomy v1

### Acceptance

- the team can point to what counts as real evidence and what is still only sentiment or noise

---

## Stage 1: Plan Outcome Record

### Purpose

Create one canonical record for plan and intervention outcomes.

### Work

- define outcome record schema
- map current sources into it
- support:
  - plan attempts
  - replans
  - interventions
  - behavioral completion / failure
- make it auditable and append-only

### Suggested files

- `backend/app/services/plan_outcome_service.py`
- `backend/app/models/` if persistence is required
- tests under `backend/tests/unit/`

### Acceptance

- Sparkle can represent what happened after help, not just what was said during help

---

## Stage 2: Outcome Learning Layer

### Purpose

Turn repeated outcomes into candidate learnings.

### Work

- aggregate outcome records by:
  - user
  - plan pattern
  - intervention family
  - strategy setting
  - overload / capacity pattern
- separate:
  - validated learning
  - weak signal
  - contradictory signal
  - stale signal
- produce a compact learning report

### Suggested files

- `backend/app/services/outcome_learning_service.py`
- tests under `backend/tests/unit/`

### Acceptance

- the system can say not just “feedback was received,” but “this pattern probably works” or “this pattern repeatedly fails”

---

## Stage 3: Promotion and Conflict Governor

### Purpose

Make cross-session learning safe.

### Work

- define promotion thresholds
- define conflict resolution between:
  - new evidence
  - older promoted evidence
  - profile preferences
  - companion-state tendencies
  - strategy history
- define demotion / expiry rules
- ensure repeated evidence is required before profile-level promotion

### Suggested files

- `backend/app/services/companion_state_service.py`
- `backend/app/services/user_strategy_state_service.py`
- `backend/app/services/self_revision_service.py`
- new governor module if needed

### Acceptance

- session noise does not become profile truth
- real repeated evidence can become durable learning
- conflicts are visible, not hidden

---

## Stage 4: Outcome-to-Planning Bridge

### Purpose

Make validated learning improve future planning.

### Work

- feed validated learnings into:
  - `SituationBrief`
  - planning strategy compiler
  - plan-quality gate
  - adaptive replanner
- examples:
  - known overload pattern -> default lighter first step
  - known grounding benefit -> stronger retrieval requirement
  - known failure to follow dense plans -> higher scaffold level
  - known success with short checkpoint cadence -> prefer that rhythm

### Suggested files

- `backend/app/orchestration/situation_brief.py`
- `backend/app/orchestration/planning_strategy_compiler.py`
- `backend/app/orchestration/plan_quality_gate.py`
- `backend/app/orchestration/adaptive_replanner.py`

### Acceptance

- future plans visibly differ because of validated prior outcomes
- those differences are explainable and reversible

---

## Stage 5: Human-Eval Operations Loop

### Purpose

Make human transcript review operational instead of optional.

### Work

- extend issue taxonomy
- define repeated-failure thresholds
- connect findings to backlog labels or release blockers
- define a fixed operating cadence:
  - run review
  - summarize
  - escalate repeated failures
  - feed product decisions

### Suggested files

- `backend/app/services/human_eval_review_service.py`
- `scripts/review_human_eval_run.py`
- docs under `docs/product/evaluation/` and `docs/verification/`

### Acceptance

- repeated transcript failures become explicit product priorities
- the next sprint can be justified by actual human evidence

---

## Stage 6: Plan Outcome Evaluation Harness

### Purpose

Prove that Phase C actually improves later cycles.

### Work

- define a benchmark that compares:
  - first-cycle plan quality
  - later-cycle plan quality after outcome learning
- include:
  - improvement from failure
  - stability after success
  - no silent overfitting
- score:
  - better later plans
  - fewer repeated mistakes
  - preserved trust
  - low drift

### Suggested files

- `backend/app/services/plan_outcome_evaluator.py`
- fixtures under `backend/tests/fixtures/`
- tests under `backend/tests/integration/`

### Acceptance

- later cycles are measurably better because of validated learning

---

## Stage 7: Production Promotion and Freeze

### Purpose

Lock Phase C once the learning loop is good enough to stop churn.

### Work

- add observability for:
  - promotion counts
  - demotion counts
  - ignored-noise counts
  - repeated-failure tags
  - outcome-driven plan changes
- freeze the promotion contract
- document human-eval operations

### Acceptance

- the growth engine can remain stable while the team moves on to body-awareness and Live Alpha truth

---

## 10. Codex Handoff Packs

## Pack C0: Outcome Baseline Audit

### Goal

Map the current feedback and outcome surface.

### Ownership

- verification docs
- signal inventory
- taxonomy draft

### Files to touch

- `docs/verification/`
- `backend/tests/`

### Do not do

- do not change runtime behavior yet

---

## Pack C1: Plan Outcome Record

### Goal

Create one canonical outcome record.

### Ownership

- service
- schema
- unit tests

### Files to touch

- `backend/app/services/`
- `backend/app/models/` if needed
- `backend/tests/unit/`

### Do not do

- do not create a second memory system

---

## Pack C2: Outcome Learning Layer

### Goal

Aggregate repeated evidence into candidate learning.

### Ownership

- outcome learning service
- evidence thresholds
- conflict hooks

### Files to touch

- `backend/app/services/`
- `backend/tests/unit/`

### Do not do

- do not silently promote weak evidence

---

## Pack C3: Promotion and Conflict Governor

### Goal

Make cross-session learning safe and bounded.

### Ownership

- promotion logic
- conflict resolution
- demotion / expiry

### Files to touch

- `backend/app/services/companion_state_service.py`
- `backend/app/services/user_strategy_state_service.py`
- `backend/app/services/self_revision_service.py`
- tests

### Do not do

- do not let one-turn praise write profile truth

---

## Pack C4: Outcome-to-Planning Bridge

### Goal

Feed validated learning back into future plans.

### Ownership

- situation brief integration
- planning strategy integration
- replanning integration

### Files to touch

- `backend/app/orchestration/situation_brief.py`
- `backend/app/orchestration/planning_strategy_compiler.py`
- `backend/app/orchestration/plan_quality_gate.py`
- `backend/app/orchestration/adaptive_replanner.py`

### Do not do

- do not add unexplained planning biases

---

## Pack C5: Human-Eval Ops Loop

### Goal

Operationalize transcript review into product action.

### Ownership

- issue taxonomy
- repeated-failure summarization
- scripts and docs

### Files to touch

- `backend/app/services/human_eval_review_service.py`
- `scripts/review_human_eval_run.py`
- `docs/product/evaluation/`
- `docs/verification/`

### Do not do

- do not leave human review as a passive summary only

---

## Pack C6: Outcome Evaluation Harness

### Goal

Prove later cycles improve because of feedback.

### Ownership

- fixtures
- evaluator
- integration tests

### Files to touch

- `backend/app/services/`
- `backend/tests/integration/`
- `backend/tests/fixtures/`

### Do not do

- do not claim Phase C complete without multi-cycle proof

---

## 11. What Must Be True Before Starting Phase D

Before moving to body-awareness that governs, all of these should be true:

1. Phase A is frozen and stable.
2. Phase B is accepted and has a stable contract.
3. Phase C can distinguish noise from validated learning.
4. Future plans measurably improve because of previous outcomes.
5. Human-eval findings can create actual product priorities and release blockers.

If these are not true, do not declare the evolution engine real.

---

## 12. Chief-Designer Guidance

The main danger in Phase C is drift into one of three traps:

1. `Sentiment drift`
   Mistaking “the user liked it” for “the plan worked.”

2. `Memory drift`
   Promoting weak evidence into profile truth too early.

3. `Evaluation drift`
   Treating human transcript review as a ceremony instead of a decision engine.

The correct Phase C mentality is:

> **learn conservatively, promote only validated evidence, and make later understanding and later plans better because of what reality taught Sparkle**

That is the real evolution engine.
