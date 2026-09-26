"""V3-FIX-150 红测：Redis 不可用时引擎 lifespan 必须降级启动，而非 UnboundLocalError 启动即崩。

缺陷（wt458 真链探针实锤，登记于 v3/06_agent_fleet/DYNAMIC_ISSUES.md V3-FIX-150）：
``app/main.py`` lifespan 中 ``from app.core.event_bus import event_bus`` 只在
``if cache_service.redis:`` 分支内执行（函数内 import = 局部赋值）；Redis 连接
失败（连不上 / NOAUTH）时 ``cache.init_redis`` 走既有告警路径把 ``redis`` 置
None，该分支整体跳过，名字从未绑定；而后 intervention_outcome_verifier 分支
无条件求值 ``event_bus is not None`` → UnboundLocalError → Application startup
failed，uvicorn 退出码 3。与 V3-FIX-78「全断供快速诚实失败」意图相悖：Redis
单点故障把「降级启动」变成「拒绝启动」。

修后契约：
1. Redis 不可用（连接拒绝 / 认证失败两种形态）时 lifespan 正常进入运行态，
   不抛 UnboundLocalError（真 uvicorn 形态下退出码 0 而非 3，由独立端口真栈
   探针另行验证，见卡片验证记录）；
2. 降级可观测：显式 WARNING 日志声明事件流消费者停用、引擎以进程内 event_bus
   降级运行（publish fail-soft）；
3. 降级态无消费者任务被孵化（app.state 无 *_consumer_task 句柄）。

模拟口径：monkeypatch ``CacheService.init_redis`` / ``ConnectionManager.init_redis``
为「连接失败 → ``self.redis = None``」——与真实失败路径逐位同形（refused / NOAUTH
两种异常都在 init_redis 内被吞、``CacheService.redis`` 显式置 None，见 cache.py /
websocket.py 的 except 分支），不需要真网络，两种形态在进程内收敛到同一终态；
真网络两形态由真栈探针覆盖。DB 段用 sqlite（pytest 标准环境），lifespan 内全部
DB 失败路径本就 fail-soft（非致命）。
"""

from __future__ import annotations

from typing import Any

import pytest
from loguru import logger

pytestmark = pytest.mark.asyncio

_DEGRADED_WARNING_MARKER = "event consumers degraded"


def _capture_warnings() -> tuple[list[Any], Any]:
    """loguru WARNING 级日志捕获（同 test_prodfix1 的 sink 模式）。"""
    records: list[Any] = []
    handler_id = logger.add(records.append, level="WARNING")
    return records, lambda: logger.remove(handler_id)


def _log_text(records: list[Any]) -> str:
    return "\n".join(str(rec) for rec in records)


async def _fail_init_redis_redis_unavailable(self: Any, _failure: str) -> None:
    """镜像真实 init_redis 失败路径的终态：连接异常被吞、self.redis 置 None。"""
    self.redis = None
    logger.warning(f"Redis Cache connection failed (simulated {_failure}): injected by V3-FIX-150 red test")


@pytest.mark.parametrize("failure", ["connection_refused", "noauth"])
async def test_lifespan_degrades_when_redis_unavailable(monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    """Redis 不可用时 lifespan 降级启动：不崩（修前 UnboundLocalError）+ 显式降级警告。"""
    from app.core.cache import CacheService
    from app.core.websocket import ConnectionManager

    async def _cache_fail(self: CacheService) -> None:
        await _fail_init_redis_redis_unavailable(self, failure)

    async def _ws_fail(self: ConnectionManager) -> None:
        self.redis = None
        self.pubsub = None

    monkeypatch.setattr(CacheService, "init_redis", _cache_fail)
    monkeypatch.setattr(ConnectionManager, "init_redis", _ws_fail)

    import app.main as main_module

    records, remove = _capture_warnings()
    try:
        # 修前：UnboundLocalError: cannot access local variable 'event_bus'
        #       where it is not associated with a value → startup failed
        # 修后：正常进入运行态（yield 到 with 体内）
        async with main_module.lifespan(main_module.app):
            assert main_module.cache_service.redis is None, "模拟的 Redis 不可用终态未生效"
    finally:
        remove()

    text = _log_text(records)
    assert "UnboundLocalError" not in text, "lifespan 内出现未绑定局部名异常"
    assert _DEGRADED_WARNING_MARKER in text, "Redis 不可用时缺少显式降级 WARNING（降级必须可观测，不许静默）"

    # 降级态自证：没有任何事件消费者任务被孵化（全部 redis 门控分支被跳过）
    consumer_task_attrs = [
        key for key in vars(main_module.app.state) if key.endswith("_consumer_task") or key.endswith("_consumer")
    ]
    assert consumer_task_attrs == [], f"降级态不应有消费者任务在跑: {consumer_task_attrs}"
