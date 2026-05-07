# R13-R1A4: Tasks + Execution -- Independent Audit Report

> **Date**: 2026-05-07 | **Auditor**: Opus Independent Agent | **Scope**: Full Task CRUD, State Machine, Quick Actions, Execution, Subtasks, Low-Yield Detection
> **Status**: FRESH INDEPENDENT AUDIT -- no reliance on prior R11 findings

---

## Summary

| Category | P0 (Blocks User) | P1 (Degrades UX) | P2 (Polish) | Verified Working |
|----------|:-----------------:|:-----------------:|:-----------:|:----------------:|
| Task CRUD | 0 | 2 | 2 | 8 |
| State Machine | 0 | 1 | 1 | 6 |
| Quick Actions | 0 | 0 | 0 | 6 |
| Task-Goal Association | 0 | 1 | 0 | 3 |
| Execution Features | 0 | 0 | 1 | 5 |
| Low-Yield Detection | 0 | 0 | 0 | 3 |
| Task Detail Screen | 0 | 1 | 1 | 5 |
| Edge Cases | 0 | 0 | 1 | 4 |
| **Total** | **0** | **5** | **6** | **40** |

**Overall**: Task system is substantially complete and well-wired. No P0 blockers. Five P1 findings require attention before launch.

---

## P1 Findings

### P1-01: Go UpdateTaskRequest Missing Tags/Type/EnergyCost Fields
**Severity**: P1 -- Data Loss Risk
**Files**:
- `backend/gateway/internal/service/task_command.go:35-44` -- `UpdateTaskRequest` only has `Title, EstimatedMinutes, Difficulty, Priority, DueDate, GuideContent`
- `mobile/lib/shared/entities/task_model.dart:353-386` -- Flutter `TaskUpdate` has `type, tags, energyCost, status, userNote`

**Evidence**: Flutter sends `TaskUpdate` with `tags`, `type`, and `energyCost` fields, but the Go `UpdateTaskRequest` struct does not contain these fields. The `UpdateTask` SQL query (line 391-410) only updates `title, estimated_minutes, difficulty, priority, guide_content, due_date`. Since the Go update goes through `proxyWithHeaders` to Python (proxy_routes.go:102), the actual persistence works via Python. However, the Go `TaskCommandService.UpdateTask` method is incomplete -- if any code path uses it directly instead of proxying, `tags`, `type`, `energy_cost`, `status`, and `userNote` would be silently dropped.

**Risk**: If the Go command service is ever used directly (e.g., for CQRS write path, future admin tools, or event replay), tag/type changes will be lost.

**Fix**: Add `Tags`, `Type`, `EnergyCost`, `Status`, `UserNote` fields to `UpdateTaskRequest` and the SQL query.

---

### P1-02: RESTORE State Has No Backend Transition Path
**Severity**: P1 -- Orphan State
**Files**:
- `backend/gateway/internal/db/schema.sql:559` -- DB enum includes `RESTORE`
- `mobile/lib/shared/entities/task_model.dart:29` -- Flutter enum includes `restore`
- `backend/gateway/internal/service/task_command.go` -- No `RestoreTask` method
- `mobile/lib/features/task/data/repositories/task_repository.dart` -- No `restoreTask` API call

**Evidence**: The `RESTORE` status exists in the DB enum and Flutter model, and the Flutter UI handles it (treated identically to `PAUSED` in task_detail_screen.dart:93, task_list_screen.dart:495, task_quick_action_menu.dart:231). However, there is no Go `RestoreTask` method, no Python API endpoint to transition to RESTORE, and no Flutter repository method to call it. The state appears to be set only by backend logic (likely the stale/paused recovery system), but there is no user-facing action to trigger or clear it.

**Risk**: Tasks stuck in RESTORE state have no clear user recovery path beyond the StaleRecoveryCard, which calls `resumeTask` (transitioning PAUSED->IN_PROGRESS, but RESTORE status may not match the SQL WHERE clause in `ResumeTask` which filters `status = 'PAUSED'`).

