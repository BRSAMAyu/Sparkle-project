"""V4-I01 · EpisodeResumeView 聚合服务 —— 目标 Episode 接续读模型的唯一 IO 入口。

真源纪律（B05 §1 映射表 + 卡 V4-I01 铁律「不建第二任务真值」）：
- 本服务**只读**：goal/task/run/outcome/subtask/plan 行 + OutcomeLedger 读面 +
  memory epoch 读侧，全部为既有权威；零写路径、零新表、零迁移、零模型调用。
- 视图按需计算、带 TTL（``expires_at``），**不落第二真值表**——任何与权威不一致
  → 重建视图（重算），不就地修补（B05 §5 原文）。
- 任何降级都给**类型化原因**（:data:`RESUME_DEGRADE_REASONS` 封闭词表），不出半真
  视图：已删对象不复活、跨用户拒绝（I3 + 安全遥测日志）、goal 终态/绑定不一致
  → 退回明确校准（旧计划不强推）、无本轮 ContextSelectionReceipt ref 不出视图。

数据流（首页装载时）：调用方先完成上下文选择并取得 ``context_selection://`` ref
（B05 §2：receipt 在 resume view 返回之前），再调 :meth:`build_resume_view`；
返回 :class:`EpisodeResumeResult`（view 或降级原因 + WARN 收集）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.action_command import version_token
from app.core.action_plan import action_plan_projection
from app.core.episode_resume_view import (
    CONTEXT_SELECTION_REF_SCHEME,
    assemble_resume_view,
    normalize_why_now,
    validate_resume_view_shape,
)
from app.core.run_state_machine import ACTIVE_RUN_STATUSES
from app.core.time_utils import utcnow
from app.models.agent_run import AgentRun
from app.models.goal import Goal
from app.models.plan import Plan
from app.models.task import CognitiveOwnership, SubTask, SubTaskStatus, Task, TaskStatus
from app.services.memory_service import MemoryService
from app.services.outcome_ledger_service import OutcomeLedgerService

#: 视图默认 TTL（秒）。风格对齐 X-03 ``DEFAULT_PROPOSAL_TTL_SECONDS``（30 分钟）：
#: 接续视图按首页装载按需计算，TTL 只覆盖「同轮呈现」窗口，过期即重算。
DEFAULT_RESUME_VIEW_TTL_SECONDS = 30 * 60

#: 视图 TTL 上限（秒）：不超过 X-03 ``MAX_PROPOSAL_TTL_SECONDS`` 的 24h 风格。
MAX_RESUME_VIEW_TTL_SECONDS = 24 * 3600

#: ``pending_human_step`` 允许出现的服务任务状态集：COMPLETED 无待办、ABANDONED
#: 旧计划不强推——两者一律 null（测试钉死）。
PENDING_STEP_TASK_STATUSES: frozenset[TaskStatus] = frozenset(
    {
        TaskStatus.PENDING,
        TaskStatus.IN_PROGRESS,
        TaskStatus.PAUSED,
        TaskStatus.STUCK,
        TaskStatus.RESTORE,
    }
)

#: goal 进入这些终态 → 目标已改变/关闭，旧计划退回明确校准（「目标改变」的
#: 可判定权威面；细粒度内容变更检测受限于无 goal 版本绑定列，见卡 limitations）。
GOAL_CLOSED_STATUSES: frozenset[str] = frozenset({"completed", "archived", "cancelled"})

#: outcome 账本按任务关联扫描的有界页参数（读面 keyset 分页，最多扫 3 页）。
_OUTCOME_SCAN_PAGE_SIZE = 100
_OUTCOME_SCAN_MAX_PAGES = 3


@dataclass(frozen=True)
class EpisodeResumeResult:
    """聚合结果：``view`` 与 ``reason_code`` 互斥——有视图必有权威面，降级必有原因。"""

    view: dict[str, Any] | None
    reason_code: str | None = None
    #: WARN 收集（如 why_now 字段级降级原因），带 task 标识由服务层日志留痕。
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def degraded(self) -> bool:
        return self.view is None


class EpisodeResumeService:
    """``episode_resume_view.v1`` 聚合器（只读；无第二真值、无写路径）。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def build_resume_view(
        self,
        *,
        user_id: UUID | str,
        task_id: UUID | str,
        context_receipt_ref: str,
        goal_id: UUID | str | None = None,
        now: datetime | None = None,
        ttl_seconds: int = DEFAULT_RESUME_VIEW_TTL_SECONDS,
    ) -> EpisodeResumeResult:
        """聚合既有权威为接续视图；不可聚合时返回类型化降级（视图不出）。

        ``context_receipt_ref`` 必填（B05 §2：ContextSelectionReceipt 在 resume
        view 返回之前产生；本卡只绑 ref、不实现 receipt 本体）。``goal_id`` 可
        显式指定（缺省经 ``task.plan_id → plans.goal_id`` 既有链路解析）。
        """
        now = now or utcnow()
        warnings: list[str] = []

        if (
            not isinstance(ttl_seconds, int)
            or isinstance(ttl_seconds, bool)
            or not (0 < ttl_seconds <= MAX_RESUME_VIEW_TTL_SECONDS)
        ):
            raise ValueError(f"ttl_seconds must be int in (0, {MAX_RESUME_VIEW_TTL_SECONDS}], got {ttl_seconds!r}")
        if (
            not isinstance(context_receipt_ref, str)
            or context_receipt_ref.split("://", 1)[0] != CONTEXT_SELECTION_REF_SCHEME
        ):
            return EpisodeResumeResult(
                view=None,
                reason_code="context_receipt_missing",
                warnings=("context_receipt_ref missing or wrong scheme (context_selection://)",),
            )

        user_id_str = str(user_id)
        task_id_str = str(task_id)

        # ── 1. task 权威行（存在 + 未删 + 属主）──────────────────────────
        task = (
            await self.db.execute(select(Task).where(Task.id == task_id, Task.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if task is None:
            return EpisodeResumeResult(view=None, reason_code="object_not_found")
        if str(task.user_id) != user_id_str:
            # I3：跨对象拒绝——拒绝不 500 泄漏、不静默跨读；记安全遥测（WARN 留痕）
            logger.warning(
                "EpisodeResumeView 跨对象访问拒绝 (task_id={}, caller={}, owner={})",
                task_id_str,
                user_id_str,
                task.user_id,
            )
            return EpisodeResumeResult(view=None, reason_code="cross_object_access")

        # ── 2. goal 权威解析（显式指定或 plan 链路）───────────────────────
        resolved_goal_id = str(goal_id) if goal_id is not None else None
        if resolved_goal_id is None:
            if task.plan_id is None:
                return EpisodeResumeResult(view=None, reason_code="goal_unresolved")
            plan = (
                await self.db.execute(select(Plan).where(Plan.id == task.plan_id, Plan.deleted_at.is_(None)))
            ).scalar_one_or_none()
            if plan is None:
                return EpisodeResumeResult(view=None, reason_code="goal_unresolved")
            if str(plan.user_id) != user_id_str:
                logger.warning(
                    "EpisodeResumeView 跨对象访问拒绝 (plan_id={}, caller={}, owner={})",
                    plan.id,
                    user_id_str,
                    plan.user_id,
                )
                return EpisodeResumeResult(view=None, reason_code="cross_object_access")
            if plan.goal_id is None:
                return EpisodeResumeResult(view=None, reason_code="goal_unresolved")
            resolved_goal_id = str(plan.goal_id)

        goal = (
            await self.db.execute(select(Goal).where(Goal.id == resolved_goal_id, Goal.deleted_at.is_(None)))
        ).scalar_one_or_none()
        if goal is None:
            return EpisodeResumeResult(view=None, reason_code="object_not_found")
        if str(goal.user_id) != user_id_str:
            logger.warning(
                "EpisodeResumeView 跨对象访问拒绝 (goal_id={}, caller={}, owner={})",
                resolved_goal_id,
                user_id_str,
                goal.user_id,
            )
            return EpisodeResumeResult(view=None, reason_code="cross_object_access")

        # ── 3. 「目标改变 → 退回明确校准」门（旧计划不强推）────────────────
        if str(getattr(goal, "status", "") or "") in GOAL_CLOSED_STATUSES:
            return EpisodeResumeResult(
                view=None,
                reason_code="goal_changed_requires_calibration",
                warnings=(f"goal {resolved_goal_id} status={goal.status} closed — resume view withheld",),
            )
        plan_goal_refs = {
            ref
            for ref in (getattr(task, "source_refs", None) or ())
            if isinstance(ref, str) and ref.startswith("goal://")
        }
        if plan_goal_refs and f"goal://{resolved_goal_id}" not in plan_goal_refs:
            return EpisodeResumeResult(
                view=None,
                reason_code="goal_changed_requires_calibration",
                warnings=(
                    f"task plan bound to {sorted(plan_goal_refs)} but resolved goal is goal://{resolved_goal_id}",
                ),
            )

        # ── 4. 在途 run（X-05 agent_runs 唯一持久真源；终态不进 run_ref）────
        run = (
            await self.db.execute(
                select(AgentRun)
                .where(
                    AgentRun.task_id == task.id,
                    AgentRun.user_id == task.user_id,
                    AgentRun.status.in_([s.value for s in ACTIVE_RUN_STATUSES]),
                )
                .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        # ── 5. 上次已确认位置（subtask 完成戳优先，task 级确认/完成兜底）────
        last_step = await self._last_confirmed_step(task)

        # ── 6. 等待人类步骤（X-01 ActionPlan 统一读侧门；完成/放弃任务不出）──
        pending_step = self._pending_human_step(task, warnings)

        # ── 7. why_now（action_plan.v1.1 字段位投影；v1 行 = null）─────────
        why_now, why_now_reason = normalize_why_now(getattr(task, "why_now", None), now=now)
        if why_now_reason is not None:
            # §4.1 字段级降级：仅 why_now 置 null + WARN（带 task_id 与原因），
            # 视图其余字段不受影响。
            warnings.append(f"why_now degraded: {why_now_reason}")
            logger.warning("EpisodeResumeView why_now 字段级降级 (task_id={}): {}", task_id_str, why_now_reason)

        # ── 8. last_valid_outcome（D-02 账本读面；truth_class 全 5 值 1:1）──
        last_outcome = await self._last_valid_outcome(user_id=user_id_str, task_id=task_id_str, until=now)

        # ── 9. memory epoch（C-07：读失败按 0 → 与任何快照必不一致 → 重算）──
        memory_epoch = await self._memory_epoch(user_id_str)

        computed_at = now.replace(tzinfo=None)
        expires_at = computed_at + timedelta(seconds=ttl_seconds)
        view = assemble_resume_view(
            goal_id=resolved_goal_id,
            task_id=task_id_str,
            run_id=str(run.id) if run is not None else None,
            last_outcome=last_outcome,
            last_step=last_step,
            pending_step=pending_step,
            why_now=why_now,
            computed_at=computed_at,
            expires_at=expires_at,
            context_receipt_ref=context_receipt_ref,
            memory_epoch=memory_epoch,
        )
        shape_violations = validate_resume_view_shape(view)
        if shape_violations:  # pragma: no cover — 防御：冻结结构漂移必须 fail-loud
            raise ValueError(f"resume view shape violations: {shape_violations}")
        return EpisodeResumeResult(view=view, reason_code=None, warnings=tuple(warnings))

    # ------------------------------------------------------------------
    # 内部：各权威只读面
    # ------------------------------------------------------------------

    async def _last_confirmed_step(self, task: Task) -> dict[str, Any] | None:
        """上次已确认位置：最新完成 subtask 优先，task 级确认/完成戳兜底，无则 null。

        version_token 复用 X-03 ``action_command.version_token``（updated_at 令牌）。
        """
        subtask = (
            await self.db.execute(
                select(SubTask)
                .where(
                    SubTask.parent_task_id == task.id,
                    SubTask.status == SubTaskStatus.COMPLETED,
                    SubTask.completed_at.is_not(None),
                )
                .order_by(SubTask.completed_at.desc(), SubTask.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if subtask is not None:
            return {
                "step_ref": f"subtask://{subtask.id}",
                "description": subtask.title,
                "confirmed_at": subtask.completed_at,
                "version_token": version_token(subtask.updated_at),
            }
        anchors = [t for t in (task.completed_at, task.confirmed_at) if t is not None]
        if anchors:
            confirmed_at = max(anchors)
            return {
                "step_ref": f"task://{task.id}",
                "description": task.title,
                "confirmed_at": confirmed_at,
                "version_token": version_token(task.updated_at),
            }
        return None

    def _pending_human_step(self, task: Task, warnings: list[str]) -> dict[str, Any] | None:
        """等待人类步骤：X-01 ActionPlan（统一读侧门）投影；不可得 → null 不造。

        - legacy 行 / 计划损坏 → 统一门整块降级 None → pending 为 null（诚实降级）；
        - COMPLETED / ABANDONED 任务无待办 → null（旧计划不强推）。
        """
        if task.status not in PENDING_STEP_TASK_STATUSES:
            return None
        projection = action_plan_projection(task)
        if projection is None:
            warnings.append("pending_human_step unavailable: no valid action_plan projection")
            return None
        return {
            "description": projection["smallest_useful_step"]["description"],
            "cognitive_ownership": CognitiveOwnership(projection["cognitive_ownership"]).value,
            "execution_mode": projection["execution_mode"],
        }

    async def _last_valid_outcome(self, *, user_id: str, task_id: str, until: datetime) -> dict[str, Any] | None:
        """D-02 账本读面：与 task 关联的最新 outcome（correlation.task_id 匹配）。

        有界 keyset 扫描（复用 ``OutcomeLedgerService.query`` 公共读面，页大小
        100 × 最多 3 页）；找不到 → null——**不得**以「练了 N 分钟」类替代呈现
        （MASTER_DESIGN §6）。``truth_class`` 全 5 值 1:1 透传（demo 不排除）。
        """
        ledger = OutcomeLedgerService(self.db)
        cursor: str | None = None
        for _page in range(_OUTCOME_SCAN_MAX_PAGES):
            page = await ledger.query(user_id=user_id, until=until, limit=_OUTCOME_SCAN_PAGE_SIZE, cursor=cursor)
            for entry in page.items:
                if entry.correlation.get("task_id") == task_id:
                    return {
                        "outcome_id": entry.outcome_id,
                        "truth_class": entry.truth_class.value,
                        "recorded_at": entry.occurred_at,
                    }
            if not page.next_cursor:
                break
            cursor = page.next_cursor
        return None

    async def _memory_epoch(self, user_id: str) -> int:
        """C-07 memory epoch 读侧；读失败按 0 处理（context_manager 同纪律）→ 必不一致 → 重算。"""
        try:
            return int(await MemoryService(self.db).get_memory_epoch(user_id))
        except Exception as exc:  # noqa: BLE001 — 与 context_manager._get_memory_epoch 同口径
            logger.warning("EpisodeResumeView memory epoch 读失败 (user_id={}): {}", user_id, exc)
            return 0


__all__ = [
    "DEFAULT_RESUME_VIEW_TTL_SECONDS",
    "GOAL_CLOSED_STATUSES",
    "MAX_RESUME_VIEW_TTL_SECONDS",
    "PENDING_STEP_TASK_STATUSES",
    "EpisodeResumeResult",
    "EpisodeResumeService",
]
