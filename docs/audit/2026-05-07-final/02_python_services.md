# Python Services Layer Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Python Services Layer is architecturally sound with strong separation of concerns, consistent async patterns, and thorough error handling around external dependencies. The signal pipeline (SpineOrchestrator) and state aggregation systems are well-structured with proper kill-switch integration and audit trails. However, there are several issues that should be addressed before launch: event consumers lack explicit idempotency guarantees, all Celery tasks use `asyncio.run()` without retry configuration, and a few patterns carry real operational risk.

## Critical Issues (P0)

None found. No SQL injection, no credential exposure, no unguarded write paths.

## High Issues (P1)

### P1-1: All Celery tasks lack retry configuration

**Files**: All files in `backend/app/tasks/`
- `absence_scan_task.py`
- `checkpoint_nudge_task.py`
- `community_checkin_reminder.py`
- `guest_cleanup.py`
- `login_attempt_cleanup.py`
- `accountability_tasks.py`
- `policy_tasks.py`
- `update_similarities.py`

None of the 17 `@shared_task` definitions specify `max_retries`, `autoretry_for`, `acks_late=True`, or `retry_backoff`. If a transient error occurs (DB timeout, Redis blip), the task simply fails and is never retried. For a production system, at minimum `acks_late=True` and `autoretry_for=(Exception,)` with exponential backoff should be set.

Example from `absence_scan_task.py:18`:
```python
@shared_task(name="tasks.absence.scan_absent_users")
def scan_absent_users() -> dict[str, int]:
```
Should be:
```python
@shared_task(
    name="tasks.absence.scan_absent_users",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    acks_late=True,
)
```

### P1-2: Event consumers lack explicit idempotency

**Files**:
- `backend/app/services/achievement_event_consumer.py` (line 77-97)
- `backend/app/services/task_event_consumer.py` (line 61-91)

`GalaxyEventConsumer` uses `@reliable_consumer` decorator but `AchievementEventConsumer` and `TaskEventConsumer` do not. None of the three consumers have explicit idempotency checks for duplicate event processing. If the same `task.completed` event is delivered twice (Redis stream re-delivery after consumer crash), the following will execute twice:
- `AchievementEngine.process_event()` (double-counting progress)
- `AdaptiveReplanner.on_task_completed()` (double adjustment)
- Goal progress recalculation in `task_event_consumer.py:173-200`

The `GalaxyEventConsumer._handle_error_created()` has partial deduplication for error-gap node creation (line 246-253) but not for the event processing itself.

### P1-3: `asyncio.run()` inside Celery tasks creates event loop per invocation

**Files**: All Celery tasks in `backend/app/tasks/`

Every task creates and destroys an event loop via `asyncio.run()`. This is the documented pattern for mixing sync Celery with async code, but it means:
1. No connection pooling reuse between task invocations
2. Potential for "Event loop is closed" errors if any library caches the loop globally
3. `get_db_context()` (sync context manager wrapping async) may not properly clean up async sessions on exception paths

The `update_similarities.py:43-44` pattern is particularly risky:
```python
with get_db_context() as db:
    import asyncio
    asyncio.run(_update_all_similarities(db))
```
If `_update_all_similarities` raises, the `get_db_context().__exit__` runs in the sync context while the async cleanup may not execute properly.

## Medium Issues (P2)

### P2-1: Bare `except Exception: pass` in notification_service.py

**File**: `backend/app/services/notification_service.py:201-202, 218-219`

Two places silently swallow exceptions without logging:
```python
# Line 201-202
except Exception:
    pass

# Line 218-219
except Exception:
    pass
```
These guard the consecutive-ignore backoff and fatigue protection features. If either fails, there is no diagnostic trail. Should add `logger.debug(...)` at minimum.

### P2-2: `push_scheduler.py` uses `scan_iter` for recall queue processing

**File**: `backend/app/services/push_scheduler.py:125`

```python
async for key in self.redis.scan_iter(match=f"{_RECALL_QUEUE_PREFIX}*"):
```
`SCAN_ITER` in production Redis can be slow if the key space is large. For a periodic 15-minute job, this is likely acceptable but should be monitored. Consider using a Redis SET to track users with pending queues instead.

### P2-3: `update_similarities.py` O(n^2) pairwise user similarity computation

**File**: `backend/app/tasks/update_similarities.py:148-213`

