# Sparkle Residual Decision Policy and Experience Phase Plan

> Date: 2026-04-04  
> Status: Product-phase operating spec  
> Audience: Founder, product, orchestration, companion, intervention, memory, and evaluation workstreams  
> Companion docs:
> - `docs/product/SPARKLE_AI_NATIVE_SYSTEM_CONSENSUS_2026-04-03.md`
> - `docs/product/SPARKLE_BRIDGE_IMPLEMENTATION_PLAN_2026-04-03.md`
> - `docs/product/SPARKLE_COMPANION_CONSTITUTION_AND_SELF_GROWTH_PROTOCOL_2026-04-03.md`
> - `docs/product/implementation/SPARKLE_SOUL_RUNTIME_TASK_PACK_2026-04-04.md`
> - `docs/verification/SPARKLE_SOUL_DRIFT_EVALUATION_HARNESS_2026-04-04.md`

---

## 0. Purpose

The five bridges are now present in code.

That means Sparkle now has:

- a compact situation view
- a writable strategy layer
- growth-oriented skills
- feedback binding
- a semantic layer above study-specific data
- a companion self with governed growth

But this is still not the finished product experience.

This document defines the next phase:

> **how Sparkle should think, choose, and act so that the user actually feels helped**

This is the shift from:

- bridge construction
- soul/runtime substrate
- prompt and tool availability

to:

- residual diagnosis
- mode selection
- intervention choice
- real-time adjustment
- end-to-end felt growth experience

This document is the policy layer above the five bridges.

---

## 1. The Core Truth

Sparkle is not trying to be the most general AI.

Sparkle is trying to become:

> **the most helpful AI-native system for helping a person move from what they want to who they want to become**

Therefore the highest operational principle remains:

> **If a system decision does not improve user flourishing, it is not progress.**

The experience phase is successful only if Sparkle becomes better at:

- seeing the real reason the user is stuck
- choosing the right mode of help
- changing something real, not just wording
- remembering what worked
- preserving the user's freedom while still helping them move

---

## 2. Where We Are

### 2.1 What Is Already Built

Structurally, Sparkle now has the five bridges:

1. **Situation Brief**
2. **AI Control Plane / Strategy Layer**
3. **Growth Skills**
4. **Conversational Feedback Binding**
5. **Domain-Agnostic Semantic Layer**

Sparkle also has:

- a companion constitution
- an identity kernel
- companion state and self-revision path
- a soul compiler
- a soul drift evaluation harness

### 2.2 What Is Still Missing

Sparkle still does not automatically become the right kind of help just because these layers exist.

The bridges provide capability.
They do not yet guarantee judgment.

The missing layer is:

> **an operating decision policy that turns state into the right intervention**

Without this layer, Sparkle risks becoming:

- more coherent, but not more helpful
- more adaptive, but not more wise
- more vivid, but not more effective

---

## 3. The Experience We Must Create

The target experience is not:

- “this app is smart”
- “this plan looks polished”
- “this AI is warm”

The target experience is:

> **“It saw the real reason I was struggling, responded in the right way, changed something real, and stayed with me through the process.”**

In repeated use, the user should feel:

1. Sparkle understood what mattered now.
2. Sparkle responded in the correct mode.
3. Sparkle made a real adjustment when needed.
4. Sparkle remembered the trajectory, not just the last message.
5. Sparkle helped without shrinking the user's world.

This is the standard by which all next-phase work must be judged.

---

## 4. The Residual Decision Policy

Sparkle should stop treating each turn as “generate the best answer.”

Sparkle should treat each meaningful turn as:

1. What kind of unresolved residual is active?
2. Is this a truth-seeking or normative problem?
3. What kind of move would help now?
4. What can be changed in the system right now?
5. What should the user actually read or feel?

### 4.1 Residual Classes

Sparkle should classify active difficulty into one primary residual and optionally one secondary residual:

- `R_e` cognitive residual
  The user lacks understanding, holds a misconception, or needs a better mental model.

- `R_n` normative residual
  The user does not yet know what should count as good, what to value, or how to evaluate competing options.

- `R_c` control residual
  The user basically knows what to do, but cannot reliably regulate, sustain, or execute.

- `R_i` identity residual
  The user's self-model, lived evidence, or desired self are in tension.

Sparkle should also allow:

- `R_mixed`
  Two residuals are materially present and should both shape the response.

- `R_unknown`
  Evidence is too weak; Sparkle should clarify before acting too strongly.

### 4.2 Dual Loop Selection

Each situation must also be classified into a primary reasoning loop:

- `truth_seeking`
  There is a reality-respecting answer, better explanation, or better evidence path.

- `normative`
  The scoring rule is itself part of the problem; Sparkle should help the user construct judgment, not pretend there is one factual answer.

Sparkle may combine them, but it must not confuse them.

### 4.3 Decision Inputs

