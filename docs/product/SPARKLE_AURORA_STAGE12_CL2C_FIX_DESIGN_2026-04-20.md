# SPARKLE Aurora Stage 12 WS-CL2c Fix Design (2026-04-20)

> **Status**: pre-implementation artifact for `WS-CL2c`
> **Goal**: replace restart-loss-prone `InMemoryDistilledStrategyStore` with a durable DB-backed repository.

## 1. Current Symptom

Stage 11 CL0 proved that the current strategy store is process-local and restart-unsafe:

- implementation is `InMemoryDistilledStrategyStore`
- restart drops all state
- retrieval / pipeline seams cannot be trusted as a durable substrate

## 2. Layer Classification

Stage 12 locks the store to:

1. **L2 inference cache**
2. **not** a compiler
3. **not** a new inference engine
4. **Aurora read-only**

The store is a data component for inferred strategy records, not a new reasoning or compilation entrypoint.

## 3. DB Plan

Stage 12 will introduce:

1. a dedicated strategy-store table via Alembic
2. a DB-backed repository that preserves the current CRUD / transition / query semantics
3. an adapter or alias strategy so existing callers can move off `InMemoryDistilledStrategyStore`

## 4. Migration Note

There is no durable in-memory data to migrate forward.

The real problem is restart-loss, not historic data conversion. Stage 12 therefore needs:

1. schema migration
2. repository migration
3. test conversion

It does **not** need an in-memory to DB backfill job.

## 5. Rule V Regression Proof

`WS-CL2c` must add regression tests that prove:

1. a strategy created through the DB-backed repository survives repository re-instantiation
2. lifecycle transitions remain legal and durable
3. retrieval still works against the durable repository
4. no remaining runtime path depends on `InMemoryDistilledStrategyStore`

## 6. Out-of-Scope

1. enabling distiller by default
2. wiring strategies to the user front door
3. turning the store into a new compiler or Aurora write lane
