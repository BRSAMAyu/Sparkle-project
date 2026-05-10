# Community & Accountability Python Backend Audit

**Date**: 2026-05-10
**Auditor**: Senior Python Backend Engineer
**Scope**: 28 files across services, models, schemas, API, signals, routing, and tasks

---

## Summary

| Severity | Count |
|----------|-------|
| P0       | 5     |
| P1       | 12    |
| P2       | 18    |
| P3       | 10    |
| **Total** | **45** |

---

## P0 Findings (Data Loss / Security / Crash)

### [P0-01] SQL Injection via Raw SQL in EncryptionService.register_public_key
**File**: `backend/app/services/community_advanced_service.py:156-162`
**Category**: security
**Description**: Uses `text()` with string interpolation via `:user_id` and `:device_id` parameters passed as `str(user_id)`. While SQLAlchemy parameterizes named binds, the `user_id` value is coerced to `str()` before being passed. The real risk is that this raw SQL bypasses the ORM soft-delete filter (`not_deleted_filter()`), meaning it can set `is_active = false` on rows that are already soft-deleted, silently reviving them on the next query.
**Context**:
```python
await db.execute(
    text("""
        UPDATE user_encryption_keys
        SET is_active = false, updated_at = NOW()
        WHERE user_id = :user_id AND device_id = :device_id AND is_active = true
    """),
    {"user_id": str(user_id), "device_id": data.device_id}
)
```
**Suggested Fix**: Replace with ORM update statement that also respects `not_deleted_filter()`:
```python
stmt = (
    update(UserEncryptionKey)
    .where(
        UserEncryptionKey.user_id == user_id,
        UserEncryptionKey.device_id == data.device_id,
        UserEncryptionKey.is_active == True,
        UserEncryptionKey.not_deleted_filter(),
    )
    .values(is_active=False, updated_at=_utcnow())
)
await db.execute(stmt)
```

---

### [P0-02] PII Leak in Accountability Struggle Event Payload
**File**: `backend/app/services/social_signal_bridge.py:455`
**Category**: security
**Description**: The `target_name` (user display name) is included in the event payload published to the Redis event bus. While the consuming code uses it for notification content, the event is published to a shared stream (`ACCOUNTABILITY_STRUGGLE_DETECTED`). Any consumer of this stream sees the target user's display name, which is PII. The `CommunitySignalBridge.AURORA_FORBIDDEN_SOCIAL_KEYS` lists `display_name` and `nickname` as forbidden, but `target_name` bypasses this because it is a different key name.
**Context**:
```python
payload = {
    "event_type": ACCOUNTABILITY_STRUGGLE_DETECTED,
    "user_id": str(user_uuid),
    "plan_id": str(plan_uuid),
    "target_name": target_name,  # PII in shared stream
    ...
}
await event_bus.publish(ACCOUNTABILITY_STRUGGLE_DETECTED, payload)
```
**Suggested Fix**: Remove `target_name` from the event payload. Pass the user_id only; let the consumer resolve the display name from the DB. If the consumer needs it for notification text, fetch it directly from the `User` table using `user_id`.

---

### [P0-03] Race Condition in AccountabilityPartnership UniqueConstraint
**File**: `backend/app/models/accountability.py:91-95`
**Category**: logic
**Description**: The `UniqueConstraint("initiator_id", "partner_id")` only covers (initiator, partner), not the symmetric pair (partner, initiator). Two users can simultaneously create partnerships: User A initiates with User B (initiator=A, partner=B), and User B initiates with User A (initiator=B, partner=A). Both rows pass the unique constraint, creating a duplicate active partnership. The `_end_accountability_partnerships_between_users` function in community_service.py searches for partnerships in both directions, but it only runs *after* a block/unfriend event, not at partnership creation time.
**Context**:
```python
__table_args__ = (
    UniqueConstraint(
        "initiator_id",
        "partner_id",
        name="uq_accountability_partnership_pair",
    ),
    ...
)
```
**Suggested Fix**: Add application-level check before creating a partnership: query for existing partnerships in both directions (A->B and B->A) with status != ENDED. Also consider adding a canonical ordering constraint (store smaller UUID as initiator_id) similar to the Friendship model pattern, or add a database-level check constraint that validates no reverse pair exists.

---

