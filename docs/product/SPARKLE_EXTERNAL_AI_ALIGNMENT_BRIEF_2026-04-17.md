# Sparkle External AI Alignment Brief

> Date: 2026-04-17  
> Status: Active briefing document for Claude / ChatGPT / external strategic reviewers  
> Audience: Founder, external AI collaborators, chief designer, Codex handoff threads  
> Purpose: Give external AI systems a truthful, code-grounded understanding of Sparkle so they can reason at the right level

---

## 0. Why This Document Exists

The founder is now using multiple frontier AI systems as strategic collaborators.

That creates a context problem:

- external AIs can reason well in the abstract
- but they cannot directly see the full Sparkle codebase, runtime seams, or the real development history
- this leads to high-level advice that is often directionally useful but partially disconnected from the actual project

This document is the bridge.

Its job is to explain:

1. what Sparkle is actually trying to be
2. what has already been built
3. what has already been frozen and should not be casually redesigned
4. what remains unproven
5. what kinds of advice are useful now
6. what kinds of advice are likely to drift away from reality

This document is intentionally pragmatic.

It is not meant to sell the project.
It is meant to let strong external AIs reason about the project truthfully.

---

## 1. One-Sentence Project Definition

Sparkle is:

> **an AI-native planning and guidance system for ordinary users who cannot manually extract the best results from frontier AI on their own**

Operationally:

> **Sparkle tries to understand the user deeply, turn that understanding plus the user’s own data into the best possible plan and next move, then adapt over time through feedback and outcomes.**

Sparkle is not primarily:

- a generic chatbot
- a showcase of many agents
- a pure execution agent
- a feature bundle

It is a `system`, not just an `assistant`, because it is intended to manage the whole loop:

1. gather information
2. build understanding
3. identify what is missing
4. generate the plan
5. support execution and adaptation
6. learn from outcomes
7. preserve continuity over time

---

## 2. The Two Real Moats

Everything important in Sparkle serves one of these two moats.

### 2.1 Moat A: User Understanding Quality

Sparkle should surface things the user cannot easily see alone, in a way the user recognizes as true.

This includes:

- real bottlenecks
- hidden constraints
- missing planning-critical facts
- useful behavioral patterns
- the user’s actual readiness and capacity
- what style of guidance works for this user

### 2.2 Moat B: Plan Quality

Sparkle should produce:

- a better plan
- a better sequence
- a better next move
- better pacing
- better recovery logic
- better adaptation

than a non-expert user would typically get from raw GPT / Claude prompting.

If a subsystem does not improve one of these two moats, it is secondary.

---

## 3. The Current Product Standard

The main product test is still the same north-star:

### Thermodynamics in 14 Days

A student:

- has a real exam in 14 days
- uploads slides, notes, textbook excerpts, homework, and prior mistakes
- does not fully understand what is wrong with their study approach
- gets overloaded during the journey

Sparkle must:

- understand the user’s real state
- identify missing planning-critical information
- build a grounded study plan
- adapt when overload or failure happens
- preserve continuity and trust
- do this better than raw frontier-model use for a comparable non-expert user

This is the main reference scenario.

---

## 4. Where the Project Actually Is

Sparkle is no longer a vague architecture project.

It now has a serious internal operating substrate.

### 4.1 What Is Real in Code

The following system layers materially exist in the codebase:

- canonical compiled user insight state  
  File anchors:
  [backend/app/core/user_insight_state.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/core/user_insight_state.py)
  [backend/app/services/user_insight_compiler.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/user_insight_compiler.py)

- orchestration-time situation understanding and decision context  
  File anchors:
  [backend/app/orchestration/situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py)
  [backend/app/orchestration/orchestrator.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/orchestrator.py)

- planning strategy compilation and plan-quality gating  
  File anchors:
  [backend/app/orchestration/planning_strategy_compiler.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/planning_strategy_compiler.py)
  [backend/app/orchestration/plan_quality_gate.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/plan_quality_gate.py)

- outcome learning and feedback-driven growth loops  
  File anchors:
  [backend/app/services/plan_outcome_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/plan_outcome_service.py)
  [backend/app/services/five_layer_learning_contract.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/five_layer_learning_contract.py)

- body-awareness and capability governance  
  File anchors:
  [backend/app/orchestration/capability_selection_policy.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/capability_selection_policy.py)
  [backend/app/services/capability_registry_service.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_registry_service.py)

- AI semantic-control layer with ontology and doctrine renderer  
  File anchors:
  [backend/app/orchestration/ai_strategy_ontology.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/ai_strategy_ontology.py)
  [backend/app/orchestration/ai_strategy_renderer.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/ai_strategy_renderer.py)

### 4.2 What Is Also True

Even though the architecture is now substantial, the product is still not fully proven in the way that matters most.

Specifically:

- many evaluators are still stronger as regression harnesses than as final product truth
- the full mobile product path is not yet the primary truth source
- runnable coherence matters more now than more internal architecture
- human evaluation exists, but still needs to become the central judge

