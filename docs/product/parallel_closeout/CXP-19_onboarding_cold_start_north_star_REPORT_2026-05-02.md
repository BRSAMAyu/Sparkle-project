# CXP-19 Report — Onboarding, Cold Start, And North Star Journey

## Goal
Make the first session produce real product value faster: a correctable goal profile, a usable cold-start context for first planning, an Aurora baseline signal, and measurable first-value milestones.

## Work Completed
- Cold-start modeling now preserves the user's actual goal type instead of forcing every onboarding context to `exam`.
- Onboarding baseline labels are normalized into planning-ready, user-facing values like `完全没学过`, `上过课但没复习`, and `已经学过一部分`.
- Skipping modeling now still persists a safe, correctable default `cold_start_context` with `safe_default`, `skipped`, and `assumptions_correctable` metadata.
- The modeling-complete bridge records the first plan request as a North Star milestone before auto-generating the first plan.
- Profile onboarding records first goal profile and first Aurora baseline milestones.
- First task completion records the first task milestone once per user.
- North Star trend payloads now expose first-value counts: goal profile, Aurora baseline, first plan request, and first task completion.
- Mobile onboarding routes now use the cold-start transition for persona onboarding and modeling chat, and the onboarding preview card uses existing localized copy.

## User Experience Before / After
Before: a skipped or partial onboarding could leave planning without durable cold-start context, non-exam goals could be misclassified as exam goals, and first-value progress was mostly invisible to North Star metrics.

After: a new user can state or skip a goal path and still land in a recoverable flow. Sparkle keeps assumptions explicitly correctable, preserves whether the user is pursuing an exam/project/skill, and can measure whether the user reached profile -> Aurora baseline -> plan request -> first task completion.

## Cross-System Links
- Backend onboarding API: `backend/app/api/v1/profile_transparency.py`
- Planning/modeling bridge: `backend/app/orchestration/planning_workflow.py`
- Task completion loop: `backend/app/services/task_service.py`
- North Star metrics: `backend/app/services/north_star_metrics_service.py`, `backend/app/schemas/north_star_metrics.py`
- Mobile onboarding routes/copy: `mobile/lib/features/user/user_routes.dart`, `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart`

## Verification
- `cd backend && pytest tests/services/test_north_star_metrics_service.py tests/orchestration/test_planning_workflow_cold_start.py` — 5 passed.
- `cd backend && ruff check app/orchestration/planning_workflow.py app/services/north_star_metrics_service.py app/schemas/north_star_metrics.py app/api/v1/profile_transparency.py app/services/task_service.py tests/services/test_north_star_metrics_service.py tests/orchestration/test_planning_workflow_cold_start.py` — passed.
- `cd mobile && dart format --output=none --set-exit-if-changed lib/features/user/user_routes.dart lib/features/user/presentation/screens/persona_onboarding_screen.dart` — passed.
- `cd mobile && dart analyze lib/features/user/user_routes.dart lib/features/user/presentation/screens/persona_onboarding_screen.dart` — exit 0 with existing info-level lints in `persona_onboarding_screen.dart`.
- `cd mobile && flutter test test/widget/cold_start_route_transition_test.dart test/widget/modeling_chat_screen_test.dart` — blocked before these tests by unrelated compile errors in visual-elements/openclaw files.

## Remaining Risks
- Mobile full-test verification needs the CXP-17/CXP-18 visual-elements and OpenClaw compile blockers fixed first.
- The first plan request milestone is recorded when the modeling bridge auto-enters planning; if a future flow creates a first plan outside that bridge, it should call the same North Star milestone service.
- The shared worktree contains many unrelated uncommitted changes from other tasks, so final integration should stage CXP-19 hunks carefully.

## Commit
Branch: `codex/CXP-19-cold-start-journey`

Commit hash: not created in this pass because the repository already contained extensive unrelated uncommitted work from other CXP branches.
