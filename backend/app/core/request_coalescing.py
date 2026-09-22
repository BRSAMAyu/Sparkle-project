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

失效面（SHIELD-INVAL，2026-09）：TTL 结果缓存原先只有自然过期一条出路，
写路径（诊断评分/任务吸收/mastery 更新）提交后读面最长滞留一个 ttl 窗口的
旧值。:meth:`EndpointShield.invalidate_prefix` 提供按 key 前缀的进程内失效；
跨层触发走 :func:`register_read_view_invalidation_hook` /
:func:`notify_read_view_invalidated` 回调注册表——API 层把本端点 shield 的
失效回调挂进核心，服务层写路径经 notify 宣告「某用户读面已变化」，服务层
因此**不反向 import API 层**。

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
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


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
        # 最近一次前缀失效的 monotonic 时间戳：其前启动的计算不得落缓存，
        # 防止「失效 → 在飞旧值完成回填」把失效悄悄撤销（SHIELD-INVAL）。
        self._last_invalidation = 0.0
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

    def invalidate_prefix(self, key_prefix: str) -> int:
        """按 key 前缀清 TTL 结果缓存（写后即时投影的失效面，SHIELD-INVAL）。

        ``key_prefix`` 与 :meth:`run` 的 ``key`` 同构（不含 name 前缀），
        例如 ``f"{user_id}:"`` 清掉该 user 全部参数变体的缓存条目。只清已
        完成的结果缓存，不打断在飞计算——single-flight 与并发钳制语义
        原样保留；但启动早于本次失效的计算完成后不落缓存（见
        ``_on_compute_done``），失效不会被在飞旧值回填撤销。返回清除的
        条目数（观测用）。纯内存 dict 操作，同步、无 IO。
        """
        full_prefix = f"{self.name}:{key_prefix}"
        victims = [k for k in self._cache if k.startswith(full_prefix)]
        for k in victims:
            self._cache.pop(k, None)
        self._last_invalidation = time.monotonic()
        return len(victims)

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
        started = time.monotonic()
        task: asyncio.Task[T] = asyncio.ensure_future(loader())
        self._inflight[key] = task
        deadline = started + self.ttl
        task.add_done_callback(lambda t, k=key, d=deadline, s=started: self._on_compute_done(k, t, d, s))
        return await asyncio.shield(task)

    def _on_compute_done(self, key: str, task: asyncio.Task[Any], deadline: float, started: float) -> None:
        self._inflight.pop(key, None)
        if task.cancelled():
            return
        if task.exception() is not None:
            return  # 失败不写缓存，让下一个请求重试
        if self.ttl > 0 and started > self._last_invalidation:
            # 启动早于最近一次失效的计算可能读到写前 DB 状态，不落缓存——
            # 否则失效会被这个在飞旧值悄悄回填撤销（SHIELD-INVAL）。
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


# ---------------------------------------------------------------------------
# 读面失效回调注册表（SHIELD-INVAL）
# ---------------------------------------------------------------------------

#: domain → 失效回调列表。回调签名 ``(user_id: str) -> int``（返回清除的
#: 缓存条目数），由**拥有进程内读面缓存的层**（API 端点 shield）在模块
#: 导入时注册；服务层写路径经 :func:`notify_read_view_invalidated` 触发。
#: 依赖方向保持 服务层 → core ← API 层：服务层只认识 domain 名字符串，
#: 不 import API 模块；回调闭包在注册方模块命名空间解析 shield 引用
#: （运行时查找，测试 monkeypatch 替换 shield 实例同样生效）。
_READ_VIEW_INVALIDATION_HOOKS: dict[str, list[Callable[[str], int]]] = {}


def register_read_view_invalidation_hook(domain: str, hook: Callable[[str], int]) -> None:
    """注册 ``domain`` 读面的进程内缓存失效回调（同一回调只挂一次）。"""
    hooks = _READ_VIEW_INVALIDATION_HOOKS.setdefault(domain, [])
    if hook not in hooks:
        hooks.append(hook)


def notify_read_view_invalidated(domain: str, user_id: str) -> int:
    """宣告某用户读面已变化：逐个调用失效回调，返回清除条目总数。

    纯进程内同步操作、零 IO。回调异常只记日志不传播——失效是 best-effort
    读投影，失败最坏退回 TTL 自然过期，绝不阻断写路径（与吸收侧
    「缓存面不可达只降级不回滚」同款纪律）。无注册回调（纯服务层调用方、
    单测未挂 API 路由）时为 no-op，返回 0。
    """
    cleared = 0
    for hook in list(_READ_VIEW_INVALIDATION_HOOKS.get(domain, ())):
        try:
            cleared += hook(user_id) or 0
        except Exception:  # noqa: BLE001 — 失效失败不阻断写路径
            logger.exception("read-view invalidation hook failed (domain=%s, user_id=%s)", domain, user_id)
    return cleared
