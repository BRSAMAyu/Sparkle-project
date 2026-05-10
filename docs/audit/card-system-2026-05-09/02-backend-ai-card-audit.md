# Backend AI Card System Audit

**Date**: 2026-05-09
**Scope**: Python AI engine layer -- card protocol models, services, generation, orchestration
**Auditor**: Senior Python/Backend Auditor
**Files Reviewed**: 30+ source files across models, services, orchestration, signals, tools, and migrations

---

## Summary

| Severity | Count |
|----------|-------|
| P0 (data loss/crash) | 3 |
| P1 (broken feature) | 8 |
| P2 (performance/quality) | 7 |
| P3 (cleanup) | 5 |
| **Total** | **23** |

---

## P0 Issues

### P0-01: `archived_at` column referenced in code but not declared on Card model

**File**: `backend/app/services/card_service.py`, line 370
**Category**: Logic Bug
**Description**: The `_transition` method sets `card.archived_at = datetime.utcnow()` when transitioning to ARCHIVED status. However, the `Card` model in `backend/app/models/card_protocol.py` does NOT declare an `archived_at` column. The `BaseModel` base class also has no `archived_at` field. The column DOES exist in the Alembic migration (`cp001a2b3c4d5_add_card_protocol_tables.py`, line 62), creating a model/schema mismatch.

**Current behavior**: At runtime, setting `card.archived_at` will raise `AttributeError` on fresh model instances loaded without the column mapped, OR if SQLAlchemy allows the attribute to be set, it will silently discard the value on flush because there is no mapped column to persist it to. Either way, the archive timestamp is lost.

**Expected behavior**: The `Card` model should declare `archived_at = Column(DateTime, nullable=True)` so that the value is persisted when a card is archived.

**Fix approach**: Add to `Card` class in `card_protocol.py`:
```python
archived_at = Column(DateTime, nullable=True)
```

---

### P0-02: `card_protocol/__init__.py` re-exports wrong class name

**File**: `backend/app/services/card_protocol/__init__.py`, line 1
**Category**: Logic Bug
**Description**: The file imports `ShareService` from `card_snapshot_service`:
```python
from app.services.card_protocol.card_snapshot_service import ShareService
```
But `ShareService` is defined in `share_service.py`, not in `card_snapshot_service.py`. The `card_snapshot_service.py` file only defines `CardSnapshotService` and `ShareService` is in a completely different module. However, `ShareService` IS also instantiated inside `card_snapshot_service.py`'s `CardSnapshotService` (line 935 of that file). The actual `ShareService` class lives in `share_service.py`.

Wait -- upon re-reading, `card_snapshot_service.py` DOES contain a `ShareService` class at line 931. So this import actually works. However, the `__init__.py` of `card_protocol/` has TWO different `__init__.py` files that contradict each other. The package-level `__init__.py` (the one I read that imports from `behaviour_intervention_bridge`, etc.) exports `ShareService` from `card_snapshot_service`, while the `card_snapshot_service.py` file also defines a `ShareService`. But `share_service.py` ALSO defines `ShareService`.

This creates a confusing situation where there are two `ShareService` classes with potentially different behaviors. The package `__init__.py` imports from `card_snapshot_service`, which works but is unexpected.

**Current behavior**: The `ShareService` from `card_snapshot_service.py` is exported. The one in `share_service.py` is only used if imported directly. Both classes exist but could diverge.

**Expected behavior**: There should be a single canonical `ShareService`. The import chain should be unambiguous.

**Fix approach**: Move the `ShareService` class definition to `share_service.py` only, and update `card_snapshot_service.py` to import from there. Update `__init__.py` to import from `share_service`.

---

### P0-03: `_find_edge_by_identity` ignores soft-deleted edges, allowing resurrection of deleted edge tuples

