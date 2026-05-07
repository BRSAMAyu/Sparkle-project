# Database Schema & Migrations Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The database layer is architecturally sound with 247 tables, 1066 indexes, 324 foreign key constraints, and comprehensive role-based access control. The schema shows mature patterns: soft-delete via `deleted_at`, HNSW vector indexes with partial conditions, proper CASCADE/SET NULL/RESTRICT FK strategies, and CHECK constraints on financial and range fields. However, there are three categories of issues that need attention: migration chain divergence (3 heads), Go-side schema drift after today's migrations, and minor consistency issues in enum values and timestamp types.

## Critical Issues (P0)

### P0-1: Migration chain has 3 unmerged heads

The Alembic migration chain diverges into 3 independent heads with no merge migration to unify them:

1. **Head A**: `02a063d173ec` (PII hash columns, via `wp19_20260507` -> ... -> baseline)
2. **Head B**: `c27_20260503` (restore task status, via `c26` -> ... -> baseline)
3. **Head C**: `p001_20260507` (goal_id in plans, via `7f807dcd4e5f` -> ... -> baseline)

Alembic will refuse to apply new migrations if there is more than one head. Any developer running `alembic upgrade head` or `alembic revision` will encounter an error. A merge migration that consolidates all three heads into one is required.

**Files**:
- `backend/alembic/versions/02a063d173ec_add_pii_hash_columns_for_encryption.py` (head)
- `backend/alembic/versions/c27_20260503_add_restore_task_status.py` (head)
- `backend/alembic/versions/p001_20260507_add_goal_id_to_plans.py` (head)

### P0-2: Go-side schema.sql and models.go out of sync with latest migrations

Two migrations applied today (2026-05-07) have not been reflected in the Go-side generated artifacts:

1. **`p001_20260507`** adds `plans.goal_id` (UUID, FK to `goals.id`) -- this column is absent from `schema.sql` and `models.go Plan` struct.
2. **`wp19_20260507`** adds `chat_messages.metadata` (JSONB) -- this column IS present in `schema.sql` but models.go already has it, suggesting partial sync.
3. **`02a063d173ec`** adds PII hash columns (`username_hash`, `email_hash`, `google_id_hash`, `apple_id_hash`, `wechat_unionid_hash`) to `users` -- absent from `schema.sql` and `models.go User` struct.

Run `make sync-db` after merging the migration heads to regenerate both files.

**Files**:
- `backend/gateway/internal/db/schema.sql:4176` (plans table missing `goal_id`)
- `backend/gateway/internal/db/models.go` (Plan struct missing `GoalID`)

## High Issues (P1)

### P1-1: `achievementtype` enum contains duplicate value in schema.sql

The `schema.sql` dump contains both `'planning'` (lowercase) and `'PLANNING'` (uppercase) in the `achievementtype` enum:

```sql
CREATE TYPE achievementtype AS ENUM (
    ...
    'planning',
    'PLANNING'
);
```

Migration `r8_fix_achievementtype_enum_duplicate` (revision `r8_fix_achievementtype_enum_duplicate`) was written to fix this, and the Python model (`AchievementType.PLANNING = "planning"`) correctly uses only lowercase. However, the schema.sql dump still shows both values because the dump was taken before the migration ran. After running `alembic upgrade head` and `make sync-db`, this should resolve. Verify with:

```sql
SELECT unnest(enum_range(NULL::achievementtype));
```

**Files**:
- `backend/gateway/internal/db/schema.sql:123-136` (enum definition)
- `backend/alembic/versions/r8_fix_achievementtype_enum_duplicate.py` (fix migration)

### P1-2: 23 empty downgrade functions (forward-only migrations)

23 of 130 migration files contain empty `downgrade()` functions (just `pass`). These include structural changes (create tables, add columns, add indexes) and cannot be rolled back. Of particular note:

- `wp18_20260502_add_on_delete_and_check_constraints.py` -- alters FK constraints, no downgrade
- `5f2b9b3c0e6f_create_event_outbox_tables.py` -- creates CQRS tables, no downgrade
- `9c4d7e8f1a2b_align_cqrs_schema_with_gateway.py` -- CQRS alignment, no downgrade
- `wp19_20260507_add_chat_messages_metadata_jsonb.py` -- adds column, no downgrade

For launch, this is acceptable as long as rollbacks are not planned. Document this as a known limitation.

**Files**: See full list in analysis (23 files with `def downgrade` containing zero `op.` calls).

### P1-3: Timestamp timezone inconsistency across tables

The schema mixes `timestamp without time zone` (852 occurrences) and `timestamp with time zone` (32 occurrences) for `created_at`/`updated_at` columns. For example:

