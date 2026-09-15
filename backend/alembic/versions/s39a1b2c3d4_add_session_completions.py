"""add stage39 session completion ledger

Revision ID: s39a1b2c3d4
Revises: s31a1b2c3d4
Create Date: 2026-04-23 10:10:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s39a1b2c3d4"
down_revision: Union[str, None] = "s31a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.String(length=36)
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "session_completions",
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("user_id", _uuid_type(), nullable=False),
        sa.Column("completion_type", sa.String(length=64), nullable=False),
        sa.Column("source_event", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index(
        "ix_session_completions_user_id",
        "session_completions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_completions_user_id_created_at",
        "session_completions",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_session_completions_user_id_created_at", table_name="session_completions")
    op.drop_index("ix_session_completions_user_id", table_name="session_completions")
    op.drop_table("session_completions")
