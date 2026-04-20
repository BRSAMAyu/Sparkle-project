# SPARKLE Aurora Stage 15 CL1 Narrow Wire Report (2026-04-20)

> **Status**: landed bounded Stage 15 wire-on path
> **Authority**:
> - [SPARKLE_AURORA_STAGE15_CL1_CLAIM_ARTIFACT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_CL1_CLAIM_ARTIFACT_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE15_CL1_DISCLOSE_ARTIFACT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_CL1_DISCLOSE_ARTIFACT_2026-04-20.md)
> - [SPARKLE_AURORA_STAGE15_CL1_WIRE_NARROW_ARTIFACT_2026-04-20.md](/Users/brsama/code/GitHub/Sparkle-project/docs/product/SPARKLE_AURORA_STAGE15_CL1_WIRE_NARROW_ARTIFACT_2026-04-20.md)

## 1. Landed Read Path

Stage 15 wires exactly one bounded user-visible path:

1. backend `PredictiveService` enriches dashboard `next_intent_forecast`
2. the enrichment is emitted only as `within_category_preference`
3. mobile parses that payload into `PredictionInsightData.withinCategoryPreference`
4. `PredictedIntentCard` renders one bounded hint plus the required caveat

No other front-door surface consumes the payload.

## 2. Feature Flag

The bounded hint is gated by:

1. `SPARKLE_CL1_WITHIN_CATEGORY_WIRE_ON`

Default posture remains:

1. off unless explicitly enabled

## 3. Bounded Payload Shape

The user-visible path consumes only this compact contract:

```json
{
  "claim_scope": "within_category_only",
  "surface": "dashboard.predicted_intent_card",
  "request_category": "task",
  "preferred_tool": "create_task",
  "confidence": 0.79,
  "support_count": 6,
  "shadow_records": 7,
  "divergence_rate": 0.14
}
```

Hard interpretation:

1. no workflow-step payload is exposed
2. no prompt-facing or profile-facing payload is exposed
3. the mobile layer composes the caveated wording locally from machine fields

## 4. User-Facing Contract

The visible Stage 15 block says, in substance:

1. within one coarse request category, recent results favor one tool path
2. this does not imply workflow understanding

The visible block does **not** say:

1. Sparkle understands the user's whole workflow
2. Sparkle remembers cross-step intent
3. Sparkle has learned a durable broad personalization profile from CL1

## 5. Proof Points

- backend targeted Stage 15 sweep: `6 passed`
- mobile targeted Stage 15 sweep: `4 passed`

Covered behaviors:

1. dashboard predictions may carry the bounded hint
2. chat-surface predictions may not carry it
3. mobile parses the payload correctly
4. the hint and caveat render together and disappear together
