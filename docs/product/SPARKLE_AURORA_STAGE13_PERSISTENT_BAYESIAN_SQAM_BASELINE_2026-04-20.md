# SPARKLE Aurora Stage 13 PersistentBayesianLearner SQAM Baseline (2026-04-20)

> **Workstream**: `WS-SQ-MEASURE`
> **Method**: `SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md`
> **Component**: `PersistentBayesianLearner`
> **Verdict**: `repair-first`

## 1. Entry Points Evaluated

Training path:

1. `ToolPreferenceRouter.update_learner_from_history()`

Read path:

1. `PersistentBayesianLearner.get_probability()`

Persistence boundary:

1. `PersistentBayesianLearner` Redis round-trip and reload path

The measurement intentionally uses the real production-shaped call graph for this component. It does **not** redesign the learner or patch the labels during measurement.

## 2. Frozen Audit Fixture

Because Stage 13 has no safe production sampler in this workspace, the measurement uses a frozen audit fixture that mirrors the current routing contract:

| Source state | Target | Raw execution result | User-perceived outcome | Repeats |
| --- | --- | --- | --- | --- |
| `state_plan` | `create_plan` | success | **not helpful** | 5 |
| `state_plan` | `break_down_task` | success | helpful | 3 |
| `state_focus` | `pomodoro_focus` | success | **not helpful** | 4 |
| `state_focus` | `reflection_prompt` | success | helpful | 3 |
| `state_review` | `reopen_error_book` | success | helpful | 4 |
| `state_review` | `semantic_search` | success | **not helpful** | 3 |

Measurement label precedence follows SQAM:

1. `was_helpful`
2. else `user_satisfaction >= 4`
3. else raw `success`

## 3. Dimension Scorecard

| Dimension | Metric | Value | Threshold | Verdict | Notes |
| --- | --- | --- | --- | --- | --- |
| information_density | `ID1 = supported_pairs / observed_pairs` | `1.00` (`6 / 6`) | `>= 0.70` | `wire-ready` | 22 observations across 6 supported pairs; no sparsity failure |
| stability | `ST1 = 1 - max_reload_drift` | `1.00` (`max drift = 0.00`) | `>= 0.95` | `wire-ready` | Stage 12 persistence repair holds across reload |
| discriminative_power | `DP1 = correct_top1_decisions / labeled_source_states` | `0.33` (`1 / 3`) | `>= 0.60` | `repair-first` | top-1 picks optimize for raw success, not actual helpfulness |
| safety_margin | `SM1 = 1 - false_confident_rate` | `0.33` (`1 - 2 / 3`) | `>= 0.85` | `repair-first` | two high-confidence decisions are confidently wrong once user-perceived outcome is applied |

## 4. Why `DP1` and `SM1` Fail

Current production behavior collapses the reward label to raw tool execution success:

```python
source = f\"state_{record.tool_category or 'general'}\"
target = record.tool_name
success = 1 if record.success else 0
await self.learner.update(source, target, success)
```

That means the learner records:

1. "the tool ran without error"
2. but **not** "the tool actually helped"

In the frozen fixture, this causes two false top-1 choices:

| Source state | Top-1 pick under current code | Predicted probability | Effective user outcome |
| --- | --- | --- | --- |
| `state_plan` | `create_plan` | `0.857` | `false` |
| `state_focus` | `pomodoro_focus` | `0.833` | `false` |
| `state_review` | `reopen_error_book` | `0.833` | `true` |

This is not a persistence problem. It is an upstream signal-fidelity problem.

## 5. Ranked Shortfalls

1. **Top-1 shortfall**: reward-label fidelity collapse in `ToolPreferenceRouter.update_learner_from_history()`
   - current label = raw `success`
   - missing signal = `was_helpful` / `user_satisfaction`
   - affected dimensions = `discriminative_power`, `safety_margin`
2. Secondary shortfall: source-state compression to `state_{tool_category}` hides richer workflow context
3. Secondary shortfall: one router integration path still instantiates `ToolPreferenceRouter(..., redis_client=None)` and therefore does not consume persistent state on that path

Only shortfall `#1` is eligible for `WS-SQ-FEED`.

## 6. Stage 13 Decision

`PersistentBayesianLearner` remains **not wire-ready** after Stage 12 substrate repair.

Why:

1. it is now information-dense enough to measure
2. it is stable enough to persist
3. it is **still not trustworthy enough** to drive a user-visible decision path because its top recommendations optimize for execution success rather than user-perceived usefulness

This is exactly the problem `WS-SQ-FEED` must repair.
