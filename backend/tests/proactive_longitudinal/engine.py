"""P-05 · 多天时间线引擎：真实服务 + 可控时钟的纵向驱动.

一天（sim day d）的驱动序列（两组唯一差异在 3 步）：

1. **可控时钟推进**（``PersonaWorld.apply_clock``）：把活动痕迹/计划窗口/任务
   到期/建议投递时间/cooldown 窗口尾从模拟时刻换算成真实时间戳——随后真实服务
   内部的 ``datetime.now`` 即感知为「第 d 天」（backdate 口径与
   ``tests/aurora/test_comeback_context.py``、``dbfixture.backdate_proposal_expiry``
   同源）；
2. **内在行为**（两组共享、seed 导出）：intrinsic 自发重启日 → 经统一 command
   path 完成下一个待办任务（与主动面无关的基线行为）；
3. **主动面生成**（仅 proactive 组）：直调真实 ``comeback_nudge_task``（生产
   celery 任务函数；``app.db.session.AsyncSessionLocal`` 重定向到本世界引擎——
   基建绑定，非语义 mock）；sent/skipped 及原因（not_eligible /
   suggestion_suppressed{muted,cooldown} / duplicate_recent）全量记录；
4. **persona 决策**（seeded 模型）：accept → 经 ``ActionCommandService`` 真实
   执行（IN_PROGRESS 低风险可逆：授权下 auto / 未授权 proposal+确认；
   COMPLETED 中风险不可逆：恒 proposal+确认——P-04 风险门）；dismiss → 真实
   ``record_ignore_today``（同日 PM 探针验证 cooldown 窗口内抑制）；mute →
   真实 ``record_mute``；
5. **授权生命周期**（P-04）：首次 accept 走 grant 仪式；「被打扰到关停」谱在
   累计无行动建议达阈值时 revoke + mute。
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.proactive_longitudinal.persona import (
    SUGGESTION_TYPE,
    PersonaSpec,
    decide_disposition,
)
from tests.v3_action_eval.dbfixture import ScenarioDB

__all__ = [
    "PersonaWorld",
    "run_persona_group",
    "run_population",
    "GENERATION_SLOT_AM",
    "GENERATION_SLOT_PM",
]

#: AM 建议生成时刻（模拟日的当日钟点分数，09:00）
GENERATION_SLOT_AM = 0.375
#: PM 探针（dismiss 同日 15:00 二次生成——cooldown 窗口内抑制的纵向素材）
GENERATION_SLOT_PM = 0.625

#: comeback 任务只在单线程 executor 里跑（celery _run_async 的 worker loop 绑定线程）
_TASK_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="p05-celery-task")

_LIFECYCLE_OUTCOME_KEYS = (
    "source",
    "ledger_done",
    "ledger_total",
    "ledger_completed",
    "deadline_met",
)


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class SimClock:
    """模拟时刻 → 真实时间戳换算（tick 帧）.

    第 ``day`` 天 ``frac`` 钟点锚定到当步真实 now（墙钟单步内漂移秒级，相对日
    粒度可忽略且每步重锚定）。模拟时刻 ``s``（天）换算为 ``W - (day+frac-s) 天``。
    """

    def __init__(self, day: int, frac: float) -> None:
        self.day = day
        self.frac = frac
        self.wall = _now_naive()

    def back(self, sim_moment_days: float) -> datetime:
        return self.wall - timedelta(days=(self.day + self.frac - sim_moment_days))

    def date_offset(self, sim_day: int) -> date:
        """模拟日对应的真实 date（date 粒度语义与产品 ``days_remaining`` 一致）."""
        return self.wall.date() + timedelta(days=sim_day - self.day)

    def iso_back(self, sim_moment_days: float) -> str:
        return self.back(sim_moment_days).isoformat()


@dataclass
class _WorldState:
    """引擎内存侧 persona 状态（真实状态面在 DB；这里是时间线簿记）。"""

    completions: dict[int, float] = field(
        default_factory=dict
    )  # task order_index → sim 时刻（天）
    delivered_at: dict[str, float] = field(
        default_factory=dict
    )  # notification id → sim 时刻
    suggestion_seq: int = 0
    consecutive_non_accept: int = 0
    ignore_until_sim: float | None = None  # cooldown 窗口尾（模拟时刻）
    muted: bool = False
    auto_granted: bool = False
    first_accept_done: bool = False
    ledger_completed_at: float | None = None
    ignore_count: int = 0


class PersonaWorld:
    """一个 persona × 一个组的隔离世界（独立 sqlite 引擎 + 真实服务驱动）。"""

    def __init__(
        self,
        spec: PersonaSpec,
        *,
        group: str,
        days: int,
        day_hooks: dict[int, Any] | None = None,
    ) -> None:
        self.spec = spec
        self.group = group
        self.days = days
        self._day_hooks = day_hooks or {}
        self.state = _WorldState()
        self._world = ScenarioDB()
        self._factory = self._world.session_factory()
        self.session: AsyncSession | None = None
        self.user_id: UUID | None = None
        self.records: list[dict[str, Any]] = []

    async def __aenter__(self) -> PersonaWorld:
        await self._world.__aenter__()
        self.session = self._factory()
        await self._seed()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self.session is not None:
            await self.session.close()
        await self._world.__aexit__(*exc_info)

    # ------------------------------------------------------------------ seed

    async def _seed(self) -> None:
        from app.models.goal import Goal
        from app.models.plan import Plan, PlanStage, PlanType
        from app.models.task import Task, TaskStatus, TaskType
        from app.models.user import User

        assert self.session is not None
        spec = self.spec
        user_id = uuid4()
        self.user_id = user_id
        session = self.session
        session.add(
            User(
                id=user_id,
                username=f"p05_{spec.persona_id}_{self.group}",
                email=f"p05_{spec.persona_id}_{self.group}@eval.local",
                hashed_password="p05",
            )
        )
        await session.flush()
        plan = Plan(
            name=f"P05 {spec.arc} 计划",
            user_id=user_id,
            type=PlanType.SPRINT,
            subject="计算机网络",
            target_date=_now_naive().date(),  # 真值由 SimClock 每 tick 重写
            plan_stage=PlanStage.SPRINT,
            is_active=True,
            is_primary=True,
        )
        session.add(plan)
        await session.flush()
        goal = Goal(
            user_id=user_id,
            title="期末计算机网络冲 85 分",
            goal_type="exam",
            status="active",
            is_primary=True,
            plan_id=plan.id,
            progress=0.0,
        )
        session.add(goal)
        await session.flush()
        plan.goal_id = goal.id
        for i in range(spec.total_tasks):
            status = (
                TaskStatus.COMPLETED if i < spec.pre_completed else TaskStatus.PENDING
            )
            task = Task(
                user_id=user_id,
                plan_id=plan.id,
                title=f"任务 {i + 1} · TCP 第{i + 1}讲",
                type=TaskType.LEARNING,
                tags=["p05"],
                estimated_minutes=30,
                difficulty=2,
                energy_cost=1,
                status=status,
                order_index=i,
            )
            if status is TaskStatus.COMPLETED:
                task.completed_at = _now_naive()  # tick 时重写为模拟时刻
                self.state.completions[i] = float(
                    spec.initial_active_sim_day - (spec.pre_completed - 1 - i)
                )
            session.add(task)
        await session.commit()

    # ------------------------------------------------------------------ clock

    async def apply_clock(self, day: int, frac: float) -> SimClock:
        """把全部持久化时间戳换算到「第 day 天 frac 钟点」帧（可控时钟推进）。"""
        from app.models.notification import Notification
        from app.models.plan import Plan
        from app.models.task import Task
        from app.models.user import User
        from app.models.user_preferences import UserPreferencesCenter

        assert self.session is not None and self.user_id is not None
        clock = SimClock(day, frac)
        spec = self.spec
        session = self.session

        plan = (
            (
                await session.execute(
                    select(Plan).where(
                        Plan.user_id == self.user_id, Plan.is_active.is_(True)
                    )
                )
            )
            .scalars()
            .first()
        )
        if plan is not None:
            plan.target_date = clock.date_offset(spec.deadline_sim_day)

        tasks = (
            (
                await session.execute(
                    select(Task)
                    .where(Task.user_id == self.user_id)
                    .order_by(Task.order_index)
                )
            )
            .scalars()
            .all()
        )
        for task in tasks:
            if (
                task.status.value == "COMPLETED"
                and task.order_index in self.state.completions
            ):
                task.completed_at = clock.back(self.state.completions[task.order_index])
            elif task.status.value == "PENDING":
                task.due_date = clock.date_offset(_due_sim_day(spec, task.order_index))

        user = await session.get(User, self.user_id)
        if user is not None:
            user.last_login_at = clock.back(self._last_activity_moment())

        for notif_id, sim_moment in self.state.delivered_at.items():
            notif = await session.get(Notification, UUID(notif_id))
            if notif is not None:
                notif.created_at = clock.back(sim_moment)

        if self.state.ignore_until_sim is not None:
            row = (
                (
                    await session.execute(
                        select(UserPreferencesCenter).where(
                            UserPreferencesCenter.user_id == self.user_id
                        )
                    )
                )
                .scalars()
                .first()
            )
            if row is not None and isinstance(row.explicit, dict):
                section = dict(
                    row.explicit.get("proactive_suggestion_ignored_until") or {}
                )
                if SUGGESTION_TYPE in section:
                    section[SUGGESTION_TYPE] = clock.iso_back(
                        self.state.ignore_until_sim
                    )
                    row.explicit = {
                        **row.explicit,
                        "proactive_suggestion_ignored_until": section,
                    }

        await session.commit()
        return clock

    async def _sync_point(self) -> None:
        """celery 任务线程与主 session 的交接点：提交挂起写并失效身份图。"""
        assert self.session is not None
        await self.session.commit()
        self.session.expire_all()

    # ------------------------------------------------------------- generation

    async def _run_comeback_task(self) -> dict[str, Any]:
        """直调生产 celery 任务（真实生成/抑制/投递逻辑；仅 DB 绑定重定向）。"""
        import app.db.session as db_session_module
        from app.core.celery_tasks import comeback_nudge_task

        assert self.user_id is not None
        await self._sync_point()
        original = db_session_module.AsyncSessionLocal
        db_session_module.AsyncSessionLocal = self._factory
        try:
            user_id = str(self.user_id)
            result: dict[str, Any] = await asyncio.get_running_loop().run_in_executor(
                _TASK_EXECUTOR, lambda: comeback_nudge_task(user_id)
            )
        finally:
            db_session_module.AsyncSessionLocal = original
        await self._sync_point()
        return dict(result)

    async def _latest_notification(self) -> dict[str, Any] | None:
        from app.models.notification import Notification

        assert self.session is not None and self.user_id is not None
        # 只取建议本体（任务完成会连带 achievement 等其他类型通知，不属评估对象）
        row = (
            (
                await self.session.execute(
                    select(Notification)
                    .where(
                        Notification.user_id == self.user_id,
                        Notification.type == SUGGESTION_TYPE,
                        Notification.deleted_at.is_(None),
                    )
                    .order_by(Notification.created_at.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if row is None:
            return None
        return {
            "id": str(row.id),
            "title": row.title,
            "content": row.content,
            "data": dict(row.data or {}),
        }

    # ----------------------------------------------------------------- actions

    async def _pending_tasks(self) -> list[Any]:
        from app.models.task import Task, TaskStatus

        assert self.session is not None and self.user_id is not None
        rows = (
            (
                await self.session.execute(
                    select(Task)
                    .where(
                        Task.user_id == self.user_id,
                        Task.status == TaskStatus.PENDING,
                        Task.deleted_at.is_(None),
                    )
                    .order_by(Task.order_index)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def _complete_next_task(
        self, *, sim_moment: float, source: str
    ) -> dict[str, Any]:
        """persona 行动面：经统一 command path 启动并完成下一个待办（真实服务）。"""
        from app.core.action_command import ActionCommandType, ProposalStatus
        from app.services.action_command_service import ActionCommandService

        assert self.session is not None and self.user_id is not None
        pending = await self._pending_tasks()
        if not pending:
            return {"source": source, "outcome": "no_pending_task"}
        task = pending[0]
        actions: list[dict[str, Any]] = []
        service = ActionCommandService(self.session)
        for to_status in ("IN_PROGRESS", "COMPLETED"):
            result = await service.create_proposal(
                user_id=self.user_id,
                command_type=ActionCommandType.TASK_UPDATE_STATUS.value,
                payload={"task_id": str(task.id), "to_status": to_status},
                execute_if_authorized=True,
            )
            mode = str(result.proposal.authorization.get("mode"))
            reasons = list(result.proposal.authorization.get("reason_codes") or [])
            if result.proposal.status is ProposalStatus.PENDING:
                # auto 未覆盖（未授权 / 中风险不可逆）→ persona 确认（行动本身即用户意愿）
                committed = await service.approve(
                    result.proposal.id, user_id=self.user_id
                )
                executed = bool(committed.applied)
            else:
                executed = result.proposal.status is ProposalStatus.COMMITTED
            actions.append(
                {
                    "step": to_status,
                    "mode": mode,
                    "reason_codes": reasons,
                    "executed": executed,
                    "task_id": str(task.id),
                }
            )
        self.state.completions[task.order_index] = sim_moment
        await self._sync_point()
        ledger_done = len(self.state.completions)
        outcome: dict[str, Any] = {
            "source": source,
            "actions": actions,
            "ledger_done": ledger_done,
            "ledger_total": self.spec.total_tasks,
        }
        if (
            ledger_done >= self.spec.total_tasks
            and self.state.ledger_completed_at is None
        ):
            self.state.ledger_completed_at = sim_moment
            outcome["ledger_completed"] = True
            outcome["deadline_met"] = sim_moment <= self.spec.deadline_sim_day
        return outcome

    async def _grant_auto(self) -> None:
        """P-04 授权仪式：总开关 + auto-eligible 类别 grant（真实授权面）。"""
        from app.models.user_settings import UserSettings
        from app.services.action_permission_service import ActionPermissionService

        assert self.session is not None and self.user_id is not None
        session = self.session
        row = (
            (
                await session.execute(
                    select(UserSettings).where(UserSettings.user_id == self.user_id)
                )
            )
            .scalars()
            .first()
        )
        if row is None:
            session.add(UserSettings(user_id=self.user_id, low_risk_auto_execute=True))
        else:
            row.low_risk_auto_execute = True
        permissions = ActionPermissionService(session)
        for category in ("task.update_status", "task.update_fields"):
            await permissions.grant_category(self.user_id, category)
        self.state.auto_granted = True
        await self._sync_point()

    async def _revoke_auto(self) -> None:
        from app.services.action_permission_service import ActionPermissionService

        assert self.session is not None and self.user_id is not None
        permissions = ActionPermissionService(self.session)
        for category in ("task.update_status", "task.update_fields"):
            await permissions.revoke_category(self.user_id, category)
        self.state.auto_granted = False
        await self._sync_point()

    async def _apply_feedback(
        self, disposition: str, *, sim_moment: float
    ) -> dict[str, Any]:
        """P-03 反馈回路（真实服务调用；cooldown 尾以模拟时刻记账、tick 时换算）。"""
        from app.services.proactive_suggestion_service import (
            ProactiveSuggestionFeedbackService,
        )

        assert self.session is not None and self.user_id is not None
        service = ProactiveSuggestionFeedbackService(self.session)
        if disposition == "mute":
            result = await service.record_mute(self.user_id, SUGGESTION_TYPE)
            self.state.muted = True
            return dict(result)
        if disposition == "dismiss":
            result = await service.record_ignore_today(self.user_id, SUGGESTION_TYPE)
            self.state.ignore_until_sim = sim_moment + 1.0  # 24h 窗口尾（模拟时刻）
            self.state.ignore_count += 1
            return dict(result)
        return {"reason": "silent_ignore"}

    # -------------------------------------------------------------- day loop

    def _record(self, kind: str, payload: dict[str, Any]) -> None:
        self.records.append(
            {
                "kind": kind,
                "group": self.group,
                "persona": self.spec.persona_id,
                "arc": self.spec.arc,
                **payload,
            }
        )

    def _last_activity_moment(self) -> float:
        return max(
            self.state.completions.values(),
            default=float(self.spec.initial_active_sim_day),
        )

    async def run(self) -> list[dict[str, Any]]:
        spec = self.spec
        proactive = self.group == "proactive"
        for day in range(self.days):
            await self.apply_clock(day, GENERATION_SLOT_AM)

            # 1) 内在行为（两组共享）：自发重启完成一个待办
            if day in spec.intrinsic_restart_days:
                outcome = await self._complete_next_task(
                    sim_moment=day + 0.2, source="intrinsic"
                )
                self._record(
                    "lifecycle",
                    {
                        "sim_day": day,
                        "event": "intrinsic_restart",
                        **_compact_outcome(outcome),
                    },
                )

            last_activity_day = int(self._last_activity_moment())
            days_remaining = max(0, spec.deadline_sim_day - day)
            self._record(
                "day",
                {
                    "sim_day": day,
                    "days_away": max(0, day - last_activity_day),
                    "days_remaining": days_remaining,
                    "stalled": (day - last_activity_day) >= 3,
                    "ledger_done": len(self.state.completions),
                    "ledger_total": spec.total_tasks,
                    "plan_expired": spec.deadline_sim_day < day,
                    "ledger_completed_at": self.state.ledger_completed_at,
                    "muted": self.state.muted,
                },
            )

            if not proactive:
                continue

            # 2) 主动面生成（真实任务）+ persona 决策 + 行动/反馈
            gen = await self._run_comeback_task()
            gen_record: dict[str, Any] = {
                "sim_day": day,
                "slot": "am",
                "result": str(gen.get("status")),
                "reason": gen.get("reason"),
                "suppression": gen.get("suppression"),
            }
            self._record("generation", gen_record)
            if gen.get("status") == "sent":
                notif = await self._latest_notification()
                assert notif is not None
                # 生成时刻语义：账本是否在建议投放前就已完成（负担反例判据——
                # 必须在决策/行动前取值，accept 完成最后一个任务不算"完成后投放"）
                ledger_complete_at_gen = self.state.ledger_completed_at is not None
                self.state.delivered_at[notif["id"]] = day + GENERATION_SLOT_AM
                self.state.suggestion_seq += 1
                await self.apply_clock(day, GENERATION_SLOT_AM)
                days_away_at_gen = max(0, day - int(self._last_activity_moment()))
                disposition = decide_disposition(
                    spec,
                    sim_day=day,
                    slot="am",
                    suggestion_seq=self.state.suggestion_seq,
                    consecutive_non_accept=self.state.consecutive_non_accept,
                )
                action_outcome: dict[str, Any] | None = None
                if disposition == "accept":
                    if (
                        not self.state.first_accept_done
                        and spec.auto_grant_on_first_accept
                    ):
                        await self._grant_auto()
                        self.state.first_accept_done = True
                        self._record(
                            "lifecycle", {"sim_day": day, "event": "auto_grant"}
                        )
                    action_outcome = await self._complete_next_task(
                        sim_moment=day + GENERATION_SLOT_AM, source="suggestion"
                    )
                    self.state.consecutive_non_accept = 0
                else:
                    self.state.consecutive_non_accept += 1
                    gen_record["persona_feedback"] = await self._apply_feedback(
                        disposition, sim_moment=day + GENERATION_SLOT_AM
                    )
                self._record(
                    "suggestion",
                    {
                        "sim_day": day,
                        "slot": "am",
                        "suggestion_seq": self.state.suggestion_seq,
                        "notification_id": notif["id"],
                        "days_away": days_away_at_gen,
                        "days_remaining": notif["data"].get("days_remaining"),
                        "why_now": notif["data"].get("why_now"),
                        "suggested_action": notif["data"].get("suggested_action"),
                        "destination_route": notif["data"].get("destination_route"),
                        "disposition": disposition,
                        "fatigue_level": round(
                            min(
                                spec.fatigue_step * self.state.consecutive_non_accept,
                                0.6,
                            ),
                            3,
                        ),
                        "action": (
                            _compact_outcome(action_outcome) if action_outcome else None
                        ),
                        "ledger_done_after": len(self.state.completions),
                        "post_ledger_complete": ledger_complete_at_gen,
                    },
                )

                # dismiss 同日 PM 探针：cooldown 窗口内二次生成必须被真源抑制
                if disposition == "dismiss":
                    gen_pm = await self._run_comeback_task()
                    self._record(
                        "generation",
                        {
                            "sim_day": day,
                            "slot": "pm",
                            "result": str(gen_pm.get("status")),
                            "reason": gen_pm.get("reason"),
                            "suppression": gen_pm.get("suppression"),
                            "probe": "cooldown_mid_window",
                        },
                    )

            # 3) 「被打扰到关停」反例谱：累计无行动建议达阈值 → revoke + mute
            if (
                spec.revoke_after_ignores is not None
                and self.state.ignore_count >= spec.revoke_after_ignores
            ):
                if self.state.auto_granted:
                    await self._revoke_auto()
                    self._record(
                        "lifecycle",
                        {"sim_day": day, "event": "auto_revoke", "trigger": "burden"},
                    )
                if not self.state.muted:
                    await self._apply_feedback(
                        "mute", sim_moment=day + GENERATION_SLOT_PM
                    )
                    self._record(
                        "lifecycle",
                        {"sim_day": day, "event": "persona_mute", "trigger": "burden"},
                    )

            # 4) 逐日钩子（测试/反例谱注入点：手动 revoke、grant 等时间线事件）
            hook = self._day_hooks.get(day)
            if hook is not None:
                await hook(self)
        return self.records


# --------------------------------------------------------------------- helpers


def _due_sim_day(spec: PersonaSpec, order_index: int) -> int:
    """任务到期日谱：stalled 首任务已逾期（诚实 stale 谱）、deadline 紧贴窗口、completion 在未来。"""
    if spec.arc == "stalled":
        return order_index - 3
    if spec.arc == "deadline":
        return order_index - 1
    return order_index + 2


def _compact_outcome(outcome: dict[str, Any] | None) -> dict[str, Any]:
    if not outcome:
        return {}
    kept = {
        k: v
        for k, v in outcome.items()
        if k in _LIFECYCLE_OUTCOME_KEYS or k in ("actions", "outcome")
    }
    return kept


# ------------------------------------------------------------------ population


async def run_persona_group(
    specs: list[PersonaSpec], *, group: str, days: int
) -> list[dict[str, Any]]:
    """顺序跑一组 persona（每人独立世界；串行避免 executor/连接争用）。"""
    records: list[dict[str, Any]] = []
    for spec in specs:
        async with PersonaWorld(spec, group=group, days=days) as world:
            records.extend(await world.run())
    return records


async def run_population(
    specs: list[PersonaSpec], *, groups: tuple[str, ...], days: int
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        out[group] = await run_persona_group(specs, group=group, days=days)
    return out
