"""Evidence-driven insight cards（D-07）——洞察呈现层的派生真源投影。

设计纪律（卡 D-07 / Forbidden）：
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
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.intervention_lifecycle import (
    EVIDENCE_TIER_INSUFFICIENT,
    LifecycleEventType,
    SliceSummary,
)
from app.models.goal import Goal
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.task import Task, TaskStatus
from app.services.intervention_lifecycle_service import InterventionLifecycleService

_SCHEMA_VERSION = "insights.evidence_cards.v1"
_DEFAULT_WINDOW_DAYS = 30
_EVIDENCE_REF_CAP = 5

#: 呈现层深链（应用内路由；与 mobile/lib/features/insights/insights_routes.dart
#: 和 goal 路由对齐）。
_DIRECTIVE_AUDIT_LINK = "/learning/insights/directives"

_RESPONSE_EVENT_TYPES = (
    LifecycleEventType.ACCEPTED.value,
    LifecycleEventType.EDITED.value,
    LifecycleEventType.REJECTED.value,
)

#: 无任何证据时的诚实空态（含不生成人格结论的口径声明）。
_EMPTY_NOTE = (
    "no evidence in window: no friction exposures, no observed intervention "
    "outcomes, no active goal with a task ledger; no interpretation or persona "
    "conclusions generated without data"
)


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
        cards.extend(
            await self._friction_pattern_cards(user_id=UUID(str(user_id)), since=since)
        )
        cards.extend(
            await self._interventions_that_helped_cards(
                user_id=UUID(str(user_id)), since=since, now_naive=now_naive
            )
        )
        cards.extend(await self._goal_progress_cards(user_id=UUID(str(user_id))))

        payload: dict[str, Any] = {
            "cards": cards,
            "window_days": window_days,
            "generated_at": now_naive.isoformat(),
        }
        meta: dict[str, Any] = {"schema_version": _SCHEMA_VERSION}
        if not cards:
            meta["note"] = _EMPTY_NOTE
        return {"data": payload, "meta": meta}

    # ------------------------------------------------------------------
    # ① friction pattern——D-05 lifecycle 事件表按 friction_tag 聚合
    # ------------------------------------------------------------------
    async def _friction_pattern_cards(
        self, *, user_id: UUID, since: datetime
    ) -> list[dict[str, Any]]:
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

        ranked = sorted(
            exposures_by_tag.items(), key=lambda item: (-len(item[1]), item[0])
        )
        most_frequent_tag = ranked[0][0] if len(ranked) > 1 and len(ranked[0][1]) >= 2 else None

        cards: list[dict[str, Any]] = []
        for tag, exposures in ranked:
            responses = responses_by_tag.get(tag, {})
            qualifiers = ["counts_only_from_lifecycle_events"]
            if len(exposures) < 3:
                qualifiers.append("small_sample")
            decision_refs = [
                exposure.decision_id for exposure in exposures[:_EVIDENCE_REF_CAP]
            ]
            interpretation: dict[str, Any] = {"friction_tag": tag}
            interpretation["role"] = (
                "most_frequent" if most_frequent_tag == tag else "observed"
            )
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
                    },
                    "evidence": [
                        {
                            "label_key": "evidence_directive_log",
                            "deep_link": _DIRECTIVE_AUDIT_LINK,
                            "refs": decision_refs,
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
        summary = await lifecycle.association_summary(
            user_id=user_id, since=since, now=now_naive
        )
        cards: list[dict[str, Any]] = []
        for slice_summary in summary.slices:
            # 证据不足的切片不发"有帮助"结论（无证据不做断言）。
            if (
                slice_summary.evidence_strength == EVIDENCE_TIER_INSUFFICIENT
                or slice_summary.n_positive <= 0
            ):
                continue
            signature = slice_summary.signature
            refs = await self._decision_refs_for_signature(
                user_id=user_id, since=since, slice_summary=slice_summary
            )
            qualifiers = ["correlation_not_causation", "counts_only_from_lifecycle_events"]
            if slice_summary.n_observed < 3:
                qualifiers.append("small_sample")
            censored = (
                slice_summary.n_censored_not_yet_due
                + slice_summary.n_censored_window_closed
                + slice_summary.n_censored_user_churned
                + slice_summary.n_unknown
            )
            cards.append(
                {
                    "id": (
                        f"interventions_that_helped:{signature.intervention_type}"
                        f":{signature.friction_tag}"
                    ),
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
                        "samples": slice_summary.n_observed,
                        "not_yet_observed": censored,
                    },
                    "evidence": [
                        {
                            "label_key": "evidence_directive_log",
                            "deep_link": _DIRECTIVE_AUDIT_LINK,
                            "refs": refs,
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
                        InterventionLifecycleEvent.event_type
                        == LifecycleEventType.EXPOSED.value,
                        InterventionLifecycleEvent.intervention_type
                        == signature.intervention_type,
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
            select(func.count())
            .select_from(Task)
            .where(and_(Task.plan_id == goal.plan_id, Task.deleted_at.is_(None)))
        )
        done_result = await self.db.execute(
            select(func.count())
            .select_from(Task).where(
                and_(
                    Task.plan_id == goal.plan_id,
                    Task.deleted_at.is_(None),
                    Task.status == TaskStatus.COMPLETED,
                )
            )
        )
        total = int(total_result.scalar() or 0)
        completed = int(done_result.scalar() or 0)

        progress_column = getattr(goal, "progress", None)
        progress_value = (
            float(progress_column) if isinstance(progress_column, (int, float)) else None
        )

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