The `_update_all_similarities` function computes Jaccard similarity for every pair of active users. With N active users, this is O(N^2) database operations. For 1,000 active users, that is ~500K pair comparisons. The batch flush at line 213-215 helps but each iteration calls `_get_common_subjects()` (a separate DB query) for qualifying pairs.

For production at scale, consider:
- Pre-computing user item vectors and using vector similarity
- Batching the common subjects query
- Setting an upper bound on active users processed per run

### P2-4: `_build_fallback_analysis` in error_book_service.py has hardcoded Chinese strings

**File**: `backend/app/services/error_book_service.py:708-718`

The fallback analysis path overwrites the I18n-generated values with hardcoded Chinese:
```python
# Lines 707-718: these overwrite the i18n values set above
correct_approach = (
    f"先用自己的话复述题目核心概念..."
)
similar_traps = [
    "把符号本身和它表示的对象混为一谈",
    ...
]
```
This violates the i18n strategy documented in CLAUDE.md. The `I18n.t()` calls at lines 688-705 produce correct localized strings, but lines 707-718 unconditionally overwrite them with hardcoded Chinese.

### P2-5: `dashboard_service.py` uses `datetime.now()` without UTC for daily report

**File**: `backend/app/services/dashboard_service.py:46`

```python
today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
```
This uses local server time rather than UTC. The rest of the file uses `_utcnow()` which returns UTC. Mixed timezone handling could cause incorrect "today" boundaries if the server timezone is not UTC.

### P2-6: `achievement_event_consumer.py` uses ephemeral consumer names

**File**: `backend/app/services/achievement_event_consumer.py:69`

```python
consumer_name=f"achievement-{_utcnow().timestamp()}",
```
Each restart creates a new consumer name. In Redis Streams, old consumer names accumulate in the consumer group, leading to pending message buildup. The `task_event_consumer.py` uses a stable `f"task-{os.getpid()}"` which is better but still not fully deterministic.

### P2-7: `guest_cleanup.py` deletes users without cascading cleanup

**File**: `backend/app/tasks/guest_cleanup.py:99-104`

```python
delete_query = delete(User).where(
    User.id.in_(user_ids_to_delete),
    User.registration_source == "guest",
)
await db.execute(delete_query)
```
This deletes User rows but does not clean up related data (tasks, plans, notifications, cognitive fragments, etc.) that reference the user via foreign key. If FK constraints have ON DELETE CASCADE this is fine, but if not, this will leave orphaned records or fail on FK violations.

### P2-8: `_handle_task_completed` in `task_event_consumer.py` does not handle KeyError

**File**: `backend/app/services/task_event_consumer.py:95-96`

```python
user_id = UUID(event["user_id"])
task_id = UUID(event["task_id"])
```
If the event payload is missing `user_id` or `task_id`, this raises `KeyError` which propagates up. Other event handlers in the same file use `event.get("user_id")` with None checks. The inconsistency means a malformed event could crash the consumer loop for this event type.

## Low Issues (P3)

### P3-1: Inconsistent `_utcnow()` helper duplication

Multiple files define their own `_utcnow()`:
- `dashboard_service.py:25-26`
- `error_book_service.py:50-51`
- `notification_service.py:17-18`
- `achievement_event_consumer.py:30-31`
- `galaxy_event_consumer.py:29-30`
- `update_similarities.py:26-27`
- `guest_cleanup.py:18-19`
- `login_attempt_cleanup.py:17-18`

The project already has `app.core.time_utils.utcnow` (used by `state_aggregator/service.py:6`). All these should use the shared utility.

### P3-2: `notification_service.py:508` module-level singleton

```python
notification_service = NotificationService()
```
A module-level singleton `NotificationService()` is created but never used anywhere in the audited files. Static methods are called on the class directly. This is dead code.

### P3-3: `community_checkin_reminder.py` fetches Group per member individually

**File**: `backend/app/tasks/community_checkin_reminder.py:52-53`

```python
group = await db.get(Group, member.group_id)
```
This is inside a loop over `overdue_members`, meaning if 100 members belong to the same group, 100 separate DB queries fetch the same Group object. Should batch group IDs and prefetch.

### P3-4: `accountability_tasks.py` fetches all active partnerships without pagination

**File**: `backend/app/tasks/accountability_tasks.py:375-379`

