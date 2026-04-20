# SPARKLE Aurora Stage 15 CL1 Wire-Narrow Artifact (2026-04-20)

> **Stage**: 15
> **Workstream**: `WS-CL1-WIRE-NARROW`
> **Authority**: [SPARKLE_AURORA_STAGE15_CL1_CLAIM_ARTIFACT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_CL1_CLAIM_ARTIFACT_2026-04-20.md)
> **Status**: frozen before Stage 15 code

## 1. Exact Read Path

The only Stage 15 bounded wire-on path is:

1. backend dashboard payload emits one `within_category_preference` object
2. mobile dashboard parses it
3. `PredictedIntentCard` renders one bounded CL1 hint plus the required caveat

## 2. Feature Flag

Stage 15 uses:

1. `SPARKLE_CL1_WITHIN_CATEGORY_WIRE_ON`

Default state:

1. off

## 3. Rollback Surface

Stage 15 rollback means:

1. backend stops emitting `within_category_preference`
2. mobile hides the hint and caveat
3. baseline prediction card remains intact

## 4. Fallback Rule

If the learner has no stable within-category signal:

1. do not emit a degraded hint
2. do not emit a placeholder caveat
3. leave the baseline prediction surface unchanged

## 5. Rule U Proof Points

Stage 15 proof must show:

1. the bounded hint appears only when the payload is present
2. the caveat appears with it
3. both disappear when the payload is absent or disabled
