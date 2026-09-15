"""add group knowledge base trust hierarchy and galaxy scope

Revision ID: gkb001_group_knowledge_base
Revises: df1a2b3c4d5e, gnd001_node_documents
Create Date: 2026-04-26 12:00:00
"""

from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID


revision: str = "gkb001_group_knowledge_base"
down_revision: str | tuple[str, str] | None = ("df1a2b3c4d5e", "gnd001_node_documents")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    trust_level_enum = sa.Enum("official", "verified", "member", name="groupfiletrustlevel")
    trust_level_enum.create(bind, checkfirst=True)

    op.add_column(
        "group_files",
        sa.Column("trust_level", trust_level_enum, nullable=False, server_default="member"),
    )
    op.add_column(
        "group_files",
        sa.Column("is_knowledge_base", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "group_files",
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "group_files",
        sa.Column("citation_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "group_files",
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "group_files",
        sa.Column("rating_total", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_index("ix_group_files_trust_level", "group_files", ["trust_level"], unique=False)
    op.create_index("ix_group_files_is_knowledge_base", "group_files", ["is_knowledge_base"], unique=False)
    op.create_index(
        "idx_group_files_knowledge_base",
        "group_files",
        ["group_id", "is_knowledge_base"],
        unique=False,
    )

    op.add_column(
        "collaborative_galaxies",
        sa.Column("group_id", GUID(), nullable=True),
    )
    op.add_column(
        "collaborative_galaxies",
        sa.Column("galaxy_scope", sa.String(length=32), nullable=False, server_default="shared"),
    )
    op.create_foreign_key(
        "fk_collaborative_galaxies_group_id",
        "collaborative_galaxies",
        "groups",
        ["group_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_collaborative_galaxies_group_id", "collaborative_galaxies", ["group_id"], unique=False)
    op.create_index("ix_collaborative_galaxies_galaxy_scope", "collaborative_galaxies", ["galaxy_scope"], unique=False)
    op.create_unique_constraint(
        "uq_collaborative_galaxies_group_id",
        "collaborative_galaxies",
        ["group_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_collaborative_galaxies_group_id", "collaborative_galaxies", type_="unique")
    op.drop_index("ix_collaborative_galaxies_galaxy_scope", table_name="collaborative_galaxies")
    op.drop_index("ix_collaborative_galaxies_group_id", table_name="collaborative_galaxies")
    op.drop_constraint("fk_collaborative_galaxies_group_id", "collaborative_galaxies", type_="foreignkey")
    op.drop_column("collaborative_galaxies", "galaxy_scope")
    op.drop_column("collaborative_galaxies", "group_id")

    op.drop_index("idx_group_files_knowledge_base", table_name="group_files")
    op.drop_index("ix_group_files_is_knowledge_base", table_name="group_files")
    op.drop_index("ix_group_files_trust_level", table_name="group_files")
    op.drop_column("group_files", "rating_total")
    op.drop_column("group_files", "rating_count")
    op.drop_column("group_files", "citation_count")
    op.drop_column("group_files", "download_count")
    op.drop_column("group_files", "is_knowledge_base")
    op.drop_column("group_files", "trust_level")

    trust_level_enum = sa.Enum("official", "verified", "member", name="groupfiletrustlevel")
    trust_level_enum.drop(op.get_bind(), checkfirst=True)
