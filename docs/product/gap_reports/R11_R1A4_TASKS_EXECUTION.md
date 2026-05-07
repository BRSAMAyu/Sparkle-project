# R11-R1A4: Tasks + Execution Journey Audit

**Date**: 2026-05-07
**Auditor**: Claude Code Agent
**Scope**: Complete task management lifecycle from creation through execution, completion, and reflection

---

## Summary: PASS with minor issues

The task management journey is comprehensively implemented across all three layers (Flutter, Go, Python). The state machine covers all required transitions (PENDING -> IN_PROGRESS -> PAUSED/STUCK/COMPLETED/ABANDONED/RESTORE). The offline-first architecture with optimistic updates, the CQRS event-driven backend, and the rich feedback loop are all production-quality. Two P1 issues and several P2 items were found but none block launch.

---

## Critical Issues (P0): 0

No launch-blocking issues found.

---

## High Issues (P1): 2

### Finding 1: Go TaskCommandService lacks PAUSED/RESTORE/STUCK state transitions
- **Severity**: P1
- **User Impact**: The Go `task_command.go` only implements Create/Start/Complete/Abandon/Delete/Update. PAUSE, RESUME, and STUCK transitions are proxied directly to Python (`proxy_routes.go` lines 116-118) without Go-side domain events. This means the Redis read model in `task_sync.go` never receives TaskPaused/TaskResumed/TaskStuck events, so the Redis cached task views can become stale for paused/stuck tasks.
- **File**: `backend/gateway/internal/service/task_command.go`
- **Current Code**: No `PauseTask`, `ResumeTask`, or `MarkStuck` methods exist
- **Expected**: Either (a) Go should proxy these state changes through its own command service and emit domain events, or (b) Python should publish events to the same Redis stream that the Go worker consumes from, ensuring the read model stays consistent.
- **Fix**: Add `PauseTask`/`ResumeTask`/`MarkStuck` methods to `TaskCommandService`, or ensure Python's task state change endpoints publish to `cqrs:stream:task` so the `TaskSyncWorker` can update Redis read models.

### Finding 2: Task detail screen Edit button navigates to generic create screen without pre-filling task data
- **Severity**: P1
- **User Impact**: When a user taps "Edit" on the task detail screen (bottom action bar), they are taken to `/tasks/new` instead of the edit mode with pre-filled data. The edit mode exists in `TaskCreateScreen` (loaded via `taskId` query param), but the bottom bar doesn't pass it.
- **File**: `mobile/lib/features/task/presentation/screens/task_detail_screen.dart:942-946`
- **Current Code**:
  ```dart
  // TRACKED(TD-002): 需要创建任务编辑页面，暂时导航到创建页面
  unawaited(context.push('/tasks/new'));
  ```
- **Expected**: Navigation should be `context.push('/tasks/new?taskId=${task.id}')` to trigger edit mode with the existing task data pre-filled.
- **Fix**: Change line 946 to `unawaited(context.push('/tasks/new?taskId=${task.id}'))`.

---

## Medium Issues (P2): 7

### Finding 3: No task deletion undo mechanism
- **Severity**: P2
- **User Impact**: When a user deletes a task, it's a soft delete (Go `task_command.go` sets `deleted_at`), but there's no undo option. The confirmation dialog doesn't offer a grace period or undo snackbar.
- **File**: `mobile/lib/features/task/presentation/screens/task_detail_screen.dart:1028-1050`
- **Current Code**: Delete immediately calls `ref.read(taskListProvider.notifier).deleteTask(task.id)` then pops.
- **Expected**: Show a snackbar with an "Undo" action for 5-10 seconds before the soft-delete propagates.
- **Fix**: Implement an undo-capable delete flow using a delayed sync pattern, similar to how `completeTask` uses optimistic updates with retry/discard.

### Finding 4: Reflection questions in feedback dialog use hardcoded Chinese/English strings
- **Severity**: P2
- **User Impact**: Three reflection question fields use `_copyForLocale(context, zh: '...', en: '...')` instead of the i18n system (`context.l10n`). These strings won't be included in localization files and can't be translated to additional languages.
- **File**: `mobile/lib/features/task/presentation/widgets/task_feedback_dialog.dart:727-766`
- **Current Code**: `_copyForLocale(context, zh: '这个任务中你卡在哪里了？', en: 'Where did you get stuck in this task?')` etc.
- **Expected**: Use `AppLocalizations` keys like `context.l10n.taskFeedbackStuckQuestion`.
- **Fix**: Add the 6 strings (3 labels + 3 hints) to `app_localizations_en.dart` and `app_localizations_zh.dart`, then reference via `context.l10n`.