Bottom line:

> **Sparkle is architecture-complete enough to be judged.**  
> **It is not yet product-complete enough to be trusted without live proof.**

---

## 5. What Has Been Built and Is Now Considered v1-Frozen

The founder and implementation runs have already completed a major five-phase architecture chapter.

These areas should be treated as `v1 frozen architecture`, not as open fields for casual redesign.

### 5.1 Phase A: User Insight Engine

Goal achieved:

- compile user truth
- detect missing planning-critical information
- gate planning readiness
- ask before planning when readiness is too low

Current reality:

- canonical insight state exists
- calibration and anti-drift exist
- transparency and user correction exist

Important boundary:

- the architecture is frozen
- the live market-level proof of “best user understanding” is not frozen

### 5.2 Phase B: Planning Engine

Goal achieved:

- compile planning strategy
- define plan-quality contract
- gate weak plans
- benchmark planning quality in a controlled harness

Important boundary:

- benchmark is useful regression evidence
- benchmark is not final product truth

### 5.3 Phase C: Feedback and Growth Engine

Goal achieved:

- plan outcomes can be recorded
- learning can be synthesized and promoted
- five-layer growth logic can feed back into planning

Important boundary:

- evaluation harnesses are still structured regression tools
- final truth still requires real user outcomes and transcript review

### 5.4 Phase D: Body Awareness and Capability Governance

Goal achieved:

- Sparkle can maintain a body map / capability view
- it can compile requirement profiles
- it can apply bounded selection and bounded knob governance

Important boundary:

- evaluation harnesses remain controlled
- final product truth requires live-path verification

### 5.5 Phase E: Five-Layer Learning System

Goal achieved:

- constitutional / session / episode / profile / system layers now exist as a governed learning structure
- conflict resolution and drift firewall exist

Important boundary:

- evaluator remains a regression harness, not final product proof

### 5.6 AI Semantic-Control Layer

This deserves special emphasis.

The AI system used to expose many opaque raw strategy tags directly to the model.
That layer has now been reworked into:

- ontology-backed strategy terms
- doctrine rendering
- model-facing natural-language control guidance
- compliance tracing

Important boundary:

- semantic-control architecture is frozen as `v1`
- real-world proof that the AI system follows doctrine well enough still depends on live transcripts

---

## 6. The Most Important Historical Correction

One of the most important internal realizations came from the data-utilization audit:

[docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md)

That audit established a crucial truth:

> Sparkle had collected much more user data than it was actually turning into model-visible understanding.

The corrected diagnosis was:

- collection and storage were relatively strong
- context assembly was partial
- prompt rendering was leakier than expected
- actual model consumption of user data was much lower than architectural confidence suggested

This led to the Stage 2 profile-and-insight work:

- canonical `UserInsightState`
- signal registry
- multi-span analysis
- bounded prediction
- calibration and correction
- transparency and user control

This history matters because external AI systems should not assume Sparkle is “just a big memory system.”

The real design challenge has been:

> how to convert in-app behavioral data into model-visible, decision-useful understanding without drift, fake certainty, or dead data

---

## 7. What Stage 2 Actually Means

Stage 2 is not “build more architecture.”

Stage 2 means:

> **move from internal system completion to runnable product coherence and live alpha truth**

The top-level Stage 2 document is:

[docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md)

The real focus now is:

1. runnable full-stack path
2. real north-star loop
3. visible adaptation UX
4. human evaluation and transcript review
5. product simplification around the core loop

This is the most important context external AIs must preserve:

> Sparkle does not primarily need new abstract architecture right now.  
> It needs sharper system-level decisions that help the product become coherent, visible, and provably helpful.

---

## 8. The Founder’s Current Design Concern

The founder is now thinking beyond “did we implement enough modules?”

The current concern is:

> **How do we build the next stage of Sparkle as a truly adaptive, meta-cognitive system without drifting into philosophy theater or disconnected architecture?**

There are several active lines of thinking behind this:

- long-horizon, high-value goals create special failure modes
- top human experts do not merely answer; they regulate uncertainty, strategy, pacing, and evidence acquisition
- Sparkle may need a next-generation adaptive harness engineering layer
- the system may need stronger self-modeling and better evidence loops, not just more planning heuristics

This is where the founder has been discussing ideas with Claude and ChatGPT.

That discussion is valuable, but it must remain grounded in actual Sparkle constraints.

---

## 9. How External AIs Should Interpret the “Amadeus / DCT” Material

The founder has also been reflecting on Amadeus / DCT / CC-style ideas and asking what can migrate into Sparkle.

The correct way to interpret that material is:

### 9.1 What Can Migrate

Not the metaphysics.

What can migrate are the **engineering-grade abstractions** that cut real system problems cleanly.

The most promising examples are:

- residual typing
- impact grading
- self-model / confidence profile
- truth-vs-normative basis separation
- evidence-closure loops
- growth-jump typologies for user and system learning

