# Sparkle AI System Semantic Control Execution Plan

> Date: 2026-04-06  
> Status: Active implementation plan  
> Audience: Founder, chief designer, implementation Codex runs, orchestration, backend, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_STAGE2_PRODUCT_COHERENCE_EXECUTION_PLAN_2026-04-06.md`
> - `docs/product/implementation/SPARKLE_PHASE_A_USER_INSIGHT_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_B_PLANNING_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_C_FEEDBACK_AND_GROWTH_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_D_BODY_AWARENESS_AND_CAPABILITY_GOVERNANCE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_E_FIVE_LAYER_LEARNING_SYSTEM_EXECUTION_PLAN_2026-04-05.md`

---

## 0. Why This Plan Exists

Sparkle’s AI system now has real internal control layers:

- residual diagnosis
- decision policy
- planning strategy
- body-awareness guidance
- five-layer learning hints
- strategy state

That is good.

But we now have a serious model-guidance risk:

> **internal strategy tags are reaching the model as compact labels without enough semantic explanation of what they mean behaviorally**

Examples include:

- `experience_mode`
- `intervention_family`
- `loop_type`
- `primary_residual`
- `plan_mode`
- `plan_depth`
- `pacing_profile`
- `grounding_mode`
- `fallback_policy`
- `session_mode`

These tags are useful for the runtime.

They are **not** sufficient by themselves as model-facing control language.

If the model sees opaque or partially explained tags, several failures follow:

1. the model may only weakly follow strategy
2. the model may treat internal labels as style hints instead of behavioral constraints
3. strategy meanings may drift across prompt surfaces
4. planning quality may depend too much on the model “guessing what we meant”
5. future contributors may add more labels without adding semantic doctrine

This plan fixes that class of problem.

---

## 1. The Core Diagnosis

Sparkle currently has a **semantic-control gap**.

### 1.1 What We Have

We have:

- internal control state
- deterministic compilers
- prompt wiring
- runtime gating
- evaluation harnesses

### 1.2 What We Lack

We do **not yet** have:

- one canonical model-facing ontology of strategy terms
- one doctrine layer that explains each tag in behavioral language
- one consistent rendering path from internal strategy to AI instructions
- one validation layer that checks whether the final answer actually follows the intended strategy
- one anti-regression harness that proves the model understands our strategy vocabulary

### 1.3 The Real Problem

The problem is not “we have too many tags.”

The problem is:

> **the AI system’s control language is still partly written for the runtime, not for the model**

This is dangerous because the AI system is now the core of the product.

We should treat this as one of the highest-leverage improvements in the whole project.

---

## 2. Stage Goal

The goal of this plan is:

> **Turn Sparkle’s internal strategy vocabulary into a fully explained, behaviorally grounded, testable control language that the model can reliably follow.**

When this plan is complete, Sparkle should no longer depend on raw labels alone.

Instead, Sparkle should provide the model with:

- clear semantic meanings
- allowed behaviors
- forbidden behaviors
- priority order
- response-shape consequences
- tool and grounding implications
- examples of correct execution

---

## 3. Definition of Done

This work is complete only when all of these are true:

1. every model-facing control tag has one canonical definition
2. the model no longer sees raw tags without semantic explanation
3. strategy meaning is rendered consistently across prompt surfaces
4. the final response can be checked against the intended strategy
5. new strategy tags cannot be added without also defining their semantics
6. the north-star journey shows better strategy compliance and clearer behavior

---

## 4. Non-Goals

This plan is **not** for:

- replacing all internal tags with prose everywhere
- removing structured runtime state
- rebuilding the decision policy from scratch
- adding more strategy tags
- making prompts much longer without discipline

The goal is:

> **keep internal structure for the system, but translate it into strong model-facing doctrine**

---

## 5. The Strategy Vocabulary That Must Be Governed

The first pass must cover all AI-facing control vocabularies that materially affect generation.

### 5.1 Decision Vocabulary

- `primary_residual`
- `secondary_residual`
- `loop_type`
- `experience_mode`
- `intervention_family`
- `reversibility_level`

### 5.2 Planning Vocabulary

- `plan_mode`
- `plan_horizon`
- `plan_depth`
- `scaffold_level`
- `pacing_profile`
- `checkpoint_cadence`
- `grounding_mode`
- `assumption_policy`
- `fallback_policy`

### 5.3 Strategy-State Vocabulary

- `session_mode`
- `push_vs_support`
- `intervention_intensity`
- `explanation_style`
- `retrieval_emphasis`

### 5.4 Body-Awareness Vocabulary

- `primary_subsystem`
- `capability_selection_summary`
- bounded adjustment types
- model-tier hints
- grounding-path hints

### 5.5 Learning Vocabulary

- `five_layer_growth_summary`
- outcome-learning hints that influence planning
- conflict/demotion warnings that should affect confidence and caution

---

## 6. Design Principles

### 6.1 No Opaque Tags To The Model

The model should never receive a bare label when that label carries important behavioral meaning.

Bad:

- `experience_mode = stabilize`

Good:

- `This turn is in stabilize mode: reduce load, lower intensity, avoid expanding scope, and help the user regain control before pushing progress.`

### 6.2 One Canonical Semantic Source

There must be one source of truth for:

- tag name
- human meaning
- behavioral goal
- do
- do not
- preferred response shape
- grounding/tool implications

### 6.3 Runtime Structure And Model Semantics Must Stay Coupled

If a runtime tag changes meaning, the model-facing doctrine must change too.

No silent drift is allowed.

### 6.4 Strategy Must Be Checkable

We should be able to evaluate whether a response:

- actually clarified when it should
- actually reduced load when in stabilize mode
- actually used user materials when grounding was mandatory
- actually avoided fake certainty in normative mode

### 6.5 Fewer, Sharper Controls Beat More Raw Labels

Do not solve this by multiplying tags.
Solve it by making the existing controls legible and behaviorally strong.

---

## 7. Multi-Stage Execution Plan

## 7.1 Pack AI-0: AI Control Vocabulary Audit

### Purpose

Build a full inventory of every model-facing strategy/control tag.

### Tasks

- search all orchestration, planner, prompt, and tool-generation seams
- inventory every enum-like control value that reaches the model
- classify each one:
  - runtime-only
  - model-facing
  - mixed
- identify where raw values are surfaced directly
- identify duplicate vocabularies or near-synonyms

### Expected Artifacts

- one AI control vocabulary inventory doc
- one machine-readable fixture listing:
  - term
  - source file
  - current meaning
  - current prompt exposure
  - risk level

### Acceptance Criteria

- no important model-facing tag is missing from the inventory
- current exposure points are explicit

---

## 7.2 Pack AI-1: Canonical Strategy Ontology

### Purpose

Create the single source of truth for model-facing control semantics.

### Tasks

- define a canonical ontology module, likely under:
  - `backend/app/orchestration/ai_strategy_ontology.py`
  - or `backend/app/services/ai_strategy_ontology.py`
- for every governed tag, define:
  - identifier
  - short label
  - behavioral meaning
  - target user effect
  - positive instructions
  - negative instructions
  - response shape guidance
  - grounding/tool implications
  - compatibility notes
- define which terms are internal-only and should never be exposed directly

### Acceptance Criteria

- every model-facing strategy term has one canonical definition
- new terms cannot be added casually without semantic definition

---

## 7.3 Pack AI-2: Doctrine Renderer

### Purpose

Replace raw tag exposure with semantically grounded model instructions.

### Tasks

- build a renderer that converts:
  - `decision_context`
  - `planning_strategy`
  - `body_awareness_guidance`
  - selected strategy-state fields
into:
  - natural-language doctrine for the model
  - compact but behaviorally explicit guidance
- update:
  - [prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py)
  - [lang_graph_planner.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/lang_graph_planner.py)
  - any other prompt-building seams
- ensure the raw labels can remain in metadata/debugging, but not as the primary AI control language

### Acceptance Criteria

- raw labels like `stabilize`, `trajectory_review`, `mandatory`, `provisional` are no longer presented to the model without explanation
- the doctrine is compact enough for runtime use
- prompt duplication is reduced, not increased chaotically

---

## 7.4 Pack AI-3: Action Binding and Response Contract

### Purpose

Make sure strategy labels do not merely decorate prompts, but actually shape generated behavior.

### Tasks

- define response-contract consequences for major strategy modes
- examples:
  - `clarify` means ask one high-value question before planning
  - `stabilize` means reduce scope, reduce pressure, avoid heavy multi-step demands
  - `decide` + normative means surface criteria and tradeoffs without fake certainty
  - `grounding_mode=mandatory` means user-material evidence must appear explicitly
  - `plan_mode=provisional` means assumptions must be named
- wire those contracts into:
  - existing validation/review gates
  - planner constraints
  - response checks where appropriate

### Acceptance Criteria

- every critical strategy term has a visible behavioral consequence
- a strategy violation can be detected and flagged

---

## 7.5 Pack AI-4: Prompt Surface Consolidation

### Purpose

Reduce semantic drift caused by multiple prompt surfaces rendering strategy differently.

### Tasks

- identify all prompt surfaces that currently express strategy
- consolidate them into a smaller number of stable sections
- ensure:
  - responder
  - planner
  - tool-use path
  - special generation flows
  all receive compatible semantics

### Acceptance Criteria

- one strategy meaning is not rendered differently in three places
- prompt sections have clear ownership and purpose

---

## 7.6 Pack AI-5: Strategy Understanding Evaluation Harness

### Purpose

Test whether the AI system actually follows the semantic control layer.

### Tasks

- build evaluation cases for:
  - low-readiness clarify
  - stabilize vs mobilize
  - explain vs decide
  - normative uncertainty
  - mandatory grounding
  - provisional planning with explicit assumptions
  - identity-fragile reframe
- compare:
  - raw-tag prompt behavior
  - semantically rendered doctrine behavior
- score:
  - behavior compliance
  - response-shape compliance
  - grounding compliance
  - trust and tone compliance

### Acceptance Criteria

- the semantic-control version performs clearly better than the raw-label version
- failures are attributable and inspectable

---

## 7.7 Pack AI-6: Observability and Runtime Traceability

### Purpose

Make AI strategy compliance inspectable in live runs.

### Tasks

- emit metadata for:
  - selected strategy terms
  - rendered semantic doctrine summary
  - expected response contract
  - observed compliance flags where possible
- expose enough trace data for transcript review without bloating the user-facing experience

### Acceptance Criteria

- transcript reviewers can see what strategy was intended
- mismatches between intended and produced behavior are traceable

---

## 7.8 Pack AI-7: Stage 2 Product Proof Integration

### Purpose

Use the improved semantic-control layer in the real product loop.

### Tasks

- re-run the full-stack north-star journey
- specifically inspect:
  - whether clarification is better timed
  - whether plans follow the intended mode more strongly
  - whether adaptation language is more coherent
  - whether strategy feels less like hidden internal machinery and more like wise behavior
- feed results into the Stage 2 human evaluation loop

### Acceptance Criteria

- the real product shows more reliable strategy compliance
- human review reports fewer “the AI had the right policy tag but wrong behavior” failures

---

## 8. Required Code Areas

The first pass should expect to touch some or all of:

- [decision_policy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/decision_policy.py)
- [residual_diagnosis.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/residual_diagnosis.py)
- [planning_strategy_compiler.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/planning_strategy_compiler.py)
- [prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py)
- [lang_graph_planner.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/lang_graph_planner.py)
- [validation_engine.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/validation_engine.py)
- [plan_quality_gate.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/plan_quality_gate.py)
- [capability_registry_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_registry_service.py)
- evaluation harnesses for planning and experience phases

---

## 9. Anti-Drift Rules

### 9.1 No New Tag Without Semantics

A new AI-facing strategy label cannot be introduced unless:

- it is added to the ontology
- its behavioral doctrine is defined
- its validation consequences are defined

### 9.2 No Raw Internal Jargon In Primary AI Guidance

Internal codes may remain in metadata.
They should not remain the primary control language in prompts.

### 9.3 Do Not Explode Prompt Size

The renderer must stay compact.
The fix is better doctrine, not giant prompt dumps.

### 9.4 Preserve Runtime Determinism

We are not replacing structured control with pure prose.
We are translating structured control into better model-facing semantics.

---

## 10. What Success Should Feel Like

When this plan succeeds, the AI system should behave as if it truly understands what our strategies mean.

That means:

- `clarify` feels like wise clarification, not raw hesitation
- `stabilize` feels like supportive load reduction, not generic empathy
- `decide` feels like disciplined criteria-building, not fake certainty
- `mandatory grounding` feels like genuine evidence use, not token citation
- `provisional plan` feels explicitly assumption-aware

In short:

> **the model should follow Sparkle’s strategy as behavior, not merely read Sparkle’s strategy as labels**

---

## 11. The First Pack To Execute

The next Codex should begin with:

### `Pack AI-0: AI Control Vocabulary Audit`

Its first job is not to rewrite prompts immediately.

Its first job is to produce the full inventory of:

- all strategy/control tags that reach the model
- where they are rendered
- whether they are semantically explained
- where the biggest guidance risk is

That inventory becomes the base for the ontology and doctrine renderer.

---

## 12. Final Principle

Sparkle’s AI system is the core of the product.

If the model does not deeply understand our strategy language, then the whole system remains weaker than it looks.

So the real mission of this plan is:

> **make Sparkle’s internal intelligence legible to the model itself, so the model can act with the depth, discipline, and coherence the architecture was designed to produce**

