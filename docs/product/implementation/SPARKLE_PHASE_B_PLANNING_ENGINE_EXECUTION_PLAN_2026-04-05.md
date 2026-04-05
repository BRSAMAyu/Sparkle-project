# Sparkle Phase B Planning Engine Execution Plan

> Date: 2026-04-05  
> Status: Active execution plan  
> Audience: Founder, chief designer, implementation Codex runs, backend, evaluation, product  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_A_USER_INSIGHT_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`

---

## 0. Why This Phase Exists

Phase A made Sparkle better at knowing when it does not know enough.

Phase B exists to answer the next harder question:

> **When Sparkle does know enough, can it generate a plan that is materially better than raw frontier-model use for ordinary users?**

This phase is about winning the second real moat:

> **plan quality**

Sparkle should not merely produce plausible plans.
It should produce plans that are:

- better grounded
- better paced
- better sequenced
- more adaptive
- more honest about uncertainty
- easier for non-expert users to actually follow

---

## 1. Phase B Goal

Phase B goal:

> **Turn Sparkle’s current planning runtime into a benchmarkable Planning Engine that can produce better plans and better next moves than raw AI use for ordinary users.**

If Phase B succeeds, Sparkle should become better at:

1. converting insight into an actual planning strategy
2. generating plans with stronger task sequence, pacing, and realism
3. grounding plans in user materials, constraints, and readiness
4. making plans usable for non-expert users, not just impressive to engineers
5. revising or downgrading plans when confidence, readiness, or evidence is weak

---

## 2. Definition of Done

Phase B is done only when all of the following are true:

1. Sparkle has a canonical `plan quality contract` for planning turns.
2. Planning behavior is explicitly shaped by:
   - Phase A insight state
   - `SituationBrief`
   - residual diagnosis
   - `UserStrategyState`
   - user materials / grounding state
   - real deadline and capacity constraints
3. Planning turns produce plans that include:
   - a clear goal frame
   - explicit assumptions
   - a realistic workload and pacing model
   - milestones or phases
   - concrete next actions
   - adaptation triggers
   - fallback / downgrade logic when reality changes
4. Sparkle has a plan-quality gate that can reject, downgrade, or revise weak plans before they reach the user.
5. There is a benchmark harness comparing Sparkle against raw-model baselines on the same user dossiers and materials.
6. Sparkle wins a meaningful share of benchmark scenarios on a human-readable rubric, not just on internal heuristics.

---

## 3. Non-Goals

Phase B is not for:

- full execution autonomy
- broad new agent creation
- replacing the orchestrator
- replacing `LangGraphPlanner`
- building a parallel plan stack disconnected from current runtime
- expanding into many new domains before the study-planning moat is strong
- decorative UX work that does not improve plan quality

This phase is specifically about:

> **turning user understanding into better plans**

---

## 4. Design Principles

### 4.1 Plan Quality Beats Architecture Novelty

Do not build new abstractions unless they improve real plan quality.

### 4.2 One Planning Stack

Reuse and strengthen the existing planning path.
Do not create a second planner, second plan schema, or second review path.

### 4.3 Plans Must Be Growth-First

A Sparkle plan should optimize for:

- realistic progress
- retained agency
- reduced overload
- truthfulness about uncertainty
- compounding capability, not just task volume

### 4.4 Plans Must Be Non-Expert Friendly

The target user is not a prompt engineer.
The plan must be immediately understandable and usable.

### 4.5 Grounding Is Mandatory When Material Exists

If the user has attached or relevant materials, the plan should use them.
Planning without available evidence should count as lower quality.

### 4.6 Planning Should Be Reversible

Weak or medium-confidence plans should:

- declare assumptions
- expose uncertainty
- offer a provisional path when necessary

### 4.7 Benchmarking Is Part of the Product

Phase B is not done because the code looks good.
It is done when Sparkle repeatedly beats raw-model baselines on meaningful cases.

---

## 5. What We Must Reuse

Phase B should be built on top of current working components:

- [SituationBriefBuilder](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [ResidualDiagnosisRuntime](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/residual_diagnosis.py)
- [DecisionPolicyCompiler](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/decision_policy.py)
- [ExperienceActuator](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/experience_actuator.py)
- [ValidationEngine](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/validation_engine.py)
- [LangGraphPlanner](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/lang_graph_planner.py)
- [PlanReviewService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/plan_review_service.py)
- [GroundingValidator](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/grounding_validator.py)
- [AdaptiveReplanner](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/adaptive_replanner.py)
- [PlanStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_state_service.py)
- [PlanService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_service.py)
- [MaterialRetrievalTools](/Users/brsama/code/GitHub/Sparkle-project/backend/app/tools/material_retrieval_tools.py)
- [GrowthStrategyTools](/Users/brsama/code/GitHub/Sparkle-project/backend/app/tools/growth_strategy_tools.py)
- [StandardWorkflow](/Users/brsama/code/GitHub/Sparkle-project/backend/app/agents/standard_workflow.py)
- [Prompts](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py)

We should not rebuild these as parallel systems.

---

## 6. Target Architecture for Phase B

Phase B should add four major runtime artifacts and one benchmark layer.

### 6.1 Artifact A: Growth-First Plan Contract

Purpose:

- define what a Sparkle plan must contain to count as high quality

Core outputs:

- `plan_goal_frame`
- `plan_assumptions`
- `plan_scope_and_horizon`
- `plan_structure`
- `plan_next_actions`
- `plan_grounding_basis`
- `plan_risks`
- `plan_adaptation_triggers`

Important rule:

This is not a separate persistence model first.
It is a planning-quality contract used in runtime generation, validation, and evaluation.

### 6.2 Artifact B: Planning Strategy Compiler

Purpose:

- convert runtime insight into a concrete planning recipe

Core outputs:

- `plan_type`
- `planning_depth`
- `pacing_profile`
- `scaffold_level`
- `checkpoint_cadence`
- `grounding_mode`
- `assumption_policy`
- `fallback_policy`

This is the bridge between understanding and actual plan generation.

### 6.3 Artifact C: Plan Quality Gate

Purpose:

- score and validate generated plans before they are shown or persisted

Core outputs:

- `quality_score`
- `fit_score`
- `grounding_score`
- `feasibility_score`
- `next_action_score`
- `adaptation_score`
- `decision` (`approve`, `revise`, `downgrade_to_provisional`, `ask_more`)

### 6.4 Artifact D: Plan Revision Contract

Purpose:

- ensure adaptation and replanning preserve quality instead of creating drift

Core outputs:

- `why_plan_changed`
- `what_assumption_failed`
- `what_stays`
- `what_changes`
- `new_next_action`

### 6.5 Artifact E: Planning Benchmark Harness

Purpose:

- compare Sparkle planning against strong raw-model baselines

Core outputs:

- scenario scorecards
- baseline comparison tables
- win / tie / loss summary
- human-review notes

---

## 7. Canonical Plan Quality Standard

Every strong Sparkle plan should explicitly cover:

1. `Goal Frame`
   What exactly are we trying to achieve, by when, and why now?

2. `Assumptions`
   What is Sparkle assuming because the user did not provide enough information?

3. `Readiness Fit`
   Is this a full plan, provisional plan, or first-step-only plan?

4. `Workload Model`
   How much time, energy, and difficulty is this plan assuming?

5. `Sequence`
   What comes first, second, and third, and why in that order?

6. `Grounding`
   Which user materials, known weak spots, and profile truths shaped the plan?

7. `Next Move`
   What should the user do next, ideally in the next day?

8. `Adaptation Trigger`
   What signal should cause the plan to change?

9. `Failure Guard`
   What should Sparkle do if the plan turns out too hard, too vague, or too optimistic?

If a plan does not satisfy most of these, it is not high quality.

---

## 8. Runtime Data Model

Phase B should add compact planning read models such as:

`CompiledPlanningStrategy`

Suggested shape:

```text
CompiledPlanningStrategy
  plan_type
  plan_horizon
  plan_depth
  scaffold_level
  pacing_profile
  checkpoint_cadence
  grounding_mode
  assumption_policy
  fallback_policy
  required_plan_sections
