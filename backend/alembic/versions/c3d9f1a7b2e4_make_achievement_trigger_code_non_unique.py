"""make achievement trigger code non unique

Revision ID: c3d9f1a7b2e4
Revises: a8c2f4d9b1e7
Create Date: 2026-03-10 13:30:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "c3d9f1a7b2e4"
down_revision = "a8c2f4d9b1e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_achievements_trigger_code", table_name="achievements")
    op.create_index("ix_achievements_trigger_code", "achievements", ["trigger_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_achievements_trigger_code", table_name="achievements")
    op.create_index("ix_achievements_trigger_code", "achievements", ["trigger_code"], unique=True)
