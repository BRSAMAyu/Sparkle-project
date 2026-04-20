# SPARKLE Aurora Stage 13 Signal Quality Audit Method (SQAM) (2026-04-20)

> **Workstream**: `WS-SQ-METHOD`
> **Purpose**: define the formal measurement gate required by Rule W before any continuous-learning component may be considered wire-ready.
> **Authority**: `SPARKLE_AURORA_STAGE13_DISPATCH_PLAN_2026-04-20.md`

## 1. Rule W Citation

This document is the Stage 13 authority for Rule W.

Future stages must cite this method when they make any "wire / not wire" claim about a continuous-learning component. They may not:

1. skip a dimension
2. replace a metric without an explicit method revision
3. lower a threshold after seeing measurement results
4. treat `unmeasurable` as a soft-pass

## 2. Scope

`SQAM` applies to continuous-learning components whose outputs could eventually influence a user-visible read or decision path.

Stage 13 applies it first to:

- `PersistentBayesianLearner`

## 3. Rating Scale

Each dimension produces one of:

- `wire-ready`
- `repair-first`
- `unmeasurable`

Hard interpretation:

1. a component is **not wire-ready** unless all four dimensions are `wire-ready`
2. any `unmeasurable` dimension automatically blocks wiring
3. threshold changes require a method revision, not a measurement-side exception

## 4. Evaluation Window

Default audit window:

1. recent 30-day production-shaped history when available
2. otherwise a frozen audit fixture that mirrors the current production entrypoint and call graph

Stage 13 uses a frozen audit fixture because no safe production sampling job exists in this repo workspace.

## 5. Four Dimensions

### 5.1 Information Density

**Question**

Does the component have enough labeled observations, across enough source-target pairs, to carry a meaningful signal?

**Metric**

`ID1 = supported_pairs / observed_pairs`

Where:

- `observed_pairs` = distinct `source -> target` pairs seen in the audit window
- `supported_pairs` = observed pairs whose posterior observation count is at least `3`
- posterior observation count = `alpha + beta - 2`

**Wire-ready threshold**

`ID1 >= 0.70`

**Fallback / no-data rule**

Mark `unmeasurable` if either condition is true:

1. total observations in the audit window `< 12`
2. observed pairs `< 4`

**Why this threshold exists**

A learner that only has a handful of labeled edges may be technically "running" while still carrying too little information to justify user-visible use.

### 5.2 Stability

**Question**

Does the component preserve its signal across persistence boundaries, or does the score drift when the process reloads?

**Metric**

`ST1 = 1.0 - max_reload_drift`

Where:

- `max_reload_drift = max(|p_before_reload - p_after_reload|)` across all supported pairs
- `p_*` are probabilities returned by the real component entrypoint before and after a persistence round-trip

**Wire-ready threshold**

`ST1 >= 0.95`

Equivalent interpretation:

- `max_reload_drift <= 0.05`

**Fallback / no-data rule**

Mark `unmeasurable` if there are no supported pairs to round-trip.

**Why this threshold exists**

If a score meaningfully changes across a reload boundary, it is not stable enough to govern a user-visible read path.

### 5.3 Discriminative Power

**Question**

Can the component distinguish "technically succeeded" from "actually helped the user" when choosing a top route?

**Metric**

`DP1 = correct_top1_decisions / labeled_source_states`

Where:

- evaluate each source state that has at least two candidate targets
- choose the component's top-1 target by predicted probability
- define the effective user outcome label in this order:
  - `was_helpful`
  - else `user_satisfaction >= 4`
  - else raw `success`
- a top-1 decision is `correct` when the chosen target's effective user outcome label is `true`

**Wire-ready threshold**

`DP1 >= 0.60`

**Fallback / no-data rule**

Mark `unmeasurable` if fewer than `3` source states have both:

1. at least two candidate targets
2. at least one effective outcome label

**Why this threshold exists**

A learner that cannot separate "the tool ran" from "the tool genuinely helped" is not ready to influence a user-facing path, even if its infrastructure is healthy.

### 5.4 Safety Margin

**Question**

How often does the component become confidently wrong?

**Metric**

`SM1 = 1.0 - false_confident_rate`

Where:

- high-confidence decision = predicted probability `>= 0.70`
- false-confident decision = high-confidence decision whose effective user outcome label is `false`
- effective user outcome label uses the same precedence as `DP1`

**Wire-ready threshold**

`SM1 >= 0.85`

Equivalent interpretation:

- `false_confident_rate <= 0.15`

**Fallback / no-data rule**

Mark `unmeasurable` if the audit window contains zero high-confidence decisions.

**Why this threshold exists**

A component that is often confidently wrong is more dangerous than one that is merely sparse.

## 6. Worked Example

This example is illustrative and freezes the method shape before Stage 13 measurement.

### 6.1 Fixture Shape

Source states:

1. `state_plan`
2. `state_focus`
3. `state_review`

Candidate targets per state:

1. one target with more raw execution successes
2. one target with better user-perceived helpfulness

### 6.2 Example Read

If the learner is trained on raw `success` only:

- `ID1` may still pass because enough observations exist
- `ST1` may still pass because persistence is healthy
- `DP1` may fail because top-1 choices optimize for execution success instead of helpfulness
- `SM1` may fail because high-confidence picks can still be unhelpful

This is exactly why Rule W exists: a repaired substrate can still be non-wireable for quality reasons.

## 7. Verdict Template

Every SQAM report must include:

| Dimension | Metric | Value | Threshold | Verdict | Notes |
| --- | --- | --- | --- | --- | --- |
| information_density | `ID1` | ... | `>= 0.70` | ... | ... |
| stability | `ST1` | ... | `>= 0.95` | ... | ... |
| discriminative_power | `DP1` | ... | `>= 0.60` | ... | ... |
| safety_margin | `SM1` | ... | `>= 0.85` | ... | ... |

The report must also state:

1. which component was measured
2. which production entrypoints were evaluated
3. which shortfall ranked `#1`
4. whether the component is `wire-ready`, `repair-first`, or `unmeasurable`

## 8. Stage 13 Lock

The thresholds in this method are frozen for Stage 13:

- `ID1 >= 0.70`
- `ST1 >= 0.95`
- `DP1 >= 0.60`
- `SM1 >= 0.85`

`WS-SQ-MEASURE` may use these thresholds only as written. It may not tune them after observing the data.