```

`PlanQualityReport`

Suggested shape:

```text
PlanQualityReport
  overall_score
  fit_score
  feasibility_score
  grounding_score
  next_action_score
  adaptation_score
  issues
  decision
```

Important rule:

Phase B should stay read-first and validation-first before adding new persistent plan metadata.

---

## 9. Multi-Stage Execution Plan

## Stage 0: Phase B Baseline Audit

### Purpose

Establish the real current state of planning quality before changing behavior.

### Work

- audit all current planning entry points:
  - `create_plan`
  - `time_planning`
  - plan-like routing through `ValidationEngine`
  - plan review path
  - adaptive replanning path
- collect 8 to 12 representative planning scenarios
- record current outputs from Sparkle
- record raw-model baseline outputs from the same user dossiers
- define the benchmark rubric

### Outputs

- scenario set
- baseline transcript set
- current-gap summary
- benchmark rubric v1

### Suggested files

- new verification doc under `docs/verification/`
- new test / fixture folder under `backend/tests/benchmark/` or `backend/tests/integration/`

### Acceptance

- the team can point to concrete reasons current Sparkle plans are better, worse, or equal to raw baselines

---

## Stage 1: Growth-First Plan Contract

### Purpose

Make plan quality explicit instead of leaving it to general LLM style.

### Work

- define the canonical plan sections
- define what counts as:
  - full plan
  - provisional plan
  - next-step-only response
- define required fields for exam sprint planning first
- specify what must be included when materials exist
- specify what must be included when Phase A readiness is medium vs high

### Suggested implementation

- add a new planning contract module, likely under `backend/app/orchestration/`
- keep it separate from `ExecutablePlan`
- use it for generation guidance and review, not as a replacement DAG schema

### Suggested files

- `backend/app/orchestration/plan_quality_contract.py`
- tests under `backend/tests/unit/`

### Acceptance

- there is one canonical, code-readable contract for what a good plan must contain
- `PlanReviewService` and prompt shaping can read this contract

---

## Stage 2: Planning Strategy Compiler

### Purpose

Turn insight into a planning recipe before asking the model to generate a plan.

### Work

- compile from:
  - `SituationBrief`
  - Phase A readiness
  - residual diagnosis
  - strategy state
  - material availability
  - deadline intensity
  - overload / recovery signals
- derive:
  - plan shape
  - plan scope
  - pacing
  - required grounding
  - allowed optimism level
  - checkpoint cadence

### Suggested implementation

- add a planning compiler next to `decision_policy.py`, not inside it
- feed its output into prompt construction and plan validation

### Suggested files

- `backend/app/orchestration/planning_strategy_compiler.py`
- `backend/app/orchestration/situation_brief.py`
- `backend/app/orchestration/prompts.py`

### Acceptance

- given the same runtime input, Sparkle derives a deterministic planning strategy
- medium-readiness and high-readiness turns produce materially different planning profiles

---

## Stage 3: Plan Generation Integration

### Purpose

Make the actual planning path obey the new contract and strategy compiler.

### Work

- integrate planning strategy into:
  - `ValidationEngine`
  - prompt construction
  - `LangGraphPlanner`
  - `StandardWorkflow` plan-response shaping
- ensure grounded planning behavior:
  - if materials exist and strategy says grounding is required, plan generation should use them
- ensure Phase A provisional mode is respected:
  - assumptions are surfaced
  - plan scope is narrowed when needed

### Suggested files

- `backend/app/orchestration/validation_engine.py`
- `backend/app/orchestration/prompts.py`
- `backend/app/orchestration/lang_graph_planner.py`
- `backend/app/agents/standard_workflow.py`

### Acceptance

- planning responses now visibly include the required contract sections
- provisional planning does not masquerade as certainty
- plans with attached materials actually reference those materials

---

## Stage 4: Plan Quality Gate

### Purpose

Prevent weak plans from reaching the user as if they were strong.

### Work

- build a plan-quality evaluator or gate
- score:
  - goal fit
  - deadline/capacity realism
  - grounding use
  - sequencing quality
  - next-step actionability
  - adaptation quality
  - assumption honesty
- integrate with `PlanReviewService`
- define decisions:
  - approve
  - revise
  - downgrade to provisional
  - ask clarification

### Suggested files

- `backend/app/orchestration/plan_quality_gate.py`
- `backend/app/orchestration/plan_review_service.py`
- `backend/tests/unit/`

### Acceptance

- obviously weak plans are caught
- the gate can explain why a plan is weak
- the gate does not over-block strong plans

---

## Stage 5: Plan Revision and Adaptation Quality

### Purpose

Ensure replanning improves the plan instead of just changing it.

### Work

- connect the planning contract to `AdaptiveReplanner`
- require revision outputs to state:
  - what changed
  - why it changed
  - what remains stable
  - what the next action now is
- make sure overload, missed progress, and clarified user constraints lead to cleaner revisions

### Suggested files

- `backend/app/orchestration/adaptive_replanner.py`
- `backend/app/services/plan_state_service.py`
- `backend/app/services/plan_service.py`

### Acceptance

- replans preserve continuity
- revisions feel like intelligent adaptation, not random replacement

---

## Stage 6: Benchmark Harness Against Raw Models

### Purpose

Prove that Sparkle is actually better.

### Benchmark Scenarios

At minimum:

1. cold-start 14-day thermodynamics exam sprint
2. overloaded student with low capacity and high urgency
3. user with uploaded materials and weak spots
4. contradictory self-report vs profile evidence
5. vague goal that requires clarification before planning
6. plan revision after missed execution

### Baselines

For each scenario, compare:

- Sparkle current planning stack
- raw frontier model prompt baseline A
- raw frontier model prompt baseline B

### Rubric

Score each output on:

1. `understanding fit`
2. `constraint realism`
3. `plan sequence quality`
4. `grounding quality`
5. `next-action usefulness`
6. `adaptation / fallback quality`
7. `non-expert usability`
8. `trustworthiness`

### Acceptance

Phase B should not be called complete until Sparkle has a credible win profile, such as:

- wins or ties on most scenarios overall
- clearly wins on grounding and non-expert usability
- does not lose badly on realism or clarity

Exact numeric thresholds can be tuned, but the benchmark must be real.

---

## Stage 7: Production Promotion and Freeze

### Purpose

Lock Phase B once the planning engine is good enough to stop churn.

### Work

- add observability for plan-quality metrics
- document the contract and benchmark expectations
- freeze the Phase B runtime interfaces
- only reopen the planning core when:
  - benchmarks fail
  - human eval identifies repeated weakness
  - Phase C outcome evidence proves the planning logic is wrong

### Acceptance

- Phase B can remain stable while the team moves on to plan-outcome learning and broader product proof

---

## 10. Codex Handoff Packs

## Pack B0: Planning Baseline Audit

### Goal

Create the current-state map and benchmark rubric.

### Ownership

- verification artifacts
- benchmark fixtures
- scenario definitions

### Files to touch

- `backend/tests/integration/`
- `backend/tests/benchmark/`
- `docs/verification/`

### Do not do

- do not change planning behavior yet

---

## Pack B1: Plan Contract

### Goal

Define one canonical Growth-First plan contract.

### Ownership

- contract module
- unit tests
- prompt-section requirements

### Files to touch

- `backend/app/orchestration/`
- `backend/tests/unit/`

### Do not do

- do not replace `ExecutablePlan`
- do not create a second DAG system

---

## Pack B2: Planning Strategy Compiler

### Goal

Compile planning strategy from runtime insight.

### Ownership

- new compiler
- `SituationBrief` integration
- prompt shaping

### Files to touch

- `backend/app/orchestration/planning_strategy_compiler.py`
- `backend/app/orchestration/situation_brief.py`
- `backend/app/orchestration/prompts.py`

### Do not do

- do not bury this logic as prompt-only text

---

## Pack B3: Generation Integration

### Goal

Make the live planning path obey the new contract and strategy.

### Ownership

- validation path
- plan generation path
- plan response shaping

### Files to touch

- `backend/app/orchestration/validation_engine.py`
- `backend/app/orchestration/lang_graph_planner.py`
- `backend/app/agents/standard_workflow.py`
- `backend/app/orchestration/prompts.py`

### Do not do

- do not create a separate planner agent

---

## Pack B4: Plan Quality Gate

### Goal

Score and stop weak plans.

### Ownership

- plan-quality gate
- review integration
- failure routing

### Files to touch

- `backend/app/orchestration/plan_quality_gate.py`
- `backend/app/orchestration/plan_review_service.py`
- `backend/tests/unit/`

### Do not do

- do not make this a vague score-only tool without enforceable decisions

---

## Pack B5: Replanning Quality

### Goal

Make revisions coherent and explainable.

### Ownership

- revision contract
- adaptive replanner integration
- plan continuity tests

### Files to touch

- `backend/app/orchestration/adaptive_replanner.py`
- `backend/app/services/plan_state_service.py`
- `backend/app/services/plan_service.py`

### Do not do

- do not rewrite the whole replanning system

---

## Pack B6: Benchmark Harness

### Goal

Prove Sparkle planning quality against raw baselines.

### Ownership

- scenario fixtures
- scoring harness
- comparison docs

### Files to touch

- `backend/tests/integration/`
- `backend/tests/benchmark/`
- `docs/verification/`

### Do not do

- do not mark Phase B complete without baseline comparison

---

## 11. What Must Be True Before Starting Phase C

Before moving to the feedback / growth system phase, all of these should be true:

1. Phase A is frozen and stable enough not to churn.
2. Phase B has one canonical plan-quality contract.
3. Sparkle can produce strong full plans and honest provisional plans.
4. Weak plans are caught before they are shipped.
5. At least one benchmark set shows Sparkle is better than raw-model planning on meaningful cases.

If these are not true, do not declare the planning moat won.

---

## 12. Chief-Designer Guidance

The main danger in Phase B is drift into one of three traps:

1. `Architectural drift`
   Building a second planner because the current one feels messy.

2. `Prompt drift`
   Writing beautiful plan instructions without adding enforceable plan-quality gates.

3. `Benchmark drift`
   Deciding Sparkle is “better” because the outputs feel sophisticated rather than because they win against real baselines.

The correct Phase B mentality is:

> **use the current organism, make planning quality explicit, benchmark it honestly, and do not move on until Sparkle can win its wedge**

That wedge is simple:

> **for ordinary users, on important goals, Sparkle should produce better plans than raw AI use**

That is what this phase must prove.
