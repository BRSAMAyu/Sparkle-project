# Sparkle Phase D Body Awareness and Capability Governance Execution Plan

> Date: 2026-04-05  
> Status: Active execution plan  
> Audience: Founder, chief designer, implementation Codex runs, backend, product, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_BODY_MAP_AND_CAPABILITY_REGISTRY_SPEC_2026-04-04.md`
> - `docs/product/implementation/SPARKLE_PHASE_A_USER_INSIGHT_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_B_PLANNING_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_C_FEEDBACK_AND_GROWTH_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`

---

## 0. Why This Phase Exists

Phase A made Sparkle better at understanding the user.

Phase B made Sparkle better at producing better plans.

Phase C made Sparkle better at learning from outcomes.

Phase D exists to answer the next decisive question:

> **Does Sparkle actually know its own body well enough to use the right subsystem, at the right time, for the right reason?**

Right now, Sparkle already has many organs:

- multiple models
- many agents
- orchestration paths
- retrieval systems
- OpenClaw pipeline
- prediction and galaxy systems
- mobile surfaces
- intervention surfaces
- visual and ambient surfaces
- planning, feedback, and growth services

But a pile of organs is not yet a living operating system.

Phase D is where Sparkle begins to become:

> **a bounded, rights-aware system that can inspect its own body, understand what it can do, understand what it should not do, and select the right capability in service of user understanding and plan quality**

This phase is not about unrestricted autonomy.
It is about:

- operational self-knowledge
- capability selection
- bounded system control
- auditability
- user benefit

---

## 1. Phase D Goal

Phase D goal:

> **Make Sparkle’s body-awareness operational so that capability choice, subsystem routing, and bounded system-layer adjustments improve user understanding quality and plan quality.**

If Phase D succeeds, Sparkle should become better at:

1. knowing which subsystem it should use for a given planning situation
2. knowing when a cheaper or simpler path is enough
3. knowing when user materials, special agents, or stronger orchestration are required
4. explaining internally why it chose one organ instead of another
5. making bounded, auditable session-level system adjustments without hallucinating control it does not have

---

## 2. Definition of Done

Phase D is done only when all of the following are true:

1. There is one canonical capability registry covering the major system organs:
   - models
   - agents
   - tools
   - pipelines
   - surfaces
   - evidence sources
   - configuration knobs

2. Sparkle can compile a runtime body map from that registry for the current turn.

3. The planning/runtime path can derive a `capability requirement profile` from:
   - user understanding state
   - planning strategy
   - decision policy
   - outcome learning
   - current surface constraints

4. At least three real runtime decisions are governed by body-awareness rather than only prompt suggestion.
   Examples:
   - whether to force user-material grounding
   - whether to use a specialist agent or a simpler path
   - whether to use a more expensive model tier or a lighter one

5. Sparkle can produce a compact capability-use rationale that is auditable.

6. Bounded system-layer adjustments exist, but only for approved reversible knobs.

7. There is proof that capability-aware routing improves either:
   - user understanding quality
   - plan quality
   - grounding quality
   - or runtime trustworthiness

---

## 3. Non-Goals

Phase D is not for:

- letting Sparkle freely rewrite its architecture
- unrestricted model switching
- hidden system-prompt rewriting
- replacing all hand-authored orchestration with one “super-agent”
- speculative agent spawning without clear user benefit
- decorative body-map visualizations without runtime use
- broad automation of every subsystem just because it exists

This phase is specifically about:

> **knowing the body, choosing the right organ, and operating only within declared rights**

---

## 4. Design Principles

### 4.1 Body Awareness Must Serve The Two Moats

Phase D only matters if it improves:

- `User Understanding Quality`
- `Plan Quality`

If a capability-registry addition does not improve one of those, it is secondary.

### 4.2 Knowing The Body Is Not The Same As Controlling The Body

Sparkle must know:

- what exists
- what it is for
- what it costs
- what state it is in
- what it can read
- what it can write

That still does not mean it may control everything.

### 4.3 Rights Must Be Declared, Not Implied

Every system-layer knob must declare:

- whether it is readable
- whether it is writable
- which layer may write it
- whether the change is reversible
- what evidence threshold is required

### 4.4 Capability Choice Must Be Auditable

Sparkle should be able to explain internally:

- why this subsystem was chosen
- what cheaper path was rejected
- what evidence requirement caused escalation
- what user benefit justified the cost

### 4.5 Prefer Small Real Runtime Wins Over Grand Control

The best early Phase D victories are not dramatic.
They are things like:

- correctly choosing user-material retrieval first
- correctly escalating to a stronger planning path only when needed
- correctly not using an expensive or complex subsystem when the simple path is enough

### 4.6 System-Layer Writes Must Start Reversible

Phase D should begin with bounded session-level or reversible episode-level system adjustments.
Profile-level and broader system-layer writes should remain rare and heavily constrained.

---

## 5. What We Must Reuse

Phase D should build on top of current working components:

- [CapabilityRegistryService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_registry_service.py)
- [SituationBriefBuilder](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [DecisionPolicyCompiler](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/decision_policy.py)
- [PlanningStrategyCompiler](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/planning_strategy_compiler.py)
- [ExperienceActuator](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/experience_actuator.py)
- [UserStrategyStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_strategy_state_service.py)
- [OutcomePromotionGovernor](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/outcome_promotion_governor.py)
- [LLMRouter] and the current model-routing layer
- current tool registries and orchestration wiring
- current multi-agent API and body-map endpoint

We should not rebuild these as parallel systems.

---

## 6. Target Architecture For Phase D

Phase D should add five major runtime artifacts and one evaluation loop.

### 6.1 Artifact A: Canonical Capability Registry

Purpose:

- define Sparkle’s available body in one stable schema

Core outputs:

- `capability_id`
- `capability_kind`
- `purpose`
- `availability`
- `cost_hint`
- `latency_hint`
- `quality_hint`
- `read_scope`
- `write_scope`
- `when_to_use`
- `when_not_to_use`
- `required_preconditions`
- `rights_model`
- `reversibility`

This is the canonical body definition.

### 6.2 Artifact B: Runtime Body Map

Purpose:

- compile the current live body from the registry plus runtime health/context

Core outputs:

- `available_organs`
- `healthy_organs`
- `blocked_organs`
- `candidate_organs_for_turn`
- `surface_constraints`
- `cost_sensitive_organs`
- `evidence_relevant_organs`

This is the live per-turn body snapshot.

### 6.3 Artifact C: Capability Requirement Profile

Purpose:

- translate the current situation into what kind of organ the turn actually needs

Core outputs:

- `needs_grounded_materials`
- `needs_specialist_reasoning`
- `needs_multi_step_planning`
- `needs_low_latency_response`
- `needs_visible_adaptation`
- `needs_reversible_adjustment`
- `allowed_cost_band`
- `forbidden_paths`

This is the bridge from user/problem state to system choice.

### 6.4 Artifact D: Capability Selection Policy

Purpose:

- choose the right subsystem path and reject the wrong ones

Core outputs:

- `selected_model_tier`
- `selected_agent_path`
- `selected_tool_family`
- `selected_retrieval_path`
- `selected_surface_actions`
- `selection_rationale`
- `fallback_path`

This is where body-awareness starts governing runtime.

### 6.5 Artifact E: Bounded System Knob Governor

Purpose:

- allow only approved, reversible system-layer adjustments

Core outputs:

- `candidate_adjustments`
- `allowed_adjustments`
- `blocked_adjustments`
- `reversibility_window`
- `audit_log_entry`

This is the first operational system-layer control path.

### 6.6 Artifact F: Capability-Aware Evaluation Loop

Purpose:

- prove that body-awareness improves the product rather than making it more complicated

Core outputs:

- selection correctness score
- grounding win rate
- specialist escalation precision
- unnecessary-complexity rate
- capability choice error cases
- cost/quality tradeoff notes

---

## 7. Canonical Phase D Standard

Every strong Phase D runtime should satisfy all of the following:

1. `Body Truth`
   Sparkle knows which organs are actually available now.

2. `Need Match`
   Sparkle chooses organs based on current need, not static preference.

3. `Rights Safety`
   Sparkle does not exceed declared read/write rights.

4. `Cost Discipline`
   Sparkle does not escalate to expensive or complex paths without justification.

5. `Grounding Discipline`
   Sparkle chooses grounded paths when user materials or evidence-sensitive planning require them.

6. `Fallback Safety`
   Sparkle has a simpler or safer fallback when the preferred organ is unavailable or too risky.

7. `Auditability`
   The system can explain why the choice was made.

If a capability-aware decision does not satisfy most of these, it is not high quality.

---

## 8. Runtime Data Model

Phase D should add compact read models such as:

`CapabilityRegistryEntry`

Suggested shape:

```text
CapabilityRegistryEntry
  capability_id
  label
  capability_kind
  purpose
  availability
  quality_hint
  latency_hint
  cost_hint
  read_scope
  write_scope
  reversible
  when_to_use
  when_not_to_use
  required_preconditions
  declared_knobs
