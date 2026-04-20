# SPARKLE Aurora Stage 14 WS-CL1-INTEG Artifact (2026-04-20)

> **Workstream**: `WS-CL1-INTEG`
> **Purpose**: lock the integration inventory and the exact fallback symptom before any code repair begins.

## 1. Production Call-Site Inventory

Current non-test `ToolPreferenceRouter(...)` construction sites are:

| File | Redis injection shape | Classification | Stage 14 action |
| --- | --- | --- | --- |
| `backend/app/orchestration/context_builder.py` | `self.redis` | already persistent-capable | no code change |
| `backend/app/orchestration/orchestrator_production.py` | `self.redis` | already persistent-capable | no code change |
| `backend/app/routing/router_node.py` | hardcoded `redis_client=None` | broken production seam | repair required |

No additional production call sites were found under `backend/app` or `backend/services`.

Because the call-site count is `3`, the dispatch-plan appendix threshold (`>5`) is **not** triggered.

## 2. Target Injection Path

`RouterNode` already receives:

1. `redis_client` at construction time
2. `user_id` at construction time
3. `db_session` from `WorkflowState.context_data`

The Stage 14 repair is therefore narrow:

1. keep `RouterNode` as the integration owner
2. pass the already-available `redis_client` through to `ToolPreferenceRouter`
3. do not redesign routing topology or learner math

## 3. Intentional Non-Persistent Sites

Stage 14 does **not** reclassify explicitly offline / unit-test constructions of `ToolPreferenceRouter` as production defects.

This WS is limited to the production seam named in the Stage 13 handoff.

## 4. Locked Rule V Fallback Symptom

The regression symptom to guard permanently is:

> inside `RouterNode`, a history update path that should have used `PersistentBayesianLearner` silently falls back to the in-memory `BayesianLearner` because `ToolPreferenceRouter(..., redis_client=None)` is hardcoded.

Required Rule V proof:

1. pre-fix symptom is reproduced against `RouterNode`
2. post-fix path uses `PersistentBayesianLearner`
3. repaired path still preserves fallback safety when `redis_client` is truly absent

## 5. Boundary Lock

Allowed:

1. grep/inventory confirmation
2. redis injection repair
3. regression and integration tests for the fallback symptom

Not allowed:

1. learner formula changes
2. route-ranking redesign
3. shadow-mode logic
4. user-visible wire-on
