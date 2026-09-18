"""plan_execution_records: intent-level uniqueness (C2, sysrev round2)

Revision ID: sr8r2g2_c2_intent
Revises: 0150e391736a
Create Date: 2026-09-18

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1"
    verification_query: "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_plan_execution_records_intent';"
    backfill_plan: "n/a — legacy rows have no intent attribution, stay NULL (不猜)"
    owner: "r2-fix-wave-g2"

C2 (sysrev round2 方案 A): P2-3 的条件占位（应用层）之上加 DB 级防线——
plan_execution_records.execution_intent_id + 部分唯一索引，保证一个执行
意图至多落一条方案执行记录。并发/崩溃窗口下的重复写入触发 IntegrityError，
由 PlanExecutionRecordService.create_record 捕获并回查现有记录幂等返回。
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "sr8r2g2_c2_intent"
down_revision: Union[str, None] = "0150e391736a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "plan_execution_records"
_COLUMN = "execution_intent_id"
_FK = "fk_plan_exec_records_intent"
_UQ_INDEX = "uq_plan_execution_records_intent"


def _uuid_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.UUID(as_uuid=True)
    return sa.CHAR(length=36)


def upgrade() -> None:
    op.add_column(_TABLE, sa.Column(_COLUMN, _uuid_type(), nullable=True))
    op.create_foreign_key(
        _FK,
        _TABLE,
        "execution_intents",
        [_COLUMN],
        ["id"],
        ondelete="SET NULL",
    )
    # PG：部分唯一索引（NULL 不参与，存量未归属行共存）；
    # SQLite：postgresql_where 被忽略退化为全列唯一索引，而 SQLite 唯一索引
    # 中 NULL 互异，语义等价（仓内测试基座为 SQLite，避免 R1 的 Least 型方言回退）
    op.create_index(
        _UQ_INDEX,
        _TABLE,
        [_COLUMN],
        unique=True,
        postgresql_where=sa.text(f"{_COLUMN} IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(_UQ_INDEX, table_name=_TABLE)
    op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    op.drop_column(_TABLE, _COLUMN)