```

`CompiledBodyMap`

Suggested shape:

```text
CompiledBodyMap
  available_organs
  blocked_organs
  evidence_organs
  planning_organs
  adaptation_organs
  expensive_organs
  surface_constraints
  recommended_organs
```

`CapabilityRequirementProfile`

Suggested shape:

```text
CapabilityRequirementProfile
  planning_depth_required
  grounding_required
  material_dependency
  specialization_required
  latency_sensitivity
  adaptation_visibility_required
  cost_band
  forbidden_paths
```

`CapabilitySelectionReport`

Suggested shape:

```text
CapabilitySelectionReport
  selected_capabilities
  rejected_capabilities
  selection_rationale
  fallback_plan
  bounded_adjustments
  audit_notes
```

Important rule:

Phase D should remain read-first and selection-first before deeper system-layer writes.

---

## 9. Multi-Stage Execution Plan

## Stage 0: Phase D Baseline Audit

### Purpose

Establish the real current state of body-awareness before changing behavior.

### Work

- inventory the current runtime organs:
  - model routing tiers
  - agent families
  - tool families
  - planning pipelines
  - retrieval systems
  - surfaces
  - system knobs already in use
- identify which runtime decisions already exist but are implicit
- identify where wrong subsystem choice currently hurts:
  - grounding failures
  - over-complex routing
  - expensive-path overuse
  - specialist underuse
  - missing surface actions
- choose 8 to 12 representative scenarios where body-awareness should matter

### Outputs

- system-organ inventory
- capability gap summary
- current implicit-routing map
- baseline scenario set

### Suggested files

- new verification doc under `docs/verification/`
- fixtures under `backend/tests/fixtures/`

### Acceptance

- the team can point to concrete places where Sparkle chooses the wrong organ today

---

## Stage 1: Canonical Capability Registry

### Purpose

Turn the current body map into one stable machine-readable registry.

### Work

- define one canonical registry schema
- register:
  - models
  - agents
  - tools
  - orchestration paths
  - retrieval organs
  - visible surfaces
  - allowed system knobs
- add declared rights, preconditions, and reversibility
- standardize `when_to_use` and `when_not_to_use`

### Suggested implementation

- extend `backend/app/services/capability_registry_service.py`
- keep registry entries compact and auditable
- avoid burying business logic in hand-written prose fields alone

### Suggested files

- `backend/app/services/capability_registry_service.py`
- tests under `backend/tests/services/`
- optional contract snapshot under `docs/contracts/`

### Acceptance

- one stable registry exists for the major organs Sparkle may inspect or govern

---

## Stage 2: Runtime Body Map Compiler

### Purpose

Compile the current live body from the registry plus runtime conditions.

### Work

- incorporate:
  - current route/surface
  - attached materials
  - known subsystem availability
  - feature flags
  - mode constraints
  - system health snapshots where available
- derive:
  - available organs
  - blocked organs
  - recommended organ families
  - expensive organs that need justification

### Suggested implementation

- keep this next to `SituationBrief`, not buried inside the service layer
- expose it on the runtime brief as compact structured data

### Suggested files

- `backend/app/orchestration/situation_brief.py`
- `backend/app/services/capability_registry_service.py`
- prompt wiring only after the body map is stable

### Acceptance

- every important turn can expose a compact body map without large prompt bloat

---

## Stage 3: Capability Requirement Profile

### Purpose

Translate the user/problem state into system needs.

### Work

- compile requirements from:
  - Phase A readiness
  - Phase B planning strategy
  - Phase C outcome learning
  - decision policy
  - current materials/evidence state
  - visible adaptation requirements
- derive:
  - whether grounding is mandatory
  - whether specialist reasoning is needed
  - whether a simple path is enough
  - whether latency is more important than depth
  - whether bounded system adjustments are allowed

### Suggested implementation

- add a dedicated compiler next to `planning_strategy_compiler.py`
- do not bury requirement inference inside prompt strings

### Suggested files

- `backend/app/orchestration/capability_requirement_compiler.py`
- `backend/app/orchestration/situation_brief.py`
- tests under `backend/tests/unit/`

### Acceptance

- the same turn state deterministically yields the same requirement profile

---

## Stage 4: Capability Selection Policy

### Purpose

Make body-awareness govern real runtime choices.

### Work

- choose from the body map and requirement profile:
  - model tier
  - agent path
  - retrieval path
  - tool family
  - surface action family
- integrate into:
  - orchestrator routing
  - planning path selection
  - retrieval emphasis
  - specialist-agent escalation
- ensure rejected paths are explainable

### Suggested implementation

- introduce a capability-selection policy, not ad hoc conditional sprawl
- allow soft guidance first, then hard routing for proven cases

### Suggested files

- `backend/app/orchestration/capability_selection_policy.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/execution_engine.py`
- `backend/app/orchestration/prompts.py`

### Acceptance

- at least three real runtime choices are now governed by body-awareness

---

## Stage 5: Capability Audit and Visible Rationale

### Purpose

Make subsystem choice inspectable and, when useful, visible.

### Work

- emit audit metadata for:
  - chosen organ
  - rejected organ
  - cost/latency tradeoff
  - grounding reason
  - fallback path
- expose compact internal rationale in:
  - response metadata
  - debug traces
  - optional product-visible “why this path” fields where appropriate

### Suggested implementation

- keep user-facing rationale minimal and high-signal
- keep full audit detail in metadata and logs

### Suggested files

- `backend/app/orchestration/response_builder.py`
- `backend/app/orchestration/prompts.py`
- `backend/app/services/capability_registry_service.py`

### Acceptance

- the team can inspect why the system chose a given path without reading vague logs

---

## Stage 6: Bounded System Knob Governance

### Purpose

Let Sparkle adjust a small approved subset of system behavior safely.

### Work

- declare an allowlist of reversible knobs such as:
  - retrieval emphasis
  - escalation threshold
  - grounding strictness
  - visible adaptation verbosity
  - model-cost sensitivity
- define for each knob:
  - allowed layer
  - reversibility window
  - evidence threshold
  - blocked write cases
- wire through a bounded governor with audit logging

### Suggested implementation

- start session-level first
- episode/profile/system only where there is strong evidence and explicit rights

### Suggested files

- `backend/app/services/capability_registry_service.py`
- `backend/app/services/user_strategy_state_service.py`
- optional new governor under `backend/app/services/`

### Acceptance

- Sparkle can make a small number of bounded, reversible system adjustments without exceeding declared rights

---

## Stage 7: Capability-Aware Evaluation Harness

### Purpose

Prove that body-awareness improves the product instead of just increasing complexity.

### Work

- build evaluation scenarios covering:
  - user materials required vs optional
  - specialist agent needed vs not needed
  - high-latency deep path vs fast sufficient path
  - visible adaptation surface selection
  - bounded knob adjustment correctness
- score:
  - selection correctness
  - grounding quality improvement
  - unnecessary escalation rate
  - missed-specialist rate
  - cost discipline
  - user-facing coherence

### Suggested files

- `backend/app/services/capability_selection_evaluator.py`
- verification docs under `docs/verification/`
- integration tests under `backend/tests/integration/`

### Acceptance

- there is credible evidence that capability-aware routing improves understanding, planning, grounding, or trustworthiness

---

## Stage 8: Production Promotion and Freeze

### Purpose

Move Phase D from substrate to governed runtime and then stop redesigning it.

### Work

- promote proven capability-aware decisions to primary runtime paths
- freeze:
  - registry schema
  - requirement profile contract
  - selection report contract
  - allowed knob list
- document:
  - what Phase D now governs
  - what Phase D still must not govern

### Acceptance

- the system can remain stable while the team moves on to Phase E and Live Alpha truth

---

## 10. Codex Handoff Packs

## Pack D0: Body Awareness Baseline Audit

### Scope

- inventory organs
- map implicit runtime choices
- create baseline scenarios

### Ownership

- verification docs
- fixtures
- capability-inventory snapshots

### Files likely touched

- `docs/verification/`
- `backend/tests/fixtures/`

### Acceptance

- we know exactly where body-awareness should improve product behavior

---

## Pack D1: Canonical Capability Registry

### Scope

- unify the registry schema and register major organs

### Ownership

- registry service
- tests

### Files likely touched

- `backend/app/services/capability_registry_service.py`
- `backend/tests/services/test_capability_registry_service.py`

### Acceptance

- one stable registry exists for major runtime organs

---

## Pack D2: Runtime Body Map Compiler

### Scope

- compile a live body map into the brief/runtime context

### Ownership

- situation brief integration
- body-map runtime shape

### Files likely touched

- `backend/app/orchestration/situation_brief.py`
- `backend/app/services/capability_registry_service.py`
- `backend/tests/unit/test_situation_brief.py`

### Acceptance

- body-awareness is available on the main runtime path as structured context

---

## Pack D3: Capability Requirement Compiler

### Scope

- derive system needs from planning/runtime state

### Ownership

- requirement compiler
- deterministic tests

### Files likely touched

- `backend/app/orchestration/capability_requirement_compiler.py`
- `backend/app/orchestration/situation_brief.py`
- `backend/tests/unit/`

### Acceptance

- planning-like turns now produce deterministic capability requirements

---

## Pack D4: Capability Selection Policy

### Scope

- turn body-awareness into actual subsystem selection

### Ownership

- selection policy
- orchestrator integration
- routing integration

### Files likely touched

- `backend/app/orchestration/capability_selection_policy.py`
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/execution_engine.py`
- `backend/tests/orchestration/`

