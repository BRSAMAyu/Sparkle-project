# SPARKLE Aurora Stage 15 CL1 Claim Artifact (2026-04-20)

> **Stage**: 15
> **Workstream**: `WS-CL1-CLAIM`
> **Authority**: [SPARKLE_AURORA_STAGE15_DISPATCH_PLAN_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_DISPATCH_PLAN_2026-04-20.md)
> **Status**: frozen before Stage 15 code

## 1. Exact Stage 15 Claim

Stage 15 is allowed to make exactly one user-visible continuous-learning claim:

> **Within one coarse request category, Sparkle may surface one recently stronger tool path if the signal is stable enough and the observation guard is still green.**

Chinese working copy:

> **只在同一类请求内部，如果近期信号足够稳定且观察守门仍为绿色，Sparkle 才会提示一个更常对你有效的工具路径。**

## 2. What Stage 15 Does Not Claim

Stage 15 explicitly does **not** claim:

1. Sparkle understands the user's full workflow
2. Sparkle understands cross-step intent transitions or recovery state
3. Sparkle has learned a durable user preference outside one coarse category

## 3. One Bounded Surface

The claim may appear only in:

1. dashboard `PredictedIntentCard`

Hard interpretation:

1. no chat-system prompt language may rely on this claim
2. no push / notification / evidence / profile surface may reuse this claim
3. no other dashboard card may restate this claim without a new dispatch

## 4. Fallback Wording

If no stable within-category preference exists, Stage 15 must show nothing.

Hard interpretation:

1. no placeholder "learning in progress" copy
2. no weakly supported recommendation copy
3. the baseline dashboard prediction remains the only visible guidance

## 5. Narrowness Test

Any copy is invalid if a reasonable user could infer:

1. workflow understanding
2. cross-category personalization
3. long-term durable preference modeling
