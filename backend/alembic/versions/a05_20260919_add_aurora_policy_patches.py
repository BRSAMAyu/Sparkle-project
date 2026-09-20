"""A-05 · Aurora policy patch store (new table, additive)

Revision ID: a05_20260919
Revises: d05_20260919
Create Date: 2026-09-19

契约真源：backend/app/core/policy_patch.py
（POLICY_PATCH_SCHEMA_VERSION = "aurora_policy_patch.v1"）。

新表 ``aurora_policy_patches``：六面白名单 policy patch 的持久生命周期面
（candidate→evidenced→active→expire/revoke）。撤销 = 状态迁移（state=
revoked + 审计 transition_history 保留），行永不物理删除——用户纠正的
审计依据是行内 append-only 历史，不是会消失的 outbox（D-05 同款分工）。

幂等唯一约束 ``uq_policy_patch_once (patch_id)``：patch_id 内容寻址
（core derive_policy_patch_id），同内容重提议命中约束（服务层返回既有行）。
枚举列不带 DB CHECK（X-01/D-05 同款纪律：封闭词表由应用层契约强制——
core/policy_patch.py 的 fail-closed 验证是唯一写入路径）。

索引：user_id / state / expires_at（effective 集读取与过期 sweep 面）。
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.models.base import GUID

revision: str = "a05_20260919"
down_revision: Union[str, None] = "d05_20260919"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "aurora_policy_patches",
        sa.Column("id", GUID(), primary_key=True, nullable=False),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("patch_id", sa.String(length=64), nullable=False),
        sa.Column("surface", sa.String(length=32), nullable=False),
        sa.Column("payload", _jsonb_type(), nullable=False),
        sa.Column("scope_goal_type", sa.String(length=32), nullable=True),
        sa.Column("scope_friction_tag", sa.String(length=40), nullable=True),
        sa.Column("state", sa.String(length=24), nullable=False, server_default="candidate"),
        sa.Column("provenance", sa.String(length=32), nullable=False, server_default="decision_loop"),
        sa.Column("evidence_refs", _jsonb_type(), nullable=False),
        sa.Column("evidence_tier", sa.String(length=24), nullable=True),
        sa.Column("evidence_verified_at", sa.DateTime(), nullable=True),
        sa.Column("user_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("activated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("revoke_reason", sa.String(length=200), nullable=True),
        sa.Column("transition_history", _jsonb_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("patch_id", name="uq_policy_patch_once"),
    )
    op.create_index("ix_aurora_policy_patches_user", "aurora_policy_patches", ["user_id"])
    op.create_index("ix_aurora_policy_patches_state", "aurora_policy_patches", ["state"])
    op.create_index("ix_aurora_policy_patches_expires", "aurora_policy_patches", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_aurora_policy_patches_expires", table_name="aurora_policy_patches")
    op.drop_index("ix_aurora_policy_patches_state", table_name="aurora_policy_patches")
    op.drop_index("ix_aurora_policy_patches_user", table_name="aurora_policy_patches")
    op.drop_table("aurora_policy_patches")
