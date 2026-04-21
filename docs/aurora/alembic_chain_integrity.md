# Aurora Alembic Chain Integrity

Date: 2026-04-21

## Summary

Stage 29.5 repaired the two stage-level migration gaps discovered during the repo hygiene audit:

| stage | revision | type | reason |
| --- | --- | --- | --- |
| Stage 19 | `s19c1d2e3f4` | no-op revision | Stage 19 introduced Redis working-memory and governed write-lane behavior, but no relational DDL |
| Stage 22 | `s22c1d2e3f4` | no-op revision | Stage 22 wired achievement/calendar/baseline behavior onto existing tables, but no relational DDL |
| Stage 29.5 | `s295a1b2c3d4` | merge revision | merges `s29a1b2c3d4`, `s19c1d2e3f4`, and `s22c1d2e3f4` back to one head |

## Current Head

`alembic history` now reports:

```text
s29a1b2c3d4, s19c1d2e3f4, s22c1d2e3f4 -> s295a1b2c3d4 (head) (mergepoint), Merge Stage 29 and no-op backfill heads.
```

This restores a single authoritative head for Stage 29.5 while preserving the real historical branching that already existed in the repo.

## Repair Notes

- `backend/alembic/versions/s19c1d2e3f4_stage19_no_schema_change.py`
- `backend/alembic/versions/s22c1d2e3f4_stage22_no_schema_change.py`
- `backend/alembic/versions/s295a1b2c3d4_merge_stage_backfill_heads.py`

Each no-op revision includes:

- explicit `Stage {N} - No Schema Change` annotation
- a human-readable reason
- a Stage 29.5 audit verification stamp

## Policy Going Forward

From Stage 29.5 onward, every stage must do exactly one of the following:

1. land a real Alembic revision for DDL changes
2. land a no-op Alembic revision that explicitly states why the stage changed behavior only

Silent stage-level migration gaps are no longer allowed.
