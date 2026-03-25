# LTM Rollback Playbook

## Feature Flags to Disable
- `USE_CONTEXT_PACK`
- `ANALYSIS_SYNC_ON_EVENT`
- `ENABLE_EVIDENCE_HEALTH_JOB`
- `ENABLE_BEHAVIOR_DECAY`
- `ENABLE_MEMORY_RETRACTION`
- `USE_CONTEXT_INTENT_ROUTER`
- `ENABLE_MEMORY_PANEL`
- `ENABLE_MEMORY_GOVERNANCE`
- `ENABLE_MEMORY_EXPORT`

## Migration Rollback
1) Identify the last applied LTM migrations in `backend/alembic/versions/`.
2) Downgrade step-by-step:
   - `cd backend && alembic downgrade -1`
3) Repeat until reaching the previous stable revision.

## Data Retention Notes
- Retractions are soft (`retracted_at`), no hard deletes.
- Evidence health marks `evidence_missing` and snapshots for episodic items.
- Memory history is preserved (versioned preferences); rollbacks do not remove history.

## Operational Checklist
- Disable flags in environment/config and restart services.
- Stop scheduled jobs for evidence health/decay.
- Validate core chat, task, and event ingestion flows.

## Rollback Drill
1) Run the drill script:
   - `cd backend && python scripts/ltm_rollback_drill.py`
2) Verify all flags in the drill output can be toggled off.
3) Apply changes in the environment/config and restart services.

Sample output (truncated):
```
LTM Rollback Drill
===================
Current flags:
- USE_CONTEXT_PACK: off
- ENABLE_MEMORY_JOBS: off
...
Flags to switch off (in order):
- ENABLE_LTM_ROLLOUT: already_off
- ENABLE_CONTEXT_RANKING: already_off
...
```
