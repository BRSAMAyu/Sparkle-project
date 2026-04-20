# SPARKLE Aurora Stage 12 WS-CL2a Fix Design (2026-04-20)

> **Status**: pre-implementation artifact for `WS-CL2a`
> **Goal**: repair the Redis key mismatch between the live `PersistentBayesianLearner` and the persistence helper path.

## 1. Current Symptom

Stage 11 CL0 found a real persistence split:

- live learner reads / writes `learner:{user_id}`
- helper task `persist_bayesian_data` writes `bayesian_learner:{user_id}`

This means a helper-written state is invisible to the live learner.

## 2. Target State

`PersistentBayesianLearner` and its helper path must converge on:

- canonical key: `learner:{user_id}`
- canonical TTL: `86400 * 7` seconds

## 3. Compatibility Strategy

Stage 12 will not introduce a heavyweight migration script.

Instead:

1. helper write path will be aligned to `learner:{user_id}`
2. learner load path may optionally include a compatibility read from `bayesian_learner:{user_id}` if needed for a soft transition
3. old `bayesian_learner:` keys are allowed to age out naturally under TTL

## 4. TTL Choice

Use `7 days` as the canonical TTL because it already matches the live learner's current implementation and is sufficient for short-horizon routing memory.

Stage 12 will not widen this TTL unless a regression test proves the current window is insufficient.

## 5. Rule V Regression Proof

`WS-CL2a` must add a regression test that proves the original audit symptom and the repaired behavior:

1. seed Redis through the helper path semantics
2. instantiate the live learner
3. assert the learner can read the seeded state under the fixed key contract
4. retain a negative assertion proving the old split would have left the live learner empty

## 6. Out-of-Scope

1. changing routing algorithms
2. changing user-facing behavior
3. surfacing Bayesian stats to the front door
