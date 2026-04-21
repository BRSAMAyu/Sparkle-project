# Sparkle Product Thesis and Refocused Roadmap

> Date: 2026-04-05  
> Status: Active strategic product definition  
> Audience: Founder, chief designer, product, engineering, implementation Codex runs  
> Companion docs:
> - `docs/product/SPARKLE_AI_NATIVE_SYSTEM_CONSENSUS_2026-04-03.md`
> - `docs/product/SPARKLE_NEXT_PHASE_MASTER_PLAN_2026-04-04.md`
> - `docs/product/SPARKLE_LIVE_ALPHA_GATE_2026-04-04.md`
> - `docs/product/SPARKLE_RESIDUAL_DECISION_POLICY_AND_EXPERIENCE_PHASE_PLAN_2026-04-04.md`
> - `docs/product/SPARKLE_LIVE_PRODUCT_INTEGRATION_AND_EVALUATION_PLAN_2026-04-04.md`

---

## 0. Why This Document Exists

We now have a clearer product view.

The system vision is still large:

- self-achievement
- growth
- deep user understanding
- AI-native operating system
- one Sparkle for each user

But the product must win somewhere concrete before it earns the right to become everything else.

This document sharpens the center of gravity.

It defines:

1. what Sparkle is actually trying to be right now
2. what our real competitive moat is
3. what the product loop really is
4. what we should optimize for before broader ambition
5. how the roadmap should be interpreted through this lens

---

## 1. The Product Thesis

Sparkle is not primarily a general-purpose AI assistant.

Sparkle is:

> **an AI-native planning and guidance operating system for ordinary users who cannot manually extract the best results from frontier AI on their own**

More concretely:

> **Sparkle helps users understand how to achieve their important goals, and then gives them better plans, better next moves, and better ongoing guidance than they would get from raw AI use alone.**

This is the current product wedge.

Not “do everything.”
Not “be the most agentic.”
Not “have the most tools.”

The wedge is:

> **understand the user deeply, then turn that understanding plus their data into the best plan**

---

## 2. The Two True Moats

Everything in Sparkle should ultimately strengthen one of these two moats.

### 2.1 Moat A: User Understanding Quality

Sparkle should understand the user better than the user can currently articulate alone.

This does **not** mean mystical omniscience.

It means practical, high-value insight into:

- what the user really wants
- why it matters
- what constraints are real
- what bottleneck is active now
- what information is still missing
- what guidance style works for this user
- what patterns the user cannot easily see in themselves

The product standard is:

> **Sparkle should surface things the user cannot easily see alone, in a way the user recognizes as true.**

### 2.2 Moat B: Plan Quality

Sparkle should produce:

- a better plan
- a better task sequence
- a better next move
- a better pacing strategy
- a better explanation path
- a better adaptation path

than a user would typically get by using raw OpenAI/Anthropic prompting directly.

This is the true market test.

If Sparkle cannot beat raw model usage for non-expert users on plan quality, the rest of the architecture does not matter.

---

## 3. Who The Product Is For

Sparkle is not being built first for power users who already know:

- prompt engineering
- context packing
- model selection
- how to structure a good planning request

Sparkle is being built first for:

> **the majority of capable but non-expert users who have important goals, valuable data, and weak AI-operating skill**

Examples:

- students preparing for finals
- people trying to learn difficult material under deadline
- people with real goals but poor self-structuring ability
- users who know they want something but do not know how to turn their situation into the right plan

This is why Sparkle matters.

We are reducing the AI skill gap.

---

## 4. The Current Product Loop

The current Sparkle loop should be understood as:

1. `Identify the goal`
2. `Understand the user deeply enough`
3. `Build the best plan and next moves`
4. `Support execution through guidance and adaptation`
5. `Summarize results and collect feedback`
6. `Use feedback to improve the next cycle`

This loop is evolutionary.

### 4.1 The Most Important Clarification

At the current stage, Sparkle is primarily:

> **the designer, strategist, guide, and adaptive planner**

It is not yet required to perform the entire action world itself.

Execution may be done by:

- the user
- OpenClaw
- Claude Code
- Codex
- future execution agents

That execution layer matters later.

Right now, Sparkle must first become excellent at:

- understanding
- planning
- adapting
- learning

---

## 5. What The Architecture Is For

All architecture, modules, and subsystems should be treated as servants of the two moats.

### 5.1 Systems That Serve Understanding

These exist to improve user understanding quality:

