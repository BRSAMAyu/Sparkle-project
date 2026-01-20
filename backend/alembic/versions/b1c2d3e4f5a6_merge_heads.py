"""merge heads a7c9e1f2b3d4 and f6a1b2c3d4e5

Revision ID: b1c2d3e4f5a6
Revises: a7c9e1f2b3d4, f6a1b2c3d4e5
Create Date: 2026-01-21 00:00:00.000000
"""

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = ("a7c9e1f2b3d4", "f6a1b2c3d4e5")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
