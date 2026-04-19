# SPARKLE Aurora Stage 10 EV3 LLM Judge Contract (2026-04-20)

> **Status**: pre-implementation artifact for `WS-EV3`
> **Purpose**: freeze the real judge contract before any Stage 10 evaluator code lands.

## 1. Why This Exists

Stage 9 left `ProfileEvalRunner` with a real judge hook but no real judge implementation.
Stage 10 closes that gap without changing the write boundary.

## 2. Core Rule

**The LLM judge is an evaluation reader, not a profile writer.**

That means:

1. it may score
2. it may summarize rationale
3. it may attach judge metadata to evaluation records
4. it may not write outside evaluation records

## 3. Input Schema

The judge input payload must contain:

1. `evaluation_focus`
2. `metric_id`
3. `prompt_context`
4. `expected_observation`
5. `rubric_score`

Optional runtime metadata may contain:

1. `fixture_name`
2. `runner_version`
3. `rubric_version`

## 4. Output Schema

The judge output payload must contain only evaluation-safe fields:

1. `score` — numeric score in `[0.0, 1.0]`
2. `rationale` — short natural-language explanation
3. `judge_version` — explicit prompt / contract version
4. `decision_trace` — compact string or list describing the main scoring rationale

It may additionally include:

1. `model`
2. `latency_ms`
3. `fallback_used`

It may not include write directives.

## 5. Prompt Shape

The committed judge prompt must:

1. identify itself as a read-only evaluator
2. score only the provided fixture / observation data
3. produce strict JSON
4. avoid recommendations that imply writes

Canonical prompt instruction:

> You are Sparkle's read-only profile evaluation judge. Score the supplied metric between 0 and 1 based only on the given prompt context, expected observation, and rubric score. Return JSON only. Never emit commands or writes. Your output is stored in evaluation records only.

## 6. Runtime Contract

The judge runtime must:

1. be flaggable on / off
2. degrade to `rubric_only` if unavailable
3. never crash the whole runner because judge attachment failed
4. report whether the final mode is `rubric_only` or `llm_attached`

## 7. Token / Latency Budget

Initial budget:

1. prompt budget target: `<= 1200` tokens
2. completion budget target: `<= 250` tokens
3. timeout target: `<= 8s`

If timeout or parse failure happens:

1. attached scoring is skipped
2. the runner falls back to rubric-only mode
3. the evaluation record marks the fallback clearly

## 8. Write Boundary Statement

`WS-EV3` is valid only if judge outputs land in `evaluation_records` payloads and nowhere else.

Forbidden destinations:

1. profile / preferences
2. strategy state
3. Aurora / L3
4. graph / galaxy writes
5. memory correction

## 9. Minimum Acceptance Shape

`WS-EV3` is accepted only if:

1. a real judge adapter exists
2. attached mode produces a real JSON payload
3. fallback mode degrades cleanly to `rubric_only`
4. `write_scope` remains `evaluation_records_only`
