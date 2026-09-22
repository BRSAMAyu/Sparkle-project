"""D-COMM-4 · 共学自习室在场证明表 study_room_sessions

Revision ID: dc4room_20260922
Revises: erridemconc_20260922
Create Date: 2026-09-23

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：DROP TABLE study_room_sessions。
        本表是纯增量在场证明记录（进出场事件流水），回滚即丢弃该类记录；
        不触碰 groups/group_members/users 等既有表——自习室是小队
        （Group(type=SPRINT)）的场景化挂靠，复用裁决见
        services/community_study_room_service.py 模块注释。"
    verification_query: "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='study_room_sessions';"
    backfill_plan: "无回填。新表零存量，历史在场数据自上线起累积。"
    owner: "D-COMM-4"
    ticket: "D-COMMUNITY 设计卡 §3.3 共学自习室（P1，纯在场证明：
        显式进出为主、心跳兜底崩溃恢复；时长仅展示不进榜分）。"

方言可移植性：部分唯一索引 uq_study_room_open_session 使用
CREATE UNIQUE INDEX ... WHERE (exited_at IS NULL AND deleted_at IS NULL)，
PG 与 SQLite 均支持部分索引谓词；与模型层
Index(..., postgresql_where=...) 等价（模型侧该索引只在 PG 方言建，
sqlite 测试路径由本迁移/服务层 enter 幂等语义兜底）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID

revision: str = "dc4room_20260922"
down_revision: str | None = "erridemconc_20260922"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "study_room_sessions"
_OPEN_SESSION_INDEX = "uq_study_room_open_session"
_OPEN_SESSION_PREDICATE = "exited_at IS NULL AND deleted_at IS NULL"


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(ix["name"] == index_name for ix in sa.inspect(bind).get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, _TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("id", GUID(), nullable=False),
        sa.Column("group_id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("entered_at", sa.DateTime(), nullable=False),
        sa.Column("exited_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=False),
        # BaseModel 公共列（id/created_at/updated_at/deleted_at）
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_study_room_sessions_group_id", _TABLE, ["group_id"])
    op.create_index("ix_study_room_sessions_user_id", _TABLE, ["user_id"])
    op.create_index("idx_study_room_group_entered", _TABLE, ["group_id", "entered_at"])
    op.create_index("idx_study_room_user_entered", _TABLE, ["user_id", "entered_at"])
    op.create_index(
        "ix_study_room_sessions_deleted_at",
        _TABLE,
        ["deleted_at"],
    )
    op.create_index(
        _OPEN_SESSION_INDEX,
        _TABLE,
        ["group_id", "user_id"],
        unique=True,
        sqlite_where=sa.text(_OPEN_SESSION_PREDICATE),
        postgresql_where=sa.text(_OPEN_SESSION_PREDICATE),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, _TABLE):
        return
    if _has_index(bind, _TABLE, _OPEN_SESSION_INDEX):
        op.drop_index(_OPEN_SESSION_INDEX, table_name=_TABLE)
    op.drop_index("ix_study_room_sessions_deleted_at", table_name=_TABLE)
    op.drop_index("idx_study_room_user_entered", table_name=_TABLE)
    op.drop_index("idx_study_room_group_entered", table_name=_TABLE)
    op.drop_index("ix_study_room_sessions_user_id", table_name=_TABLE)
    op.drop_index("ix_study_room_sessions_group_id", table_name=_TABLE)
    op.drop_table(_TABLE)
