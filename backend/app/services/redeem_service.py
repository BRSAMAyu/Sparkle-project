"""
Core: <execution>
Phase: <execute>
Stage: D-REDEEM

兑换码服务 —— 参赛期付费闭环（DL-D-R1 MONETIZATION §5 第 0 期）。

面分工（分层边界）：
- admin 批量生成（生成面）：``generate_batch`` —— 明文只在返回值中出现一次；
- 用户核销（核销面）：``redeem`` —— 原子条件 UPDATE 防并发双花，核销成功
  将用户 ``users.entitlement`` 升 pro 并写 ``entitlement_expires_at``
  （叠加语义：仍在有效期内的 pro 从现到期日顺延，否则从当前时刻起算）。

安全红线：
- **明文不落库不进日志**：表里只有域分隔 SHA-256（``hash_redeem_code``）；
  本模块所有 logger 调用禁止携带明文/哈希以外的码面信息（测试有 caplog 断言）。
- 判级真源唯一：授予/到期判定只走 ``app/core/entitlement``，不在本模块造
  第二判级。
"""

from __future__ import annotations

import hashlib
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlement import (
    ENTITLEMENT_PRO,
    entitlement_effective,
)
from app.core.time_utils import utcnow
from app.models.redeem_code import RedeemCode
from app.models.user import User

#: 码面字母表：去掉 0/O/1/I/L 的易混淆字符（31 个，手抄友好）
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
#: 码格式 SPARK-XXXX-XXXX-XXXX（前缀 5 + 12 位随机段）
CODE_GROUP_COUNT = 3
CODE_GROUP_SIZE = 4
CODE_NORMALIZED_LENGTH = 5 + CODE_GROUP_COUNT * CODE_GROUP_SIZE
#: 哈希域分隔前缀（防跨系统彩虹表复用）
HASH_DOMAIN = "sparkle_redeem.v1"

_NORMALIZE_RE = re.compile(r"[^0-9A-Za-z]")

# 核销终态词表（有界，API 面按此映射 HTTP 语义）
REDEEM_OK = "ok"
REDEEM_INVALID = "invalid"
REDEEM_EXPIRED = "expired"
REDEEM_EXHAUSTED = "exhausted"
REDEEM_ERROR = "error"


def normalize_redeem_code(raw: str) -> str:
    """任意输入 → 归一化码面（去非字母数字 + 大写）。用于哈希与幂等比对。"""
    return _NORMALIZE_RE.sub("", str(raw or "")).upper()


def hash_redeem_code(normalized: str) -> str:
    """归一化码面 → 域分隔 SHA-256 hex。这是 DB 里唯一存在的码面形态。"""
    return hashlib.sha256(f"{HASH_DOMAIN}:{normalized}".encode("utf-8")).hexdigest()


def looks_like_redeem_code(normalized: str) -> bool:
    """格式前置校验（长度 + 前缀），防止无意义哈希查库。"""
    return len(normalized) == CODE_NORMALIZED_LENGTH and normalized.startswith("SPARK")


def generate_redeem_code() -> str:
    """生成单枚明文码 SPARK-XXXX-XXXX-XXXX（secrets CSPRNG）。"""
    groups = [
        "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_GROUP_SIZE))
        for _ in range(CODE_GROUP_COUNT)
    ]
    return "SPARK-" + "-".join(groups)


@dataclass
class RedeemOutcome:
    """核销终态（有界词表 + 展示面字段）。"""

    status: str
    tier: str | None = None
    entitlement_expires_at: datetime | None = None
    message: str | None = None


@dataclass
class GeneratedBatch:
    """批次生成结果：``codes`` 是明文唯一出口。"""

    batch_id: str
    codes: list[str]
    expires_at: datetime | None = None


async def generate_batch(
    db: AsyncSession,
    *,
    tier: str = ENTITLEMENT_PRO,
    duration_days: int = 30,
    count: int = 5,
    max_uses: int = 1,
    created_by: UUID | str | None = None,
    batch_id: str | None = None,
    expires_in_days: int | None = None,
) -> GeneratedBatch:
    """admin 面批量生成。哈希冲突/格式异常自动重生成；flush 不 commit（get_db 收口）。"""
    from app.core.entitlement import normalize_entitlement

    if normalize_entitlement(tier) != ENTITLEMENT_PRO:
        raise ValueError("tier 仅支持 'pro'（参赛演示期封闭词表）")
    resolved_batch_id = (batch_id or f"batch-{uuid4().hex[:12]}")[:64]
    now = utcnow()
    expires_at = now + timedelta(days=expires_in_days) if expires_in_days else None

    codes: list[str] = []
    seen_hashes: set[str] = set()
    while len(codes) < count:
        code = generate_redeem_code()
        normalized = normalize_redeem_code(code)
        if not looks_like_redeem_code(normalized):  # 防字母表/长度配置回归
            continue
        code_hash = hash_redeem_code(normalized)
        if code_hash in seen_hashes:
            continue
        existing = (
            await db.execute(select(RedeemCode.id).where(RedeemCode.code_hash == code_hash))
        ).scalar_one_or_none()
        if existing is not None:
            continue
        seen_hashes.add(code_hash)
        db.add(
            RedeemCode(
                code_hash=code_hash,
                code_prefix=code[: 5 + CODE_GROUP_SIZE],  # SPARK-XXXX（缺末段，非明文）
                tier=normalize_entitlement(tier),
                duration_days=duration_days,
                max_uses=max_uses,
                used_count=0,
                created_by=created_by,
                batch_id=resolved_batch_id,
                expires_at=expires_at,
            )
        )
        codes.append(code)
    await db.flush()
    logger.info(
        "redeem batch created batch_id={} count={} duration_days={} max_uses={}",
        resolved_batch_id,
        len(codes),
        duration_days,
        max_uses,
    )
    return GeneratedBatch(batch_id=resolved_batch_id, codes=codes, expires_at=expires_at)


