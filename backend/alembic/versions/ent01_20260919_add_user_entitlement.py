"""users.entitlement：独立权益字段，拆除 IsPro=FlameLevel>=3 派生（D17 冻结决策）

Revision ID: ent01_20260919
Revises: ud01_20260919
Create Date: 2026-09-19

背景：网关与引擎曾以 `IsPro = flame_level >= 3` 派生权益（gateway
user_context.go / chat_orchestrator_chatflow.go fallback / engine
user_service.get_context），而 guest_seed_service 会把游客 flame_level 写到
15 → 全部游客以 is_pro=true 进入 llm_router 的 pro 层钳制，真实 email 用户
反被压 free 层。D17 冻结决策：entitlement 独立成字段，flame_level 保留为
展示层字段、永久禁作权益判据。

语义：
- 现有行（guest / seed / email 一视同仁）全部默认 'free'；游客体验模式本就
  应该走 free 层，游客 LLM 路由将从 pro 降回 free（预期行为变化）。
- 值域约定（应用层约束，暂不加 CHECK，为未来分层留位）：
  'free' | 'pro'（引擎侧将 premium/paid 视同 pro，见 agent_grpc_service
  ._resolve_request_user_tier）。
- 网关→引擎过界信号仍是 proto UserProfile.is_pro（agent_service.proto:140），
  其取值来源由 flame 派生改为读本列。

验证：加列为加法安全操作；单迁移可在本地 sqlite 基座隔离重放；
主库只写纪律 —— 本迁移对共享 dev DB 仅允许 alembic upgrade 这一条写路径。

# Migration Contract:
#   type: reversible
#   rollback_plan: "alembic downgrade -1"
#   verification_query: "SELECT column_name, column_default, is_nullable FROM information_schema.columns WHERE table_name='users' AND column_name='entitlement';"
#   backfill_plan: "n/a（NOT NULL DEFAULT 'free' 由 PostgreSQL 自动填充全部现有行）"
#   owner: "backend"
#   ticket: "V3-FIX-02（P0，D17 冻结决策）"
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ent01_20260919"
down_revision: str | None = "ud01_20260919"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("entitlement", sa.String(length=32), server_default=sa.text("'free'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "entitlement")