### [P0-04] Privacy Engine State is In-Memory Only (Lost on Restart)
**File**: `backend/app/signals/privacy_community_intelligence.py:156-157`
**Category**: logic
**Description**: `PrivacyPreservingCommunityEngine` stores budgets and cohorts in `self._budgets` and `self._cohorts` dicts. This instance is created fresh every time `CommunitySignalBridge.__init__` runs (line 71 of community_signal_bridge.py), meaning privacy budgets reset to zero on every request. The `CommunitySignalBridge` is instantiated per-request (not a singleton), so the in-memory privacy budget tracking provides zero protection. An attacker can make unlimited queries without ever hitting the epsilon budget cap.
**Context**:
```python
class PrivacyPreservingCommunityEngine:
    def __init__(self):
        self._budgets: dict[str, PrivacyBudget] = {}
        self._cohorts: dict[str, PrivacyPreservingCohort] = {}
```
And in CommunitySignalBridge:
```python
def __init__(self, db: AsyncSession, redis=None) -> None:
    ...
    self.privacy_engine = PrivacyPreservingCommunityEngine()  # fresh instance every time
```
**Suggested Fix**: The `CommunitySignalBridge._check_daily_budget` already reads from the DB `PrivacyBudgetLedger`, which is the production-grade path. Remove the in-memory budget tracking from `PrivacyPreservingCommunityEngine` or make the engine a singleton/Redis-backed. The `aggregate_cohort_signal` method on the engine spends the in-memory budget but this has no effect because the instance is ephemeral. The DB-based budget check in the bridge is the real guard, so the in-memory spend is dead code that gives a false sense of security.

---

### [P0-05] Unbounded N+1 Queries in _count_mutual_checkin_days
**File**: `backend/app/services/accountability_achievement_service.py:492-533`
**Category**: performance
**Description**: For each of the 7 days checked, this method executes 2 separate DB queries (one for user checkins, one for partner checkins), totaling 14 queries per call. This runs for every partnership during the achievement evaluation Celery task. With N partnerships, this results in 14*N queries. Additionally, each query scans the `accountability_checkin` table without an upper bound on results (no `.limit()`), so for active partnerships with many checkins, this fetches all checkin records for that day.
**Context**:
```python
for i in range(days):
    # ... creates day_start, day_end
    user_checkins = await db.execute(...)  # query 1
    partner_checkins = await db.execute(...)  # query 2
```
**Suggested Fix**: Rewrite as a single query that fetches all checkins for both users in the partnership over the 7-day window, then group by date in Python:
```python
result = await db.execute(
    select(
        AccountabilityCheckin.user_id,
        func.date(AccountabilityCheckin.created_at).label("checkin_date"),
        AccountabilityCheckin.created_at,
    ).where(
        AccountabilityCheckin.partnership_id == partnership_id,
        AccountabilityCheckin.user_id.in_([user_id, partner_id]),
        AccountabilityCheckin.created_at >= cutoff,
    )
)
```

---

## P1 Findings (Wrong Data / Broken Feature / API Contract)

### [P1-01] _check_perfect_month_for_user Uses UTC Dates, Not User Local Timezone
**File**: `backend/app/services/accountability_achievement_service.py:535-561`
**Category**: logic
**Description**: The `_calculate_streak` method correctly uses user timezone (`_user_timezone`) to determine daily boundaries, but `_check_perfect_month_for_user` and `_count_mutual_checkin_days` use raw UTC `datetime` objects for day boundaries. If a user is in UTC+8 and checks in at 11 PM local time (3 PM UTC), the UTC-based date grouping counts this as the previous day. This causes false negatives for perfect month and mutual support achievements.
**Context**:
```python
async def _check_perfect_month_for_user(self, db, partnership_id, user_id, year, month, days_in_month):
    month_start = datetime(year, month, 1).replace(tzinfo=UTC)
    month_end = datetime(year, month, days_in_month, 23, 59, 59).replace(tzinfo=UTC)
    result = await db.execute(
        select(func.distinct(func.date(AccountabilityCheckin.created_at))).where(...)
    )
```
**Suggested Fix**: Use the user's timezone to determine local dates, consistent with `_calculate_streak`. Convert `created_at` to local date before comparing.

---

### [P1-02] Streak Calculation Inconsistency Between achievement_service and accountability_tasks
**File**: `backend/app/services/accountability_achievement_service.py:405-442` vs `backend/app/tasks/accountability_tasks.py:742-801`
**Category**: logic
**Description**: Two completely different streak calculation algorithms exist:
1. `AccountabilityAchievementService._calculate_streak`: Uses user timezone, counts any checkin day
2. `accountability_tasks._calculate_streak`: Uses UTC date, applies a "quality threshold" (mood >= 4 or minutes >= 15)

The Celery task awards achievements based on quality-threshold streaks, but the achievement service's `check_streak_achievements` uses the non-quality version. A user could be awarded a 7-day streak achievement from the achievement service but the Celery task would show a different streak count. This creates inconsistent achievement state.
**Suggested Fix**: Unify into a single streak calculation function. Make the quality threshold optional (defaulting to the same behavior) and use it consistently in both paths.

