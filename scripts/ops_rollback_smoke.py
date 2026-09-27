#!/usr/bin/env python3
"""O-06 · rollback smoke —— 统一操作面翻转/回滚冒烟.

场景（单能力，三步）：live 基线读取 → 翻到 shadow → rollback 恢复；
全程断言一个哨兵「用户态键」逐字不变（验收：shadow/live 切换不丢用户 state）。

安全姿态（绝不默认真实 destructive）：
- 默认 ``--in-process``：fakeredis 进程内实例，零真实栈接触，可无栈运行；
- ``--redis-url`` 运维模式：对真实 Redis 执行，**必须**同时显式给出
  ``--i-understand-this-flips-real-capabilities`` 与 ``--capability <id>``，
  且目标 mode 硬编码为 ``shadow``（回滚恢复）——本脚本永不写 ``off``/``live``，
  不提供批量端点，不做「先看后动」以外的一键动作。

用法：
    python3 scripts/ops_rollback_smoke.py                       # fakeredis 冒烟
    python3 scripts/ops_rollback_smoke.py --capability 39.mode  # 同上，指定能力
    python3 scripts/ops_rollback_smoke.py --redis-url redis://localhost:6379/0 \
        --capability 39.mode --i-understand-this-flips-real-capabilities
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

# 本脚本显式面向「进程内 fakeredis 或运维显式给 URL」两种受控形态，
# 不读 .env / 不连默认栈（AUTH/环境判据与运行栈零接触）。
sys.path.insert(0, str(BACKEND_DIR))

SMOKE_TARGET_MODE = "shadow"  # 硬编码：冒烟只翻 shadow，靠 rollback 恢复
SENTINEL_KEY = "sparkle:ops:smoke_sentinel:user_state"
SENTINEL_VALUE = "user-state-must-not-change"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--capability", default="dual_core_router.mode", help="capability_id（默认 dual_core_router.mode）"
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--in-process", action="store_true", help="fakeredis 进程内冒烟（默认）")
    mode_group.add_argument("--redis-url", default=None, help="真实 Redis URL（运维模式）")
    parser.add_argument(
        "--i-understand-this-flips-real-capabilities",
        action="store_true",
        help="运维模式二次确认；缺失时拒绝执行真实翻转",
    )
    return parser.parse_args()


async def _run(client: Any, capability_id: str) -> int:
    from app.core import ops_surface

    spec = ops_surface.get_spec(capability_id)
    await client.set(SENTINEL_KEY, SENTINEL_VALUE)

    snapshot = await ops_surface.capability_snapshot(client, spec)
    baseline_mode = snapshot["mode"]
    print(f"[1/3] baseline: {capability_id} mode={baseline_mode} (settings_mode={snapshot['settings_mode']})")

    set_result = await ops_surface.set_capability_mode(
        client, spec, SMOKE_TARGET_MODE, actor="rollback-smoke", reason="O-06 smoke"
    )
    print(f"[2/3] flipped: {baseline_mode} -> {set_result['mode']} (history_recorded={set_result['history_recorded']})")
    if set_result["mode"] != SMOKE_TARGET_MODE:
        print(f"FAIL: expected {SMOKE_TARGET_MODE}, got {set_result['mode']}")
        return 1

    rollback = await ops_surface.rollback_capability(client, spec, actor="rollback-smoke")
    print(f"[3/3] rollback: {rollback['previous_mode']} -> {rollback['mode']}")
    history = await ops_surface.capability_history(client, spec, limit=5)

    checks = {
        "flipped_to_shadow": set_result["mode"] == SMOKE_TARGET_MODE,
        "rollback_restored_baseline": rollback["mode"] == baseline_mode,
        "history_recorded": bool(history) and history[0].get("action") == "rollback",
        "user_state_intact": await client.get(SENTINEL_KEY) == SENTINEL_VALUE,
    }
    for name, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    if not all(checks.values()):
        return 1
    print("SMOKE OK")
    return 0


async def main_async() -> int:
    args = _parse_args()
    if args.redis_url:
        if not args.i_understand_this_flips_real_capabilities:
            print("REFUSING: --redis-url requires --i-understand-this-flips-real-capabilities")
            return 2
        import redis.asyncio as aioredis

        client = aioredis.from_url(args.redis_url)
    else:
        import fakeredis.aioredis

        # decode_responses=True 与生产 cache_service 客户端同构（cache.py:73）。
        client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    try:
        return await _run(client, args.capability)
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()
        elif hasattr(client, "close"):
            await client.close()  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))
