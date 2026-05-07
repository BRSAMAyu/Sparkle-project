"""add metadata jsonb column to chat_messages

Revision ID: wp19_20260507
Revises: z1a2b3c4d5e6
Create Date: 2026-05-07 00:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "wp19_20260507"
down_revision: str | None = "z1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _column_exists(table_name: str, column_name: str) -> bool:
    result = op.get_bind().execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.first() is not None


def upgrade() -> None:
    if not _is_postgresql():
        return

    if not _column_exists("chat_messages", "metadata"):
        op.execute(
            sa.text(
                """
                ALTER TABLE public.chat_messages
                ADD COLUMN metadata jsonb
                """
            )
        )


def downgrade() -> None:
    if not _is_postgresql():
        return

    if _column_exists("chat_messages", "metadata"):
        op.execute(
            sa.text(
                """
                ALTER TABLE public.chat_messages
                DROP COLUMN metadata
                """
            )
        )