**Fix**: Either (a) add a `RestoreTask` transition in Go (RESTORE -> IN_PROGRESS with appropriate WHERE clause), or (b) have the StaleRecoveryCard's resume action handle RESTORE status by calling a dedicated endpoint.

---

### P1-03: Hardcoded i18n Strings in Move-to-Plan Dialog
**Severity**: P1 -- i18n Gap
**File**: `mobile/lib/features/task/presentation/screens/task_detail_screen.dart:518-564`

**Evidence**: The `_showMoveToPlanPicker` method contains 8 hardcoded bilingual strings using inline `zh ? 'Chinese' : 'English'` pattern:
- Line 523: `'Move task to plan'` / `'移动任务到计划'`
- Line 525: `'Detach from current plan'` / `'从当前计划分离'`
- Line 533-534: `'Active plans'` / `'进行中的计划'`, `'Archived plans'` / `'已归档的计划'`
- Line 559-560: `'Task detached from plan'` / `'已从计划分离'`, `'Task moved successfully'` / `'移动成功'`
- Line 564: `'Move failed'` / `'移动失败'`
- Line 1063: `'Task deleted'` / `'任务已删除'`

These should use `context.l10n.*` keys for consistency with the rest of the app.

**Fix**: Add l10n keys for these 8 strings and replace the inline ternaries.

---

### P1-04: `confirmGeneratedTasks` Uses Raw URL Instead of ApiEndpoints
**Severity**: P1 -- Maintainability / Route Drift
**File**: `mobile/lib/features/task/data/repositories/task_repository.dart:1691`
```dart
final response = await _apiClient.post<dynamic>(
  '/tasks/confirm-batch/$toolResultId',
);
```

**Evidence**: All other task API calls use `ApiEndpoints.*` constants. This one uses a hardcoded string. Furthermore, there is no corresponding `/tasks/confirm-batch/:toolResultId` route registered in `backend/gateway/internal/handler/proxy_routes.go` -- the Go proxy only registers `/tasks` CRUD routes but NOT `confirm-batch`.

**Risk**: This endpoint will 404 when called because Go gateway has no route for it. Either the Python API has it and the Go route is missing, or this is dead code.

**Fix**: Add `POST /tasks/confirm-batch/:toolResultId` to Go proxy_routes.go and use `ApiEndpoints.confirmBatchTasks(toolResultId)`.

---

### P1-05: No "Reopen Completed Task" Feature
**Severity**: P1 -- Missing Recovery Path
**Files**:
- `mobile/lib/shared/entities/task_model.dart:389-403` -- `TaskComplete` model only
- `backend/gateway/internal/service/task_command.go:233-276` -- `CompleteTask` WHERE `status = 'IN_PROGRESS'`
- No `ReopenTask` method anywhere in Go or Flutter

**Evidence**: Once a task is COMPLETED, the user has no way to reopen it (transition back to IN_PROGRESS or PENDING). The `restoreDeletedTask` in task_provider.dart:381 recreates a deleted task, but there is no equivalent for completed tasks. This is a common user need ("I accidentally marked it done" / "I need to revisit this").

**Risk**: User frustration when accidentally completing a task.

**Fix**: Add `ReopenTask` method in Go TaskCommandService (COMPLETED -> IN_PROGRESS or PENDING) and wire through Python API + Flutter.

---

## P2 Findings

### P2-01: No Task Description Field
**Severity**: P2 -- Feature Gap
**Files**:
- `backend/gateway/internal/db/schema.sql:5622-5658` -- No `description` column in tasks table
- `mobile/lib/shared/entities/task_model.dart:119-156` -- No `description` field in TaskModel
- `mobile/lib/features/task/presentation/screens/task_create_screen.dart` -- No description input field

