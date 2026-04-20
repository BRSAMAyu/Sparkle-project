# SPARKLE Aurora Stage 11 EV4 Config Schema (2026-04-20)

> **Purpose**: freeze the evaluator judge engineering fields before `WS-EV4` code lands.

## Config Fields

| Field | Type | Default | Allowed range / values | Notes |
| --- | --- | --- | --- | --- |
| `judge.weight` | `float` | `0.3` | `[0.1, 0.9]` | judge share in final weighted score |
| `rubric.weight` | `float` | `0.7` | computed as `1.0 - judge.weight` | may not be configured independently out of sync |
| `judge.timeout_ms` | `int` | `8000` | `1000 - 15000` | timeout for live judge call |
| `judge.budget_tokens` | `int` | `1200` | `256 - 4096` | hard cap passed into judge request metadata |
| `judge.prompt_version` | `string` | `stage11.ev4.judge.v1` | committed artifact versions only | cannot be runtime-mutated outside code/config |
| `judge.enabled` | `bool` | `true` | `true / false` | false means attached path degrades cleanly |

## Precedence

1. explicit constructor / CLI arg
2. environment variable override
3. committed default

## Degrade Rules

1. disabled or unavailable judge must still emit an `llm_attachment` payload with fallback metadata
2. fallback must never write outside `evaluation_records_only`
3. invalid weights or budgets must clamp or reject before runtime scoring