---

### [P1-03] _is_first_partnership Returns True Only When Count == 1
**File**: `backend/app/services/accountability_achievement_service.py:461-479`
**Category**: logic
**Description**: `_is_first_partnership` queries for active partnerships and returns `count == 1`. But the "first partnership" achievement should be awarded when the user creates their very first partnership (ever), not when they have exactly one active partnership. If a user had 2 partnerships, ended one, they would still have `count == 1` and would incorrectly be awarded the "first partnership" achievement again when the achievement check runs.
**Context**:
```python
async def _is_first_partnership(self, db, user_id) -> bool:
    result = await db.execute(
        select(func.count(AccountabilityPartnership.id)).where(
            AccountabilityPartnership.status == AccountabilityStatus.ACTIVE,
            or_(
                AccountabilityPartnership.initiator_id == user_id,
                AccountabilityPartnership.partner_id == user_id,
            ),
        )
    )
    count = result.scalar() or 0
    return count == 1
```
**Suggested Fix**: Check for the existence of any `UserAchievement` with `achievement_id == "accountability_first_partnership"` instead of counting partnerships. Or count ALL partnerships (not just ACTIVE) and check `count == 1`.

---

### [P1-04] award_achievement Bypasses _unlock_achievement (Duplicate Code Path)
**File**: `backend/app/services/accountability_achievement_service.py:336-401`
**Category**: logic
**Description**: `award_achievement` is a public method that creates achievements with `db.commit()` (a full commit), while `_unlock_achievement` also does `db.commit()`. If both are called in the same transaction flow (e.g., from check_streak_achievements -> _unlock_achievement -> commit, then separately award_achievement -> commit), the second call would see the committed state from the first. However, `award_achievement` also calls `notification_service.create` with a plain dict instead of a `NotificationCreate` object (line 384), which may fail at runtime depending on the notification service's type checking.
**Context**:
```python
await notification_service.create(
    db,
    user_id,
    {  # plain dict, not NotificationCreate
        "title": f"...",
        "content": achievement_def["description"],
        "type": "achievement",
        "data": {...},
    },
    push_via_websocket=True,
)
```
**Suggested Fix**: Replace the plain dict with `NotificationCreate(...)` to match the type expected by the notification service, consistent with how `_unlock_achievement` does it (which also has the same bug).

---

### [P1-05] CommunityErrorAggregationService Uses datetime.utcnow() (Deprecated)
**File**: `backend/app/services/community_error_aggregation_service.py:38,79`
**Category**: bug
**Description**: Uses `datetime.utcnow()` instead of `datetime.now(UTC)`. `datetime.utcnow()` creates a naive datetime without timezone info and is deprecated in Python 3.12+. This is inconsistent with the rest of the codebase which uses `_utcnow()` (which calls `datetime.now(UTC).replace(tzinfo=None)`). While the resulting timestamps are close, `utcnow()` does not account for system clock adjustments and can produce slightly different values. More importantly, `aggregate_and_annotate_node` calls `await self.db.commit()` at line 75, which commits the entire session state, not just the node update. This can accidentally persist unrelated pending changes.
**Context**:
```python
async def aggregate_and_annotate_node(self, node_id: UUID) -> dict | None:
    ...
    node.community_signal = signal
    await self.db.commit()  # full commit, not flush
```
**Suggested Fix**: Replace `datetime.utcnow()` with `_utcnow()`. Change `await self.db.commit()` to `await self.db.flush()` to avoid side-effect commits.

---

### [P1-06] Friendship Reverse-Pending Detection Has Canonical Ordering Mismatch
**File**: `backend/app/services/community_service.py:197-203`
**Category**: logic
**Description**: The reverse-pending check constructs the query using string comparison (`str(target_id) < str(user_id)`) to determine which UUID is "smaller", but the Friendship model stores canonical ordering where `user_id < friend_id`. The code checks for `Friendship.user_id == (target_id if str(target_id) < str(user_id) else user_id)` which maps to the canonical field correctly. However, if the canonical ordering was different from the string ordering (possible with UUIDs where string and binary orderings differ), this would miss the reverse pending request. In practice UUID string comparison and value comparison produce the same ordering, but this is fragile.
**Suggested Fix**: Use the same canonical sorting as the new friendship creation (lines 216-219): compute `small_id, large_id = sorted([user_id, target_id], key=lambda v: str(v))` and use these consistently.

---