- memory
- behavior profiling
- feedback binding
- residual diagnosis
- companion continuity
- semantic state mapping
- body-awareness context
- human evaluation transcripts

### 5.2 Systems That Serve Plan Quality

These exist to improve plan quality:

- situation brief
- strategy state
- decision policy
- grounding and user-material retrieval
- planning pipeline
- intervention families
- pacing adaptation
- execution feedback loop

### 5.3 Systems That Are Secondary Until They Improve The Two Moats

These are valuable, but secondary unless they materially improve understanding or plan quality:

- achievements
- visual systems
- BGM
- community
- decorative dashboards
- additional agents without a clear planning benefit

This does not mean they are unimportant.
It means their right to exist depends on user benefit.

---

## 6. The Core User Experience

## 6.5 Aurora Stage Naming Update (Amended 2026-04-21)

The Aurora implementation roadmap is now governed by the accepted v2.1 amendment record:

- [SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_ROADMAP_v2_1_AMENDMENT_2026-04-21.md)

The active stage ladder is:

1. Stage 19: Working Memory + LLM extract dry-run + consolidation
2. Stage 20: Sufficiency Judge + Conflict Resolver + Route History
3. Stage 21: Skill MVP
4. Stage 22: Baseline Repair
5. Stage 23: Bayesian wire-on + SS-AUDIT
6. Stage 24: Accountability Policy Compiler
7. Stage 25: Reflection Wire-On
8. Stage 26: Scene Consolidation
9. Stage 27: Foresight Engine
10. Stage 28: Traits weak-prior layer
11. Stage 29: SRLPhaseTracker beside ScaffoldingFSM
12. Stage 30: Metacognition three-axis expansion
13. Stage 31: Idiographic Lite
14. Stage 32: CL SQAM tail closeout

Rule naming is correspondingly locked as:

1. Rule AD: Sufficiency Judge governance
2. Rule AE: Conflict Resolver governance
3. Rule AF: Skill cross-user sharing governance
4. Rule AG: Accountability compiler governance
5. Rule AH: reflection-loop contamination guard
6. Rule AI: scene clustering idempotence + temporal anchoring
7. Rule AJ: prediction cannot become control flow
8. Rule AK: traits remain low-confidence and non-exposed
9. Rule AL: SRL / SDT language governance + empathy budget
10. Rule AM: metacognition outputs may not use diagnostic labels
11. Rule AN: idiographic association may not cross users or claim causality

Operational locks from the amendment are:

1. Stage 22 is a repair stage, not a Bayesian stage, and introduces no new rule family.
2. Stage 23 is the first stage allowed to consume `Route History + Sufficiency + Skill injection evidence` for Bayesian wiring, and it may not build a parallel history collector.
3. Stage 25 and Stage 26 are parallelizable in theory, but the default order under constrained execution bandwidth is `25 → 26`.
4. Stage 29 does not rename `ScaffoldingFSM`; it adds a separate `SRLPhaseTracker`.
5. Stage 31 is intentionally Lite: it may discover user-specific associations but may not claim causality.

The core user experience is not:

- “Sparkle is smart”
- “Sparkle has many features”
- “Sparkle feels emotional”

The core user experience is:

> **Sparkle understood my real situation, turned my information into a better plan than I could have made myself, and kept improving that plan as reality changed.**

This is the product.

### 6.1 In the 14-Day Exam Scenario

Sparkle should:

- know what information it still needs
- pull what matters from the user’s materials
- identify what the user actually misunderstands
- produce the best possible study plan
- adjust the plan when the load is too high
- preserve continuity when the user struggles
- learn from the result

If Sparkle cannot do that better than a direct raw-model workflow, the product is not ready.

### 6.2 In Future Non-Study Domains

The same loop still applies:

- understand the person
- understand the goal
- understand the obstacle
- build the best guidance path
- adapt it
- learn from outcomes

So the substrate remains right.
The wedge remains planning and guidance.

---

## 7. The Competitive Standard

Sparkle should be judged against a hard benchmark:

> **Can Sparkle produce better user-specific plans and guidance than frontier AI used directly by a non-expert user?**

This implies a practical comparison framework.

### 7.1 Benchmark Setup

Give both Sparkle and a raw frontier model the same:

- goal
- deadline
- materials
- baseline state
- constraints
- recent failures

Then compare:

- understanding quality
- plan quality
- task usefulness
- pacing quality
- adaptation quality
- user trust
- follow-through

### 7.2 The Rule

If Sparkle does not clearly win on these dimensions for non-expert users, we have not built the moat yet.

---

