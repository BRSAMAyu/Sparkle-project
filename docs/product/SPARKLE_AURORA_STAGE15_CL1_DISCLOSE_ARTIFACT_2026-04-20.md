# SPARKLE Aurora Stage 15 CL1 Disclosure Artifact (2026-04-20)

> **Stage**: 15
> **Workstream**: `WS-CL1-DISCLOSE`
> **Authority**: [SPARKLE_AURORA_STAGE15_CL1_CLAIM_ARTIFACT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_CL1_CLAIM_ARTIFACT_2026-04-20.md)
> **Status**: frozen before Stage 15 code

## 1. Required Caveat Text

Chinese:

> **仅基于同类请求里的近期结果，不代表 Sparkle 理解了你的完整工作流。**

English:

> **Based only on recent results inside this request category. It does not mean Sparkle understands your whole workflow.**

## 2. Placement

The caveat must appear:

1. in the same `PredictedIntentCard` container as the Stage 15 CL1 hint
2. visually adjacent to the hint text

## 3. Hidden-State Rule

The caveat must be hidden when:

1. the Stage 15 feature flag is off
2. no stable within-category preference is available
3. the shadow observation guard auto-disables the surface

## 4. Forbidden Language

Stage 15 may not use wording equivalent to:

1. "Sparkle understands how you work"
2. "Sparkle remembers your workflow"
3. "Sparkle knows what you need next across contexts"
4. "Sparkle has learned your personal work style"
5. "Sparkle understands your recovery state / step sequence / full intent"

## 5. UI Safety Rule

If the caveat is removed, detached, or visually separated so that the user can read the hint without the caveat, Stage 15 is invalid.
