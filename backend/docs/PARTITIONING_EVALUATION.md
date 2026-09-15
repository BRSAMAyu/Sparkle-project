# Database Partitioning & Snowflake ID Strategy Evaluation

## Executive Summary

The current system relies on UUID v4 for primary keys across both Python and Go services. While robust for uniqueness, UUID v4 causes index fragmentation and offers no time-locality for partition pruning. Moving to `chat_messages` range partitioning by `created_at` (as proposed in `DB_PARTITIONING_STRATEGY.md`) is a solid first step, but adopting Snowflake IDs (or UUID v7) would offer significant performance benefits by combining uniqueness with time-ordering.

However, a full migration to Snowflake IDs/UUID v7 across the entire stack is a high-effort, high-risk change for this phase. 

**Decision:** We will proceed with the **Range Partitioning by `created_at`** strategy for `chat_messages` as originally planned, using Composite Primary Keys `(id, created_at)`. We will defer the global Snowflake ID migration to a future optimization phase but will implement UUID v7 for *new* high-volume tables (like `outbox_events` if we decide to partition it now) to future-proof them.

## Analysis of Snowflake ID vs. UUID v4

### 1. Current State (UUID v4)
- **Pros:**
  - Simple, universally supported.
  - No coordination required between distributed services.
  - Existing code uses standard libraries (`uuid.uuid4()` in Python, `uuid.New()` in Go).
- **Cons:**
  - **Index Fragmentation:** Random distribution causes random page writes, bloating B-Tree indexes.
  - **No Time Locality:** Cannot use the PK for time-based queries or partition pruning.
  - **Storage:** 16 bytes (128 bits), though efficient, is larger than 64-bit integers.

### 2. Snowflake ID (Twitter/Discord style)
- **Pros:**
  - **Time-Ordered:** 64-bit integers with a timestamp component.
  - **Index Efficiency:** Appends to the right of the B-Tree, minimizing splits.
  - **Partition Pruning:** Queries on ID implicitly query on time.
- **Cons:**
  - **Infrastructure Complexity:** Requires a unique "Worker ID" per instance to avoid collisions. This adds operational complexity (ZooKeeper/Etcd or static config).
  - **Type Changes:** Migrating UUID (128-bit) columns to BigInt (64-bit) is a massive breaking change for FKs and application logic.

### 3. UUID v7 (The Middle Ground)
- **Pros:**
  - **Time-Ordered:** Embeds a timestamp in the first 48 bits.
  - **Compatible:** It is still a 128-bit UUID. No schema type change (still `uuid` in Postgres).
  - **Index Efficiency:** Better than v4, similar to Snowflake.
- **Cons:**
  - **Library Support:** Native support is newer (Python 3.13+ has better support, or external libs).
  - **Migration:** Existing data is still v4 (random). Only new data would be sequential.

## Plan: Range Partitioning Implementation

We will implement the strategy defined in `backend/docs/DB_PARTITIONING_STRATEGY.md` with slight refinements.

### Target Table: `chat_messages`
This table is high-volume, append-only, and queried primarily by time (recent sessions).

### Step 1: Migration Strategy (Zero Downtime preferred, but low-traffic window acceptable)

1.  **Rename**: `ALTER TABLE chat_messages RENAME TO chat_messages_old;`
2.  **Create Partitioned Table**:
    ```sql
    CREATE TABLE chat_messages (
        -- ... columns ...
        PRIMARY KEY (id, created_at)
    ) PARTITION BY RANGE (created_at);
    ```
3.  **Create Partitions**:
    - `chat_messages_default`: For historical data (or specific ranges if we want to backfill).
    - `chat_messages_2024_q1`, `chat_messages_2024_q2`, etc.
    - `chat_messages_2025_q1` (Current)
4.  **Data Migration**: Batch copy from `chat_messages_old` to `chat_messages`.
5.  **Validation**: Verify counts and integrity.
6.  **Swap**: The application will seamlessly write to the new table (since the name matches).

### Step 2: Code Adjustments

- **Composite PKs**: SQLAlchemy and Go models need to respect that the PK is now composite `(id, created_at)`.
    - *Correction*: Application code often selects by `id`. In Postgres partitioning, `SELECT * FROM chat_messages WHERE id = ?` works but scans all partitions (inefficient).
    - **Optimization**: Update high-frequency queries to include `created_at` where possible: `SELECT * FROM chat_messages WHERE id = ? AND created_at = ?`.
    - If `created_at` is unknown (e.g., getting a specific message by ID link), the global index overhead is acceptable for now, or we can maintain a separate lookup table (though that defeats the purpose).
    - *Actually*, since we only partition `chat_messages`, and it's mostly accessed via `session_id` (which implies a time range) or by the AI engine (context loading), we are mostly fine.

### Step 3: Outbox Events (Future Proofing)

The `event_outbox` table is another candidate. For this phase, we will apply a **retention policy** (Deletion) rather than partitioning, as processed events don't need to be kept forever in the hot store.

## Todo Update

I will now proceed to create the migration script for `chat_messages`.