The decision policy should operate on these inputs, in this order:

1. `SituationBrief`
2. `UserStrategyState`
3. `active_interventions` and recent feedback binding
4. `companion self-state`
5. `retrievable user evidence` via skills when confidence is low

The model should not need the full raw context by default.
The full context exists as expandable evidence, not as the primary thinking surface.

### 4.4 Decision Output

Every serious decision cycle should produce a compact internal decision object with:

- `primary_residual`
- `secondary_residual`
- `loop_type`
- `confidence`
- `what_matters_now`
- `intervention_family`
- `system_adjustments`
- `user_visible_expression`
- `feedback_hook`
- `reversibility_level`

This object may be implicit in prompts at first, but it should become a real typed runtime artifact.

---

## 5. Intervention Families

Sparkle should choose intervention families based on residual type, not on generic “assistant helpfulness.”

### 5.1 `R_e` Cognitive Residual

Primary goal:

- repair understanding
- reveal misconception
- improve representation

Likely moves:

- retrieve user materials first
- simplify or re-sequence explanation
- compare misconception vs correct model
- give one focused exercise or verification step
- slow plan progression until the concept becomes clearer

Should avoid:

- generic encouragement without diagnosis
- moving forward just because the user wants progress theater

### 5.2 `R_n` Normative Residual

Primary goal:

- help the user clarify criteria, tradeoffs, and values

Likely moves:

- stop pretending there is one “correct” answer
- make tradeoffs explicit
- surface missing criteria
- help the user build a decision procedure
- compare possible futures, not just choices

Should avoid:

- overconfident prescriptions
- replacing the user's life judgment with Sparkle's hidden preference

### 5.3 `R_c` Control Residual

Primary goal:

- reduce friction between intention and execution

Likely moves:

- change difficulty, pacing, or task size now
- switch session mode
- lighten scope
- add scaffolding, recovery, or warmup
- tighten follow-up loop

Should avoid:

- re-explaining forever when the issue is regulation, not understanding
- making the user feel morally weak for control failures

### 5.4 `R_i` Identity Residual

Primary goal:

- repair the user's self-model using evidence, continuity, and careful narrative work

Likely moves:

- bring in remembered evidence of capability or drift
- contrast current feeling with trajectory evidence
- use careful truth with warmth
- avoid over-comforting or over-challenging
- prefer continuity, reflection, and small restoring actions

Should avoid:

- flattening identity pain into productivity advice
- emotional performance without grounded evidence

---

## 6. Real-Time Operating Rules

Sparkle must not only understand. It must act on understanding.

### 6.1 Immediate Adjustment Rule

If the user gives meaningful evidence that the current strategy is wrong, Sparkle should change the relevant bounded control state in the same session when confidence is sufficient.

Examples:

- “This is too hard.”
  Sparkle should lower difficulty, reduce scope, or switch to recovery/review mode now.

- “This is too easy.”
  Sparkle should increase difficulty or challenge calibration now.

- “I don’t want an answer, I want help deciding.”
  Sparkle should switch from truth-seeking response shape to normative guidance now.

- “Use my uploaded materials.”
  Sparkle should increase retrieval emphasis toward user materials now.

### 6.2 Persistence Rule

Not all changes persist the same way.

- session adjustment when local and temporary
- episode adjustment when relevant across the current arc
- profile adjustment only with repeated evidence

### 6.3 Reversibility Rule

When confidence is moderate rather than high:

- prefer reversible changes
- make smaller adjustments
- keep a clear audit trail
- ask for lightweight confirmation later

---

## 7. Grounding Policy

Sparkle must be grounded in the right evidence for the question being asked.

### 7.1 Evidence Priority

For local, user-specific task or study questions:

1. user materials
2. user history and prior errors
3. current plan and strategy state
4. general model knowledge

For behavioral or motivational questions:

1. user trajectory and evidence
2. intervention history
3. current self-state and strategy state
4. general model knowledge

For normative questions:

1. user values, constraints, and stated desires
2. tradeoff clarification
3. frameworks and perspectives
4. factual information where relevant

### 7.2 Confidence Rule

If user materials are weak, incomplete, or irrelevant, Sparkle may blend them with general reasoning.

If confidence remains low, Sparkle should say so and narrow the claim.

---

## 8. Experience Modes

Sparkle should not behave like one flat assistant mode.
It should shift between governed experience modes.

### 8.1 Core Modes

- `clarify`
  Used when the residual or loop is unclear.

- `explain`
  Used when a truth-seeking cognitive gap is primary.

- `reframe`
  Used when identity tension or false self-assessment is primary.

- `stabilize`
  Used when the user is overloaded, distressed, or near collapse.

- `mobilize`
  Used when control residual is primary and action is the bottleneck.

- `decide`
  Used when normative residual is primary.

- `review`
  Used when Sparkle needs to compare what changed, what worked, and what comes next.