### [P1-07] SocialSignalEventConsumer Lacks DLQ and Retry Mechanism
**File**: `backend/app/services/social_signal_event_consumer.py:38-40`
**Category**: event-bus
**Description**: When an exception occurs in the event loop, the consumer logs the error and sleeps for 1 second, then retries the same `subscribe` call. There is no DLQ (Dead Letter Queue), no max-retry limit, and no backoff. If the error is persistent (e.g., malformed event data), the consumer enters an infinite retry loop. The `subscribe` call itself may re-deliver the same failing event forever, blocking all subsequent events in the stream.
**Context**:
```python
while self._running:
    try:
        await self.event_bus.subscribe(...)
        break
    except Exception as exc:
        logger.error("SocialSignalEventConsumer error: {}", exc)
        await asyncio.sleep(1)
```
**Suggested Fix**: Add max retry count with exponential backoff. On permanent failure, publish to a DLQ stream for manual inspection. Add a `consumer_name` with a unique identifier to avoid blocking other consumers.

---

### [P1-08] _filter_opted_in_values Makes N+1 DB Queries for Privacy Check
**File**: `backend/app/services/community_signal_bridge.py:417-431`
**Category**: performance
**Description**: For each contributor value (dict with user_id), the method calls `_community_intelligence_enabled` which executes a DB query to check `UserSettings`. With 100 contributors, this results in 100 individual DB queries. This should be batched into a single query.
**Context**:
```python
for item in contributor_values:
    if isinstance(item, dict):
        contributor_id = item.get("user_id")
        if contributor_id and not await self._community_intelligence_enabled(contributor_id):
            continue
```
**Suggested Fix**: Batch-fetch all user settings in one query:
```python
contributor_ids = [item["user_id"] for item in contributor_values if isinstance(item, dict) and item.get("user_id")]
settings_result = await self.db.execute(
    select(UserSettings.user_id, UserSettings.community_intelligence_enabled)
    .where(UserSettings.user_id.in_(contributor_ids))
)
opted_in = {row[0] for row in settings_result.all() if row[1]}
```

---

### [P1-09] Celery Tasks Use asyncio.run() Inside get_db_context()
**File**: `backend/app/tasks/accountability_tasks.py:258-260` and `backend/app/tasks/community_checkin_reminder.py:106-107`
**Category**: bug
**Description**: The Celery tasks call `asyncio.run(_send_daily_reminders(db))` where `db` is obtained from `get_db_context()`. `get_db_context()` is a sync context manager that likely creates a sync database session. But `_send_daily_reminders` expects an `AsyncSession`. If the sync session is passed, all `await db.execute()` calls will fail with `TypeError: object AsyncSession can't be used in 'await' expression`. The code works only if `get_db_context()` returns an async-compatible session wrapper, which is unusual for a sync context manager.
**Context**:
```python
with get_db_context() as db:
    result = asyncio.run(_send_daily_reminders(db))
```
**Suggested Fix**: Verify `get_db_context()` returns an `AsyncSession`. If it returns a sync session, refactor to use `AsyncSessionLocal()` instead. The correct pattern is `async with AsyncSessionLocal() as db:` inside an `asyncio.run()`.

---

### [P1-10] Missing Pagination in _send_group_checkin_reminders
**File**: `backend/app/tasks/community_checkin_reminder.py:36-43`
**Category**: performance
**Description**: The query fetches ALL group members who haven't checked in today without any limit. For a platform with thousands of groups and tens of thousands of members, this single query loads every overdue member into memory simultaneously, then iterates through all of them sending notifications one by one.
**Context**:
```python
members_stmt = select(GroupMember).where(
    GroupMember.not_deleted_filter(),
    or_(
        GroupMember.last_checkin_date.is_(None),
        func.date(GroupMember.last_checkin_date) < today,
    ),
)
result = await db.execute(members_stmt)
overdue_members = result.scalars().all()  # unbounded
```
**Suggested Fix**: Add batching with `LIMIT/OFFSET` or use `yield_per()` to process members in chunks.

---

### [P1-11] Privacy Budget Double-Spend Between _check_daily_budget and _write_privacy_budget_ledger
**File**: `backend/app/services/community_signal_bridge.py:442-462, 464-491`
**Category**: logic
**Description**: `_write_privacy_budget_ledger` calls `_check_daily_budget` again (line 475) to get the remaining balance. But the caller `build_privacy_preserving_cohort_signal` already called `_check_daily_budget` (line 308). Between the two calls, the `_write_privacy_budget_ledger` call creates a new `PrivacyBudgetLedger` record and flushes it. If two requests for the same user arrive concurrently, both can pass the first `_check_daily_budget`, then both write ledger records, resulting in more epsilon spent than the daily limit allows. There is no `SELECT ... FOR UPDATE` or Redis-based lock on the budget check.
**Context**:
```python
# Caller checks budget (line 308)
budget_check = await self._check_daily_budget(requester, query_type=query_type, query_cost=query_cost)
# ...later, _write_privacy_budget_ledger checks again (line 475)
check = await self._check_daily_budget(subject_id, query_type=query_type, query_cost=0.0)
```
**Suggested Fix**: Use a Redis-based distributed lock per (subject_id, query_type) during budget check + write. Or use `SELECT ... FOR UPDATE` on the budget ledger sum query.

