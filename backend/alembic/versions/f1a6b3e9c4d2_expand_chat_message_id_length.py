"""expand chat message id length

Revision ID: f1a6b3e9c4d2
Revises: d4f7a2c9b3e1
Create Date: 2026-03-07 23:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1a6b3e9c4d2"
down_revision = "d4f7a2c9b3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "chat_messages",
        "message_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=128),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "chat_messages",
        "message_id",
        existing_type=sa.String(length=128),
        type_=sa.String(length=36),
        existing_nullable=True,
    )
