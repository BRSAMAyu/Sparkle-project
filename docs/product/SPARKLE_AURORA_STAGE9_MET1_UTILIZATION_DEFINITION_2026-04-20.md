# SPARKLE Aurora Stage 9 MET1 Utilization Definition (2026-04-20)

> **Status**: pre-implementation artifact for `WS-MET1`
> **Purpose**: freeze the metric contract for prompt / inference utilization before Stage 9 collection code lands.

## 1. Why This Exists

Stage 8 proved more of Sparkle's loop is closed and user-visible, but the system still lacks a stable way to answer:

1. how much canonical user/context data actually reaches the prompt
2. how much of that data is actually reflected in the final answer / decision path

This artifact defines the minimum metric contract so later stages can compare progress without changing definitions midstream.

## 2. Metric Families

Stage 9 defines two utilization families:

1. `prompt_utilization`
2. `inference_utilization`

These are directional product-quality metrics, not billing metrics and not raw token-usage metrics.

## 3. Prompt Utilization

### Definition

`prompt_utilization` measures how much of the canonical high-value context selected for a run is actually rendered into the prompt / control surface seen by the model.

### Numerator

The count of selected canonical signal blocks that are rendered into the final prompt bundle or equivalent structured control payload.

Examples:

1. selected `SituationBrief` sections that appear in the rendered prompt
2. selected canonical profile / transparency claims that are rendered
3. selected planning / grounding constraints that are rendered

### Denominator

The count of canonical signal blocks selected for inclusion at the decision layer before prompt rendering.

Examples:

1. selected `SituationBrief` sections
2. selected user/profile/context signal groups
3. required grounding / planning blocks

### Output

Stage 9 records:

1. `selected_signal_block_count`
2. `rendered_signal_block_count`
3. `prompt_utilization_ratio = rendered / selected`

### Degradation behavior

If the system cannot determine selected blocks for a run, it records:

1. `metric_status = unknown`
2. `prompt_utilization_ratio = null`
3. `degradation_reason`

It must not silently emit `0.0`.

## 4. Inference Utilization

### Definition

`inference_utilization` measures how much of the canonical evidence and profile/context signals are reflected in the final answer or decision output in a traceable way.

### Numerator

The count of final-answer or decision-output segments that can be traced back to canonical evidence classes or selected signal families.

Examples:

1. answer cites or paraphrases user-material evidence
2. answer explicitly references current constraint / profile claim / uncertainty marker
3. decision output names the grounding basis, evidence class, or selected signal family

### Denominator

The count of eligible canonical signal families that should have influenced the answer / decision for that run.

Examples:

1. mandatory grounding signals
2. active profile claims used in the turn
3. active uncertainty or calibration markers relevant to the turn

### Output

Stage 9 records:

1. `eligible_signal_family_count`
2. `traceable_signal_family_count`
3. `inference_utilization_ratio = traceable / eligible`

### Degradation behavior

If traceability is unavailable for a run, it records:

1. `metric_status = unknown`
2. `inference_utilization_ratio = null`
3. `degradation_reason`

It must not silently emit `0.0`.

## 5. Sampling Window

Stage 9 uses:

1. per-run raw events
2. daily aggregates
3. rolling 7-day aggregates

Stage 9 does not require weekly / monthly product dashboards yet.

## 6. Aggregation Contract

For each aggregation window, Stage 9 records:

1. run count
2. known-value count
3. unknown-value count
4. average utilization ratio over known values
5. median utilization ratio over known values

Unknown runs remain visible as unknown and are excluded from ratio averaging.

## 7. Collection Boundaries

### Backend collection

Stage 9 may collect from existing seams including:

1. `SituationBrief` / prompt section selection
2. prompt rendering / response builder output
3. token-usage recording paths
4. evaluator-side traceability metadata

### Client collection

Stage 9 may collect companion events from existing client observability only when needed to correlate visible user-front-door behavior with backend runs.

### Forbidden shortcuts

Stage 9 must not:

1. infer utilization from raw token counts alone
2. use billing usage as a proxy for prompt / inference utilization
3. rewrite product logic just to improve the metric

## 8. Initial Storage Shape

Stage 9 collection may start with lightweight structured observability events containing:

1. `request_id`
2. `session_id`
3. `chat_mode`
4. `metric_family`
5. numerator
6. denominator
7. ratio
8. status
9. `degradation_reason`

This stage does not require a final analytics schema redesign.

## 9. Acceptance Criteria

`WS-MET1` is accepted only if:

1. both metric families have frozen numerator / denominator definitions
2. degradation behavior is explicit
3. Stage 9 collection code records the metrics on real runs
4. the handoff can show at least one concrete run with populated utilization records