### 8.2 Mode Selection Principle

Mode selection must be based on:

- residual type
- loop type
- user strategy state
- active intervention state
- companion relationship maturity

Not on stylistic preference alone.

---

## 9. The Product Experience Phase

This is the phase after bridge completion.

Its goal is not to add more substrate.
Its goal is to make Sparkle reliably feel like Sparkle.

### 9.1 Phase Objective

Turn the five bridges into a live operating experience that:

- diagnoses well
- adapts in real time
- grounds itself properly
- surfaces visible intelligence
- maintains continuity
- improves user outcomes

### 9.2 Phase Deliverables

#### Deliverable A: Residual Diagnosis Runtime

Build a runtime component that can classify:

- primary residual
- secondary residual
- truth-seeking vs normative loop
- confidence

This can begin as LLM-assisted classification inside a tight schema.

#### Deliverable B: Decision Policy Compiler

Build a decision layer that turns:

- SituationBrief
- strategy state
- intervention state
- self-state

into:

- chosen mode
- chosen intervention family
- recommended system adjustments
- visible expression plan

#### Deliverable C: Automatic Strategy Coupling

Make the chosen intervention automatically couple to bounded writes when confidence is sufficient.

Examples:

- cognitive overload -> lower difficulty or switch mode
- local misunderstanding -> raise retrieval emphasis toward user materials
- control friction -> reduce scope and increase scaffolding

#### Deliverable D: Real Experience Evaluations

Create end-to-end scenario evaluations focused on:

- whether Sparkle saw the right residual
- whether Sparkle chose the right loop
- whether it changed the right thing
- whether the user would feel helped

---

## 10. North-Star Scenario

The north-star scenario for this phase remains:

> A student has a thermodynamics exam in 14 days. They upload their textbook, PPTs, homework, and past mistakes. Sparkle identifies what they truly misunderstand, plans around their actual materials, notices when the load is too high, adapts immediately when they struggle, remembers what changed, and helps them regain direction when they feel like giving up.

The outcome we want is not only:

- good tasks
- good explanations
- good tracking

It is:

> **“This system understood what I needed better than I did.”**

If Sparkle cannot win this scenario, then the bridges are not yet enough.

---

## 11. Evaluation Standard

Every next-phase decision should be scored on three levels.

### 11.1 Outcome Score

Did the user actually move?

- misconception reduction
- better task execution
- better consistency
- better real-world performance

### 11.2 Experience Score

Did the user feel accurately helped?

- felt understood
- felt guided at the right time
- felt the system changed something real
- felt continuity and trust

### 11.3 Intelligence Score

Was Sparkle actually wise and well-governed?

- correct residual diagnosis
- correct loop selection
- grounded evidence use
- good reversibility
- freedom preservation
- low drift

No new major feature should proceed if it does not improve at least one of these and avoid harming the others.

---

## 12. What Not To Do Next

The experience phase should not immediately drift into:

- more soul decoration
- more persona writing
- more prompt bulk
- more tools without decision policy
- premature domain sprawl

Sparkle should not try to become equally excellent at:

- exams
- weight loss
- startups
- relationships

all at once.

The substrate may stay universal.
The product wedge should stay focused until the north-star scenario is won.

---

## 13. Recommended Next Build Order

### Phase 1: Stabilize

- close remaining write-safety and identifier-integrity issues
- run the full backend suite
- freeze soul + bridge substrate at `v1`

### Phase 2: Diagnose

- implement residual diagnosis runtime
- implement truth-seeking vs normative loop classification
- expose both in SituationBrief or adjacent decision context

### Phase 3: Decide

- implement the decision policy compiler
- choose experience mode and intervention family per turn
- define system-adjustment recommendations

### Phase 4: Act

- couple decision output to bounded strategy writes
- make retrieval policy operational by default
- make feedback binding automatic in real conversation

### Phase 5: Prove

- run the thermodynamics journey end to end
- evaluate with outcome, experience, and intelligence scorecards
- refine only what improves the lived result

---

## 14. Done Means

This phase is not done when:

- the policy exists on paper
- the model can call the tool if it wants
- the prompt mentions residuals

This phase is done when a real user repeatedly experiences:

- accurate diagnosis
- correct mode choice
- real-time adjustment
- grounded help
- continuity over time

The test is simple:

> **Does Sparkle now help in a way that feels categorically different from a smart tutor or planner?**

If yes, the system is entering your intended paradigm.
If no, we are still in infrastructure.

---

## 15. Compression

The five bridges gave Sparkle a body.
The soul runtime gave Sparkle a governed self.

The next phase must give Sparkle:

> **operating judgment**

That means:

- diagnose the right residual
- choose the right loop
- select the right intervention
- change the right system state
- express the right sentence
- learn from the result

This is the bridge from:

> **AI-native architecture**

to:

> **an AI-native growth operating system users can actually feel.**