### 9.2 What Should Not Migrate Directly

These should not be used as direct product-design foundations:

- ontology-first metaphysical claims
- consciousness theories
- unfalsifiable global worldviews

The right internal posture is:

> use the theory to generate good distinctions  
> use engineering evidence to decide whether those distinctions deserve to live in Sparkle

---

## 10. The Most Useful External-AI Contributions Right Now

External AIs are most helpful when they operate at the following level:

### 10.1 Useful

- identifying missing schemas or state objects
- sharpening system boundaries
- identifying where a current loop lacks evidence or self-modeling
- helping define telemetry, residual typing, impact grading, checkpoint logic, or self-calibration structures
- helping compress large philosophical intuitions into practical system contracts
- comparing possible next-stage designs against the current code-backed reality

### 10.2 Less Useful Right Now

- proposing major new foundational architecture layers without checking existing implementation
- treating synthetic benchmark wins as final product truth
- recommending a fully new system identity while ignoring the frozen product thesis
- abstract AGI or consciousness framing that does not resolve a concrete Sparkle system decision

---

## 11. What External AIs Need to Know About Real Constraints

### 11.1 Data Constraint

Sparkle does not rely on cross-app OS-level surveillance.

The main design principle is:

> **understand the user using only Sparkle’s own in-app signals, uploaded materials, interaction history, and feedback loops**

That is why the profile/insight system is so central.

### 11.2 Product Constraint

Sparkle must remain legible to ordinary users.

It cannot become a hidden black box that “knows everything” but never exposes or lets the user correct anything.

Transparency and user control are product requirements, not optional extras.

### 11.3 Strategy Constraint

The system now has enough architecture.

So the next strong ideas must usually look like:

- one new schema
- one new telemetry dimension
- one new self-model object
- one new evidence loop
- one clearer runtime gate

not:

- one more giant subsystem

---

## 12. Current Open Questions Worth External Strategic Help

These are the highest-value design questions now.

### 12.1 System Self-Model

Sparkle has become strong at modeling the user.
It is still weaker at modeling itself.

An important next question is:

> How should Sparkle represent its own confidence, likely failure regimes, and recommended governance intensity by task type?

This is a strong candidate for next-stage work.

### 12.2 Evidence-Closure / Checkpoint Design

Sparkle still lacks enough cheap, deliberate verification probes.

Important question:

> How should Sparkle insert low-cost checkpoint mechanisms that calibrate its own understanding and plan assumptions before large failures accumulate?

### 12.3 Residual Typing and Governance Unification

Sparkle already has many gates and validators, but they are not all expressed through one residual taxonomy.

Important question:

> Would an explicit residual-type schema unify adaptation logic, telemetry, and future dynamic thresholds without adding too much conceptual weight?

### 12.4 Impact Grading

The system already treats planning as high-impact in practice, but impact governance is not yet one universal front-door schema.

Important question:

> Should Sparkle add an explicit impact-level object before routing so governance intensity is more coherent across response types?

### 12.5 Basis Separation in Planning

Important question:

> Should planning outputs distinguish between epistemic claims and normative recommendations so user disagreement can be routed correctly?

This would help separate:

- “you misunderstood my state”
- from
- “your proposed path conflicts with my values or preferences”

---

## 13. The Most Important Practical Reminder

External AI systems should not judge Sparkle as if it were still at the “invent the architecture” stage.

That stage is largely over.

The correct framing now is:

> Sparkle already has a serious internal organism.  
> The central challenge is turning that organism into a coherent, visible, trustworthy, provably helpful product.

So the right advice is usually:

- compress
- clarify
- unify
- instrument
- prove

more than:

- expand
- philosophize
- proliferate modules

---

## 14. Recommended Reading Order for External AI Reviewers

If an external AI system is being given multiple documents, the recommended order is:

1. [docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_PRODUCT_THESIS_AND_REFOCUSED_ROADMAP_2026-04-05.md)
2. [docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_DATA_UTILIZATION_ANALYSIS_2026-04-06.md)
3. [docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_STAGE2_PRODUCT_COHERENCE_AND_LIVE_ALPHA_PLAN_2026-04-06.md)
4. [docs/product/SPARKLE_CODEX_ALIGNMENT_AND_HANDOFF_2026-04-07.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_CODEX_ALIGNMENT_AND_HANDOFF_2026-04-07.md)
5. this document

If only one document can be sent, send this one.

---

## 15. Final Compression

If an external AI only remembers five things, they should be these:

1. Sparkle’s real product is `understand user -> build plan -> adapt through feedback`.
2. The two moats are `user understanding quality` and `plan quality`.
3. Phases A-E and the AI semantic-control layer are already built and architecturally frozen as `v1`.
4. The main missing truth is not architecture, but `runnable coherence + human-evaluated product proof`.
5. The next strong ideas should usually come as `compact system contracts`, not as new grand philosophy or major subsystem sprawl.
