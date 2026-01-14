"""partition_chat_messages

Revision ID: 087653ac70dd
Revises: p5_community_advanced_features
Create Date: 2026-01-03 21:21:28.063000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.utils.migration_helpers import (
    foreign_key_exists,
    get_inspector,
    is_partitioned_table,
    table_exists,
)

# revision identifiers, used by Alembic.
revision = '087653ac70dd'
down_revision = 'c40859dd0336'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = get_inspector()

    if table_exists(inspector, "chat_messages") and is_partitioned_table(bind, "chat_messages"):
        # Ensure partitions exist (safe for re-runs)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_legacy PARTITION OF chat_messages
            FOR VALUES FROM (MINVALUE) TO ('2024-01-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2024_q1 PARTITION OF chat_messages
            FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2024_q2 PARTITION OF chat_messages
            FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2024_q3 PARTITION OF chat_messages
            FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2024_q4 PARTITION OF chat_messages
            FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2025_q1 PARTITION OF chat_messages
            FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2025_q2 PARTITION OF chat_messages
            FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2025_q3 PARTITION OF chat_messages
            FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2025_q4 PARTITION OF chat_messages
            FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2026_q1 PARTITION OF chat_messages
            FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_2026_q2 PARTITION OF chat_messages
            FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');
        """)
        op.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages_default PARTITION OF chat_messages
            DEFAULT;
        """)
        op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_message_id_created_at_key
        ON chat_messages (message_id, created_at)
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages (created_at)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_chat_session_id ON chat_messages (session_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_messages (user_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_chat_task_id ON chat_messages (task_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_chat_role ON chat_messages (role)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages (session_id, created_at DESC)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_deleted_at ON chat_messages (deleted_at)")

        inspector = get_inspector()
        if not foreign_key_exists(inspector, "chat_messages", "chat_messages_task_id_fkey"):
            op.execute("""
            ALTER TABLE chat_messages 
            ADD CONSTRAINT chat_messages_task_id_fkey 
            FOREIGN KEY (task_id) REFERENCES tasks(id)
            """)
        if not foreign_key_exists(inspector, "chat_messages", "chat_messages_user_id_fkey"):
            op.execute("""
            ALTER TABLE chat_messages 
            ADD CONSTRAINT chat_messages_user_id_fkey 
            FOREIGN KEY (user_id) REFERENCES users(id)
            """)
        return

    # 1. Rename existing table
    if table_exists(inspector, "chat_messages"):
        if table_exists(inspector, "chat_messages_old"):
            # Destructive reset for pre-data recovery to enable renaming.
            op.execute("DROP TABLE IF EXISTS chat_messages_old CASCADE")
        op.execute("ALTER TABLE IF EXISTS chat_messages RENAME TO chat_messages_old")
    
    # 2. Create parent partitioned table
    # Note: We must include created_at in the primary key for partitioning
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
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
        CONSTRAINT chat_messages_partitioned_pkey PRIMARY KEY (id, created_at)
    ) PARTITION BY RANGE (created_at);
    """)

    # 3. Create partitions
    # Initial partition for old data (up to 2024-01-01)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_legacy PARTITION OF chat_messages
        FOR VALUES FROM (MINVALUE) TO ('2024-01-01');
    """)

    # Quarterly partitions for 2024
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2024_q1 PARTITION OF chat_messages
        FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2024_q2 PARTITION OF chat_messages
        FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2024_q3 PARTITION OF chat_messages
        FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2024_q4 PARTITION OF chat_messages
        FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');
    """)
    
    # Quarterly partitions for 2025
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2025_q1 PARTITION OF chat_messages
        FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2025_q2 PARTITION OF chat_messages
        FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2025_q3 PARTITION OF chat_messages
        FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2025_q4 PARTITION OF chat_messages
        FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');
    """)

    # Quarterly partitions for 2026 (Future proofing)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2026_q1 PARTITION OF chat_messages
        FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');
    """)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_2026_q2 PARTITION OF chat_messages
        FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');
    """)

    # Default partition for anything else (safety net)
    op.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages_default PARTITION OF chat_messages
        DEFAULT;
    """)

    # 4. Data Migration
    inspector = get_inspector()
    if table_exists(inspector, "chat_messages_old"):
        op.execute("INSERT INTO chat_messages SELECT * FROM chat_messages_old ON CONFLICT DO NOTHING")

    # 5. Recreate Indexes on the partitioned table
    # Indices are automatically created on partitions if created on parent, 
    # but we need to create them on the parent now.
    
    # The unique constraint on message_id must now include created_at
    # We drop the strict global unique constraint on message_id and create a composite one
    op.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS chat_messages_message_id_created_at_key 
    ON chat_messages (message_id, created_at)
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_messages (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_session_id ON chat_messages (session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_messages (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_task_id ON chat_messages (task_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_role ON chat_messages (role)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created ON chat_messages (session_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chat_messages_deleted_at ON chat_messages (deleted_at)")

    # 6. Foreign Keys
    # Note: FKs *to* other tables are supported in partitioned tables.
    # We re-add them to the parent table.
    inspector = get_inspector()
    if not foreign_key_exists(inspector, "chat_messages", "chat_messages_task_id_fkey"):
        op.execute("""
        ALTER TABLE chat_messages 
        ADD CONSTRAINT chat_messages_task_id_fkey 
        FOREIGN KEY (task_id) REFERENCES tasks(id)
        """)
    
    if not foreign_key_exists(inspector, "chat_messages", "chat_messages_user_id_fkey"):
        op.execute("""
        ALTER TABLE chat_messages 
        ADD CONSTRAINT chat_messages_user_id_fkey 
        FOREIGN KEY (user_id) REFERENCES users(id)
        """)

    # 7. Cleanup
    # We keep chat_messages_old for now as backup, but rename it to indicate it's backup
    # In a real production scenario with huge data, we might drop it later.
    # op.execute("DROP TABLE chat_messages_old") 


def downgrade():
    inspector = get_inspector()

    # Reverse the process
    # 1. Drop partitioned table
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
    
    # 2. Restore old table
    if table_exists(inspector, "chat_messages_old"):
        op.execute("ALTER TABLE IF EXISTS chat_messages_old RENAME TO chat_messages")
    
    # 3. Restore Indexes and Constraints
    # Note: The original PK and indices might need to be explicitly recreated if renaming didn't preserve them perfectly 
    # (Renaming usually preserves them, but let's be safe regarding names)
    
    # The original PK was just (id)
    # The rename preserves the PK constraint name usually, but let's ensure.
    pass
