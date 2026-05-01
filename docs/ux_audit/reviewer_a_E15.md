# Reviewer A — E15: DB迁移健康——52个Alembic迁移一致性
Timestamp: 2026-04-26T12:10:00+08:00
Chain Index: 22 (reviewer_a_queue)

## Chain Flow Summary
Alembic迁移系统应为单链（1个根→1个头），使`alembic upgrade head`能从空库重建完整schema。当前状态：88个迁移文件（非文档中的52个），23个未合并头，33个孤立分支（down_revision=None），39个SQLAlchemy模型表在Go schema.sql中不存在。迁移系统实质上不可用，`make db-migrate`在未设置`FORCE_STAMP=1`时必定失败。

## Critical Issues 🔴

**E15-C1: 23 unmerged heads — `alembic upgrade head` impossible**
Expected: Exactly 1 head. Actual: 23 heads. The Makefile `db-migrate` target (line 57-58) already detects this: `heads_count -ne 1 → exit 1`. Any developer running `make sync-db` without `FORCE_STAMP=1` hits an immediate failure. Evidence: `alembic/versions/` has 88 files with 23 competing heads including `cc9383c4c29f` (baseline), `tp0c1d2e3f4a5` (theater), `s40b1c2d3e4` (aurora runtime v1), `stage_c5_aurora_decision_telemetry`, and 19 others.

**E15-C2: 33 migrations with `down_revision = None` — completely disconnected branches**
28 of these have actual schema operations (create_table/add_column). They will never be applied by `alembic upgrade head` because Alembic only follows the chain from head → root. Evidence: `43ff976a8b29`, `4f6c3b8e1d2a`, `5f2b9b3c0e6f`, `8b2f0b2d9b1a`, `a1b2c3d4e5f6`, `a2d4e6f8b1c3`, `a4b5c6d7e8f9`, `b2c3d4e5f6g7`, `b8f1c2d3e4f5`, `c1f4e7a9b2d6`, `c8e4f2a3b1d5`, `c9f3b2a7e1d4`, `cc9383c4c29f`, `d1e2f3a4b5c6`, `e7e90c21943d`, `f7a9c3e2d1b4`, `f9c16a4b2d3e`, `oc001a2b3c4d5`, `oc004e5f6a7b8`, `ps003_phase3_strategy_outcomes`, `s26a1b2c3d4`, `s27a1b2c3d4`, `s31a1b2c3d4`, `s39a1b2c3d4`, `s39b1c2d3e4`, `s40a1b2c3d4`, `s40b1c2d3e4`, `tp1e2f3a4b5c6` plus 5 empty merges.

**E15-C3: 39 SQLAlchemy model tables missing from Go schema.sql (production DB)**
These tables have model definitions AND are actively queried by service code (38/39 confirmed runtime references), but don't exist in `backend/gateway/internal/db/schema.sql`. In production (Go-managed DB), any service accessing these tables will crash with `relation does not exist`. Key affected subsystems:
- Aurora Stage 20-31: `aurora_judgment_records`, `conflict_resolution_records`, `routing_decision_log`, `unresolved_conflicts`, `shared_skills`, `user_skills`, `persdyn_attractors`, `daily_behavior_vector`, `idiographic_associations`, `idiographic_changepoints`, `srl_phase_states`
- Card Protocol: `cards`, `card_edges`, `card_snapshots`, `card_adoption_records`, `card_share_records`, `planning_artifacts`, `task_occurrences`, `intervention_records`
- Execution/OpenClaw: `execution_audit_log`, `execution_schedules`
- Theater/Simulation: `theater_candidate_bundles`, `theater_predictions`, `simulation_runs`
- Infrastructure: `event_bus_dlq`, `outbox_events`, `distilled_strategy_cache`, `scenes`, `session_completions`, `push_delivery_records`, `report_snapshots`, `leaderboard_snapshots`, `user_learning_profiles`, `candidate_action_feedback`, `user_push_opt_in`, `intervention_outcomes`, `intervention_strategy_outcomes`, `skill_share_moderation_queue`, `accountability_policies`

**E15-C4: Baseline schema is completely isolated**
`cc9383c4c29f_full_baseline_schema.py` creates 126 tables (the foundational schema) but has `down_revision = None` and no other migration chains FROM it. It's a standalone root that was never connected to any subsequent migration. The 86 remaining migrations form their own disconnected chains. Evidence: chain-from-baseline analysis shows depth=1 (only itself).

## Major Issues 🟡

**E15-M1: Migration count discrepancy — 88 files vs documented 52**
The state file description says "52个Alembic迁移" but the actual file count is 88 (87 unique revisions). The project has outgrown its documentation, suggesting no consolidation/squash has been performed. 36 additional migrations were added without updating the count.

