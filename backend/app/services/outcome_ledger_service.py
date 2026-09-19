"""D-02 · Outcome Ledger 读模型服务 —— 跨五源的统一 outcome 查询层。

形态（契约 = ``app/core/outcome_ledger.py``）：
- **纯读模型，零 schema 变更**：聚合 tasks / study_records / focus_sessions /
  expansion_feedback(quiz) / behavioral_outcomes 五源，不建新表、不写库。
- **不重复计数（同因合并）**：五源流按 standalone 谓词**天然不相交**——
  ``study_records`` 的完成回声行（record_type=task_complete 且 task_id 非空）
  不进独立流，只作为对应 ``task_completion`` outcome 的多源证据附着。因此
  跨流合并是纯排序拼接，keyset 分页精确无重复。
- **跨流全序（R2 P1 返修）**：分页全序 = (occurred_at, ``'<source>:<id>'``)
  字典序倒序；各流 SQL keyset 以**带前缀的全局键形态**比较
  （``_stream_key_expr``），与 merged 排序严格同构——跨流同刻 tie 处不再
  重复交付（旧实现剥前缀比较裸 UUID 所致）。
- **证据解析三重门（R2 P2-1/P2-2 返修）**：kind↔scheme 白名单 + 文件生命
  周期就绪 + TaskDocument 任务关联性——归属不等于相关，声明不构成证明。
- **focus 时间方向（R2 P2-3 返修）**：只有完成时刻之前开始的会话才计入
  覆盖率，完成后的会话不得追溯升级（truth 单调性说明见 REPORT）。
- **幂等**：读模型 + 确定性 ``derive_outcome_id`` —— 相同输入重复查询产
  完全相同的条目与 id（测试钉住）；无写入面即无写侧幂等负担。
- **用户隔离**：所有谓词以 ``user_id`` 为第一过滤键（复用查询层谓词，
  与 D-01 envelope 的 user_id 隔离键同语义）。
- **cohort 边界**：``exclude_seed_cohort=True`` 时排除 guest/seed 注册源
  （B-02 F1 词表 ``("guest","seed")``，fleet 级批扫消费方使用；单用户查询
  默认 False，guest 查自己的账本合法）。

查询接口（服务层函数，不新增 HTTP 端点）：
- ``query(...)`` → ``OutcomePage``（keyset 分页 + source/truth_class 过滤 + 时间窗）；
- ``count_by_source(...)`` → 各源 outcome 数（同 standalone 谓词，计数不重复）；
- ``truth_coverage(...)`` → task completion 的真相分布（actual vs self_reported），
  即「完成 ≠ 点击」的度量面。

分页语义（truth_class 过滤下的一致性）：非 task 源真相恒为 actual，因此
``truth_class != actual`` 时非 task 流整流排除；``actual`` 过滤时 task 流在
服务内按批推进（有界，``_TASK_FILTER_BATCH_CAP``）直到凑满一页或流尽——
过滤后页面不欠填、游标不跳页不重页。

消费方接入点（详见 core 模块 docstring 与 v3-output/D-02/REPORT.md）：
- Aurora / Context Compiler（A-05）：``query(truth_class=TruthClass.ACTUAL)``；
- Experience Memory（M-06）：``query(source=OutcomeSource.BEHAVIORAL)`` +
  correlation.intervention_id；
- Galaxy（G-01/G-02）：``query(source=STUDY_RECORD/FOCUS_SESSION)`` + node_id 关联；
- North Star WVPL：``truth_coverage`` 的 actual 面。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String, and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_plan import action_plan_projection
from app.core.outcome_ledger import (
    ECHO_STUDY_RECORD_TYPES,
    EVIDENCE_KIND_REF_SCHEMES,
    EVIDENCE_TRUST_TIERS,
    QUIZ_FEEDBACK_SOURCES,
    EvidenceRole,
    EvidenceTrustTier,
    OutcomeEntry,
    OutcomeEvidence,
    OutcomePolarity,
    OutcomeSource,
    TruthClass,
    classify_task_completion,
    decode_cursor,
    derive_outcome_id,
    encode_cursor,
    parse_declared_evidence,
)
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import ExpansionFeedback, StudyRecord
from app.models.intervention_adaptive import BehavioralOutcome
from app.models.task import Task, TaskStatus
from app.models.user import User

#: B-02 F1 / leaderboard_service 同款 cohort 排除词表（冻结值钉死见测试）。
EXCLUDED_COHORT_REGISTRATION_SOURCES: tuple[str, ...] = ("guest", "seed")

#: v1 可解析 ref scheme 全集（= EVIDENCE_KIND_REF_SCHEMES 并集 = document）。
#: document:// 解析条件（R2 P2-1/P2-2 返修）：归属用户 + 文件生命周期就绪 +
#: **与被完成任务存在 TaskDocument 显式关联**（防「无关旧文件洗白」）。其余
#: scheme（task://、subtask://、memory:// 等）v1 一律不解析 → 永不单独升 actual
#: （诚实降级：声明不构成证明——task/subtask 行本身也只是用户主张）。
RESOLVABLE_REF_SCHEMES: frozenset[str] = frozenset(
    {scheme for schemes in EVIDENCE_KIND_REF_SCHEMES.values() for scheme in schemes}
)

#: StoredFile「证据就绪」状态集：字节实际存在（uploaded）且处理完成（processed）。
#: uploading（从未传完）/queued/processing（在途）/failed（失败）不算已验证证据。
STORED_FILE_READY_STATUSES: frozenset[str] = frozenset({"uploaded", "processed"})

_VERIFIABLE_KINDS = frozenset(
    {kind for kind, tier in EVIDENCE_TRUST_TIERS.items() if tier is EvidenceTrustTier.VERIFIABLE}
)

_MAX_LIMIT = 200
_DEFAULT_LIMIT = 20
_TASK_FILTER_BATCH_CAP = 20  # truth 过滤下 task 流的有界批次推进上限


@dataclass(frozen=True)
class OutcomePage:
    """一页账本条目（keyset 分页）。"""

    items: tuple[OutcomeEntry, ...]
    next_cursor: str | None = None
    source_counts: dict[str, int] = field(default_factory=dict)  # 本页各源条数


def _coalesce(*columns: Any) -> Any:
    """多列取首非空（单列直接返回——sqlite 的 coalesce 要求 ≥2 参数）。"""
    if len(columns) == 1:
        return columns[0]
    return func.coalesce(*columns)


def _uuid_str(value: UUID | str | None) -> str | None:
    if value is None:
        return None
    return str(value) if isinstance(value, UUID) else str(UUID(str(value)))


def _safe_uuid_str(value: UUID | str | None) -> str:
    """quiz meta 等非受信 JSON 字段的 UUID 提取：脏值降级为 ""，不炸整查询。"""
    try:
        return _uuid_str(value) or ""
    except (ValueError, TypeError, AttributeError):
        return ""


def _stream_key_expr(source: OutcomeSource, id_expr: Any) -> Any:
    """全局键表达式 ``'<source>:' || id``——keyset 比较与 merged 全局排序严格同构。

    R2 P1 返修：跨流同刻 tie 的确定性全序是 (occurred_at, '<source>:<id>')
    字典序。旧实现把游标键剥前缀后拿**裸 UUID** 与外流游标键比较，同刻处条件
    恒真 → 跨页重复交付。keyset 谓词必须用带前缀的全局键形态比较，禁止跨流
    比较裸 UUID。
    """
    return literal(f"{source.value}:").concat(id_expr.cast(String))


class OutcomeLedgerService:
    """跨五源 outcome 统一查询层（只读）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 查询主入口
    # ------------------------------------------------------------------

    async def query(
        self,
        *,
        user_id: UUID | str,
        source: OutcomeSource | str | None = None,
        truth_class: TruthClass | str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = _DEFAULT_LIMIT,
        cursor: str | None = None,
        exclude_seed_cohort: bool = False,
    ) -> OutcomePage:
        """按 (occurred_at, key) 倒序翻页；source/truth_class/时间窗过滤。

        truth_class 过滤语义：非 task 源真相恒为 actual（服务器记录的行为观察），
        因此 ``truth_class != actual`` 时非 task 源整流排除；``actual`` 时 task 源
        仅保留分级为 actual 的行——消费方拿到的「已证实」面不含自报完成。
        """
        user_id = UUID(str(user_id))
        wanted_source = OutcomeSource(source) if source is not None else None
        wanted_truth = TruthClass(truth_class) if truth_class is not None else None
        limit = max(1, min(_MAX_LIMIT, int(limit)))
        anchor = decode_cursor(cursor)

        cohort_filter = self._cohort_filter(exclude_seed_cohort)

        streams: dict[OutcomeSource, list[OutcomeEntry]] = {}
        # 各流「下方还有原始行」的续传点：(occurred_at, 全局 key)。非 None 即流未取尽。
        continuations: dict[OutcomeSource, tuple[datetime, str]] = {}

        if wanted_source in (None, OutcomeSource.TASK_COMPLETION):
            entries, continuation = await self._task_completions(
                user_id=user_id,
                since=since,
                until=until,
                limit=limit,
                anchor=anchor,
                cohort_filter=cohort_filter,
                truth_filter=wanted_truth,
            )
            streams[OutcomeSource.TASK_COMPLETION] = entries
            if continuation is not None:
                continuations[OutcomeSource.TASK_COMPLETION] = continuation

        non_task_truth_ok = wanted_truth in (None, TruthClass.ACTUAL)
        if non_task_truth_ok:
            builders = (
                (OutcomeSource.STUDY_RECORD, self._standalone_study_records),
                (OutcomeSource.FOCUS_SESSION, self._focus_sessions),
                (OutcomeSource.QUIZ_FEEDBACK, self._quiz_feedbacks),
                (OutcomeSource.BEHAVIORAL, self._behavioral_outcomes),
            )
            for stream_source, builder in builders:
                if wanted_source in (None, stream_source):
                    entries, continuation = await builder(
                        user_id=user_id,
                        since=since,
                        until=until,
                        limit=limit,
                        anchor=anchor,
                        cohort_filter=cohort_filter,
                    )
                    streams[stream_source] = entries
                    if continuation is not None:
                        continuations[stream_source] = continuation

        merged: list[OutcomeEntry] = [entry for rows in streams.values() for entry in rows]
        # 五流不相交（standalone 谓词保证），key 全局唯一 → 排序即合并，无重复计数。
        merged.sort(key=lambda entry: (entry.occurred_at, entry.key), reverse=True)
        page = merged[:limit]
        has_more = len(merged) > limit or bool(continuations)

        next_cursor: str | None = None
        if has_more:
            if page:
                # 页末条目即安全续传点：keyset 保证下页严格在其下——已返回项不重、
                # 未返回项（含本页裁掉的预取行）不漏。
                last = page[-1]
                next_cursor = encode_cursor(last.occurred_at, last.key)
            else:
                # 空页但流未取尽（truth 深扫整批被滤掉）：用流的原始续传点。
                # 此时无任何条目被返回，裁剪风险不存在。
                boundary = max(continuations.values(), key=lambda pair: (pair[0], pair[1]))
                next_cursor = encode_cursor(boundary[0], boundary[1])

        counts: dict[str, int] = {}
        for entry in page:
            counts[entry.source.value] = counts.get(entry.source.value, 0) + 1
        return OutcomePage(items=tuple(page), next_cursor=next_cursor, source_counts=counts)

    async def count_by_source(
        self,
        *,
        user_id: UUID | str,
        since: datetime | None = None,
        until: datetime | None = None,
        exclude_seed_cohort: bool = False,
    ) -> dict[str, int]:
        """各源独立 outcome 计数（同 standalone 谓词，与 query 口径一致，不重复）。"""
        user_id = UUID(str(user_id))
        cohort = self._cohort_filter(exclude_seed_cohort)
        win = self._window_factory(since, until)

        def _where(*predicates: Any) -> Any:
            return [p for p in predicates if p is not None]

        task_where = _where(
            Task.user_id == user_id,
            Task.status == TaskStatus.COMPLETED,
            Task.not_deleted_filter(),
            win(Task, Task.completed_at, Task.created_at),
            cohort(Task.user_id),
        )
        study_where = _where(
            StudyRecord.user_id == user_id,
            StudyRecord.not_deleted_filter(),
            or_(
                StudyRecord.task_id.is_(None),
                StudyRecord.record_type.not_in(ECHO_STUDY_RECORD_TYPES),
            ),
            win(StudyRecord, StudyRecord.created_at),
            cohort(StudyRecord.user_id),
        )
        focus_where = _where(
            FocusSession.user_id == user_id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.not_deleted_filter(),
            win(FocusSession, FocusSession.end_time, FocusSession.created_at),
            cohort(FocusSession.user_id),
        )
        quiz_where = _where(
            ExpansionFeedback.user_id == user_id,
            ExpansionFeedback.not_deleted_filter(),
            ExpansionFeedback.meta_data["source"].as_string().in_(tuple(QUIZ_FEEDBACK_SOURCES)),
            win(ExpansionFeedback, ExpansionFeedback.created_at),
            cohort(ExpansionFeedback.user_id),
        )
        behavioral_where = _where(
            BehavioralOutcome.user_id == user_id,
            BehavioralOutcome.not_deleted_filter(),
            win(BehavioralOutcome, BehavioralOutcome.timestamp, BehavioralOutcome.created_at),
            cohort(BehavioralOutcome.user_id),
        )

        async def _count(stmt: Any) -> int:
            result = await self.db.execute(stmt)
            return int(result.scalar() or 0)

        return {
            OutcomeSource.TASK_COMPLETION.value: await _count(
                select(func.count()).select_from(Task).where(*task_where)
            ),
            OutcomeSource.STUDY_RECORD.value: await _count(
                select(func.count()).select_from(StudyRecord).where(*study_where)
            ),
            OutcomeSource.FOCUS_SESSION.value: await _count(
                select(func.count()).select_from(FocusSession).where(*focus_where)
            ),
            OutcomeSource.QUIZ_FEEDBACK.value: await _count(
                select(func.count()).select_from(ExpansionFeedback).where(*quiz_where)
            ),
            OutcomeSource.BEHAVIORAL.value: await _count(
                select(func.count()).select_from(BehavioralOutcome).where(*behavioral_where)
            ),
        }

    async def truth_coverage(
        self,
        *,
        user_id: UUID | str,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = 1000,
    ) -> dict[str, Any]:
        """task completion 的真相分布（「完成 ≠ 点击」度量面）。

        返回 ``{total, actual, self_reported, unknown, actual_ratio}``。
        actual_ratio = actual / total（total=0 时为 None 而非 0——没有分母时
        不伪造比率）。分类输入逐任务计算（focus 覆盖聚合 + quiz 物化存在性 +
        declared ref 解析）；limit 为保护上限（默认 1000、硬顶 2000），超窗任务
        按最新截断——**total 与 ratio 均只反映截断窗内的任务**，超窗不报错也不
        计入（返回值无 truncated 标志，消费方对 >1000 任务的用户需自知截断语义；
        v2 若需精确分布应改为分组聚合 SQL）。
        """
        user_id = UUID(str(user_id))
        limit = max(1, min(_MAX_LIMIT * 10, int(limit)))
        entries, _continuation = await self._task_completions(
            user_id=user_id,
            since=since,
            until=until,
            limit=limit,
            anchor=None,
            cohort_filter=self._cohort_filter(False),
            truth_filter=None,
        )
        counts = {member.value: 0 for member in TruthClass}
        for entry in entries:
            counts[entry.truth_class.value] += 1
        total = len(entries)
        return {
            "total": total,
            "actual": counts[TruthClass.ACTUAL.value],
            "self_reported": counts[TruthClass.SELF_REPORTED.value],
            "unknown": counts[TruthClass.UNKNOWN.value],
            "actual_ratio": (counts[TruthClass.ACTUAL.value] / total) if total else None,
        }

    # ------------------------------------------------------------------
    # 内部：谓词助手
    # ------------------------------------------------------------------

    @staticmethod
    def _window(since: datetime | None, until: datetime | None, *occurred_cols: Any) -> Any:
        """occurred_at = coalesce(*cols) 上的 [since, until) 谓词（None = 无谓词）。"""
        occurred = _coalesce(*occurred_cols)
        clauses = []
        if since is not None:
            clauses.append(occurred >= since)
        if until is not None:
            clauses.append(occurred < until)
        return and_(*clauses) if clauses else None

    @staticmethod
    def _window_factory(since: datetime | None, until: datetime | None):
        def _apply(model: Any, *occurred_cols: Any) -> Any:
            cols = occurred_cols or (model.created_at,)
            return OutcomeLedgerService._window(since, until, *cols)

        return _apply

    @staticmethod
    def _keyset(occurred: Any, key_expr: Any, anchor: tuple[datetime, str] | None) -> Any:
        """keyset 谓词：(occurred, key) < anchor（倒序翻页；None = 无谓词）。"""
        if anchor is None:
            return None
        anchor_ts, anchor_key = anchor
        return or_(
            occurred < anchor_ts,
            and_(occurred == anchor_ts, key_expr < anchor_key),
        )

    @staticmethod
    def _cohort_filter(exclude_seed_cohort: bool):
        if not exclude_seed_cohort:
            return lambda _col: None
        seed_ids = select(User.id).where(User.registration_source.in_(EXCLUDED_COHORT_REGISTRATION_SOURCES))
        return lambda col: col.not_in(seed_ids)

    # ------------------------------------------------------------------
    # 内部：五流构建
    # ------------------------------------------------------------------

    async def _task_completions(
        self,
        *,
        user_id: UUID,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        anchor: tuple[datetime, str] | None,
        cohort_filter: Any,
        truth_filter: TruthClass | None,
    ) -> tuple[list[OutcomeEntry], tuple[datetime, str] | None]:
        """task_completion 流（唯一逐条分级的源）。

        truth_filter 非空时按批推进（每批 limit 行、keyset 续传，上限
        ``_TASK_FILTER_BATCH_CAP`` 批）直到凑满 limit 条过滤后条目或流尽——
        分级谓词（focus 覆盖/quiz 物化/ref 解析）不是纯 SQL，过滤在物化后进行。
        """
        collected: list[OutcomeEntry] = []
        batches = 0
        fetch_n = limit + 1  # 多取 1 行作「流未取尽」探针
        continuation: tuple[datetime, str] | None = None
        # anchor 保持全局键形态（'<source>:<id>'）——与 _stream_key_expr 同构（R2 P1）。
        while True:
            occurred = _coalesce(Task.completed_at, Task.created_at)
            predicates = [
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.not_deleted_filter(),
                self._window(since, until, Task.completed_at, Task.created_at),
                self._keyset(occurred, _stream_key_expr(OutcomeSource.TASK_COMPLETION, Task.id), anchor),
                cohort_filter(Task.user_id),
            ]
            stmt = (
                select(Task)
                .where(*[p for p in predicates if p is not None])
                .order_by(occurred.desc(), Task.id.desc())
                .limit(fetch_n)
            )
            tasks = list((await self.db.execute(stmt)).scalars().all())
            if not tasks:
                break

            batch = await self._classify_task_batch(
                user_id=user_id,
                tasks=tasks,
                truth_class_filter=truth_filter,
            )
            collected.extend(batch)

            last = tasks[-1]
            anchor = (last.completed_at or last.created_at, f"task_completion:{last.id}")
            batches += 1
            if len(tasks) == fetch_n:
                continuation = (
                    last.completed_at or last.created_at,
                    f"task_completion:{last.id}",
                )
            else:
                continuation = None  # 满批才可能有余；短批 = 流尽
            if len(collected) >= limit or len(tasks) < fetch_n or batches >= _TASK_FILTER_BATCH_CAP:
                break
        return collected[:limit], continuation

    async def _classify_task_batch(
        self,
        *,
        user_id: UUID,
        tasks: list[Any],
        truth_class_filter: TruthClass | None,
    ) -> list[OutcomeEntry]:
        task_ids = [task.id for task in tasks]
        echoes = await self._echo_study_records(user_id, task_ids)
        focus_rows = await self._task_focus_sessions(user_id, task_ids)
        quiz_rows = await self._task_quiz_feedbacks(user_id, task_ids)
        verified_refs = await self._resolve_declared_refs(user_id, tasks)

        entries: list[OutcomeEntry] = []
        for task in tasks:
            task_id_str = _uuid_str(task.id) or ""
            task_echoes = echoes.get(task.id, [])
            task_focus = focus_rows.get(task.id, [])
            task_quiz = quiz_rows.get(task.id, [])
            focus_minutes = sum(float(row.duration_minutes or 0) for row in task_focus)

            projection = action_plan_projection(task)  # X-01 统一门（禁止绕过）
            declared = parse_declared_evidence(projection["completion_evidence"]) if projection else None
            verified_kinds = verified_refs.get(task.id, frozenset())
            truth = classify_task_completion(
                completed_at=task.completed_at,
                declared_evidence=declared,
                focus_minutes_covered=focus_minutes,
                quiz_materialized=bool(task_quiz),
                verified_evidence_kinds=verified_kinds,
                actual_minutes=task.actual_minutes,
            )
            if truth_class_filter is not None and truth is not truth_class_filter:
                continue

            evidence: list[OutcomeEvidence] = []
            for entry in declared or ():
                kind = entry.get("evidence_kind")
                is_verified = kind in verified_kinds
                evidence.append(
                    OutcomeEvidence(
                        source="declared_ref",
                        ref=entry.get("ref"),
                        evidence_kind=kind,
                        role=(
                            EvidenceRole.INDEPENDENT
                            if is_verified and kind in _VERIFIABLE_KINDS
                            else EvidenceRole.PIPELINE_ECHO
                        ),
                        verified=is_verified,
                    )
                )
            for row in task_quiz:
                evidence.append(
                    OutcomeEvidence(
                        source="quiz_feedback",
                        ref=f"quiz_feedback://{row.id}",
                        evidence_kind="quiz_result",
                        role=EvidenceRole.INDEPENDENT,
                        verified=True,
                    )
                )
            for row in task_focus:
                evidence.append(
                    OutcomeEvidence(
                        source="focus_session",
                        ref=f"focus_session://{row.id}",
                        evidence_kind="system_event",
                        role=EvidenceRole.INDEPENDENT,
                        verified=True,
                    )
                )
            for row in task_echoes:
                evidence.append(
                    OutcomeEvidence(
                        source="study_record",
                        ref=f"study_record://{row.id}",
                        evidence_kind="system_event",
                        role=EvidenceRole.PIPELINE_ECHO,
                        verified=False,
                    )
                )

            correlation: dict[str, str] = {"task_id": task_id_str}
            if task.plan_id:
                correlation["plan_id"] = _uuid_str(task.plan_id) or ""
            if task.knowledge_node_id:
                correlation["node_id"] = _uuid_str(task.knowledge_node_id) or ""

            entries.append(
                OutcomeEntry(
                    outcome_id=derive_outcome_id(source=OutcomeSource.TASK_COMPLETION, source_id=task.id),
                    source=OutcomeSource.TASK_COMPLETION,
                    source_id=task_id_str,
                    user_id=_uuid_str(task.user_id) or "",
                    occurred_at=task.completed_at or task.created_at,
                    truth_class=truth,
                    polarity=OutcomePolarity.POSITIVE,
                    source_ref=f"task://{task_id_str}",
                    correlation=correlation,
                    minutes=float(task.actual_minutes) if task.actual_minutes is not None else None,
                    evidence=tuple(evidence),
                )
            )
        return entries

    async def _echo_study_records(self, user_id: UUID, task_ids: list[Any]) -> dict[Any, list[Any]]:
        if not task_ids:
            return {}
        stmt = select(StudyRecord).where(
            StudyRecord.user_id == user_id,
            StudyRecord.task_id.in_(task_ids),
            StudyRecord.record_type.in_(ECHO_STUDY_RECORD_TYPES),
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        grouped: dict[Any, list[Any]] = {}
        for row in rows:
            grouped.setdefault(row.task_id, []).append(row)
        return grouped

    async def _task_focus_sessions(self, user_id: UUID, task_ids: list[Any]) -> dict[Any, list[Any]]:
        """完成时刻**之前开始**的 focus 会话才有资格作覆盖证据（R2 P2-3 时间方向）。

        完成之后开始的会话不能追溯升级（账本每次查询重算，否则同一 outcome_id
        今天 self_reported、明天 actual 的非单调翻转）。开始于完成前、结束于完成后
        的会话与工作窗口重叠，仍计入。
        """
        if not task_ids:
            return {}
        stmt = (
            select(FocusSession)
            .join(Task, Task.id == FocusSession.task_id)
            .where(
                FocusSession.user_id == user_id,
                FocusSession.task_id.in_(task_ids),
                FocusSession.status == FocusStatus.COMPLETED,
                FocusSession.not_deleted_filter(),
                FocusSession.start_time < Task.completed_at,
            )
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        grouped: dict[Any, list[Any]] = {}
        for row in rows:
            grouped.setdefault(row.task_id, []).append(row)
        return grouped

    async def _task_quiz_feedbacks(self, user_id: UUID, task_ids: list[Any]) -> dict[Any, list[Any]]:
        """quiz 反馈按 meta_data.task_id 关联（GalaxyFeedbackService 存入 event_data）。"""
        if not task_ids:
            return {}
        task_id_strs = [str(value) for value in task_ids]
        stmt = select(ExpansionFeedback).where(
            ExpansionFeedback.user_id == user_id,
            ExpansionFeedback.meta_data["source"].as_string().in_(tuple(QUIZ_FEEDBACK_SOURCES)),
            ExpansionFeedback.meta_data["task_id"].as_string().in_(task_id_strs),
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        grouped: dict[Any, list[Any]] = {}
        for row in rows:
            raw = (row.meta_data or {}).get("task_id") if isinstance(row.meta_data, dict) else None
            parsed = _safe_uuid_str(raw) if raw is not None else ""
            if not parsed:
                continue  # 脏 meta：不关联任何 task，不炸查询
            grouped.setdefault(UUID(parsed), []).append(row)
        return grouped

    async def _resolve_declared_refs(self, user_id: UUID, tasks: list[Any]) -> dict[Any, frozenset[str]]:
        """v1 ref 解析（R2 P2-1/P2-2 返修后的完整条件）：

        1. **kind↔scheme 白名单**（``EVIDENCE_KIND_REF_SCHEMES``）：只有配对
           scheme 的 ref 才参与解析——code 无解析器，任何 scheme 都不升 actual；
           quiz_result 走 quiz_feedback 物化面而非声明 ref；
        2. **归属 + 生命周期**：document:// 文件必须归属本人、未软删、
           ``status ∈ STORED_FILE_READY_STATUSES``、``lifecycle_status='active'``
           且 ``erased_at IS NULL``（uploading/orphaned/revoked/erased 无效）；
        3. **任务关联性**：文件必须经 TaskDocument 显式挂到**被完成的这个任务**
           （防「上传过任意文件的用户把之后所有完成都洗成 actual」的归属≠相关性洞）。

        其余 scheme（task://、subtask://、memory:// 等）v1 不解析——声明保留、
        永不单独升 actual（诚实降级：无法证明时不伪装 actual）。批量解析避免 N+1。
        """
        from app.models.file_storage import SourceLifecycleStatus, StoredFile
        from app.models.task_document import TaskDocument

        # 先收集各 task 声明的 (kind, scheme, raw_id) 三元组（只留白名单配对）
        declared_refs: dict[Any, list[tuple[str, str, str]]] = {}
        doc_ids: set[str] = set()
        for task in tasks:
            projection = action_plan_projection(task)
            if not projection:
                continue
            refs: list[tuple[str, str, str]] = []
            for entry in parse_declared_evidence(projection["completion_evidence"]):
                ref = entry.get("ref")
                kind = entry.get("evidence_kind")
                if not ref or not isinstance(ref, str) or "://" not in ref:
                    continue
                scheme, _, raw_id = ref.partition("://")
                if scheme not in EVIDENCE_KIND_REF_SCHEMES.get(str(kind), frozenset()) or not raw_id:
                    continue
                # 规范化为 canonical UUID 字符串：大小写不敏感匹配，且脏值不进 IN 列表
                try:
                    canonical = str(UUID(raw_id))
                except (ValueError, TypeError, AttributeError):
                    continue
                refs.append((str(kind), scheme, canonical))
                if scheme == "document":
                    doc_ids.add(canonical)
            if refs:
                declared_refs[task.id] = refs

        if not declared_refs:
            return {}

        # 文件面：归属 + 生命周期就绪（P2-2）
        ready_files: set[str] = set()
        if doc_ids:
            rows = await self.db.execute(
                select(StoredFile.id).where(
                    StoredFile.user_id == user_id,
                    StoredFile.id.in_(list(doc_ids)),
                    StoredFile.not_deleted_filter(),
                    StoredFile.status.in_(tuple(STORED_FILE_READY_STATUSES)),
                    StoredFile.lifecycle_status == SourceLifecycleStatus.ACTIVE.value,
                    StoredFile.erased_at.is_(None),
                )
            )
            ready_files = {str(row) for row in rows.scalars().all()}

        # 关联面：本批任务 × 就绪文件的显式挂载（P2-1 相关性）
        task_doc_links: set[tuple[str, str]] = set()
        if ready_files:
            declaring_task_ids = [task.id for task in tasks if task.id in declared_refs]
            rows = await self.db.execute(
                select(TaskDocument.task_id, TaskDocument.file_id).where(
                    TaskDocument.task_id.in_(declaring_task_ids),
                    TaskDocument.file_id.in_([UUID(fid) for fid in ready_files]),
                    TaskDocument.not_deleted_filter(),
                )
            )
            task_doc_links = {(str(row[0]), str(row[1])) for row in rows.all()}

        verified: dict[Any, frozenset[str]] = {}
        for task in tasks:
            refs = declared_refs.get(task.id)
            if not refs:
                continue
            kinds: set[str] = set()
            for kind, scheme, raw_id in refs:
                if scheme == "document" and (str(task.id), raw_id) in task_doc_links:
                    kinds.add(kind)
            if kinds:
                verified[task.id] = frozenset(kinds)
        return verified

    async def _standalone_study_records(
        self,
        *,
        user_id: UUID,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        anchor: tuple[datetime, str] | None,
        cohort_filter: Any,
    ) -> tuple[list[OutcomeEntry], tuple[datetime, str] | None]:
        occurred = StudyRecord.created_at
        predicates = [
            StudyRecord.user_id == user_id,
            StudyRecord.not_deleted_filter(),
            or_(
                StudyRecord.task_id.is_(None),
                StudyRecord.record_type.not_in(ECHO_STUDY_RECORD_TYPES),
            ),
            self._window(since, until, occurred),
            self._keyset(
                occurred,
                _stream_key_expr(OutcomeSource.STUDY_RECORD, StudyRecord.id),
                anchor,
            ),
            cohort_filter(StudyRecord.user_id),
        ]
        stmt = (
            select(StudyRecord)
            .where(*[p for p in predicates if p is not None])
            .order_by(occurred.desc(), StudyRecord.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        continuation = (rows[-1].created_at, f"study_record:{rows[-1].id}") if len(rows) > limit else None
        return [
            OutcomeEntry(
                outcome_id=derive_outcome_id(source=OutcomeSource.STUDY_RECORD, source_id=row.id),
                source=OutcomeSource.STUDY_RECORD,
                source_id=_uuid_str(row.id) or "",
                user_id=_uuid_str(row.user_id) or "",
                occurred_at=row.created_at,
                truth_class=TruthClass.ACTUAL,
                polarity=OutcomePolarity.POSITIVE,
                source_ref=f"study_record://{row.id}",
                correlation={"node_id": _uuid_str(row.node_id) or ""},
                minutes=float(row.study_minutes) if row.study_minutes is not None else None,
                mastery_delta=float(row.mastery_delta) if row.mastery_delta is not None else None,
                evidence=(
                    OutcomeEvidence(
                        source="study_record",
                        ref=f"study_record://{row.id}",
                        evidence_kind="system_event",
                        role=EvidenceRole.INDEPENDENT,
                        verified=True,
                    ),
                ),
            )
            for row in rows
        ], continuation

    async def _focus_sessions(
        self,
        *,
        user_id: UUID,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        anchor: tuple[datetime, str] | None,
        cohort_filter: Any,
    ) -> tuple[list[OutcomeEntry], tuple[datetime, str] | None]:
        occurred = _coalesce(FocusSession.end_time, FocusSession.created_at)
        predicates = [
            FocusSession.user_id == user_id,
            FocusSession.status == FocusStatus.COMPLETED,
            FocusSession.not_deleted_filter(),
            self._window(since, until, FocusSession.end_time, FocusSession.created_at),
            self._keyset(
                occurred,
                _stream_key_expr(OutcomeSource.FOCUS_SESSION, FocusSession.id),
                anchor,
            ),
            cohort_filter(FocusSession.user_id),
        ]
        stmt = (
            select(FocusSession)
            .where(*[p for p in predicates if p is not None])
            .order_by(occurred.desc(), FocusSession.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        continuation = (
            (rows[-1].end_time or rows[-1].created_at, f"focus_session:{rows[-1].id}") if len(rows) > limit else None
        )
        entries: list[OutcomeEntry] = []
        for row in rows:
            correlation: dict[str, str] = {}
            if row.task_id:
                correlation["task_id"] = _uuid_str(row.task_id) or ""
            entries.append(
                OutcomeEntry(
                    outcome_id=derive_outcome_id(source=OutcomeSource.FOCUS_SESSION, source_id=row.id),
                    source=OutcomeSource.FOCUS_SESSION,
                    source_id=_uuid_str(row.id) or "",
                    user_id=_uuid_str(row.user_id) or "",
                    occurred_at=row.end_time or row.created_at,
                    truth_class=TruthClass.ACTUAL,
                    polarity=OutcomePolarity.POSITIVE,
                    source_ref=f"focus_session://{row.id}",
                    correlation=correlation,
                    minutes=float(row.duration_minutes) if row.duration_minutes is not None else None,
                    evidence=(
                        OutcomeEvidence(
                            source="focus_session",
                            ref=f"focus_session://{row.id}",
                            evidence_kind="system_event",
                            role=EvidenceRole.INDEPENDENT,
                            verified=True,
                        ),
                    ),
                )
            )
        return entries, continuation

    async def _quiz_feedbacks(
        self,
        *,
        user_id: UUID,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        anchor: tuple[datetime, str] | None,
        cohort_filter: Any,
    ) -> tuple[list[OutcomeEntry], tuple[datetime, str] | None]:
        occurred = ExpansionFeedback.created_at
        predicates = [
            ExpansionFeedback.user_id == user_id,
            ExpansionFeedback.not_deleted_filter(),
            ExpansionFeedback.meta_data["source"].as_string().in_(tuple(QUIZ_FEEDBACK_SOURCES)),
            self._window(since, until, occurred),
            self._keyset(
                occurred,
                _stream_key_expr(OutcomeSource.QUIZ_FEEDBACK, ExpansionFeedback.id),
                anchor,
            ),
            cohort_filter(ExpansionFeedback.user_id),
        ]
        stmt = (
            select(ExpansionFeedback)
            .where(*[p for p in predicates if p is not None])
            .order_by(occurred.desc(), ExpansionFeedback.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        continuation = (rows[-1].created_at, f"quiz_feedback:{rows[-1].id}") if len(rows) > limit else None
        entries: list[OutcomeEntry] = []
        for row in rows:
            meta = row.meta_data if isinstance(row.meta_data, dict) else {}
            quiz_source = meta.get("source")
            # meta_data 是非受信 JSON 字段：脏 task_id/node_id 降级为无关联，不炸整查询
            correlation: dict[str, str] = {}
            if meta.get("node_id"):
                correlation["node_id"] = _safe_uuid_str(meta["node_id"])
            if meta.get("task_id"):
                correlation["task_id"] = _safe_uuid_str(meta["task_id"])
            entries.append(
                OutcomeEntry(
                    outcome_id=derive_outcome_id(source=OutcomeSource.QUIZ_FEEDBACK, source_id=row.id),
                    source=OutcomeSource.QUIZ_FEEDBACK,
                    source_id=_uuid_str(row.id) or "",
                    user_id=_uuid_str(row.user_id) or "",
                    occurred_at=row.created_at,
                    truth_class=TruthClass.ACTUAL,
                    polarity=OutcomePolarity.POSITIVE if quiz_source == "quiz_passed" else OutcomePolarity.NEGATIVE,
                    source_ref=f"quiz_feedback://{row.id}",
                    correlation=correlation,
                    score=float(row.implicit_score) if row.implicit_score is not None else None,
                    evidence=(
                        OutcomeEvidence(
                            source="quiz_feedback",
                            ref=f"quiz_feedback://{row.id}",
                            evidence_kind="quiz_result",
                            role=EvidenceRole.INDEPENDENT,
                            verified=True,
                        ),
                    ),
                )
            )
        return entries, continuation

    async def _behavioral_outcomes(
        self,
        *,
        user_id: UUID,
        since: datetime | None,
        until: datetime | None,
        limit: int,
        anchor: tuple[datetime, str] | None,
        cohort_filter: Any,
    ) -> tuple[list[OutcomeEntry], tuple[datetime, str] | None]:
        occurred = _coalesce(BehavioralOutcome.timestamp, BehavioralOutcome.created_at)
        predicates = [
            BehavioralOutcome.user_id == user_id,
            BehavioralOutcome.not_deleted_filter(),
            self._window(since, until, BehavioralOutcome.timestamp, BehavioralOutcome.created_at),
            self._keyset(
                occurred,
                _stream_key_expr(OutcomeSource.BEHAVIORAL, BehavioralOutcome.id),
                anchor,
            ),
            cohort_filter(BehavioralOutcome.user_id),
        ]
        stmt = (
            select(BehavioralOutcome)
            .where(*[p for p in predicates if p is not None])
            .order_by(occurred.desc(), BehavioralOutcome.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        continuation = (
            (rows[-1].timestamp or rows[-1].created_at, f"behavioral:{rows[-1].id}") if len(rows) > limit else None
        )
        entries: list[OutcomeEntry] = []
        for row in rows:
            entries.append(
                OutcomeEntry(
                    outcome_id=derive_outcome_id(source=OutcomeSource.BEHAVIORAL, source_id=row.id),
                    source=OutcomeSource.BEHAVIORAL,
                    source_id=_uuid_str(row.id) or "",
                    user_id=_uuid_str(row.user_id) or "",
                    occurred_at=row.timestamp or row.created_at,
                    truth_class=TruthClass.ACTUAL,
                    polarity=OutcomePolarity.POSITIVE if row.success else OutcomePolarity.NEGATIVE,
                    source_ref=f"behavioral://{row.id}",
                    correlation=(
                        {"intervention_id": _uuid_str(row.intervention_id) or ""} if row.intervention_id else {}
                    ),
                    minutes=float(row.time_to_outcome) if row.time_to_outcome is not None else None,
                    score=1.0 if row.success else 0.0,
                    evidence=(
                        OutcomeEvidence(
                            source="behavioral",
                            ref=f"behavioral://{row.id}",
                            evidence_kind="system_event",
                            role=EvidenceRole.INDEPENDENT,
                            verified=True,
                        ),
                    ),
                )
            )
        return entries, continuation
