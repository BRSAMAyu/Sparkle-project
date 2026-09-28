"""V4-I06 · add context_selection_receipts table (context_selection_receipt.v1 落库面)

合同：v4/evidence/V4-B05/contract_receipt_min.md §2。
结构由 app.models.context_selection_receipt.ContextSelectionReceiptRow 定义；
契约结构（candidates/budget/why_now/input_versions）走 JSONB，校验唯一权威在
app.core.context_selection_receipt（表不造第二真值）。

Revision ID: i06_20260928
Revises: wt598_20260927
Create Date: 2026-09-28
"""

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

# revision identifiers, used by Alembic.
revision = "i06_20260928"
down_revision = "wt598_20260927"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, "context_selection_receipts"):
        return
    op.create_table(
        "context_selection_receipts",
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("receipt_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("selection_role", sa.String(length=40), nullable=False),
        sa.Column("decision_id", sa.String(length=64), nullable=True),
        sa.Column("memory_epoch", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selector_version", sa.String(length=120), nullable=False),
        sa.Column("input_versions", sa.JSON(), nullable=False),
        sa.Column("candidates", sa.JSON(), nullable=False),
        sa.Column("budget", sa.JSON(), nullable=False),
        sa.Column("why_now", sa.JSON(), nullable=True),
        sa.Column("pack_run_id", GUID(), nullable=True),
        sa.Column("request_id", sa.String(length=100), nullable=True),
        sa.Column("trace_id", sa.String(length=100), nullable=True),
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("receipt_id", name="uq_context_selection_receipts_receipt_id"),
    )
    op.create_index(
        "idx_context_selection_receipts_user_created",
        "context_selection_receipts",
        ["user_id", "created_at"],
    )
    op.create_index("idx_context_selection_receipts_user_id", "context_selection_receipts", ["user_id"])
    op.create_index("idx_context_selection_receipts_role", "context_selection_receipts", ["selection_role"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, "context_selection_receipts"):
        return
    op.drop_index("idx_context_selection_receipts_role", table_name="context_selection_receipts")
    op.drop_index("idx_context_selection_receipts_user_id", table_name="context_selection_receipts")
    op.drop_index("idx_context_selection_receipts_user_created", table_name="context_selection_receipts")
    op.drop_table("context_selection_receipts")
