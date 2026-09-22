"""D-COMM-5 · 小队错题卡分享表 squad_shared_errors

Revision ID: dc5share_20260922
Revises: dc4room_20260922
Create Date: 2026-09-23

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：DROP TABLE squad_shared_errors。
        本表是纯增量分享分发记录（引用 error_id + 分享时刻快照），回滚即
        丢弃该类记录；不触碰 groups/error_records/users 等既有表——分享
        是错题本（error_records）到冲刺小队（Group(type=SPRINT)）的只读
        分发，复用裁决见 services/community_shared_error_service.py 与
        models/squad_shared_error.py 模块注释。"
    verification_query: "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='squad_shared_errors';"
    backfill_plan: "无回填。新表零存量，分享记录自上线起累积。"
    owner: "D-COMM-5"
    ticket: "D-COMMUNITY 设计卡 §3.5 错题卡分享（P2：谁在哪卡住了的
        小队知识互助；分享不产生光子/不进任何榜）。"

方言可移植性：部分唯一索引 uq_squad_shared_error_active 使用
CREATE UNIQUE INDEX ... WHERE (deleted_at IS NULL)，PG 与 SQLite 均支持
部分索引谓词；与模型层 Index(..., postgresql_where=...) 等价（照
D-COMM-4 dc4room_20260922 的双方言先例）。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.models.base import GUID

revision: str = "dc5share_20260922"
down_revision: str | None = "dc4room_20260922"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "squad_shared_errors"
_ACTIVE_SHARE_INDEX = "uq_squad_shared_error_active"
_ACTIVE_SHARE_PREDICATE = "deleted_at IS NULL"


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _has_index(bind, table_name: str, index_name: str) -> bool:
    return any(ix["name"] == index_name for ix in sa.inspect(bind).get_indexes(table_name))


def _jsonb_type():
    """content 快照列：PG 走 JSONB（与模型 JSONBCompat 的 PG 侧等价），sqlite 退化 JSON。"""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    bind = op.get_bind()
    if _has_table(bind, _TABLE):
        return
    op.create_table(
        _TABLE,
        sa.Column("id", GUID(), nullable=False),
        sa.Column("group_id", GUID(), nullable=False),
        sa.Column("error_id", GUID(), nullable=False),
        sa.Column("sharer_id", GUID(), nullable=False),
        sa.Column("content", _jsonb_type(), nullable=False),
        sa.Column("snapshot_note", sa.Text(), nullable=True),
        sa.Column("mastery_level", sa.Float(), nullable=False),
        sa.Column("mastery_delta", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False),
        # BaseModel 公共列（id/created_at/updated_at/deleted_at）
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["error_id"], ["error_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sharer_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_squad_shared_errors_group_id", _TABLE, ["group_id"])
    op.create_index("ix_squad_shared_errors_error_id", _TABLE, ["error_id"])
    op.create_index("ix_squad_shared_errors_sharer_id", _TABLE, ["sharer_id"])
    op.create_index("idx_squad_shared_error_group_time", _TABLE, ["group_id", "created_at"])
    op.create_index("idx_squad_shared_error_sharer", _TABLE, ["sharer_id", "group_id"])
    op.create_index("ix_squad_shared_errors_deleted_at", _TABLE, ["deleted_at"])
    op.create_index(
        _ACTIVE_SHARE_INDEX,
        _TABLE,
        ["group_id", "error_id"],
        unique=True,
        sqlite_where=sa.text(_ACTIVE_SHARE_PREDICATE),
        postgresql_where=sa.text(_ACTIVE_SHARE_PREDICATE),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_table(bind, _TABLE):
        return
    if _has_index(bind, _TABLE, _ACTIVE_SHARE_INDEX):
        op.drop_index(_ACTIVE_SHARE_INDEX, table_name=_TABLE)
    op.drop_index("ix_squad_shared_errors_deleted_at", table_name=_TABLE)
    op.drop_index("idx_squad_shared_error_sharer", table_name=_TABLE)
    op.drop_index("idx_squad_shared_error_group_time", table_name=_TABLE)
    op.drop_index("ix_squad_shared_errors_sharer_id", table_name=_TABLE)
    op.drop_index("ix_squad_shared_errors_error_id", table_name=_TABLE)
    op.drop_index("ix_squad_shared_errors_group_id", table_name=_TABLE)
    op.drop_table(_TABLE)
