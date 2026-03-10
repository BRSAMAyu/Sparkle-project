"""add user equipment sources

Revision ID: f14e9c2b7a1d
Revises: c3d9f1a7b2e4
Create Date: 2026-03-10 16:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f14e9c2b7a1d"
down_revision = "c3d9f1a7b2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("equipped_skin_source", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("equipped_title_source", sa.String(length=20), nullable=True))
    op.create_index(op.f("ix_users_equipped_skin_source"), "users", ["equipped_skin_source"], unique=False)
    op.create_index(op.f("ix_users_equipped_title_source"), "users", ["equipped_title_source"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_equipped_title_source"), table_name="users")
    op.drop_index(op.f("ix_users_equipped_skin_source"), table_name="users")
    op.drop_column("users", "equipped_title_source")
    op.drop_column("users", "equipped_skin_source")
