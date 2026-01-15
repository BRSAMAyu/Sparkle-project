"""Merge TEMPLATE_SAFE_MIGRATION and p15_feedback heads.

Revision ID: merge_template_safe_p15_feedback
Revises: TEMPLATE_SAFE_MIGRATION, p15_feedback
Create Date: 2026-02-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "merge_template_safe_p15_feedback"
down_revision: Union[str, Sequence[str], None] = ("TEMPLATE_SAFE_MIGRATION", "p15_feedback")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
