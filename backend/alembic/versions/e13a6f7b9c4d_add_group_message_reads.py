"""add group message reads

Revision ID: e13a6f7b9c4d
Revises: d4f7a2c9b3e1
Create Date: 2026-03-13 15:10:00
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "e13a6f7b9c4d"
down_revision = "d4f7a2c9b3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = postgresql.UUID(as_uuid=True).with_variant(sa.String(length=36), "sqlite")
    op.create_table(
        "group_message_reads",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("message_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["group_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_group_message_read"),
    )
    op.create_index(
        "ix_group_message_reads_deleted_at",
        "group_message_reads",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_group_message_reads_message_id",
        "group_message_reads",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        "ix_group_message_reads_user_id",
        "group_message_reads",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "idx_group_message_read_message",
        "group_message_reads",
        ["message_id", "read_at"],
        unique=False,
    )
    op.create_index(
        "idx_group_message_read_user",
        "group_message_reads",
        ["user_id", "read_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_group_message_read_user", table_name="group_message_reads")
    op.drop_index("idx_group_message_read_message", table_name="group_message_reads")
    op.drop_index("ix_group_message_reads_user_id", table_name="group_message_reads")
    op.drop_index("ix_group_message_reads_message_id", table_name="group_message_reads")
    op.drop_index("ix_group_message_reads_deleted_at", table_name="group_message_reads")
    op.drop_table("group_message_reads")