- Most tables: `created_at timestamp without time zone NOT NULL`
- `accountability_checkin`, `accountability_partnership`, `agent_execution_stats`: `created_at timestamp with time zone DEFAULT now() NOT NULL`

In a globally-deployable application, using `timestamp without time zone` means timestamps are interpreted relative to the server's timezone, which can cause confusion when users span multiple timezones. The Python `BaseModel` uses `datetime.utcnow` (naive UTC), which is consistent, but the `with time zone` tables may store UTC offsets that differ.

**Files**:
- `backend/gateway/internal/db/schema.sql` (mixed across ~30 tables)
- `backend/app/models/base.py:108` (uses `datetime.utcnow`)

## Medium Issues (P2)

### P2-1: `smoke_document_vectors` test table in production schema

A test/smoke table `smoke_document_vectors` is present in `schema.sql` with full ACL grants to service roles (`sparkle_engine`, `sparkle_gateway`, `sparkle_celery`, `sparkle_readonly`). This table should not exist in production schema dumps and should be excluded via `pg_dump --exclude-table` or removed after testing.

**Files**:
- `backend/gateway/internal/db/schema.sql:5231-5243` (table definition)
- `backend/gateway/internal/db/schema.sql:11226-11229` (index on test table)

### P2-2: 79 tables owned by `brsama` instead of `postgres`

79 out of 309 objects (tables, types, functions) are owned by local user `brsama` instead of the service account `postgres`. In production, the `OWNER` should be a designated service account. This happens because the `pg_dump` captures the local development owner. The `make sync-db` command should normalize ownership.

**Files**: `backend/gateway/internal/db/schema.sql` (scattered throughout)

### P2-3: Missing composite index for `group_members(group_id, user_id)` query

Query `IsGroupMember` in `query.sql:64` does:
```sql
SELECT EXISTS(SELECT 1 FROM group_members WHERE group_id = $1 AND user_id = $2)
```

There is no composite index on `(group_id, user_id)` -- only individual indexes. A composite index would make this hot-path membership check faster.

**Files**:
- `backend/gateway/internal/db/query.sql:63-64`

### P2-4: Missing index on `post_likes(user_id, post_id)` for DeletePostLike

The `DeletePostLike` query (`query.sql:119-120`) deletes by `(user_id, post_id)` but the only indexes are separate on `user_id` and `post_id`. A composite unique index on `(user_id, post_id)` would serve both the unique constraint and the delete query.

**Files**:
- `backend/gateway/internal/db/query.sql:119-120`

### P2-5: Seed script contains hardcoded demo password

The seed script uses `DEMO_PASSWORD = os.getenv("LOCAL_SMOKE_PASSWORD", "Chat123456")` and a hardcoded `"DemoFriend123"` for friend accounts. While documented as local-only, this is a risk if the seed script is accidentally run against a non-local environment.

**Files**:
- `backend/scripts/seed_demo_user_enhanced.py:54`

### P2-6: HNSW indexes lack explicit `m` and `ef_construction` parameters

All 7 HNSW vector indexes use default `m` and `ef_construction` parameters. For a 1024-dimensional vector space with potentially millions of rows, tuning these parameters (e.g., `m = 32, ef_construction = 128`) can significantly improve recall vs. index build time tradeoff.

**Files**:
- `backend/alembic/versions/stage38_06_add_vector_hnsw_indexes.py`
- `backend/gateway/internal/db/schema.sql:10018,10130,10165,10606,11117,11145,11229`

## Low Issues (P3)

### P3-1: Two backup directories exist in `alembic/versions/`

`versions_backup/` (61 files) and `versions.backup/` (13 files) contain historical migration files that are not part of the active chain. These should be removed or moved outside the alembic directory to avoid confusion.

**Files**:
- `backend/alembic/versions_backup/`
- `backend/alembic/versions.backup/`

### P3-2: `cs001` migration has `down_revision = None` but was created after baseline

`cs001_add_community_signal_to_knowledge_nodes.py` has `down_revision = None`, making it a second root (alongside the baseline `cc9383c4c29f`). While this works because it was later merged via `c50dce18e33a`, it indicates the migration was generated incorrectly (should have had the current head as down_revision). No current impact, but worth noting for process improvement.

**Files**:
- `backend/alembic/versions/cs001_add_community_signal_to_knowledge_nodes.py:12`

### P3-3: 14 CHECK constraints marked `NOT VALID`

All CHECK constraints added by `wp18_20260502` are marked `NOT VALID`, meaning PostgreSQL does not enforce them for existing rows. This was presumably intentional (to avoid full table scans on large tables during migration), but they should be validated post-launch:

```sql
ALTER TABLE tasks VALIDATE CONSTRAINT chk_tasks_difficulty_range;
ALTER TABLE users VALIDATE CONSTRAINT chk_users_photon_balance_non_negative;
-- etc.
```