async def get_batch_summary(db: AsyncSession, *, batch_id: str) -> dict | None:
    """admin 面：批次核销进度（不含任何码面信息）。None = 批次不存在。"""
    rows = (
        await db.execute(
            select(
                RedeemCode.batch_id,
                RedeemCode.tier,
                RedeemCode.duration_days,
                RedeemCode.expires_at,
                RedeemCode.created_by,
            )
            .where(RedeemCode.batch_id == batch_id, RedeemCode.not_deleted_filter())
            .limit(1)
        )
    ).first()
    if rows is None:
        return None
    total_used = (
        await db.execute(
            select(RedeemCode.used_count).where(
                RedeemCode.batch_id == batch_id,
                RedeemCode.not_deleted_filter(),
            )
        )
    ).scalars().all()
    total_rows = (
        await db.execute(
            select(RedeemCode.id).where(
                RedeemCode.batch_id == batch_id,
                RedeemCode.not_deleted_filter(),
            )
        )
    ).all()
    batch_id_, tier, duration_days, expires_at, created_by = rows
    return {
        "batch_id": batch_id_,
        "tier": tier,
        "duration_days": duration_days,
        "expires_at": expires_at,
        "created_by": created_by,
        "total": len(total_rows),
        "used_count": sum(total_used),
    }


async def redeem(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    code: str,
) -> RedeemOutcome:
    """用户核销入口。原子性：条件 UPDATE（used_count < max_uses 行内守卫）
    在行锁下串行化，并发同码恰成功 max_uses 次；flush 不 commit（get_db 收口）。"""
    normalized = normalize_redeem_code(code)
    if not looks_like_redeem_code(normalized):
        return RedeemOutcome(status=REDEEM_INVALID, message="兑换码格式无效")

    row = (
        await db.execute(
            select(RedeemCode).where(
                RedeemCode.code_hash == hash_redeem_code(normalized),
                RedeemCode.not_deleted_filter(),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return RedeemOutcome(status=REDEEM_INVALID, message="兑换码不存在或已失效")

    now = utcnow()
    if row.expires_at is not None and row.expires_at <= now:
        logger.info("redeem rejected code_prefix={} batch_id={} reason=expired", row.code_prefix, row.batch_id)
        return RedeemOutcome(status=REDEEM_EXPIRED, message="兑换码已过期")

    # —— 原子核销（防并发双花的唯一判定点）——
    claimed = await db.execute(
        update(RedeemCode)
        .where(
            RedeemCode.id == row.id,
            RedeemCode.used_count < RedeemCode.max_uses,
        )
        .values(used_count=RedeemCode.used_count + 1, used_by=user_id, used_at=now)
    )
    if claimed.rowcount != 1:
        logger.info("redeem rejected code_prefix={} batch_id={} reason=exhausted", row.code_prefix, row.batch_id)
        return RedeemOutcome(status=REDEEM_EXHAUSTED, message="兑换码已被使用")

    outcome = await _grant_pro(
        db, user_id=user_id, tier=row.tier, duration_days=row.duration_days, now=now
    )
    if outcome.status != REDEEM_OK:
        return outcome
    logger.info(
        "redeem ok user_id={} code_prefix={} batch_id={} tier={} new_expiry={}",
        user_id,
        row.code_prefix,
        row.batch_id,
        outcome.tier,
        outcome.entitlement_expires_at,
    )
    return outcome


async def _grant_pro(
    db: AsyncSession,
    *,
    user_id: UUID | str,
    tier: str,
    duration_days: int,
    now: datetime | None = None,
) -> RedeemOutcome:
    """核销成功后的权益授予（叠加语义）。

    - 授予档位经 ``normalize_entitlement`` 归一（生成面已封闭为 'pro'）；
    - 仍在有效期的 pro 从现到期日顺延；free / 已过期从当前时刻起算；
    - 永久 pro 特例：``entitlement_expires_at`` 保持 NULL——码的时长在永久
      权益上无叠加意义，且绝不把既有永久权益降级为有期权益。
    """
    from app.core.entitlement import normalize_entitlement

    granted_tier = normalize_entitlement(tier)
    now_value: datetime = now or utcnow()

    user_row = (
        await db.execute(
            select(User.entitlement, User.entitlement_expires_at).where(User.id == user_id)
        )
    ).one_or_none()
    if user_row is None:
        return RedeemOutcome(status=REDEEM_ERROR, message="用户不存在")

    current_entitlement, current_expires = user_row
    effective_now = entitlement_effective(current_entitlement, current_expires, now=now_value)
    if effective_now == ENTITLEMENT_PRO and current_expires is None:
        # 永久 pro：保持 NULL（绝不把既有永久权益降级为有期权益）。
        new_expiry = None
    elif effective_now == ENTITLEMENT_PRO and current_expires is not None and current_expires > now_value:
        new_expiry = current_expires + timedelta(days=duration_days)
    else:
        new_expiry = now_value + timedelta(days=duration_days)

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(entitlement=granted_tier, entitlement_expires_at=new_expiry)
    )
    return RedeemOutcome(
        status=REDEEM_OK,
        tier=granted_tier,
        entitlement_expires_at=new_expiry,
        message="兑换成功",
    )
