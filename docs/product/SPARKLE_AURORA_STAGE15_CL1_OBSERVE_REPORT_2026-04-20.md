# SPARKLE Aurora Stage 15 CL1 Observe Report (2026-04-20)

> **Status**: landed bounded observation and rollback guard
> **Authority**:
> - [SPARKLE_AURORA_STAGE14_CL1_SHADOW_REPORT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE14_CL1_SHADOW_REPORT_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE15_CL1_OBSERVE_ARTIFACT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_CL1_OBSERVE_ARTIFACT_2026-04-20.md)

## 1. Guard Source

Stage 15 reuses the Stage 14 shadow recorder only.

It reads:

1. latest `20` shadow records
2. summary fields `total_records` and `divergence_rate`

It does not read or emit:

1. prompt payloads
2. evidence payloads
3. profile payloads
4. notification payloads

## 2. Activation Threshold

The bounded hint stays active only when:

1. at least `5` shadow records exist
2. divergence rate is `<= 0.35`

If either condition fails:

1. backend emits no `within_category_preference`
2. mobile shows no Stage 15 CL1 hint
3. baseline dashboard prediction stays intact

## 3. Category Stability Threshold

Even with a green shadow guard, the bounded hint still requires:

1. at least `3` recent observations in the same category
2. at least `2` distinct tools in that category
3. top same-category probability `>= 0.65`
4. margin over runner-up `>= 0.10`

If any of these fail:

1. Stage 15 emits no bounded hint

## 4. Rollback Semantics

Stage 15 rollback is intentionally boring:

1. unset the feature flag
2. or allow the guard to auto-disable by divergence
3. the card falls back to the pre-Stage-15 prediction shape

No schema migration or cleanup path is required.

## 5. Verification

- backend observation/guard sweep: `6 passed`

Representative covered cases:

1. stable same-category signal emits a bounded payload
2. high shadow divergence suppresses the payload
3. dashboard-only forecasts may attach the payload
4. chat-input forecasts may not attach the payload
