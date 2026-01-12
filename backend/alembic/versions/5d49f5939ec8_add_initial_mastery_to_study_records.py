"""add_initial_mastery_to_study_records

Revision ID: 5d49f5939ec8
Revises: effadcff68cd
Create Date: 2026-01-03 14:42:15.123456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d49f5939ec8'
down_revision: Union[str, None] = 'effadcff68cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add initial_mastery column to study_records
    op.add_column('study_records', sa.Column('initial_mastery', sa.Float(), nullable=True))
    
    # Optional: Fill existing data with a default or calculated value if needed
    # For now, we leave it as NULL for old records since we can't accurately reconstruct it without auditing history


def downgrade() -> None:
    # Remove initial_mastery column
    op.drop_column('study_records', 'initial_mastery')
