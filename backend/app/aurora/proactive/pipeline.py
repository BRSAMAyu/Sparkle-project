"""
Aurora proactive pipeline — event → filter → Aurora (P-01).

把主动式触达做成 **event → deterministic filter → Aurora 出口** 的事件驱动
管线（PROACTIVE_SYSTEM.md §2），替代"定时轮询 + 问 LLM"反模式：

    EventBus(sparkle_events) → classify_event → evaluate_suppression
      → ProactiveDecisionRecord → metrics + shadow/live 出口

核心性质：
- **零 LLM**：全管线（分类、抑制、记录、投递）没有任何模型调用；本模块
  不 import 任何 LLM 客户端，测试以 mock 计数器断言调用数 = 0。
- **shadow 默认**：``shadow=True``（settings 兜底）时全链路照跑，但
  would-notify 只记录（metrics 计数 + 有界 ``recent_records`` + 可注入
  sink），不触发任何真实出口。
- **Aurora 出口复用既有通道**：live 模式经 ``SystemUpdateService.enqueue``
  （journey consumers 同款系统更新通道）投递，不重建通知通道；投递适配器
  可注入（测试用记录器）。
- **消费者组复用 EventBus 既有订阅机制**（idempotency / DLQ / retry 全部
  继承），group 名 ``aurora_proactive_pipeline``，回调永不抛出。
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Mapping

from loguru import logger

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.metrics import PROACTIVE_PIPELINE_DECISIONS_TOTAL
from app.aurora.proactive.state import SHADOW_SCOPE, LIVE_SCOPE, ProactiveSuppressionStore
from app.aurora.proactive.suppression import SuppressionSnapshot, evaluate_suppression
from app.aurora.proactive.triggers import TriggerClassification, classify_event

if TYPE_CHECKING:  # 仅类型标注；运行期鸭子类型，保持本模块轻量可导入。
    from app.core.event_bus import EventBus

__all__ = [
    "ProactiveDecisionRecord",
    "ProactiveEventPipeline",
    "DecisionSink",
]

DecisionSink = Callable[["ProactiveDecisionRecord"], Awaitable[None]]
DeliveryFn = Callable[[str, TriggerClassification, str], Awaitable[bool]]


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True, slots=True)
class ProactiveDecisionRecord:
    """一条事件走完管线的最终决定（shadow 审计的最小完整单元）。"""

    event_name: str
    trigger: str | None  # 白名单外被忽略的事件为 None
    user_id: str
    #: "notify"（allowed 且已按模式处理）| "suppressed" | "ignored"
    decision: str
    #: 抑制原因（suppressed 时与 SUPPRESSION_STEPS 同名）；其余为 None/""。
    reason: str | None
    step: str | None
    subject_key: str = ""
    shadow: bool = True
    occurred_at: str = ""
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_name": self.event_name,
            "trigger": self.trigger,
            "user_id": self.user_id,
            "decision": self.decision,
            "reason": self.reason,
            "step": self.step,
            "subject_key": self.subject_key,
            "shadow": self.shadow,
            "occurred_at": self.occurred_at,
            "details": dict(self.details),
        }


class ProactiveEventPipeline:
    """主动式事件管线（确定性触发 + 确定性抑制 + 可审 shadow）。"""

    STREAM_NAME = "sparkle_events"
    GROUP_NAME = "aurora_proactive_pipeline"
    CONSUMER_NAME_PREFIX = "aurora-proactive"
    #: shadow 审计环形缓冲上限（防无界增长；指标才是聚合真源）。
    MAX_RECENT_RECORDS = 1000

    def __init__(
        self,
        *,
        store: ProactiveSuppressionStore | None = None,
        redis: Any = None,
        shadow: bool | None = None,
        sink: DecisionSink | None = None,
        deliver: DeliveryFn | None = None,
    ) -> None:
        self.store = store or ProactiveSuppressionStore(redis)
        # shadow 缺省读管线旋钮（env 可覆写），默认开。
        self.shadow = (
            bool(proactive_config.PROACTIVE_PIPELINE_SHADOW) if shadow is None else bool(shadow)
        )
        self._sink = sink
        self._deliver = deliver or self._default_deliver
        self.recent_records: deque[ProactiveDecisionRecord] = deque(maxlen=self.MAX_RECENT_RECORDS)

    # -- pipeline ---------------------------------------------------------

    async def handle_event(self, event: Mapping[str, Any]) -> ProactiveDecisionRecord | None:
        """处理一条事件；白名单外返回 None，否则返回完整决定记录。永不抛出。"""
        occurred_at = _utcnow()
        event_name = str(event.get("event_type") or "").strip()
        classification = classify_event(event, now=occurred_at)
        if classification is None:
            # 非白名单 / 非触发形状：静默忽略（debug 级，避免刷屏）。
            logger.debug("proactive pipeline ignored event_type={!r}", event_name)
            return None

        user_id = str(event.get("user_id") or "").strip()
        if not user_id:
            # 事件没有 user_id 无法做 per-user 抑制与触达：按 ignored 记录，
            # 不消费计数（与 journey consumers 的丢弃语义一致）。
            record = ProactiveDecisionRecord(
                event_name=event_name,
                trigger=str(classification.trigger.value),
                user_id="",
                decision="ignored",
                reason="missing_user_id",
                step=None,
                shadow=True,
                occurred_at=occurred_at.isoformat(),
            )
            await self._record(record)
            return record

        scope = SHADOW_SCOPE if self.shadow else LIVE_SCOPE
        try:
            snapshot = await self.store.build_snapshot(user_id, scope=scope, now=occurred_at)
        except Exception as exc:  # 快照构建失败（store 故障/redis 未配置）：fail-closed
            # R2 P1-1：宁可少发不可误发——置 state_unavailable 总闸，抑制链
            # 直接全抑制（reason=state_unavailable），绝不以零计数快照放行。
            logger.warning("proactive snapshot unavailable, fail-closed user={}: {!r}", user_id, exc)
            snapshot = SuppressionSnapshot(now=occurred_at, state_unavailable=True)

        decision = evaluate_suppression(
            trigger=classification.trigger,
            subject_key=classification.subject_key,
            snapshot=snapshot,
        )

        if not decision.allowed:
            record = ProactiveDecisionRecord(
                event_name=event_name,
                trigger=str(classification.trigger.value),
                user_id=user_id,
                decision="suppressed",
                reason=decision.reason,
                step=decision.step,
                subject_key=classification.subject_key,
                shadow=self.shadow,
                occurred_at=occurred_at.isoformat(),
                details=dict(decision.details),
            )
            await self._record(record)
            return record

        # ---- allowed：状态消费与出口处理（被抑制的事件绝不走到这里）----
        # cap/cooldown/novelty 只被"真发/would-notify"消耗。
        try:
            await self.store.record_notification(
                user_id,
                trigger=str(classification.trigger.value),
                subject_key=classification.subject_key,
                scope=scope,
                now=occurred_at,
            )
        except Exception as exc:
            logger.warning("proactive state write failed user={}: {!r}", user_id, exc)

        details: dict[str, Any] = {"correlation": dict(classification.correlation)}
        if self.shadow:
            logger.info(
                "proactive would-notify user={} trigger={} event={} (shadow)",
                user_id,
                str(classification.trigger.value),
                event_name,
            )
        else:
            delivered = False
            try:
                delivered = await self._deliver(user_id, classification, event_name)
            except Exception as exc:
                logger.warning("proactive delivery failed user={}: {!r}", user_id, exc)
            details["delivered"] = delivered

        record = ProactiveDecisionRecord(
            event_name=event_name,
            trigger=str(classification.trigger.value),
            user_id=user_id,
            decision="notify",
            reason=None,
            step=None,
            subject_key=classification.subject_key,
            shadow=self.shadow,
            occurred_at=occurred_at.isoformat(),
            details=details,
        )
        await self._record(record)
        return record

    # -- wiring -----------------------------------------------------------

    async def attach(self, event_bus: "EventBus") -> None:
        """以既有消费者组机制订阅 sparkle_events（idempotency/DLQ 继承）。"""
        await event_bus.subscribe(
            stream=self.STREAM_NAME,
            group_name=self.GROUP_NAME,
            consumer_name=f"{self.CONSUMER_NAME_PREFIX}-{id(self):x}",
            callback=self._on_bus_event,
        )

    async def _on_bus_event(self, payload: dict) -> None:
        try:
            await self.handle_event(payload)
        except Exception as exc:  # 双保险：消费回调永不抛出（失败走 DLQ 语义）
            logger.error("proactive pipeline crashed on event: {!r}", exc)

    # -- outlets ----------------------------------------------------------

    async def _record(self, record: ProactiveDecisionRecord) -> None:
        """决定落审计面：Prometheus 计数 + 有界环形缓冲 + 可注入 sink。"""
        PROACTIVE_PIPELINE_DECISIONS_TOTAL.labels(
            trigger=record.trigger or "none",
            event_name=record.event_name or "unknown",
            decision=record.decision,
            reason=record.reason or "none",
        ).inc()
        self.recent_records.append(record)
        if self._sink is not None:
            try:
                await self._sink(record)
            except Exception as exc:
                logger.warning("proactive decision sink failed: {!r}", exc)

    @staticmethod
    async def _default_deliver(user_id: str, classification: TriggerClassification, event_name: str) -> bool:
        """live 出口：既有 Aurora/system-update 通道（journey consumers 同款）。"""
        from app.services.system_update_service import build_system_update, SystemUpdateService

        from app.core.cache import cache_service

        trigger_name = str(classification.trigger.value)
        title = {
            "deadline": "临近的截止时间",
            "overdue": "有一项任务已过期",
            "slot_missed": "刚才的学习时段错过了",
            "user_active": "继续刚才的进度",
            "upstream_completed": "上游任务完成了",
            "goal_stalled": "目标进度需要看一下",
            "run_awaiting": "有一个执行在等你确认",
        }.get(trigger_name, "有一条新消息")
        payload = build_system_update(
            update_type=f"proactive_{trigger_name}",
            category="aurora",
            title=f"Aurora：{title}",
            description="由事件触发的主动式提醒（确定性抑制链已通过）。",
            priority="medium",
            metadata={
                "pipeline": "proactive_v1",
                "trigger": trigger_name,
                "event_name": event_name,
                "subject_key": classification.subject_key,
                "correlation": dict(classification.correlation),
            },
        )
        return await SystemUpdateService(cache_service.redis).enqueue(user_id, payload)
