# CXP-08 Daily Task Bar And Execution Flow Report

Date: 2026-05-02
Branch: codex/CXP-08-daily-task-execution-flow

## Outcome

Daily execution now has a shared backend judgment for "what should I do next?" instead of independent due-date sorting in each surface. `/tasks/today`, `/tasks/recommended`, and the Home dashboard next-move payload can rank the same task using plan focus, deadline pressure, task priority, estimated duration, difficulty, energy cost, and current Aurora energy state.

The mobile task list also makes failed completion sync visible and recoverable. A task that completed locally but failed to sync now shows a warning strip with the sync error, plus retry and discard actions.

## User Journeys

### Daily Start

Before: recommended tasks were mostly sorted by deadline and priority. A high-priority but high-energy card could dominate the daily bar even when Aurora had detected a higher-friction state.

After: the daily selector downshifts toward doable tasks when Aurora is in L2/L3 or wake score is high, while still respecting due dates, active plan focus, and sprint/primary-plan pressure. The Home next-move card receives the same reason and selection signals.

### Task Completion

Before: the backend completion loop updated plan, Galaxy, achievements, and Aurora, but the mobile parser could drop top-level `next_actions` from the response.

After: mobile preserves completion next actions even when the API returns them beside the `data` envelope, so the feedback dialog can continue into review, expansion, practice, rest, or plan continuation.

### Task Too Hard

Existing quick action behavior was preserved: "too hard" calls the adaptive replanner and returns smaller subtasks. The daily selector now also treats high Aurora energy pressure as a signal to prefer lower-energy, lower-difficulty next steps.

### Skipped Task

Existing skip behavior was preserved: skipping abandons the task and removes it from active surfaces. The daily selector excludes abandoned tasks from today/recommended ranking.

### Offline/Error State

Before: failed completion sync was stored in `TaskSyncStatus.failed`, but the list card did not expose a direct recovery path.

After: failed cards show the error, retry completion with the stored actual minutes/note, or discard the optimistic local change by refreshing server state.

## Evidence

- `cd backend && python3 -m py_compile app/services/daily_task_selection_service.py app/api/v1/tasks.py app/services/growth_dashboard_service.py`
- `cd backend && pytest tests/api/test_task_quick_actions_api.py` -> 7 passed
- `cd mobile && flutter analyze lib/features/task/presentation/widgets/task_card.dart lib/features/task/presentation/screens/task_list_screen.dart lib/features/task/data/repositories/task_repository.dart` -> No issues found

## User Impact

The user can start the day with a next task that better matches the real execution moment: what is urgent, what plan matters, how hard the card is, and whether Aurora sees a strained state. If completion fails to sync, the user no longer has to wonder whether progress vanished; the card says what happened and offers a retry.
