"""add srl phase states table

Revision ID: s29a1b2c3d4
Revises: s28a1b2c3d4
Create Date: 2026-04-21 15:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "s29a1b2c3d4"
down_revision = "s28a1b2c3d4"
branch_labels = None
depends_on = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _json_type() -> sa.JSON:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _uuid_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.String(length=36)
    return postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "srl_phase_states"):
        op.create_table(
            "srl_phase_states",
            sa.Column("user_id", _uuid_type(), nullable=False),
            sa.Column("current_phase", sa.String(length=32), nullable=False, server_default="UNKNOWN"),
            sa.Column("phase_started_at", sa.DateTime(), nullable=False),
            sa.Column("previous_phase", sa.String(length=32), nullable=True),
            sa.Column("transition_evidence_ids", _json_type(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="default"),
            sa.Column("id", _uuid_type(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id"),
        )

    inspector = sa.inspect(bind)
    deleted_at_index = op.f("ix_srl_phase_states_deleted_at")
    user_id_index = op.f("ix_srl_phase_states_user_id")
    if not _index_exists(inspector, "srl_phase_states", deleted_at_index):
        op.create_index(deleted_at_index, "srl_phase_states", ["deleted_at"], unique=False)
    if not _index_exists(inspector, "srl_phase_states", user_id_index):
        op.create_index(user_id_index, "srl_phase_states", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_srl_phase_states_user_id"), table_name="srl_phase_states")
    op.drop_index(op.f("ix_srl_phase_states_deleted_at"), table_name="srl_phase_states")
    op.drop_table("srl_phase_states")
