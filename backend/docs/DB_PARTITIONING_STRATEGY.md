# Database Partitioning Strategy: `chat_messages`

## 1. Foreign Key Analysis

The `chat_messages` table is referenced by the following tables, which will be affected by partitioning:

1.  **`group_messages` (reply_to_id, thread_root_id)**:
    *   Self-referencing foreign keys are tricky with partitioning.
    *   If `group_messages` is partitioned (planned for future), these constraints need careful handling.
    *   Currently, `chat_messages` is for AI chats, while `group_messages` is for community. They seem distinct but share similar structures.
    *   *Correction*: `chat_messages` is NOT referenced by `group_messages`. `group_messages` references itself.

2.  **`chat_messages` self-references (implicit)**:
    *   The schema does not show explicit `reply_to_id` in `chat_messages`, but logical threading exists via `session_id`.
    *   The `message_id` has a unique constraint `chat_messages_message_id_key`.

3.  **No Direct Foreign Keys found referencing `chat_messages` in `schema.sql`**:
    *   I searched `REFERENCES public.chat_messages` and found **0 results**.
    *   This is excellent news. It means `chat_messages` is a leaf node in the dependency graph regarding incoming FKs.
    *   *Verification*: `chat_messages` has FKs TO `tasks` and `users`. But nothing points TO it.

## 2. Partitioning Strategy (Range Partitioning by `created_at`)

Since there are no incoming foreign keys, we can proceed with standard range partitioning without complex composite key refactoring for other tables.

### Steps:

1.  **Rename Existing Table**:
    ```sql
    ALTER TABLE chat_messages RENAME TO chat_messages_old;
    ```

2.  **Create Partitioned Parent Table**:
    *   Must include the partition key (`created_at`) in the primary key.
    *   Original PK was `id`. New PK must be `(id, created_at)`.
    ```sql
    CREATE TABLE chat_messages (
        user_id uuid NOT NULL,
        task_id uuid,
        session_id uuid NOT NULL,
        message_id character varying(36),
        role public.messagerole NOT NULL,
        content text NOT NULL,
        actions json,
        parse_degraded boolean,
        tokens_used integer,
        model_name character varying(100),
        id uuid NOT NULL,
        created_at timestamp without time zone NOT NULL,
        updated_at timestamp without time zone NOT NULL,
        deleted_at timestamp without time zone,
        PRIMARY KEY (id, created_at) -- Composite PK required
    ) PARTITION BY RANGE (created_at);
    ```

3.  **Create Partitions**:
    ```sql
    CREATE TABLE chat_messages_2024_q1 PARTITION OF chat_messages
        FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
    -- ... future partitions
    ```

4.  **Migrate Data**:
    ```sql
    INSERT INTO chat_messages SELECT * FROM chat_messages_old;
    ```

5.  **Recreate Indexes**:
    *   `idx_chat_created_at` (Essential for partition pruning)
    *   `idx_chat_session_id`
    *   `idx_chat_user_id`

6.  **Cleanup**:
    *   Drop `chat_messages_old` after verification.

## 3. Implementation Plan

We will create an Alembic migration script to perform this operation safely.

**Risks**:
*   Changing PK from `id` to `(id, created_at)` might affect application logic if it relies on `id` uniqueness globally (it still is, but DB enforces it differently).
*   Code relying on `get_by_id` might need `created_at` hint for performance, though `id` lookup still works (scans all partitions if no constraint).
*   **Crucial**: Since `message_id` (string) had a unique constraint, we must ensure it remains unique. Global uniqueness indexes on partitioned tables are hard.
    *   *Solution*: We might drop the strict DB-level unique constraint on `message_id` and rely on application logic + UUID generation, OR include `created_at` in that unique index too.

## 4. Constraint Handling

*   **Foreign Keys (Outgoing)**: `task_id` -> `tasks(id)`, `user_id` -> `users(id)`. These are fine.
*   **Unique Constraints**: `chat_messages_message_id_key` (on `message_id`).
    *   PostgreSQL requires unique constraints on partitioned tables to include the partition key.
    *   New Constraint: `UNIQUE (message_id, created_at)`.
    *   *Implication*: Theoretically allows duplicate `message_id` if they have different `created_at`. In practice, UUIDs prevent this.

## 5. Automation

Use `pg_partman` (if available) or a scheduled Celery task to create future partitions.
