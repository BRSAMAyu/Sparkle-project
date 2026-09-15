# Phase A User Insight Contract

This document freezes the stable runtime contract for the Phase A User Insight Engine.

Compatibility rule:
- Do not rename, remove, or repurpose these fields without updating this document and the Phase A durability pack.

## Stable Interfaces

### `CompiledInsightState`
- Location: `backend/app/orchestration/schemas.py`
- Role: internal Phase A runtime schema compiled from profile truth, gaps, contradictions, and readiness.
- Stability:
  - `version` remains `1.0` in the durability pass.
  - `planning_readiness` remains a nested readiness payload.
  - `recommended_clarification` remains an ordered list.

### `planning_readiness`
- Location:
  - `CompiledInsightState.planning_readiness`
  - `SituationBrief.insight_state.planning_readiness`
- Role: canonical readiness payload for planning quality.
- Required keys:
  - `readiness_score`
  - `readiness_level`
  - `recommended_action`
  - `blocking_unknowns`
  - `blocking_contradictions`
  - `ask_before_plan`

### `planning_readiness_action`
- Location: `SituationBrief.decision_context.planning_readiness_action`
- Role: prompt/runtime-facing mirror of `planning_readiness.recommended_action`.
- Allowed values:
  - `ask`
  - `provisional`
  - `proceed`

### `phase_a_guardrail`
- Location: `SituationBrief.decision_context.phase_a_guardrail`
- Role: explicit runtime guardrail for planning turns.
- Allowed values:
  - `ask_before_plan`
  - `provisional_plan_with_assumptions`
  - absent

### `strategic_clarification_questions`
- Location: `SituationBrief.decision_context.strategic_clarification_questions`
- Role: ordered list of Phase A clarification questions for prompts and runtime observability.
- Stability:
  - remains ordered
  - hard-stop runtime uses only index `0`
  - prompt/runtime may retain up to 3 items

### `ask_before_plan`
- Location:
  - `planning_readiness.ask_before_plan`
  - `SituationBrief.insight_state.ask_before_plan`
- Role: boolean canonical mirror for whether Phase A requires clarification before planning.
- Stability:
  - remains boolean
  - remains equivalent to `planning_readiness_action == "ask"`

## Internal vs Prompt/Runtime Fields

Internal schema fields:
- `CompiledInsightState`
- `planning_readiness`
- `ask_before_plan`

Prompt/runtime metadata fields:
- `planning_readiness_action`
- `phase_a_guardrail`
- `strategic_clarification_questions`

## Durability Notes

- Planning-like turn detection must come from the shared planning-intent helper.
- The hard runtime guard may emit exactly one clarification question before planning.
- Phase A should only broaden heuristics when durability benchmarks fail or later evidence shows repeated misses.
