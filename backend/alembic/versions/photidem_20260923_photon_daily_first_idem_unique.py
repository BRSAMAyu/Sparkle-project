"""PHOTON-IDEM · photon_transaction_history 每日首胜幂等键唯一部分索引

Revision ID: photidem_20260923
Revises: dc5share_20260922
Create Date: 2026-09-23

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：DROP INDEX uq_photon_tx_daily_first_idem。
        索引纯约束、不携带数据；downgrade 后 schema 与升级前一致（升级时按
        保留最早语义收敛掉的重复首胜流水不可再生——但那些行本身就是并发双发
        污染，会虚增「可兑换基数」，见 backfill_plan）。"
    verification_query: "SELECT indexname, indexdef FROM pg_indexes WHERE indexname='uq_photon_tx_daily_first_idem';"
    backfill_plan: "无回填。反向操作：先收敛后建索引——升级时删除索引管辖域
        （related_item_id LIKE 'daily_first:%'）内 (user_id, related_item_id)
        重复组中不是最早的那批行（保留最早=首个真实发放事件；后来者是并发
        check-then-insert 竞态双发的虚增基数污染，删除即还原审计诚实性）；
        管辖域外的取值域（NULL、裸 achievement_id / contract_id、guest_welcome、
        achievement_combo:<hex16>、purchase 裸 item_id）一概不动。"
    owner: "PHOTON-IDEM"
    ticket: "PHOTON-STREAM 残留：首胜发放的去重门是读侧先查重
        （PhotonService._find_existing_transaction，check-then-insert），缓存
        失守+DB 兜底双路径并发时两请求可同时读到「未发放」→ 双发双计基数。
        写入侧以唯一部分索引 + ON CONFLICT DO NOTHING RETURNING 收口。"

方案裁决（为什么是部分索引，不是全列唯一；为什么 combo 域不并入）：
    photon_transaction_history.related_item_id 是多写入方共享列，取值域实测
    （演示库只读 SELECT，2026-09-23，共 297 行）：NULL 7 行（transfer_in/out、
    redeem_pro、旧 grant_achievement）、裸 achievement_id 81 行（celery 重试与
    成就引擎，grant_achievement）、guest_welcome 170 行（guest_seed，**跨用户
    同键合法**——170 行恰 170 个用户，per-user 域内零重复）、裸 item_id 5 行
    （purchase，**同用户同 item 合法重复购买**——演示库实测 1 组同 (user,item)
    重复对）、daily_first:<ISO> 2 行（2 用户，域内零重复）、
    achievement_combo:<hex16> 32 行。全列 (user_id, related_item_id) 唯一会
    当场炸掉 2 组域外既有重复（重复购买 + NULL 转账组），且把「可重复购买」
    「跨用户同键」改写成非法——故收窄到首胜幂等键命名空间，键域与读侧门
    （_find_existing_transaction 的 user+type+amount+source+related_item_id
    匹配）在 daily_first 域内严格同域。

    **combo 域不并入**（裁决）：其键 `achievement_combo:<uuid4.hex[:16]>` 的
    唯一性由生成器构造保证（2^-64 碰撞），索引对它零防重放价值；且 combo 的
    业务语义是「每次达标即一次独立合法经济事件」（PHOTON-STREAM 定案），不存在
    「同键=重复发放」的幂等语义可供索引执行——给它上唯一约束是在执行一个
    该域不存在的错误不变量，还会把假想中的生成器 bug 从「静默双发」变成
    「无冲突处理的路径上硬 500」。成本虽同，价值为零、风险为正，故否决。

方言可移植性：CREATE UNIQUE INDEX ... WHERE <LIKE 谓词>（PG 与 SQLite 均支持
部分索引）；存量收敛用 correlated EXISTS + (created_at, CAST(id AS TEXT))
字典序比较的双方言可移植写法——本表 PK 是 uuid，PG 无 min(uuid) 聚合
（ERR-IDEM-CONCUR 在 mastery_audit_log 用的 MIN(id) 依赖 SERIAL 整型主键，
此处不可复制），CAST 写法在双方言下语义一致：保留每组 (user_id,
related_item_id) 中 created_at 最早者，同刻并列时以 id 文本序定 tie-break
（确定性、双方言一致）。
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

revision: str = "photidem_20260923"
down_revision: str | None = "dc5share_20260922"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_photon_tx_daily_first_idem"

# 索引管辖域：每日首胜幂等键命名空间（与写侧 PhotonService 的前缀守卫同域）
_IDEM_SCOPE_PREDICATE = "related_item_id LIKE 'daily_first:%'"

# 收敛子查询里对同一谓词的限定名变体（手工展开，不用字符串替换的取巧写法）
_KEEPER_SCOPE_PREDICATE = "keeper.related_item_id LIKE 'daily_first:%'"


def upgrade() -> None:
    # 1) 收敛存量重复（仅索引管辖域 daily_first:%）：保留每组 (user_id,
    #    related_item_id) 最早一行（created_at 最小；同刻以 id 文本序
    #    tie-break）。最早行 = 首个真实发放事件；后来者 = 并发竞态双发的
    #    虚增「可兑换基数」污染。uuid 主键上无 min() 聚合（PG 无 min(uuid)），
    #    故用 correlated EXISTS 的双方言可移植写法（ERR-IDEM-CONCUR 的
    #    MIN(id) 写法依赖 SERIAL 整型主键，此处不可复制）。
    op.execute(
        f"""
        DELETE FROM photon_transaction_history
        WHERE {_IDEM_SCOPE_PREDICATE}
          AND EXISTS (
              SELECT 1 FROM photon_transaction_history AS keeper
              WHERE {_KEEPER_SCOPE_PREDICATE}
                AND keeper.user_id = photon_transaction_history.user_id
                AND keeper.related_item_id = photon_transaction_history.related_item_id
                AND (
                    keeper.created_at < photon_transaction_history.created_at
                    OR (
                        keeper.created_at = photon_transaction_history.created_at
                        AND CAST(keeper.id AS TEXT) < CAST(photon_transaction_history.id AS TEXT)
                    )
                )
          )
        """
    )

    # 2) 唯一部分索引：只约束每日首胜幂等键命名空间，键域与读侧门同域。
    #    注意 NULL 行天然在谓词外（NULL LIKE ... 为 NULL，不视为真）。
    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
        ON photon_transaction_history(user_id, related_item_id)
        WHERE {_IDEM_SCOPE_PREDICATE}
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
