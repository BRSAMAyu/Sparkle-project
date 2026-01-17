"""add nightly review feedback fields

Revision ID: p16_add_nightly_review_feedback
Revises: p15_add_nightly_reviews
Create Date: 2026-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.utils.migration_helpers import column_exists, get_inspector, table_exists


revision = "p16_add_nightly_review_feedback"
down_revision = "p15_add_nightly_reviews"
branch_labels = None
depends_on = None


def upgrade():
    inspector = get_inspector()
    if table_exists(inspector, "nightly_reviews") and not column_exists(inspector, "nightly_reviews", "reviewed_at"):
        op.add_column("nightly_reviews", sa.Column("reviewed_at", sa.DateTime(), nullable=True))


def downgrade():
    inspector = get_inspector()
    if table_exists(inspector, "nightly_reviews") and column_exists(inspector, "nightly_reviews", "reviewed_at"):
        op.drop_column("nightly_reviews", "reviewed_at")
