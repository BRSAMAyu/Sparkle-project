#!/usr/bin/env python3
"""D-REDEEM · 展会一次性引导脚本：在目标部署库上直接铸造演示兑换码。

用途：参赛演示开始前，对已应用 rd01_20260922 迁移的部署库生成 5 枚
pro/30 天兑换码（等价于 admin API POST /api/v1/billing/redeem-codes，
但无需先造 admin 账号）。运行后明码只打印一次 —— **不落日志、可安全入
参赛报告**（报告归档于 docs/competition/）。

用法（在 backend 目标环境执行）：
    cd backend && python ../scripts/devtools/generate_demo_redeem_codes.py \
        --count 5 --tier pro --duration-days 30

环境要求：DATABASE_URL（或默认 settings）指向目标库；alembic 已 upgrade 至
rd01_20260922 及以后。

# One-shot Script Contract:
#   category: devtools（一次性引导，非治理守卫）
#   lifecycle: 参赛演示期；演示结束后可随批次记录一起废弃
#   writes: redeem_codes 表（INSERT）；绝不动 users
#   owner: "backend"
#   ticket: "D-REDEEM（参赛付费闭环演示）"
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("TESTING", "false")


async def main() -> int:
    parser = argparse.ArgumentParser(description="铸造演示兑换码（明码仅打印一次）")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--tier", type=str, default="pro")
    parser.add_argument("--duration-days", type=int, default=30)
    parser.add_argument("--max-uses", type=int, default=1)
    parser.add_argument("--batch-id", type=str, default=None)
    args = parser.parse_args()

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import settings
    from app.db.session import AsyncSessionLocal
    from app.services import redeem_service

    engine_url = settings.DATABASE_URL
    if not engine_url:
        print("ERROR: DATABASE_URL 未设置（需指向已迁移的目标库）", file=sys.stderr)
        return 1

    async with AsyncSessionLocal() as db:  # type: AsyncSession
        batch = await redeem_service.generate_batch(
            db,
            tier=args.tier,
            duration_days=args.duration_days,
            count=args.count,
            max_uses=args.max_uses,
            batch_id=args.batch_id,
            expires_in_days=90,
        )
        await db.commit()

    print(f"batch_id={batch.batch_id} tier={args.tier} duration_days={args.duration_days}")
    for code in batch.codes:
        print(code)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
