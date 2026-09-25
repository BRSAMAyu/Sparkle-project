"""J-05 ·「我卡住了」旗舰恢复旅程服务 —— 全产品统一恢复入口的装配层。

产品意图（v3/07_tasks/cards/J-05.md）：Stuck 做成全产品统一恢复入口——
Home/Goal/Action 三面携带各自真实 context 触发；最多先问一个高价值
问题（context 驱动，非固定问卷）；输出主 intervention；用户可
「不是这个原因」纠正，纠正进入反馈环影响后续判断（不静默丢弃）。

**不重建真源**（卡面 Forbidden 第 1 条），本服务只做装配：
- 摩擦诊断/单问选择/主 intervention 提名 = 冻结的 A-03 引擎
  （``app.aurora.friction_diagnosis.diagnose_friction``，LLM 0 次、
  确定性、对脏输入不 raise）——单问出口与差异化选择都是引擎既语义
  （IG 选问 + Q1 充分门），本层零复制判定；
- 近期失败记录 = ``task_stuck_signal_service`` 既有读侧
  （stuck/abandoned/timeout 判据同源）；
- 目标/任务事实 = Goal/Task 表读侧原样投影（A-07 goal_state 同款读
  侧纪律：零写库、不修饰）。

本层新增的三件事（引擎之外的正交事实）：
1. **context 装配**：把 db 真源行投影成 ``FrictionDiagnosisInput`` 的
   flat 事实（缺事实保持 None——结构诚实，不猜）；
2. **单问上限（产品口径）**：旅程内最多问一问；answer 轮若引擎仍想
   追问（Q1），以「会话问题预算已用完」声明触发引擎自身 B1 best-guess
   出口（uncertain 标注），绝不由本层伪造第二个诊断；
3. **纠正反馈环**：「不是这个原因」落 ``StuckJourneyCorrection``；
   后续派生把被纠正类型从主判断中垫后——后继者取引擎后验里下一位有
   提名的类型；后验无后继（单一类型证据）时如实回落「根分裂问」
   （A-03 冻结问题库首问 = 引擎 U1.unknown 出口的同一问），并标注
   ``correction_no_alternative``——纠正永远可见，不静默丢弃；
4. **V3-FIX-51 交付契约**：``main_intervention`` 恒带
   ``delivery="recommendation"``（建议非执行；见
   ``JOURNEY_INTERVENTION_DELIVERY``）——旅程提名不经 A-02 执行守卫，
   与 chat 面（过守卫的 ``selected``）的差异在类型面声明，非静默。

文案纪律：本服务零用户文案（问题文本/分支标签出自 A-03 冻结问题库，
intervention 是目录键；展示文案在客户端 l10n 完成；receipt 的
decision_reason 是面向回执的单一说明句，与引擎 receipt 同形制）。
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.friction_diagnosis import (
    DEFAULT_SESSION_QUESTION_LIMIT,
    FRICTION_INTERVENTION_NOMINATIONS,
    FRICTION_QUESTION_BANK,
    FrictionDiagnosis,
    OneBestQuestion,
    diagnose_friction,
)
from app.models.goal import Goal
from app.models.stuck_journey import StuckJourneyCorrection
from app.models.task import Task, TaskStatus
from app.services.task_stuck_signal_service import load_recent_task_execution_signals

STUCK_JOURNEY_SCHEMA_VERSION = "stuck_journey.v1"

#: 三面入口（路由层校验值域）。
STUCK_JOURNEY_SURFACES = frozenset({"home", "goal", "action"})

#: V3-FIX-51 · 旅程提名的交付语义（决策两面守卫不对称的**声明式处置**）：
#: chat 面决策经 A-02 结构守卫（``FrictionChatWiringService.CHAT_TURN_CAPABILITIES``
#: 能力/权限/分配事实）选出 ``selected`` 才出面；旅程面 ``main_intervention``
#: 是 A-03 诊断提名直出（不经 A-02 执行守卫）——同一摩擦类型两面结论可合法
#: 不同（A-08 p03 反例：chat 诊断对但结构不可服务 + 旅程 B1 错型）。本服务
#: **不执行**任何干预，提名由客户端动作面消费（各有其守卫）；契约恒带
#: ``delivery="recommendation"``——「建议非执行」在类型面声明，消费方据此
#: 区分两面语义，差异登记非静默（有子进程测试锁）。
JOURNEY_INTERVENTION_DELIVERY = "recommendation"

#: 纠正反馈环口径：freshness 窗口与容量上限（超出窗口/容量不再垫后——
#: 纠正不记仇，但窗口内的纠正一定生效）。
CORRECTION_FRESHNESS_DAYS = 14
CORRECTION_MAX_ACTIVE = 20

#: 近期失败计数窗口（天）——失败信号 occurred_at 的回看窗。
RECENT_FAILURE_WINDOW_DAYS = 14

#: 停滞在飞任务集合（context 投影口径；与 mobile stuck_recovery_provider
#: 的 _stallableStatuses 同源——pending 从未开始不算卡住）。
_IN_FLIGHT_STATUSES = (
    TaskStatus.IN_PROGRESS,
    TaskStatus.PAUSED,
    TaskStatus.STUCK,
    TaskStatus.RESTORE,
)


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip().upper()


def _strip(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


@dataclass(frozen=True)
class _JourneyContext:
    """真源读取结果（原样投影；None = 真源没有该事实，不猜）。"""

    goal: Goal | None
    task: Task | None
    recent_failure_count: int
    recent_failure_titles: tuple[str, ...]
    days_since_progress: int | None


class StuckJourneyService:
    """统一恢复旅程装配（一个 db 会话一个实例；全部读侧 + 纠正单写）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 对外三入口
    # ------------------------------------------------------------------

    async def start(
        self,
        *,
        user_id: UUID,
        surface: str,
        goal_id: UUID | None = None,
        task_id: UUID | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """三面入口：读取真实 context → 引擎诊断 → 纠正垫后 → 载荷。"""
        current = now or datetime.utcnow()
        context = await self._load_context(
            user_id, goal_id=goal_id, task_id=task_id, now=current
        )
        corrections = await self._active_corrections(user_id, now=current)
        diagnosis = diagnose_friction(self._engine_input(context))
        return self._build_payload(
            surface=surface,
            context=context,
            diagnosis=diagnosis,
            corrections=corrections,
            question_cap_reached=False,
            extra_annotations={},
        )

    async def answer(
        self,
        *,
        user_id: UUID,
        surface: str,
        question_id: str,
        branch_key: str,
        goal_id: UUID | None = None,
        task_id: UUID | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """回答闭环节点：branch_key 直传（A-03 引擎语义）重放诊断。

        单问上限在本层落：已问 1 问（``questions_asked_session=1``）；
        引擎若仍想追问（Q1），改以「会话问题预算已用完」声明重派生——
        走引擎自身 B1 best-guess 出口（uncertain=True），旅程不再出第二问。
        """
        current = now or datetime.utcnow()
        context = await self._load_context(
            user_id, goal_id=goal_id, task_id=task_id, now=current
        )
        corrections = await self._active_corrections(user_id, now=current)
        engine_input = self._engine_input(context)
        engine_input["answered_branches"] = [(question_id, branch_key)]
        engine_input["questions_asked_session"] = 1
        diagnosis = diagnose_friction(engine_input)

        question_cap_reached = False
        if diagnosis.outcome == "ask":
            # 产品口径「最多先问一个」：预算声明用完 → 引擎 B1 best-guess。
            engine_input["questions_asked_session"] = DEFAULT_SESSION_QUESTION_LIMIT
            diagnosis = diagnose_friction(engine_input)
            question_cap_reached = True

        return self._build_payload(
            surface=surface,
            context=context,
            diagnosis=diagnosis,
            corrections=corrections,
            question_cap_reached=question_cap_reached,
            extra_annotations={
                "answered_question_id": question_id,
                "answered_branch_key": branch_key,
            },
        )

    async def correct(
        self,
        *,
        user_id: UUID,
        surface: str,
        friction_type: str,
        intervention_key: str | None = None,
        goal_id: UUID | None = None,
        task_id: UUID | None = None,
        reason_text: str | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """「不是这个原因」：纠正落库（反馈环）→ 立即按纠正重派生旅程。

        返回携带 ``journey``（纠正后输出）——调用方可直接观察纠正前后
        主判断变化；落库失败异常向上抛（不静默）。
        """
        current = now or datetime.utcnow()
        context = await self._load_context(
            user_id, goal_id=goal_id, task_id=task_id, now=current
        )
        diagnosis = diagnose_friction(self._engine_input(context))
        corrections = await self._active_corrections(user_id, now=current)

        record = StuckJourneyCorrection(
            user_id=user_id,
            surface=surface,
            friction_type=friction_type,
            intervention_key=(_strip(intervention_key)[:32] or None) if intervention_key else None,
            task_id=task_id,
            goal_id=goal_id,
            reason_text=(_strip(reason_text)[:500] or None) if reason_text else None,
            context_snapshot=self._context_facts(context),
            schema_version=STUCK_JOURNEY_SCHEMA_VERSION,
            corrected_at=current,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        journey = self._build_payload(
            surface=surface,
            context=context,
            diagnosis=diagnosis,
            corrections=[*corrections, record],
            question_cap_reached=False,
            extra_annotations={"corrected_this_turn": True},
        )
        return {
            "version": STUCK_JOURNEY_SCHEMA_VERSION,
            "correction_id": str(record.id),
            "receipt": {
                "receipt_type": "stuck_journey_correction",
                "corrected_friction_type": friction_type,
                "surface": surface,
                "corrected_at": record.corrected_at.isoformat(),
                "decision_reason": (
                    "纠正已记录：后续的卡点判断会把这类原因往后放。"
                ),
            },
            "journey": journey,
        }

    # ------------------------------------------------------------------
    # context 装配（真源读侧；缺事实 = None，不猜）
    # ------------------------------------------------------------------

    async def _load_context(
        self,
        user_id: UUID,
        *,
        goal_id: UUID | None,
        task_id: UUID | None,
        now: datetime,
    ) -> _JourneyContext:
        task = await self._resolve_task(user_id, goal_id=goal_id, task_id=task_id)
        goal = await self._resolve_goal(user_id, goal_id=goal_id, task=task)

        signals = await load_recent_task_execution_signals(self.db, user_id=user_id)
        window_start = now - timedelta(days=RECENT_FAILURE_WINDOW_DAYS)
        recent_issues: list[Any] = []
        for signal in signals:
            if not signal.is_issue:
                continue
            occurred = self._signal_time(signal)
            if occurred is not None and occurred >= window_start:
                recent_issues.append((occurred, signal))
        recent_issues.sort(key=lambda pair: pair[0], reverse=True)

        last_touch: datetime | None = None
        if task is not None:
            last_touch = self._task_last_touch(task)
        for occurred, _signal in recent_issues:
            if last_touch is None or occurred > last_touch:
                last_touch = occurred
        days_since_progress = (
            max(0, (now - last_touch).days) if last_touch is not None else None
        )

        return _JourneyContext(
            goal=goal,
            task=task,
            recent_failure_count=len(recent_issues),
            recent_failure_titles=tuple(
                _strip(signal.title) for _occurred, signal in recent_issues[:3]
            ),
            days_since_progress=days_since_progress,
        )

    async def _resolve_task(
        self,
        user_id: UUID,
        *,
        goal_id: UUID | None,
        task_id: UUID | None,
    ) -> Task | None:
        """action 面：指定任务；home/goal 面：最近触碰的在飞任务（真源读侧）。"""
        if task_id is not None:
            result = await self.db.execute(
                select(Task).where(
                    Task.id == task_id,
                    Task.user_id == user_id,
                    Task.not_deleted_filter(),
                )
            )
            return result.scalar_one_or_none()
        query = select(Task).where(
            Task.user_id == user_id,
            Task.status.in_(list(_IN_FLIGHT_STATUSES)),
            Task.not_deleted_filter(),
        )
        if goal_id is not None:
            query = query.join(Goal, Goal.plan_id == Task.plan_id).where(
                Goal.id == goal_id
            )
        result = await self.db.execute(query.order_by(Task.updated_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def _resolve_goal(
        self,
        user_id: UUID,
        *,
        goal_id: UUID | None,
        task: Task | None,
    ) -> Goal | None:
        if goal_id is not None:
            result = await self.db.execute(
                select(Goal).where(
                    Goal.id == goal_id,
                    Goal.user_id == user_id,
                    Goal.not_deleted_filter(),
                )
            )
            return result.scalar_one_or_none()
        if task is not None and task.plan_id is not None:
            result = await self.db.execute(
                select(Goal).where(
                    Goal.plan_id == task.plan_id,
                    Goal.user_id == user_id,
                    Goal.not_deleted_filter(),
                )
            )
            goal = result.scalar_one_or_none()
            if goal is not None:
                return goal
        result = await self.db.execute(
            select(Goal)
            .where(
                Goal.user_id == user_id,
                Goal.status == "active",
                Goal.not_deleted_filter(),
            )
            .order_by(Goal.is_primary.desc(), Goal.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _engine_input(self, context: _JourneyContext) -> dict[str, Any]:
        """真源事实 → A-03 flat 输入。blocked_on_external /
        materials_available_unused 无读侧真源，保持 None（不猜）。"""
        task = context.task
        goal = context.goal
        if task is not None:
            task_anchor = _strip(task.title)[:60] or None
        elif goal is not None:
            task_anchor = _strip(goal.title)[:60] or None
        else:
            task_anchor = None
        return {
            "utterance": "",
            "task_anchor": task_anchor,
            "days_since_progress": context.days_since_progress,
            "recent_failure_count": (
                context.recent_failure_count if context.recent_failure_count else None
            ),
            "has_active_goal": goal is not None and _strip(goal.status) == "active",
            "has_task_context": task is not None,
        }

    def _context_facts(self, context: _JourneyContext) -> dict[str, Any]:
        """context 投影（真源事实；纠正快照/载荷共用同一投影，零第二口径）。"""
        task = context.task
        goal = context.goal
        return {
            "goal": self._goal_projection(goal),
            "task": self._task_projection(task),
            "recent_failures": {
                "window_days": RECENT_FAILURE_WINDOW_DAYS,
                "count": context.recent_failure_count,
                "titles": list(context.recent_failure_titles),
            },
            "days_since_progress": context.days_since_progress,
        }

    @staticmethod
    def _goal_projection(goal: Goal | None) -> dict[str, Any] | None:
        if goal is None:
            return None
        return {
            "id": str(goal.id),
            "title": _strip(goal.title),
            "status": _strip(goal.status),
            "progress": float(goal.progress or 0.0),
        }

    @staticmethod
    def _task_projection(task: Task | None) -> dict[str, Any] | None:
        if task is None:
            return None
        return {
            "id": str(task.id),
            "title": _strip(task.title),
            "status": _status_value(task.status),
            "estimated_minutes": task.estimated_minutes,
        }

    # ------------------------------------------------------------------
    # 纠正反馈环
    # ------------------------------------------------------------------

    async def _active_corrections(
        self, user_id: UUID, *, now: datetime
    ) -> list[StuckJourneyCorrection]:
        """freshness 窗口内的纠正记录（corrected_at 降序，容量上限）。"""
        window_start = now - timedelta(days=CORRECTION_FRESHNESS_DAYS)
        result = await self.db.execute(
            select(StuckJourneyCorrection)
            .where(
                StuckJourneyCorrection.user_id == user_id,
                StuckJourneyCorrection.corrected_at >= window_start,
                StuckJourneyCorrection.not_deleted_filter(),
            )
            .order_by(StuckJourneyCorrection.corrected_at.desc())
            .limit(CORRECTION_MAX_ACTIVE)
        )
        return list(result.scalars().all())

    def _apply_corrections(
        self,
        context: _JourneyContext,
        diagnosis: FrictionDiagnosis,
        corrections: list[StuckJourneyCorrection],
    ) -> tuple[FrictionDiagnosis, list[str]]:
        """纠正垫后（act 出口）：被纠正类型让位于引擎后验里下一位有提名的类型。

        引擎对象不可变（frozen）——垫后经 ``dataclasses.replace`` 产出新
        diagnosis（friction_type/nominations 换位），reasons 追加纠正码，
        后验原样保留（审计面不动）。返回 (垫后 diagnosis, applied ids)。
        """
        if not corrections or diagnosis.outcome != "act":
            return diagnosis, []
        disconfirmed = {c.friction_type for c in corrections}
        if diagnosis.friction_type not in disconfirmed:
            return diagnosis, []
        applied = [c.friction_type for c in corrections if c.friction_type == diagnosis.friction_type]
        posterior_types = [ftype for ftype, _score in diagnosis.posterior]
        for candidate in posterior_types:
            if candidate in disconfirmed or candidate == "unknown":
                continue
            nominations = FRICTION_INTERVENTION_NOMINATIONS.get(candidate) or ()
            if nominations:
                return self._retype_diagnosis(diagnosis, candidate), applied
        # 后验无后继（单一类型证据）→ 回落根分裂问（引擎 U1 同一问），
        # 如实标注：纠正生效但没有可给的替代判断。
        return self._retype_diagnosis(
            diagnosis,
            "unknown",
            anchor=self._anchor_of(context),
        ), applied

    @staticmethod
    def _retype_diagnosis(
        diagnosis: FrictionDiagnosis,
        new_type: str,
        *,
        anchor: str | None = None,
    ) -> FrictionDiagnosis:
        """引擎 frozen 对象的垫后投影（dataclasses.replace，零引擎内改动）。"""
        if new_type != "unknown":
            nominations = FRICTION_INTERVENTION_NOMINATIONS.get(new_type) or ()
            return dataclasses.replace(
                diagnosis,
                friction_type=new_type,
                nominated_interventions=nominations,
                reasons=diagnosis.reasons + ("J1.correction_demoted_primary",),
            )
        root = FRICTION_QUESTION_BANK[0]  # q_direction_vs_push（priority=1 根分裂）
        question = OneBestQuestion(
            question_id=root.question_id,
            text=root.render(anchor),
            branch_options=tuple(
                (branch.key, branch.label) for branch in root.branches
            ),
            information_gain_bits=0.0,
            discriminates=tuple(
                sorted(set().union(*(branch.supports for branch in root.branches)))
            ),
        )
        return dataclasses.replace(
            diagnosis,
            outcome="ask",
            friction_type="unknown",
            nominated_interventions=(),
            question=question,
            reasons=diagnosis.reasons
            + (
                "J1.correction_demoted_primary",
                "J1.correction_no_alternative_root_question",
            ),
        )

    # ------------------------------------------------------------------
    # 载荷装配
    # ------------------------------------------------------------------

    def _build_payload(
        self,
        *,
        surface: str,
        context: _JourneyContext,
        diagnosis: FrictionDiagnosis,
        corrections: list[StuckJourneyCorrection],
        question_cap_reached: bool,
        extra_annotations: dict[str, Any],
    ) -> dict[str, Any]:
        if question_cap_reached:
            # 单问上限：不出第二问（B1 best-guess 的 act 判断已随引擎给出）。
            diagnosis = dataclasses.replace(
                diagnosis,
                question=None,
                reasons=diagnosis.reasons + ("J1.journey_question_cap_reached",),
            )
        diagnosis, _applied_ids = self._apply_corrections(context, diagnosis, corrections)
        diagnosis_dict = diagnosis.to_dict()

        question = diagnosis_dict.get("question")
        nominated = list(diagnosis_dict.get("nominated_interventions") or [])
        main_intervention: dict[str, Any] | None = None
        if diagnosis.outcome == "act" and nominated:
            main_intervention = {
                "type": nominated[0],
                "nominated": nominated,
                "friction_type": diagnosis.friction_type,
                # V3-FIX-51：契约面恒声明「建议非执行」（JOURNEY_INTERVENTION_DELIVERY）。
                "delivery": JOURNEY_INTERVENTION_DELIVERY,
                "uncertain": bool(diagnosis.uncertain),
                "adjusted_by_correction": any(
                    reason == "J1.correction_demoted_primary"
                    for reason in diagnosis.reasons
                ),
            }

        applied_ids = [str(record.id) for record in corrections]
        correction_active = any(
            reason.startswith("J1.") for reason in diagnosis.reasons
        )
        return {
            "version": STUCK_JOURNEY_SCHEMA_VERSION,
            "surface": surface,
            "context": self._context_facts(context),
            "outcome": diagnosis.outcome,
            "friction_type": diagnosis.friction_type,
            "question": question,
            "main_intervention": main_intervention,
            "uncertain": bool(diagnosis.uncertain),
            "diagnosis_version": diagnosis_dict.get("schema_version"),
            "receipt": {
                "receipt_type": "stuck_journey",
                "decision_reason": (
                    "卡点判断来自既有任务/目标状态证据与你的回答；不是评价。"
                ),
                "active_corrections": len(corrections),
                "correction_active": correction_active,
                "correction_no_alternative": any(
                    reason == "J1.correction_no_alternative_root_question"
                    for reason in diagnosis.reasons
                ),
                "applied_correction_ids": applied_ids,
            },
            "annotations": {
                **extra_annotations,
                "question_cap_reached": question_cap_reached,
            },
        }

    # ------------------------------------------------------------------
    # 小工具
    # ------------------------------------------------------------------

    @staticmethod
    def _anchor_of(context: _JourneyContext) -> str | None:
        if context.task is not None:
            return _strip(context.task.title)[:60] or None
        if context.goal is not None:
            return _strip(context.goal.title)[:60] or None
        return None

    @staticmethod
    def _task_last_touch(task: Task) -> datetime:
        # 直接属性判空窄化（A-07 同款纪律：getattr 无法窄化 Optional→Any 返回）。
        paused_at = task.paused_at
        updated_at = task.updated_at
        created_at = task.created_at
        if paused_at is not None and updated_at is not None and paused_at > updated_at:
            return paused_at
        if updated_at is not None:
            return updated_at
        if created_at is not None:
            return created_at
        return datetime.utcnow()

    @staticmethod
    def _signal_time(signal: Any) -> datetime | None:
        raw = getattr(signal, "occurred_at", None)
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw))
        except ValueError:
            return None


__all__ = [
    "STUCK_JOURNEY_SCHEMA_VERSION",
    "STUCK_JOURNEY_SURFACES",
    "CORRECTION_FRESHNESS_DAYS",
    "CORRECTION_MAX_ACTIVE",
    "RECENT_FAILURE_WINDOW_DAYS",
    "StuckJourneyService",
]
