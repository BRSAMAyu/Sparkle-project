"""MiniMax 账户级 RPM 预算闸（跨进程共享，DIST-SEMAPHORE）。

依据：
- v3-output/MINIMAX-QUOTA/REPORT.md：MiniMax 官方按**账户**（主+子账号共享）限
  RPM/TPM——免费 20 RPM / 1M TPM，充值 200 RPM / 10M TPM，无文档化并发数。
  RPM 才是账户级硬约束；本地并发池只是进程内自保护阀。
- v3-output/BATCH-CAP/REPORT.md 裁决 6/7：三进程（引擎 + glm_batch worker 容器内
  2 个 prefork 子进程）各持本地 asyncio 池时，RPM 预算无全局面；分布式收敛需
  Redis，超 BATCH-CAP 卡面——本模块兑现该登记。

设计（答 BATCH-CAP 步骤 3「Redis 分布式信号量」登记，粒度按官方 RPM 口径而非并发）：
- **固定窗口计数器**：60s 窗口一个 Redis key，``INCR`` 占预算、``EXPIRE`` 自愈。
  桶容量 = ``MINIMAX_RPM_BUDGET``（每分钟发起数），窗口滚动即 refill——与官方
  「每分钟每账户 N 发起」同构。选固定窗口而非并发信号量，因为官方计的是
  *发起* 而非 *在途*：请求一旦向 API 发起，配额已被消费、无可释放语义。
- **TTL 防死锁**：无「持有者」故无信号量死锁面——崩溃进程不可能悬空占预算
  （消费即花费）；窗口 key 带 2×窗口长度的 TTL，即使 INCR 与 EXPIRE 之间进程
  崩溃（MULTI/EXEC 内已原子化，此窗口理论不存在），任何后续一次 acquire 也会
  重新武装 TTL，状态永不永久楔死。
- **原子性**：INCR+EXPIRE 走事务 pipeline（MULTI/EXEC，不依赖 Lua——fakeredis
  测试基建无 lupa 也可复验）。超预算方先 INCR 再 DECR 回滚：竞态下最坏
  「保守误拒」（永不超发），对保护性预算是诚实方向。
- **诚实降级**：Redis 缺席/出错 → 放行（回退本地池第二道防线）+ 限频告警，
  不阻断业务；恢复后自动回到分布式预算。
- **超时语义对齐 BATCH-CAP**：等预算超时抛非空 TimeoutError（含 budget/窗口
  用量快照），消费端照既有 fallback 链归类 TIMEOUT（可重试）。
"""

from __future__ import annotations

import asyncio
import time

from loguru import logger

from app.config import settings
from app.core.cache import cache_service

_WINDOW_SECONDS = 60.0
_KEY_PREFIX = "sparkle:llm:minimax:rpm"
_POLL_CAP_SECONDS = 1.0
_DEGRADE_WARN_COOLDOWN_SECONDS = 300.0


