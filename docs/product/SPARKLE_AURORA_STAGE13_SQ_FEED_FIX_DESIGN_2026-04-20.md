# SPARKLE Aurora Stage 13 WS-SQ-FEED Fix Design (2026-04-20)

> **Workstream**: `WS-SQ-FEED`
> **Source**: `SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_BASELINE_2026-04-20.md`

## 1. Locked Shortfall

`WS-SQ-FEED` may repair exactly one shortfall:

> reward-label fidelity collapse in `ToolPreferenceRouter.update_learner_from_history()`

Current training treats raw execution success as the only reward label:

```python
success = 1 if record.success else 0
await self.learner.update(source, target, success)
```

This ignores the richer user-perceived outcome signals already present on `UserToolHistory`:

1. `was_helpful`
2. `user_satisfaction`

## 2. Why This Is Upstream Signal Fidelity, Not Learner Redesign

The learner itself remains unchanged:

1. no new learner class
2. no posterior formula change
3. no threshold change
4. no route-selection strategy change

The repair is strictly about feeding the learner a more faithful outcome label from the existing upstream history record.

## 3. Narrow Repair Boundary

Allowed:

1. derive the effective training outcome from `UserToolHistory`
2. prefer `was_helpful`
3. else prefer `user_satisfaction >= 4`
4. else fall back to raw `success`

Not allowed:

1. changing the `source` encoding
2. adding new history columns
3. redesigning `PersistentBayesianLearner`
4. fixing any secondary shortfall from the SQAM report

## 4. Targeted SQAM Improvement

Primary target:

- `DP1` discriminative power

Expected secondary improvement:

- `SM1` safety margin

Stage 13 closeout will rerun the affected dimension on the same frozen fixture and prove that `DP1` improves without moving the Stage 13 thresholds.

## 5. Rule V Regression Assertions

The regression proof must directly reproduce the measured symptom:

1. a tool that technically succeeds but is explicitly marked `was_helpful = false` must not out-rank a tool that succeeds and is marked helpful
2. a tool with `user_satisfaction >= 4` must beat a merely successful tool when `was_helpful` is absent

These tests must survive as permanent guards for the audit symptom named in the Stage 13 SQAM report.
