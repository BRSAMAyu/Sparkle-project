"""gfix03: drop 三列 MIG-only 死列（审计 round2 schema-route-tail）

Revision ID: gfix03_20260918
Revises: gfix02_20260918
Create Date: 2026-09-18

背景：scripts/devtools/orm_migration_audit.py 三方审计（ORM ↔ 迁移链 ↔ 实库）
把三个"迁移链有来源、ORM 无映射"的死列登记为 P1 挂账
（docs/competition/2026-tmall-hackathon/系统审查/round2/schema-consistency-audit.md）。
全仓 grep（含网关 SQLC query、proto、mobile、裸 SQL）确认零消费后，本迁移
以 DROP COLUMN IF EXISTS 收口：

  1. cards.archived_at        来源 cp001a2b3c4d5_add_card_protocol_tables
     （Card ORM 无映射；card_service._transition 对该属性赋值不落库，属死代码）
  2. chat_messages.metadata   来源 wp19_20260507_add_chat_messages_metadata_jsonb
     （ChatMessage ORM 无映射；age_gate.SENSITIVE_FIELDS 仅死规格声明）
  3. user_settings.accessibility_settings
                                 来源 fv14_20260502_add_accessibility_settings
     （UserSettings ORM 无映射；UserSettingsService.update_settings 以 hasattr
       过滤，mobile 上送的该 key 本就被静默丢弃）

IF EXISTS 保证幂等；downgrade 按各来源迁移的原始列定义复原。
"""
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "gfix03_20260918"
down_revision: Union[str, tuple, None] = "gfix02_20260918"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE cards DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS metadata")
    op.execute("ALTER TABLE user_settings DROP COLUMN IF EXISTS accessibility_settings")


def downgrade() -> None:
    op.add_column("cards", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column(
        "chat_messages",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "user_settings",
        sa.Column(
            "accessibility_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