### Finding 5: Move-to-plan picker shows untranslated strings
- **Severity**: P2
- **User Impact**: The plan picker dialog on task detail uses hardcoded English strings: `'Move task to plan'`, `'Detach from current plan'`, `'Active plans'`, `'Archived plans'`, `'Task detached from plan'`, `'Task moved successfully'`, `'Move failed: $e'`.
- **File**: `mobile/lib/features/task/presentation/screens/task_detail_screen.dart:517-557`
- **Current Code**: Hardcoded strings like `title: 'Move task to plan'`
- **Expected**: All user-facing strings should use `context.l10n`.
- **Fix**: Add i18n keys and replace hardcoded strings.

### Finding 6: _GuideInfoRow label separator hardcoded as Chinese colon
- **Severity**: P2
- **User Impact**: The structured guide section renders labels with a fullwidth colon character "：" regardless of locale. This looks correct in Chinese but incorrect in English where a regular colon ":" is expected.
- **File**: `mobile/lib/features/task/presentation/screens/task_detail_screen.dart:1247`
- **Current Code**: `TextSpan(text: '$label：', ...)`
- **Expected**: Use locale-appropriate separator: `$label:` for English, `$label：` for Chinese.
- **Fix**: Use `I18nService.instance.isChinese ? '：' : ': '` for the separator.

### Finding 7: No date-based sorting option in task list
- **Severity**: P2
- **User Impact**: The task list supports filtering by status and priority, and manual reordering, but has no automatic sort by due date or creation date. Users with many tasks may struggle to find time-sensitive items.
- **File**: `mobile/lib/features/task/presentation/screens/task_list_screen.dart`
- **Current Code**: No sort-by-date option exists in the filter UI.
- **Expected**: Add a sort toggle (by due date, by creation date, by priority) alongside the existing filters.
- **Fix**: Add a sort provider and sort dropdown/toggle in the app bar.

### Finding 8: TaskSyncWorker doesn't handle PAUSED/RESTORE/STUCK events from Redis stream
- **Severity**: P2
- **User Impact**: Related to Finding 1. Even if Python publishes task.pause/task.resume events to Redis, the Go `TaskSyncWorker.handleEvent()` switch statement doesn't have cases for these events, so they'd be silently ignored.
- **File**: `backend/gateway/internal/worker/task_sync.go:129-150`
- **Current Code**: Switch only handles `EventTaskCreated/Started/Completed/Abandoned/Deleted/Updated`
- **Expected**: Add cases for `EventTaskPaused`, `EventTaskResumed`, `EventTaskStuck` to update the Redis read model status.
- **Fix**: Extend the switch statement and add corresponding handler methods.

### Finding 9: Stuck task status transition is one-way (no auto-recovery to IN_PROGRESS)
- **Severity**: P2
- **User Impact**: When a task is marked STUCK, the user can only proceed via the stuck help sheet (which offers chat or Aurora core session). There's no "resume from stuck" button in the execution screen's bottom controls -- the pause button is hidden when status is STUCK and the user must use the stuck help sheet to proceed. The FV-16 auto-recovery flow for PAUSED exists but no analogous auto-recovery for STUCK tasks.
- **File**: `mobile/lib/features/task/presentation/screens/task_execution_screen.dart:2185-2186`
- **Current Code**: `final canPause = task.status == TaskStatus.inProgress || task.status == TaskStatus.stuck;` -- this is actually correct, pause IS available from stuck. However, there's no direct "I'm no longer stuck" resume path.
- **Expected**: Consider adding a "Continue anyway" option in the stuck help sheet that transitions STUCK -> IN_PROGRESS without requiring a full pause/resume cycle.
- **Fix**: Add a "Continue" button to `StuckHelpSheet` that calls `resumeTask` after marking stuck resolved.

---

## Findings Detail

### Verified Working: 42 items confirmed

