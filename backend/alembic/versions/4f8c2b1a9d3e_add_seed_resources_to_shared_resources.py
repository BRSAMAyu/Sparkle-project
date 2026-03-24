"""add_seed_resources_to_shared_resources

Revision ID: 4f8c2b1a9d3e
Revises: 07fd88c7ed8b
Create Date: 2026-03-19 10:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT seed_library_id, seed_item_id FROM shared_resources LIMIT 1;"
#   backfill_plan: "n/a"
#   owner: "codex"
#   ticket: "n/a"

# revision identifiers, used by Alembic.
revision: str = "4f8c2b1a9d3e"
down_revision: Union[str, None] = "07fd88c7ed8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shared_resources", sa.Column("seed_library_id", sa.UUID(), nullable=True))
    op.add_column("shared_resources", sa.Column("seed_item_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_shared_resources_seed_library_id",
        "shared_resources",
        "seed_libraries",
        ["seed_library_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_shared_resources_seed_item_id",
        "shared_resources",
        "seed_items",
        ["seed_item_id"],
        ["id"],
    )
    op.create_index(
        "idx_share_resource_seed_library",
        "shared_resources",
        ["seed_library_id"],
        unique=False,
    )
    op.create_index(
        "idx_share_resource_seed_item",
        "shared_resources",
        ["seed_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_share_resource_seed_item", table_name="shared_resources")
    op.drop_index("idx_share_resource_seed_library", table_name="shared_resources")
    op.drop_constraint("fk_shared_resources_seed_item_id", "shared_resources", type_="foreignkey")
    op.drop_constraint("fk_shared_resources_seed_library_id", "shared_resources", type_="foreignkey")
    op.drop_column("shared_resources", "seed_item_id")
    op.drop_column("shared_resources", "seed_library_id")
