# SPARKLE Aurora Stage 14 WS-CL1-SHADOW Report (2026-04-20)

> **Workstream**: `WS-CL1-SHADOW`
> **Purpose**: record the landed zero-user-impact shadow pipe for bounded learner-vs-fallback observation.

## 1. Landed Runtime Shape

Stage 14 lands a narrow shadow recorder:

1. feature-flagged by `SPARKLE_CL1_SHADOW_MODE`
2. Redis-backed only
3. stored under the L2-side namespace:
   - `inference_cache:tool_preference_shadow:{user_id}`
4. TTL-bounded
5. queryable through internal recorder helpers only

## 2. Recorder Schema

Each record includes:

1. `timestamp`
2. `user_id`
3. `source_state`
4. `fallback_choice`
5. `learner_choice`
6. `eventual_outcome`
7. `diverged`
8. `fallback_probability`
9. `learner_probability`

## 3. Zero User-Visible Impact Proof

Stage 14 verifies the key behavior with targeted tests:

1. when shadow mode is on, `fallback_choice` still becomes `router_decision`
2. `learner_choice` is recorded separately in shadow storage
3. divergence summary is queryable
4. no prompt, push, evidence, or user-facing route consumes the shadow record

Representative verified shadow record:

```json
{
  "source_state": "state_plan",
  "fallback_choice": "fallback_tool",
  "learner_choice": "learner_tool",
  "diverged": true
}
```

## 4. Interpretation

Stage 14 now has the pipe it needed for pre-wire observation:

1. learner and fallback can be compared without changing the user-visible route
2. divergence can be inspected later by Stage 15
3. Stage 14 still does **not** define a production observation window or wire-on policy
