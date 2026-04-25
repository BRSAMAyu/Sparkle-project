# Reviewer A — C11: 间隔重复提醒链路（Celery→推送→复习chat）
Timestamp: 2026-04-25T20:35:00+08:00
Chain Index: 5

## Chain Flow Summary

Celery Beat fires `scan_spaced_repetition_reminders` daily at 9:30 AM (Asia/Shanghai). The scan dispatches per-user tasks that evaluate each Galaxy node: nodes with mastery 30%-80% that are at exactly 1, 3, 7, 14, or 30 days since last study get a push notification. The notification carries a deep link `/chat?review_node={id}&node_label={name}&prompt=带我复习...`. On tap, `push_navigation_service` extracts the deep link, routes through `DeepLinkService` to `/chat`, and the chat screen passes `review_node` context to Aurora via `extra_context`. Aurora generates a specialized review prompt for that node.

## Critical Issues 🔴

None found.

## Major Issues 🟡

**1. `celery_tasks.py:1141-1150`: Exact-day interval matching — missed scan days lose review opportunities permanently**

The `_spaced_repetition_due_interval_days` function checks if `elapsed_days in (1, 3, 7, 14, 30)`. If the Celery scan is skipped on day 7 (server downtime, queue backlog, crash), on day 8 the elapsed_days is 8 which doesn't match any interval. The day-7 review is permanently missed — the next chance is day 14. This doubles the review gap for that node.

There's no grace window (e.g., "trigger if within ±1 day of interval"). For a system designed around spaced repetition learning science, missing intervals directly impacts retention.

Expected: Trigger if `elapsed_days >= interval and elapsed_days < interval + grace_window`. Actual: Only triggers on exact match.

**2. `celery_tasks.py:1105-1107`: Fixed intervals regardless of mastery level**

Intervals are `(1, 3, 7, 14, 30)` for all nodes regardless of mastery. A node at 31% mastery (barely learned) gets the same schedule as one at 79% (well-learned). Standard spaced repetition algorithms (SM-2, Anki) increase intervals for well-known material and decrease for poorly-known material. The current system treats all mid-mastery nodes identically.

Expected: Nodes at lower mastery (30-50%) should have shorter intervals; nodes at higher mastery (65-80%) should have longer intervals. Actual: All nodes get the same fixed schedule.

## Minor Issues 🟢

**3. `celery_tasks.py:1251-1283`: 500-user scan limit per day**

The scan limits to 500 users per invocation. If there are more active users, some won't get processed that day. They'll be picked up the next day, but this creates inconsistent UX where some users always get reminders and others don't.

**4. `celery_tasks.py:1194-1197`: Nodes below 30% mastery are excluded from review**

Nodes with mastery < 30% are skipped entirely. These are the weakest nodes that arguably need the most review. The rationale seems to be that very weak nodes should be re-learned rather than reviewed, but the threshold may be too aggressive.

## Working Well ✅

**Celery scheduling and scan logic** (`celery_tasks.py`):
- Daily scan at 9:30 AM Asia/Shanghai — reasonable morning timing
- Per-user task dispatch prevents timeout on large user bases
- Cooldown enforcement (24h) via `notification_center_service.py:72-77` prevents notification spam
- Filters out `decay_paused` nodes (line 1190-1192)

**Notification payload** (`notification_center_service.py:79-128`):
- Includes `node_id`, `node_name`, `mastery`, `interval_days` in payload
- Deep link constructed with `review_node` + `node_label` + pre-built `prompt` (line 79-94)
- `primary_action` with `action_type: "galaxy_node_review"` and full payload
- `push_via_websocket=True` ensures immediate delivery

**Push notification routing** (`push_navigation_service.dart`):
- `handleOpenedPayload` extracts `deep_link` from notification data (line 80-89)
- Routes through `DeepLinkService.handleExternalDeepLink` preserving full query string
- Falls back to `destination_route` if `deep_link` is empty

**Route parameter extraction** (`routes.dart:191-197`):
- `/chat` route correctly extracts `review_node` and `node_label` from query parameters
- Builds `initialExtraContext` map that preserves all review context
- Passes to `ChatScreen` as `initialExtraContext` parameter

**Chat context delivery** (`chat_screen.dart:506-531`):
- `_queueInitialPromptDispatch` sends the pre-built review prompt with `extraContextOverrides`
- `chat_provider.dart:799-840` passes `extraContextOverrides` through WebSocket as `extra_context`
- WebSocket payload preserves `review_node` and `node_label` in the `extra_context` field

**Aurora runtime processing** (`service.py:765-794`):
- `_review_focus_from_context` extracts `review_node` and `node_label` from `request_extra_context`
- `_build_review_node_first_turn_message` generates specialized review prompt with node-specific language
- Falls back to `_humanize_review_node_id` if `node_label` is missing (line 775)

**Test coverage**:
- Backend unit test `test_spaced_repetition_reminder.py:72-77` validates notification payload contains `review_node` and `node_label`
- Mobile integration test `h5_cross_system_chains_test.dart:86-91` validates routing from notification to chat with correct context

## Files Examined

1. `backend/app/core/celery_tasks.py` (lines 1105-1283, scan + per-user task + interval calculation)
2. `backend/app/core/celery_app.py` (line 1033-1038, beat schedule)
3. `backend/app/services/notification_center_service.py` (lines 45-155, notification creation + cooldown)
4. `backend/app/services/galaxy/review_urgency_service.py` (separate UI scoring, not used by reminders)
5. `backend/tests/unit/test_spaced_repetition_reminder.py` (payload validation)
6. `mobile/lib/core/services/push_navigation_service.dart` (notification tap → deep link extraction)
7. `mobile/lib/core/services/deep_link_service.dart` (deep link routing)
8. `mobile/lib/app/routes.dart` (query parameter extraction for /chat)
9. `mobile/lib/features/chat/presentation/screens/chat_screen.dart` (context delivery)
10. `mobile/lib/features/chat/presentation/providers/chat_provider.dart` (extra context passthrough)
11. `mobile/test/widget/h5_cross_system_chains_test.dart` (integration test validation)

## Confidence: High — The end-to-end flow from Celery scan to Aurora review prompt is well-wired and tested. Issues are limited to interval algorithm quality, not broken links.
