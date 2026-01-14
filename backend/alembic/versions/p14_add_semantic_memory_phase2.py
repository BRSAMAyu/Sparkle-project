"""add semantic memory phase2 tables

Revision ID: p14_add_semantic_memory_phase2
Revises: p13_add_event_stream_state
Create Date: 2026-01-15 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID
from app.utils.migration_helpers import get_inspector, index_exists, table_exists


revision = "p14_add_semantic_memory_phase2"
down_revision = "p13_add_event_stream_state"
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    if not table_exists(inspector, "strategy_nodes"):
        op.create_table(
            "strategy_nodes",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("user_id", GUID(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.String(length=2000), nullable=True),
            sa.Column("subject_code", sa.String(length=50), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("content_hash", sa.String(length=64), nullable=True),
            sa.Column("source_type", sa.String(length=20), nullable=False),
            sa.Column("evidence_refs", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id")
        )
    if not index_exists(inspector, "strategy_nodes", "idx_strategy_nodes_user"):
        op.create_index("idx_strategy_nodes_user", "strategy_nodes", ["user_id"], unique=False)
    if not index_exists(inspector, "strategy_nodes", "idx_strategy_nodes_hash"):
        op.create_index("idx_strategy_nodes_hash", "strategy_nodes", ["content_hash"], unique=False)

    if not table_exists(inspector, "semantic_links"):
        op.create_table(
            "semantic_links",
            sa.Column("id", GUID(), nullable=False),
            sa.Column("source_type", sa.String(length=30), nullable=False),
            sa.Column("source_id", sa.String(length=64), nullable=False),
            sa.Column("target_type", sa.String(length=30), nullable=False),
            sa.Column("target_id", sa.String(length=64), nullable=False),
            sa.Column("relation_type", sa.String(length=40), nullable=False),
            sa.Column("strength", sa.Float(), nullable=False),
            sa.Column("created_by", sa.String(length=20), nullable=False),
            sa.Column("evidence_refs", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id")
        )
    if not index_exists(inspector, "semantic_links", "idx_semantic_links_source"):
        op.create_index("idx_semantic_links_source", "semantic_links", ["source_type", "source_id"], unique=False)
    if not index_exists(inspector, "semantic_links", "idx_semantic_links_target"):
        op.create_index("idx_semantic_links_target", "semantic_links", ["target_type", "target_id"], unique=False)
    if not index_exists(inspector, "semantic_links", "idx_semantic_links_relation"):
        op.create_index("idx_semantic_links_relation", "semantic_links", ["relation_type"], unique=False)


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "semantic_links"):
        if index_exists(inspector, "semantic_links", "idx_semantic_links_relation"):
            op.drop_index("idx_semantic_links_relation", table_name="semantic_links")
        if index_exists(inspector, "semantic_links", "idx_semantic_links_target"):
            op.drop_index("idx_semantic_links_target", table_name="semantic_links")
        if index_exists(inspector, "semantic_links", "idx_semantic_links_source"):
            op.drop_index("idx_semantic_links_source", table_name="semantic_links")
        op.drop_table("semantic_links")

    if table_exists(inspector, "strategy_nodes"):
        if index_exists(inspector, "strategy_nodes", "idx_strategy_nodes_hash"):
            op.drop_index("idx_strategy_nodes_hash", table_name="strategy_nodes")
        if index_exists(inspector, "strategy_nodes", "idx_strategy_nodes_user"):
            op.drop_index("idx_strategy_nodes_user", table_name="strategy_nodes")
        op.drop_table("strategy_nodes")