1. **Task List Screen** (`task_list_screen.dart`): Full implementation with status filter chips (all/pending/in_progress/paused/completed), priority filter (high/medium/low), text search, reorder mode, and FAB for creation.

2. **Pull-to-refresh**: Implemented via `RefreshIndicator` wrapping the list with `onRefresh: () => ref.read(taskListProvider.notifier).refreshTasks()`.

3. **Empty states**: Two distinct empty states -- "no results" for search with query display, and "no tasks" with a call-to-action button to create.

4. **Task count badges/summary**: `_TaskListSummary` widget shows counts for total/pending/in_progress/paused/completed when more than 2 tasks are visible.

5. **Loading skeletons**: `SparkleListSkeleton(count: 5)` shown when loading and empty.

6. **Error state with retry**: `CustomErrorWidget.page` with retry callback when tasks list is empty and error exists.

7. **Partial error handling**: Warning banner shown at top when error exists but tasks are still visible (stale data).

8. **Task Model** (`task_model.dart`): Complete model with 7 task statuses (PENDING, IN_PROGRESS, PAUSED, RESTORE, STUCK, COMPLETED, ABANDONED), 7 task types (LEARNING, TRAINING, ERROR_FIX, REFLECTION, SOCIAL, PLANNING, OCR), sync status tracking, source lifecycle bindings, and full copyWith.

9. **Task Creation Screen** (`task_create_screen.dart`): Full form with title (required + validated), type selector, tags, estimated time, difficulty, energy cost, due date picker, optional AI guide generation. Supports both create and edit modes.

10. **AI suggestions during creation**: Debounced (800ms) title input triggers `getSuggestions()` API call, showing knowledge node chips with auto-apply capability.

11. **Task creation with nudges**: `createTaskWithNudges()` returns behavioral suggestions that display after creation for time adjustments.

12. **Plan linking**: Task creation accepts `planId` and `planName` query parameters, shows plan context card during creation.

13. **Task Detail Screen** (`task_detail_screen.dart`): Rich detail view with sliver app bar, type/status chips, structured guide section, plan context card, subtask expansion tile, move-to-plan picker, share capability, source lifecycle badges, "why this today" panel.

14. **Task Execution Screen** (`task_execution_screen.dart`): Comprehensive execution environment with timer (count-up/countdown/pomodoro), focus mode entry card, task protocol panel, guide panel, subtask list, quick tools panel, AI chat panel, stuck help FAB, AI coach FAB.

15. **Timer modes**: Count-up, countdown (with preset durations 15/25/45/60 min), and pomodoro (25 min work / 5 min break cycles) with reset button.

16. **Focus protection exit confirmation**: Triple-step confirmation dialog after 15 seconds on the execution screen. Auto-pauses task on exit if elapsed time exceeds half the estimated time.

17. **Task completion flow**: Full completion dialog with elapsed time display, success criteria checklist, free-text note field, and explicit "criteria met / not met" choice.

18. **Optimistic completion updates**: Task status immediately set to COMPLETED in local state with `syncStatus: pending`, then synced to server. Failure marks as `syncStatus: failed` with retry option.

19. **Completion celebration**: `TaskCompletionCelebration` widget with confetti animation, success criteria display, and auto-dismiss timer.

20. **Task feedback dialog** (`task_feedback_dialog.dart`): Rich post-completion feedback with AI response (typewriter effect), star rating, difficulty category, three structured reflection questions (stuck point, effective method, adjustment intention), achievement unlocks display, streak milestones, flame/stats updates, and next action suggestions.

21. **Next actions after completion**: Shows recommended next steps (quick review, light expand, practice apply, rest break, continue plan) with tap-to-navigate behavior.

22. **Achievement integration**: Task completion triggers achievement check via `_processAchievementUnlocks()`, visual element unlocks for achievements.

23. **Provider cascade on completion**: Invalidates galaxy, plan, learning portfolio, achievement, weekly growth narrative, and dashboard providers on task completion.

24. **Task Provider** (`task_provider.dart`): Complete `TaskNotifier` with all CRUD operations, state transitions (start/pause/resume/complete/abandon/stuck), reorder, quick actions (snooze/too-hard/skip), guide generation, execution state management, and feedback submission.