class MinimaxRpmGate:
    """跨进程 MiniMax 每分钟发起预算闸（Redis 固定窗口）。

    直接以 ``(budget, redis_client_supplier)`` 参数化以便单测注入多实例模拟
    多进程；生产经 :func:`get_minimax_rpm_gate` 单例使用。
    """

    def __init__(
        self,
        budget: int,
        *,
        key_prefix: str = _KEY_PREFIX,
        window_seconds: float = _WINDOW_SECONDS,
        redis_getter=None,
    ):
        if budget <= 0:
            raise ValueError(f"MinimaxRpmGate budget must be > 0, got {budget}")
        self.budget = int(budget)
        self.key_prefix = key_prefix
        self.window_seconds = float(window_seconds)
        # 默认经 cache_service 取连接（生产）；可注入 supplier 供单测模拟
        # 独立连接（多"进程"共享同一 Redis 存储的真竞争语义）。
        self._redis_getter = redis_getter or (lambda: cache_service.redis)
        # 轻量观测（供测试与运维）
        self.total_acquired = 0
        self.total_rejected_timeout = 0
        self.total_degraded = 0
        self._last_degrade_warn_at = 0.0

    # ------------------------------------------------------------------
    # 预算获取
    # ------------------------------------------------------------------

    async def acquire(self, timeout: float) -> None:
        """取得 1 个「本分钟发起」配额；等不到则抛带快照的 TimeoutError。

        - Redis 缺席/出错：诚实降级（放行，交本地并发池把关）+ 限频告警；
        - 窗口满：等待至窗口滚动或 timeout 到点（先到者胜）。
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(0.0, timeout)
        snapshot = ""
        while True:
            redis_client = self._redis_getter()
            if redis_client is None:
                self._warn_degraded("redis absent (no client available)")
                return
            try:
                acquired, retry_after, snapshot = await self._try_take(redis_client)
            except Exception as exc:  # redis 异常族（连接/命令错误）均诚实降级
                self._warn_degraded(f"redis error: {type(exc).__name__}: {exc}")
                return
            if acquired:
                self.total_acquired += 1
                return
            remaining = deadline - loop.time()
            if remaining <= 0:
                self.total_rejected_timeout += 1
                raise TimeoutError(self._timeout_message(timeout, snapshot))
            # 睡到窗口滚动（retry_after）与剩余预算（remaining）的较小值，
            # 再设轮询上限——醒来重读窗口，天然适应跨窗口。
            await asyncio.sleep(max(0.01, min(retry_after + 0.05, remaining, _POLL_CAP_SECONDS)))

    async def _try_take(self, redis_client) -> tuple[bool, float, str]:
        """原子尝试占 1 个预算。返回 (是否取得, 建议重试等待秒数, 窗口快照)。"""
        now = time.time()
        window = int(now // self.window_seconds)
        key = f"{self.key_prefix}:{window}"
        # 事务 pipeline（MULTI/EXEC）保证 INCR 与 EXPIRE 同生共死——不依赖
        # Lua；即使整条未落（进程在 EXEC 前崩溃），下次 acquire 的 INCR 也
        # 会重新武装 EXPIRE，状态可自愈（TTL 防死锁）。
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, int(self.window_seconds * 2))
            results = await pipe.execute()
        count = int(results[0])
        if count > self.budget:
            # 回滚自己的一次 INCR：不占而退，窗口余量还给其他进程。
            # 竞态下可能保守误拒（他进程正持膨胀计数），永不超发。
            await redis_client.decr(key)
            retry_after = (window + 1) * self.window_seconds - now
            used = min(count - 1, self.budget)
            return False, retry_after, f"budget={self.budget}/min, window_used>={used}, window={window}"
        return True, 0.0, f"budget={self.budget}/min, window_used={count}, window={window}"

    def _timeout_message(self, timeout: float, snapshot: str) -> str:
        """等预算超时的诊断消息（非空 + 快照，对齐 BATCH-CAP 空消息修复）。"""
        return (
            f"MiniMax account RPM budget exhausted: no request slot within "
            f"{timeout}s ({snapshot or f'budget={self.budget}/min'}). Please try again later."
        )

    # ------------------------------------------------------------------
    # 诚实降级
    # ------------------------------------------------------------------

    def _warn_degraded(self, reason: str) -> None:
        """降级放行 + 限频告警（冷却窗口内只告警一次，避免多进程日志风暴）。"""
        self.total_degraded += 1
        now = time.time()
        if now - self._last_degrade_warn_at >= _DEGRADE_WARN_COOLDOWN_SECONDS:
            self._last_degrade_warn_at = now
            logger.warning(
                f"[MinimaxRpmGate] Distributed RPM budget unavailable ({reason}); "
                f"falling back to local concurrency pool only. "
                f"(budget={self.budget}/min NOT enforced across processes)"
            )

    # ------------------------------------------------------------------
    # 观测
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, int | float]:
        return {
            "budget_per_minute": self.budget,
            "window_seconds": self.window_seconds,
            "total_acquired": self.total_acquired,
            "total_rejected_timeout": self.total_rejected_timeout,
            "total_degraded": self.total_degraded,
        }


_singleton: MinimaxRpmGate | None = None


def get_minimax_rpm_gate() -> MinimaxRpmGate | None:
    """按 settings 返回生产单例；``MINIMAX_RPM_BUDGET <= 0``（默认）→ None。

    None = 禁用（回滚位，与 BATCH-CAP 的 env 路径兼容：仅本地池，行为与
    DIST-SEMAPHORE 之前完全一致）。启用判读在每次 acquire 时进行，
    env 改值 + 重启即可生效/回滚。
    """
    global _singleton
    budget = int(getattr(settings, "MINIMAX_RPM_BUDGET", 0) or 0)
    if budget <= 0:
        return None
    if _singleton is None or _singleton.budget != budget:
        _singleton = MinimaxRpmGate(budget)
    return _singleton
