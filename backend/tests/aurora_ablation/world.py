"""A-08 · PersonaWorld：一个 persona × 一个臂的隔离世界（真实服务 + 可控时钟）。

基建口径（P-05 同款纪律）：
- **DB**：sqlite+aiosqlite 内存引擎 + ``Base.metadata.create_all`` 真实 schema
  （``tests.v3_action_eval.dbfixture.ScenarioDB`` 同源）；真实服务直接构造。
- **Redis**：fakeredis（``tests/services/test_friction_chat_wiring.py`` 同款
  基建绑定——spine 状态 / pending 问句 / 预算计数的真实存取路径）。
- **可控时钟**：模拟日 → 真实时间戳的 backdate 换算（与
  ``tests/proactive_longitudinal/engine.py`` 同源）。世界侧写入（Task 痕迹/
  spine 状态/lifecycle occurred_at）按模拟时刻落；带 ``now`` 通道的服务直传
  模拟时刻；``onupdate`` 时钟戳用 Core update 显式值覆盖（防真实墙钟污染）。
- **世界侧写入（persona 的世界事实，非 Aurora 语义）**：User/Plan/Goal/Task
  行按时间线直接落库（persona 的学习世界是模拟对象，与 P-05 种子同法）；
  **Aurora 语义零直写**——决策/问句/纠正/patch/lifecycle 全部经真实服务。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import fakeredis.aioredis
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from tests.aurora_ablation.persona import EPISODE_SESSION_BUDGET, Episode, PersonaSpec
from tests.v3_action_eval.dbfixture import ScenarioDB

__all__ = ["PersonaWorld", "sim_clock"]

#: spine 状态 scope/TTL（真实 spine 词表内 day 档 48h——经验状态的「近期」
#: 语义；过期由真实 ``_scan_expired``/``expire_stale`` 在 backdate 时间戳上判定）。
_SPINE_SCOPE = "day"
_SPINE_TTL_HOURS = 48

#: spine 状态键 → claim（真实 ``_RULE_TABLE`` 既有 claim 值域）。
_SPINE_CLAIMS: dict[str, str] = {
    "task_granularity_fit": "recent_task_too_large",
    "knowledge_transfer": "transfer_failure",
    "affective_pressure": "affective_pressure_detected",
    "goal_mode": "deadline_pressure_detected",
    "growth_momentum": "momentum_shifting",
    "recall_needed": "recall_opportunity_missed",
    "community_cohort_pattern": "peer_pattern_detected",
    "material_utilization": "material_underutilized",
}


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def sim_clock(day: int, frac: float = 0.5) -> tuple[datetime, Any]:
    """模拟日时刻 → （该时刻的真实时间戳, iso 形式）。

    锚定到当步真实 now（墙钟单步内漂移秒级，日粒度可忽略；每会话重锚定，
    同 P-05 SimClock 口径）。
    """
    wall = _now_naive()
    moment = wall - timedelta(days=(day + frac))
    return moment, wall


class PersonaWorld:
    """一个 persona × 一个臂的隔离世界。

    ``arm`` 决定能力面消融（输入投影面；产品代码零改动）：
    - ``no_memory``：失败痕迹/纠正不落库（旅程面读不到历史）；
    - ``no_experience``：spine 不写、patch 不提议（engine 侧短路）；
    - ``fixed_policy``：world 照常，引擎调用在 engine 侧短路。
    """

    def __init__(self, spec: PersonaSpec, *, arm: str) -> None:
        self.spec = spec
        self.arm = arm
        self._db = ScenarioDB()
        self._factory = self._db.session_factory()
        self.session: AsyncSession | None = None
        self.redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        self.user_id: UUID | None = None
        self.plan_id: UUID | None = None
        self.goal_id: UUID | None = None
        self.episode_task_id: UUID | None = None
        self.resolved_refs: dict[str, list[str]] = {}  # friction_tag → [decision_id]
        self.resolved_episode_count = 0

    async def __aenter__(self) -> PersonaWorld:
        await self._db.__aenter__()
        self.session = self._factory()
        await self._seed()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self.session is not None:
            await self.session.close()
        try:
            await self.redis.aclose()
        except Exception:  # noqa: BLE001 — fakeredis 关闭容错
            pass
        await self._db.__aexit__(*exc_info)

    # ------------------------------------------------------------------ seed

    async def _seed(self) -> None:
        from app.models.goal import Goal
        from app.models.plan import Plan, PlanStage, PlanType
        from app.models.user import User

        assert self.session is not None
        session = self.session
        user_id = uuid4()
        self.user_id = user_id
        session.add(
            User(
                id=user_id,
                username=f"a08_{self.spec.persona_id}_{self.arm}",
                email=f"a08_{self.spec.persona_id}_{self.arm}@eval.local",
                hashed_password="a08",
            )
        )
        await session.flush()
        plan = Plan(
            name=f"A08 {self.spec.arc} 计划",
            user_id=user_id,
            type=PlanType.SPRINT,
            subject="计算机网络",
            target_date=_now_naive().date(),
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
        self.plan_id = plan.id
        self.goal_id = goal.id
        await session.commit()

    # ------------------------------------------------------------------ time

    async def now_at(self, day: int) -> datetime:
        moment, _ = sim_clock(day)
        return moment

    # ------------------------------------------------------- episode world

    async def begin_episode_world(self, episode: Episode, day: int) -> None:
        """卡点段开局：当前任务 STUCK（backdate 停滞起点）+ 失败痕迹
        （no_memory 臂不落历史）+ spine 经验状态（no_experience 臂不写）。"""
        from app.models.task import Task, TaskStatus, TaskType

        assert self.session is not None and self.user_id is not None
        session = self.session
        moment, _ = sim_clock(day)
        stalled_at = moment - timedelta(days=episode.days_stalled)
        task = Task(
            user_id=self.user_id,
            plan_id=self.plan_id,
            title=f"任务 · TCP {episode.friction_type} 关卡",
            type=TaskType.LEARNING,
            tags=["a08"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.STUCK,
            order_index=day,
            updated_at=stalled_at,
            created_at=stalled_at,
            paused_at=stalled_at,
        )
        session.add(task)
        await session.flush()
        self.episode_task_id = task.id

        if self.arm != "no_memory" and episode.failure_count > 0:
            for i in range(episode.failure_count):
                failed_at = moment - timedelta(days=(i + 1) * 1.5)
                session.add(
                    Task(
                        user_id=self.user_id,
                        plan_id=self.plan_id,
                        title=f"尝试 {i + 1} · {episode.friction_type} 练习",
                        type=TaskType.LEARNING,
                        tags=["a08"],
                        estimated_minutes=30,
                        difficulty=2,
                        energy_cost=1,
                        status=TaskStatus.ABANDONED,
                        order_index=day - 100 - i,
                        updated_at=failed_at,
                        created_at=failed_at,
                    )
                )
        await session.commit()

        if self.arm != "no_experience":
            from tests.aurora_ablation.persona import friction_spine_key

            await self.write_spine_state(friction_spine_key(episode.friction_type), day)

    async def complete_episode_task(self, day: int) -> None:
        """段收口（解决）：当前任务 COMPLETED @ 模拟时刻（进度锚推进）。"""
        from app.models.task import TaskStatus

        await self._close_episode_task(TaskStatus.COMPLETED, day, resolved=True)
        self.resolved_episode_count += 1

    async def abandon_episode_task(self, day: int) -> None:
        """段收口（放弃）：预算内未走出。

        - 默认臂：ABANDONED @ 模拟时刻（真实失败痕迹——下一段旅程可读）；
        - no_memory 臂：软删（deleted_at @ 模拟时刻）——「失败不留可检索痕迹」
          的无记忆基线语义。
        """
        from app.models.task import TaskStatus

        if self.arm == "no_memory":
            await self._soft_delete_episode_task(day)
            return
        await self._close_episode_task(TaskStatus.ABANDONED, day, resolved=False)

    async def _close_episode_task(self, status: Any, day: int, *, resolved: bool) -> None:
        from app.models.task import Task

        assert self.session is not None
        if self.episode_task_id is None:
            return
        moment, _ = sim_clock(day)
        values: dict[str, Any] = {
            "status": status,
            "updated_at": moment,  # 显式值覆盖 onupdate（可控时钟纪律）
        }
        if resolved:
            values["completed_at"] = moment
        else:
            values["paused_at"] = moment
        await self.session.execute(
            update(Task).where(Task.id == self.episode_task_id).values(**values)
        )
        await self.session.commit()
        self.episode_task_id = None

    async def _soft_delete_episode_task(self, day: int) -> None:
        from app.models.task import Task

        assert self.session is not None
        if self.episode_task_id is None:
            return
        moment, _ = sim_clock(day)
        await self.session.execute(
            update(Task)
            .where(Task.id == self.episode_task_id)
            .values(deleted_at=moment, updated_at=moment)
        )
        await self.session.commit()
        self.episode_task_id = None

    async def refresh_goal_progress(self) -> None:
        from app.models.goal import Goal

        assert self.session is not None and self.goal_id is not None
        goal = await self.session.get(Goal, self.goal_id)
        if goal is not None:
            goal.progress = min(1.0, 0.1 * self.resolved_episode_count)
            await self.session.commit()

    # ------------------------------------------------------- spine（经验面）

    async def write_spine_state(self, state_key: str, day: int, *, confidence: float = 0.72) -> None:
        """真实 spine ``StateRegister.upsert_from_signal`` + ``last_updated_at``
        backdate 重写（过期语义交由真实 ``_is_expired``/``expire_stale``）。"""
        from app.signals.state_register import StateRegister
        from app.signals.types import ActionableSignal

        assert self.user_id is not None
        claim = _SPINE_CLAIMS.get(state_key, "observed")
        signal = ActionableSignal(
            signal_id=f"a08_{self.spec.persona_id}_d{day}_{state_key}",
            source_event_ids=[f"sim://a08/{self.spec.persona_id}/d{day}"],
            source_system="task_service",
            state_key=state_key,
            claim=claim,
            confidence=confidence,
            scope=_SPINE_SCOPE,
            ttl_hours=_SPINE_TTL_HOURS,
            evidence_summary=f"A-08 纵向时间线：模拟日 {day} 的行为信号（persona {self.spec.persona_id}）",
            possible_effects=["ExecutionDirective"],
            priority="medium",
        )
        register = StateRegister(self.redis)
        await register.upsert_from_signal(str(self.user_id), signal)
        await self._backdate_spine_entry(state_key, day)

    async def _backdate_spine_entry(self, state_key: str, day: int) -> None:
        import json

        moment, _ = sim_clock(day)
        key = f"spine:state:{self.user_id}:{state_key}"
        raw = await self.redis.get(key)
        if not raw:
            return
        entry = json.loads(raw)
        entry["last_updated_at"] = moment.isoformat()
        ttl_seconds = int(entry.get("ttl_hours", 72)) * 3600
        await self.redis.set(key, json.dumps(entry, ensure_ascii=False), ex=ttl_seconds)

    async def day_tick(self, day: int) -> None:
        """日 tick：真实 spine 过期清扫（backdate 时间戳下的真实 TTL 判定）。"""
        from app.signals.state_register import StateRegister

        assert self.user_id is not None
        await StateRegister(self.redis).expire_stale(str(self.user_id))

    async def active_spine_keys(self) -> list[str]:
        from app.signals.state_register import StateRegister

        assert self.user_id is not None
        entries = await StateRegister(self.redis).get_active_states(str(self.user_id))
        return [e.state_key for e in entries]

    # ------------------------------------------------------------ task reads

    async def task_status_counts(self) -> dict[str, int]:

        assert self.session is not None and self.user_id is not None
        rows = (
            (
                await self.session.execute(
                    select_tasks(self.user_id)
                )
            )
            .scalars()
            .all()
        )
        by_status: dict[str, int] = {}
        for row in rows:
            key = str(getattr(row.status, "value", row.status))
            by_status[key] = by_status.get(key, 0) + 1
        return by_status

    @property
    def budget(self) -> int:
        return EPISODE_SESSION_BUDGET


def select_tasks(user_id: UUID):  # noqa: ANN201 — 供 task_status_counts 的轻量查询
    from sqlalchemy import select

    from app.models.task import Task

    return select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))
