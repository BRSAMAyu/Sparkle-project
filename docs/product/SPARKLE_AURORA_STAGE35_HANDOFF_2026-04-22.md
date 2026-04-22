# SPARKLE AURORA Stage 35 Handoff

Date: 2026-04-22
Stage: 35
Status: implementation handoff

## Delivered

- Mobile now deserializes and renders `working_memory_snapshot`, `achievement_summary`, `active_skills_summary`, `engagement_state`, and `foresight_hint` from `UserStateV1 v1.13` with explicit empty states instead of silent drops.
- Six `UserStateV1` fields are now explicitly marked `@BackendOnly` in Dart and mirrored in `/Users/brsama/code/GitHub/Sparkle-project-stage34-head/docs/aurora/stage35_backend_only_fields.md`, allowing Rule AU to distinguish intentional backend-only contract fields from true mobile black holes.
- Rule AU (`Mobile Parity`) is now documented, guarded, and added to `/Users/brsama/code/GitHub/Sparkle-project-stage34-head/scripts/rule_guard_manifest.tsv`; current measured black-hole rate is `0.000%`.
- `DualCoreRoutingInput` now accepts `metacognition_hint`, and the router computes a stage-35 bias delta in `shadow` mode without changing live decisions by default.
- `metacognition_profile` remains prompt-visible and now also influences router shadow computation through a bounded summary path; raw dashboard/process scaffolding data remains blocked from routing.
- `scripts/journey_smoke.sh` now reproduces a 7-hop main journey plus a 3-hop error journey with hop-localized failures, DB assertions, event assertions, and WebSocket/system-update format checks.
- CI now runs the Stage 35 journey smoke job on every PR after guards and backend tests complete.

## Feature Flags

- Backend master: `AURORA_STAGE35_MODE` default `shadow`
- Backend child: `AURORA_STAGE35_METACOG_ROUTER_MODE` default `shadow`
- Mobile surface gate: `mobile.stage35_cards_enabled` default `true`
  Current mobile implementation consumes this through `AppFeatureFlags.enableStage35ProfileCards`, so cards can be hidden with a launch/build-time override while preserving the Stage 35 UI composition.

## Verification Snapshot

- Rule AU guard: pass, black-hole rate `0.000%`
- Metacognition user-scope guard: pass
- Stage 35 drill: `off -> shadow -> live -> shadow -> off` pass
- Stage 35 backend/router suite: pass
- Journey smoke:
  Main journey `signup -> goal -> plan -> first-task -> complete -> feedback -> replan` pass
  Error journey `error-created -> replan-evaluated -> replan-triggered` pass

## Stage 36 Notes

- `AURORA_STAGE35_METACOG_ROUTER_MODE` remains `shadow` by default; no live promotion should happen until the required shadow soak and decision-distribution review complete.
- Mobile parity now has a stable baseline; any new `UserStateV1` field added in later stages must either render, declare as backend-only, or be documented before merge.
- `scripts/journey_smoke.sh` is fast enough for PR usage and can be expanded in Stage 36, but it should remain blocking and must not move to `continue-on-error`.
- The mobile card kill path is now externally configurable via `mobile.stage35_cards_enabled`; if dedicated remote-config infrastructure is introduced later, it should write into the same gate rather than forking a new control surface.