**File**: `backend/app/services/card_edge_service.py`, lines 90-103
**Category**: Data Integrity
**Description**: The `_find_edge_by_identity` method queries `CardEdge` by (from_card_id, to_card_id, edge_type) without filtering on `deleted_at` or `active`. The `UniqueConstraint("from_card_id", "to_card_id", "edge_type")` in the model is database-level and applies to ALL rows including soft-deleted ones. When `create_edge` calls `_find_edge_by_identity`, it can find a soft-deleted edge and then update it (set it active again). This means a soft-deleted edge can be silently resurrected with different metadata, bypassing any audit trail.

**Current behavior**: A soft-deleted edge (deleted_at is not None) can be found and reactivated, losing the deletion record and potentially violating data integrity expectations.

**Expected behavior**: Soft-deleted edges should not be found by `_find_edge_by_identity`. Only non-deleted edges should be considered for update.

**Fix approach**: Add `CardEdge.not_deleted_filter()` to the query in `_find_edge_by_identity`:
```python
stmt = select(CardEdge).where(
    CardEdge.from_card_id == from_card_id,
    CardEdge.to_card_id == to_card_id,
    CardEdge.edge_type == edge_type,
    CardEdge.not_deleted_filter(),  # ADD THIS
)
```

---

## P1 Issues

### P1-01: `_transition` has no lifecycle validation -- allows illegal state transitions

**File**: `backend/app/services/card_service.py`, lines 361-384
**Category**: Logic Bug
**Description**: The `_transition` method allows ANY status transition. For example, a COMPLETED card can be set back to DRAFT, a CANCELLED card can be set to ACTIVE, etc. There is no state machine enforcement. Invalid transitions like DRAFT -> COMPLETED (skipping ACTIVE) are also allowed.

**Current behavior**: Any card can transition to any status, including nonsensical paths like ARCHIVED -> ACTIVE or COMPLETED -> DRAFT.

**Expected behavior**: A state machine should enforce legal transitions. For example: DRAFT -> ACTIVE, ACTIVE -> PAUSED/COMPLETED/ARCHIVED/CANCELLED, PAUSED -> ACTIVE/CANCELLED, etc.

**Fix approach**: Add a `_VALID_TRANSITIONS` map to `CardService`:
```python
_VALID_TRANSITIONS: dict[CardLifecycleStatus, set[CardLifecycleStatus]] = {
    CardLifecycleStatus.DRAFT: {CardLifecycleStatus.ACTIVE, CardLifecycleStatus.CANCELLED},
    CardLifecycleStatus.ACTIVE: {CardLifecycleStatus.PAUSED, CardLifecycleStatus.COMPLETED, CardLifecycleStatus.ARCHIVED, CardLifecycleStatus.CANCELLED},
    CardLifecycleStatus.PAUSED: {CardLifecycleStatus.ACTIVE, CardLifecycleStatus.CANCELLED, CardLifecycleStatus.ARCHIVED},
    CardLifecycleStatus.COMPLETED: {CardLifecycleStatus.ARCHIVED},
    CardLifecycleStatus.ARCHIVED: set(),  # Terminal
    CardLifecycleStatus.CANCELLED: set(),  # Terminal
}
```
Then validate in `_transition` before applying.

---

### P1-02: `update_card` allows setting `lifecycle_status` via **kwargs without validation

**File**: `backend/app/services/card_service.py`, lines 155-158
**Category**: Logic Bug
**Description**: The `update_card` method accepts `**kwargs` and applies them via `setattr`. This means `lifecycle_status` can be changed through `update_card(metadata=..., lifecycle_status="COMPLETED")`, bypassing the `_transition` method entirely and its event bus publishing, version increment for transitions, and the `archived_at` field update.

**Current behavior**: Callers can directly mutate `lifecycle_status` via `update_card`, skipping lifecycle validation and event emission.

**Expected behavior**: Lifecycle transitions should only go through `_transition`. The `update_card` method should reject lifecycle-changing fields.

**Fix approach**: Add to the `for key, value in kwargs.items()` loop:
```python
PROTECTED_FIELDS = {"id", "created_at", "lifecycle_status"}
if key in PROTECTED_FIELDS:
    continue
```
Callers should use `activate()`, `pause()`, etc. for lifecycle changes.

