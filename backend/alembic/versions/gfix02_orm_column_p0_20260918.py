"""item_similarities / post_comments 补齐 ORM 领先迁移的 P0 列（审计 round2）

Revision ID: gfix02_20260918
Revises: gfix01_20260918
Create Date: 2026-09-18

背景：scripts/devtools/orm_migration_audit.py 三方审计（ORM ↔ 迁移链 ↔ 实库）
发现两处 ORM 领先迁移的列漂移（gfix01 同类，运行时 UndefinedColumn 级）：

  1. item_similarities.subject_id            （recommendation.ItemSimilarity:96）
     item_similarities.total_learners_either （recommendation.ItemSimilarity:90）
     → collaborative_filtering_service.select(ItemSimilarityModel) 会带出全部
       映射列，迁移真值库上直接 UndefinedColumn。
  2. post_comments.deleted_at（SoftDeleteMixin，index=True）
     → api/v1/community.py 多处 select(PostComment)，游客/社区链路同 gfix01
       毒化事务模式。

本迁移按 ORM 定义补列补索引，使三方在 P0 口径上归零。其余漂移
（迁移领先 ORM 的 17 张网关 CQRS/退役 spine 表、3 个死列、dev 库 29 张
会话遗留表等）为 P1，已在审计报告挂账：
docs/competition/2026-tmall-hackathon/系统审查/round2/schema-consistency-audit.md
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "gfix02_20260918"
down_revision: Union[str, tuple, None] = "gfix01_20260918"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "item_similarities",
        sa.Column("total_learners_either", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "item_similarities",
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("post_comments", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_post_comments_deleted_at", "post_comments", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_post_comments_deleted_at", table_name="post_comments")
    op.drop_column("post_comments", "deleted_at")
    op.drop_column("item_similarities", "subject_id")
    op.drop_column("item_similarities", "total_learners_either")
