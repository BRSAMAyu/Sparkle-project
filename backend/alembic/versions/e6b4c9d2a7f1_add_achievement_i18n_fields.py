"""add achievement i18n fields

Revision ID: e6b4c9d2a7f1
Revises: d5e7a3c2b1f4
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e6b4c9d2a7f1"
down_revision = "d5e7a3c2b1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "achievements",
        sa.Column("name_i18n", sa.JSON(), nullable=True),
    )
    op.add_column(
        "achievements",
        sa.Column("description_i18n", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("achievements", "description_i18n")
    op.drop_column("achievements", "name_i18n")
