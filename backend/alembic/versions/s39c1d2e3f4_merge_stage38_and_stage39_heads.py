"""merge stage38 and stage39 heads

Revision ID: s39c1d2e3f4
Revises: stage38_06_add_vector_hnsw_indexes, s39b1c2d3e4
Create Date: 2026-04-24 15:20:00
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "s39c1d2e3f4"
down_revision: Union[tuple[str, str], None] = (
    "stage38_06_add_vector_hnsw_indexes",
    "s39b1c2d3e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
