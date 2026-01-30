"""merge heads aa12/add_subtasks/multi_plan_state_support

Revision ID: c9f1a2b3c4d5
Revises: aa12bb34cc56, add_subtasks, multi_plan_state_support
Create Date: 2026-01-26
"""

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "c9f1a2b3c4d5"
down_revision = ("aa12bb34cc56", "add_subtasks", "multi_plan_state_support")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
