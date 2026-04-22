# SPARKLE AURORA Stage 34 Handoff

Date: 2026-04-22
Stage: 34
Status: implementation handoff

## Delivered

- `aurora_stage34` has been formalized as a three-mode control surface with child feature modes for `error_bridge`, `capsule`, and `journey_subscribers`.
- `episodic_memories` and `active_goals` are now attached at `UserContext` top level and mirrored into the context assembly path used by prompt normalization.
- `CapsuleFavorite` preferences can now be compiled into `stable_preferences.capsule`; `shadow` mode generates the structure without exposing it downstream.
- `user.registered` and `plan.created` now have concrete downstream subscribers for onboarding, profile bootstrap, galaxy seeding, and first-plan achievement progression.
- Rule AS guard coverage now includes `context_builder` attach/build methods and `user_insight_compiler.to_inline_snapshot`.
- Rule AT is added to detect orphan services/consumers unless they are deprecated or explicitly exempted.

## Feature Flags

- Master: `AURORA_STAGE34_MODE` default `off`
- Child: `AURORA_STAGE34_ERROR_BRIDGE_MODE` default `shadow`
- Child: `AURORA_STAGE34_CAPSULE_MODE` default `shadow`
- Child: `AURORA_STAGE34_JOURNEY_SUBSCRIBERS_ENABLED` default `live`

## Stage 35 Notes

- Mobile can now parse `episodic_memories`, `active_goals`, and `stable_preferences.capsule` without backend schema expansion.
- Stage 34 archived orphaned services under `/Users/brsama/code/GitHub/Sparkle-project-stage34-head/backend/app/_deprecated/stage34`; recovery is possible by moving files back with history preserved.
- Metacognition to Router remains partial and is intentionally untouched here.
- Any Stage 35 rollout should reuse the three-mode kill-switch pattern rather than introducing boolean fallbacks.

