"""add email_verified and token_revoked_before to users

Revision ID: c9f3b2a7e1d4
Revises: fb26d4a1c9e2
Create Date: 2026-03-15 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9f3b2a7e1d4"
down_revision: Union[str, None] = "fb26d4a1c9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("token_revoked_before", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("token_revoked_before")
        batch_op.drop_column("email_verified")
