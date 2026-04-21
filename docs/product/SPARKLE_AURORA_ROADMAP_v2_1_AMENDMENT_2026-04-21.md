# SPARKLE Aurora Roadmap v2.1 Amendment Record (2026-04-21)

> Status: accepted governance amendment after Stage 21 final-accept
> Scope: records the accepted roadmap correction from Aurora roadmap v2.0 to v2.1 without rewriting the already-accepted Stage 16-21 governance chain
> This document supersedes only Stage 22+ sequencing, naming, and dependency interpretation. Stage 16-21 delivered rules and accepted handoffs remain valid historical artifacts.

---

## 0. Amendment Purpose

This amendment exists because three things became true at the same time:

1. Stage 20 and Stage 21 were completed and accepted clean.
2. independent audits showed that several v3.0 roadmap assumptions were factually wrong or methodologically overstated.
3. Stage 22+ planning needed a corrected base before any new dispatch could be issued.

The accepted correction is:

- keep Stage 16-21 intact
- insert Stage 22 as **Baseline Repair**
- move Bayesian wire-on to Stage 23
- move Accountability compiler to Stage 24
- reclassify several later stages from “brand new” to “extension” or “provisional”

---

## 1. Current Accepted State

### Stage Status

| Stage | Status | Notes |
| --- | --- | --- |
| Stage 20 | accept clean | Sufficiency split, Conflict Resolver, Route History all landed with no carry-forward debt |
| Stage 21 | accept clean | Skill MVP landed with 31 backend + 10 mobile + 4 guards green |
| Stage 22 | not yet dispatched | reserved for Baseline Repair only |

### Governance Continuity

The accepted rule chain through Stage 21 remains:

1. Rule Y: inferred write governance
2. Rule Z: cross-user privacy
3. Rule AB: Aggregator integrity
4. Rule AC: Working Memory transience
5. Rule AD: Sufficiency split governance
6. Rule AE: Conflict audit governance
7. Rule AF: Skill cross-user sharing governance

Rule AA remains permanently skipped and must never be reused.

---

## 2. Accepted Fact Corrections

The following v3.0 assumptions were rejected and are now corrected:

1. Reflection was not “missing.” Reflection logic already exists, but it is not yet wired to Bayesian outcome signals.
2. Scaffolding was not “absent.” `ScaffoldingFSM` already tracks capability-zone adaptation, but it is not an SRL three-phase tracker.
3. Metacognition was not “missing.” Calibration tracking already exists, but it does not yet cover the full three-axis bias surface.
4. Prompt-pipe leakage was overstated. `error_summary`, `recent_errors`, and `recent_mastery_changes` are already rendered in prompt assembly, so the old “~30 line fix” claim is invalid.

Operational consequence:

- Stage 22 must begin with a fresh telemetry-backed data-utilization baseline.
- the former `WS-BR-PROMPT-PIPE` repair item is downgraded to `WS-BR-PROMPT-VERIFY`.

---

## 3. Aurora Stage Ladder (v2.1)

| Stage | Theme | Type | Rule |
| --- | --- | --- | --- |
| 21 | Skill MVP | accepted clean | AF |
| 22 | Baseline Repair | debt paydown / substrate repair | — |
| 23 | Bayesian wire-on + SS-AUDIT | planned | reuse Rule W |
| 24 | Accountability Policy Compiler | planned | AG |
| 25 | Reflection Wire-On | extension of existing reflection stack | AH |
| 26 | Scene Consolidation | new capability | AI |
| 27 | Foresight Engine | provisional; reclassify before dispatch after code recheck | AJ |
| 28 | Traits weak-prior layer | new capability | AK |
| 29 | SRLPhaseTracker + scaffold alignment | new service beside existing ScaffoldingFSM | AL |
| 30 | Metacognition three-axis expansion | extension | AM |
| 31 | Idiographic Lite | association only, not causal claims | AN |
| 32 | CL SQAM tail closeout | Track B | — |

Important interpretation:

1. Stage 29 is not a rename of `ScaffoldingFSM`. It is a new `SRLPhaseTracker` service that coexists with capability-zone tracking.
2. Stage 31 is explicitly **Lite**. It may discover user-specific associations, but it may not claim causality or generalize those associations across users.
3. Stage 27 remains provisional until dispatch-time code verification confirms whether it is truly new or partly an expansion of existing prediction-theater coverage.

---

## 4. Stage 22 Baseline Repair Bundle

Stage 22 is now locked as a 7-workstream repair stage.