```python
active_partnerships_query = select(AccountabilityPartnership).where(
    AccountabilityPartnership.status == AccountabilityStatus.ACTIVE
)
result = await db.execute(active_partnerships_query)
partnerships = result.scalars().all()
```
At scale, loading all active partnerships into memory could be problematic. Consider cursor-based processing.

### P3-5: `state_aggregator/service.py` internal cache has no max-size bound

**File**: `backend/app/state_aggregator/service.py:228-231`

```python
if len(self._cache) > 500:
    expired_keys = [k for k, (_, exp) in self._cache.items() if exp <= now]
    for k in expired_keys:
        del self._cache[k]
```
The cache eviction only triggers when size exceeds 500 and only removes expired entries. If all 500 entries are still valid, no eviction occurs and the cache continues to grow. Consider adding an LRU eviction strategy or hard cap.

### P3-6: `error_book_service.py` LLM prompt has raw user input

**File**: `backend/app/services/error_book_service.py:580-597`

The LLM prompt directly interpolates `question`, `user_ans`, and `correct_ans` from user input. While this goes through `llm_client.chat_completion()` which should handle escaping, the raw string interpolation into the prompt template could be a prompt injection vector if the user deliberately crafts malicious input.

## Positive Findings

1. **Consistent async patterns**: All services properly use `async/await` with `AsyncSession`. No blocking calls in async context found.

2. **Robust error isolation**: The `error_book_service.py:analyze_and_link()` method is a good example of defensive programming -- each downstream system (semantic memory, signal processing, mastery sync, event bus) is wrapped in its own try/except so one failure does not block others.

3. **Well-structured SpineOrchestrator**: The signal pipeline has comprehensive audit trails (CausalTrace), governance modules (fabrication guard, safety degradation, high-impact confirmation), and kill-switch integration for every Aurora feature.

4. **Notification preference system**: The multi-layer suppression chain (disabled types -> consecutive ignore backoff -> fatigue protection -> quiet hours) is thorough and well-implemented.

5. **StateAggregatorService**: Clean separation of 20 aggregation dimensions with per-field TTL, kill-switch support (off/shadow/live modes), and proper caching with cache-key fingerprinting for turn-dependent fields.

6. **Type safety**: The `signals/types.py` file defines a comprehensive set of 40+ typed dataclasses with `to_dict()`/`from_dict()` serialization. The `state_aggregator/schema.py` uses frozen dataclasses with proper generics.

7. **ReviewSchedulerService SM-2**: Correct implementation of the SM-2 spaced repetition algorithm with proper EF bounding (1.3-2.5), jitter to prevent review bombing, and mastery update logic.

8. **Kill switch integration**: Both `StateAggregatorService` and `SpineOrchestrator` properly check Aurora kill switches before executing features, with shadow-mode support for testing.

9. **GDPR compliance**: `login_attempt_cleanup.py` implements proper 90-day retention with batch deletion (500 per batch), avoiding long-running transactions.

10. **Dashboard caching**: `dashboard_service.py` properly caches the expensive multi-query dashboard payload with 5-minute TTL.

## Files Audited

### Services
- `backend/app/services/dashboard_service.py`
- `backend/app/services/error_book_service.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/nudge_service.py`
- `backend/app/services/push_scheduler.py`
- `backend/app/services/achievement_event_consumer.py`
- `backend/app/services/galaxy_event_consumer.py`
- `backend/app/services/task_event_consumer.py`
- `backend/app/services/file_processing_orchestrator.py`
- `backend/app/services/fme_l3_closure_bridge.py`

### Signals
- `backend/app/signals/spine_orchestrator.py` (partial -- 800 of ~1200 lines)
- `backend/app/signals/types.py`

### State Aggregator
- `backend/app/state_aggregator/service.py`
- `backend/app/state_aggregator/schema.py`

### Tasks
- `backend/app/tasks/absence_scan_task.py`
- `backend/app/tasks/checkpoint_nudge_task.py`
- `backend/app/tasks/community_checkin_reminder.py`
- `backend/app/tasks/guest_cleanup.py`
- `backend/app/tasks/login_attempt_cleanup.py`
- `backend/app/tasks/accountability_tasks.py`
- `backend/app/tasks/policy_tasks.py`
- `backend/app/tasks/update_similarities.py`