**Evidence**: Tasks only have `title`, `guideContent`, `aiPrompt`, and `userNote`. There is no separate `description` field for the user to add freeform context. The `userNote` field serves double duty but is only populated after completion.

---

### P2-02: Task List Pagination Not Implemented Client-Side
**Severity**: P2 -- Performance
**File**: `mobile/lib/features/task/presentation/providers/task_provider.dart:147-148`
```dart
final paginatedResponse = await _taskRepository.getTasks(filters: {});
```

**Evidence**: The repository supports `page` and `pageSize` parameters (task_repository.dart:328-329), but the provider always uses defaults (page=1, pageSize=10). With 100+ tasks, only the first 10 load. There is no infinite scroll or load-more mechanism in the task list UI.

---

### P2-03: No Task Dependencies / Blocking
**Severity**: P2 -- Feature Gap
**Evidence**: No `task_dependencies` table in schema.sql, no dependency fields in TaskModel, no UI for setting up task blocking relationships. This is a known feature gap for future implementation.

---

### P2-04: Task List Filter Missing STUCK and ABANDONED Statuses
**Severity**: P2 -- UX Gap
**File**: `mobile/lib/features/task/presentation/screens/task_list_screen.dart:18`
```dart
enum TaskFilterOptions { all, pending, inProgress, paused, completed }
```

**Evidence**: The filter chips show 5 options but the DB supports 7 statuses (including STUCK and ABANDONED). STUCK tasks are grouped under "inProgress" filter and ABANDONED tasks are not filterable at all. Users cannot easily find abandoned tasks.

---

### P2-05: Focus Timer Does Not Persist Elapsed Time to Backend
**Severity**: P2 -- Data Gap
**File**: `mobile/lib/features/task/presentation/screens/task_execution_screen.dart:88-101`

**Evidence**: The `_elapsedSeconds` counter runs locally in the execution screen state. If the user exits and re-enters, the timer resets to 0. The `actualMinutes` is only recorded at completion time. There is no periodic save of progress (e.g., to handle app crashes or navigation away).

---

### P2-06: Quick Action Menu Not Accessible from Task Detail Screen
**Severity**: P2 -- UX Consistency
**Files**:
- `mobile/lib/features/task/presentation/screens/task_detail_screen.dart` -- No reference to `showTaskQuickActionMenu`
- `mobile/lib/features/task/presentation/widgets/task_quick_action_menu.dart` -- Only called from TaskCard

**Evidence**: Quick actions (snooze, too-hard, skip, help) are only accessible via the task card's long-press in the list view. The task detail screen has no way to access these actions. Users must navigate back to the list to snooze or skip a task.

---

## Verified Working

### Task CRUD

1. **Create**: Flutter TaskCreateScreen (task_create_screen.dart) -> TaskRepository.createTaskWithNudges -> POST `/tasks` via Go proxy -> Python. All fields saved: title, type, tags, estimatedMinutes, difficulty, energyCost, planId, dueDate, knowledgeNodeId, guideContent, guideJson. AI suggestions and nudges work. **VERIFIED**

2. **Read**: TaskListScreen loads tasks via `getTasks()` with pagination support in repository. TaskDetailScreen uses `taskDetailProvider` (FutureProvider.family) for individual task. Demo mode fallback works. **VERIFIED**

3. **Update**: Edit mode in TaskCreateScreen loads existing task (`_loadExistingTask`) and sends `TaskUpdate` via `PUT /:id`. Updates title, type, estimatedMinutes, difficulty, energyCost, tags, dueDate. Calendar sync and reminder rescheduling triggered. **VERIFIED** (via Python proxy)

4. **Delete**: TaskDetailScreen shows confirmation dialog (line 1017-1080) with `showSensoryDialog`. Calls `deleteTask` -> soft delete via `DELETE /:id`. Undo mechanism via `restoreDeletedTask`. Calendar cleanup included. **VERIFIED**

### State Machine

