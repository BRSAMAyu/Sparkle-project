"""merge galaxy document knowledge system heads

Revision ID: merge_galaxy_doc_20260426
Revises: cf20260426_file_copies, gkb001_group_knowledge_base, td001_task_documents
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa


revision = "merge_galaxy_doc_20260426"
down_revision = ("cf20260426_file_copies", "gkb001_group_knowledge_base", "td001_task_documents")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
