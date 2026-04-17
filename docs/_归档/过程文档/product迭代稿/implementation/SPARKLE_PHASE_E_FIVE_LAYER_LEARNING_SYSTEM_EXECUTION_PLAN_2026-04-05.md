# Sparkle Phase E Five-Layer Learning System Execution Plan

> Date: 2026-04-05  
> Status: Active execution plan  
> Audience: Founder, chief designer, implementation Codex runs, backend, product, evaluation  
> Companion docs:
> - `docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md`
> - `docs/product/SPARKLE_THREE_SYSTEM_IMPROVEMENT_PLAN_2026-04-05.md`
> - `docs/product/SPARKLE_COMPANION_CONSTITUTION_AND_SELF_GROWTH_PROTOCOL_2026-04-03.md`
> - `docs/product/SPARKLE_NEXT_PHASE_MASTER_PLAN_2026-04-04.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`
> - `docs/product/implementation/SPARKLE_PHASE_A_USER_INSIGHT_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_B_PLANNING_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_C_FEEDBACK_AND_GROWTH_ENGINE_EXECUTION_PLAN_2026-04-05.md`
> - `docs/product/implementation/SPARKLE_PHASE_D_BODY_AWARENESS_AND_CAPABILITY_GOVERNANCE_EXECUTION_PLAN_2026-04-05.md`

---

## 0. Why This Phase Exists

Phase A made Sparkle better at understanding the user.

Phase B made Sparkle better at planning.

Phase C made Sparkle better at learning from outcomes.

Phase D made Sparkle better at knowing and using its body.

Phase E exists to answer the next decisive question:

> **Can Sparkle become each user’s real Sparkle across time without drifting, overfitting, or violating its constitution?**

Right now, Sparkle’s strongest learning layer is still the session layer.

That is useful, but it is not yet enough for the product vision.

To fulfill the vision, Sparkle must mature all five layers:

1. constitutional  
2. session  
3. episode  
4. profile  
5. system

This phase is where Sparkle moves from:

> **smart short-term adaptation**

to:

> **durable, trustworthy, user-specific growth**

Phase E is not about giving Sparkle unrestricted self-modification.
It is about:

- safe persistence
- evidence-gated promotion
- cross-layer conflict handling
- reversible demotion
- constitutional anti-drift
- long-term personalization that still serves the user’s flourishing

---

## 1. Phase E Goal

Phase E goal:

> **Complete the five-layer learning system so Sparkle can safely learn across sessions, become more accurate for a specific user over time, and remain constitutionally aligned.**

If Phase E succeeds, Sparkle should become better at:

1. distinguishing what belongs in session, episode, profile, or nowhere
2. preserving context-specific learning without overgeneralizing it
3. resolving contradictions between short-term signals and long-term truths
4. demoting stale or disproven learning instead of only accumulating more memory
5. becoming recognizably more effective and more personal for a user across time
6. preserving constitutional alignment while doing all of the above

---

## 2. Definition of Done

Phase E is done only when all of the following are true:

1. The five layers have one explicit, stable contract:
   - what each layer is for
   - what evidence each layer accepts
   - what each layer may read
   - what each layer may write
   - when promotion is allowed
   - when demotion is required

2. Episode learning is mature enough to support real journeys such as:
   - exam sprint
   - overload week
   - recovery period
   - project burst

3. Profile learning is mature enough to represent cross-session truths without:
   - overfitting one emotional moment
   - overlearning one failed plan
   - silently replacing user intent

4. Cross-layer conflict resolution exists and is operational.

5. Constitutional anti-drift checks exist for layer promotions and self-descriptive changes.

6. System-layer rights are explicitly bounded:
   - what Sparkle may eventually control
   - what remains forbidden
   - what requires stronger approval or evidence

7. There is proof that multi-session personalization improves at least one of:
   - user understanding quality
   - plan quality
   - adaptation fit
   - trust and continuity

---

## 3. Non-Goals

Phase E is not for:

- giving Sparkle unrestricted selfhood
- letting one conversation rewrite long-term identity
- storing every moment forever
- using personalization to maximize attachment or retention
- inventing a second parallel memory stack
- skipping constitutional review because the learning “feels right”

This phase is specifically about:

> **safe, evidence-gated, cross-session personalization in service of user flourishing**

---

## 4. Design Principles

### 4.1 Constitutional First

No personalization win is worth constitutional drift.

If a learning increases vividness but weakens:

- truth discipline
- non-manipulation
- freedom preservation
- user-centered telos

then it is a bad learning.

### 4.2 Session Is Cheap, Profile Is Expensive