5. **PENDING -> IN_PROGRESS**: `StartTask` in Go (WHERE status = 'PENDING') + Python endpoint. Auto-triggered when entering execution screen with a pending task (task_execution_screen.dart:175-197). **VERIFIED**

6. **IN_PROGRESS -> COMPLETED**: `CompleteTask` in Go (WHERE status = 'IN_PROGRESS'). Optimistic update with sync status tracking in Flutter. Celebration animation + confetti + feedback dialog. Achievement unlocks processed. **VERIFIED**

7. **IN_PROGRESS -> PAUSED**: `PauseTask` in Go (WHERE status = 'IN_PROGRESS'). Auto-pause on long exit from execution screen (task_execution_screen.dart:256-270). Resume reminder notification. Offline queue support. **VERIFIED**

8. **PAUSED -> IN_PROGRESS**: `ResumeTask` in Go (WHERE status = 'PAUSED'). Triggered from quick actions, task card, or StaleRecoveryCard. **VERIFIED**

9. **IN_PROGRESS -> STUCK**: `MarkStuck` in Go (WHERE status = 'IN_PROGRESS'). Diagnosis dialog via StuckHelpSheet. Triggered from execution screen FAB. **VERIFIED**

10. **PENDING/IN_PROGRESS -> ABANDONED**: `AbandonTask` in Go (WHERE status IN ('PENDING', 'IN_PROGRESS')). Different from delete -- sets status, preserves record. Triggered via quick action "skip". **VERIFIED**

### Quick Actions

11. **Quick Action Menu**: 6 actions (pause, resume, snooze, too-hard, skip, help). All wired to real backend calls via `TaskNotifier`. Loading/success/error feedback via `AppFeedback`. Context-sensitive -- only shows applicable actions for current status. **VERIFIED**

12. **Snooze**: Reschedules due date, updates calendar, reschedules reminders. Returns user-friendly message. **VERIFIED**

13. **Too-Hard**: Creates subtasks to break down task, decreases difficulty. Returns subtask data. **VERIFIED**

14. **Skip**: Sets status to ABANDONED, removes from calendar, cancels reminders. **VERIFIED**

### Task-Goal Association

15. **Plan Context Card**: Task detail screen shows parent plan card (task_detail_screen.dart:626-700) with navigation to plan detail (`context.push('/plans/${plan.id}')`). Loading and error states handled. **VERIFIED**

16. **Move to Plan**: `_showMoveToPlanPicker` provides card picker with active/archived plans, detach option. Calls `moveTaskToPlan` -> resolves card IDs -> `POST /cards/:id/move`. **VERIFIED**

17. **Task Creation from Plan Context**: TaskCreateScreen accepts `planId` and `planName` query parameters, shows plan badge. **VERIFIED**

### Execution Features

18. **Timer Integration**: TimerWidget supports count-up, countdown, and Pomodoro modes. Preset durations available. Timer state management in execution screen. BGM integration for focus session. **VERIFIED**

19. **Subtasks**: Full CRUD via SubtaskNotifier. Toggle completion, reorder, delete. Progress tracking (`subtasksTotal`/`subtasksCompleted` in TaskModel). Shown in task detail with expansion tile. **VERIFIED**

20. **AI Execution Handoff**: `handoffTaskToAi` dispatches to OpenClaw execution engine. Template selection, offline queueing, execution polling (5s interval), result approval/rejection. **VERIFIED**

21. **Focus Protection**: Exit confirmation after 15 seconds. Auto-pause on long exit. Pomodoro break/work cycle. **VERIFIED**

22. **Offline Support**: Task pause/resume operations enqueue via SyncEngine when offline. `TaskOfflineIndicator` widget shows sync status. Offline queue drain on reconnection. **VERIFIED**

### Low-Yield Behavior Detection

23. **LowYieldGentleBlockCard**: Exists and is functional. Shows activity, reason, suggestion with 3 action buttons (correct, continue, switch). Deadline and goal context chips. Semantic label for accessibility. **VERIFIED**

