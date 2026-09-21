"""D-05 · Intervention → Outcome 关联管线服务层。

形态（契约 = ``app/core/intervention_lifecycle.py``）：
- **生命周期记录**：``record_exposure`` / ``record_response`` /
  ``record_outcome_association``。幂等由存储层唯一约束
  ``uq_intervention_lifecycle_once (decision_id, event_type, dedupe_subkey)``
  + 方言化 ``INSERT .. ON CONFLICT DO NOTHING`` 保证（M-07 FOR UPDATE+复查的
  唯一约束同法）：并发重复/重放投递第二写 rowcount=0 → ``recorded=False``，
  不抛异常、不留第二行。
- **漏斗完整性**：accept/edit/reject/start 与 outcome 关联都要求 exposure
  先在（同一 user 下）——没有 exposure 的响应是孤儿事件，拒收（可观测降级
  而非静默落库）。shadow 治理决策与 inert 干预（A-01）不可能有 exposure，
  ``record_exposure`` 直接拒绝（伪造漏斗锚点 = 假数据入口）。
- **outcome 白名单双层门**（灵魂红线）：``is_whitelisted_outcome_source``
  （枚举成员 ∈ 白名单）+ 窗口校验 + 关联键匹配，三层全过才落
  ``outcome_observed`` 行。chat reply/sentiment 类源在两层都被拒。
- **关联扫描**（``associate_pending_outcomes``）：增量 pass——取用户近期
  exposure（观察窗可能未关的 + 刚关闭的），一次 D-02 ledger 分页遍历，按
  关联键 + 窗口时序匹配，逐条落关联行（幂等可重跑）。outcome 真相不在此
  复制：关联行只存 (outcome_ref, source, polarity, truth_class) 镜像快照。
- **保守关联摘要**（``association_summary``）：per-user / per-scope（goal/
  friction/execution_mode/intervention_type 切片过滤），censored 三态分解、
  Wilson 区间、证据档位、非因果 claim 模板——统计谦抑语义全部来自契约纯
  函数，本层只做聚合。
- **增量/缓存钩**（M-06 Context retrieval 预留）：``watermark()`` 是事件集
  的内容印记（行数 + 最新时刻 + id 摘要）——事件集不变则印记不变，M-06 可
  以 (cache_key, watermark) 做摘要缓存失效，无需理解内部结构。

边界（不重建真源）：
- outcome 事实 → D-02 ``OutcomeLedgerService``（本服务只读消费）；
- 干预决策事实 → A-01 契约（本服务只消费 decision_id 与镜像字段）；
- 生命周期事件本身 → 本服务的 ``intervention_lifecycle_events`` 表（D-05
  自有真源；event_outbox 7 天清理，只承载集成通知——``_emit_outbox_event``
  M-07 同款守卫写，表不存在时降级跳过）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping
from uuid import UUID

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.aurora_decision import AuroraDecisionContract, aurora_decision_from_dict
from app.core.event_registry import EventSource, build_event_metadata
from app.core.intervention_lifecycle import (
    DEFAULT_OBSERVATION_WINDOW_HOURS,
    INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
    MAX_OBSERVATION_WINDOW_HOURS,
    OUTCOME_ASSOCIATION_SOURCES,
    USER_RESPONSE_EVENT_TYPES,
    AssociationSummary,
    LifecycleEventType,
    ObservationStatus,
    SituationSignature,
    SliceSummary,
    association_claim,
    association_evidence_tier,
    clamp_observation_window_hours,
    derive_lifecycle_event_id,
    execution_mode_slice,
    friction_tag_from_state_key,
    goal_slice,
    is_exposable_intervention,
    is_whitelisted_outcome_source,
    linkage_keys,
    outcome_links_exposure,
    resolve_observation_status,
    truth_class_weight,
    wilson_interval,
)
from app.core.outcome_ledger import OutcomeEntry, OutcomeSource
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.user import User
from app.services.outcome_ledger_service import EXCLUDED_COHORT_REGISTRATION_SOURCES, OutcomeLedgerService

INTERVENTION_LIFECYCLE_SERVICE_VERSION = "intervention-lifecycle.d05.v1"

# outbox 集成通知的事件名映射（仅本服务自有 aggregate 的三个新名；accept/
# edit/reject 不发 outbox——reserved 名 intervention.feedback_recorded 属
# intervention_request aggregate 族，桥接归 A-04 接线卡，见 REPORT §follow-up）。
_OUTBOX_EVENT_NAMES: dict[str, str] = {
    LifecycleEventType.EXPOSED.value: "intervention.exposed",
    LifecycleEventType.STARTED.value: "intervention.started",
    LifecycleEventType.OUTCOME_OBSERVED.value: "intervention.outcome_associated",
}
_LIFECYCLE_AGGREGATE_TYPE = "intervention_lifecycle"

#: 关联扫描的回看地平线：最大观察窗（30d）+ 7d 宽限（窗口刚关的 exposure 仍
#: 扫一轮，outcome 幂等保证重复扫描零成本）。
_ASSOCIATION_SCAN_HORIZON = timedelta(hours=MAX_OBSERVATION_WINDOW_HOURS + 7 * 24)

#: 单用户单次关联扫描的 ledger 分页上限（200/页 × 25 页 = 5000 条封顶）。
_LEDGER_PAGE_LIMIT = 200
_LEDGER_MAX_PAGES = 25

#: 摘要聚合的单次加载上限（exposure 侧；防失控扫描）。
_SUMMARY_EVENT_CAP = 5000


@dataclass(frozen=True)
class LifecycleRecordResult:
    """一次生命周期记录的结果（幂等语义对调用方可观测）。"""

    recorded: bool
    reason: str
    event_id: str
    decision_id: str
    event_type: str


def _utcnow() -> datetime:
    return datetime.utcnow()


def _naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)  # DB naive-UTC 规范（假定存入即 UTC）
    return value


class InterventionLifecycleService:
    """干预生命周期记录 + outcome 关联 + 保守摘要（D-05 全部三个 Work 面）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 1. 生命周期记录（幂等）
    # ------------------------------------------------------------------

    async def record_exposure(
        self,
        *,
        decision: AuroraDecisionContract | Mapping[str, Any],
        user_id: UUID | str,
        goal_type: str | None = None,
        friction_state_key: str | None = None,
        plan_id: UUID | str | None = None,
        node_id: UUID | str | None = None,
        intervention_request_id: UUID | str | None = None,
        window_hours: int | None = DEFAULT_OBSERVATION_WINDOW_HOURS,
        occurred_at: datetime | None = None,
        detail: Mapping[str, Any] | None = None,
        emit: bool = True,
    ) -> LifecycleRecordResult:
        """记录 exposure（漏斗锚点；同一 decision 恰一次）。

        拒绝面（全部返回 recorded=False + reason，不抛异常——调用方可观测降级）：
        决策载荷损坏 / 契约校验不过 / inert 干预 / shadow 治理决策。
        friction 推导优先级：显式 ``friction_state_key`` > 决策 evidence_refs 中
        的 ``signal://<state_key>`` > ``unattributed``。
        """
        contract = self._coerce_decision(decision)
        if contract is None:
            return self._refused("", LifecycleEventType.EXPOSED.value, "decision_payload_invalid")
        violations = contract.validate()
        if violations:
            return self._refused(contract.decision_id_or_compute(), LifecycleEventType.EXPOSED.value, "decision_contract_violated")
        exposable, reason = is_exposable_intervention(contract.intervention_type, contract.governance_mode)
        if not exposable:
            return self._refused(contract.decision_id_or_compute(), LifecycleEventType.EXPOSED.value, reason)

        decision_id = contract.decision_id_or_compute()
        friction = friction_tag_from_state_key(friction_state_key or self._friction_state_key_from_refs(contract))
        task_id = self._task_id_from_action_ref(contract.action_proposal_ref)
        effective_window = clamp_observation_window_hours(window_hours)
        occurred = _naive(occurred_at) or _utcnow()

        detail_payload: dict[str, Any] = {"window_hours": effective_window}
        if detail:
            detail_payload.update(dict(detail))

        values = {
            "user_id": UUID(str(user_id)),
            "decision_id": decision_id,
            "event_type": LifecycleEventType.EXPOSED.value,
            "intervention_type": contract.intervention_type,
            "execution_mode": None if contract.execution_mode is None else contract.execution_mode.value,
            "goal_type": goal_slice(goal_type),
            "friction_tag": friction,
            "linkage": linkage_keys(
                task_id=task_id,
                plan_id=plan_id,
                node_id=node_id,
                intervention_request_id=intervention_request_id,
            ),
            "detail": detail_payload,
            "dedupe_subkey": "",
            "occurred_at": occurred,
        }
        return await self._insert_once(
            values,
            outcome=None,
            emit=emit,
            outbox_payload_extra={
                "intervention_type": contract.intervention_type,
                "goal_type": values["goal_type"],
                "friction_tag": friction,
                "window_hours": effective_window,
            },
        )

    async def record_response(
        self,
        *,
        decision_id: str,
        user_id: UUID | str,
        event_type: LifecycleEventType | str,
        occurred_at: datetime | None = None,
        detail: Mapping[str, Any] | None = None,
        emit: bool = True,
    ) -> LifecycleRecordResult:
        """记录 accept/edit/reject/start（同一 decision 同一类型恰一次）。

        漏斗完整性：exposure 必须先在（同 user）。无 exposure 的响应是孤儿
        事件——拒收并留痕（伪造中段 = 无锚点计数，双计风险源）。
        """
        kind = LifecycleEventType(event_type)
        if kind.value not in USER_RESPONSE_EVENT_TYPES:
            raise ValueError(f"event_type {event_type!r} is not a user-response lifecycle event")

        exposure = await self._get_exposure(decision_id=decision_id, user_id=user_id)
        if exposure is None:
            return self._refused(str(decision_id), kind.value, "no_exposure")

        values = {
            "user_id": UUID(str(user_id)),
            "decision_id": str(decision_id),
            "event_type": kind.value,
            "intervention_type": exposure.intervention_type,
            "execution_mode": exposure.execution_mode,
            "goal_type": exposure.goal_type,
            "friction_tag": exposure.friction_tag,
            "linkage": exposure.linkage,
            "detail": dict(detail) if detail else None,
            "dedupe_subkey": "",
            "occurred_at": _naive(occurred_at) or _utcnow(),
        }
        return await self._insert_once(values, outcome=None, emit=emit)

    async def record_outcome_association(
        self,
        *,
        decision_id: str,
        outcome: OutcomeEntry,
        emit: bool = False,
    ) -> LifecycleRecordResult:
        """记录一条白名单 outcome 与干预的关联（同一 outcome 对同一 decision 恰一次）。

        三层门（任一不过即拒，recorded=False + reason）：
        1. 白名单 + 硬拒绝门（``is_whitelisted_outcome_source``——chat/sentiment
           类源在此永拒）；
        2. exposure 存在且 outcome 归属同一 user；
        3. 窗口内时序（exposed_at ≤ outcome.occurred_at ≤ 窗口末）+ 关联键
           匹配（``outcome_links_exposure``）。
        """
        if not is_whitelisted_outcome_source(outcome.source):
            return self._refused(str(decision_id), LifecycleEventType.OUTCOME_OBSERVED.value, "outcome_source_not_whitelisted")

        exposure = await self._get_exposure(decision_id=decision_id, user_id=outcome.user_id)
        if exposure is None:
            return self._refused(str(decision_id), LifecycleEventType.OUTCOME_OBSERVED.value, "no_exposure")

        window_hours = self._window_hours_of(exposure)
        window_end = exposure.occurred_at + timedelta(hours=window_hours)
        outcome_at = _naive(outcome.occurred_at)
        if outcome_at is None or outcome_at < exposure.occurred_at or outcome_at > window_end:
            return self._refused(str(decision_id), LifecycleEventType.OUTCOME_OBSERVED.value, "outcome_out_of_window")
        if not outcome_links_exposure(exposure.linkage or {}, outcome.correlation):
            return self._refused(str(decision_id), LifecycleEventType.OUTCOME_OBSERVED.value, "outcome_not_linked_to_intervention")

        values = {
            "user_id": exposure.user_id,
            "decision_id": str(decision_id),
            "event_type": LifecycleEventType.OUTCOME_OBSERVED.value,
            "intervention_type": exposure.intervention_type,
            "execution_mode": exposure.execution_mode,
            "goal_type": exposure.goal_type,
            "friction_tag": exposure.friction_tag,
            "linkage": exposure.linkage,
            "outcome_source": OutcomeSource(outcome.source).value,
            "outcome_ref": outcome.outcome_id,
            "outcome_polarity": outcome.polarity.value if hasattr(outcome.polarity, "value") else str(outcome.polarity),
            "outcome_truth_class": outcome.truth_class.value if hasattr(outcome.truth_class, "value") else str(outcome.truth_class),
            "detail": None,
            "dedupe_subkey": outcome.outcome_id,
            "occurred_at": outcome_at,
        }
        return await self._insert_once(values, outcome=outcome, emit=emit)

    # ------------------------------------------------------------------
    # 2. 关联扫描（增量 pass，幂等可重跑）
    # ------------------------------------------------------------------

    async def associate_pending_outcomes(
        self,
        *,
        user_id: UUID | str,
        now: datetime | None = None,
    ) -> int:
        """扫描用户近期 exposure，把窗口内、关联键匹配的白名单 outcome 落关联行。

        一次 ledger 分页遍历（O(页数) 查询），exposure 匹配在内存完成；重复
        运行零成本（outcome 幂等键拒第二行）。返回新落关联行数。
        """
        user_uuid = UUID(str(user_id))
        now_naive = _naive(now) or _utcnow()
        horizon_from = now_naive - _ASSOCIATION_SCAN_HORIZON

        exposures = list(
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent)
                    .where(
                        InterventionLifecycleEvent.user_id == user_uuid,
                        InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                        InterventionLifecycleEvent.occurred_at >= horizon_from,
                        InterventionLifecycleEvent.not_deleted_filter(),
                    )
                    .order_by(InterventionLifecycleEvent.occurred_at.asc())
                    .limit(500)
                )
            ).scalars().all()
        )
        if not exposures:
            return 0

        earliest = min(e.occurred_at for e in exposures)
        latest_window_end = max(
            e.occurred_at + timedelta(hours=self._window_hours_of(e)) for e in exposures
        )
        ledger = OutcomeLedgerService(self.db)
        entries: list[OutcomeEntry] = []
        cursor: str | None = None
        for _ in range(_LEDGER_MAX_PAGES):
            page = await ledger.query(
                user_id=user_uuid,
                since=max(earliest, horizon_from),
                until=latest_window_end,
                limit=_LEDGER_PAGE_LIMIT,
                cursor=cursor,
            )
            entries.extend(page.items)
            cursor = page.next_cursor
            if cursor is None:
                break

        whitelisted = [entry for entry in entries if entry.source in OUTCOME_ASSOCIATION_SOURCES]
        new_links = 0
        for exposure in exposures:
            window_end = exposure.occurred_at + timedelta(hours=self._window_hours_of(exposure))
            for entry in whitelisted:
                outcome_at = _naive(entry.occurred_at)
                if outcome_at is None or outcome_at < exposure.occurred_at or outcome_at > window_end:
                    continue
                if not outcome_links_exposure(exposure.linkage or {}, entry.correlation):
                    continue
                result = await self.record_outcome_association(decision_id=exposure.decision_id, outcome=entry)
                if result.recorded:
                    new_links += 1
        if new_links:
            await self.db.commit()
        return new_links

    # ------------------------------------------------------------------
    # 3. 保守关联摘要（per-user / per-scope）
    # ------------------------------------------------------------------

    async def association_summary(
        self,
        *,
        user_id: UUID | str | None = None,
        intervention_type: str | None = None,
        goal_type: str | None = None,
        friction_tag: str | None = None,
        execution_mode: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        now: datetime | None = None,
        user_last_active_at: datetime | None = None,
        include_demo_cohort: bool = False,
    ) -> AssociationSummary:
        """历史结果摘要（验收 ②）。

        - ``user_id`` 给定 → per-user 摘要（scope=("user", uuid)）；
        - ``user_id=None`` → 跨用户聚合（scope=("global",)，默认排除
          seed/guest cohort——词表复用 D-02 ``EXCLUDED_COHORT_REGISTRATION_SOURCES``，
          不另立第二套 cohort 分类学）。
        - 切片过滤（goal/friction/execution_mode/intervention_type）在存储列上
          下推；摘要内再按 SituationSignature 分组。
        - ``user_last_active_at`` 缺省时按 ``users.last_login_at`` 解析（churned
          判定的活跃面；这是观察能力的度量，不是 outcome 信号——chat 内容
          永不进入本管线）。
        """
        if user_id is not None:
            scope = ("user", str(UUID(str(user_id))))
            user_filter_uuid: UUID | None = UUID(str(user_id))
        else:
            scope = ("global",)
            user_filter_uuid = None

        now_naive = _naive(now) or _utcnow()
        predicates = [InterventionLifecycleEvent.not_deleted_filter()]
        if user_filter_uuid is not None:
            predicates.append(InterventionLifecycleEvent.user_id == user_filter_uuid)
        if intervention_type is not None:
            predicates.append(InterventionLifecycleEvent.intervention_type == str(intervention_type))
        if goal_type is not None:
            predicates.append(InterventionLifecycleEvent.goal_type == goal_slice(goal_type))
        if friction_tag is not None:
            predicates.append(InterventionLifecycleEvent.friction_tag == str(friction_tag))
        if execution_mode is not None:
            predicates.append(
                InterventionLifecycleEvent.execution_mode == execution_mode_slice(execution_mode)
                if execution_mode_slice(execution_mode) != "unattributed"
                else InterventionLifecycleEvent.execution_mode.is_(None)
            )
        window = OutcomeLedgerService._window_factory(since, until)(InterventionLifecycleEvent, InterventionLifecycleEvent.occurred_at)
        if window is not None:  # since/until 全空时无谓词（D-02 _where(None) 同款纪律）
            predicates.append(window)

        rows = list(
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent)
                    .where(*predicates)
                    .order_by(InterventionLifecycleEvent.occurred_at.asc())
                    .limit(_SUMMARY_EVENT_CAP)
                )
            ).scalars().all()
        )

        if user_filter_uuid is None and not include_demo_cohort:
            rows = await self._exclude_demo_cohort_rows(rows)

        watermark = self._watermark_of(rows)
        slices = await self._aggregate_slices(rows, now_naive=now_naive, user_last_active_at=user_last_active_at, scope=scope)
        return AssociationSummary(
            scope=scope,
            generated_at=now_naive,
            since=_naive(since),
            until=_naive(until),
            watermark=watermark,
            slices=tuple(slices),
        )

    async def watermark(self, *, user_id: UUID | str | None = None) -> str:
        """事件集内容印记（M-06 摘要缓存失效钩；事件集不变 → 印记不变）。"""
        predicates = [InterventionLifecycleEvent.not_deleted_filter()]
        if user_id is not None:
            predicates.append(InterventionLifecycleEvent.user_id == UUID(str(user_id)))
        rows = list(
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent.occurred_at, InterventionLifecycleEvent.id)
                    .where(*predicates)
                    .order_by(InterventionLifecycleEvent.occurred_at.desc())
                    .limit(1000)
                )
            ).all()
            or []
        )
        return self._watermark_of_pairs(rows)

    @staticmethod
    def summary_cache_key(
        *,
        user_id: UUID | str | None = None,
        intervention_type: str | None = None,
        goal_type: str | None = None,
        friction_tag: str | None = None,
        execution_mode: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> str:
        """确定性缓存键（M-06 Context retrieval 以 (key, watermark) 做失效）。"""
        payload = json.dumps(
            {
                "v": INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
                "user_id": str(user_id) if user_id else None,
                "intervention_type": intervention_type,
                "goal_type": goal_type,
                "friction_tag": friction_tag,
                "execution_mode": execution_mode,
                "since": since.isoformat() if since else None,
                "until": until.isoformat() if until else None,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        import hashlib

        return "d05:assoc_summary:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]

    # ------------------------------------------------------------------
    # 内部：记录与查询原语
    # ------------------------------------------------------------------

    async def _insert_once(
        self,
        values: Mapping[str, Any],
        *,
        outcome: OutcomeEntry | None,
        emit: bool,
        outbox_payload_extra: Mapping[str, Any] | None = None,
    ) -> LifecycleRecordResult:
        """方言化 ON CONFLICT DO NOTHING 插入（唯一约束 = 幂等语义本体）。"""
        event_type = str(values["event_type"])
        decision_id = str(values["decision_id"])
        event_id = derive_lifecycle_event_id(
            decision_id=decision_id,
            event_type=event_type,
            dedupe_subkey=str(values.get("dedupe_subkey") or ""),
        )
        model_values = dict(values)
        stmt = self._insert_statement(InterventionLifecycleEvent, model_values)
        result = await self.db.execute(stmt)
        inserted = bool(result.rowcount)
        if inserted:
            await self.db.commit()
            if emit:
                await self._emit_outbox_event(
                    user_id=model_values["user_id"],
                    decision_id=decision_id,
                    event_type=event_type,
                    occurred_at=model_values["occurred_at"],
                    payload_extra=outbox_payload_extra,
                    outcome=outcome,
                )
        # 重复路径不 rollback（achievement_engine 同款纪律）：DO NOTHING 语句本身
        # 已完成、无未决写入；rollback 会 expire 会话内全部已加载实例，导致
        # associate_pending_outcomes 重跑扫描（全 duplicate）时下一次属性访问在
        # async 上下文里触发同步 lazy IO（MissingGreenlet）。
        return LifecycleRecordResult(
            recorded=inserted,
            reason="" if inserted else "duplicate_event",
            event_id=event_id,
            decision_id=decision_id,
            event_type=event_type,
        )

    def _insert_statement(self, model, values: Mapping[str, Any]):
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        bind = self.db.get_bind()
        conflict_cols = ["decision_id", "event_type", "dedupe_subkey"]
        if bind.dialect.name == "postgresql":
            return pg_insert(model).values(**values).on_conflict_do_nothing(index_elements=conflict_cols)
        return sqlite_insert(model).values(**values).on_conflict_do_nothing(index_elements=conflict_cols)

    async def _get_exposure(
        self, *, decision_id: str, user_id: UUID | str | None = None
    ) -> InterventionLifecycleEvent | None:
        predicates = [
            InterventionLifecycleEvent.decision_id == str(decision_id),
            InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
            InterventionLifecycleEvent.not_deleted_filter(),
        ]
        if user_id is not None:
            predicates.append(InterventionLifecycleEvent.user_id == UUID(str(user_id)))
        row = (
            await self.db.execute(
                select(InterventionLifecycleEvent).where(*predicates).order_by(InterventionLifecycleEvent.occurred_at.asc()).limit(1)
            )
        ).scalar_one_or_none()
        return row

    @staticmethod
    def _window_hours_of(exposure: InterventionLifecycleEvent) -> int:
        detail = exposure.detail if isinstance(exposure.detail, Mapping) else {}
        return clamp_observation_window_hours(detail.get("window_hours"))

    @staticmethod
    def _coerce_decision(decision: AuroraDecisionContract | Mapping[str, Any]) -> AuroraDecisionContract | None:
        if isinstance(decision, AuroraDecisionContract):
            return decision
        return aurora_decision_from_dict(decision)

    @staticmethod
    def _friction_state_key_from_refs(contract: AuroraDecisionContract) -> str | None:
        for ref in contract.evidence_refs:
            if ref.startswith("signal://"):
                return ref.split("signal://", 1)[1] or None
        return None

    @staticmethod
    def _task_id_from_action_ref(action_proposal_ref: str | None) -> str | None:
        if not action_proposal_ref or not action_proposal_ref.startswith("task://"):
            return None
        return action_proposal_ref.split("task://", 1)[1] or None

    @staticmethod
    def _refused(decision_id: str, event_type: str, reason: str) -> LifecycleRecordResult:
        logger.info("InterventionLifecycle: refused {} event (reason={}, decision={})", event_type, reason, decision_id)
        return LifecycleRecordResult(recorded=False, reason=reason, event_id="", decision_id=decision_id, event_type=event_type)

    # ------------------------------------------------------------------
    # 内部：摘要聚合
    # ------------------------------------------------------------------

    async def _aggregate_slices(
        self,
        rows: list[InterventionLifecycleEvent],
        *,
        now_naive: datetime,
        user_last_active_at: datetime | None,
        scope: tuple[str, ...],
    ) -> list[SliceSummary]:
        exposures_by_decision: dict[str, InterventionLifecycleEvent] = {}
        responses: dict[str, list[InterventionLifecycleEvent]] = {}
        outcomes: dict[str, list[InterventionLifecycleEvent]] = {}
        for row in rows:
            if row.event_type == LifecycleEventType.EXPOSED.value:
                exposures_by_decision.setdefault(row.decision_id, row)
            elif row.event_type == LifecycleEventType.OUTCOME_OBSERVED.value:
                outcomes.setdefault(row.decision_id, []).append(row)
            else:
                responses.setdefault(row.decision_id, []).append(row)

        # churned 判定的活跃面：显式参数 > users.last_login_at（per-user 解析）
        last_active_by_user = await self._resolve_last_active(
            {e.user_id for e in exposures_by_decision.values()}, fallback=user_last_active_at
        )

        groups: dict[tuple[str, str, str, str], list[_ExposureFacts]] = {}
        for decision_id, exposure in exposures_by_decision.items():
            outcome_rows = outcomes.get(decision_id, [])
            response_rows = responses.get(decision_id, [])
            facts = _ExposureFacts(
                exposure=exposure,
                outcome_rows=outcome_rows,
                accepted=any(r.event_type == LifecycleEventType.ACCEPTED.value for r in response_rows),
                started=any(r.event_type == LifecycleEventType.STARTED.value for r in response_rows),
                last_active=last_active_by_user.get(exposure.user_id),
            )
            signature = SituationSignature(
                intervention_type=exposure.intervention_type,
                goal_type=exposure.goal_type or "unknown",
                friction_tag=exposure.friction_tag or "unattributed",
                execution_mode=execution_mode_slice(exposure.execution_mode),
            )
            groups.setdefault(signature.as_tuple(), []).append(facts)

        scope_label = "该用户" if scope[0] == "user" else "全局范围"
        summaries: list[SliceSummary] = []
        for key in sorted(groups):
            facts_list = groups[key]
            n_exposed = len(facts_list)
            n_accepted = sum(1 for f in facts_list if f.accepted)
            n_started = sum(1 for f in facts_list if f.started)
            n_positive = n_negative = 0
            n_not_yet = n_closed = n_churned = n_unknown = 0
            weighted_positive = weighted_total = 0.0
            for facts in facts_list:
                status = resolve_observation_status(
                    exposed_at=facts.exposure.occurred_at,
                    window_hours=self._window_hours_of(facts.exposure),
                    outcome_times=[r.occurred_at for r in facts.outcome_rows],
                    now=now_naive,
                    user_last_active_at=facts.last_active,
                )
                if status is ObservationStatus.OBSERVED:
                    for r in facts.outcome_rows:
                        if r.occurred_at and facts.exposure.occurred_at <= r.occurred_at:
                            if r.outcome_polarity == "positive":
                                n_positive += 1
                            elif r.outcome_polarity == "negative":
                                n_negative += 1
                            weight = truth_class_weight(r.outcome_truth_class)
                            weighted_total += weight
                            if r.outcome_polarity == "positive":
                                weighted_positive += weight
                elif status is ObservationStatus.CENSORED_NOT_YET_DUE:
                    n_not_yet += 1
                elif status is ObservationStatus.CENSORED_WINDOW_CLOSED:
                    n_closed += 1
                elif status is ObservationStatus.CENSORED_USER_CHURNED:
                    n_churned += 1
                else:
                    n_unknown += 1

            n_observed = n_positive + n_negative
            rate = (n_positive / n_observed) if n_observed else 0.0
            interval = wilson_interval(n_positive, n_observed)
            weighted_rate = (weighted_positive / weighted_total) if weighted_total > 0 else 0.0
            tier = association_evidence_tier(n_observed)
            signature = SituationSignature(
                intervention_type=key[0], goal_type=key[1], friction_tag=key[2], execution_mode=key[3]
            )
            summaries.append(
                SliceSummary(
                    signature=signature,
                    n_exposed=n_exposed,
                    n_accepted=n_accepted,
                    n_started=n_started,
                    n_positive=n_positive,
                    n_negative=n_negative,
                    n_censored_not_yet_due=n_not_yet,
                    n_censored_window_closed=n_closed,
                    n_censored_user_churned=n_churned,
                    n_unknown=n_unknown,
                    weighted_positive=weighted_positive,
                    weighted_total=weighted_total,
                    positive_association_rate=rate,
                    rate_interval=interval,
                    weighted_positive_rate=weighted_rate,
                    evidence_strength=tier,
                    claim=association_claim(
                        tier, n_observed=n_observed, n_positive=n_positive, n_negative=n_negative, scope_label=scope_label
                    ),
                )
            )
        return summaries

    async def _resolve_last_active(
        self, user_ids: set, *, fallback: datetime | None
    ) -> dict:
        """活跃面解析：显式 fallback > users.last_login_at（缺失用户无条目 → None）。"""
        if not user_ids:
            return {}
        if fallback is not None:
            return {user_id: fallback for user_id in user_ids}
        rows = list(
            (
                await self.db.execute(
                    select(User.id, User.last_login_at).where(User.id.in_(list(user_ids)))
                )
            ).all()
            or []
        )
        resolved = {user_id: _naive(last_login) for user_id, last_login in rows}
        return resolved

    async def _exclude_demo_cohort_rows(
        self, rows: list[InterventionLifecycleEvent]
    ) -> list[InterventionLifecycleEvent]:
        """global scope 的 cohort 边界（词表复用 D-02，B-02 F1 同源）。"""
        user_ids = {row.user_id for row in rows}
        if not user_ids:
            return rows
        seed_ids = set(
            (
                await self.db.execute(
                    select(User.id).where(User.registration_source.in_(EXCLUDED_COHORT_REGISTRATION_SOURCES))
                )
            ).scalars().all()
        )
        return [row for row in rows if row.user_id not in seed_ids]

    @staticmethod
    def _watermark_of(rows: Iterable[InterventionLifecycleEvent]) -> str:
        pairs = [(row.occurred_at, str(row.id)) for row in rows]
        return InterventionLifecycleService._watermark_of_pairs(pairs)

    @staticmethod
    def _watermark_of_pairs(pairs: list) -> str:
        import hashlib

        if not pairs:
            return "empty"
        newest = max(pairs, key=lambda pair: (pair[0] or datetime.min, str(pair[1])))
        seed = json.dumps(
            {
                "n": len(pairs),
                "max_occurred_at": newest[0].isoformat() if newest[0] else None,
                "max_id": str(newest[1]),  # GUID 列返回 UUID 对象；印记一律 canonical str
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return "wm_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    # ------------------------------------------------------------------
    # 内部：outbox 集成通知（M-07 守卫写；分析真源在表，不在 outbox）
    # ------------------------------------------------------------------

    async def _emit_outbox_event(
        self,
        *,
        user_id: UUID,
        decision_id: str,
        event_type: str,
        occurred_at: datetime,
        payload_extra: Mapping[str, Any] | None,
        outcome: OutcomeEntry | None,
    ) -> bool:
        outbox_name = _OUTBOX_EVENT_NAMES.get(event_type)
        if outbox_name is None:
            return False
        if not await _outbox_tables_exist(self.db):
            logger.debug("lifecycle outbox emit skipped: event_outbox tables unavailable")
            return False
        try:
            sequence_number = await _next_sequence(self.db, _LIFECYCLE_AGGREGATE_TYPE, user_id)
            payload: dict[str, Any] = {
                "schema_version": INTERVENTION_LIFECYCLE_SCHEMA_VERSION,
                "decision_id": decision_id,
                "lifecycle_event_type": event_type,
            }
            if payload_extra:
                payload.update(dict(payload_extra))
            if outcome is not None:
                payload.update(
                    {
                        "outcome_ref": outcome.outcome_id,
                        "outcome_source": OutcomeSource(outcome.source).value,
                        "outcome_polarity": outcome.polarity.value,
                    }
                )
            metadata = build_event_metadata(
                user_id=user_id,
                source=EventSource.SERVER_SERVICE,
                service="intervention_lifecycle_service",
                event_name=outbox_name,
                aggregate_type=_LIFECYCLE_AGGREGATE_TYPE,
                aggregate_id=user_id,
                sequence_number=sequence_number,
                occurred_at=occurred_at,
                correlation=None,  # decision_id 非 canonical UUID，不能进 correlation（D-01 已知限制）
                extra={
                    "decision_id": decision_id,
                    "lifecycle_event_type": event_type,
                    "service_version": INTERVENTION_LIFECYCLE_SERVICE_VERSION,
                },
            )
            await self.db.execute(
                text("""
                    INSERT INTO event_outbox
                    (aggregate_type, aggregate_id, event_type, event_version, sequence_number, payload, metadata)
                    VALUES (:aggregate_type, :aggregate_id, :event_type, 1, :sequence_number, :payload, :metadata)
                    """),
                {
                    "aggregate_type": _LIFECYCLE_AGGREGATE_TYPE,
                    "aggregate_id": str(user_id),
                    "event_type": outbox_name,
                    "sequence_number": sequence_number,
                    "payload": json.dumps(payload, ensure_ascii=False),
                    "metadata": json.dumps(metadata, ensure_ascii=False),
                },
            )
            await self.db.commit()
            return True
        except Exception as exc:  # noqa: BLE001 — outbox 是集成通知，失败不阻塞记录真源
            logger.warning("lifecycle outbox emit failed (decision_id={}): {}", decision_id, exc)
            await self.db.rollback()
            return False


@dataclass(frozen=True)
class _ExposureFacts:
    exposure: InterventionLifecycleEvent
    outcome_rows: list[InterventionLifecycleEvent]
    accepted: bool
    started: bool
    last_active: datetime | None


# ---------------------------------------------------------------------------
# outbox 辅助（galaxy_service / M-07 writer pattern，standalone 复制面）
# ---------------------------------------------------------------------------


async def _outbox_tables_exist(db: AsyncSession) -> bool:
    connection = await db.connection()
    return await connection.run_sync(lambda sync_conn: _has_table(sync_conn, "event_outbox"))


def _has_table(sync_conn, name: str) -> bool:
    from sqlalchemy import inspect

    try:
        return inspect(sync_conn).has_table(name)
    except Exception:  # noqa: BLE001
        return False


async def _next_sequence(db: AsyncSession, aggregate_type: str, aggregate_id: UUID) -> int:
    try:
        result = await db.execute(
            text("""
                INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence)
                VALUES (:aggregate_type, :aggregate_id, 1)
                ON CONFLICT (aggregate_type, aggregate_id)
                DO UPDATE SET next_sequence = event_sequence_counters.next_sequence + 1
                RETURNING next_sequence
                """),
            {"aggregate_type": aggregate_type, "aggregate_id": str(aggregate_id)},
        )
        return int(result.scalar_one())
    except Exception as exc:  # noqa: BLE001 — dialect without upsert/returning
        logger.debug("sequence upsert fallback ({})", exc)
        current_result = await db.execute(
            text(
                "SELECT next_sequence FROM event_sequence_counters " "WHERE aggregate_type = :t AND aggregate_id = :a"
            ),
            {"t": aggregate_type, "a": str(aggregate_id)},
        )
        current = current_result.scalar_one_or_none()
        if current is None:
            await db.execute(
                text(
                    "INSERT INTO event_sequence_counters (aggregate_type, aggregate_id, next_sequence) "
                    "VALUES (:t, :a, 1)"
                ),
                {"t": aggregate_type, "a": str(aggregate_id)},
            )
            return 1
        nxt = int(current) + 1
        await db.execute(
            text("UPDATE event_sequence_counters SET next_sequence = :n " "WHERE aggregate_type = :t AND aggregate_id = :a"),
            {"n": nxt, "t": aggregate_type, "a": str(aggregate_id)},
        )
        return nxt
