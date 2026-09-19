"""X-05 · Run 投影消费者 —— EXECUTION_STATUS_CHANGED → agent_runs 状态脊柱.

消费 ``sparkle_events`` 流上的 ``execution.status_changed``（ExecutionService
``_publish_status_event`` 单一漏斗，14 个调用点全覆盖），把 ExecutionIntent 的
执行器协议状态投影为用户可见 run 状态（映射见
``app/core/run_state_machine.INTENT_STATUS_TO_RUN_STATUS``）。

X-05B · EXECUTING 执行面接线：同组加消费 ``run.status_changed``（execution
轨道步进里程碑，producer = ``execution_run_producer.publish_execution_step_event``，
零新事件名——D-01 冻结词表既有名），投影 EXECUTING 可见步进（状态落点 +
steps_done/current_stage 进度）到 run 脊柱（``project_execution_step``）。

架构定位（X-05 RUNTIME_MAP §5）：
- **零侵入**：execution_service 状态漏斗一行不改（步进 producer 是独立钩子
  函数，X-05B 只加调用点）；投影经既有 event_bus（Redis Streams
  consumer group，pending 条目在组存续期间不丢）；
- **幂等**：project_intent_status 内部 FOR UPDATE+复查（重复投递 no-op），
  run 创建按 ``intent:{id}:attempt:{n}`` 确定性幂等键恰一次；终态事件重投
  由幻影守卫收敛（R2 F1）；步进事件同 intent+attempt+step 重投恰一次
  （transition 复查 + record_step 序号单调，X-05B）；
- **可修复**：投影滞后/丢失由 ``AgentRunService.recover_stale_runs`` 的
  intent 漂移修复兜底（QUEUED 分支同样覆盖，R2 F3）；
- **失败不丢**：投影异常向上抛给 bus（有界重试 → DLQ + metric + DB 落档），
  不在消费者层吞掉（R2 F9）。

启动接线：``app/main.py`` lifespan（与 ExecutionEventConsumer 同款，
``cache_service.redis`` 存在才启）。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from loguru import logger

from app.core.event_bus import EventBus
from app.core.event_types import EXECUTION_STATUS_CHANGED
from app.core.run_state_machine import RunEventName
from app.db.session import AsyncSessionLocal
from app.services.agent_run_service import AgentRunService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class RunProjectionConsumer:
    """execution 轨道 → run 脊柱的状态投影器（at-least-once 投递 + 幂等投影）。"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "run_projection_consumer"

    def __init__(self, event_bus: EventBus, session_factory=None):
        self.event_bus = event_bus
        # 会话工厂可注入（测试注入 sqlite 会话；生产缺省引擎会话）。
        self._session_factory = session_factory or AsyncSessionLocal
        self._running = False

    async def start(self) -> None:
        await self.event_bus.connect()
        self._running = True
        logger.info("RunProjectionConsumer started, listening on {}", self.STREAM_NAME)

        while self._running:
            try:
                await self.event_bus.subscribe(
                    stream=self.STREAM_NAME,
                    group_name=self.GROUP_NAME,
                    consumer_name=f"run-projection-{_utcnow().timestamp()}",
                    callback=self.handle_event,
                )
                break
            except Exception as exc:
                logger.error("RunProjectionConsumer error: {}", exc)
                await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False

    async def handle_event(self, event: dict) -> None:
        """bus 回调（每条消息一次）。

        错误契约（R2 F3/F9 返修）：**不吞投影失败**——callback 抛出时
        ``EventBus._process_stream_message`` 走既有的有界重试 → DLQ（Redis 流 +
        ``event_bus_dlq`` DB 落档 + ``EVENT_BUS_CONSUMER_FAILURE_TOTAL``/
        ``EVENT_BUS_DLQ_TOTAL`` metric）管线。此前这里捕获一切异常仅打日志，
        会把非法迁移/瞬时 DB 抖动变成"ack 即永久丢事件"，且绕过全部可观测性。

        仅两类情况静默跳过（不 raise）：非目标事件类型、payload 缺关键键
        （无投影信息，重试无意义）。
        """
        event_type = str(event.get("event_type") or "").strip()
        if event_type == EXECUTION_STATUS_CHANGED:
            await self.project_event(event)
        elif event_type == RunEventName.STATUS_CHANGED.value:
            await self.project_step_event(event)
        return

    async def project_event(self, event: dict) -> None:
        intent_id = str(event.get("execution_intent_id") or "").strip()
        user_id = str(event.get("user_id") or "").strip()
        new_status = str(event.get("new_status") or "").strip()
        if not intent_id or not user_id or not new_status:
            logger.debug("run projection skipped: malformed event keys {}", sorted(event.keys()))
            return

        task_id_raw = str(event.get("task_id") or "").strip()
        task_id: UUID | None = None
        if task_id_raw:
            try:
                task_id = UUID(task_id_raw)
            except ValueError:
                task_id = None

        async with self._session_factory() as db:
            service = AgentRunService(db)
            result = await service.project_intent_status(
                intent_id=UUID(intent_id),
                user_id=UUID(user_id),
                new_status=new_status,
                task_id=task_id,
            )
        if result is None:
            logger.debug(
                "run projection no-op intent_id={} status={}",
                intent_id,
                new_status,
            )
        else:
            logger.info(
                "run projection applied intent_id={} run_id={} created={} status={}",
                intent_id,
                result.run.id,
                result.created,
                result.run.status.value if result.run.status else None,
            )

    async def project_step_event(self, event: dict) -> None:
        """X-05B · execution 步进里程碑（``run.status_changed``）→ run 投影。

        payload 扩展字段（producer 见 ``execution_run_producer``）：
        ``execution_intent_id`` / ``user_id`` / ``task_id`` / ``milestone`` /
        ``run{to_status, step{ordinal, stage, steps_total}}``。缺关键键静默
        跳过（与状态漏斗同契约）；有 ``run`` 块但 ``to_status`` 非法 → 抛
        RunStateError（毒事件走 DLQ，与未映射 intent 状态同待遇）。
        """
        intent_id = str(event.get("execution_intent_id") or "").strip()
        user_id = str(event.get("user_id") or "").strip()
        if not intent_id or not user_id:
            logger.debug("run step projection skipped: malformed event keys {}", sorted(event.keys()))
            return

        run_block = event.get("run")
        if not isinstance(run_block, dict):
            run_block = {}
        step_block = run_block.get("step")
        if not isinstance(step_block, dict):
            step_block = {}

        to_status = str(run_block.get("to_status") or "").strip() or None
        ordinal_raw = step_block.get("ordinal")
        ordinal = int(ordinal_raw) if ordinal_raw is not None else None
        stage = str(step_block.get("stage") or "").strip() or None
        steps_total_raw = step_block.get("steps_total")
        steps_total = int(steps_total_raw) if steps_total_raw is not None else None
        milestone = str(event.get("milestone") or "").strip() or None

        if to_status is None and ordinal is None:
            logger.debug("run step projection skipped: no to_status/step in event keys {}", sorted(event.keys()))
            return

        task_id_raw = str(event.get("task_id") or "").strip()
        task_id: UUID | None = None
        if task_id_raw:
            try:
                task_id = UUID(task_id_raw)
            except ValueError:
                task_id = None

        async with self._session_factory() as db:
            service = AgentRunService(db)
            result = await service.project_execution_step(
                intent_id=UUID(intent_id),
                user_id=UUID(user_id),
                task_id=task_id,
                milestone=milestone,
                to_status=to_status,
                ordinal=ordinal,
                stage=stage,
                steps_total=steps_total,
            )
        if result is None:
            logger.debug("run step projection no-op intent_id={} milestone={}", intent_id, milestone)
        else:
            logger.info(
                "run step projection applied intent_id={} run_id={} milestone={} steps_done={}",
                intent_id,
                result.run.id,
                milestone,
                result.run.steps_done,
            )
