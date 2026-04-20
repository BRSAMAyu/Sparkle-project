# SPARKLE Aurora Stage 14 PersistentBayesianLearner SQAM Scale Rerun (2026-04-20)

> **Workstream**: `WS-CL1-SCALE`
> **Method**: `SPARKLE_AURORA_STAGE13_SIGNAL_QUALITY_AUDIT_METHOD_2026-04-20.md`
> **Fixture authority**: `backend/tests/fixtures/persistent_bayesian_stage14_scale_fixture.json`

## 1. Frozen Proxy Fixture

The Stage 14 rerun uses a frozen production-scale proxy fixture with:

1. `11` distinct source states
2. `22` observed `source -> target` pairs
3. `220` total observations
4. the same Stage 13 effective-outcome precedence:
   - `was_helpful`
   - else `user_satisfaction >= 4`
   - else raw `success`

No threshold changed. No fixture row changed after the artifact was frozen.

## 2. Scorecard

| Dimension | Value | Threshold | Verdict | Notes |
| --- | --- | --- | --- | --- |
| information_density (`ID1`) | `1.00` (`22 / 22`) | `>= 0.70` | `wire-ready` | all observed pairs are supported |
| stability (`ST1`) | `1.00` (`max drift = 0.00`) | `>= 0.95` | `wire-ready` | persistent round-trip remains exact |
| discriminative_power (`DP1`) | `1.00` (`11 / 11`) | `>= 0.60` | `wire-ready` | all source states pick the helpful top-1 route |
| safety_margin (`SM1`) | `1.00` (`1 - 0 / 11`) | `>= 0.85` | `wire-ready` | no high-confidence decision is falsely confident |

## 3. Representative Top-1 Decisions

| Source state | Top-1 pick | Probability | Effective user outcome |
| --- | --- | --- | --- |
| `state_plan` | `generate_tasks_for_plan` | `0.923` | `true` |
| `state_task` | `breakdown_task` | `0.923` | `true` |
| `state_focus` | `get_task_summary` | `0.923` | `true` |
| `state_growth` | `get_situation_brief` | `0.923` | `true` |
| `state_query` | `query_plan_tasks` | `0.923` | `true` |

The remaining six source states follow the same pattern on the frozen fixture.

## 4. Interpretation

Stage 14 answered the fixture-scale concern from Stage 13 in the narrowest allowed way:

1. the same SQAM method remains green after the proxy fixture is enlarged past the Stage 14 floor
2. the Stage 13 pass was therefore not just a `3`-state / `22`-observation accident
3. Path A survives the scale gate

This rerun still does **not** authorize wire-on by itself. Stage 14 must still respect the source-state compression audit and zero-impact shadow boundary.