**E15-M2: 14 ghost tables in migrations with no SQLAlchemy model**
Tables created in migrations but with no corresponding model: `aurora_decision_telemetry`, `aurora_policy_versions`, `aurora_scheduled_wakes`, `aurora_state_snapshots`, `commitments`, `event_outbox`, `event_sequence_counters`, `focus_contracts`, `identity_evidence`, `insight_claims`, `probe_outcomes`, `transition_decision_records`, `user_scenario_states`, `window_states`. These exist (or would exist) in the DB but no Python code references them. Likely leftover from abandoned features.

**E15-M3: `FORCE_STAMP=1` as permanent workaround masks the real problem**
The Makefile's `FORCE_STAMP=1` escape hatch runs `alembic stamp heads` which lies to Alembic about what's been applied. This means the `alembic_version` table may show all revisions as "applied" even though the actual DB schema was created by Go's `schema.sql` dump. The migration system is cosmetic, not functional.

**E15-M4: db-dump overwrites schema.sql from live DB, not from migrations**
`make db-dump` (Makefile line 98-103) runs `pg_dump` and overwrites `schema.sql`. This means `schema.sql` reflects whatever is currently in the database, not what the migrations define. If a table was manually created or created via `FORCE_STAMP` bypass, it becomes the de facto schema regardless of migration state.

**E15-M5: No migration consolidation/squash script exists**
No `squash_*` or `consolidate_*` scripts found in `backend/scripts/`. With 88 disconnected migrations and 23 heads, the only viable fix is a full squash into a single baseline migration. The absence of tooling for this makes the fix harder.

## Minor Issues 🟢

**E15-m1: 4 empty merge migrations exist as standalone heads**
`9c4d7e8f1a2b_align_cqrs_schema_with_gateway.py`, `b7c1f2d4e6a1_add_knowledge_node_to_shared_resources.py`, `s19c1d2e3f4_stage19_no_schema_change.py`, `s22c1d2e3f4_stage22_no_schema_change.py` have `down_revision = None` and no schema operations. Pure noise in the migration directory.

## Working Well ✅

- **env.py properly imports all models** (line 24-57): Ensures `target_metadata = Base.metadata` covers all registered models for autogenerate
- **Baseline schema is comprehensive**: Creates 126 tables covering core functionality (users, tasks, plans, galaxy, community, cognitive, achievements, etc.)
- **`_ensure_alembic_version_table()`** (env.py line 91-116): Handles missing alembic_version table and VARCHAR(64) upgrade gracefully
- **Makefile head detection** (line 57-72): Already has safety check for multi-head state with diagnostic output
- **No `create_all()` bypass**: App code never calls `Base.metadata.create_all()` — all table creation is migration-based (or schema.sql-based via Go)
- **All 88 migration files have valid revision IDs**: No duplicate revision IDs detected, no parse errors
- **Individual migration quality is acceptable**: Each migration has proper upgrade/downgrade pairs with table/column operations

## Files Examined
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/` (all 88 files scanned programmatically)
- `backend/alembic/versions/cc9383c4c29f_full_baseline_schema.py`
- `backend/alembic/versions/stage_c4_intervention_outcomes.py`
- `backend/alembic/versions/stage_c5_aurora_decision_telemetry.py`
- `backend/alembic/versions/c17a1b2c3d4_add_achievement_context_snapshot.py`
- `backend/alembic/versions/c18a1b2c3d4_error_record_galaxy_echo.py`
- `backend/app/models/` (all 97 files scanned for __tablename__)
- `backend/gateway/internal/db/schema.sql` (174 tables)
- `Makefile` (sync-db, db-migrate, db-dump, db-sqlc targets)
- `docs/ux_audit/audit_state.json`

## Confidence: High — analysis is fully automated (no guessing)

### Summary Statistics
| Metric | Value |
|--------|-------|
| Migration files | 88 |
| Unique revisions | 87 |
| Unmerged heads | 23 |
| Migrations with down_revision=None | 33 (28 with ops) |
| Merge migrations | 11 |
| Tables in baseline schema | 126 |
| Total tables in migrations | 204 |
| Tables in SQLAlchemy models | 191 |
| Tables in Go schema.sql | 174 |
| Model tables missing from Go schema | 39 |
| Ghost tables (in migrations, no model) | 14 |
| `alembic upgrade head` | FAILS (23 heads) |

### Recommended Fix Priority
1. **Squash all migrations** into a single baseline that matches current Go `schema.sql` (174 tables)
2. **Add missing 39 tables** from SQLAlchemy models to the squash
3. **Remove 14 ghost tables** from the squash (or add models if they're still needed)
4. **Single head, single root** — the squash becomes the only migration
5. **Going forward**: enforce single-head CI check (already partially in Makefile)
