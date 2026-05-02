# CXP-16 Report — Achievements, Photon, Shop, And Rewards

## Goal
Make reward moments reflect real growth loops, stay idempotent under retries, and connect achievement unlocks to Photon/title rewards plus shareable user-facing feedback.

## Work Completed
- Added first-class achievement event paths for community sharing and Aurora calibration completion.
- Wired community resource sharing, achievement share-card generation, and Aurora core-session completion into the achievement event consumer.
- Added idempotency reservations for share IDs and Aurora session IDs so retrying a share/calibration event does not duplicate Photon grants.
- Added initial seed achievements:
  - `community_first_share` grants 30 Photons and the `spark_sharer` title.
  - `aurora_first_calibration` grants 80 Photons and the `aurora_calibrated` title.
- Extended focused achievement tests to prove community share and Aurora calibration unlock once and record exactly one Photon transaction.

## User Experience Before / After
Before: task completion, streak, and knowledge mastery could unlock achievements, but sharing and Aurora calibration were not explicit achievement paths.

After: a user can now feel recognized for sharing useful work with others and for completing a meaningful Aurora calibration, with restrained rewards that explain the behavior and update Photon/title state consistently.

## Cross-System Links
- Backend achievement engine: new trigger codes, progress evaluation, and retry dedupe.
- Backend event consumer: consumes `community.resource_shared`, `achievement.shared`, and `aurora.calibration.completed`.
- Community bridge: publishes share events for shared resources.
- Achievement share cards: publish share events after share-count persistence.
- Aurora core session: publishes calibration-completed events after session completion.
- Seed data: adds community and Aurora reward definitions.

## Verification
- `cd backend && pytest tests/unit/test_achievement_engine_phase3.py::test_community_share_unlocks_once_and_grants_reward tests/unit/test_achievement_engine_phase3.py::test_aurora_calibration_completion_unlocks_once -q`
  - Result: 2 passed.
- `cd backend && pytest tests/unit/test_achievement_engine_phase3.py tests/unit/test_achievement_event_consumer.py tests/services/test_achievement_reward_observability.py -q`
  - Result: 24 passed.
- `cd backend && pytest tests/unit/test_achievement_system_alignment.py -q`
  - Result: 11 passed.
- Isolated worktree rerun with test-only `SECRET_KEY` and local `time_utils.py` helper present:
  - `cd backend && SECRET_KEY=test-secret-key-for-cxp16-tests-123456 pytest tests/unit/test_achievement_engine_phase3.py tests/unit/test_achievement_event_consumer.py tests/services/test_achievement_reward_observability.py tests/unit/test_achievement_system_alignment.py -q`
  - Result: 35 passed.

## Remaining Risks
- Community share achievements currently count persisted `SharedResource` rows and achievement share-card counts. If future share surfaces bypass both systems, they should publish `community.resource_shared` or `achievement.shared`.
- Aurora calibration publishing is best-effort; failures are logged and do not block session completion.
- Mobile copy already receives existing achievement unlock payloads, but a dedicated UI polish pass could add category-specific copy for the new community/Aurora seeds.

## Commit
Branch: `codex/CXP-16-achievements-photon-shop-rewards`
Commit: pending final task commit