25. **Offline queue** (`task_offline_queue.dart`): Full offline-first queue for start/pause/resume/complete/abandon operations with dedup keys and priority ordering.

26. **Paused task status panel** (`paused_task_status_panel.dart`): Shows pause reason (manual/inactivity/system with localized explanations), duration pill, resume button with undo option, and reason detail dialog.

27. **Paused recovery on task detail**: `StaleRecoveryCard` shown when task is PAUSED/RESTORE, offering resume or edit options with elapsed time calculation.

28. **Restore dialog** (`task_restore_dialog.dart`): Dedicated restore dialog showing next step suggestion from task metadata or guide content.

29. **Stuck help flow**: `StuckHelpSheet` bottom sheet with chat-about-stuck and Aurora core session options. `markTaskStuck()` sends diagnostic data (recent steps, elapsed seconds, trigger source).

30. **Go task command service** (`task_command.go`): CQRS with outbox pattern for reliable event publishing. Transactional consistency for Create/Start/Complete/Abandon/Delete/Update operations.

31. **Go proxy routes** (`proxy_routes.go`): Complete REST API with 30+ task endpoints including CRUD, lifecycle transitions (start/pause/resume/complete/abandon/stuck), guidance, suggestions, resources, feedback, snooze, skip, too-hard, reorder, today, recommended, and micro-recommendations.

32. **Task sync worker** (`task_sync.go`): Redis-based CQRS projection worker handling TaskCreated/Started/Completed/Abandoned/Deleted/Updated events, maintaining read models and stats in Redis.

33. **Python task API** (`tasks.py`): Full REST endpoints for all state transitions with service-layer calls ensuring state sync and event publishing.

34. **Achievement event consumer** (`achievement_event_consumer.py`): Listens for `task.completed` events and triggers `AchievementEngine.process_event()` with TASK_COMPLETED event type.

35. **Low-yield gentle block** (`low_yield_gentle_block_card.dart`): Complete UI card showing low-yield activity detection with reason, suggestion, deadline/goal context chips, and three actions (correct/continue/switch). Provider (`low_yield_block_provider.dart`) manages block state.

36. **Low-yield guard** (Python `low_yield_guard.py`): Backend detection logic in `SpineOrchestrator` that checks activities under deadline pressure and emits divine moment cards via `_emit_low_yield_card()`.

37. **Daily/today tasks**: `taskListProvider` loads `todayTasks` via `getTodayTasks()` API endpoint. Dashboard screen has `task_board_provider.dart` for today's task board.

38. **Task notification scheduling**: `TaskNotificationScheduler` schedules, reschedules, and cancels reminders on task create/update/delete/complete.

39. **Calendar sync**: Tasks with due dates are synced to the calendar via `calendarRepository.syncTaskLinkedEvent()`.

40. **Subtask management**: `SubtaskListWidget` and `subtask_provider.dart` handle subtask display and toggling.

41. **AI execution handoff**: OpenClaw integration with execution intents, templates, approval cards, and result confirmation/rejection flow.

42. **Task offline indicator**: `TaskOfflineIndicator` widget shows sync status in both task list and execution screens.

---

## Architecture Summary

### State Machine (Verified Complete)
```
PENDING --start--> IN_PROGRESS
IN_PROGRESS --pause--> PAUSED
IN_PROGRESS --stuck--> STUCK
IN_PROGRESS --complete--> COMPLETED
IN_PROGRESS --abandon--> ABANDONED
PENDING --abandon--> ABANDONED
PAUSED --resume--> IN_PROGRESS (via RESTORE intermediate)
PAUSED --auto_recover--> RESTORE --resume--> IN_PROGRESS
STUCK --pause--> PAUSED
STUCK --complete--> COMPLETED
```

### Data Flow (Verified End-to-End)
```
Flutter tap -> task_provider.dart (optimistic update)
  -> task_repository.dart (Dio HTTP)
    -> Go proxy_routes.go (proxy with auth)
      -> Python tasks.py (FastAPI endpoint)
        -> TaskService (state transition + validation)
          -> PostgreSQL (persistent storage)
          -> Redis Streams (event bus)
            -> TaskSyncWorker (Go, Redis read model)
            -> AchievementEventConsumer (Python, achievement checks)
  <- JSON response
  <- Flutter state update (confirm or rollback)
```