### Acceptance

- at least three real runtime choices are capability-governed

---

## Pack D5: Audit and Visible Rationale

### Scope

- make subsystem choice inspectable and minimally visible

### Ownership

- metadata exposure
- rationale formatting

### Files likely touched

- `backend/app/orchestration/response_builder.py`
- `backend/app/orchestration/prompts.py`
- `backend/tests/unit/`

### Acceptance

- engineers and evaluators can inspect why a system path was chosen

---

## Pack D6: Bounded System Knob Governance

### Scope

- implement reversible allowed system-layer adjustments

### Ownership

- knob allowlist
- governor
- rights checks

### Files likely touched

- `backend/app/services/capability_registry_service.py`
- `backend/app/services/user_strategy_state_service.py`
- optional new governor service
- tests under `backend/tests/unit/`

### Acceptance

- a small approved set of system knobs can be changed safely and reversibly

---

## Pack D7: Capability-Aware Evaluation Harness

### Scope

- prove capability-aware routing is actually worth it

### Ownership

- evaluator
- scenarios
- verification docs

### Files likely touched

- `backend/app/services/capability_selection_evaluator.py`
- `backend/tests/integration/`
- `docs/verification/`

### Acceptance

- there is credible evidence that Phase D improves product outcomes

---

## 11. What Not To Do

