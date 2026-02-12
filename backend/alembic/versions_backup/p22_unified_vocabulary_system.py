"""unified vocabulary system with importance-based review

Revision ID: p22_unified_vocabulary_system
Revises: p21_plan_execution_records
Create Date: 2026-01-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.utils.migration_helpers import get_inspector, table_exists

# revision identifiers, used by Alembic.
revision: str = "p22_unified_vocabulary_system"
down_revision: Union[str, None] = "p21_plan_execution_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = get_inspector()

    # Check if word_books table exists
    if not table_exists(inspector, "word_books"):
        # Create word_books table if it doesn't exist
        op.create_table(
            "word_books",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("word", sa.String(100), nullable=False),
            sa.Column("phonetic", sa.String(100), nullable=True),
            sa.Column("definition", sa.Text(), nullable=False),
            # Old Ebbinghaus review fields (kept for backward compatibility)
            sa.Column("mastery_level", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("next_review_at", sa.DateTime(), nullable=False),
            sa.Column("last_review_at", sa.DateTime(), nullable=True),
            sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
            # New unified review system fields
            sa.Column("importance", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("consecutive_correct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("correct_review_count", sa.Integer(), nullable=False, server_default="0"),
            # Extended metadata
            sa.Column("part_of_speech", sa.String(50), nullable=True),
            sa.Column("source_translation_id", sa.String(100), nullable=True),
            sa.Column("context_sentence", sa.Text(), nullable=True),
            sa.Column("source_task_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )
        op.create_index("ix_word_books_user_id", "word_books", ["user_id"])
        op.create_index("ix_word_books_word", "word_books", ["word"])
        op.create_index("idx_wordbook_review", "word_books", ["user_id", "next_review_at"])
        op.create_unique_constraint("uq_user_word", "word_books", ["user_id", "word"])
        op.create_foreign_key(
            "fk_word_books_user_id",
            "word_books", "users",
            ["user_id"], ["id"],
            ondelete="CASCADE"
        )
        op.create_foreign_key(
            "fk_word_books_source_task_id",
            "word_books", "tasks",
            ["source_task_id"], ["id"],
            ondelete="SET NULL"
        )
    else:
        # Add new columns to existing word_books table
        existing_columns = {col['name'] for col in inspector.get_columns('word_books')}

        if 'importance' not in existing_columns:
            op.add_column('word_books',
                sa.Column('importance', sa.Integer(), nullable=True, server_default='3'))
        if 'consecutive_correct' not in existing_columns:
            op.add_column('word_books',
                sa.Column('consecutive_correct', sa.Integer(), nullable=True, server_default='0'))
        if 'correct_review_count' not in existing_columns:
            op.add_column('word_books',
                sa.Column('correct_review_count', sa.Integer(), nullable=True, server_default='0'))
        if 'part_of_speech' not in existing_columns:
            op.add_column('word_books',
                sa.Column('part_of_speech', sa.String(length=50), nullable=True))
        if 'source_translation_id' not in existing_columns:
            op.add_column('word_books',
                sa.Column('source_translation_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    inspector = get_inspector()

    if table_exists(inspector, "word_books"):
        existing_columns = {col['name'] for col in inspector.get_columns('word_books')}

        # Drop new columns if they exist
        if 'source_translation_id' in existing_columns:
            op.drop_column('word_books', 'source_translation_id')
        if 'part_of_speech' in existing_columns:
            op.drop_column('word_books', 'part_of_speech')
        if 'correct_review_count' in existing_columns:
            op.drop_column('word_books', 'correct_review_count')
        if 'consecutive_correct' in existing_columns:
            op.drop_column('word_books', 'consecutive_correct')
        if 'importance' in existing_columns:
            op.drop_column('word_books', 'importance')
