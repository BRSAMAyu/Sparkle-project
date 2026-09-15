"""add seed library ratings

Revision ID: a4b5c6d7e8f9
Revises: f7a9c3e2d1b4
Create Date: 2026-03-22 22:35:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.models.base


# revision identifiers, used by Alembic.
revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "f7a9c3e2d1b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seed_library_ratings",
        sa.Column("id", app.models.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", app.models.base.GUID(), nullable=False),
        sa.Column("library_id", app.models.base.GUID(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["library_id"], ["seed_libraries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "library_id", name="uq_seed_library_ratings_user_library"),
    )
    op.create_index(
        "ix_seed_library_ratings_library_id",
        "seed_library_ratings",
        ["library_id"],
        unique=False,
    )
    op.create_index(
        "ix_seed_library_ratings_user_id",
        "seed_library_ratings",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_seed_library_ratings_user_id", table_name="seed_library_ratings")
    op.drop_index("ix_seed_library_ratings_library_id", table_name="seed_library_ratings")
    op.drop_table("seed_library_ratings")
