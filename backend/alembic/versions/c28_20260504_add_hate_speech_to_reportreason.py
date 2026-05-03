"""add hate_speech to reportreason enum

Revision ID: c28_20260504
Revises:
Create Date: 2026-05-04

"""
from alembic import op

revision = "c28_20260504"
down_revision = "c27_20260503"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE reportreason ADD VALUE IF NOT EXISTS 'HATE_SPEECH'")


def downgrade() -> None:
    pass
