"""add critical composite indexes for task/goal hot paths

Revision ID: comp_idx_20260510
Revises: comp_idx_20260508
Create Date: 2026-05-10
"""

revision = 'comp_idx_20260510'
down_revision = 'comp_idx_20260508'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("COMMIT")
    # Composite index for task event consumer: SELECT ... FROM tasks WHERE plan_id = ? AND user_id = ? AND status = ?
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_plan_user_status
        ON tasks (plan_id, user_id, status);
    """)
    # Composite index for goal progress queries: SELECT * FROM goals WHERE plan_id = ?
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_goals_plan_id
        ON goals (plan_id);
    """)
    # notifications: SELECT ... WHERE user_id = ? AND is_read = false ORDER BY created_at DESC
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_notifications_user_read_created
        ON notifications (user_id, is_read, created_at DESC)
        WHERE deleted_at IS NULL;
    """)
    # user_state_snapshots: SELECT * ... WHERE user_id = ? ORDER BY snapshot_at DESC LIMIT 1
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_state_snapshots_user_snapshot
        ON user_state_snapshots (user_id, snapshot_at DESC);
    """)
    # friendships: accepted friends queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_friendships_user_status
        ON friendships (user_id, status);
    """)
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_friendships_friend_status
        ON friendships (friend_id, status);
    """)
    # error_records: 7/30-day lookback queries
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_records_user_created
        ON error_records (user_id, created_at DESC);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_tasks_plan_user_status;")
    op.execute("DROP INDEX IF EXISTS idx_goals_plan_id;")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_read_created;")
    op.execute("DROP INDEX IF EXISTS idx_user_state_snapshots_user_snapshot;")
    op.execute("DROP INDEX IF EXISTS idx_friendships_user_status;")
    op.execute("DROP INDEX IF EXISTS idx_friendships_friend_status;")
    op.execute("DROP INDEX IF EXISTS idx_error_records_user_created;")
