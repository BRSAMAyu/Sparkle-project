"""
Core: infra
Phase: execute
Stage: O-07

O-07 · Celery 队列背压 —— 上限 / 丢弃策略 / 可观测（FIX-49 的队列面治理）。

背景（FIX-49，bed33844）：引擎内推送循环曾绕过 Stage38 杀开关，把
``classify_node_sector_batch`` 等任务持续灌进 glm_batch 队列，专用 worker
消费不动 → 无界回积（API 费用流失 + 内存爬升的总源头之一）。既有
``glm_batch_service.evaluate_dispatch``（E-06 停车道语义）是**调用方自愿
协作**的软门（依赖 caller 传入 celery_status）；本模块是投递 choke point
（``celery_dispatch.dispatch_task_async``）上的**强制硬顶**：即便调用方
不做健康评估，队列深度到上限后投递即被丢弃。

语义（每一条都对齐 O-07 卡面「上限/丢弃策略/可观测」）：
- **上限**：按队列配置深度上限（``QUEUE_BACKPRESSURE_LIMITS_JSON`` 覆盖，
  未覆盖队列用 ``QUEUE_BACKPRESSURE_DEFAULT_MAX_DEPTH``；0/负数 = 显式不限）。
- **丢弃策略**：超限投递**不投递**（不排队、不延迟、不静默）——返回 False
  并记 ``sparkle_queue_backpressure_drops_total{queue}`` + WARNING（含深度/
  上限，可审计）。丢弃是显式结果而非延迟堆积：上游「投递失败」分支本就
  存在（restore-storm 修复后 dispatch 永不抛异常），丢弃与既有失败语义同形。
- **可观测**：每次探测回写 ``sparkle_queue_depth{queue}`` gauge（OBSERVABILITY
  的 queue depth 面板数据源）；探测失败记
  ``sparkle_queue_backpressure_probe_failures_total{queue}``。

有界降级（O-07「Redis 故障不得无界成本」在队列面的推论）：
- 背压探测自身失败（broker 不可达）→ **放行投递**并只记 probe_failures
  计数。这不是 fail-open 漏洞：broker 不可达时紧随其后的 ``send_task``
  必然投递失败（dispatch 超时熔断返回 False），不存在「探测失败但消息
  无界入队」的路径；探测失败放行只为不在 broker 短暂抖动时误丢任务。
- 探测是 off-loop（executor 线程）+ ``wait_for`` 硬超时（复用
  celery_dispatch 的教训：同步 Redis I/O 永不进事件循环线程）。

Redis broker 的队列深度即 ``LLEN <queue_name>``（celery Redis broker 的
存储模型），经 celery 自己的连接池读取，不引入第二个 Redis 客户端配置面。
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from loguru import logger

from app.config import settings
from app.core.metrics import get_or_create_metric
from prometheus_client import Counter, Gauge

#: 队列当前深度（OBSERVABILITY「queue depth/Celery health」面板数据源）。
QUEUE_DEPTH = get_or_create_metric(
    Gauge,
    "sparkle_queue_depth",
    "Current Celery broker queue depth (LLEN) by queue name",
    ["queue"],
)

#: 超限丢弃计数（丢弃策略的可观测面；>alert 时先查该指标定位被灌爆的队列）。
QUEUE_BACKPRESSURE_DROPS_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_queue_backpressure_drops_total",
    "Task dispatches dropped because queue depth exceeded the backpressure cap",
    ["queue"],
)

#: 探测失败计数（有界降级面：broker 不可达时放行但必须留痕）。
QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_queue_backpressure_probe_failures_total",
    "Queue depth probe failures (broker unreachable); dispatch proceeds bounded",
    ["queue"],
)

#: O-07 · queue backpressure 语义版本（行为变更需过 reviewer）。
QUEUE_BACKPRESSURE_VERSION = "queue_backpressure.v1"


@dataclass(frozen=True)
class QueueBackpressureDecision:
    """一次背压判定的只读快照（纯数据，测试/审计可直接断言）。"""

    queue: str
    depth: int | None  # None = 探测失败（broker 不可达等）
    limit: int  # 0/负 = 显式不限
    allowed: bool
    reason: str


def parse_queue_limits(raw: str | None) -> dict[str, int]:
    """解析 ``QUEUE_BACKPRESSURE_LIMITS_JSON``（确定性；垃圾输入 → 空映射）。

    值语义：正整数 = 该队列深度上限；0/负数 = 该队列**显式**不限（运维
    针对性关闭某队列的背压）。非 int 值逐键丢弃，不让一个坏键毒化整表。
    """
    if not raw or not str(raw).strip():
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("queue_backpressure: LIMITS_JSON is not valid JSON; ignoring (raw hidden)")
        return {}
    if not isinstance(parsed, dict):
        logger.warning("queue_backpressure: LIMITS_JSON is not a JSON object; ignoring")
        return {}
    limits: dict[str, int] = {}
    for key, value in parsed.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            logger.warning("queue_backpressure: ignoring non-integer limit for queue {!r}", key)
            continue
        limits[str(key)] = int(value)
    return limits


def get_queue_limit(queue: str) -> int:
    """解析队列的深度上限：按队列覆盖 → 全局默认；≤0 = 显式不限。"""
    overrides = parse_queue_limits(str(getattr(settings, "QUEUE_BACKPRESSURE_LIMITS_JSON", "") or ""))
    if queue in overrides:
        return overrides[queue]
    return int(getattr(settings, "QUEUE_BACKPRESSURE_DEFAULT_MAX_DEPTH", 1000) or 0)


async def _llen_off_loop(queue: str) -> int:
    """在 executor 线程里经 celery 连接池执行 ``LLEN <queue>``（永不冻结事件循环）。"""
    from app.core.celery_app import celery_app

    def _llen() -> int:
        with celery_app.connection_or_acquire() as conn:
            client = conn.default_channel.client
            return int(client.llen(queue))

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _llen)


async def check_queue_backpressure(queue: str) -> QueueBackpressureDecision:
    """投递前背压判定（探测 + 上限裁决 + 指标回写）。

    - 探测成功：回写 ``sparkle_queue_depth``；深度 ≥ 上限 → 不允许（丢弃策略
      由调用方执行：不 send_task、记 drops 指标）。
    - 探测失败：允许（有界降级，见模块注释）+ 记 probe_failures。
    - ``QUEUE_BACKPRESSURE_ENABLED=False`` 或上限 ≤0：不限（显式关闭）。
    """
    queue = str(queue or "")
    if not queue:
        return QueueBackpressureDecision(queue=queue, depth=None, limit=0, allowed=True, reason="no_queue")

    limit = get_queue_limit(queue)
    if not bool(getattr(settings, "QUEUE_BACKPRESSURE_ENABLED", True)) or limit <= 0:
        return QueueBackpressureDecision(queue=queue, depth=None, limit=limit, allowed=True, reason="disabled")

    timeout = float(getattr(settings, "QUEUE_BACKPRESSURE_PROBE_TIMEOUT_SECONDS", 1.5) or 1.5)
    try:
        depth = await asyncio.wait_for(_llen_off_loop(queue), timeout=timeout)
    except Exception as exc:  # noqa: BLE001 — 有界降级：探测失败放行（broker 挂则 send_task 必失败）
        QUEUE_BACKPRESSURE_PROBE_FAILURES_TOTAL.labels(queue=queue).inc()
        logger.warning(
            "[QueueBackpressure] depth probe failed queue={} timeout={}s -> allow (bounded: broker down fails send_task anyway): {!r}",
            queue,
            timeout,
            exc,
        )
        return QueueBackpressureDecision(queue=queue, depth=None, limit=limit, allowed=True, reason="probe_failed")

    QUEUE_DEPTH.labels(queue=queue).set(depth)
    if depth >= limit:
        return QueueBackpressureDecision(
            queue=queue,
            depth=depth,
            limit=limit,
            allowed=False,
            reason=f"queue_depth={depth}>=cap={limit}",
        )
    return QueueBackpressureDecision(queue=queue, depth=depth, limit=limit, allowed=True, reason="within_cap")


async def enforce_queue_backpressure(queue: str) -> bool:
    """判定 + 丢弃记账（超限记 drops 指标 + WARNING）。返回是否允许投递。"""
    decision = await check_queue_backpressure(queue)
    if decision.allowed:
        return True
    QUEUE_BACKPRESSURE_DROPS_TOTAL.labels(queue=decision.queue).inc()
    logger.warning(
        "[QueueBackpressure] drop dispatch queue={} depth={} cap={} ({}); "
        "task NOT enqueued (bounded backlog policy)",
        decision.queue,
        decision.depth,
        decision.limit,
        decision.reason,
    )
    return False