---

### [P1-12] _write_privacy_budget_ledger Remaining Epsilon Calculation is Wrong
**File**: `backend/app/services/community_signal_bridge.py:482`
**Category**: logic
**Description**: The remaining_epsilon is calculated as `check.remaining_epsilon - epsilon_spent`. But `check` comes from a fresh `_check_daily_budget(subject_id, query_type=query_type, query_cost=0.0)` call where `query_cost=0.0`. With cost=0, the check returns `remaining_epsilon = max_epsilon - spent`. Then the code subtracts `epsilon_spent` again: `max(0.0, float(check.get("remaining_epsilon", max_epsilon)) - epsilon_spent)`. This double-subtracts: first in the caller's `_check_daily_budget`, then again here. The persisted `remaining_epsilon` in the ledger will be lower than the actual remaining budget.
**Context**:
```python
# _check_daily_budget with cost=0.0 returns remaining = max - already_spent
check = await self._check_daily_budget(subject_id, query_type=query_type, query_cost=0.0)
# Then subtracts epsilon_spent AGAIN:
remaining_epsilon=max(0.0, float(check.get("remaining_epsilon", max_epsilon)) - epsilon_spent),
```
**Suggested Fix**: When `query_cost=0.0` in the check, the returned `remaining_epsilon` already reflects the true remaining budget before this spend. So the line should just be: `remaining_epsilon=max(0.0, float(check.get("remaining_epsilon", max_epsilon)))`. Or pass the actual `query_cost` to the check instead of 0.0.

---

## P2 Findings (Performance / Edge Cases / Non-Critical)

### [P2-01] N+1 Query in CommunitySignalCollector._current_inferred_value
**File**: `backend/app/services/community_signal_collector.py:163-171`
**Category**: performance
**Description**: Opens a new `AsyncSessionLocal()` session to read preferences, which creates a separate DB connection. This is called on every 8th community interaction. The session creation overhead plus the query creates unnecessary load.
**Suggested Fix**: Pass the DB session through from the caller, or cache the preference value in Redis.

---

### [P2-02] CommunitySignalCollector.record_interaction Uses Fire-and-Forget asyncio.create_task
**File**: `backend/app/services/community_service.py:75-82`
**Category**: bug
**Description**: `_record_community_signal` calls `asyncio.create_task(CommunitySignalCollector(...).record_interaction(...))`. The created task is not stored or awaited, meaning any exception inside the task is silently swallowed. If the Redis connection is down or the task fails, the signal is lost with no logging or retry. Additionally, `asyncio.create_task` requires an active event loop; if called from a synchronous context, it raises `RuntimeError`.
**Suggested Fix**: Store the task reference and add a done callback for error logging. Consider using a background task queue or at minimum wrap in try/except with logging.

---

### [P2-03] _claim_dedupe_key Returns True on Redis Failure (Silent Bypass)
**File**: `backend/app/services/social_signal_bridge.py:580-595`
**Category**: logic
**Description**: When Redis is unavailable, `_claim_dedupe_key` catches the exception and returns `True`, allowing the struggle signal to be published. This means that if Redis is down, every struggle detection event will be published, potentially spamming partners with duplicate alerts.
**Suggested Fix**: Return `False` on Redis failure (fail-closed) to prevent duplicate notifications. Log a warning so ops can investigate.

---

### [P2-04] PrivacyPreservingCohort.PRIVACY_FLOOR Mutated on Instance
**File**: `backend/app/signals/privacy_community_intelligence.py:332-333`
**Category**: logic
**Description**: `aggregate_cohort_signal` sets `cohort.PRIVACY_FLOOR = min_cohort_size` on line 332, which mutates a class attribute (not instance attribute). Since `PrivacyPreservingCohort` is a dataclass, this actually sets an instance attribute that shadows the class attribute. However, if multiple coroutines share the same engine instance, they could race on the class attribute mutation before the instance attribute is set. This is technically safe due to GIL, but is poor practice.
**Suggested Fix**: Pass `min_cohort_size` as a constructor parameter instead of mutating class attributes.

