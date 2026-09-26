"""V3-FIX-258 · chat_messages.origin 演示产出 origin 标记列

Revision ID: f258_20260925
Revises: j06_20260925
Create Date: 2026-09-25

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：drop column chat_messages.origin
        （落库行产出来源标记；回滚后 demo 产出与真实模型产出重新在 schema
        层不可区分，即回到缺陷态，无数据丢失——标记值本身随列删除）。"
    verification_query: "SELECT origin, count(*) FROM chat_messages GROUP BY origin;"
    backfill_plan: "不回填（历史不可考）。存量行统一由 server_default 'llm'
        落默认值——迁移前的历史 demo 轮无任何持久标记可依（本缺陷本体），
        按时间+model_name 启发式回填只会引入新的误标面，故本列仅对迁移
        上线后的新写入有区分力。"
    owner: "wt544 (V3-FIX-258, Stream: BACKEND)"
    ticket: "v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-258 —— wt533 B-02
        审计 F1：demo 模式产出（DEMO_MOCK_RESPONSES/通用演示回复）落库后与
        真实模型产出在 schema 层不可区分，唯一标记是瞬态 OTel span
        llm.demo_mode；且 mock 文本经 _persist_assistant_message 喂记忆推断
        管线。写侧两 choke point（orchestrator _persist_assistant_message、
        REST save_chat_message）按 llm_service.demo_mode 置 'demo'，记忆
        推断 process_chat_turn 入口整轮跳过 demo 轮。

列语义（与 app.models.chat.MessageOrigin 一一对应）：
- llm：常规管线产出（user 行/系统模板行/存量行默认值）。
- demo：演示模式脚本产出。demo 行的 model_name 仍是「配置了但从未运行」
  的模型名，lineage 查询以本列为准。
不建索引：判别查询低频且非热点谓词，需要时可后补。
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f258_20260925"
down_revision: str | None = "j06_20260925"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = sa.inspect(bind)
    return column_name in {col["name"] for col in insp.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    if _column_exists(bind, "chat_messages", "origin"):
        return
    op.add_column(
        "chat_messages",
        sa.Column("origin", sa.String(length=20), nullable=False, server_default="llm"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "chat_messages", "origin"):
        return
    op.drop_column("chat_messages", "origin")
