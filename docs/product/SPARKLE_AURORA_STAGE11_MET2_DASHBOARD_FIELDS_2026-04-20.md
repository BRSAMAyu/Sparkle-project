# SPARKLE Aurora Stage 11 MET2 Dashboard Fields (2026-04-20)

> **Purpose**: freeze which MET1 carrier fields must become operator-visible during `WS-MET2`.

## Dashboard Additions

### Per chat-mode item

1. `avg_prompt_utilization_percent`
2. `avg_inference_utilization_percent`
3. `prompt_utilization_known_count`
4. `prompt_utilization_unknown_count`
5. `prompt_utilization_not_applicable_count`
6. `inference_utilization_known_count`
7. `inference_utilization_unknown_count`
8. `inference_utilization_not_applicable_count`

### Overview / export rollup

1. `avg_prompt_utilization_percent`
2. `avg_inference_utilization_percent`
3. `prompt_utilization_known_count`
4. `inference_utilization_known_count`

## Rendering Requirements

1. user-facing summary may compress these into short trust labels
2. developer-facing view must show raw percentages plus known / unknown counts
3. `unknown` and `not_applicable` must remain distinct
