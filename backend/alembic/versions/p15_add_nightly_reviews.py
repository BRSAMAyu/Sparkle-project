"""add nightly reviews phase2

Revision ID: p15_add_nightly_reviews
Revises: p14_add_semantic_memory_phase2
Create Date: 2026-01-15 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.models.base import GUID


revision = "p15_add_nightly_reviews"
down_revision = "p14_add_semantic_memory_phase2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nightly_reviews",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=False),
        sa.Column("summary_text", sa.String(length=2000), nullable=True),
        sa.Column("todo_items", sa.JSON(), nullable=True),
        sa.Column("evidence_refs", sa.JSON(), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "review_date")
    )
    op.create_index("idx_nightly_reviews_user", "nightly_reviews", ["user_id"], unique=False)
    op.create_index("idx_nightly_reviews_date", "nightly_reviews", ["review_date"], unique=False)


def downgrade():
    op.drop_index("idx_nightly_reviews_date", table_name="nightly_reviews")
    op.drop_index("idx_nightly_reviews_user", table_name="nightly_reviews")
    op.drop_table("nightly_reviews")
