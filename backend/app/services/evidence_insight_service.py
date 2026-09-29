"""Evidence-driven insight cards（D-07）——洞察呈现层的派生真源投影。

设计纪律（卡 D-07 / Forbidden；V4-D05 呈现契约增量）：
- **不重建真源**：三类洞察全部派生自已交付面——摩擦模式读 D-05
  intervention lifecycle 事件表（friction_tag 记录时点固化）；"有帮助的应对"
  读 D-05 ``association_summary``（保守关联摘要，非因果）；目标进展读
  Goal/Task 真源（A-07 ``_comeback_goal_state`` 同款读侧口径：progress 列
  原样上报 + 任务账本诚实计数，两口径互不篡改）。
- **五要素结构**：每张卡 fact → interpretation → uncertainty → evidence →
  implication。fact 只含真实计数；interpretation 是定性档位（不用分数）；
  uncertainty 如实声明样本与"相关非因果"；evidence 携带应用内深链；
  implication 指向可行动面。
- **假精确红线（M-10 口径）**：不输出 confidence/rate/score/百分比族——
  定性词与计数替代；文案组合在移动端 l10n 完成（本服务只出结构化字段）。
- **无数据不生成结论**：窗口内零证据 → 不出卡，更不生成人格结论。
- **纠正即更新**：卡片是每次请求从真源现算的派生视图，不落陈旧快照；
  纠正/新事实（完成任务、反馈干预、关联 outcome）落库后的下一次读取
  如实反映。

V4-D05 呈现契约（``insight.presentation.v1``，全部出口过门）：
- **夸大表述门**（``exaggeration_gate``）：每张卡出面前过 M-06 因果断言扫描
  + 数值面（因果/成效措辞×百分比、部分关联子集上的百分比）——违例卡整体
  扣下并进 ``meta.presentation_gate_dropped``（响亮失败，不静默改写）；
- **样本量先去重**（D02-R1 C-3 消费方义务）：呈现侧样本量按
  ``attr_<sha256[:32]>`` 样本身份先行去重——重放投递如实计 raw、永不放大
  样本量（``uncertainty.duplicate_outcome_samples_dropped`` 审计可见）；
- **单主建议信封**（``next_step``）：一条观察 ≤ 一个主建议；``user_can_reject``
  恒 True、``reject_penalty`` 恒 "none"（拒绝路径真实存在且零惩罚）；
- **理解宣称门**（``understanding``）：无数据/有 missing+censored 不出
  「充分理解」（``claim_allowed=False`` + 封闭理由，档位定性）；
- **回访记录**（``data.revisit``）：上次建议是否相关由真实事件证明
  （响应类型 + 去重后链接 outcome 样本身份），无事件不出回访、不套模板。

V4-U13 撤回排除显式在册（消费 D05 契约 ``exclude_withdrawn_refs`` 唯一权威）：
- 已删除/撤回的来源记录（软删 lifecycle 事件、软删任务）按精确身份从呈现
  引用中排除（查询本就过滤），排除**计数**以
  ``uncertainty.withdrawn_refs_excluded`` 如实随行——撤回不是静默消失，
  读面可分呈现「无数据/证据不足/已撤回排除」三态；计数不改任何 fact 分子
  分母（真源口径零改动）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.insight_presentation import (
    REASON_NO_DATA_NO_CLAIM,
    SampleDedup,
    build_revisit_record,
    build_suggestion_envelope,
    exaggeration_gate,
    exclude_withdrawn_refs,
    presentation_sample_id,
    understanding_claim_gate,
)
from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_INSUFFICIENT,
    LifecycleEventType,
    SliceSummary,
    resolve_observation_status,
)
from app.models.goal import Goal
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.intervention_lifecycle_service import InterventionLifecycleService

#: 五要素卡契约版本不变（v1：fact/interpretation/uncertainty/evidence/implication
#: 结构与既有消费面向后兼容）；V4-D05 呈现契约增量以 payload 根级
#: ``presentation_schema: insight.presentation.v1`` 独立版本化（附加字段：
#: next_step/understanding/revisit）。
_SCHEMA_VERSION = "insights.evidence_cards.v1"
_DEFAULT_WINDOW_DAYS = 30
_EVIDENCE_REF_CAP = 5

#: 呈现侧样本量只认方向观察（与 D-05 ``SliceSummary.n_observed`` 同口径：
#: positive/negative；neutral/censored/unknown 永不进样本量）。
_DIRECTIONAL_POLARITIES = ("positive", "negative")

#: 呈现层深链（应用内路由；与 mobile/lib/features/insights/insights_routes.dart
#: 和 goal 路由对齐）。
_DIRECTIVE_AUDIT_LINK = "/learning/insights/directives"

_RESPONSE_EVENT_TYPES = (
    LifecycleEventType.ACCEPTED.value,
    LifecycleEventType.EDITED.value,
    LifecycleEventType.REJECTED.value,
    LifecycleEventType.STARTED.value,
)

#: 无任何证据时的诚实空态（含不生成人格结论的口径声明）。
_EMPTY_NOTE = (
    "no evidence in window: no friction exposures, no observed intervention "
    "outcomes, no active goal with a task ledger; no interpretation or persona "
    "conclusions generated without data"
)

#: 洞察卡的定性理解档（V4-D05：无数据/有 missing+censored 不出「充分理解」；
#: 档位由 understanding_claim_gate 判定，文案组合在移动端 l10n 完成）。
_UNDERSTANDING_BAND_ALLOWED = "qualitative_only"
_UNDERSTANDING_BAND_INCOMPLETE = "incomplete_evidence"
_UNDERSTANDING_BAND_NO_DATA = "no_data"


class EvidenceInsightService:
    """把已交付真源投影成五要素洞察卡（只读、零写入、零 LLM）。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_cards(
        self,
        *,
        user_id: UUID | str,
        window_days: int = _DEFAULT_WINDOW_DAYS,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        now_naive = (now or datetime.utcnow()).replace(tzinfo=None)
        since = now_naive - timedelta(days=window_days)

        cards: list[dict[str, Any]] = []
        cards.extend(await self._friction_pattern_cards(user_id=UUID(str(user_id)), since=since))
        cards.extend(
            await self._interventions_that_helped_cards(user_id=UUID(str(user_id)), since=since, now_naive=now_naive)
        )
        cards.extend(await self._goal_progress_cards(user_id=UUID(str(user_id))))

        # V4-D05 夸大表述门：每张卡出面前过门（M-06 因果断言扫描 + 数值面）。
        # 违例卡整体扣下并显式登记（响亮失败，不静默改写、不静默丢弃）。
        final_cards: list[dict[str, Any]] = []
        gate_dropped: list[dict[str, Any]] = []
        for card in cards:
            verdict = exaggeration_gate(
                card,
                n_linked=self._card_linked_count(card),
                n_denominator=self._card_denominator_count(card),
            )
            if not verdict.allowed:
                gate_dropped.append({"id": card.get("id"), "reasons": list(verdict.reasons)})
                continue
            # 单主建议信封：一条观察 ≤ 一个主建议；拒绝路径恒存在且零惩罚。
            card["next_step"] = build_suggestion_envelope(
                observation_id=str(card.get("id", "")),
                candidates=[card["implication"]],
            ).to_dict()
            # 理解宣称门：无数据/有 missing+censored 不出「充分理解」。
            card["understanding"] = self._understanding_block(card)
            final_cards.append(card)

        revisit = await self._build_revisit(user_id=UUID(str(user_id)), since=since, now_naive=now_naive)

        payload: dict[str, Any] = {
            "cards": final_cards,
            "window_days": window_days,
            "generated_at": now_naive.isoformat(),
            "revisit": revisit.to_dict(),
            "presentation_schema": "insight.presentation.v1",
        }
        meta: dict[str, Any] = {"schema_version": _SCHEMA_VERSION}
        if not final_cards:
            meta["note"] = _EMPTY_NOTE
        if gate_dropped:
            meta["presentation_gate_dropped"] = gate_dropped
        return {"data": payload, "meta": meta}

    # ------------------------------------------------------------------
    # V4-D05 呈现契约辅助（门参数、理解档、回访）
    # ------------------------------------------------------------------

    @staticmethod
    def _card_linked_count(card: dict[str, Any]) -> int:
        """卡的「已关联」分子（夸大表述门的部分关联检查用）。"""
        kind = card.get("kind")
        fact = card.get("fact") or {}
        if kind == "friction_pattern":
            return int(fact.get("accepted", 0)) + int(fact.get("edited", 0)) + int(fact.get("rejected", 0))
        if kind == "interventions_that_helped":
            return int(fact.get("n_observed", 0))
        if kind == "goal_progress":
            return int((fact.get("ledger") or {}).get("completed", 0))
        return 0

    @staticmethod
    def _card_denominator_count(card: dict[str, Any]) -> int:
        """卡的公开分母（三例只有两例关联 → 分母 3 必须随行）。"""
        kind = card.get("kind")
        fact = card.get("fact") or {}
        uncertainty = card.get("uncertainty") or {}
        if kind == "friction_pattern":
            return int(fact.get("exposures", 0))
        if kind == "interventions_that_helped":
            return int(fact.get("n_exposed", 0))
        if kind == "goal_progress":
            return int(uncertainty.get("samples", 0))
        return 0

    @staticmethod
    def _understanding_block(card: dict[str, Any]) -> dict[str, Any]:
        """理解宣称门出口（结构化档位 + 封闭理由；本服务任何档位都不产理解宣称文案）。"""
        uncertainty = card.get("uncertainty") or {}
        samples = int(uncertainty.get("samples", 0) or 0)
        missing = int(uncertainty.get("not_determinable", 0) or 0) + int(uncertainty.get("n_unknown", 0) or 0)
        censored = int(uncertainty.get("not_yet_observed", 0) or 0) + int(uncertainty.get("censored_total", 0) or 0)
        verdict = understanding_claim_gate(samples=samples, missing=missing, censored=censored)
        if not verdict.allowed:
            band = (
                _UNDERSTANDING_BAND_NO_DATA
                if REASON_NO_DATA_NO_CLAIM in verdict.reasons
                else _UNDERSTANDING_BAND_INCOMPLETE
            )
        else:
            band = _UNDERSTANDING_BAND_ALLOWED
        return {
            "claim_allowed": verdict.allowed,
            "band": band,
            "reasons": list(verdict.reasons),
            "samples": samples,
            "missing": missing,
            "censored": censored,
        }

    async def _build_revisit(self, *, user_id: UUID, since: datetime, now_naive: datetime) -> Any:
        """回访记录：上次建议（窗口内最近一次 exposure）是否相关的真实事件证明。

        无 exposure → ``no_prior_suggestion``（不编造回访）；判定消费 D-05
        ``resolve_observation_status``（窗口/删失唯一权威）+ 呈现侧样本身份去重。
        """
        exposure = (
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent)
                    .where(
                        and_(
                            InterventionLifecycleEvent.not_deleted_filter(),
                            InterventionLifecycleEvent.user_id == user_id,
                            InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                            InterventionLifecycleEvent.occurred_at >= since,
                        )
                    )
                    .order_by(InterventionLifecycleEvent.occurred_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if exposure is None:
            return build_revisit_record(
                decision_id="",
                intervention_type="",
                friction_tag="",
                shown_at=None,
                response=None,
                outcome_ids=(),
                observation_status=None,
            )

        rows = list(
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent).where(
                        and_(
                            InterventionLifecycleEvent.not_deleted_filter(),
                            InterventionLifecycleEvent.user_id == user_id,
                            InterventionLifecycleEvent.decision_id == exposure.decision_id,
                            InterventionLifecycleEvent.event_type != LifecycleEventType.EXPOSED.value,
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        response_rows = [r for r in rows if r.event_type in _RESPONSE_EVENT_TYPES]
        # 拒绝是用户的一等决定（最高优先）；否则取最近一次响应。
        rejected = [r for r in response_rows if r.event_type == LifecycleEventType.REJECTED.value]
        response: str | None
        if rejected:
            response = LifecycleEventType.REJECTED.value
        else:
            response = max(response_rows, key=lambda r: r.occurred_at).event_type if response_rows else None
        outcome_ids = [
            r.outcome_ref for r in rows if r.event_type == LifecycleEventType.OUTCOME_OBSERVED.value and r.outcome_ref
        ]

        user_last_active = await self._resolve_last_active(user_id)
        observation = resolve_observation_status(
            exposed_at=exposure.occurred_at,
            window_hours=InterventionLifecycleService._window_hours_of(exposure),
            outcome_times=[r.occurred_at for r in rows if r.event_type == LifecycleEventType.OUTCOME_OBSERVED.value],
            now=now_naive,
            user_last_active_at=user_last_active,
        )
        return build_revisit_record(
            decision_id=exposure.decision_id,
            intervention_type=exposure.intervention_type,
            friction_tag=exposure.friction_tag or "unattributed",
            shown_at=exposure.occurred_at,
            response=response,
            outcome_ids=outcome_ids,
            observation_status=observation,
        )

    async def _resolve_last_active(self, user_id: UUID) -> datetime | None:
        """活跃面解析（D-05 ``_resolve_last_active`` 同源：users.last_login_at）。"""
        row = (await self.db.execute(select(User.last_login_at).where(User.id == user_id))).first()
        value: datetime | None = row[0] if row else None
        if value is None:
            return None
        return value.replace(tzinfo=None) if value.tzinfo is None else value

    # ------------------------------------------------------------------
    # ① friction pattern——D-05 lifecycle 事件表按 friction_tag 聚合
    # ------------------------------------------------------------------
    async def _withdrawn_exposure_ids_by_tag(self, *, user_id: UUID, since: datetime) -> dict[str, list[str]]:
        """窗口内已删除/撤回 exposure 的 decision_id 按 friction_tag 分组。

        软删行不进任何 fact 计数（``not_deleted_filter`` 既有权威），这里只取
        其身份供 D05 契约 ``exclude_withdrawn_refs`` 做精确身份过滤与排除计数
        （撤回排除显式在册）；不复活、不连坐。
        """
        rows = (
            await self.db.execute(
                select(
                    InterventionLifecycleEvent.friction_tag,
                    InterventionLifecycleEvent.decision_id,
                ).where(
                    and_(
                        InterventionLifecycleEvent.user_id == user_id,
                        InterventionLifecycleEvent.occurred_at >= since,
                        InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                        InterventionLifecycleEvent.deleted_at.is_not(None),
                    )
                )
            )
        ).all()
        grouped: dict[str, list[str]] = {}
        for tag, decision_id in rows:
            grouped.setdefault(str(tag or "unattributed"), []).append(str(decision_id))
        return grouped

    async def _friction_pattern_cards(self, *, user_id: UUID, since: datetime) -> list[dict[str, Any]]:
        rows = list(
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent).where(
                        and_(
                            InterventionLifecycleEvent.not_deleted_filter(),
                            InterventionLifecycleEvent.user_id == user_id,
                            InterventionLifecycleEvent.occurred_at >= since,
                            InterventionLifecycleEvent.friction_tag != "unattributed",
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        exposures_by_tag: dict[str, list[InterventionLifecycleEvent]] = {}
        responses_by_tag: dict[str, dict[str, int]] = {}
        for row in rows:
            tag = row.friction_tag or "unattributed"
            if row.event_type == LifecycleEventType.EXPOSED.value:
                exposures_by_tag.setdefault(tag, []).append(row)
            elif row.event_type in _RESPONSE_EVENT_TYPES:
                bucket = responses_by_tag.setdefault(tag, {})
                bucket[row.event_type] = bucket.get(row.event_type, 0) + 1

        if not exposures_by_tag:
            return []

        ranked = sorted(exposures_by_tag.items(), key=lambda item: (-len(item[1]), item[0]))
        most_frequent_tag = ranked[0][0] if len(ranked) > 1 and len(ranked[0][1]) >= 2 else None

        cards: list[dict[str, Any]] = []
        withdrawn_by_tag = await self._withdrawn_exposure_ids_by_tag(user_id=user_id, since=since)
        for tag, exposures in ranked:
            responses = responses_by_tag.get(tag, {})
            qualifiers = ["counts_only_from_lifecycle_events"]
            if len(exposures) < 3:
                qualifiers.append("small_sample")
            decision_refs = [exposure.decision_id for exposure in exposures[:_EVIDENCE_REF_CAP]]
            # V4-U13 撤回排除显式在册：候选引用过 D05 契约精确身份过滤
            # （查询窗口与软删读之间若发生删除竞态，被撤回身份在此确定性
            # 落入 excluded，绝不进呈现引用）。
            filtered_refs = exclude_withdrawn_refs(decision_refs, withdrawn_by_tag.get(tag, []))
            withdrawn_excluded = len(withdrawn_by_tag.get(tag, []))
            interpretation: dict[str, Any] = {"friction_tag": tag}
            interpretation["role"] = "most_frequent" if most_frequent_tag == tag else "observed"
            cards.append(
                {
                    "id": f"friction_pattern:{tag}",
                    "kind": "friction_pattern",
                    "fact": {
                        "friction_tag": tag,
                        "exposures": len(exposures),
                        "accepted": responses.get(LifecycleEventType.ACCEPTED.value, 0),
                        "edited": responses.get(LifecycleEventType.EDITED.value, 0),
                        "rejected": responses.get(LifecycleEventType.REJECTED.value, 0),
                    },
                    "interpretation": interpretation,
                    "uncertainty": {
                        "qualifiers": qualifiers,
                        "samples": len(exposures),
                        # V4-U13 撤回排除显式在册（真实计数；不改 fact 分子分母）。
                        "withdrawn_refs_excluded": withdrawn_excluded,
                    },
                    "evidence": [
                        {
                            "label_key": "evidence_directive_log",
                            "deep_link": _DIRECTIVE_AUDIT_LINK,
                            "refs": filtered_refs.kept,
                        }
                    ],
                    "implication": {
                        "action_key": "review_directives",
                        "deep_link": _DIRECTIVE_AUDIT_LINK,
                    },
                }
            )
        return cards

    # ------------------------------------------------------------------
    # ② interventions that helped——D-05 association_summary 保守关联摘要
    # ------------------------------------------------------------------
    async def _interventions_that_helped_cards(
        self, *, user_id: UUID, since: datetime, now_naive: datetime
    ) -> list[dict[str, Any]]:
        lifecycle = InterventionLifecycleService(self.db)
        summary = await lifecycle.association_summary(user_id=user_id, since=since, now=now_naive)
        # D02-R1 C-3 呈现侧义务：样本量按样本身份先行去重（重放投递只如实计
        # raw，永不放大去重后样本量）。
        directional_by_signature = await self._directional_outcome_rows(user_id=user_id, since=since)
        withdrawn_by_signature = await self._withdrawn_exposure_ids_by_signature(user_id=user_id, since=since)
        cards: list[dict[str, Any]] = []
        for slice_summary in summary.slices:
            # 证据不足的切片不发"有帮助"结论（无证据不做断言）。
            if slice_summary.evidence_strength == EVIDENCE_TIER_INSUFFICIENT or slice_summary.n_positive <= 0:
                continue
            signature = slice_summary.signature
            refs = await self._decision_refs_for_signature(user_id=user_id, since=since, slice_summary=slice_summary)
            # V4-U13 撤回排除显式在册：候选引用过 D05 契约精确身份过滤
            # （查询窗口与软删读之间若发生删除竞态，被撤回身份在此确定性
            # 落入 excluded，绝不进呈现引用）。
            filtered_refs = exclude_withdrawn_refs(
                refs,
                withdrawn_by_signature.get(
                    (signature.intervention_type, signature.friction_tag),
                    [],
                ),
            )
            qualifiers = ["correlation_not_causation", "counts_only_from_lifecycle_events"]
            if slice_summary.n_observed < 3:
                qualifiers.append("small_sample")
            # 呈现侧样本量 = 去重后的方向观察（D02-R1 C-3）。
            outcome_rows = directional_by_signature.get((signature.intervention_type, signature.friction_tag), [])
            dedup = self._dedupe_slice_samples(outcome_rows)
            if dedup.duplicates_dropped > 0:
                qualifiers.append("replayed_deliveries_excluded_from_sample")
            censored_not_due = slice_summary.n_censored_not_yet_due
            # V3-FIX-357-A：删失语义拆分（D-05「censored/unknown 语义明确区分」
            # 验收①的呈现面落地）——只有 not_yet_due 才是「结果未到期」；
            # 窗口已关/用户流失/无法判定合并进 not_determinable（诚实口径：
            # 这些暴露不会产生可判定结果，不得伪装成「还没到期」）。
            # 三桶加总：窗口已关 + 用户流失 + 无法判定（与 SliceSummary 删失字段一一对应）。
            not_determinable = (
                slice_summary.n_censored_window_closed + slice_summary.n_censored_user_churned + slice_summary.n_unknown
            )
            cards.append(
                {
                    "id": (f"interventions_that_helped:{signature.intervention_type}" f":{signature.friction_tag}"),
                    "kind": "interventions_that_helped",
                    "fact": {
                        "intervention_type": signature.intervention_type,
                        "friction_tag": signature.friction_tag,
                        "n_exposed": slice_summary.n_exposed,
                        "n_accepted": slice_summary.n_accepted,
                        "n_observed": slice_summary.n_observed,
                        "n_positive": slice_summary.n_positive,
                        "n_negative": slice_summary.n_negative,
                    },
                    "interpretation": {
                        # 定性证据档（D-05 原样），不是分数。
                        "evidence_strength": slice_summary.evidence_strength,
                        "direction": "positive_association",
                        "causal": bool(slice_summary.causal_claim),
                    },
                    "uncertainty": {
                        "qualifiers": qualifiers,
                        # 呈现侧样本量 = 按样本身份去重后的方向观察数
                        # （重放投递如实计 raw，不进样本量）。
                        "samples": dedup.n_unique,
                        "outcome_samples_raw": dedup.n_raw,
                        "duplicate_outcome_samples_dropped": dedup.duplicates_dropped,
                        "not_yet_observed": censored_not_due,
                        "not_determinable": not_determinable,
                        # V4-U13 撤回排除显式在册（真实计数；不改 fact 分子分母）。
                        "withdrawn_refs_excluded": len(
                            withdrawn_by_signature.get(
                                (signature.intervention_type, signature.friction_tag),
                                [],
                            )
                        ),
                    },
                    "evidence": [
                        {
                            "label_key": "evidence_directive_log",
                            "deep_link": _DIRECTIVE_AUDIT_LINK,
                            "refs": filtered_refs.kept,
                        }
                    ],
                    "implication": {
                        "action_key": (
                            "keep_observing"
                            if slice_summary.evidence_strength == "single_observation"
                            else "review_directives"
                        ),
                        "deep_link": _DIRECTIVE_AUDIT_LINK,
                    },
                }
            )
        return cards

    async def _withdrawn_exposure_ids_by_signature(
        self, *, user_id: UUID, since: datetime
    ) -> dict[tuple[str, str], list[str]]:
        """窗口内已删除/撤回 exposure 的 decision_id 按 (type, tag) 分组（撤回排除源）。"""
        rows = (
            await self.db.execute(
                select(
                    InterventionLifecycleEvent.intervention_type,
                    InterventionLifecycleEvent.friction_tag,
                    InterventionLifecycleEvent.decision_id,
                ).where(
                    and_(
                        InterventionLifecycleEvent.user_id == user_id,
                        InterventionLifecycleEvent.occurred_at >= since,
                        InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                        InterventionLifecycleEvent.deleted_at.is_not(None),
                    )
                )
            )
        ).all()
        grouped: dict[tuple[str, str], list[str]] = {}
        for intervention_type, friction_tag, decision_id in rows:
            key = (str(intervention_type), str(friction_tag or "unattributed"))
            grouped.setdefault(key, []).append(str(decision_id))
        return grouped

    async def _directional_outcome_rows(
        self, *, user_id: UUID, since: datetime
    ) -> dict[tuple[str, str], list[InterventionLifecycleEvent]]:
        """窗口内方向观察行按 (intervention_type, friction_tag) 分组（呈现侧去重源）。"""
        rows = list(
            (
                await self.db.execute(
                    select(InterventionLifecycleEvent).where(
                        and_(
                            InterventionLifecycleEvent.not_deleted_filter(),
                            InterventionLifecycleEvent.user_id == user_id,
                            InterventionLifecycleEvent.occurred_at >= since,
                            InterventionLifecycleEvent.event_type == LifecycleEventType.OUTCOME_OBSERVED.value,
                            InterventionLifecycleEvent.outcome_polarity.in_(_DIRECTIONAL_POLARITIES),
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        grouped: dict[tuple[str, str], list[InterventionLifecycleEvent]] = {}
        for row in rows:
            grouped.setdefault((row.intervention_type, row.friction_tag or "unattributed"), []).append(row)
        return grouped

    @staticmethod
    def _dedupe_slice_samples(rows: list[InterventionLifecycleEvent]) -> SampleDedup:
        """方向观察行 → 按 (decision_id, outcome_ref) 样本身份去重（``attr_<sha256[:32]>``）。

        同一 decision 的重放投递恒产同样本身份（去重）；不同 decision 链接同一
        outcome 是两条真实链接（不去重）。
        """
        seen: set[str] = set()
        raw = 0
        for row in rows:
            if not row.outcome_ref:
                continue
            raw += 1
            seen.add(presentation_sample_id(decision_id=row.decision_id, outcome_id=row.outcome_ref))
        return SampleDedup(
            n_raw=raw,
            n_unique=len(seen),
            unique_sample_ids=tuple(sorted(seen)),
            duplicates_dropped=max(0, raw - len(seen)),
        )

    async def _decision_refs_for_signature(
        self, *, user_id: UUID, since: datetime, slice_summary: SliceSummary
    ) -> list[str]:
        signature = slice_summary.signature
        rows = (
            await self.db.execute(
                select(InterventionLifecycleEvent.decision_id)
                .where(
                    and_(
                        InterventionLifecycleEvent.not_deleted_filter(),
                        InterventionLifecycleEvent.user_id == user_id,
                        InterventionLifecycleEvent.occurred_at >= since,
                        InterventionLifecycleEvent.event_type == LifecycleEventType.EXPOSED.value,
                        InterventionLifecycleEvent.intervention_type == signature.intervention_type,
                        InterventionLifecycleEvent.goal_type == signature.goal_type,
                        InterventionLifecycleEvent.friction_tag == signature.friction_tag,
                    )
                )
                .limit(_EVIDENCE_REF_CAP)
            )
        ).all()
        return [row[0] for row in rows]

    # ------------------------------------------------------------------
    # ③ goal progress——Goal/Task 真源读侧投影（A-07 同款双口径）
    # ------------------------------------------------------------------
    async def _goal_progress_cards(self, *, user_id: UUID) -> list[dict[str, Any]]:
        goal = await self._primary_active_goal(user_id)
        if goal is None:
            return []

        total_result = await self.db.execute(
            select(func.count()).select_from(Task).where(and_(Task.plan_id == goal.plan_id, Task.deleted_at.is_(None)))
        )
        done_result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(
                and_(
                    Task.plan_id == goal.plan_id,
                    Task.deleted_at.is_(None),
                    Task.status == TaskStatus.COMPLETED,
                )
            )
        )
        # V4-U13 撤回排除显式在册：已删除/撤回的任务记录不进账本（既有权威），
        # 其计数如实随行——读面可声明「已排除 N 条」，而非静默消失。
        withdrawn_result = await self.db.execute(
            select(func.count())
            .select_from(Task)
            .where(and_(Task.plan_id == goal.plan_id, Task.deleted_at.is_not(None)))
        )
        withdrawn_tasks = int(withdrawn_result.scalar() or 0)
        total = int(total_result.scalar() or 0)
        completed = int(done_result.scalar() or 0)

        progress_column = getattr(goal, "progress", None)
        progress_value = float(progress_column) if isinstance(progress_column, (int, float)) else None

        fact: dict[str, Any] = {
            "goal_id": str(goal.id),
            "title": (goal.title or "").strip(),
            "status": (goal.status or "active").strip(),
            "ledger": {"completed": completed, "total": total},
            # 真源 progress 列读数原样上报（可能是 0），不做修饰。
            "progress_column": progress_value,
        }

        qualifiers = ["task_ledger_is_honest_progress"]
        band = "no_task_evidence"
        if total > 0:
            ratio = completed / total
            if completed >= total:
                band = "all_complete"
            elif ratio >= 0.8:
                band = "nearly_done"
            elif ratio >= 0.34:
                band = "in_progress"
            else:
                band = "just_started"
            if progress_value is not None and abs(progress_value - ratio) > 0.05:
                # progress 列与账本口径漂移：如实声明，不互相篡改（R2-A）。
                qualifiers.append("progress_column_may_lag_ledger")
        else:
            qualifiers.append("no_task_ledger")

        goal_link = f"/goals/{goal.id}"
        return [
            {
                "id": f"goal_progress:{goal.id}",
                "kind": "goal_progress",
                "fact": fact,
                "interpretation": {"band": band},
                "uncertainty": {
                    "qualifiers": qualifiers,
                    "samples": total,
                    # V4-U13 撤回排除显式在册（真实计数；不改账本口径）。
                    "withdrawn_refs_excluded": withdrawn_tasks,
                },
                "evidence": [
                    {
                        "label_key": "evidence_goal_ledger",
                        "deep_link": goal_link,
                        "refs": [str(goal.id)],
                    }
                ],
                "implication": {"action_key": "open_goal", "deep_link": goal_link},
            }
        ]

    async def _primary_active_goal(self, user_id: UUID) -> Goal | None:
        stmt = (
            select(Goal)
            .where(and_(Goal.user_id == user_id, Goal.status == "active"))
            .order_by(Goal.is_primary.desc(), Goal.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


__all__ = ["EvidenceInsightService"]
