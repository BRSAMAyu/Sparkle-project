"""add user_similarities and item_similarities tables

Revision ID: z1a2b3c4d5e6
Revises: a6e9c1f4d2b3
Create Date: 2026-03-18 03:00:00
"""

from alembic import op
import sqlalchemy as sa

from app.models.base import GUID


# revision identifiers, used by Alembic.
revision = "z1a2b3c4d5e6"
down_revision = "a6e9c1f4d2b3"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "user_similarities"):
        op.create_table(
            "user_similarities",
            sa.Column("user_id_1", GUID(), nullable=False),
            sa.Column("user_id_2", GUID(), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=False),
            sa.Column("common_items_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("common_subjects", sa.JSON(), nullable=True),
            sa.Column("last_calculated_at", sa.DateTime(), nullable=False),
            sa.Column("calculation_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("id", GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id_1"], ["users.id"]),
            sa.ForeignKeyConstraint(["user_id_2"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id_1", "user_id_2", name="uq_user_similarity_pair"),
        )
        op.create_index("idx_user_sim_user1", "user_similarities", ["user_id_1"])
        op.create_index("idx_user_sim_user2", "user_similarities", ["user_id_2"])
        op.create_index("idx_user_sim_score", "user_similarities", ["similarity_score"])
        op.create_index(
            "ix_user_similarities_deleted_at",
            "user_similarities",
            ["deleted_at"],
        )

    if not _has_table(bind, "item_similarities"):
        op.create_table(
            "item_similarities",
            sa.Column("item_id_1", GUID(), nullable=False),
            sa.Column("item_type_1", sa.String(length=50), nullable=False),
            sa.Column("item_id_2", GUID(), nullable=False),
            sa.Column("item_type_2", sa.String(length=50), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=False),
            sa.Column("common_learners", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_calculated_at", sa.DateTime(), nullable=False),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("id", GUID(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "item_id_1", "item_type_1", "item_id_2", "item_type_2",
                name="uq_item_similarity_pair"
            ),
        )
        op.create_index("idx_item_sim_item1", "item_similarities", ["item_id_1"])
        op.create_index("idx_item_sim_item2", "item_similarities", ["item_id_2"])
        op.create_index("idx_item_sim_score", "item_similarities", ["similarity_score"])
        op.create_index(
            "ix_item_similarities_deleted_at",
            "item_similarities",
            ["deleted_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _has_table(bind, "item_similarities"):
        op.drop_index("ix_item_similarities_deleted_at", table_name="item_similarities")
        op.drop_index("idx_item_sim_score", table_name="item_similarities")
        op.drop_index("idx_item_sim_item2", table_name="item_similarities")
        op.drop_index("idx_item_sim_item1", table_name="item_similarities")
        op.drop_table("item_similarities")

    if _has_table(bind, "user_similarities"):
        op.drop_index("ix_user_similarities_deleted_at", table_name="user_similarities")
        op.drop_index("idx_user_sim_score", table_name="user_similarities")
        op.drop_index("idx_user_sim_user2", table_name="user_similarities")
        op.drop_index("idx_user_sim_user1", table_name="user_similarities")
        op.drop_table("user_similarities")
