"""add_accountability_liked_by

Revision ID: d1e2f3a4b5c6
Revises: c8e4f2a3b1d6
Create Date: 2026-03-18 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c8e4f2a3b1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accountability_checkin",
        sa.Column(
            "liked_by",
            postgresql.JSONB(),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("accountability_checkin", "liked_by")