Do not:

- let Sparkle write arbitrary system config
- create a second hidden routing system beside the main orchestrator
- treat the capability registry as a dump of every internal detail with no runtime use
- add decorative body-awareness context that never governs real decisions
- use Phase D to justify uncontrolled agent spawning or expensive-model overuse
- mix rights declarations with vague prose only

---

## 12. Main Drift Traps

### 12.1 Capability Theater

Showing a rich body map without changing runtime decisions.

### 12.2 Hidden Centralization

Accidentally creating one giant “selector god object” that becomes impossible to reason about.

### 12.3 Cost Blindness

Escalating to expensive or complex paths without proving user benefit.

### 12.4 Rights Drift

Letting registry-declared reads quietly become writes.

### 12.5 Over-automation

Trying to turn Phase D into full system autonomy before the product has earned it.

### 12.6 Misaligned Optimization

Improving subsystem elegance without improving understanding or planning quality.

---

## 13. Recommended Execution Order

1. `Pack D0: Body Awareness Baseline Audit`
2. `Pack D1: Canonical Capability Registry`
3. `Pack D2: Runtime Body Map Compiler`
4. `Pack D3: Capability Requirement Compiler`
5. `Pack D4: Capability Selection Policy`
6. `Pack D5: Audit and Visible Rationale`
7. `Pack D6: Bounded System Knob Governance`
8. `Pack D7: Capability-Aware Evaluation Harness`

This order matters.

Do not start with system writes.
Do not start with visible rationale before real selection exists.
Do not start with evaluation before the runtime decisions are real.

---

## 14. What Must Be True Before Starting Phase E

Before moving to the next phase, all of these should be true:

1. Capability-aware routing governs real runtime choices, not just prompts.
2. The major organs are represented in one stable registry.
3. Body-awareness improves at least one of:
   - understanding quality
   - plan quality
   - grounding quality
   - trustworthiness
4. Rights are declared and bounded for approved system-layer knobs.
5. The team can inspect and explain major subsystem choices.

If these are not true, Phase D is not finished.

---

## 15. Final Standard

Phase D succeeds when Sparkle can honestly say, in system terms:

> **I know what body I have, I know what this situation requires, I know which organ to use, I know what I am not allowed to change, and I can choose the right path in service of the user’s real goal.**

That is the beginning of true AI-operating-system behavior.

Not unrestricted autonomy.
Not architecture theater.

Real bounded self-knowledge in service of better help.