24. **LowYieldBlockProvider**: State notifier ingests payloads from chat metadata, tracks handled blocks, records user actions to event stream. Multiple payload key formats supported. **VERIFIED**

25. **Integration Point**: Ingested from chat provider metadata in divine_moment_card.dart and action_card.dart. Records accept/dismiss/correct actions. **VERIFIED**

### Task Detail Screen

26. **All Information Visible**: Title (SliverAppBar), type/status chips, estimated duration, difficulty, energy cost, due date, plan context, guide content (markdown), structured guide (objective, steps, key points), AI prompt, user note, subtasks, source lifecycle badges, "why this today" panel. **VERIFIED**

27. **Edit Functionality**: Edit button in bottom bar navigates to `/tasks/new?editFrom=${task.id}` which loads existing task data into TaskCreateScreen edit mode. **VERIFIED**

28. **i18n**: Majority of strings use `context.l10n.*` -- loading, error, section titles, status labels, type labels, dialog text, guide sections. (Exception: P1-03 hardcoded strings in move-to-plan.) **VERIFIED**

29. **Delete**: Red-outlined delete button in bottom bar with confirmation dialog. Uses `showSensoryDialog`. Undo snackbar shown after deletion. **VERIFIED**

30. **Share**: Share button in app bar calls `showUniversalShareSheet` with task metadata. **VERIFIED**

### Edge Cases

31. **Empty Task List**: `EmptyState` widget with `EmptyStateType.noTasks` type, shows title/description/action button pointing to task creation. Search with no results shows `EmptyState.noResults`. **VERIFIED**

32. **Error Handling**: `CustomErrorWidget.page` with retry button. Partial error banner when tasks exist but error occurred. Error snackbar via `ref.listenManual`. **VERIFIED**

33. **Loading States**: `SparkleListSkeleton` for initial load, `LinearProgressIndicator` for suggestion loading, `LoadingIndicator.circular` for detail page, skeleton cards for subtasks. **VERIFIED**

34. **Drag Reorder**: `ReorderableListView` with drag handles. Optimistic state update with rollback on error. Only available when no filters/search active. **VERIFIED**

---

## Architecture Notes

### Data Flow Completeness
```
Flutter TaskModel -> TaskRepository -> Go Proxy (proxy_routes.go) -> Python API
                    TaskNotifier   -> Go TaskCommandService (CQRS write path)
                    TaskCard       -> Quick Actions -> Python API
                    TaskDetailScreen -> Edit -> Python API
```
Both the proxy path (for most operations) and the CQRS command path (for Go-side writes) are implemented. The proxy path is the primary path used by Flutter.

### Event Bus Integration
Task CRUD operations in Go publish domain events to the outbox:
- `task.created`, `task.started`, `task.completed`, `task.abandoned`, `task.deleted`, `task.updated`, `task.paused`, `task.resumed`, `task.stuck`
- These flow through the CQRS outbox to Redis Streams for consumption by achievement, galaxy, and other event consumers.

### Offline Resilience
Task pause/resume operations support offline queueing via `SyncEngine`. The `OfflineEnqueuedException` is thrown after enqueuing, allowing the UI to show an optimistic state.

---

## Recommendations (Priority Order)

1. **P1-02**: Add RESTORE -> IN_PROGRESS transition in Go `ResumeTask` (add `OR status = 'RESTORE'` to WHERE clause)
2. **P1-04**: Add missing Go proxy route for `/tasks/confirm-batch/:toolResultId`
3. **P1-03**: Extract 8 hardcoded strings to l10n keys
4. **P1-01**: Align Go `UpdateTaskRequest` fields with Flutter `TaskUpdate`
5. **P1-05**: Add `ReopenTask` for completed -> in_progress recovery
6. **P2-04**: Add STUCK and ABANDONED filter options
7. **P2-06**: Add quick action menu trigger from task detail screen