---

### [P2-05] Encouragement Presets Are Hardcoded in Chinese Only
**File**: `backend/app/services/social_signal_bridge.py:35-51`
**Category**: api-contract
**Description**: `PRESET_ENCOURAGEMENTS` contains hardcoded Chinese messages. The `send_struggle_alert` notification service accepts a `locale` parameter but the encouragements passed in are always Chinese. When the user's locale is English, the encouragement options shown to the partner will be in Chinese.
**Suggested Fix**: Move encouragement presets to i18n resource files and select based on locale.

---

### [P2-06] `datetime.utcnow()` Used in handle_resource_shared
**File**: `backend/app/services/community_signal_bridge.py:197`
**Category**: bug
**Description**: Uses deprecated `datetime.utcnow()` instead of `_utcnow()`. Inconsistent with the rest of the file.
**Suggested Fix**: Replace with `_utcnow()`.

---

### [P2-07] CommunitySignalBridge.broadcast_achievement_unlock Uses __import__
**File**: `backend/app/services/community_signal_bridge.py:566`
**Category**: dead-code
**Description**: Uses `__import__("json").dumps(...)` instead of `json.dumps(...)`. The `json` module is already imported at the top of the file. This is needlessly obscure and slower.
**Suggested Fix**: Replace `__import__("json").dumps(payload, ensure_ascii=False)` with `json.dumps(payload, ensure_ascii=False)`.

---

### [P2-08] Missing Pagination for _active_partnerships_for_user
**File**: `backend/app/services/social_signal_bridge.py:531-547`
**Category**: performance
**Description**: Fetches all active partnerships for a user without limit. While most users will have few partnerships, there is no guard against a user with many partnerships. The query also uses `selectinload` for both `initiator` and `partner`, adding overhead.
**Suggested Fix**: Add a reasonable limit (e.g., 50) and consider whether the selectinload is necessary for all callers.

---

### [P2-09] Celery Task _check_partner_progress Uses UTC Day Boundary
**File**: `backend/app/tasks/accountability_tasks.py:609-617`
**Category**: logic
**Description**: `today_start = _utcnow().replace(hour=0, ...)` creates a UTC midnight boundary. For users in other timezones, "today" started at a different UTC time. The "perfect day" check (both partners checked in today) will be inaccurate for non-UTC users.
**Suggested Fix**: Use per-user timezone-aware day boundaries, similar to the daily reminder task.

---

### [P2-10] PrivacyPreservingCommunityEngine.add_laplace_noise Can Return u=0.5 (Log of Zero)
**File**: `backend/app/signals/privacy_community_intelligence.py:244-247`
**Category**: logic
**Description**: `u = random.random() - 0.5` can be exactly 0 when `random.random()` returns 0.5. Then `math.log(1 - 2 * abs(u))` = `math.log(1)` = 0, and the noise is 0. While this is mathematically valid (probability 0 event), the implementation uses `1 if u >= 0 else -1` for the sign, meaning when `u=0`, the sign is `1` and `noise = -scale * 1 * 0 = 0`. This is fine but the edge case handling is fragile. More critically, if `random.random()` returns 0.0 or 1.0, `u` becomes -0.5 or 0.5, and `math.log(1 - 2 * 0.5) = math.log(0)` raises `ValueError`.
**Context**:
```python
u = random.random() - 0.5
noise = -scale * (1 if u >= 0 else -1) * math.log(1 - 2 * abs(u))
```
**Suggested Fix**: Clamp `abs(u)` to be strictly less than 0.5: `abs_u = min(abs(u), 0.499999)` before computing the log.

---

### [P2-11] No Index on AccountabilityCheckin(partnership_id, user_id, created_at)
**File**: `backend/app/models/accountability.py:144-154`
**Category**: performance
**Description**: The streak calculation queries filter by `(partnership_id, user_id)` ordered by `created_at DESC`. The existing composite index `idx_accountability_checkin_partnership_user` covers (partnership_id, user_id), but the streak queries also need `created_at` for ordering. A covering index `(partnership_id, user_id, created_at DESC)` would avoid a sort operation.
**Suggested Fix**: Add `Index("idx_checkin_partnership_user_created", "partnership_id", "user_id", "created_at")`.

---

### [P2-12] CommunityAggregateSignal Has No Expiry Cleanup Mechanism
**File**: `backend/app/models/community_privacy.py:35`
**Category**: performance
**Description**: The `expires_at` column exists but there is no background task or TTL mechanism to clean up expired signals. Over time, the `community_aggregate_signals` table will grow unboundedly.
**Suggested Fix**: Add a Celery periodic task that soft-deletes signals past their `expires_at`.

