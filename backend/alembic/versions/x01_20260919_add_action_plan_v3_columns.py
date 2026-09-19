"""X-01 · ActionPlan V3 contract columns on tasks (additive, legacy-safe)

Revision ID: x01_20260919
Revises: m01a_20260919
Create Date: 2026-09-19

契约真源：backend/app/core/action_plan.py（ACTION_PLAN_SCHEMA_VERSION = "action_plan.v1"）。
迁移内容（tasks 表 8 个 nullable 新列，全部无 server default —— NULL 即 legacy/V2.x 语义）：
- action_schema_version  String(16)   "action_plan.v1" | NULL
- desired_outcome        Text         期望结果陈述
- smallest_useful_step   JSONB        {description, useful_because:[封闭枚举]}
- completion_evidence    JSONB        [{evidence_kind, ref?, description?}]
- cognitive_ownership    VARCHAR(16)  user_core|shared|delegated（D13 首版）
- source_refs            JSONB        ["scheme://id", ...]（封闭 scheme，C-01 对齐）
- risk_class             VARCHAR(16)  low|medium|high|critical
- reversible             Boolean      可撤销性

合入窗口重挂（返修 F3，REVIEW_RECEIPT_2）：初版挂 ent01_20260919 时与并行 E-05 的
e05_20260919 同父分叉；E-05 已先行 apply（dev DB alembic_version=e05），M-01 已把
m01a_20260919 挂上 e05。主链现为 ud01→ent01→e05→m01a 单头，x01 改挂 m01a 恢复单头。

注意：execution_mode **复用** tasks 既有 String(20) 镜像列（ExecutionIntent 唯一协议，
dev DB 1231 行全 NULL，2026-09-19 复核），本迁移不触碰它；枚举列不带 DB CHECK
（沿用 execution_intent.py create_constraint=False 模式，封闭词表由应用层契约强制）。

映射文档（cards/task_occurrences 目标协议形态）：v3-output/X-01/REPORT.md。
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "x01_20260919"
down_revision: Union[str, None] = "m01a_20260919"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _jsonb_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB(astext_type=sa.Text())


def _action_plan_columns() -> tuple[tuple[str, object], ...]:
    """列清单惰性构造：JSONB 类型需在迁移运行上下文内按 dialect 决定。"""
    return (
        ("action_schema_version", sa.String(length=16)),
        ("desired_outcome", sa.Text()),
        ("smallest_useful_step", _jsonb_type()),
        ("completion_evidence", _jsonb_type()),
        ("cognitive_ownership", sa.String(length=16)),
        ("source_refs", _jsonb_type()),
        ("risk_class", sa.String(length=16)),
        ("reversible", sa.Boolean()),
    )


def upgrade() -> None:
    for name, type_ in _action_plan_columns():
        op.add_column("tasks", sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    for name, _type in reversed(_action_plan_columns()):
        op.drop_column("tasks", name)
