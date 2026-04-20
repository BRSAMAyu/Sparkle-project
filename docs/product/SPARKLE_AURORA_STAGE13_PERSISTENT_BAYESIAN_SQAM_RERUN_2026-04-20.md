# SPARKLE Aurora Stage 13 PersistentBayesianLearner SQAM Rerun (2026-04-20)

> **Purpose**: record the post-`WS-SQ-FEED` rerun of the same frozen SQAM fixture used in the Stage 13 baseline report.
> **Method**: `SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md`
> **Baseline report**: `SPARKLE_AURORA_STAGE13_PERSISTENT_BAYESIAN_SQAM_BASELINE_2026-04-20.md`

## 1. Frozen Fixture Reused

The rerun reuses the exact same Stage 13 fixture:

1. three source states: `state_plan`, `state_focus`, `state_review`
2. six observed `source -> target` pairs
3. 22 total observations
4. effective outcome label precedence unchanged:
   - `was_helpful`
   - else `user_satisfaction >= 4`
   - else raw `success`

No threshold changed between baseline and rerun.

## 2. Scorecard Delta

| Dimension | Baseline | Rerun | Threshold | Delta | Verdict |
| --- | --- | --- | --- | --- | --- |
| information_density (`ID1`) | `1.00` | `1.00` | `>= 0.70` | `0.00` | unchanged pass |
| stability (`ST1`) | `1.00` | `1.00` | `>= 0.95` | `0.00` | unchanged pass |
| discriminative_power (`DP1`) | `0.33` | `1.00` | `>= 0.60` | `+0.67` | repaired |
| safety_margin (`SM1`) | `0.33` | `1.00` | `>= 0.85` | `+0.67` | repaired |

## 3. Why The Rerun Improved

`WS-SQ-FEED` changed only the upstream reward label used by `ToolPreferenceRouter.update_learner_from_history()`:

1. prefer `was_helpful`
2. else prefer `user_satisfaction >= 4`
3. else fall back to raw `success`

No learner formula changed. No threshold changed. The improvement comes from feeding the learner a truer label.

## 4. Representative Top-1 Decisions After Repair

| Source state | Top-1 pick after rerun | Predicted probability | Effective user outcome |
| --- | --- | --- | --- |
| `state_plan` | `break_down_task` | `0.800` | `true` |
| `state_focus` | `reflection_prompt` | `0.800` | `true` |
| `state_review` | `reopen_error_book` | `0.833` | `true` |

## 5. Stage 14 Entry Consequence

Under Rule W and the frozen Stage 13 method, `PersistentBayesianLearner` is now:

- `wire-ready`

Hard interpretation:

1. this does **not** auto-wire the component into the front door
2. this **does** unlock Stage 14 Path A:
   - Stage 14 may propose a bounded `WS-CL1` candidate for `PersistentBayesianLearner` only
3. no claim is made here about the other four continuous-learning components
