#!/usr/bin/env python3
"""V4-Q04 计费死信恢复 — 用 BillingWorker 自身的落库映射直插 token_usage.

背景：共享 Redis 的 queue:billing 有第二个消费者（主检出驻留栈 worker，凭据失效），
每次 RPUSH 恢复都被其抢占并以 password auth 失败回写死信，恢复循环无法收敛。
本脚本绕过队列竞争：读 queue:billing:dead_letter 中的本 bench 记录（request_id 前缀
过滤），用 BillingWorker._to_stmt_data 的同一列映射与 insert 语句直接落库；
duplicate key 静默跳过（与 worker._retry_individually 同语义）。

这是恢复产品自身已产出的真实计量（非 Mock/非人工造数）；恢复范围、条数与理由
记录于 V4-Q04 run_manifest.recovery。

用法:
  DATABASE_URL=postgresql+asyncpg://... REDIS_URL=redis://... python3 recover_q04_billing_deadletter.py \
      --prefix wtq04- --dry-run | --apply
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from redis import asyncio as aioredis  # noqa: E402

QUEUE = "queue:billing:dead_letter"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", default="wtq04-")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        ap.error("需要 --dry-run 或 --apply")

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        print("REDIS_URL 必填（redis://:pw@host:port/0）", file=sys.stderr)
        return 2
    r = aioredis.from_url(redis_url, decode_responses=True)
    entries = await r.lrange(QUEUE, 0, -1)
    recs: dict[str, dict] = {}
    for line in entries:
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        rec = e.get("record") or {}
        rid = rec.get("request_id", "")
        if rid.startswith(args.prefix):
            recs.setdefault(rid, rec)
    print(f"dead_letter 总条目={len(entries)}，本 bench 去重记录={len(recs)}")
    if not recs:
        return 0

    from app.db.session import AsyncSessionLocal  # noqa: PLC0415
    from app.models.chat import TokenUsage  # noqa: PLC0415
    from app.services.billing_worker import BillingWorker  # noqa: PLC0415
    from sqlalchemy import insert, select  # noqa: PLC0415

    worker = BillingWorker()
    existing: set[str] = set()
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(TokenUsage.request_id).where(TokenUsage.request_id.in_(list(recs)))
        )
        existing = {r[0] for r in rows}
    todo = {k: v for k, v in recs.items() if k not in existing}
    print(f"已在库={len(existing)}，待恢复={len(todo)}")

    applied = skipped = failed = 0
    for rid, rec in todo.items():
        if args.dry_run:
            print(f"  [dry] {rid} model={rec.get('model')} tokens={rec.get('total_tokens')}")
            applied += 1
            continue
        try:
            async with AsyncSessionLocal() as session:
                async with session.begin_nested():
                    await session.execute(insert(TokenUsage), worker._to_stmt_data(rec))
                await session.commit()
            applied += 1
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if "duplicate key" in msg or "unique constraint" in msg:
                skipped += 1
            else:
                failed += 1
                print(f"  [fail] {rid}: {str(exc)[:120]}", file=sys.stderr)
    print(f"applied={applied} skipped_dup={skipped} failed={failed}")
    await r.aclose()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
