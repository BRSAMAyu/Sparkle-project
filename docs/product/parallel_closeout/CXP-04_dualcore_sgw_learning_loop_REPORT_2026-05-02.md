# CXP-04 Report — DualCore And SGW Learning Loop

## Mission

Make DualCore routing less one-way: a stance decision now carries trace ids into route history/outcome recording, explicit Aurora corrections can mark that route as failed, SGW receives the feedback, and recent route outcomes influence the next DualCore decision.

## What Changed

- Added `recent_route_outcomes` to `DualCoreRoutingInput` and wired `RoutingEngineMixin` to read the user's latest route history before deciding.
- Added route-outcome scoring in `DualCoreRouter`:
  - repeated failed `execution_first` outcomes raise `route_outcome_failure`, block automatic execution-first routing, and move the next route toward support/confirmation;
  - over-scaffolded patterns can shorten the next response and reduce repeated check-ins;
  - stable execution success reduces unnecessary scaffolding.
- Preserved route continuity by passing `route_history_decision_id` into `RoutingOutcomeRecorder` and passive signal context.
- Extended Aurora correction payloads across backend API and mobile model with:
  - `route_history_decision_id`
  - `routing_outcome_signal_id`
  - `routing_trace_id`
- Updated `CorrectionFeedbackProcessor` so disconfirming/freeform corrections with route ids:
  - backfill `RouteHistoryService.record_user_correction`;
  - mark the routing passive signal as explicitly failed;
  - apply SGW feedback via `ScaffoldingFSM.apply_feedback`;
  - expose `routing_feedback_recorded` in the correction result/effect.

## User-Visible Improvement

When Sparkle pushes too directly and the user corrects it, that correction is no longer just telemetry. The related route decision becomes a failed outcome, SGW increases support, and the next similar turn gets a humbler route: smaller next step, less pressure, and a short confirmation before pushing ahead.

## Causal Trace

1. Signal: user has a clear task, so DualCore chooses `execution_first` and records `routing_trace_id`, `route_history_decision_id`, and `routing_outcome_signal_id`.
2. Outcome: user taps a disconfirming correction such as `strategy_too_aggressive`.
3. Backfill: correction processing marks the route history row as `user_correction`, marks the passive routing signal failed, and applies SGW feedback `explicit_user_correction_after_routing`.
4. Future decision: the next DualCore input reads recent route history; two failed `execution_first` outcomes set `route_outcome_failure`, making the next decision `cognitive_first` instead of another direct push.

## Verification

- `cd backend && pytest tests/unit/test_aurora_closed_loop.py tests/unit/test_route_history_service.py tests/unit/test_dual_core_router_real_engine.py -q`
  - `32 passed`
- `cd mobile && flutter analyze lib/core/models/aurora_correction_payload.dart`
  - `No issues found`

## Notes

- The route ids are optional, so old clients keep working.
- The new correction bridge only backfills route outcomes when a surface provides route ids; surfacing those ids consistently in every chat correction UI remains a useful follow-up for final integration.