**Files**:
- `backend/gateway/internal/db/schema.sql:7692-7800`

### P3-4: `BaseModel.created_at` uses deprecated `datetime.utcnow`

`base.py:108` uses `default=datetime.utcnow` which is deprecated in Python 3.12+. Should use `default=lambda: datetime.now(UTC).replace(tzinfo=None)` for forward compatibility.

**Files**:
- `backend/app/models/base.py:108,211`

## Positive Findings

1. **Comprehensive FK cascade strategy**: 157 CASCADE, 51 SET NULL, 3 RESTRICT -- well-thought-out cascade behavior tailored to each relationship.

2. **Vector indexing is well-designed**: All embedding columns consistently use `vector(1024)` with HNSW indexes and partial conditions (`WHERE embedding IS NOT NULL`), avoiding index bloat on NULL rows.

3. **AGE graph schema is properly configured**: The `sparkle_galaxy` schema uses Apache AGE with proper label tables for vertices and edges. The `AgeClient` in `age_client.py` has proper identifier validation and parameter sanitization to prevent Cypher injection.

4. **CHECK constraints on critical fields**: Financial fields (`photon_balance`, `price_paid`), range fields (`difficulty 1-5`, `flame_level 0-100`), and subtask counters all have CHECK constraints.

5. **Role-based access control**: Service roles (`sparkle_engine`, `sparkle_gateway`, `sparkle_celery`, `sparkle_readonly`) are consistently granted appropriate permissions across all tables.

6. **Migration contract metadata**: Most migrations include structured contract metadata (type, rollback_plan, verification_query, owner, ticket), which is excellent for operational traceability.

7. **Baseline migration pattern**: The `cc9383c4c29f_full_baseline_schema.py` serves as a single comprehensive starting point, with incremental migrations building on top -- clean and maintainable.

8. **Strong index coverage**: 1066 indexes for 247 tables (~4.3 indexes per table on average), with composite and partial indexes for common query patterns. Hot paths (chat messages, tasks, plans, knowledge nodes) are well-indexed.

9. **Proper use of `CONCURRENTLY` for index creation**: The vector HNSW index migration (`stage38_06`) uses `CREATE INDEX CONCURRENTLY` to avoid locking tables during index creation.

10. **CQRS event sourcing tables well-structured**: `event_outbox`, `event_store`, `processed_events`, and `projection_snapshots` tables have proper indexes for their access patterns, including `FOR UPDATE SKIP LOCKED` support.

## Files Audited

### Alembic configuration
- `backend/alembic/env.py`
- `backend/alembic.ini`
- `backend/alembic/script.py.mako`

### All 130 migration files in `backend/alembic/versions/`:
- `cc9383c4c29f_full_baseline_schema.py` (baseline)
- `fa4b8c1d2e3f_add_node_sector_weights.py` (mega merge of 7 heads)
- `c23_20260502_merge_fv01_19_heads.py` (merge of 10 heads)
- `r8_fix_achievementtype_enum_duplicate.py` (enum dedup fix)
- `wp18_20260502_add_on_delete_and_check_constraints.py` (FK + CHECK)
- `wp19_20260507_add_chat_messages_metadata_jsonb.py` (metadata column)
- `p001_20260507_add_goal_id_to_plans.py` (goal_id FK)
- `02a063d173ec_add_pii_hash_columns_for_encryption.py` (PII hashes)
- `stage38_06_add_vector_hnsw_indexes.py` (vector indexes)
- Plus 121 other migration files

### Go-side schema
- `backend/gateway/internal/db/schema.sql` (22,159 lines)
- `backend/gateway/internal/db/models.go` (249,175 bytes, 288 structs)
- `backend/gateway/internal/db/query.sql` (316 lines)
- `backend/gateway/internal/db/query.sql.go` (47,729 lines)
- `backend/gateway/internal/db/db.go`

### Python models (all 85+ files in `backend/app/models/`)
- `backend/app/models/__init__.py` (574 lines, 250+ exports)
- `backend/app/models/base.py` (GUID, BaseModel, SoftDeleteMixin)
- `backend/app/models/user.py` (User, PushPreference, UserDevice, LoginAttempt)
- `backend/app/models/task.py` (Task, SubTask)
- `backend/app/models/plan.py` (Plan)
- `backend/app/models/goal.py` (Goal)
- `backend/app/models/achievement.py` (Achievement, types)
- `backend/app/models/encrypted_types.py`
- `backend/app/models/pii_encryption_listeners.py`

### AGE client
- `backend/app/core/age_client.py`

### Seed scripts
- `backend/scripts/seed_demo_user_enhanced.py`
- `backend/scripts/seed_demo_user.py`
- `backend/scripts/seed_phase2_demo_data.py`
