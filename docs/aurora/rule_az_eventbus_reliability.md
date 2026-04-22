# Rule AZ - EventBus Reliability

Rule AZ locks Stage 38's reliability contract for Aurora event publishing and consumption.

## Contract

1. Stage 38 owned publishers must emit through `event_bus_reliable.publish(...)` instead of bare `event_bus.publish(...)`.
2. Stage 38 owned consumers must inherit a reliability wrapper or declare `@reliable_consumer(...)` explicitly.
3. Reliability enforcement scope in this stage is the dispatch-owned publisher and consumer entrypoints:
   - `backend/app/services/task_service.py`
   - `backend/app/services/simulation/simulation_engine.py`
   - `backend/app/services/seed_library_service.py`
   - `backend/app/services/theater/prediction_theater_service.py`
   - `backend/app/services/shop_service.py`
   - `backend/app/services/stage33_journey_event_service.py`
   - `backend/app/consumers/journey_consumer_base.py`
   - `backend/app/consumers/plan_task_generation_consumer.py`
   - `backend/app/consumers/user_memory_seed_consumer.py`
   - `backend/app/services/galaxy_event_consumer.py`

## Why

- Stage 38 introduced retry, DLQ, and no-ack-on-failure semantics.
- A publisher that bypasses the reliable wrapper can silently skip Stage 38 retry/DLQ policy.
- A consumer that bypasses `@reliable_consumer` can reintroduce the original Galaxy-style ack-before-success bug.

## Guard

- Script: `scripts/guards/check_rule_az_eventbus_reliability.py`
- Manifest key: `AZ`
- Repo test: `backend/tests/unit/test_rule_az_guard.py`

## Stage 38 Notes

- Legacy non-Stage38 publishers outside the scoped list remain technical debt and are tracked for follow-up migration rather than folded into this stage's denominator.
- `event_bus.py` itself is excluded because it defines the reliability substrate rather than consuming it.
