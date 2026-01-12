"""Merge heads

Revision ID: 397296dbb0e5
Revises: 34289ecf1f13, p10_persona_v31
Create Date: 2026-01-11 00:15:50.701602

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '397296dbb0e5'
down_revision: Union[str, None] = ('34289ecf1f13', 'p10_persona_v31')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