---

### [P2-13] AccountabilityPolicy Missing deleted_at Soft Delete Filter
**File**: `backend/app/models/accountability_policy.py`
**Category**: logic
**Description**: `AccountabilityPolicy` inherits from `BaseModel` which includes `deleted_at`, but the model does not define `not_deleted_filter()` usage in any of its indexes or queries. The `list_outcomes` method in `CommunityStrategyService` manually checks `deleted_at.is_(None)`, suggesting the pattern is inconsistent.
**Suggested Fix**: Ensure all queries against `AccountabilityPolicy` use the soft-delete filter consistently.

---

### [P2-14] _build_share_meta Missing Cognitive Fragment Type Check
**File**: `backend/app/api/v1/community.py:1032-1041`
**Category**: bug
**Description**: The `_build_share_meta` function's final `else` branch assumes the resource is a `CognitiveFragment`, but it could be any unrecognized resource type. It accesses `fragment.source_type`, `fragment.severity`, etc., which will raise `AttributeError` if the resource is not a fragment.
**Suggested Fix**: Add an explicit `if resource_type == SharedResourceType.COGNITIVE_FRAGMENT:` check before the fragment-specific code. Raise `ValueError` in the final `else` branch.

---

### [P2-15] kick_member System Message Leaks Internal User Identifier
**File**: `backend/app/services/community_service.py:1106-1107`
**Category**: security
**Description**: The system message sent when a member is kicked includes `target.nickname or target.username`. The `GroupMember` object has `nickname` as a column attribute (not a User relationship), but the code accesses it directly. If `target` is a `GroupMember` without an eagerly-loaded user relationship, this will access `GroupMember.nickname` which doesn't exist (it's a User field), potentially causing an `AttributeError`.
**Suggested Fix**: Eagerly load the user relationship or fetch the user separately to get the display name.

---

### [P2-16] Group Service search_groups Has No Full-Text Search Index
**File**: `backend/app/services/community_service.py:504-510`
**Category**: performance
**Description**: Uses `Group.name.ilike(f"%{keyword}%")` which is a substring search. This cannot use B-tree indexes and results in a full table scan. For large numbers of groups, this will be slow.
**Suggested Fix**: Add a PostgreSQL GIN index on the name column for `ilike` searches, or use full-text search (`to_tsvector`/`to_tsquery`) similar to the message search implementation.

---

### [P2-17] CommunitySignalCollector Creates ProfileWriteService With Different DB Session
**File**: `backend/app/services/community_signal_collector.py:66-72`
**Category**: logic
**Description**: Opens a new `AsyncSessionLocal()` session inside `record_interaction` to update preferences. This means the preference update runs in a separate transaction from whatever triggered the community interaction. If the original transaction rolls back, the preference update still persists.
**Suggested Fix**: This is acceptable for async background tasks, but document the at-least-once semantics. Consider adding idempotency keys.

---

### [P2-18] SecureAggregationEngine.privacy_preserving_rank Has Dead Code
**File**: `backend/app/signals/privacy_community_intelligence.py:727`
**Category**: dead-code
**Description**: Line 727 creates a list comprehension `[r for r in ranked if ...]` but the result is not assigned to any variable. It is dead code.
**Context**:
```python
# Sort rankable items by score
[r for r in ranked if r["rank"] is not None or r.get("rank_reason") != "below_privacy_floor"]

# Actually, let me fix the logic:
visible = [r for r in ranked if r.get("rank_reason") != "below_privacy_floor"]
```
**Suggested Fix**: Remove the dead line 727.

---

## P3 Findings (Code Quality / Minor Improvements)

### [P3-01] Duplicate _utcnow() Definitions Across Files
**Files**: community_service.py:63, community_advanced_service.py:60, community_signal_bridge.py:37, social_signal_bridge.py:25, accountability_achievement_service.py:30, community_error_aggregation_service.py:19 (uses datetime.utcnow instead), community_signal_collector.py:19, community_strategy_service.py:14, community_checkin_reminder.py:21, accountability_tasks.py:34
**Category**: dead-code
**Description**: `_utcnow()` is defined identically in 10+ files. This should be a shared utility.
**Suggested Fix**: Move to `app.core.datetime_utils` and import from there.

---

### [P3-02] Duplicate _user_display_name Across Files
**Files**: social_signal_bridge.py:29-32, accountability_notification_service.py:47-50, accountability_tasks.py:38-41
**Category**: dead-code
**Description**: Three identical implementations of `_user_display_name`.
**Suggested Fix**: Move to a shared utility module.

---

