# Reviewer A — C03: 任务卡点(stuck)→卡点帮助面板→Aurora诊断内容
Timestamp: 2026-04-25T18:28:00+08:00
Chain Index: 1

## Chain Flow Summary

User is on the task execution screen. A FAB labeled "卡住了?" appears in the bottom-left. Tapping it opens `StuckHelpSheet` as a bottom sheet, which reads diagnostic content from the task's pre-generated `guideJson` metadata (micro_teaching / fallback_if_stuck / if_stuck). The sheet also offers "和Sparkle聊聊这个问题" which navigates to chat with a structured stuck prompt. There is no "stuck" task status — the interaction is purely UI-side with no backend state change.

## Critical Issues 🔴

**1. `backend/app/models/task.py:47-51` + `mobile/lib/features/task/presentation/screens/task_execution_screen.dart:452-466`: No stuck status — stuck state never reaches the backend**

TaskStatus enum has only `PENDING`, `IN_PROGRESS`, `COMPLETED`, `ABANDONED`. There is no `STUCK` status. No API endpoint exists to mark a task as stuck. The mobile code opens the help sheet as a purely local UI action — no API call, no status update, no event.

This means:
- The backend never learns the user was stuck
- `decision_loop.py:641` `_is_stuck_task_scene()` checks `task_state.stage == "stuck"` — but nothing ever sets this
- No stuck events flow to EventBus, achievement engine, or analytics
- Aurora's strategy recalibration (`service.py:602` `_with_strategy_recalibration_context`) relies on stale signals that never get produced from mobile stuck interactions
- The 53 governance rules and telemetry can't track stuck→unstuck transitions

Expected: Tapping "卡住了?" should set task status to STUCK (or equivalent), notify the backend, and trigger Aurora diagnostic. Actual: Purely local UI with no backend communication.

**2. `stuck_help_sheet.dart:27-31` + `task_card_generator.py:256-283`: Sheet content is static task metadata, NOT Aurora real-time diagnostic**

The chain description says "内容来自Aurora真实诊断而非静态文案". But `StuckHelpSheet` reads from `task.guideJson` — content generated at plan creation time by `task_card_generator.py`. This is static metadata baked into the task card, not a real-time Aurora diagnostic based on the user's current state.

The only Aurora interaction is the "和Sparkle聊聊这个问题" button, which navigates to chat with a pre-built prompt. This IS an Aurora conversation, but it's manual — the user must type and wait for a response, not see pre-computed diagnostic content.

Expected: Sheet shows Aurora's contextual diagnosis based on current user state. Actual: Sheet shows pre-generated generic help content from task creation time.

## Major Issues 🟡

**3. `task_execution_screen.dart:477`: `_openStuckChat` uses `context.go()` — navigation dead-end**

When user clicks "和Sparkle聊聊这个问题", `_openStuckChat` calls `context.go(route)` which replaces the entire navigation stack. The task execution screen is destroyed, and the running timer is lost. The user can't get back to their task from the chat screen. The back button from chat goes to `/home`, not back to the task.

Expected: Chat opens as overlay or push navigation, preserving the task execution context. Actual: Task execution screen is destroyed.

**4. `task_execution_screen.dart:480-493`: `_sendAuroraTrigger` doesn't pass stuck context to Aurora**

The `_sendAuroraTrigger` method sends a message via `taskChatProvider(task.id).notifier.sendMessage(message)` but doesn't include `task_state.stage="stuck"` or any stuck-specific context. Without this, Aurora's decision loop won't activate stuck-specific diagnostic mode (`_is_stuck_task_scene` returns False). The response will be generic, not the micro-teaching diagnostic described in `decision_loop.py:727-740`.

Expected: Aurora receives stuck context and activates micro-teaching diagnostic mode. Actual: Aurora receives a plain text message without stuck indicators.

## Minor Issues 🟢

None found beyond the above.

## Working Well ✅

**StuckHelpSheet widget is well-designed** (`stuck_help_sheet.dart`):
- Progressive content fallback: `micro_teaching` → `fallback_if_stuck` → `if_stuck` → `genericSuggestions` (line 27-32)
- Reads from 5+ field name variants for resilience (line 395-399, 402-416)
- Two-step micro-teaching card with diagnosis question + targeted fix (line 205-229)
- DraggableScrollableSheet with proper min/max sizing (line 35-37)
- "好了，继续" dismiss button (line 113-123)

**Stuck chat prompt is well-structured** (`task_execution_screen.dart:505-528`):
- Includes task title, estimated time, focus cue, steps, success criteria, and fallback suggestions
- Ends with clear instruction: "请先问我一个最关键的澄清问题，然后把下一步缩小到5分钟内能开始"

**FAB design is appropriate** (`task_execution_screen.dart:575-614`):
- Positioned in bottom-left, not blocking the timer
- "卡住了?" label is clear and inviting
- Tooltip and icon provide context

**Backend stuck diagnostic infrastructure exists** (`decision_loop.py`):
- `STUCK_TASK_STAGE_TOKENS` detection (line 126)
- `standard_layer_contract` for diagnostic responses (line 727-740)
- Micro-teaching mode activation (line 1255-1260)
- Rule injection for stuck tasks (line 984-992)
- Chat adapter fallback messages (chat_adapter.py line 632-635)
- Task card generator creates structured stuck_help content (task_card_generator.py line 563-617)

## Files Examined

1. `mobile/lib/features/task/presentation/widgets/stuck_help_sheet.dart` (full, 479 lines)
2. `mobile/lib/features/task/presentation/providers/task_provider.dart` (full, 1276 lines)
3. `mobile/lib/features/task/presentation/screens/task_execution_screen.dart` (lines 440-614)
4. `backend/app/aurora/runtime_v1/decision_loop.py` (stuck detection, diagnostic contracts, rule injection)
5. `backend/app/aurora/runtime_v1/service.py` (strategy recalibration context)
6. `backend/app/aurora/runtime_v1/chat_adapter.py` (micro-teaching context, fallback messages)
7. `backend/app/orchestration/task_card_generator.py` (stuck_help field generation)
8. `backend/app/models/task.py` (TaskStatus enum — no STUCK status)
9. `backend/app/services/task_service.py` (no stuck-related transitions)
10. `backend/app/api/v1/tasks.py` (no stuck endpoint)

## Confidence: High — The stuck feature has substantial backend diagnostic infrastructure but zero mobile-to-backend integration. The mobile side is purely local UI with static content. The chain description's claim of "Aurora真实诊断" is not met.
