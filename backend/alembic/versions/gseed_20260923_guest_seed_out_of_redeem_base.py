"""GSEED · 访客种子流水出「可兑换基数」——存量 grant_achievement 误标回填改型

Revision ID: gseed_20260923
Revises: sqrejoin_20260923
Create Date: 2026-09-23

Migration Contract:
    type: reversible
    rollback_plan: "alembic downgrade -1：把 guest_seed 域流水改回
        grant_achievement（恢复升级前口径）。"
    verification_query: "SELECT transaction_type, count(*) FROM photon_transaction_history
        WHERE related_item_id='guest_welcome' AND source='guest_seed:welcome_bonus'
        GROUP BY transaction_type;"
    backfill_plan: "本迁移即回填：精准改写访客种子流水类型（见下）。"
    owner: "MINT-FIX"
    ticket: "D-MONETIZE 审计 §1.5-R3 / MINT-FIX 卡第二件。访客体验种子 1000 光子
        以 grant_achievement 类型入账（guest_seed_service.py，related_item_id=
        'guest_welcome'，source='guest_seed:welcome_bonus'），落在可兑换收入词表
        （photon_redeem_service.REDEEMABLE_INCOME_TYPES）内——游客转正改写同一
        用户行后，这 1000 直接计入「可兑换基数」（兑 Pro 价 1500 的 2/3），
        弯曲「仅学习所得可兑」口径（PHOTON-CALIBRATION 1500 定价依据被补贴
        稀释）。代码侧新种子已改专有类型 guest_seed（出词表）；本迁移把存量
        误标行一并改型，使口径修复对已转正用户同样生效。

改写域（三键联合锁定，不碰域外任何行）：
    transaction_type = 'grant_achievement'   -- 误标类型
    AND source = 'guest_seed:welcome_bonus'   -- 种子专有 source
    AND related_item_id = 'guest_welcome'     -- 种子专有的跨用户同键（合法非唯一）

语义影响申报（非展示口径，实行为面）：改型后这些行的 1000 不再计入
可兑换基数，已转正用户的下一次兑 Pro 判定按纯学习收入重算——无余额变动、
无既往兑换追缴（已按旧口径兑出的 Pro 不收回），效果是「补贴不再顶替学习
收入兑会员」，与审计建议 §1.6-3 一致。改写幂等：二次执行零行命中。
"""

from __future__ import annotations

from typing import Sequence

from alembic import op

revision: str = "gseed_20260923"
down_revision: str | None = "sqrejoin_20260923"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "photon_transaction_history"
_OLD_TYPE = "grant_achievement"
_NEW_TYPE = "guest_seed"
_SEED_SOURCE = "guest_seed:welcome_bonus"
_SEED_RELATED_ID = "guest_welcome"


def _retype(op, from_type: str, to_type: str) -> None:
    op.execute(
        f"UPDATE {_TABLE} SET transaction_type = '{to_type}' "
        f"WHERE transaction_type = '{from_type}' "
        f"AND source = '{_SEED_SOURCE}' "
        f"AND related_item_id = '{_SEED_RELATED_ID}'"
    )


def upgrade() -> None:
    _retype(op, _OLD_TYPE, _NEW_TYPE)


def downgrade() -> None:
    _retype(op, _NEW_TYPE, _OLD_TYPE)
