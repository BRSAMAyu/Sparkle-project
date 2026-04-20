# SPARKLE Aurora Stage 15 CL1 Observe Artifact (2026-04-20)

> **Stage**: 15
> **Workstream**: `WS-CL1-OBSERVE`
> **Authority**: [SPARKLE_AURORA_STAGE14_CL1_SHADOW_REPORT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE14_CL1_SHADOW_REPORT_2026-04-20.md)
> **Status**: frozen before Stage 15 code

## 1. Observation Window

Stage 15 uses the existing Stage 14 shadow pipe only.

The bounded inspection window is:

1. latest 20 shadow records for the same user

## 2. Guard Thresholds

The Stage 15 surface may stay active only if:

1. at least 5 shadow records exist
2. divergence rate is `<= 0.35`

If either condition fails:

1. Stage 15 auto-disables the bounded CL1 hint
2. baseline prediction remains visible

## 3. Internal Query Surface

Stage 15 may inspect only:

1. recent shadow records
2. divergence summary

## 4. Hard Boundary

Shadow records remain:

1. outside prompt assembly
2. outside push / notification copy
3. outside evidence / profile / front-door payloads except for the boolean-style rollout guard derived from divergence
