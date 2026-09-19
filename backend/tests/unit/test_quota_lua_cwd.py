"""R2 N1 (P1)：quota.py Lua 路径 CWD 相对导致配额静默 fail-open。

复现路径（R2 报告 §3 N1 实证）：以 backend/（或任意非仓库根）为 CWD 运行时，
``RATE_LIMIT_LUA_PATH = "backend/app/services/lua/rate_limit.lua"`` 解析为不存在路径，
脚本加载失败仅 warning，``check_and_decr`` 对外返回 ``QuotaResult(allowed=True, current=0)``
——配额被确定性关闭。

修复契约：Lua 路径以模块位置 pathlib 锚定（``Path(__file__).parents[1]/"lua"``），
任意 CWD（含 chdir /tmp）下配额仍真实生效。
"""

from __future__ import annotations

import os
import uuid

import pytest
import redis.asyncio as redis

from app.services.quota import RedisRateLimiter


@pytest.fixture()
async def redis_client():
    url = os.environ.get("REDIS_URL")
    if not url:
        pytest.skip("REDIS_URL not configured")
    client = redis.from_url(url, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:
        # Needs live Redis (dev sparkle_redis requires AUTH); the contract
        # under test — real quota enforcement across CWD changes — cannot be
        # observed against an unreachable instance.
        await client.aclose()
        pytest.skip(f"live Redis unavailable ({exc.__class__.__name__})")
    yield client
    await client.aclose()


@pytest.mark.asyncio
async def test_quota_enforced_after_chdir_tmp(redis_client):
    limiter = RedisRateLimiter(redis_client=redis_client, daily_limit=10, ttl_seconds=86400)
    user_id = f"quota-cwd-{uuid.uuid4().hex}"
    key = limiter._quota_key(user_id)
    original_cwd = os.getcwd()
    try:
        os.chdir("/tmp")  # 模拟 run_grpc_with_env.sh / 容器等任意 CWD

        first = await limiter.check_and_decr(user_id, 6)
        # fail-open 特征是 (allowed=True, current=0)；真实计数应回写 current
        assert first.allowed, "额度内请求必须放行"
        assert first.current == 6, f"脚本加载失败时 fail-open 返回 current=0（实际: {first}）"

        second = await limiter.check_and_decr(user_id, 5)
        assert not second.allowed, (
            "6+5>10 必须拒绝；fail-open（CWD 相对路径加载失败）会返回 allowed=True —— "
            f"实际: {second}"
        )

        refunded = await limiter.refund(user_id, 3)
        # refund 语义 = 回退后的累计用量（R2 §4.2：700 经 refund 300 → 400），
        # 用量 6 → 3；remaining 语义（7）才是错的
        assert refunded == 3, f"refund 后累计用量应为 3（实际: {refunded}），refund 脚本同样必须 CWD 无关"
    finally:
        os.chdir(original_cwd)
        await redis_client.delete(key)