Layer cost discipline:

- session changes are cheap and reversible
- episode changes are moderately expensive
- profile changes are expensive
- system-layer changes are rare and bounded

This means promotion should become harder as we move upward.

### 4.3 Every Durable Learning Must Be Explainable

Sparkle should be able to answer internally:

- what evidence caused this learning
- why it belongs at this layer
- what could overturn it
- whether it is still fresh

### 4.4 Contradiction Is a First-Class Event

Conflicts between layers are not edge cases.
They are exactly where real personalization quality is tested.

Phase E should treat contradiction as a governed event, not as noise.

### 4.5 Personalization Must Improve The Two Moats

The five-layer system only matters if it improves:

- `User Understanding Quality`
- `Plan Quality`

If a layer change does not improve one of those, it is secondary.

### 4.6 Learning Must Stay Reversible

Phase E should add:

- expiry
- review windows
- demotion
- decay
- contradiction-triggered reevaluation

Accumulation alone is not growth.

---

## 5. What We Must Reuse

Phase E should build on top of current working components:

- [CompanionStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/companion_state_service.py)
- [UserStrategyStateService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_strategy_state_service.py)
- [OutcomePromotionGovernor](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/outcome_promotion_governor.py)
- [SelfRevisionService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/self_revision_service.py)
- [RelationshipProfileService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/relationship_profile_service.py)
- [PlanOutcomeService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_outcome_service.py)
- [OutcomeLearningService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/outcome_learning_service.py)
- [CapabilityRegistryService](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_registry_service.py)
- [CapabilityKnobGovernor](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_knob_governor.py)
- [SituationBriefBuilder](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
- [Soul compiler/runtime artifacts](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/soul_compiler.py)
- current drift evaluation and human-eval tooling

We should not rebuild these as parallel systems.

---

## 6. Target Architecture For Phase E

Phase E should add five major runtime artifacts and one evaluation loop.

### 6.1 Artifact A: Five-Layer Learning Contract

Purpose:

- define the meaning, rights, and promotion rules of each layer

Core outputs:

- `layer_id`
- `purpose`
- `allowed_signal_types`
- `write_policy`
- `promotion_policy`
- `demotion_policy`
- `review_window`
- `constitutional_constraints`

This is the canonical Phase E contract.

### 6.2 Artifact B: Layered Growth State Snapshot

Purpose:

- show what Sparkle currently believes at each layer and why

Core outputs:

- `constitutional_state`
- `session_state`
- `episode_state`
- `profile_state`
- `system_state`
- `active_conflicts`
- `stale_items`
- `pending_promotions`

This is the live five-layer read model.

### 6.3 Artifact C: Promotion and Demotion Engine

Purpose:

- govern upward and downward movement across layers

Core outputs:

- `promotion_candidates`
- `approved_promotions`
- `blocked_promotions`
- `demotion_candidates`
- `expired_items`
- `evidence_threshold_results`

This is where temporary signals become durable only when justified.

### 6.4 Artifact D: Cross-Layer Conflict Resolver

Purpose:

- detect and adjudicate contradictions across session, episode, and profile

Core outputs:

- `conflict_id`
- `conflicting_layers`
- `conflict_type`
- `winner`
- `review_required`
- `demotion_action`
- `explanation`

This is the core safety engine for durable personalization.

### 6.5 Artifact E: Constitutional Drift Firewall

Purpose:

- block learning or self-description changes that violate Sparkle’s constitution

Core outputs:

- `drift_check_result`
- `blocked_change`
- `reason`
- `escalation_required`
- `allowed_with_constraints`

This is what keeps “becoming more personal” from becoming “becoming misaligned.”

### 6.6 Artifact F: Personalization Maturity Evaluator

Purpose:

- prove that multi-session learning makes Sparkle better, not just more elaborate

Core outputs:

- continuity score
- personalization fit score
- contradiction safety score
- drift safety score
- plan-improvement-over-time score
- human-trust-over-time score

---

## 7. Canonical Phase E Standard

Every strong Phase E runtime should satisfy all of the following:

1. `Layer Discipline`
   Learning belongs to the right layer and not a higher one by default.

2. `Evidence Discipline`
   Durable learning is supported by repeated, meaningful evidence.

3. `Conflict Discipline`
   Contradictions are surfaced and resolved, not silently merged.

4. `Constitutional Discipline`
   No promotion undermines user-centered telos or anti-manipulation boundaries.

5. `Reversibility`
   Any non-constitutional learning can decay, expire, or be demoted.

6. `User Benefit`
   Personalization measurably improves understanding, planning, or continuity.

7. `Auditability`
   The system can explain what changed and why.

If a learning system does not satisfy most of these, it is not high quality.

---

## 8. Runtime Data Model

Phase E should add compact read models such as:

`LayeredLearningContract`

Suggested shape:

```text
LayeredLearningContract
  layer_id
  purpose
  allowed_signal_types
  write_scope
  promotion_threshold
  demotion_threshold
  expiry_policy
  constitutional_guardrails
```

`LayeredGrowthStateSnapshot`

Suggested shape:

```text
LayeredGrowthStateSnapshot
  session_items
  episode_items
  profile_items
  active_conflicts
  stale_items
  pending_reviews
  system_rights_state
```

`LayerConflictReport`

Suggested shape:

```text
LayerConflictReport
  conflict_id
  learning_key
  involved_layers
  conflict_type
  evidence_summary
  winner
  blocked_layers
  required_action
```

`ConstitutionalSafetyReport`

Suggested shape:

```text
ConstitutionalSafetyReport
  allowed
  blocked_reasons
  manipulation_risk
  freedom_risk
  goal_hijack_risk
  truth_discipline_risk
```

Important rule:

Phase E should stay governance-first and contract-first before adding more writable long-term state.

---

## 9. Multi-Stage Execution Plan

## Stage 0: Five-Layer Baseline Audit

### Purpose

Establish the real current state of the five-layer system before changing behavior.

### Work

- inventory current layer writes and read paths across:
  - companion state
  - user strategy state
  - outcome learning
  - relationship memory
  - capability knobs
- identify where session, episode, and profile currently blur together
- identify existing silent-promotion or lost-demotion risks
- identify where constitutional guardrails are currently implicit instead of enforced
- choose 8 to 12 representative multi-session personalization scenarios

### Outputs

- five-layer write map
- current maturity audit
- risk inventory
- baseline scenario set

### Suggested files

- verification doc under `docs/verification/`
- fixtures under `backend/tests/fixtures/`

### Acceptance

- the team can point to concrete places where the five-layer system is currently too weak or too loose

---

## Stage 1: Canonical Five-Layer Contract

### Purpose

Define the stable rules of the five-layer system.

### Work

- define one explicit contract for:
  - constitutional
  - session
  - episode
  - profile
  - system
- declare:
  - allowed signal families
  - default review windows
  - expiry rules
  - promotion and demotion thresholds
  - forbidden writes
- align language with the companion constitution

### Suggested implementation

- add a dedicated governance contract module
- keep the contract machine-readable
- avoid relying only on prose docs

### Suggested files

- `backend/app/services/five_layer_learning_contract.py`
- `docs/contracts/`
- tests under `backend/tests/unit/`

### Acceptance

- one stable layer contract exists for all future learning work

---

## Stage 2: Episode Layer Maturation

### Purpose

Make episode learning truly useful for journeys like exam sprint, overload, and recovery.

### Work

- improve episode promotion rules
- add expiry and review windows
- support journey-bounded patterns such as:
  - exam week pacing
  - overload recovery mode
  - confidence rebuilding
  - concentrated project bursts
- ensure episode learnings change planning and adaptation behavior on the next cycle

### Suggested implementation

- strengthen current promotion logic rather than building a parallel episode system
- expose episode-active learnings in the brief/runtime context

### Suggested files

- `backend/app/services/companion_state_service.py`
- `backend/app/services/user_strategy_state_service.py`
- `backend/app/services/outcome_promotion_governor.py`
- `backend/app/orchestration/situation_brief.py`

### Acceptance

- episode-specific learning survives across a real journey and expires when the journey ends

---

## Stage 3: Profile Layer Maturation

### Purpose

Make profile learning represent cross-session truths instead of accumulated residue.

### Work

- strengthen evidence thresholds for profile promotion
- distinguish:
  - stable user tendency
  - recent state
  - one-off reaction
- add freshness and contradiction sensitivity
- require multi-session support for strong profile claims
- improve profile learning use in understanding and planning

### Suggested implementation

- keep profile learning small, high-confidence, and auditable
- avoid storing raw duplication when a canonical learning exists

### Suggested files

- `backend/app/services/companion_state_service.py`
- `backend/app/services/relationship_profile_service.py`
- `backend/app/services/outcome_promotion_governor.py`
- `backend/app/services/personalization/preference_service.py`

### Acceptance

- profile state feels more accurate over time without becoming bloated or manipulative

---

## Stage 4: Cross-Layer Conflict and Demotion Engine

### Purpose

Make contradictions and stale learning first-class.

### Work

- detect conflicts between:
  - session vs episode
  - episode vs profile
  - profile vs new evidence
- add demotion and decay paths
- define winner rules:
  - fresh repeated evidence
  - constitutional override
  - context-specific episode precedence
- expose active conflicts in runtime state and audit reports

### Suggested implementation

- add one shared conflict resolver, not many local special cases
- route all layer disputes through that resolver

### Suggested files

- `backend/app/services/layer_conflict_resolver.py`
- `backend/app/services/companion_state_service.py`
- `backend/app/services/outcome_promotion_governor.py`
- tests under `backend/tests/unit/`

### Acceptance

- stale or contradictory learning is demoted or blocked instead of silently coexisting

---

## Stage 5: Constitutional Drift Firewall

### Purpose

Make constitutional alignment explicit in learning and self-description changes.

### Work

- create a constitutional check for:
  - companion growth notes
  - relationship profile promotions
  - outcome-driven planning biases
  - system-layer knob eligibility
- block changes that increase:
  - manipulation risk
  - attachment optimization
  - goal hijack risk
  - freedom reduction
- require escalation/review for borderline cases

### Suggested implementation

- keep this firewall lightweight and auditable
- do not bury it only in prompts

### Suggested files

- `backend/app/services/constitutional_drift_firewall.py`
- `backend/app/services/self_revision_service.py`
- `backend/app/services/relationship_profile_service.py`
- `backend/app/services/outcome_promotion_governor.py`

### Acceptance

- durable learning cannot silently violate Sparkle’s constitution

---

## Stage 6: System-Layer Rights Completion

### Purpose

Finish the bounded rights model for the system layer without broadening real control too early.

### Work

- define what the system layer may eventually control
- define what remains forbidden
- bind system-layer knobs to:
  - evidence thresholds
  - reversibility rules
  - approval boundaries
  - constitutional review
- align with Phase D capability governance

### Suggested implementation

- add rights completion to the capability registry / governance layer
- do not expand actual writes broadly in this stage

### Suggested files

- `backend/app/services/capability_registry_service.py`
- `backend/app/services/capability_knob_governor.py`
- contract docs under `docs/contracts/`

### Acceptance

- the system layer has a completed rights model even if only a narrow subset is operational

---

## Stage 7: Personalization Maturity Evaluation Harness

### Purpose

Prove that the five-layer system improves real multi-session quality.

### Work

- build scenarios covering:
  - exam sprint over multiple sessions
  - overload and recovery
  - contradictory self-report vs history
  - stale prior learning overturned by new evidence
  - profile truth strengthened by repeated outcome learning
- score:
  - continuity fit
  - plan-improvement-over-time
  - contradiction safety
  - drift safety
  - user trust preservation

### Suggested files

- `backend/app/services/five_layer_learning_evaluator.py`
- verification docs under `docs/verification/`
- integration tests under `backend/tests/integration/`

### Acceptance

- there is credible evidence that cross-session personalization improves Sparkle without constitutional drift

---

## Stage 8: Production Promotion and Freeze

### Purpose

Promote the five-layer system to a governed long-term substrate and then stop redesigning it.

### Work

- promote proven layer rules to the primary runtime path
- freeze:
  - five-layer contract
  - conflict-report contract
  - constitutional safety contract
  - promotion/demotion reason taxonomy
- document:
  - what the system now learns safely
  - what it still must not learn

### Acceptance

- the five-layer learning system can remain stable while the team moves on to Phase F and broader organic integration

---

## 10. Codex Handoff Packs

## Pack E0: Five-Layer Baseline Audit

### Scope

- inventory current layer writes and risks

### Ownership

- verification docs
- fixtures
- layer write map

### Files likely touched

- `docs/verification/`
- `backend/tests/fixtures/`

### Acceptance

- we know exactly where the five-layer system is still weak

---

## Pack E1: Canonical Five-Layer Contract

### Scope

- create the stable five-layer governance contract

### Ownership

- contract module
- tests

### Files likely touched

- `backend/app/services/five_layer_learning_contract.py`
- `docs/contracts/`
- `backend/tests/unit/`

### Acceptance

- one stable contract defines all five layers

---

## Pack E2: Episode Layer Maturation

### Scope

- strengthen journey-bounded learning

### Ownership

- episode promotion
- expiry
- runtime integration

### Files likely touched

- `backend/app/services/companion_state_service.py`
- `backend/app/services/user_strategy_state_service.py`
- `backend/app/services/outcome_promotion_governor.py`
- `backend/app/orchestration/situation_brief.py`

### Acceptance

- episode learnings support real journeys and expire correctly

---

## Pack E3: Profile Layer Maturation

### Scope

- strengthen cross-session truth formation

### Ownership

- profile thresholds
- freshness
- contradiction-aware promotion

### Files likely touched

- `backend/app/services/relationship_profile_service.py`
- `backend/app/services/companion_state_service.py`
- `backend/app/services/personalization/preference_service.py`
- tests under `backend/tests/unit/`

### Acceptance

- profile learning becomes more accurate and less bloated

---

## Pack E4: Conflict and Demotion Engine

### Scope

- make contradiction and staleness operational

### Ownership

- resolver
- demotion rules
- audit reporting

### Files likely touched

- `backend/app/services/layer_conflict_resolver.py`
- `backend/app/services/outcome_promotion_governor.py`
- `backend/app/services/companion_state_service.py`
- `backend/tests/unit/`

### Acceptance

- conflicting layer claims are resolved or demoted instead of silently coexisting

---

## Pack E5: Constitutional Drift Firewall

### Scope

- enforce constitutional checks on durable learning

### Ownership

- firewall
- growth-note checks
- promotion checks

### Files likely touched

- `backend/app/services/constitutional_drift_firewall.py`
- `backend/app/services/self_revision_service.py`
- `backend/app/services/relationship_profile_service.py`
- `backend/tests/unit/`

### Acceptance

- durable learning changes are constitutionally screened

---

## Pack E6: System-Layer Rights Completion

### Scope

- finish bounded rights for the system layer

### Ownership

- rights model
- knob constraints
- contract freeze

### Files likely touched

- `backend/app/services/capability_registry_service.py`
- `backend/app/services/capability_knob_governor.py`
- `docs/contracts/`

### Acceptance

- the system layer has a completed rights model even if control remains narrow

---

## Pack E7: Personalization Maturity Evaluation Harness

### Scope

- prove the five-layer system helps over time

### Ownership

- evaluator
- scenarios
- verification docs

### Files likely touched

- `backend/app/services/five_layer_learning_evaluator.py`
- `backend/tests/integration/`
- `docs/verification/`

### Acceptance

- there is credible evidence that multi-session personalization improves Sparkle safely

---

## 11. What Not To Do

Do not:

- let profile learnings absorb every short-term emotional state
- create many separate promotion systems with different rules
- treat “more personalization” as automatically better
- let system-layer rights quietly expand through convenience
- allow durable learning to bypass constitutional checks
- optimize for Sparkle’s vividness or attachment instead of user benefit

---

## 12. Main Drift Traps

### 12.1 Session Leakage

Short-term state quietly becoming long-term identity.

### 12.2 Profile Bloat

Accumulating many low-value profile facts that never improve planning or understanding.

### 12.3 Conflict Burial

Allowing contradictory learnings to coexist because resolution is inconvenient.

### 12.4 Constitutional Drift by Warmth

Using “companionship” as a reason to weaken truth discipline or freedom preservation.

### 12.5 System-Layer Expansion Creep

Gradually allowing more control without explicitly updating the rights model.

### 12.6 Personalization Theater

Making Sparkle feel more personal without actually making it more accurate or more helpful.

---

## 13. Recommended Execution Order

1. `Pack E0: Five-Layer Baseline Audit`
2. `Pack E1: Canonical Five-Layer Contract`
3. `Pack E2: Episode Layer Maturation`
4. `Pack E3: Profile Layer Maturation`
5. `Pack E4: Conflict and Demotion Engine`
6. `Pack E5: Constitutional Drift Firewall`
7. `Pack E6: System-Layer Rights Completion`
8. `Pack E7: Personalization Maturity Evaluation Harness`

This order matters.

Do not start by adding more long-term writes.
Do not start with system-layer expansion.
Do not start with new personalization surfaces before the layer rules are stable.

---

## 14. What Must Be True Before Starting Phase F

Before moving to the next phase, all of these should be true:

1. The five-layer contract is stable and explicit.
2. Episode and profile learning are trustworthy enough to improve real journeys.
3. Conflict resolution and demotion are operational.
4. Constitutional drift checks guard durable learning.
5. System-layer rights are explicitly bounded.
6. Multi-session personalization has credible evidence of user benefit.

If these are not true, Phase E is not finished.

---

## 15. Final Standard

Phase E succeeds when Sparkle can honestly say, in system terms:

> **I know what should stay temporary, what should persist for this journey, what has become a real cross-session truth, what must be forgotten or demoted, and what I am never allowed to become.**

That is the point where Sparkle starts becoming each user’s real Sparkle.

Not through flattery.
Not through unlimited memory.

Through governed growth.