## 8. What The Product Must Be Best At

Sparkle should be best at:

1. understanding the user’s true bottleneck
2. identifying what information is still missing
3. turning user data into understanding
4. turning understanding into the best plan
5. adapting that plan as reality changes
6. remembering what worked for that user

Not:

- the broadest tool use
- the most actions executed
- the largest feature surface
- the most “agentic” vibe

Those may come later.
They are not the first battle.

---

## 9. What This Means For The Current Roadmap

The six-phase roadmap is still valid.

But it must be interpreted through the new product thesis.

### 9.1 Phase 1: Live Alpha Closure

Interpretation:

Make the planning-and-guidance loop trustworthy.

This phase matters because Sparkle cannot beat competitors if its core loop is not reliable.

### 9.2 Phase 2: Felt Adaptation UX

Interpretation:

Make plan adaptation visible so users can feel that Sparkle is not generic.

This phase matters because plan quality is not enough if the user cannot perceive adaptation and trust it.

### 9.3 Phase 3: Human Evaluation Loop

Interpretation:

Judge plan usefulness and user understanding quality with real humans.

This phase matters because tests cannot prove the moat.

### 9.4 Phase 4: Body Awareness v1

Interpretation:

Teach Sparkle enough about its own body to improve understanding and plan generation.

This phase should only advance where it strengthens the two moats.

### 9.5 Phase 5: Complete the Five-Layer Learning System

Interpretation:

Make Sparkle better over time for each user.

This is how Sparkle stops being a one-shot planner and becomes a real evolving guidance system.

### 9.6 Phase 6: Organic System Integration

Interpretation:

Unify the broader body only after the core wedge is undeniably strong.

Organic integration is important.
But not before we win the planning battle.

---

## 10. The Immediate Product Priorities

The next product priorities should be:

1. prove the core planning loop is trustworthy
2. prove Sparkle produces better plans than raw AI use for non-experts
3. make adaptations visible and trust-building
4. run human evaluations focused on plan usefulness
5. only then deepen body-awareness and broader system integration

This is the correct priority order.

---

## 11. What To Build More Of

We should build more of:

- user understanding quality
- data utilization quality
- plan quality
- adaptation quality
- continuity quality
- transcript-driven product learning

We should especially improve:

- cold-start information acquisition
- user-material utilization
- bottleneck diagnosis
- plan decomposition quality
- pacing control
- adaptation reversibility
- cross-session learning

---

## 12. What To Build Less Of

We should build less of:

- architecture for its own sake
- broad new surfaces that do not improve the plan moat
- “AI-native” features that are mostly aesthetic
- extra orchestration complexity without measurable user benefit
- expansion into too many domains before the wedge is strong

---

## 13. The Cold-Start Requirement

You clarified something very important:

When the user first uses Sparkle, the system does not yet know enough.

So Sparkle must become excellent at:

> **knowing what information it still needs in order to form a deep enough understanding to generate a high-quality plan**

This means cold start is not a minor onboarding issue.
It is part of the moat.

Sparkle should know how to ask for:

- the real goal
- the deadline
- the available materials
- the user’s current level
- the user’s constraints
- the user’s behavior risks
- the most important missing evidence

This should become a dedicated product focus.

---

## 14. The AI-Native Meaning In This Context

AI-native does not mainly mean:

- many models
- many agents
- many tools

It means:

> **the system itself knows how to acquire the information it needs, interpret the user, choose the right internal capabilities, and produce the best plan through an evolving loop**

That is the practical meaning of AI-native for Sparkle.

---

## 15. The Right Success Question

From now on, the main success question should be:

> **Does this make Sparkle better at understanding users and generating better plans than raw AI for non-expert users?**

If yes, it is probably on-strategy.
If no, it is probably secondary.

---

## 16. The Next Strategic Milestone

The next true milestone remains:

> **Sparkle Live Alpha**

But Live Alpha should now be read with sharper meaning:

Sparkle Live Alpha means:

- the planning-and-guidance loop is trustworthy
- users can feel adaptation
- human evaluators can confirm plan usefulness
- Sparkle is beginning to know its own body
- Sparkle is measurably closer to winning the two moats

---

## 17. Final Guiding Sentence

Sparkle is not trying to win by doing everything.

Sparkle is trying to win by doing one extremely valuable thing better than anyone else:

> **deeply understanding ordinary users and turning their data, goals, and constraints into better plans and guidance than raw AI use can provide on its own.**

That is the product thesis.
That is the wedge.
That is what all future work must serve.
