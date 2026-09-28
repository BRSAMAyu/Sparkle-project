"""
Aurora proactive — unified user budget gate for nudges/spine channels (V4-P01).

**一条用户预算，两个渠道**（卡面：将当前 nudges/spine 渠道归到同一用户预算，
触发基于合法事件/作用范围/quietHours；只在有具体帮助时出现）。

V4 之前主动面是两族（S16 §P.0-2 结构事实）：

- **nudge 渠道**（``comeback_nudge_task``）：过 P-03 类型级抑制 + P-06
  负担闸门（quiet/cap）+ 重复窗；
- **spine 渠道**（``recall_notification_task``）：只有自身 Redis 冷却，
  **不过 quiet hours、不占共享日预算、不认另一渠道的拒绝**。

本模块是**组合层，不是第二权威**：预算面只消费既有真源——

1. P-03 :class:`~app.services.proactive_suggestion_service.
   ProactiveSuggestionFeedbackService` 的类型级抑制（既有）与 subject 级
   抑制（本卡扩展，同一 explicit JSONB 命名空间）——用户在任一渠道
   拒绝/静音后，其他渠道不得就同一 subject 补发（验收①）；
2. 过期计划 subject 只允许经 nudge 渠道已校准的 rescope 流呈现（J-07），
   spine 渠道不得再就过期计划补发 recall（验收①「过期计划」半句）；
3. P-06 :class:`~app.aurora.runtime_v1.notification_settings.
   NotificationSettingsResolver` ``evaluate_burden``——quiet hours + 用户
   本地日预算（真实 Notification 行计数），两渠道同一份（验收③预算面）；
4. 同一 ``prompt_key`` 的 effect 去重窗——同一提示多端/多 tick 只消费一次
   预算（验收③「一次 effect」）；

回归/回来（comeback）在闸门眼里与任何其他触发完全同级：**没有任何
「用户刚回来所以必须打扰」的豁免路径**（验收②），且本模块对情绪推断面
（``CognitiveFragment.sentiment`` / emotion_hint）零写入——回归是中性事件。

预算与因果留痕（验收③「可追」）：允许的提示由调用方把
:func:`build_budget_envelope` 的产出盖进 ``Notification.data
["proactive_budget"]``——预算消耗（count/cap）与触发因果（channel/type/
subject/prompt_key）与账本行同源共存；被抑制的决定落 Prometheus 计数
（有界 label，无用户维度）。

硬约束（继承 P-01/WT378 纪律）：
- 零 LLM、确定性、失败 fail-closed（设置读不到 → 抑制而非放行）；
- 旋钮 ``PROACTIVE_UNIFIED_BUDGET_ENABLED``（默认开，off = passthrough
  回滚开关，恢复各渠道既有行为）；
- 测试经 monkeypatch 覆盖本配置模块属性（pydantic Settings 禁未知字段，
  与 P-01 旋钮同款），新旋钮同步进测试复位 fixture。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Mapping
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.proactive import config as proactive_config
from app.aurora.proactive.metrics import get_or_create_budget_counter
from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

__all__ = [
    "ProactiveChannel",
    "ProactiveBudgetRequest",
    "ProactiveBudgetDecision",
    "UnifiedProactiveBudgetService",
    "derive_prompt_key",
    "subject_refs_from_payload",
    "build_budget_envelope",
    "record_cross_channel_suppression",
    "BUDGET_DECISION_REASONS",
]


class ProactiveChannel(StrEnum):
    """主动面两渠道（封闭集；metrics label 有界）。"""

    NUDGE = "nudge"  # comeback_nudge_task（nudge 家族）
    SPINE = "spine"  # recall_notification_task（spine recall 渠道）


#: spine 渠道不得补发过期计划 subject（nudge 渠道的过期计划语义归 J-07
#: rescope 流，本闸门不改变它——最小增量）。
_SUBJECT_EXPIRED_CHECKED_CHANNELS: frozenset[str] = frozenset({ProactiveChannel.SPINE.value})

#: 通知类型 → 渠道（预算信封与账本审计的固定映射；两渠道各自的投递类型）。
CHANNEL_NOTIFICATION_TYPES: Mapping[str, str] = {
    ProactiveChannel.NUDGE.value: "comeback_nudge",
    ProactiveChannel.SPINE.value: "recall_notification",
}

#: 封闭 reason 词表（metrics label 与审计对齐；扩展需同步词表测试）。
BUDGET_DECISION_REASONS: frozenset[str] = frozenset(
    {
        "allowed",
        "passthrough",
        "suggestion_suppressed",  # P-03 类型级（既有语义）
        "cross_channel_suppressed",  # P-03 subject 级跨渠道（本卡）
        "subject_expired",  # 过期计划 subject（本卡，spine 侧）
        "already_effected",  # 同 prompt_key 一次 effect 去重（本卡）
        "quiet_hours",  # P-06 透传
        "daily_cap",  # P-06 透传
        "budget_state_unavailable",  # fail-closed 总闸（设置读不到）
    }
)


def derive_prompt_key(
    channel: ProactiveChannel | str,
    suggestion_type: str,
    subject_key: str,
    *,
    prompt_kind: str = "",
) -> str:
    """稳定且渠道无关的提示身份（有界 sha256 前 32 hex）。

    「同一提示」= 同渠道族 + 同建议类型 + 同触发种类 + 同因果 subject；
    subject 为空时键只由类型/种类决定（此时调用方不应启用 effect 去重）。
    """
    raw = "|".join(
        (
            str(channel).strip().lower(),
            str(suggestion_type or "").strip().lower(),
            str(prompt_kind or "").strip().lower(),
            str(subject_key or "").strip().lower(),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def subject_refs_from_payload(payload: Mapping[str, Any]) -> dict[str, str]:
    """从建议载荷/通知 data 提取渠道无关 subject refs（``domain:id`` 键）。

    只认既有字段（plan_id/task_id/goal_id，含 goal_state.goal_id 投影），
    不新造命名；无 id 字段返回空 dict（无 subject 提示）。
    """
    refs: dict[str, str] = {}

    def _put(domain: str, raw: Any) -> None:
        text = str(raw or "").strip().lower()
        if text:
            refs[domain] = text

    _put("plan", payload.get("plan_id"))
    _put("task", payload.get("task_id"))
    goal_state = payload.get("goal_state")
    if isinstance(goal_state, Mapping):
        _put("goal", goal_state.get("goal_id"))
    _put("goal", payload.get("goal_id"))
    return refs


def build_budget_envelope(
    *,
    channel: ProactiveChannel | str,
    request: ProactiveBudgetRequest,
    decision: ProactiveBudgetDecision,
) -> dict[str, Any]:
    """预算消耗与因果来源的审计信封（盖进 Notification.data 的形状）。

    预算消耗与账本行（Notification 行本身即 cap 计数对象）同源；因果来源 =
    channel + suggestion_type + prompt_kind + subject refs + prompt_key。
    """
    return {
        "prompt_key": decision.prompt_key,
        "channel": str(channel),
        "suggestion_type": request.suggestion_type,
        "prompt_kind": request.prompt_kind,
        "subject": dict(request.subject_refs),
        "daily_count": decision.details.get("count"),
        "daily_cap": decision.details.get("cap"),
        "decided_at": decision.details.get("decided_at"),
    }


@dataclass(frozen=True, slots=True)
class ProactiveBudgetRequest:
    """一次主动触达的预算判定请求（渠道 + 类型 + 因果 subject）。"""

    user_id: str | UUID
    channel: ProactiveChannel
    #: 该提示的建议类型（nudge 渠道 = "comeback_nudge"；spine 渠道 =
    #: "recall_notification"）——P-03 类型级抑制的键。
    suggestion_type: str
    #: 渠道无关 subject refs（``{"plan": ..., "task": ..., "goal": ...}``）。
    subject_refs: Mapping[str, str] = field(default_factory=dict)
    #: 触发种类（spine recall 的 trigger_type 等；进 prompt_key 不进抑制键）。
    prompt_kind: str = ""
    #: naive-UTC 判定时刻（可控时钟；缺省当前）。
    now: datetime | None = None

    @property
    def subject_key(self) -> str:
        """预算闸门用的主 subject 键（plan > goal > task 优先级，domain:id）。"""
        for domain in ("plan", "goal", "task"):
            value = self.subject_refs.get(domain)
            if value:
                return f"{domain}:{value}"
        return ""


@dataclass(frozen=True, slots=True)
class ProactiveBudgetDecision:
    """一步裁决：允许或被哪个预算面以何原因短路（可审计）。"""

    allowed: bool
    #: 封闭 reason（BUDGET_DECISION_REASONS）。
    reason: str
    #: prompt_key（身份可追溯；passthrough 时仍派生）。
    prompt_key: str
    #: 审计细节（suppression/burden/count/cap/decided_at），不含用户内容。
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def suppressed(self) -> bool:
        return not self.allowed


class UnifiedProactiveBudgetService:
    """nudges/spine 渠道共用的用户预算闸门（组合既有权威，零新真源）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self, request: ProactiveBudgetRequest) -> ProactiveBudgetDecision:
        """确定性预算闸门。顺序固定：开关 → 抑制 → 过期 subject → effect 去重 → 负担。"""
        moment = request.now or datetime.now(UTC).replace(tzinfo=None)
        prompt_key = derive_prompt_key(
            request.channel,
            request.suggestion_type,
            request.subject_key,
            prompt_kind=request.prompt_kind,
        )

        # 0. 回滚开关：off = passthrough（恢复各渠道既有行为，审计保留）。
        if not bool(getattr(proactive_config, "PROACTIVE_UNIFIED_BUDGET_ENABLED", True)):
            decision = ProactiveBudgetDecision(True, "passthrough", prompt_key, {"decided_at": moment.isoformat()})
            _record_metric(request, decision)
            return decision

        # 1. P-03 抑制面：类型级（既有）+ subject 级跨渠道（本卡）——一次读。
        feedback = ProactiveSuggestionFeedbackService(self.db)
        try:
            type_suppression, subject_suppression = await feedback.get_suppression_with_subject(
                request.user_id,
                request.suggestion_type,
                request.subject_key,
                now=moment,
            )
        except Exception as exc:
            # fail-closed：抑制状态读不到时宁可少发不可误发（WT378-03 同哲学）。
            logger.warning("unified budget suppression read failed user={}: {!r}", request.user_id, exc)
            decision = ProactiveBudgetDecision(
                False, "budget_state_unavailable", prompt_key, {"decided_at": moment.isoformat()}
            )
            _record_metric(request, decision)
            return decision
        if type_suppression is not None:
            decision = ProactiveBudgetDecision(
                False,
                "suggestion_suppressed",
                prompt_key,
                {"suppression": dict(type_suppression), "decided_at": moment.isoformat()},
            )
            _record_metric(request, decision)
            return decision
        if subject_suppression is not None:
            decision = ProactiveBudgetDecision(
                False,
                "cross_channel_suppressed",
                prompt_key,
                {
                    "subject": request.subject_key,
                    "suppression": dict(subject_suppression),
                    "decided_at": moment.isoformat(),
                },
            )
            _record_metric(request, decision)
            return decision

        # 2. 过期计划 subject：spine 渠道不得补发（nudge 渠道保留 J-07 rescope）。
        if str(request.channel) in _SUBJECT_EXPIRED_CHECKED_CHANNELS and request.subject_refs.get("plan"):
            expired = await self._plan_expired(request.user_id, request.subject_refs["plan"], moment)
            if expired is True:
                decision = ProactiveBudgetDecision(
                    False,
                    "subject_expired",
                    prompt_key,
                    {"subject": f"plan:{request.subject_refs['plan']}", "decided_at": moment.isoformat()},
                )
                _record_metric(request, decision)
                return decision
            if expired is None:
                # 计划读不到（已删/不存在）→ 不再就该 subject 主动打扰（删除不复活）。
                decision = ProactiveBudgetDecision(
                    False,
                    "subject_expired",
                    prompt_key,
                    {
                        "subject": f"plan:{request.subject_refs['plan']}",
                        "missing": True,
                        "decided_at": moment.isoformat(),
                    },
                )
                _record_metric(request, decision)
                return decision

        # 3. 同 prompt_key 一次 effect 去重（仅带 subject 的提示有跨渠道同一性）。
        if request.subject_key:
            effected = await self._prompt_already_effected(request, prompt_key, moment)
            if effected:
                decision = ProactiveBudgetDecision(
                    False,
                    "already_effected",
                    prompt_key,
                    {
                        "window_hours": int(getattr(proactive_config, "PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS", 24)),
                        "decided_at": moment.isoformat(),
                    },
                )
                _record_metric(request, decision)
                return decision

        # 4. P-06 负担闸门（quiet hours → 用户本地日 cap；两渠道同一份预算）。
        from app.aurora.runtime_v1.notification_settings import (
            NotificationSettingsResolver,
            NotificationSettingsUnavailable,
        )

        try:
            burden = await NotificationSettingsResolver(self.db).evaluate_burden(request.user_id, now=moment)
        except NotificationSettingsUnavailable as exc:
            logger.warning("unified budget settings unavailable user={}: {!r}", request.user_id, exc)
            decision = ProactiveBudgetDecision(
                False, "budget_state_unavailable", prompt_key, {"decided_at": moment.isoformat()}
            )
            _record_metric(request, decision)
            return decision
        if not burden.allowed:
            decision = ProactiveBudgetDecision(
                False,
                burden.reason or "daily_cap",
                prompt_key,
                {**dict(burden.details), "decided_at": moment.isoformat()},
            )
            _record_metric(request, decision)
            return decision

        decision = ProactiveBudgetDecision(
            True,
            "allowed",
            prompt_key,
            {**dict(burden.details), "decided_at": moment.isoformat()},
        )
        _record_metric(request, decision)
        return decision

    # -- read faces（只读既有表，不造新真源） ------------------------------

    async def _plan_expired(self, user_id: str | UUID, plan_id: str, moment: datetime) -> bool | None:
        """subject 计划过期判定（读侧真源：Plan.target_date）。

        返回 ``None`` 表示计划不存在/已删/不属于该用户（删除不复活语义）。
        """
        from app.models.plan import Plan

        try:
            plan_uuid = UUID(str(plan_id))
        except ValueError:
            return None
        result = await self.db.execute(
            select(Plan.target_date).where(
                Plan.id == plan_uuid,
                Plan.user_id == UUID(str(user_id)),
                Plan.not_deleted_filter(),
            )
        )
        target_date = result.scalar_one_or_none()
        if target_date is None:
            return None
        return target_date < moment.date()

    async def _prompt_already_effected(
        self,
        request: ProactiveBudgetRequest,
        prompt_key: str,
        moment: datetime,
    ) -> bool:
        """同一 prompt_key 在 effect 窗口内已投递过（多端/多 tick 一次 effect）。

        与 ``_has_recent_notification`` 同款读法（取近期行、Python 侧匹配
        JSON 字段），不依赖 JSON 路径查询、跨 PG/sqlite 一致。
        """
        from app.models.notification import Notification

        window_hours = int(getattr(proactive_config, "PROACTIVE_PROMPT_EFFECT_WINDOW_HOURS", 24))
        if window_hours <= 0:
            return False
        since = moment - timedelta(hours=window_hours)
        result = await self.db.execute(
            select(Notification)
            .where(
                Notification.user_id == UUID(str(request.user_id)),
                Notification.created_at >= since,
                Notification.deleted_at.is_(None),
                Notification.type.in_(sorted(CHANNEL_NOTIFICATION_TYPES.values())),
            )
            .order_by(Notification.created_at.desc())
            .limit(100)
        )
        for notification in result.scalars().all():
            data = notification.data if isinstance(notification.data, dict) else {}
            envelope = data.get("proactive_budget")
            if isinstance(envelope, Mapping) and envelope.get("prompt_key") == prompt_key:
                return True
        return False


