"""V3-FIX-299 · mastery_audit_log 加 effect_kind 列（写侧定性 + 按类重放）

Revision ID: wt598_20260927
Revises: wt539_20260926
Create Date: 2026-09-27

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：DROP COLUMN effect_kind（PG 与
        sqlite ≥3.35 均支持）。回滚后读侧按 kind 分支的 SELECT 会因列缺失
        整体异常 → _load_prior_belief 捕获后回退存量先验（FIX-292 之前
        的 fail-open 读面），不丢数据。"
    verification_query: "SELECT effect_kind, COUNT(*) FROM mastery_audit_log GROUP BY effect_kind;"
    backfill_plan: "普查口径（wt594-shadow 裁决材料 §1.1，live PG 394 行
        快照 2026-09-25）：12 条 payload 证据行（reason LIKE 'evidence:%'，
        全部 evidence:task_outcome）→ 'evidence'；100 条 exam-sprint 绝对
        set-point 行（exam_sprint_diagnostic / post_exam_review_weak_node）
        → 'set_point'；其余 282 条（task_complete 225 + sprint_task_
        completed 35 + 错题本带后缀 21 + probe 1）→ 'projection'。回填与
        写点定性同口径（mastery_evidence.classify_effect_kind 单点映射），
        一致性由 test_wt598_effect_kind_backfill_parity_sqlite 钉住。"
    owner: "wt598 (fleet impl)"
    ticket: "V3-FIX-299——证据账本确定性重放对首条 payload 行之后的无
        payload set-point 证据行（exam-sprint 惩罚）不重套数值。裁决
        （主会话采纳 A+C）：审计行由服务端在写点定性 effect_kind，读侧重放
        按列分支（evidence=融合 / set_point=重套记录值 / projection=跳过，
        NULL fail-closed 判 projection）。``reason`` 三条客户端入口可控，
        不再作为重放定性依据（信任边界）。"
"""

from __future__ import annotations

from alembic import op

revision: str = "wt598_20260927"
down_revision: str | None = "wt539_20260926"
branch_labels: str | None = None
depends_on: str | None = None

# 回填口径 = 写点定性单点映射（mastery_evidence.classify_effect_kind）的 SQL
# 形式。三条语句顺序即优先级：载荷证据行 > exam-sprint set-point > 其余投影。
BACKFILL_EVIDENCE_SQL = "UPDATE mastery_audit_log SET effect_kind = 'evidence' WHERE effect_kind IS NULL AND reason LIKE 'evidence:%'"
BACKFILL_SET_POINT_SQL = (
    "UPDATE mastery_audit_log SET effect_kind = 'set_point' WHERE effect_kind IS NULL "
    "AND reason IN ('exam_sprint_diagnostic', 'post_exam_review_weak_node')"
)
BACKFILL_PROJECTION_SQL = "UPDATE mastery_audit_log SET effect_kind = 'projection' WHERE effect_kind IS NULL"


def upgrade() -> None:
    # 语句取跨方言公共子集（PG + sqlite）：ADD COLUMN / UPDATE 均可，不用
    # PG 专属的 ADD COLUMN IF NOT EXISTS（迁移由 alembic 保证单次执行）。
    op.execute("ALTER TABLE mastery_audit_log ADD COLUMN effect_kind VARCHAR(20)")
    op.execute(BACKFILL_EVIDENCE_SQL)
    op.execute(BACKFILL_SET_POINT_SQL)
    op.execute(BACKFILL_PROJECTION_SQL)


def downgrade() -> None:
    op.execute("ALTER TABLE mastery_audit_log DROP COLUMN effect_kind")