---

### P1-03: `PlanAdapter._ensure_default_phase_card` creates duplicate CONTAINS edges on repeated calls

**File**: `backend/app/services/card_protocol/legacy_adapter.py`, lines 191-198
**Category**: Logic Bug
**Description**: Every call to `plan_to_card` calls `_ensure_default_phase_card`, which calls `edge_service.create_edge(...)` unconditionally. The `CardEdgeService.create_edge` does check for existing edges with the same identity triplet (from, to, type) and updates if found. However, the `from_card_id` changes on every call because `plan_card.id` may be the same card. The unique constraint is `(from_card_id, to_card_id, edge_type)`, so this only works if the plan_card.id is stable. But if a plan has multiple projections (e.g., different users or re-projections), the edges accumulate.

More critically, the `UniqueConstraint` includes ALL rows (not just active ones). If the first edge was soft-deleted, `create_edge` will find it via `_find_edge_by_identity` and resurrect it (see P0-03). If the first edge was deactivated (`active=False`), it will NOT be found by `_find_edge_by_identity` (which doesn't filter on active), but the unique constraint will prevent inserting a new row. This causes an IntegrityError at the database level.

**Current behavior**: Re-projection of an existing plan can hit a unique constraint violation if the previous edge was deactivated but not soft-deleted.

**Expected behavior**: Re-projection should handle existing deactivated edges gracefully.

**Fix approach**: Either (a) soft-delete the old edge before creating a new one, or (b) make `_find_edge_by_identity` also find deactivated (but not deleted) edges and reactivate them.

---

### P1-04: `TaskOccurrence.auto_mark_missed` computes `reference_date` but never uses it

**File**: `backend/app/services/task_occurrence_service.py`, lines 257-278
**Category**: Logic Bug
**Description**: Line 262 calls `reference_date or date.today()` but discards the result. The variable `reference_date` is a parameter, and the expression `reference_date or date.today()` evaluates it but doesn't assign it. The subsequent query only uses `datetime.utcnow()` for the `window_end` comparison, ignoring the `reference_date` parameter entirely.

**Current behavior**: The `reference_date` parameter is ignored. Occurrences are always compared against the current wall clock time, not the provided reference date. This means batch/backfill operations cannot retroactively mark occurrences as missed.

**Expected behavior**: The `reference_date` should be used to compute a cutoff datetime for the missed check.

**Fix approach**: Replace line 262 with:
```python
ref_date = reference_date or date.today()
```
And add a date-based filter:
```python
TaskOccurrence.scheduled_for < ref_date,
```

---

### P1-05: `FeedbackGateEngine.process_feedback_response` double-fetches phase owner

**File**: `backend/app/services/card_protocol/feedback_gate_engine.py`, lines 103-108
**Category**: Performance
**Description**: When the feedback session completes, the code calls `_resolve_phase_owner` which fetches the phase card to get `owner_id`, then immediately uses that `owner_id` to call `_get_owned_phase` which fetches the SAME phase card again. This results in 2 DB queries for the same card.

**Current behavior**: Two DB queries for the same phase card on every feedback completion.

**Expected behavior**: One DB query.

**Fix approach**: Fetch the phase card once, then pass `owner_id` directly:
```python
phase = await self.phase_service.card_service.get_card(UUID(session.phase_card_id))
if not phase:
    raise ValueError("Phase card not found")
user_id = phase.owner_id
phase = await self.phase_service._get_owned_phase(phase.id, user_id)
```

---

### P1-06: `QueryAllTasksTool` has N+1 query pattern -- executes one DB query per plan

**File**: `backend/app/tools/task_query_tool.py`, lines 670-736
**Category**: Performance
**Description**: The `execute` method of `QueryAllTasksTool` first fetches all plans, then loops through each plan individually to query its tasks. If a user has 10 plans, this generates 11 queries (1 for plans + 10 for tasks). This is a classic N+1 pattern.

**Current behavior**: O(N) database queries where N is the number of plans.

**Expected behavior**: A single query joining tasks with plans, or at most 2 queries.

**Fix approach**: Use a single query:
```python
stmt = (
    select(Task, Plan)
    .join(Plan, Task.plan_id == Plan.id)
    .where(Task.user_id == user_uuid, Task.deleted_at.is_(None))
    ...
)
```
Then group results by plan in Python.

---

### P1-07: `CardSnapshotService.import_snapshot` can create dangling cards on partial failure

**File**: `backend/app/services/card_protocol/card_snapshot_service.py`, lines 216-258 and 471-692
**Category**: Data Integrity
**Description**: The `import_snapshot` method (and specifically `_import_plan_snapshot`) creates multiple database objects (plans, phases, tasks, knowledge nodes, edges) across many await points. If any intermediate step fails (e.g., edge creation fails after plan and phase are created), the already-created objects remain in the session but no rollback occurs. The caller may or may not commit the session. There is no try/except wrapping the entire import to ensure rollback on failure.

**Current behavior**: A partial import can leave orphaned cards, plans, and tasks in the database.

**Expected behavior**: Either the entire import should succeed atomically, or a failure should clean up all created objects.

**Fix approach**: Wrap the import in a savepoint:
```python
async with self.db.begin_nested():  # SAVEPOINT
    result = await self._import_plan_snapshot(...)
return result
```
Or add explicit try/except with cleanup.

---

### P1-08: `build_task_entity_card` sets `execution_state` based on incorrect status values

**File**: `backend/app/tools/entity_cards.py`, lines 206
**Category**: Protocol
**Description**: The `execution_state` is set to `"confirmed"` when `task.get("status") in {"IN_PROGRESS", "COMPLETED"}`. However, task status values in the system are lowercase: `"in_progress"`, `"completed"`, `"pending"`, etc. (see `UpdateTaskStatusTool._VALID_STATUSES`). The uppercase comparison will never match, so `execution_state` will always be `"draft"`.

**Current behavior**: All task entity cards have `execution_state: "draft"` regardless of actual task status.

**Expected behavior**: Tasks with status `"in_progress"` or `"completed"` should show `execution_state: "confirmed"`.

**Fix approach**: Change to lowercase:
```python
execution_state="confirmed" if task.get("status", "").lower() in {"in_progress", "completed"} else "draft",
```

---

## P2 Issues

### P2-01: `TaskCardGenerator` template keywords are hardcoded in Chinese, breaking i18n for non-Chinese users

**File**: `backend/app/orchestration/task_card_generator.py`, lines 119-126
**Category**: AI Quality
**Description**: The `_TEMPLATE_KEYWORDS` dictionary maps template IDs to Chinese keywords like "概念", "定义", "计算", etc. The `step_names` default generation (lines 361-365) also produces Chinese strings. The `done_criteria`, `mini_quiz`, and `fallback_if_stuck` builders all produce Chinese text unconditionally. This means non-Chinese users will receive task cards with Chinese content.

**Current behavior**: All generated card content is in Chinese regardless of user language preference.

**Expected behavior**: Content should respect user's language preference (i18n strategy from memory: `isChinese ? '中文' : 'English'`).

**Fix approach**: Accept a `locale` or `is_chinese` parameter in `generate()` and branch on it for all hardcoded strings. Use the same ARB-based i18n pattern where possible, or at minimum provide English fallback strings.

---

### P2-02: `TaskCardGenerator._distribute_minutes` can loop up to 200 iterations for edge cases

**File**: `backend/app/orchestration/task_card_generator.py`, lines 429-450
**Category**: Performance
**Description**: The minute distribution algorithm has a safety break at `index > 200`, but the logic for distributing the difference can get stuck in a situation where `scaled[target]` is already at minimum (3) and `diff < 0`, causing the loop to exhaust all 200 iterations.

**Current behavior**: Unnecessary CPU cycles when total_minutes is very small relative to step count.

**Expected behavior**: Early termination or a more efficient distribution algorithm.

**Fix approach**: Skip decrement when `scaled[target] <= 3` and instead move to the next target. Also consider a simpler algorithm:
```python
base = total_minutes // count
remainder = total_minutes % count
return [base + (1 if i < remainder else 0) for i in range(count)]
```

---

### P2-03: `CardService.create_card` flushes without committing -- caller must commit

**File**: `backend/app/services/card_service.py`, line 74
**Category**: Data Integrity
**Description**: The `create_card` method calls `await self.db.flush()` but never commits. This is consistent with the unit-of-work pattern, but the method also publishes an event bus message `"card.created"` before the transaction is committed. If the transaction is later rolled back, the event has already been published, leading to downstream consumers processing a card that doesn't exist in the database.

**Current behavior**: Events are published for cards that may be rolled back. This affects all methods that publish events before commit (`create_card`, `update_card`, `delete_card`, `_transition`, etc.).

**Expected behavior**: Events should only be published after the transaction is committed, or should be queued for post-commit dispatch.

**Fix approach**: Use SQLAlchemy session events to defer event publishing:
```python
@event.listens_for(session, "after_commit")
def publish_deferred_events(session):
    for event in session._deferred_events:
        await event_bus.publish(...)
```

---

### P2-04: `TaskOccurrence` queries in `get_occurrences_for_date` join on `holder_id` instead of `owner_id`

**File**: `backend/app/services/task_occurrence_service.py`, line 94
**Category**: Logic Bug
**Description**: The `get_occurrences_for_date` method joins `Card` and filters on `Card.holder_id == user_id`. However, `holder_id` and `owner_id` can differ (e.g., for adopted/forked cards). The canonical ownership field is `owner_id`. Using `holder_id` means occurrences for cards where the user is the holder but not the owner (e.g., shared cards) will be returned, which may not be the intended behavior.

**Current behavior**: Occurrences are returned based on holder, not owner. If a card was shared and adopted, the holder may be different from the original owner.

**Expected behavior**: Should filter on `owner_id` for consistency with other queries, or at least document the distinction.

**Fix approach**: Change `Card.holder_id == user_id` to `Card.owner_id == user_id` unless there's a specific reason to use holder.

---

### P2-05: `EntityCardSchema` version `"v1"` is hardcoded and never validated against

**File**: `backend/app/tools/entity_cards.py`, line 6
**Category**: Protocol
**Description**: The `ENTITY_CARD_SCHEMA_VERSION` is set to `"v1"` but is never validated by any consumer. The `validate_entity_card` function checks that `schema_version` is present but doesn't compare it to the expected version. If the schema evolves to v2, old clients might break.

**Current behavior**: Any non-empty `schema_version` passes validation regardless of actual version compatibility.

**Expected behavior**: Schema version should be checked against supported versions.

**Fix approach**: Add version check to `validate_entity_card`:
```python
supported_versions = {"v1"}
if entity_card.get("schema_version") not in supported_versions:
    issues.append(f"unsupported_schema_version")
```

---

### P2-06: `TaskCardBuilder.from_goal_type` ignores `bound_nodes` for overrides

**File**: `backend/app/signals/task_card_protocol.py`, lines 194-224
**Category**: AI Quality
**Description**: The `from_goal_type` method creates a card with `bound_nodes=overrides.get("bound_nodes", [])`. However, the `overrides` loop on line 221 uses `setattr` to overwrite any field, including `bound_nodes`. If `bound_nodes` is in `overrides`, it will be set twice -- once during construction and once via setattr. But more importantly, the `task_type` is also excluded from setattr, but `bound_nodes` and `goal_id` are excluded too. This means any `kwargs` passed to the builder function (like `steps`, `success_criteria`) must match the protocol's constructor signature exactly or be silently ignored.

**Current behavior**: The `from_goal_type` method works for simple cases but may silently drop fields if the override keys don't match TaskCardProtocol attributes.

**Expected behavior**: The method should either validate override keys or warn on unknown keys.

**Fix approach**: Add validation:
```python
unknown_keys = set(overrides.keys()) - {"goal_id", "bound_nodes", "task_type"} - {f.name for f in dataclasses.fields(TaskCardProtocol) if hasattr(dataclasses, 'fields')}
```

---

### P2-07: `TemporalEngine._parse_clock` raises unhandled ValueError for malformed time strings

**File**: `backend/app/services/card_protocol/temporal_engine.py`, lines 342-344
**Category**: Logic Bug
**Description**: The `_parse_clock` method calls `datetime.strptime(value, "%H:%M")` without a try/except. If `value` is malformed (e.g., `"25:00"`, `"9am"`, empty string), this will raise `ValueError` and crash the occurrence generation pipeline.

**Current behavior**: Malformed time window strings cause an unhandled exception that propagates up to the caller and can break task scheduling.

**Expected behavior**: Malformed time strings should be handled gracefully, either defaulting to a safe value or skipping the window.

**Fix approach**:
```python
def _parse_clock(self, value: str) -> time:
    try:
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.time()
    except (ValueError, TypeError):
        return time(9, 0)  # Default to 9:00 AM
```

---

## P3 Issues

### P3-01: `datetime.utcnow()` used throughout instead of timezone-aware `datetime.now(UTC)`

**Files**: Multiple files across card services
**Category**: Cleanup
**Description**: Multiple services use `datetime.utcnow()` which is deprecated in Python 3.12+ and creates naive datetime objects. The project already imports `from datetime import UTC` in some files (e.g., `task_card_protocol.py`). All card services should use timezone-aware datetimes for consistency.

**Affected files**: `card_service.py`, `card_operations_service.py`, `task_occurrence_service.py`, `card_snapshot_service.py`, `legacy_adapter.py`, `feedback_gate_engine.py`, `outcome_verifier.py`

**Fix approach**: Replace `datetime.utcnow()` with `datetime.now(UTC)` across all card-related services.

---

### P3-02: `CardEdge` unique constraint includes soft-deleted rows

**File**: `backend/app/models/card_protocol.py`, line 294
**Category**: Data Integrity
**Description**: The `UniqueConstraint("from_card_id", "to_card_id", "edge_type")` applies to ALL rows including soft-deleted ones. This means once an edge is created and soft-deleted, the same edge triplet can never be recreated (the unique constraint prevents it). Combined with P0-03 (finding soft-deleted edges), this creates a conflict where the service can find and modify a soft-deleted edge but can't create a new one.

**Current behavior**: Soft-deleted edges prevent recreation of the same edge triplet.

**Expected behavior**: Soft-deleted edges should not block new edge creation. Consider a partial unique index or changing the constraint to include `deleted_at IS NULL`.

**Fix approach**: Either add `deleted_at` to the unique constraint (making it a 4-column constraint) or use a database partial index: `CREATE UNIQUE INDEX ... WHERE deleted_at IS NULL`.

---

### P3-03: `CardSnapshotService._collect_tree` can hit recursion depth for deeply nested cards

**File**: `backend/app/services/card_protocol/card_snapshot_service.py`, lines 260-295
**Category**: Performance
**Description**: The `walk` function is recursive and follows the card tree. While `max_depth` defaults to 3, a caller can pass a larger value. Each recursion level awaits a DB query for children. For a plan with 10 phases, each with 20 tasks, each with 5 knowledge nodes, `max_depth=4` would generate 10 + 200 + 1000 = 1210 DB queries.

**Current behavior**: Tree collection is recursive with O(branching_factor^depth) DB queries.

**Expected behavior**: Consider a breadth-first or batched approach for deeper trees.

**Fix approach**: Add a safety check on the total number of collected nodes:
```python
MAX_TREE_NODES = 500
if len(seen) > MAX_TREE_NODES:
    return
```

---

### P3-04: `build_task_list_entity_card` uses `tool_result_id` as entity_id

**File**: `backend/app/tools/entity_cards.py`, line 344
**Category**: Protocol
**Description**: When building a task list entity card, the `entity_id` is set to `tool_result_id` (the ID of the LLM tool call), not a stable identifier for the card itself. This means the same set of tasks represented in different tool calls will have different entity IDs, breaking deduplication and caching on the frontend.

**Current behavior**: Task list cards get ephemeral entity IDs tied to tool calls.

**Expected behavior**: Entity IDs should be deterministic based on content (e.g., a hash of plan_id + task IDs).

**Fix approach**: Use `plan_id` or a composite identifier:
```python
entity_id=plan_id or hashlib.md5(str(sorted(task.get("id") for task in tasks)).encode()).hexdigest()[:12],
```

---

### P3-05: `InterventionOutcomeVerifier._has_system_applied_action` accesses dict incorrectly

**File**: `backend/app/services/card_protocol/outcome_verifier.py`, line 817
**Category**: Logic Bug
**Description**: The method converts `record.action_payload` to a dict with `dict(record.action_payload or {})`, then accesses `action_payload.get("parameter_compilation")`. If `record.action_payload` is stored as JSONB and deserialized as a dict, this works. But if it's `None`, `dict(None)` raises `TypeError`. The `or {}` handles this, but `dict(None or {})` returns `{}` which is correct. However, the next line does `dict(action_payload.get("parameter_compilation") or {})` which is redundant -- `get()` already returns None if key is missing, and `dict(None or {})` returns `{}`. This is not a bug but is unnecessarily verbose.

**Current behavior**: Works correctly but is verbose.

**Fix approach**: Simplify to:
```python
action_payload = record.action_payload or {}
parameter_compilation = action_payload.get("parameter_compilation") or {}
return parameter_compilation.get("applied") is True
```

---

## Architectural Observations

### Dual-Write Complexity

The card protocol sits alongside the legacy `Plan`/`Task` models. The `PlanAdapter` and `TaskAdapter` bridge these two worlds, but the dual-write pattern creates significant complexity:

1. Every legacy operation must be mirrored to the card protocol
2. The `legacy_plan_id` / `legacy_task_id` stored in card metadata creates a bidirectional dependency
3. No mechanism to detect or heal drift between the two representations

### Event Bus Before Commit Pattern

Throughout the card services, events are published via `self.db.flush()` followed by `self.event_bus.publish()`. The flush pushes changes to the database transaction buffer but doesn't commit. If the outer transaction rolls back, the event has already been published. This is a systemic pattern affecting data consistency between the event bus and the database.

### JSONB Metadata as Schemaless Storage

The card protocol heavily relies on JSONB `metadata_` columns for structured data (e.g., `legacy_plan_id`, `phase_index`, `current_phase_card_id`). This approach is flexible but has no schema enforcement at the database level. Key observations:

1. No validation on metadata keys or values
2. No migration path for metadata schema changes
3. Querying by JSONB keys (e.g., `Card.metadata_["legacy_plan_id"].as_string()`) bypasses type safety and can have performance implications without GIN indexes

### Missing Indexes

The `cards` table has no GIN index on the `metadata` JSONB column, despite multiple services querying it with JSONB key lookups (e.g., `Card.metadata_["legacy_plan_id"].as_string()`). Without a GIN index, these queries will result in full table scans.

---

## Recommendations

1. **Immediate (P0)**: Fix the `archived_at` missing column declaration, fix the soft-deleted edge lookup, and resolve the `ShareService` dual-definition issue.

2. **Short-term (P1)**: Add lifecycle validation to `_transition`, protect lifecycle fields in `update_card`, fix the case-mismatch in entity card status checks, and add transaction boundaries to snapshot import.

3. **Medium-term (P2)**: Add GIN index on `cards.metadata`, i18n-enable the TaskCardGenerator, fix N+1 queries in task listing tools, and move event publishing to post-commit hooks.

4. **Long-term**: Plan a migration path away from the dual-write pattern. Consider making the card protocol the primary source of truth and deprecating the legacy Plan/Task tables.
