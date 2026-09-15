from __future__ import annotations

import hashlib
from dataclasses import dataclass

from loguru import logger

from app.core.cache import cache_service

RATE_LIMIT_LUA_PATH = "backend/app/services/lua/rate_limit.lua"
RATE_LIMIT_REFUND_LUA_PATH = "backend/app/services/lua/rate_limit_refund.lua"


@dataclass
class QuotaResult:
    allowed: bool
    current: int


class RedisRateLimiter:
    def __init__(self, redis_client=None, daily_limit: int = 100000, ttl_seconds: int = 86400):
        self.redis = redis_client
        self.daily_limit = daily_limit
        self.ttl_seconds = ttl_seconds
        self._script_sha: str | None = None
        self._refund_script_sha: str | None = None

    async def _load_script(self, path: str = RATE_LIMIT_LUA_PATH, *, refund: bool = False) -> str | None:
        if not self.redis:
            return None
        current_sha = self._refund_script_sha if refund else self._script_sha
        if current_sha:
            return current_sha
        try:
            with open(path, encoding="utf-8") as handle:
                script = handle.read()
            loaded_sha = await self.redis.script_load(script)
            if refund:
                self._refund_script_sha = loaded_sha
            else:
                self._script_sha = loaded_sha
        except Exception as exc:
            logger.warning(f"Rate limiter script load failed: {exc}")
            if refund:
                self._refund_script_sha = None
            else:
                self._script_sha = None
        return self._refund_script_sha if refund else self._script_sha

    @staticmethod
    def _quota_key(user_id: str) -> str:
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]
        return f"quota:daily:{digest}"

    async def check_and_decr(self, user_id: str, amount: int) -> QuotaResult:
        if not self.redis or not user_id:
            return QuotaResult(allowed=True, current=0)
        if amount <= 0:
            return QuotaResult(allowed=True, current=0)
        sha = await self._load_script()
        if not sha:
            return QuotaResult(allowed=True, current=0)
        key = self._quota_key(user_id)
        try:
            allowed, current = await self.redis.evalsha(
                sha,
                1,
                key,
                self.daily_limit,
                amount,
                self.ttl_seconds,
            )
            return QuotaResult(allowed=bool(allowed), current=int(current))
        except Exception as exc:
            logger.warning(f"Rate limiter eval failed: {exc}")
            return QuotaResult(allowed=True, current=0)

    async def refund(self, user_id: str, amount: int) -> int:
        if not self.redis or not user_id or amount <= 0:
            return 0
        sha = await self._load_script(RATE_LIMIT_REFUND_LUA_PATH, refund=True)
        if not sha:
            return 0
        key = self._quota_key(user_id)
        try:
            current = await self.redis.evalsha(
                sha,
                1,
                key,
                amount,
                self.ttl_seconds,
            )
            return int(current)
        except Exception as exc:
            logger.warning(f"Rate limiter refund failed: {exc}")
            return 0


async def get_rate_limiter() -> RedisRateLimiter:
    if not cache_service.redis:
        await cache_service.init_redis()
    return RedisRateLimiter(redis_client=cache_service.redis)
