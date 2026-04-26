"""merge lane_d task stuck and lane_k notification disabled types

Revision ID: merge_lane_d_lane_k_2026_04_26
Revises: lane_d_task_stuck_status, lane_k_disabled_notification_types
Create Date: 2026-04-26 03:00:00

Both lanes branched from the same parent set; this empty merge collapses them.
"""

from __future__ import annotations

from typing import Sequence

revision: str = "merge_lane_d_lane_k_2026_04_26"
down_revision: str | tuple[str, str] | None = (
    "lane_d_task_stuck_status",
    "lane_k_disabled_notification_types",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
