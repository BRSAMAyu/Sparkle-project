"""add capsule personalization context

Revision ID: c2a8f1e9d0b3
Revises: fb26d4a1c9e2
Create Date: 2026-03-15 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2a8f1e9d0b3"
down_revision = "fb26d4a1c9e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "curiosity_capsules",
        sa.Column("personalization_context", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("curiosity_capsules", "personalization_context")
