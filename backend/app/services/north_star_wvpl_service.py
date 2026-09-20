"""D-06 · WVPL 北极星查询服务 —— 纯确定性聚合，零模型参与（事实 JSON 工厂）。

形态（契约 = ``app/core/north_star_wvpl.py``，口径 v1）：
- **只读查询层**：不建表、不写库、不发迁移；真源是 D-02 outcome ledger 五源读
  模型（本服务经其**公开 API** ``query``/``count_by_source`` 消费，分级零重复
  实现）+ D-05 intervention lifecycle + 既有 chat/context_pack 生产表。
- **不让模型计算数字（卡面灵魂）**：全部数字由 SQL 聚合 + Python 确定性运算
  产生；模块不 import 任何 LLM/agent 基础设施（tests/golden 有 pin 断守卫）。
  LLM 只允许在消费端**解释**本服务产出的事实 JSON。
- **幂等可重复**：``build_fact(as_of=...)`` 以 as_of 为锚点——同一 as_of + 同一
  库态 → 逐字节相同的事实 JSON（golden 钉死）。``generated_at`` 是唯一墙钟
  字段，独立于确定性面（调用方可注入冻结值做逐字节比对）。
- **可审计**：每个数字 = 口径（FACT_DEFINITIONS 随 JSON 输出）+ 源查询
  （provenance.source_queries）+ 事件溯源（loops.sample_event_ids 携带
  D-02 ``derive_outcome_id`` 幂等 outcome_id 与 task/plan/goal ref）。
- **有界扫描**：``MAX_ACTIVE_USERS_PER_RUN`` / ``MAX_LEDGER_PAGES_PER_USER``
  硬顶；触顶事实 JSON 如实 ``truncated=true``（绝不静默截断）。

与 D-02 的谓词一致性策略：五源 standalone 谓词在此处仅为「fleet 级 distinct
user 发现」而重述（per-user 计数一律走 D-02 公开 API，零漂移）；谓词只引用
D-02 冻结导出常量（``ECHO_STUDY_RECORD_TYPES`` / ``QUIZ_FEEDBACK_SOURCES`` /
``EXCLUDED_COHORT_REGISTRATION_SOURCES`` / 各枚举），不复制字面值；tests 有
词表一致 pin。
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.north_star_wvpl import (
    FACT_DEFINITIONS,
    GOAL_STALL_THRESHOLD_DAYS,
    MAX_ACTIVE_USERS_PER_RUN,
    MAX_LEDGER_PAGES_PER_USER,
    MAX_LOOP_SAMPLES,
    SOURCE_QUERIES,
    WINDOW_DAYS,
    WVPL_CALIBER_VERSION,
    WVPL_FACT_SCHEMA,
)
from app.core.outcome_ledger import (
    ECHO_STUDY_RECORD_TYPES,
    OUTCOME_LEDGER_SCHEMA_VERSION,
    QUIZ_FEEDBACK_SOURCES,
    OutcomeSource,
    TruthClass,
    derive_outcome_id,
)
from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import ExpansionFeedback, StudyRecord
from app.models.intervention_adaptive import BehavioralOutcome
from app.models.intervention_lifecycle import InterventionLifecycleEvent
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.outcome_ledger_service import EXCLUDED_COHORT_REGISTRATION_SOURCES, OutcomeLedgerService

_LEDGER_PAGE_SIZE = 200  # D-02 _MAX_LIMIT
_STATE_LEG_CHUNK = 500
_LIFECYCLE_KNOWN_MODES = ("human", "agent", "hybrid")

_TRUTH_ORDER = (
    TruthClass.ACTUAL,
    TruthClass.SELF_REPORTED,
    TruthClass.ESTIMATED,
    TruthClass.DEMO,
    TruthClass.UNKNOWN,
)


@dataclass(frozen=True)
class _LoopFact:
    """一个去重后的 loop（窗口内或全史有界集）；身份 = (task_completion, task_id)。"""

    user_id: str
    task_id: str
    plan_id: str | None
    goal_id: str | None
    occurred_at: datetime
    evidence_kinds: tuple[str, ...]

    @property
    def outcome_id(self) -> str:
        return derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=self.task_id)


def _naive_utc(value: datetime) -> datetime:
    """aware → naive UTC；naive 原样（仓库 naive-UTC 规范）。"""
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _iso(value: datetime) -> str:
    return _naive_utc(value).isoformat()


def _ratio(numerator: float, denominator: float) -> float | None:
    """比率；分母 0 → None（没有分母不伪造比率，D-02 truth_coverage 同语义）。"""
    if not denominator:
        return None
    return round(float(numerator) / float(denominator), 4)


def _median_days(values: list[float]) -> float | None:
    if not values:
        return None
    return round(float(statistics.median(values)), 4)


class NorthStarWvplService:
    """WVPL 北极星事实 JSON 查询服务（只读、确定性、有界）。"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._ledger = OutcomeLedgerService(db)

    # ------------------------------------------------------------------
    # 对外唯一入口
    # ------------------------------------------------------------------

    async def build_fact(
        self,
        *,
        as_of: datetime | None = None,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        """产出事实 JSON（dict；``canonical_fact_json`` 负责逐字节稳定序列化）。

        as_of 缺省取当前墙钟（生产语义）；幂等复跑/测试必须显式传 as_of。
        generated_at 是 provenance 墙钟，缺省取当前墙钟；确定性比对时注入冻结值。
        """
        resolved_as_of = _naive_utc(as_of) if as_of is not None else _naive_utc(datetime.utcnow())
        generated = _naive_utc(generated_at) if generated_at is not None else _naive_utc(datetime.utcnow())
        end = resolved_as_of
        start = end - timedelta(days=WINDOW_DAYS)

        # -- cohort -------------------------------------------------------
        seed_ids_subq = select(User.id).where(User.registration_source.in_(EXCLUDED_COHORT_REGISTRATION_SOURCES))
        excluded_users = int(
            (
                await self.db.execute(
                    select(func.count())
                    .select_from(User)
                    .where(User.registration_source.in_(EXCLUDED_COHORT_REGISTRATION_SOURCES))
                )
            ).scalar()
            or 0
        )

        # -- 分母：active 用户发现（fleet 级 distinct，生产 cohort）------------
        active_union_all, seed_signal_union = await self._engagement_user_sets(start, end, seed_ids_subq)
        sorted_active = sorted(active_union_all)
        users_cap_hit = len(sorted_active) > MAX_ACTIVE_USERS_PER_RUN
        active_ids = sorted_active[:MAX_ACTIVE_USERS_PER_RUN]

        # -- 每用户有界 walk（D-02 公开 API）---------------------------------
        plan_goal_map = await self._goal_plan_map()
        window_truth_counts = {cls.value: 0 for cls in _TRUTH_ORDER}
        window_task_completions = 0
        window_goal_linked = 0
        window_goal_linked_actual = 0
        candidate_loops: list[_LoopFact] = []  # 窗口内过 goal 腿的 actual 完成候选
        history_loops: list[_LoopFact] = []  # 有界全史 actual 完成候选（TTFMV/stall）
        by_source_totals: dict[str, int] = {source.value: 0 for source in OutcomeSource}
        walk_truncated = False

        for user_id in active_ids:
            counts = await self._ledger.count_by_source(user_id=UUID(user_id), since=start, until=end)
            for key, value in counts.items():
                by_source_totals[key] = by_source_totals.get(key, 0) + int(value)

            entries, truncated = await self._walk_task_completions(user_id)
            walk_truncated = walk_truncated or truncated
            for entry in entries:
                plan_id = entry.correlation.get("plan_id") or None
                goal_id = plan_goal_map.get(plan_id) if plan_id else None
                in_window = start <= entry.occurred_at < end
                kinds = tuple(sorted({e.evidence_kind for e in entry.evidence if e.evidence_kind}))
                is_actual = entry.truth_class is TruthClass.ACTUAL
                if in_window:
                    window_task_completions += 1
                    window_truth_counts[entry.truth_class.value] += 1
                    if goal_id:
                        window_goal_linked += 1
                        if is_actual:
                            window_goal_linked_actual += 1
                if is_actual and goal_id:
                    fact = _LoopFact(
                        user_id=user_id,
                        task_id=entry.source_id,
                        plan_id=plan_id,
                        goal_id=goal_id,
                        occurred_at=entry.occurred_at,
                        evidence_kinds=kinds,
                    )
                    if in_window:
                        candidate_loops.append(fact)
                    history_loops.append(fact)

        # -- state update 腿（fleet 级批量存在性检查）--------------------------
        state_task_ids = await self._state_update_task_ids(history_loops)
        window_loops = [f for f in candidate_loops if f.task_id in state_task_ids]
        history_loops_resolved = [f for f in history_loops if f.task_id in state_task_ids]

        wvpl_users_set = {f.user_id for f in window_loops}
        active_users = len(active_ids)
        wvpl_users = len(wvpl_users_set)

        # -- outcome metrics（TTFMV / goal recovery）--------------------------
        user_created_at = await self._user_created_at_map(active_ids)
        first_loop = self._first_loop_per_user(history_loops_resolved)
        ttfmv = self._ttfmv(first_loop, user_created_at, start, end, walk_truncated)
        recovery = self._goal_recovery(history_loops_resolved, start, end, walk_truncated)

        # -- proactive / mode 面 ----------------------------------------------
        behavioral = await self._behavioral_by_outcome_type(start, end, seed_ids_subq)
        lifecycle_by_type, started_by_mode = await self._intervention_lifecycle(start, end, seed_ids_subq)

        any_truncation = users_cap_hit or walk_truncated or ttfmv["truncated"] or recovery["truncated"]

        samples = sorted(window_loops, key=lambda f: (f.occurred_at, f.task_id), reverse=True)[:MAX_LOOP_SAMPLES]

        return {
            "schema": WVPL_FACT_SCHEMA,
            "caliber_version": WVPL_CALIBER_VERSION,
            "as_of": _iso(resolved_as_of),
            "window": {"start": _iso(start), "end": _iso(end), "days": WINDOW_DAYS, "half_open": "[start, end)"},
            "north_star": {
                "active_users": active_users,
                "wvpl_users": wvpl_users,
                "wvpl_ratio": _ratio(wvpl_users, active_users),
                "loops_total": len(window_loops),
                "loops_per_wvpl_user": _ratio(len(window_loops), wvpl_users),
            },
            "outcomes": {
                "by_source": by_source_totals,
                "truth_coverage": {
                    "total": window_task_completions,
                    **window_truth_counts,
                    "actual_ratio": _ratio(window_truth_counts[TruthClass.ACTUAL.value], window_task_completions),
                    "truncated": walk_truncated,
                },
                "action_outcome_conversion": {
                    "goal_linked_completions": window_goal_linked,
                    "actual": window_goal_linked_actual,
                    "ratio": _ratio(window_goal_linked_actual, window_goal_linked),
                },
                "behavioral_by_outcome_type": behavioral,
            },
            "proactive": {
                "lifecycle_events_by_type": lifecycle_by_type,
                "started_by_execution_mode": started_by_mode,
            },
            "outcome_metrics": {
                "time_to_first_meaningful_value": ttfmv,
                "goal_recovery_after_stall": recovery,
            },
            "loops": {
                "all_time_bounded": {"loops_total": len(history_loops_resolved), "truncated": walk_truncated},
                "samples": [
                    {
                        "outcome_id": f.outcome_id,
                        "source_ref": f"task://{f.task_id}",
                        "task_id": f.task_id,
                        "user_id": f.user_id,
                        "plan_id": f.plan_id,
                        "goal_id": f.goal_id,
                        "occurred_at": _iso(f.occurred_at),
                        "evidence_kinds": list(f.evidence_kinds),
                    }
                    for f in samples
                ],
            },
            "cohort": {
                "definition": f"users.registration_source NOT IN {EXCLUDED_COHORT_REGISTRATION_SOURCES}",
                "excluded_users": excluded_users,
                "excluded_users_with_window_signals": len(seed_signal_union),
            },
            "provenance": {
                "generated_at": _iso(generated),
                "generated_by": "app.services.north_star_wvpl_service.NorthStarWvplService.build_fact",
                "determinism": "pure SQL/deterministic aggregation; zero LLM/model participation",
                "outcome_ledger_schema_version": OUTCOME_LEDGER_SCHEMA_VERSION,
                "source_queries": [dict(row) for row in SOURCE_QUERIES],
                "caps": {
                    "max_active_users_per_run": MAX_ACTIVE_USERS_PER_RUN,
                    "max_ledger_pages_per_user": MAX_LEDGER_PAGES_PER_USER,
                    "max_loop_samples": MAX_LOOP_SAMPLES,
                },
                "truncated": bool(any_truncation),
            },
            "definitions": dict(FACT_DEFINITIONS),
            "limitations": [
                "v1 scans a bounded active-user cohort; caps set provenance.truncated when hit",
                "all-time loop history is bounded by MAX_LEDGER_PAGES_PER_USER per user (newest first)",
                "goal recovery v1 measures loop-to-loop gaps only (no interim state signals)",
                "behavioral_outcomes is a live-0-row source in current deployments; buckets may be empty",
            ],
        }

    # ------------------------------------------------------------------
    # fleet 级发现与聚合查询
    # ------------------------------------------------------------------

    async def _engagement_user_sets(
        self, start: datetime, end: datetime, seed_ids_subq: Any
    ) -> tuple[set[str], set[str]]:
        """active 分母信号并集（生产 cohort）+ seed/guest demo face 并集。

        五源谓词与 D-02 ``count_by_source`` 的 where 子句逐一对应（常量引用，
        不复制字面值）；per-user 计数不走这里，走 D-02 公开 API。
        """
        production = lambda col: col.not_in(seed_ids_subq)  # noqa: E731
        in_seed = lambda col: col.in_(seed_ids_subq)  # noqa: E731

        def _task_pred(cohort: Any) -> Any:
            occurred = func.coalesce(Task.completed_at, Task.created_at)
            return [
                Task.status == TaskStatus.COMPLETED,
                Task.not_deleted_filter(),
                occurred >= start,
                occurred < end,
                cohort(Task.user_id),
            ]

        def _study_pred(cohort: Any) -> Any:
            return [
                StudyRecord.not_deleted_filter(),
                or_(
                    StudyRecord.task_id.is_(None),
                    StudyRecord.record_type.not_in(ECHO_STUDY_RECORD_TYPES),
                ),
                StudyRecord.created_at >= start,
                StudyRecord.created_at < end,
                cohort(StudyRecord.user_id),
            ]

        def _focus_pred(cohort: Any) -> Any:
            occurred = func.coalesce(FocusSession.end_time, FocusSession.created_at)
            return [
                FocusSession.status == FocusStatus.COMPLETED,
                FocusSession.not_deleted_filter(),
                occurred >= start,
                occurred < end,
                cohort(FocusSession.user_id),
            ]

        def _quiz_pred(cohort: Any) -> Any:
            return [
                ExpansionFeedback.not_deleted_filter(),
                ExpansionFeedback.meta_data["source"].as_string().in_(tuple(QUIZ_FEEDBACK_SOURCES)),
                ExpansionFeedback.created_at >= start,
                ExpansionFeedback.created_at < end,
                cohort(ExpansionFeedback.user_id),
            ]

        def _behavioral_pred(cohort: Any) -> Any:
            occurred = func.coalesce(BehavioralOutcome.timestamp, BehavioralOutcome.created_at)
            return [
                BehavioralOutcome.not_deleted_filter(),
                occurred >= start,
                occurred < end,
                cohort(BehavioralOutcome.user_id),
            ]

        async def _distinct(model: Any, column: Any, predicates: list[Any]) -> set[str]:
            stmt = select(column).where(*[p for p in predicates if p is not None]).distinct()
            rows = await self.db.execute(stmt)
            return {str(row) for row in rows.scalars().all() if row is not None}

        production_sets = [
            await _distinct(
                ChatMessage,
                ChatMessage.user_id,
                [
                    ChatMessage.role == MessageRole.USER,
                    ChatMessage.not_deleted_filter(),
                    ChatMessage.created_at >= start,
                    ChatMessage.created_at < end,
                    production(ChatMessage.user_id),
                ],
            ),
            await _distinct(
                ContextPackRun,
                ContextPackRun.user_id,
                [
                    ContextPackRun.created_at >= start,
                    ContextPackRun.created_at < end,
                    production(ContextPackRun.user_id),
                ],
            ),
            await _distinct(Task, Task.user_id, _task_pred(production)),
            await _distinct(StudyRecord, StudyRecord.user_id, _study_pred(production)),
            await _distinct(FocusSession, FocusSession.user_id, _focus_pred(production)),
            await _distinct(ExpansionFeedback, ExpansionFeedback.user_id, _quiz_pred(production)),
            await _distinct(BehavioralOutcome, BehavioralOutcome.user_id, _behavioral_pred(production)),
        ]
        seed_sets = [
            await _distinct(
                ChatMessage,
                ChatMessage.user_id,
                [
                    ChatMessage.role == MessageRole.USER,
                    ChatMessage.not_deleted_filter(),
                    ChatMessage.created_at >= start,
                    ChatMessage.created_at < end,
                    in_seed(ChatMessage.user_id),
                ],
            ),
            await _distinct(
                ContextPackRun,
                ContextPackRun.user_id,
                [
                    ContextPackRun.created_at >= start,
                    ContextPackRun.created_at < end,
                    in_seed(ContextPackRun.user_id),
                ],
            ),
            await _distinct(Task, Task.user_id, _task_pred(in_seed)),
            await _distinct(StudyRecord, StudyRecord.user_id, _study_pred(in_seed)),
            await _distinct(FocusSession, FocusSession.user_id, _focus_pred(in_seed)),
            await _distinct(ExpansionFeedback, ExpansionFeedback.user_id, _quiz_pred(in_seed)),
            await _distinct(BehavioralOutcome, BehavioralOutcome.user_id, _behavioral_pred(in_seed)),
        ]
        return set().union(*production_sets), set().union(*seed_sets)

    async def _goal_plan_map(self) -> dict[str, str]:
        """plans.goal_id IS NOT NULL 的 plan_id → goal_id 映射（goal 腿的真源查询）。"""
        rows = await self.db.execute(select(Plan.id, Plan.goal_id).where(Plan.goal_id.is_not(None)))
        return {
            str(plan_id): str(goal_id) for plan_id, goal_id in rows.all() if plan_id is not None and goal_id is not None
        }

    async def _state_update_task_ids(self, loops: list[_LoopFact]) -> set[str]:
        """state update 腿：task_id ∈ study_records（未删除）的批量存在性检查。"""
        task_ids = sorted({f.task_id for f in loops})
        found: set[str] = set()
        for i in range(0, len(task_ids), _STATE_LEG_CHUNK):
            chunk = task_ids[i : i + _STATE_LEG_CHUNK]
            rows = await self.db.execute(
                select(StudyRecord.task_id).where(
                    StudyRecord.task_id.in_(chunk),
                    StudyRecord.not_deleted_filter(),
                )
            )
            found.update(str(row) for row in rows.scalars().all() if row is not None)
        return found

    async def _user_created_at_map(self, user_ids: list[str]) -> dict[str, datetime]:
        result: dict[str, datetime] = {}
        for i in range(0, len(user_ids), _STATE_LEG_CHUNK):
            chunk = user_ids[i : i + _STATE_LEG_CHUNK]
            rows = await self.db.execute(select(User.id, User.created_at).where(User.id.in_(chunk)))
            for user_id, created_at in rows.all():
                if user_id is not None and created_at is not None:
                    result[str(user_id)] = _naive_utc(created_at)
        return result

    async def _behavioral_by_outcome_type(
        self, start: datetime, end: datetime, seed_ids_subq: Any
    ) -> dict[str, dict[str, int]]:
        occurred = func.coalesce(BehavioralOutcome.timestamp, BehavioralOutcome.created_at)
        stmt = (
            select(
                BehavioralOutcome.outcome_type,
                func.count(),
                func.sum(case((BehavioralOutcome.success.is_(True), 1), else_=0)),
            )
            .where(
                BehavioralOutcome.not_deleted_filter(),
                occurred >= start,
                occurred < end,
                BehavioralOutcome.user_id.not_in(seed_ids_subq),
            )
            .group_by(BehavioralOutcome.outcome_type)
        )
        rows = await self.db.execute(stmt)
        return {
            str(outcome_type): {"total": int(total or 0), "success": int(success or 0)}
            for outcome_type, total, success in rows.all()
        }

    async def _intervention_lifecycle(
        self, start: datetime, end: datetime, seed_ids_subq: Any
    ) -> tuple[dict[str, int], dict[str, int]]:
        cohort_pred = InterventionLifecycleEvent.user_id.not_in(seed_ids_subq)

        by_type_rows = await self.db.execute(
            select(InterventionLifecycleEvent.event_type, func.count())
            .where(
                InterventionLifecycleEvent.not_deleted_filter(),
                InterventionLifecycleEvent.occurred_at >= start,
                InterventionLifecycleEvent.occurred_at < end,
                cohort_pred,
            )
            .group_by(InterventionLifecycleEvent.event_type)
        )
        by_type = {str(event_type): int(count or 0) for event_type, count in by_type_rows.all()}

        started_rows = await self.db.execute(
            select(InterventionLifecycleEvent.execution_mode, func.count())
            .where(
                InterventionLifecycleEvent.not_deleted_filter(),
                InterventionLifecycleEvent.occurred_at >= start,
                InterventionLifecycleEvent.occurred_at < end,
                cohort_pred,
                InterventionLifecycleEvent.event_type == "started",
            )
            .group_by(InterventionLifecycleEvent.execution_mode)
        )
        started: dict[str, int] = dict.fromkeys(_LIFECYCLE_KNOWN_MODES, 0)
        started["other"] = 0
        for mode, count in started_rows.all():
            key = str(mode) if mode in _LIFECYCLE_KNOWN_MODES else "other"
            started[key] = started.get(key, 0) + int(count or 0)
        return by_type, started

    # ------------------------------------------------------------------
    # D-02 公开 API 消费（per-user 有界 walk）
    # ------------------------------------------------------------------

    async def _walk_task_completions(self, user_id: str) -> tuple[list[Any], bool]:
        """单用户全史 task_completion 有界翻页（D-02 query 公开 API，零分级重复）。

        返回 (entries, truncated)；truncated=True 表示页数顶被触（更早历史未走）。
        """
        entries: list[Any] = []
        cursor: str | None = None
        for _ in range(MAX_LEDGER_PAGES_PER_USER):
            page = await self._ledger.query(
                user_id=UUID(user_id),
                source=OutcomeSource.TASK_COMPLETION,
                truth_class=None,
                since=None,
                until=None,
                limit=_LEDGER_PAGE_SIZE,
                cursor=cursor,
            )
            entries.extend(page.items)
            if page.next_cursor is None:
                return entries, False
            cursor = page.next_cursor
        return entries, True

    # ------------------------------------------------------------------
    # outcome metrics（确定性纯函数面）
    # ------------------------------------------------------------------

    @staticmethod
    def _first_loop_per_user(loops: list[_LoopFact]) -> dict[str, _LoopFact]:
        best: dict[str, _LoopFact] = {}
        for fact in loops:
            current = best.get(fact.user_id)
            if current is None or (fact.occurred_at, fact.task_id) < (current.occurred_at, current.task_id):
                best[fact.user_id] = fact
        return best

    @staticmethod
    def _ttfmv(
        first_loop: dict[str, _LoopFact],
        user_created_at: dict[str, datetime],
        start: datetime,
        end: datetime,
        truncated: bool,
    ) -> dict[str, Any]:
        cohort_days: list[float] = []
        for user_id, fact in first_loop.items():
            if not (start <= fact.occurred_at < end):
                continue
            created_at = user_created_at.get(user_id)
            if created_at is None:
                continue
            days = max(0.0, (fact.occurred_at - created_at).total_seconds() / 86400.0)
            cohort_days.append(days)
        cohort_days.sort()
        return {
            "newly_converted_users": len(cohort_days),
            "median_days": _median_days(cohort_days),
            "truncated": bool(truncated),
        }

    @staticmethod
    def _goal_recovery(loops: list[_LoopFact], start: datetime, end: datetime, truncated: bool) -> dict[str, Any]:
        """stall = 同 goal 相邻 loop 间隔 ≥ GOAL_STALL_THRESHOLD_DAYS；下一 loop 关闭。"""
        by_goal: dict[tuple[str, str], list[_LoopFact]] = {}
        for fact in loops:
            if fact.goal_id:
                by_goal.setdefault((fact.user_id, fact.goal_id), []).append(fact)
        recovery_days: list[float] = []
        for series in by_goal.values():
            series.sort(key=lambda f: (f.occurred_at, f.task_id))
            for prev, nxt in zip(series, series[1:], strict=False):
                gap_days = (nxt.occurred_at - prev.occurred_at).total_seconds() / 86400.0
                if gap_days >= GOAL_STALL_THRESHOLD_DAYS and start <= nxt.occurred_at < end:
                    recovery_days.append(gap_days)
        recovery_days.sort()
        return {
            "stall_threshold_days": GOAL_STALL_THRESHOLD_DAYS,
            "recovered_in_window": len(recovery_days),
            "median_recovery_days": _median_days(recovery_days),
            "truncated": bool(truncated),
        }


def canonical_fact_json(fact: dict[str, Any]) -> str:
    """事实 JSON 的逐字节稳定序列化（sorted keys、紧凑分隔符、UTF-8）。"""
    return json.dumps(fact, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


__all__ = ["NorthStarWvplService", "canonical_fact_json"]
