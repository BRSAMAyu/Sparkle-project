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
from app.aurora.proactive.relevance import (
    RELEVANCE_STEP,
    ProactiveRelevanceContextUnavailable,
    ProactiveRelevanceStore,
    RelevanceContext,
    RelevanceDecision,
    derive_information_digest,
    derive_information_onset,
    evaluate_relevance,
)
from app.aurora.proactive.state import LIVE_SCOPE, SHADOW_SCOPE, ProactiveSuppressionStore
from app.aurora.proactive.suppression import SuppressionSnapshot, evaluate_suppression
from app.aurora.proactive.triggers import ProactiveTrigger, TriggerClassification, classify_event

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
    #: "notify"（allowed 且已按模式处理）| "suppressed" | "no_action"（P-02
    #: 相关性语义面判定不打扰）| "ignored"
    decision: str
    #: 抑制原因（suppressed 时与 SUPPRESSION_STEPS 同名）；no_action 时与
    #: RELEVANCE_REASONS 同名；其余为 None/""。
    reason: str | None
    #: 命中的判定步骤名（suppressed=抑制器名；no_action 恒为 "relevance"）。
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
        relevance_store: ProactiveRelevanceStore | None = None,
    ) -> None:
        self.store = store or ProactiveSuppressionStore(redis)
        # P-02 相关性上下文存取：默认与抑制状态共用同一 redis 客户端。
        self.relevance_store = relevance_store or ProactiveRelevanceStore(redis)
        # shadow 缺省读管线旋钮（env 可覆写），默认开。
        self.shadow = bool(proactive_config.PROACTIVE_PIPELINE_SHADOW) if shadow is None else bool(shadow)
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

        # ---- P-02 相关性决策层（内容语义面：频控面之后、状态消费与出口之前；
        # no_action 事件不消耗 cap/cooldown/novelty，也永不到达出口与授权门）----
        try:
            relevance_context = await self._build_relevance_context(classification, event, scope=scope, now=occurred_at)
        except ProactiveRelevanceContextUnavailable as exc:
            # fail-closed（与 state_unavailable 同源哲学）：上下文读不到 →
            # 宁可漏报不可误报，不打扰。
            logger.warning("proactive relevance unavailable, fail-closed user={}: {!r}", user_id, exc)
            relevance = RelevanceDecision(False, "context_unavailable", {"scope": scope})
        else:
            relevance = evaluate_relevance(trigger=classification.trigger, context=relevance_context)

        if relevance.suppressed:
            record = ProactiveDecisionRecord(
                event_name=event_name,
                trigger=str(classification.trigger.value),
                user_id=user_id,
                decision="no_action",
                reason=relevance.reason,
                step=RELEVANCE_STEP,
                subject_key=classification.subject_key,
                shadow=self.shadow,
                occurred_at=occurred_at.isoformat(),
                details=dict(relevance.details),
            )
            await self._record(record)
            return record

        # ---- allowed：状态消费与出口处理（被抑制/无相关性的事件绝不走到这里）----
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

        # P-02：提醒摘要落账（duplicate/no_new_information 判定的记忆来源；
        # best-effort，失败只告警，决定已落不阻断事件流）。
        if relevance_context.current_digest:
            try:
                await self.relevance_store.record_reminder(
                    user_id,
                    classification.subject_key,
                    digest=relevance_context.current_digest,
                    at=occurred_at,
                    scope=scope,
                )
            except Exception as exc:
                logger.warning("proactive relevance write failed user={}: {!r}", user_id, exc)

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

    # -- relevance context（P-02）------------------------------------------

    @staticmethod
    def _parse_event_time(event: Mapping[str, Any]) -> datetime | None:
        """解析事件载荷的 ``timestamp``（naive-UTC）；缺失/坏值返回 None。"""
        raw = event.get("timestamp")
        if isinstance(raw, datetime):
            return raw if raw.tzinfo is None else raw.astimezone(UTC).replace(tzinfo=None)
        text = str(raw).strip() if raw is not None else ""
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(UTC).replace(tzinfo=None)
        return parsed

    async def _build_relevance_context(
        self,
        classification: TriggerClassification,
        event: Mapping[str, Any],
        *,
        scope: str,
        now: datetime,
    ) -> RelevanceContext:
        """组装相关性判定上下文：存储里的用户近况 + 载荷确定性派生。

        - 摘要/起点：:func:`derive_information_digest` /
          :func:`derive_information_onset`（同一输入永远同一输出）。
        - USER_ACTIVE：事件本身就是用户对该 subject 的动作 → 交互时刻取
          max(事件时间戳, 存储记录)（确定性，不依赖外部写入）。
        - has_actionable_step：默认 True（act 侧默认）；仅当载荷显式声明
          ``actionable=False`` 才判非行动（正向证据原则）。
        """
        trigger = classification.trigger
        subject_key = classification.subject_key
        context = await self.relevance_store.build_context(
            str(event.get("user_id") or ""), subject_key, scope=scope, now=now
        )

        interaction = context.subject_last_interaction_at
        if trigger is ProactiveTrigger.USER_ACTIVE:
            event_at = self._parse_event_time(event) or now
            if interaction is None or event_at > interaction:
                interaction = event_at

        actionable = event.get("actionable")
        return RelevanceContext(
            subject_last_viewed_at=context.subject_last_viewed_at,
            subject_last_interaction_at=interaction,
            last_reminder_at=context.last_reminder_at,
            last_reminder_digest=context.last_reminder_digest,
            current_digest=derive_information_digest(trigger, subject_key, event),
            subject_state_changed_at=derive_information_onset(trigger, event, now=now),
            has_actionable_step=actionable is not False,
        )

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
        from app.core.cache import cache_service
        from app.services.system_update_service import SystemUpdateService, build_system_update

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
