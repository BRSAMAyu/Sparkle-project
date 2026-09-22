"""ERR-IDEM-CONCUR · mastery_audit_log 幂等键唯一部分索引（毫秒窗口收口）

Revision ID: erridemconc_20260922
Revises: cp01confirm_20260922
Create Date: 2026-09-23

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：DROP INDEX uq_mastery_audit_log_idem_key。
        索引纯约束、不携带数据；downgrade 后 schema 与升级前一致（升级时按
        保留最早语义收敛掉的重复审计行不可再生——但那些行本身就是并发双扣
        污染，见 backfill_plan）。"
    verification_query: "SELECT indexname, indexdef FROM pg_indexes WHERE indexname='uq_mastery_audit_log_idem_key';"
    backfill_plan: "无回填。反向操作：先删后建——升级时收敛索引管辖域内
        （request_id LIKE 'edi:%' OR 'erv:%'）的存量重复三元组 (user_id,
        node_id, request_id)，每组保留最早一行（MIN(id)=首个生效证据），
        后来者是并发双写落账的重复扣分/重复回升污染，删除即还原审计诚实性；
        管辖域外的取值域（NULL、task_complete 裸 task_id、sprint_task_completed:、
        obs=/conf=/oc=/tk= 复合段、gRPC 客户端自由 request_id）一概不动。"
    owner: "ERR-IDEM-CONCUR"
    ticket: "ERR-IDEM 残留：读侧先查重门存在毫秒窗口，两个并发请求同时读到
        「未吸收」→ 双写双扣。写入侧以唯一部分索引收口。"

方案裁决（为什么是部分索引，不是全列唯一）：
    mastery_audit_log.request_id 是多写入方共享列，取值域实测（演示库只读
    SELECT，2026-09-23）：NULL 45 行（Galaxy REST /sync/mastery、/node/{id}/mastery
    不传 request_id）、裸 task_id 20 行（stats_service task_complete）、
    obs=..;conf=..;oc=..;tk=.. 复合段（outcome 证据账本）、gRPC 客户端自由
    request_id（galaxy_grpc_service 透传 request.request_id）、
    sprint_task_completed:{task}:{node}（task_service）。全列唯一会把所有
    命名空间一锅端——gRPC 客户端自由串与跨节点复用串当场炸；且演示库
    非管辖域已存在 3 组重复 (user,node,request_id) 三元组（旧格式
    error_diagnosis:{err}:{node} 历史 double-write），全列索引无法落地。
    故唯一索引收窄到 ERR-IDEM 幂等键命名空间（edi:/erv:），键域与读侧门
    （ErrorBookMasterySyncService._sync_already_applied 的 user+node+request_id
    三元组查询）严格同域。

方言可移植性：CREATE UNIQUE INDEX ... WHERE 谓词（PG 与 SQLite 均支持部分
索引，LIKE 谓词双方皆合法）；存量收敛用 DELETE ... NOT IN (SELECT MIN(id)
GROUP BY ...) 可移植写法（PG 的 DELETE...USING 方言 sqlite 不认）。
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

revision: str = "erridemconc_20260922"
down_revision: str | None = "cp01confirm_20260922"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_mastery_audit_log_idem_key"

_IDEM_SCOPE_PREDICATE = "request_id LIKE 'edi:%' OR request_id LIKE 'erv:%'"


def upgrade() -> None:
    # 1) 收敛存量重复（仅索引管辖域 edi:/erv:）：保留每组三元组最早一行。
    #    最早行 = 首个生效证据；后来者 = 并发/重试双写落账的重复扣分污染。
    #    NOT IN (SELECT MIN(id) ...) 为 PG/SQLite 双方言可移植写法。
    op.execute(
        f"""
        DELETE FROM mastery_audit_log
        WHERE ({_IDEM_SCOPE_PREDICATE})
          AND id NOT IN (
              SELECT MIN(id) FROM mastery_audit_log
              WHERE {_IDEM_SCOPE_PREDICATE}
              GROUP BY user_id, node_id, request_id
          )
        """
    )

    # 2) 唯一部分索引：只约束 ERR-IDEM 幂等键命名空间，键域与读侧门同域。
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
        ON mastery_audit_log(user_id, node_id, request_id)
        WHERE {_IDEM_SCOPE_PREDICATE}
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
