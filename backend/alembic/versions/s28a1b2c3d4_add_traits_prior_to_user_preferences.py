"""add traits prior fields to user_preferences_center

Revision ID: s28a1b2c3d4
Revises: s27a1b2c3d4
Create Date: 2026-04-21 10:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "s28a1b2c3d4"
down_revision = "s27a1b2c3d4"
branch_labels = None
depends_on = None


def _json_type() -> sa.JSON:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    with op.batch_alter_table("user_preferences_center") as batch_op:
        batch_op.add_column(
            sa.Column("traits_prior", _json_type(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(
            sa.Column("trait_observation_state", _json_type(), nullable=False, server_default=sa.text("'{}'"))
        )
        batch_op.add_column(sa.Column("traits_coldstart_completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_preferences_center") as batch_op:
        batch_op.drop_column("traits_coldstart_completed_at")
        batch_op.drop_column("trait_observation_state")
        batch_op.drop_column("traits_prior")
