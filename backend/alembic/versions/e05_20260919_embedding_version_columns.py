"""E-05：embedding 版本溯源列（document_chunks / knowledge_nodes）

Revision ID: e05_20260919
Revises: ent01_20260919
Create Date: 2026-09-19

背景：chunk/node 向量没有记录生成它的 embedding 模型身份。切换
EMBEDDING_MODEL 后，旧向量与新查询向量在同一个余弦空间里混用，相似度静默
变成垃圾（跨模型余弦距离无意义）。本迁移为 document_chunks 与
knowledge_nodes 增加 embedding_model（如 "dashscope/text-embedding-v4@1024"）
与 embedding_dim 两列，配合检索侧版本过滤（EMBEDDING_STRICT_VERSION_FILTER）
实现版本隔离；重建脚本 scripts/devtools/rebuild_embedding_index.py 负责把
存量向量补标记 / 重嵌。

纯加法、可逆；不对存量行做有假设的回填（无法证明存量向量的真实模型来源，
宁缺毋假——NULL 在过渡期按"未知来源"策略处理）。

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1（仅删两列，不动向量数据）"
#   verification_query: "SELECT column_name FROM information_schema.columns WHERE table_name='document_chunks' AND column_name IN ('embedding_model','embedding_dim');"
#   backfill_plan: "scripts/devtools/rebuild_embedding_index.py --table both --execute（真实重嵌并打标）"
#   owner: "backend"
#   ticket: "E-05 Embedding / Hybrid Retrieval 生产接入"
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e05_20260919"
down_revision: str | None = "ent01_20260919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("document_chunks", "knowledge_nodes")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("embedding_model", sa.String(length=100), nullable=True))
        op.add_column(table, sa.Column("embedding_dim", sa.Integer(), nullable=True))


def downgrade() -> None:
    for table in _TABLES:
        op.drop_column(table, "embedding_dim")
        op.drop_column(table, "embedding_model")
