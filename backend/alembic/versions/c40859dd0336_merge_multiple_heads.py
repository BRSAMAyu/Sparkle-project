"""merge multiple heads

Revision ID: c40859dd0336
Revises: 5d49f5939ec8, add_global_spark_count
Create Date: 2026-01-03 14:53:04.057369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c40859dd0336'
down_revision: Union[str, None] = ('5d49f5939ec8', 'add_global_spark_count')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