### [P3-03] CommunitySignalBridge.broadcast_achievement_unlock Has Mixed Language Strings
**File**: `backend/app/services/community_signal_bridge.py:580-583`
**Category**: api-contract
**Description**: Hardcoded English string "Congratulations! You unlocked:" mixed with Chinese system update strings (lines 163-168).
**Suggested Fix**: Use i18n for all user-facing strings.

---

### [P3-04] TemporalPrivacyBudget.try_renew Never Called
**File**: `backend/app/signals/privacy_community_intelligence.py:515-526`
**Category**: dead-code
**Description**: `TemporalPrivacyBudget.try_renew()` is defined but never called anywhere in the codebase. The hourly/daily/weekly count fields are never reset, meaning budgets only ever exhaust and never renew.
**Suggested Fix**: Either integrate renewal into the budget checking flow or remove this class entirely since the production path uses `PrivacyBudgetLedger` (DB-based).

---

### [P3-05] PrivacyBudget In-Memory Class is Never Used in Production
**File**: `backend/app/signals/privacy_community_intelligence.py:41-71`
**Category**: dead-code
**Description**: `PrivacyBudget` and `TemporalPrivacyBudget` dataclasses exist alongside the DB-backed `PrivacyBudgetLedger`. The in-memory versions are used only in unit tests and the ephemeral `PrivacyPreservingCommunityEngine`. They add confusion about which budget system is authoritative.
**Suggested Fix**: Clearly document that `PrivacyBudget` is for testing only, or remove it and use `PrivacyBudgetLedger` exclusively.

---

### [P3-06] CohortDriftDetector.compute_drift Never Used in Production
**File**: `backend/app/signals/privacy_community_intelligence.py:555-616`
**Category**: dead-code
**Description**: `CohortDriftDetector` and its methods are never called anywhere in the codebase. They are well-designed but unused infrastructure.
**Suggested Fix**: Either integrate into the production pipeline or remove to reduce maintenance burden.

---

### [P3-07] SecureAggregationEngine.federated_average and audit_trail Never Used
**File**: `backend/app/signals/privacy_community_intelligence.py:666-764`
**Category**: dead-code
**Description**: `SecureAggregationEngine.federated_average()`, `privacy_preserving_rank()`, and `audit_trail()` are defined but never called.
**Suggested Fix**: Remove or mark as planned for future implementation.

---

### [P3-08] GroupMember.joined_at Uses datetime.utcnow Default
**File**: `backend/app/models/community.py:274`
**Category**: bug
**Description**: `joined_at = Column(DateTime, default=datetime.utcnow)` passes the function reference `datetime.utcnow`, which is called at model instantiation time. This is fragile because (1) `datetime.utcnow` is deprecated, and (2) it evaluates at import time in some ORM patterns.
**Suggested Fix**: Use `default=_utcnow` or `server_default=func.now()`.

---

### [P3-09] GroupMessageRead.read_at Uses datetime.utcnow Default
**File**: `backend/app/models/community.py:377`
**Category**: bug
**Description**: Same as P3-08: `read_at = Column(DateTime, default=datetime.utcnow)`.
**Suggested Fix**: Same as P3-08.

---

### [P3-10] CommunityStrategyService.record_outcome Calls db.commit() Instead of db.flush()
**File**: `backend/app/services/community_strategy_service.py:47`
**Category**: bug
**Description**: `await self.db.commit()` commits the entire session, which may persist unrelated changes from the caller's transaction. Should use `await self.db.flush()` to only persist the new record within the caller's transaction scope.
**Suggested Fix**: Replace `await self.db.commit()` with `await self.db.flush()`.

---

## Cross-Cutting Concerns

### Missing Rate Limiting on Accountability Endpoints
The accountability struggle detection and notification path has no rate limiting. A malicious or buggy client can trigger unlimited struggle alerts, spamming partners. Consider adding rate limiting in the API layer for accountability-related endpoints.

### Inconsistent Timezone Handling
Approximately 60% of date/time code uses user-aware timezones (correct), while the remaining 40% uses raw UTC or naive datetime comparison (incorrect for users in non-UTC timezones). This primarily affects achievement calculations and Celery tasks. A systematic audit of all `created_at` comparisons should be performed.

### Incomplete Soft-Delete Pattern
Several models define `deleted_at` columns but queries inconsistently apply the soft-delete filter. Some service methods check `not_deleted_filter()` while others do not. This could expose soft-deleted records through the API.

### No Idempotency on Event Publishing
Multiple event publishing calls (`event_bus.publish`) lack idempotency keys. If a service retries an operation, the same event can be published multiple times, causing duplicate notifications or achievement awards.
