# Outbox Events Growth Strategy

## Current Situation
The `outbox_events` table is growing rapidly as it captures every domain event for reliable messaging (Transactional Outbox Pattern). Currently, processed events accumulate indefinitely.

## Analysis
- **Purpose**: Ensure events are published to the message broker (RabbitMQ/Kafka) at least once.
- **Lifecycle**: Created (in transaction) -> Published (by relay worker) -> Acknowledged.
- **Retention**: Once published, events are rarely needed unless for debugging or replay (which is rare and usually time-bound).

## Strategy: Retention Policy (Deletion)
Instead of complex partitioning for a temporary holding table, we will implement an aggressive cleanup strategy.

### 1. Index Optimization
Ensure we have an efficient index for finding published events to delete.
- Existing Index: `idx_outbox_unpublished` (where published_at IS NULL).
- **New Index Needed**: `idx_outbox_published` (where published_at IS NOT NULL) is NOT needed if we just delete `WHERE published_at < NOW() - interval '7 days'`. Postgres partial indexes or just scanning the `published_at` column (if indexed) works.
- `published_at` is heavily updated, so indexing it might cause churn, but it's necessary for cleanup.

### 2. Scheduled Cleanup Task (Celery)
We will add a Celery beat task `cleanup_outbox_events` to run daily.
- **Logic**: `DELETE FROM event_outbox WHERE published_at IS NOT NULL AND published_at < (NOW() - INTERVAL '7 DAYS')`.
- **Batching**: Delete in chunks of 1000-5000 to avoid locking the table for too long.

### 3. Alternative: Partitioning (Deferred)
If volume exceeds millions per day, we would partition by `created_at` (daily) and `DROP TABLE` old partitions. Given current scale, DELETE is sufficient and simpler.

## Implementation Plan
1. Create a Celery task in `backend/app/worker/tasks.py` (or similar).
2. Configure Celery Beat schedule.