| WS | Name | Nature |
| --- | --- | --- |
| WS-BR-DATA-BASELINE | telemetry-backed data-utilization rescore | new |
| WS-BR-PROMPT-VERIFY | prompt rendering coverage audit | downgraded from false repair claim |
| WS-BR-LOOP-CLOSURE | error→replan bridge expansion + worker permanence | real gap |
| WS-BR-ACHIEVEMENT-WIRE | achievement signals into AI-visible context with explicit consumers | real gap |
| WS-BR-CALENDAR-WIRE | calendar signals into AI-visible context | real gap |
| WS-BR-INTERVENTION-Q | intervention learner cohort fallback + queue bug repair | real gap |
| WS-BR-SEED-VERIFY | seed adoption→action→outcome verification loop | to verify in dispatch preflight |

Stage 22 acceptance framing is also corrected:

1. no fixed `5.0/10 → 7.0/10` baseline is allowed anymore
2. Stage 22 must first produce `DATA_UTILIZATION_SCORECARD_2026-04-21.md`
3. final improvement target is `re-measured baseline + 2.0`, not a stale absolute delta

Additional lock:

`WS-BR-ACHIEVEMENT-WIRE` must define at least two concrete AI consumer paths. “Make achievements visible” is not enough by itself.

---

## 5. Dependency Correction

The previously asserted dependency chain “Stage 22 Bayesian before reflection” was false.

The corrected dependency model is:

```text
Stage 21 (Skill) ──┐
Stage 20 ──────────┤
Stage 18 ──────────┴─→ Stage 22 (Baseline Repair) ─→ Stage 23 (Bayesian)
                                                      ├─→ Stage 24 (Accountability)
                                                      ├─→ Stage 25 (Reflection Wire-On)
                                                      ├─→ Stage 26 (Scene Consolidation)
                                                      ├─→ Stage 27 (Foresight)
                                                      ├─→ Stage 28 (Traits)
                                                      ├─→ Stage 29 (SRLPhaseTracker)
                                                      └─→ Stage 30 (Metacognition Expansion)

Stage 23 + sampling-density gate ─→ Stage 31 (Idiographic Lite)
Stage 31 complete ────────────────→ Stage 32 (CL SQAM tail closeout)
```

Resource note:

- Stage 25 and Stage 26 are parallelizable in principle.
- if execution bandwidth is limited, the default order is `25 → 26`.

---

## 6. Rule Ladder After Stage 21

| Rule | Stage | Meaning |
| --- | --- | --- |
| AG | 24 | Accountability compiler governance |
| AH | 25 | reflection-loop contamination guard |
| AI | 26 | scene clustering idempotence + temporal anchoring |
| AJ | 27 | prediction cannot become control flow; JITAI threshold governance |
| AK | 28 | traits remain low-confidence, non-exposed, easily overruled |
| AL | 29 | SRL / SDT language governance, option-count floor, empathy budget |
| AM | 30 | metacognition output may not use diagnostic terms |
| AN | 31 | idiographic association may not cross users or claim causality |

---

## 7. Long-Range Red Lines

The following red lines are now explicitly locked for Stage 22+ planning:

1. The product may adapt to traits; it may not try to “fix” or “cure” personality.
2. Clinical diagnostic labels such as ADHD, depression, or anxiety disorder must not appear in AI output paths.
3. Continuous empathic mirroring may not exceed two consecutive turns without moving to data, options, or reframing.
4. The system may not guess social class, family background, or social role without explicit user evidence.
5. Psychological inference may not jump from task-level evidence to person-level labels.
6. Trait labels may not appear in user-facing UI surfaces.
7. Later-stage prediction outputs may not become router control-flow branches unless an explicit future rule says otherwise.

---

## 8. Dispatch Preconditions For Future Stages

Before any Stage 22 or later dispatch is issued, Codex must explicitly verify:

1. whether prediction-theater already contains any real foresight surface relevant to Stage 27
2. whether `ScaffoldingFSM` contains any latent SRL-phase hooks or must be treated as fully separate from `SRLPhaseTracker`
3. whether `reflection_agent` can be connected to route-history outcomes without fewer than 4 workstreams

Current lock:

- Stage 25 must assume **at least 4 WS**
- Stage 29 must assume **new service creation**, not mere prompt or FSM tuning
- Stage 31 must use an operational sampling-density gate, not a hardcoded “90 day” myth

---

## 9. Immediate Follow-On State

As of 2026-04-21:

1. Stage 21 is accepted clean.
2. Stage 22 dispatch is now issued through:
   - [SPARKLE_AURORA_STAGE22_DISPATCH_PLAN_2026-04-21.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE22_DISPATCH_PLAN_2026-04-21.md)
   - [SPARKLE_AURORA_ROADMAP_v2_1_FAST_DEV_LOCK_2026-04-21.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_ROADMAP_v2_1_FAST_DEV_LOCK_2026-04-21.md)
3. Stage 23 obligations are now locked by Stage 22 dispatch §6 and inherited by fast-dev execution.

This amendment remains the stage-ladder source of truth for Aurora roadmap sequencing until a later amendment supersedes it; dispatch and fast-dev execution now hang off this amendment rather than replacing it.
