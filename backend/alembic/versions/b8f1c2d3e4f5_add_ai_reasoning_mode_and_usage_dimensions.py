"""add_ai_reasoning_mode_and_usage_dimensions

Revision ID: b8f1c2d3e4f5
Revises: a9c4e7f1b2d3
Create Date: 2026-03-20 22:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "b8f1c2d3e4f5"
down_revision: Union[str, None] = "a9c4e7f1b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("user_settings") and not _has_column(inspector, "user_settings", "ai_reasoning_mode"):
        with op.batch_alter_table("user_settings", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("ai_reasoning_mode", sa.String(length=16), nullable=False, server_default="balanced")
            )

    if inspector.has_table("token_usage"):
        with op.batch_alter_table("token_usage", schema=None) as batch_op:
            if not _has_column(inspector, "token_usage", "model_tier"):
                batch_op.add_column(sa.Column("model_tier", sa.String(length=40), nullable=True))
            if not _has_column(inspector, "token_usage", "ai_reasoning_mode"):
                batch_op.add_column(
                    sa.Column("ai_reasoning_mode", sa.String(length=16), nullable=False, server_default="balanced")
                )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if inspector.has_table("token_usage"):
        with op.batch_alter_table("token_usage", schema=None) as batch_op:
            if _has_column(inspector, "token_usage", "ai_reasoning_mode"):
                batch_op.drop_column("ai_reasoning_mode")
            if _has_column(inspector, "token_usage", "model_tier"):
                batch_op.drop_column("model_tier")

    if inspector.has_table("user_settings") and _has_column(inspector, "user_settings", "ai_reasoning_mode"):
        with op.batch_alter_table("user_settings", schema=None) as batch_op:
            batch_op.drop_column("ai_reasoning_mode")
