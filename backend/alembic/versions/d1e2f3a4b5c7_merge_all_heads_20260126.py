"""merge all heads (c9f1a2b3c4d5, ff4a5b6c7d8e, p22_task_resources_and_plan_stage, p22_unified_vocabulary_system)

Revision ID: d1e2f3a4b5c7
Revises: c9f1a2b3c4d5, ff4a5b6c7d8e, p22_task_resources_and_plan_stage, p22_unified_vocabulary_system
Create Date: 2026-01-26
"""

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision = "d1e2f3a4b5c7"
down_revision = (
    "c9f1a2b3c4d5",
    "ff4a5b6c7d8e",
    "p22_task_resources_and_plan_stage",
    "p22_unified_vocabulary_system",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
