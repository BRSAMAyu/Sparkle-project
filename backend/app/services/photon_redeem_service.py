"""
Core: <execution>
Phase: <execute>
Stage: D-COMM-2

光子 → Pro 7 天有界兑换通道（「学出会员」，D-COMMUNITY §3.1 裁决落地）。

口径（设计卡原文裁决）：
- 可兑换基数 = 审计流水重放：``transaction_type IN (grant_achievement,
  grant_daily_first, grant_contract, grant_contract_bonus)`` 的累计净收入，
  ``deduct_contract_stake / penalty`` 同步扣减基数；**``transfer_in`` 一律
  不计入**（封堵小号互转刷会员；``transfer_out`` 也不返还基数）。
- 兑换产出：复用 D-REDEEM 核销核 ``redeem_service._grant_pro`` 的叠加语义
  （有效期内顺延 / 过期与 free 从当前时刻起算 / 永久 pro 绝不降级为有期），
  写 ``users.entitlement='pro'`` + ``entitlement_expires_at``。
- 月顶：每自然月（UTC）硬顶 1 次，判定真源是 ``photon_transaction_history``
  中本通道扣减流水（``redeem_pro``）——审计即状态，零新表零迁移。
- 幂等：月顶即幂等屏障——同月重复请求恒返回 ``monthly_cap``，不重复扣减、
  不重复授予，状态收敛。

并发安全（模式同 D-REDEEM §0 条件 UPDATE 族）：
单事务内以光子原子扣减（``UPDATE users SET photon_balance = photon_balance -
cost WHERE photon_balance >= cost`` 的行内守卫）为**每用户串行化点**：
并发同用户兑换在扣减行锁上排序，后到者在锁授予后（READ COMMITTED 新快照）
做月顶复查，必见先到者已提交的 ``redeem_pro`` 流水 → 拒绝并回滚扣减。
扣减先于月顶复查、流水的写入晚于复查（自查不可见自身行），两引擎
（PG / sqlite）语义一致。

事务语义：与 redeem_service 同款——本模块只 flush 不 commit（get_db 收口）；
业务拒绝路径内部 rollback 自愈（撤销已 flush 的扣减）后返回结构化终态。

诚实申报（基数口径的既有缝隙，fail-safe 方向=少算不多算）：
- 每日首胜发放点（achievement_engine）未开 ``record_history``，流水无该收入；
- combo 加成发放用 ``grant_bonus`` 类型，不在设计卡四类型词表内。
  两者均为**发放侧既有现状**，本卡不修（给 daily_first 补流水会触发
  ``_find_existing_transaction`` 去重路径吞掉次日首胜，须独立设计去重键）；
  后果仅是基数少算、用户可兑上限降低，绝不反向放水。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.time_utils import utcnow
from app.models.shop import PhotonTransactionHistory
from app.services.photon_service import PhotonService
from app.services.redeem_service import _grant_pro

# ---------------------------------------------------------------------------
# 有界词表：业务终态（API 面按此映射 HTTP 语义，风格同 redeem_service）
# ---------------------------------------------------------------------------
REDEEM_PRO_OK = "ok"
REDEEM_PRO_INSUFFICIENT_BALANCE = "insufficient_balance"
REDEEM_PRO_INSUFFICIENT_BASE = "insufficient_base"
REDEEM_PRO_MONTHLY_CAP = "monthly_cap_reached"
REDEEM_PRO_ERROR = "error"

#: 本通道扣减流水类型（photon_transaction_history.transaction_type；
#: 已登记进 models/shop.PhotonTransactionType 枚举，杜绝 admin_adjustment 兜底误标）
REDEEM_PRO_TX_TYPE = "redeem_pro"

#: 可兑换收入来源（设计卡 §3.1 四类型封闭词表——transfer_in 天然不在表内）
REDEEMABLE_INCOME_TYPES: tuple[str, ...] = (
    "grant_achievement",
    "grant_daily_first",
    "grant_contract",
    "grant_contract_bonus",
)
#: 同步扣减基数的支出类型（契约失败扣 stake / 惩罚）
REDEEMABLE_DEDUCT_TYPES: tuple[str, ...] = (
    "deduct_contract_stake",
    "penalty",
)

REDEEM_SOURCE = "photon_redeem_pro"  # 审计 source 字面（流水溯源用）


@dataclass
class PhotonRedeemOutcome:
    """兑换终态（有界词表 + 展示面字段）。"""

    status: str
    cost_photons: int
    pro_days: int
    redeemable_base: int | None = None
    balance_after: int | None = None
    entitlement_expires_at: datetime | None = None
    message: str | None = None


def redeem_pro_cost() -> int:
    """单次兑换光子价（settings 可调，【待产品校准】）。"""
    return max(1, int(settings.PHOTON_REDEEM_PRO_COST))


def redeem_pro_days() -> int:
    """单次兑换 Pro 天数（settings 可调，【待产品校准】）。"""
    return max(1, int(settings.PHOTON_REDEEM_PRO_DAYS))


def redeem_pro_monthly_cap() -> int:
    """自然月兑换硬顶次数（设计卡裁决默认 1）。"""
    return max(0, int(settings.PHOTON_REDEEM_PRO_MONTHLY_CAP))


def _month_start(now: datetime) -> datetime:
    """UTC 自然月起点（naive，与 created_at 存储形一致）。"""
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def get_redeemable_base(db: AsyncSession, *, user_id: str) -> int:
    """可兑换基数：四类收入累计净额 − 契约失败/惩罚扣减，下限 0。

    纯审计流水重放（余额是混桶单字段，无来源分桶——见盘点报告）；
    ``transfer_in`` 不在收入词表内，天然不计入。
    """
    income = (
        await db.execute(
            select(func.coalesce(func.sum(PhotonTransactionHistory.amount), 0)).where(
                PhotonTransactionHistory.user_id == user_id,
                PhotonTransactionHistory.transaction_type.in_(REDEEMABLE_INCOME_TYPES),
            )
        )
    ).scalar_one()
    deduct = (
        await db.execute(
            select(func.coalesce(func.sum(PhotonTransactionHistory.amount), 0)).where(
                PhotonTransactionHistory.user_id == user_id,
                PhotonTransactionHistory.transaction_type.in_(REDEEMABLE_DEDUCT_TYPES),
            )
        )
    ).scalar_one()
    # 扣减类 amount 恒为负（record_transaction 落 -amount），直接相加即净额
    return max(0, int(income or 0) + int(deduct or 0))


async def _count_redeems_in_month(
    db: AsyncSession, *, user_id: str, month_start: datetime
) -> int:
    """当月已兑换笔数（本通道扣减流水；调用点保证自身行尚未写入）。"""
    return int(
        (
            await db.execute(
                select(func.count(PhotonTransactionHistory.id)).where(
                    PhotonTransactionHistory.user_id == user_id,
                    PhotonTransactionHistory.transaction_type == REDEEM_PRO_TX_TYPE,
                    PhotonTransactionHistory.created_at >= month_start,
                )
            )
        ).scalar_one()
    )


async def redeem_pro(db: AsyncSession, *, user_id: str) -> PhotonRedeemOutcome:
    """光子兑换 Pro：校验月顶/基数 → 原子扣减 → 复查月顶 → 写流水 → 授予 Pro。

    单事务：任一拒绝路径内部 rollback 后返回结构化终态（不抛 HTTP 异常，
    映射留给 API 面）；成功路径 flush 不 commit（get_db 收口）。
    """
    cost = redeem_pro_cost()
    days = redeem_pro_days()
    now = utcnow()

    # —— 快速失败面（无状态变更）：当月已兑 / 基数不足 ——
    month_start = _month_start(now)
    if await _count_redeems_in_month(db, user_id=user_id, month_start=month_start) >= redeem_pro_monthly_cap():
        return PhotonRedeemOutcome(
            status=REDEEM_PRO_MONTHLY_CAP,
            cost_photons=cost,
            pro_days=days,
            message="本月兑换次数已用完，下个月再来",
        )

    base = await get_redeemable_base(db, user_id=user_id)
    if base < cost:
        return PhotonRedeemOutcome(
            status=REDEEM_PRO_INSUFFICIENT_BASE,
            cost_photons=cost,
            pro_days=days,
            redeemable_base=base,
            message="可兑换光子不足：仅合同/首胜/成就所得可兑换（转账收入不计入）",
        )

    photon_service = PhotonService(db)
    try:
        # —— 原子扣减（每用户串行化点；行内守卫 photon_balance >= cost）——
        # manage_transaction=False：只 flush，事务收口归调用方（get_db 同款）
        deduct_result = await photon_service.deduct_photons(
            user_id=user_id,
            amount=cost,
            reason=REDEEM_SOURCE,
            transaction_type=REDEEM_PRO_TX_TYPE,
            extra_data={"pro_days": days, "channel": "photon_redeem_pro"},
            record_history=False,  # 流水在月顶复查后补写（避免自查撞见自身行）
            manage_transaction=False,
        )
    except ValueError as exc:
        # 余额不足（含用户不存在）——扣减未生效，无需回滚
        logger.info("photon redeem rejected user_id={} reason=deduct_failed: {}", user_id, exc)
        return PhotonRedeemOutcome(
            status=REDEEM_PRO_INSUFFICIENT_BALANCE,
            cost_photons=cost,
            pro_days=days,
            redeemable_base=base,
            message="光子余额不足",
        )

    # —— 月顶复查（串行化点之后；自身流水尚未写入，只见他人已提交行）——
    if await _count_redeems_in_month(db, user_id=user_id, month_start=month_start) >= redeem_pro_monthly_cap():
        await db.rollback()  # 自愈：撤销已 flush 的扣减
        return PhotonRedeemOutcome(
            status=REDEEM_PRO_MONTHLY_CAP,
            cost_photons=cost,
            pro_days=days,
            message="本月兑换次数已用完，下个月再来",
        )

    # —— 双写流水（photon 侧扣减审计）——
    await photon_service.record_transaction(
        user_id=user_id,
        transaction_type=REDEEM_PRO_TX_TYPE,
        amount=-cost,
        balance_before=deduct_result["old_balance"],
        balance_after=deduct_result["new_balance"],
        source=REDEEM_SOURCE,
        extra_data={"pro_days": days, "channel": "photon_redeem_pro"},
    )

    # —— 授予 Pro（复用 D-REDEEM 核销核：叠加语义 + 永久 pro 保护）——
    grant = await _grant_pro(db, user_id=user_id, tier="pro", duration_days=days, now=now)
    if grant.status != "ok":
        await db.rollback()
        return PhotonRedeemOutcome(
            status=REDEEM_PRO_ERROR,
            cost_photons=cost,
            pro_days=days,
            message=grant.message or "权益授予失败",
        )

    await db.flush()
    logger.info(
        "photon redeem ok user_id={} cost={} days={} balance={} new_expiry={}",
        user_id,
        cost,
        days,
        deduct_result["new_balance"],
        grant.entitlement_expires_at,
    )
    return PhotonRedeemOutcome(
        status=REDEEM_PRO_OK,
        cost_photons=cost,
        pro_days=days,
        redeemable_base=base,
        balance_after=deduct_result["new_balance"],
        entitlement_expires_at=grant.entitlement_expires_at,
        message="兑换成功",
    )
