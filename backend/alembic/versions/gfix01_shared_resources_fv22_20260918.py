"""shared_resources 补齐 FV-22 ORM 列（模型超前于 schema 的 v1 漂移收敛）

Revision ID: gfix01_20260918
Revises: r20807_20260918
Create Date: 2026-09-18

背景：community.SharedResource 模型含 adoption_count / negative_feedback_count /
quality_score / quality_hidden（FV-22 质量分体系）四列，但从未进入迁移链；
dev 库被 G8 收敛到迁移真值后该漂移显性化（游客种子查询 UndefinedColumn →
事务毒化 → guest 登录 500）。本迁移按模型定义补列，模型与 schema 对齐。

同时本迁移兼任合并点：sr8r2g2_c2_intent（G2）与 r20807_20260918（G8）此前
双双挂链 0150e391736a 形成分叉（集成期意外双头），在此收敛为单头。
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'gfix01_20260918'
down_revision: Union[str, tuple, None] = ('r20807_20260918', 'sr8r2g2_c2_intent')
branch_labels = None
depends_on = None

_NEW_COLUMNS = (
    sa.Column("adoption_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("negative_feedback_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
    sa.Column("quality_hidden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
)


def upgrade() -> None:
    for col in _NEW_COLUMNS:
        op.add_column("shared_resources", col)


def downgrade() -> None:
    for name in ("quality_hidden", "quality_score", "negative_feedback_count", "adoption_count"):
        op.drop_column("shared_resources", name)
