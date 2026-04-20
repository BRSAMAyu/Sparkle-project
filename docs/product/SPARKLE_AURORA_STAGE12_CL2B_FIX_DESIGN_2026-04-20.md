# SPARKLE Aurora Stage 12 WS-CL2b Fix Design (2026-04-20)

> **Status**: pre-implementation artifact for `WS-CL2b`
> **Goal**: repair the `multi_dimensional_learner` persistence seam so the Celery path no longer calls a missing API.

## 1. Current Symptom

Stage 11 CL0 found that `save_learning_state` in `backend/app/core/celery_tasks.py` calls:

```python
await learner.save_state(user_id, state_data)
```

But `MultiDimensionalLearner` does not expose `save_state()`, making the Celery seam structurally broken.

## 2. Target State

`MultiDimensionalLearner` must expose a real persistence API that:

1. accepts an explicit state payload
2. writes that payload to the learner's canonical Redis key
3. preserves the current `_save()` behavior for in-process updates

## 3. Compatibility Shape

Stage 12 will keep both pathways:

1. `_save()` remains the internal persistence path for current in-memory stats
2. `save_state()` becomes the explicit external write API for Celery / background repair paths

This keeps the public seam clear without forcing the rest of the learner to change.

## 4. Payload Schema

`save_state()` will accept a dict shaped like the canonical persisted payload:

1. per-dimension `stats`
2. optional `config.weights`

The method may normalize missing sections, but it must reject obviously malformed structures rather than silently inventing state.

## 5. Rule V Regression Proof

`WS-CL2b` must add a regression test that proves:

1. the old Celery seam depended on a missing `save_state()` API
2. the repaired seam can persist a supplied state payload without raising `AttributeError`
3. a fresh learner instance can load the saved state back from Redis

## 6. Out-of-Scope

1. redesigning the dimension model
2. showing multi-dimensional scores to users
3. changing Rule K lane ownership
