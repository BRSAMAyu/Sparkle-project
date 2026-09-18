"""
Core: infra
Phase: execute
Stage: restore-storm guard (engine-restore-storm)

请求合并（single-flight）+ 短 TTL 结果缓存 + 端点级并发钳制。

背景（2026-09-18 会话恢复风暴实证）：客户端恢复会在 ~1s 内并发拉取 20+ 端点，
同一 user 的重端点（galaxy/graph、aurora/control-surface、predictive 等）被重复
计算；一旦事件循环被慢调用卡住，恢复风暴会把单点放大成全端点雪崩（网关 30s
超时 → 503 连环）。

三道进程内防线（零外部依赖，Redis 不可用时同样生效）：
1. 短 TTL 结果缓存 —— 恢复场景下 5-15s 内重复拉取等价，直接命中缓存返回；
2. single-flight —— 同 key 的并发在飞请求合并为一个 loader 调用，其余等待共享
   同一结果（去重，不打 DB）；
3. 并发钳制 —— 端点级 semaphore 限制同时计算的 loader 数（冷启动钳制）；
   获取槽位/加入在飞计算等待超过 ``wait_timeout`` 时抛出 :class:`EndpointOverloaded`
   （由 app.main 统一映射为 503 + Retry-After，快速失败优于无限排队）。

用法（路由 handler 内）::

    _shield = EndpointShield(name="galaxy_graph", max_concurrency=8, ttl=10.0)

    @router.get("/graph")
    async def get_graph(user_id=Depends(...), ...):
        key = f"{user_id}:{sector_code}:{zoom_level}"
        return await _shield.run(key, lambda: _compute_graph(...))

loader 抛出的异常不会写入缓存，只会传播给当前这批等待者；后续新请求会重新计算。
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")


class EndpointOverloaded(RuntimeError):
    """端点并发钳制溢出：等待超过 wait_timeout 仍未获得结果。"""



class _CachedResult:
    __slots__ = ("expires_at", "value")

    def __init__(self, value: Any, expires_at: float) -> None:
        self.value = value
        self.expires_at = expires_at



class EndpointShield:
    """单端点的 single-flight + TTL 缓存 + 并发钳制守卫（进程内）。

    参数：
        name: 端点名（用于日志与观测）。
        max_concurrency: 同时执行的 loader 数上限（冷启动并发钳制）。
        ttl: 结果缓存秒数；``<=0`` 表示只做 single-flight 不缓存结果。
        wait_timeout: 获取计算槽位或加入在飞计算的最长等待秒数，超时雪崩 shedding。
        max_entries: TTL 缓存条目上限，防止 key 空间膨胀。
    """

    def __init__(
        self,
        *,
        name: str,
        max_concurrency: int = 8,
        ttl: float = 10.0,
        wait_timeout: float = 8.0,
        max_entries: int = 512,
    ) -> None:
        self.name = name
        self.ttl = float(ttl)
        self.wait_timeout = float(wait_timeout)
        self.max_entries = int(max_entries)
        self._semaphore = asyncio.Semaphore(max(1, int(max_concurrency)))
        self._cache: dict[str, _CachedResult] = {}
        self._inflight: dict[str, asyncio.Task[Any]] = {}
        # 观测计数（单事件循环内更新，无需锁）
        self.hits = 0
        self.deduped = 0
        self.shed = 0

    # ── 对外入口 ─────────────────────────────────────────────────────────────

    async def run(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        full_key = f"{self.name}:{key}"
        cached = self._cache_get(full_key)
        if cached is not None:
            self.hits += 1
            return cached

        inflight = self._inflight.get(full_key)
        if inflight is not None:
            self.deduped += 1
            return await self._join(inflight, full_key)

        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self.wait_timeout)
        except asyncio.TimeoutError:
            self.shed += 1
            raise EndpointOverloaded(
                f"[{self.name}] compute slots saturated, key={key}"
            ) from None

        try:
            # 拿到槽位后二次检查（等待期间可能已有同 key 计算完成/在飞）
            cached = self._cache_get(full_key)
            if cached is not None:
                self.hits += 1
                return cached
            inflight = self._inflight.get(full_key)
            if inflight is not None:
                self.deduped += 1
                return await self._join(inflight, full_key)
            return await self._compute(full_key, loader)
        finally:
            self._semaphore.release()

    def snapshot(self) -> dict[str, int]:
        """观测用：缓存/在飞/命中/去重/雪崩计数。"""
        return {
            "name": self.name,
            "cache_entries": len(self._cache),
            "inflight": len(self._inflight),
            "hits": self.hits,
            "deduped": self.deduped,
            "shed": self.shed,
        }

    # ── 内部实现 ─────────────────────────────────────────────────────────────

    def _cache_get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._cache.pop(key, None)
            return None
        return entry.value

    async def _join(self, task: asyncio.Task[Any], key: str) -> T:
        """加入在飞计算；等待超过 wait_timeout 视为过载（计算本身不受影响）。"""
        try:
            return await asyncio.wait_for(asyncio.shield(task), timeout=self.wait_timeout)
        except asyncio.TimeoutError:
            self.shed += 1
            raise EndpointOverloaded(f"[{self.name}] inflight join timed out, key={key}") from None

    async def _compute(self, key: str, loader: Callable[[], Awaitable[T]]) -> T:
        task: asyncio.Task[T] = asyncio.ensure_future(loader())
        self._inflight[key] = task
        deadline = time.monotonic() + self.ttl
        task.add_done_callback(lambda t, k=key, d=deadline: self._on_compute_done(k, t, d))
        return await asyncio.shield(task)

    def _on_compute_done(self, key: str, task: asyncio.Task[Any], deadline: float) -> None:
        self._inflight.pop(key, None)
        if task.cancelled():
            return
        if task.exception() is not None:
            return  # 失败不写缓存，让下一个请求重试
        if self.ttl > 0:
            self._cache[key] = _CachedResult(task.result(), deadline)
            self._maybe_evict()

    def _maybe_evict(self) -> None:
        if len(self._cache) <= self.max_entries:
            return
        now = time.monotonic()
        # 先清过期
        for k in [k for k, v in self._cache.items() if v.expires_at <= now]:
            self._cache.pop(k, None)
        # 仍超限时按插入序（近似最旧）丢弃
        while len(self._cache) > self.max_entries:
            self._cache.pop(next(iter(self._cache)), None)
