"""add scene consolidation tables

Revision ID: s26a1b2c3d4
Revises: s24a1b2c3d4
Create Date: 2026-04-21 10:30:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "s26a1b2c3d4"
down_revision: Union[str, None] = "s24a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _index_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "scenes"):
        op.create_table(
            "scenes",
            sa.Column("scene_id", sa.String(length=80), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("summary", sa.String(length=200), nullable=False),
            sa.Column(
                "member_memory_ids",
                sa.JSON().with_variant(sa.JSON(), "sqlite"),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
            sa.Column(
                "centroid_embedding",
                pgvector.sqlalchemy.vector.VECTOR(dim=1024).with_variant(sa.JSON(), "sqlite"),
                nullable=True,
            ),
            sa.Column("time_start", sa.DateTime(), nullable=False),
            sa.Column("time_end", sa.DateTime(), nullable=False),
            sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("version", sa.String(length=32), nullable=False, server_default="scene.v1"),
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scene_id", name="uq_scenes_scene_id"),
        )

    inspector = sa.inspect(bind)
    if not _index_exists(inspector, "scenes", "idx_scenes_user_time_window"):
        op.create_index("idx_scenes_user_time_window", "scenes", ["user_id", "time_start", "time_end"], unique=False)
    if not _index_exists(inspector, "scenes", "idx_scenes_user_quality"):
        op.create_index("idx_scenes_user_quality", "scenes", ["user_id", "quality_score"], unique=False)
    if not _index_exists(inspector, "scenes", "idx_scenes_user_version"):
        op.create_index("idx_scenes_user_version", "scenes", ["user_id", "version"], unique=False)
    if not _index_exists(inspector, "scenes", "ix_scenes_scene_id"):
        op.create_index("ix_scenes_scene_id", "scenes", ["scene_id"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _table_exists(inspector, "scenes"):
        for index_name in (
            "ix_scenes_scene_id",
            "idx_scenes_user_version",
            "idx_scenes_user_quality",
            "idx_scenes_user_time_window",
        ):
            if _index_exists(inspector, "scenes", index_name):
                op.drop_index(index_name, table_name="scenes")
        op.drop_table("scenes")
