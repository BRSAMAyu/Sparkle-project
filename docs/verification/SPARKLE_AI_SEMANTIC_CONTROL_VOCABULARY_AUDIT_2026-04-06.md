# Sparkle AI Semantic Control Vocabulary Audit

Date: 2026-04-06  
Scope: AI-0 vocabulary audit for model-facing semantic control

## Audit Summary

Sparkle had three main raw-label leak seams before this pass:

1. Responder prompt sections surfaced decision and planning tags directly in [prompts.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/prompts.py).
2. Planner constraints surfaced planning tags as compact jargon in [lang_graph_planner.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/lang_graph_planner.py).
3. Situation brief prompt formatting re-exposed decision and planning tags from `decision_context` in [situation_brief.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py).

The governed vocabulary now has one canonical source in [ai_strategy_ontology.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/ai_strategy_ontology.py), one renderer in [ai_strategy_renderer.py](/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/ai_strategy_renderer.py), and one checked-in machine fixture in [semantic_control_vocabulary_inventory.json](/Users/brsama/code/GitHub/Sparkle-project/backend/tests/fixtures/semantic_control_vocabulary_inventory.json).

## High-Risk Leak Points

- `experience_mode`, `intervention_family`, `reversibility_level`: high risk because these were previously rendered as bare control words in the responder prompt.
- `plan_mode`, `plan_depth`, `pacing_profile`, `grounding_mode`, `fallback_policy`: high risk because they previously appeared in both responder and planner prompt surfaces as opaque planning jargon.
- Raw strategy-state prompt dumps: high risk because they exposed unguided field names like `push_vs_support` and `retrieval_emphasis` directly to the model.

## Governed Term Families

- Decision diagnosis: `primary_residual`, `loop_type`, `confidence_label`
- Decision policy: `experience_mode`, `intervention_family`, `reversibility_level`
- Planning readiness: `planning_readiness`, `planning_readiness_action`
- Planning strategy: `plan_mode`, `plan_depth`, `pacing_profile`, `grounding_mode`, `fallback_policy`
- Selected strategy state: `session_mode`, `explanation_style`, `retrieval_emphasis`, `intervention_intensity`, `support_posture`
- Body awareness: `primary_subsystem`

## Current Control Path

1. Runtime compilers still generate structured tags deterministically.
2. `SituationBriefBuilder` now renders one `semantic_control` block containing:
   - `selected_terms`
   - `rendered_doctrine_summary`
   - `response_contract`
   - `compliance_expectations`
3. Prompt surfaces and planner constraints now consume that semantic layer instead of exposing raw tags as the primary model instruction.
4. Validation and observability reuse the same semantic-control payload, with observed compliance sourced from the plan-quality path when available.

## Remaining Compatibility Notes

- Raw tags remain in runtime state and metadata for traceability.
- The deprecated `decision_context["planning_*"]` projections have been removed; downstream consumers should read `planning_strategy` directly.
- Future AI-facing tags must be added to the ontology and the inventory fixture together.
