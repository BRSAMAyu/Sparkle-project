"""add task resource links and plan stage

Revision ID: p22_task_resources_and_plan_stage
Revises: p21_plan_execution_records
Create Date: 2026-01-28 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.utils.migration_helpers import get_inspector, table_exists, column_exists, index_exists


# revision identifiers, used by Alembic.
revision: str = "p22_task_resources_and_plan_stage"
down_revision: Union[str, None] = "p21_plan_execution_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()

    if not table_exists(inspector, "task_resource_links"):
        op.create_table(
            "task_resource_links",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_type", sa.String(length=50), nullable=False),
            sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("url", sa.String(length=500), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        op.create_foreign_key(
            "fk_task_resource_links_task_id",
            "task_resource_links",
            "tasks",
            ["task_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index("idx_task_resource_links_task_id", "task_resource_links", ["task_id"])
        op.create_index(
            "idx_task_resource_links_task_type",
            "task_resource_links",
            ["task_id", "resource_type"],
        )
        op.create_index("idx_task_resource_links_resource_id", "task_resource_links", ["resource_id"])

    if not table_exists(inspector, "task_knowledge_links"):
        op.create_table(
            "task_knowledge_links",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("knowledge_node_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("relation_type", sa.String(length=50), nullable=False, server_default="related"),
            sa.Column("strength", sa.Float(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        op.create_foreign_key(
            "fk_task_knowledge_links_task_id",
            "task_knowledge_links",
            "tasks",
            ["task_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_foreign_key(
            "fk_task_knowledge_links_node_id",
            "task_knowledge_links",
            "knowledge_nodes",
            ["knowledge_node_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index("idx_task_knowledge_links_task_id", "task_knowledge_links", ["task_id"])
        op.create_index(
            "idx_task_knowledge_links_task_node",
            "task_knowledge_links",
            ["task_id", "knowledge_node_id"],
        )

    if not column_exists(inspector, "plans", "plan_stage"):
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'planstage') THEN
                    CREATE TYPE planstage AS ENUM ('sprint', 'daily', 'review', 'paused');
                END IF;
            END $$;
            """
        )
        op.add_column(
            "plans",
            sa.Column(
                "plan_stage",
                sa.Enum("sprint", "daily", "review", "paused", name="planstage", create_type=False),
                nullable=False,
                server_default="daily",
            ),
        )
        if not index_exists(inspector, "plans", "idx_plans_stage"):
            op.create_index("idx_plans_stage", "plans", ["plan_stage"])


def downgrade() -> None:
    inspector = get_inspector()

    if index_exists(inspector, "plans", "idx_plans_stage"):
        op.drop_index("idx_plans_stage", table_name="plans")
    if column_exists(inspector, "plans", "plan_stage"):
        op.drop_column("plans", "plan_stage")
        op.execute("DROP TYPE IF EXISTS planstage")

    if table_exists(inspector, "task_knowledge_links"):
        op.drop_table("task_knowledge_links")

    if table_exists(inspector, "task_resource_links"):
        op.drop_table("task_resource_links")