def _record_metric(request: ProactiveBudgetRequest, decision: ProactiveBudgetDecision) -> None:
    """预算决定计数（有界 label：channel×decision×reason，无用户维度）。"""
    counter = get_or_create_budget_counter()
    if counter is None:
        return
    try:
        counter.labels(
            channel=str(request.channel),
            decision="allowed" if decision.allowed else "suppressed",
            reason=decision.reason,
        ).inc()
    except Exception:  # noqa: BLE001 — metrics 永不影响判定主链
        logger.debug("unified budget metric record failed")


async def record_cross_channel_suppression(
    db: AsyncSession,
    user_id: str | UUID,
    payload: Mapping[str, Any],
    *,
    persistent: bool,
    source_type: str,
    now: datetime | None = None,
) -> dict[str, dict[str, str]]:
    """把一次用户反馈升格为跨渠道 subject 抑制（V4-P01 拒绝/静音写入口）。

    - 从建议载荷提取 subject refs（plan/task/goal，只认既有字段）；
    - task subject 解析其所属 plan（读侧 ``Task.plan_id``）——nudge 渠道以
      plan 为主 subject，解析后两类键都能命中；
    - 逐 subject 写 P-03 同一权威的 subject 级抑制（``persistent`` 跟随
      用户动作：mute_type → 持久；ignore_today → 24h 冷却）。

    返回 ``{subject_key: suppression}``；无 subject 的建议返回空 dict。
    写失败向上抛（API 层 503，不谎报成功——与 P-03 诚实性同款）。
    """
    from app.models.task import Task

    refs = subject_refs_from_payload(payload)
    if "task" in refs and "plan" not in refs:
        try:
            task_uuid = UUID(refs["task"])
        except ValueError:
            task_uuid = None
        if task_uuid is not None:
            result = await db.execute(
                select(Task.plan_id).where(Task.id == task_uuid, Task.user_id == UUID(str(user_id)))
            )
            plan_id = result.scalar_one_or_none()
            if plan_id is not None:
                refs["plan"] = str(plan_id).lower()

    if not refs:
        return {}

    feedback = ProactiveSuggestionFeedbackService(db)
    recorded: dict[str, dict[str, str]] = {}
    for domain in ("plan", "goal", "task"):
        identifier = refs.get(domain)
        if not identifier:
            continue
        subject_key = f"{domain}:{identifier}"
        suppression = await feedback.record_subject_suppression(
            user_id,
            subject_key,
            persistent=persistent,
            source_type=source_type,
            now=now,
        )
        if suppression:
            recorded[subject_key] = suppression
    return recorded
