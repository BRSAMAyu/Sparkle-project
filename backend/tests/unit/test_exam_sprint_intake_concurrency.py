"""INTAKE-IDX —— 同目标并发 intake 竞态关闸（uq_plans_user_sprint_goal_active）.

三层验证（全部 sqlite 本地基座，主库只读纪律）：

1. **索引语义**（模型元数据 create_all）：同目标活跃 sprint 双行被 DB 拒绝；
   停用/软删后才可再建同目标活跃行；GROWTH/NULL 键行照常共存——谓词边界
   不被意外扩大。
2. **服务回退**（确定性冲突注入）：复用查询通过后、创建提交前被并发方抢先
   落库（竞态败者视角），撞 uq_plans_user_sprint_goal_active 后必须回查复用
   既有计划而非 500/双计划——与 BP-7 幂等语义闭环。
3. **真并发**：N=6 路完整 intake（真实创建路径）同表单齐发，用栅栏保证全部
   通过复用查询（全查空）后才放行创建——确定性复现查询-创建竞态窗口；
   断言 DB 只落 1 个 plan、6 路全部拿到同一 plan_id（Day-1 包允许瞬时时序
   差：plan 先提交、任务逐个提交，但上报的任务 id 必须真实归属该 plan）。
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.aurora.runtime_v1.planning import AuroraRuntimePlanningState
from app.models.base import Base
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task
from app.schemas.exam_sprint import ExamSprintIntakeRequest
from app.services.exam_sprint_intake_service import ExamSprintIntakeService


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, _ttl: int, value: str) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


def _build_engine(tmp_path, name: str):
    """sqlite 文件库（多会话并发需要真实文件；WAL 允许读写并行推进）。"""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / name}",
        connect_args={"timeout": 60},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


def _intake_request(exam_date: date, subject: str = "计算机网络") -> ExamSprintIntakeRequest:
    return ExamSprintIntakeRequest.model_validate(
        {
            "subject": subject,
            "exam_date": exam_date.isoformat(),
            "target_mode": "pass",
            "scope_context": {"text": "覆盖 CH1-CH6"},
            "baseline": {"current_level": 42, "weak_chapters": ["CH4 图论"]},
            "daily_study_minutes": 165,
        }
    )


def _standalone_service(db: AsyncSession, user_id: UUID) -> ExamSprintIntakeService:
    """mock 掉 plan 创建无关的副作用面（profile 写入 / 运行时状态 / 北极星指标）。"""
    service = ExamSprintIntakeService(db=db, redis_client=FakeRedis())
    service._persist_profile_payloads = AsyncMock()  # type: ignore[method-assign]
    service._record_north_star_intake_metrics = AsyncMock()  # type: ignore[method-assign]
    state = AuroraRuntimePlanningState(
        user_id=str(user_id),
        surface="aurora_planning",
        conversation_id=f"intake-idx-{uuid4()}",
        runtime_session_id=f"rt-{uuid4()}",
    )
    service.planning_manager.runtime_adapter.get_or_create_state = AsyncMock(return_value=state)  # type: ignore[method-assign]
    service.planning_manager.runtime_adapter.save_state = AsyncMock()  # type: ignore[method-assign]
    return service


def _sprint_plan(user_id: UUID, *, subject: str | None, target_date, is_active: bool = True, type_=PlanType.SPRINT):
    return Plan(
        user_id=user_id,
        name="同目标冲刺",
        type=type_,
        plan_stage=PlanStage.SPRINT,
        subject=subject,
        target_date=target_date,
        is_active=is_active,
        priority=PlanPriority.HIGH,
    )


# ---------------------------------------------------------------------------
# 1) 索引语义（模型元数据，create_all 基座——并发测试的地基）
# ---------------------------------------------------------------------------


@pytest.fixture(name="plans_only_session")
async def _plans_only_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [Base.metadata.tables[name] for name in ("users", "plans")]
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=tables))
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_plans_sprint_goal_partial_index_blocks_duplicates(plans_only_session):
    """同目标活跃 sprint 双行必被拒；停用/软删后可再建；GROWTH/NULL 键不参与约束。"""
    user_id = uuid4()
    goal_date = date(2026, 10, 1)

    first = _sprint_plan(user_id, subject="计算机网络", target_date=goal_date)
    plans_only_session.add(first)
    await plans_only_session.commit()

    # 同目标第二个活跃行：DB 拒绝
    plans_only_session.add(_sprint_plan(user_id, subject="计算机网络", target_date=goal_date))
    with pytest.raises(IntegrityError):
        await plans_only_session.commit()
    await plans_only_session.rollback()

    # 旧者停用后，同目标新活跃行可创建（换计划场景不受阻）
    first.is_active = False
    await plans_only_session.commit()
    second = _sprint_plan(user_id, subject="计算机网络", target_date=goal_date)
    plans_only_session.add(second)
    await plans_only_session.commit()

    # 旧者软删后，同目标新活跃行同样可创建
    second.deleted_at = datetime.now(UTC)
    await plans_only_session.commit()
    third = _sprint_plan(user_id, subject="计算机网络", target_date=goal_date)
    plans_only_session.add(third)
    await plans_only_session.commit()

    # 不同考试日 = 不同目标
    plans_only_session.add(_sprint_plan(user_id, subject="计算机网络", target_date=date(2026, 11, 1)))
    await plans_only_session.commit()

    # GROWTH 同键不参与约束
    plans_only_session.add(_sprint_plan(user_id, subject="计算机网络", target_date=goal_date, type_=PlanType.GROWTH))
    await plans_only_session.commit()

    # NULL 键行（非冲刺场景/无考试日）互异共存
    plans_only_session.add(_sprint_plan(user_id, subject=None, target_date=goal_date))
    await plans_only_session.commit()
    plans_only_session.add(_sprint_plan(user_id, subject=None, target_date=None))
    await plans_only_session.commit()
    plans_only_session.add(_sprint_plan(user_id, subject=None, target_date=None))
    await plans_only_session.commit()

    total = (
        await plans_only_session.execute(select(func.count()).select_from(Plan).where(Plan.user_id == user_id))
    ).scalar_one()
    assert total == 8


# ---------------------------------------------------------------------------
# 2) 服务回退：创建撞索引 → 回查复用（确定性，竞态败者视角）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_intake_falls_back_to_reuse_when_concurrent_plan_wins(tmp_path):
    engine = _build_engine(tmp_path, "fallback.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    request = _intake_request(exam_date)

    # 并发赢家：在败者"复用查询已通过、创建未提交"的窗口内（生成器中段钩子）
    # 抢先提交同目标计划——败者 INSERT 必撞唯一索引
    created_winner: dict[str, UUID] = {}

    async with session_factory() as loser_session:
        service = _standalone_service(loser_session, user_id)

        async def _commit_concurrent_winner(**_kwargs):
            # 复用查询已通过（此刻还没有计划）；模拟并发赢家恰在此窗口提交
            inject_session = session_factory()
            try:
                winner = Plan(
                    user_id=user_id,
                    name="7天计算机网络冲刺（并发赢家）",
                    type=PlanType.SPRINT,
                    plan_stage=PlanStage.SPRINT,
                    subject="计算机网络",
                    target_date=exam_date,
                    is_active=True,
                    priority=PlanPriority.HIGH,
                )
                inject_session.add(winner)
                await inject_session.commit()
                created_winner["id"] = winner.id
            finally:
                await inject_session.close()
            return None

        service.planning_manager._refresh_study_material_context = AsyncMock(  # type: ignore[method-assign]
            side_effect=_commit_concurrent_winner
        )

        response = await service.intake(user_id=user_id, request=request)

        assert UUID(response.launch.plan_id) == created_winner["id"]
        assert response.launch.plan_name == "7天计算机网络冲刺（并发赢家）"
        assert response.launch.plan_route == f"/plans/{created_winner['id']}"

        # 败者未留下任何残渣：plan 只有赢家一个，任务为零
        plan_count = (
            await loser_session.execute(select(func.count()).select_from(Plan).where(Plan.user_id == user_id))
        ).scalar_one()
        assert plan_count == 1
        task_count = (
            await loser_session.execute(select(func.count()).select_from(Task).where(Task.user_id == user_id))
        ).scalar_one()
        assert task_count == 0

    await engine.dispose()


# ---------------------------------------------------------------------------
# 3) 真并发：N 路完整 intake 同表单齐发 → 恰好 1 个 plan、全员同一 plan_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_intake_same_goal_creates_exactly_one_plan(tmp_path):
    n = 6
    engine = _build_engine(tmp_path, "race.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_id = uuid4()
    exam_date = date.today() + timedelta(days=7)
    request = _intake_request(exam_date)

    # 齐步栅栏：N 路全部通过复用查询（全查空）后，才放行任何一路进入创建——
    # 确定性复现"查询-创建竞态窗口"，没有栅栏时谁是赢家取决于调度运气。
    arrivals = 0
    first_pass = True
    gate = asyncio.Event()
    original_find = ExamSprintIntakeService._find_reusable_sprint_plan

    async def gated_find(self, *, user_id, request):
        nonlocal arrivals, first_pass
        if first_pass:
            arrivals += 1
            if arrivals >= n:
                first_pass = False
                gate.set()
            await gate.wait()
        return await original_find(self, user_id=user_id, request=request)

    ExamSprintIntakeService._find_reusable_sprint_plan = gated_find
    try:

        async def run_one() -> tuple[str, list[str]]:
            async with session_factory() as session:
                service = _standalone_service(session, user_id)
                response = await service.intake(user_id=user_id, request=request)
                return response.launch.plan_id, list(response.launch.first_day_task_ids)

        results = await asyncio.gather(*(run_one() for _ in range(n)))

        plan_ids = {plan_id for plan_id, _ in results}
        assert len(plan_ids) == 1, f"expected 1 plan_id across {n} concurrent intakes, got {sorted(plan_ids)}"
        single_plan_id = UUID(next(iter(plan_ids)))  # 合法 UUID（plans.id GUID 契约）

        # Day-1 包允许瞬时不一致（plan 先提交、任务逐个提交，败者回查可能
        # 只看到部分/零个 Day-1 任务——plan 身份才是本卡不变量）；但所有
        # 上报的 task id 必须真实存在且归属该 plan（无幻影 id）
        all_reported_ids = {task_id for _, day_one_ids in results for task_id in day_one_ids}

        # 独立会话复核 DB 真相：恰好 1 个 sprint plan，任务归属该 plan
        async with session_factory() as verify_session:
            sprint_plans = (
                (
                    await verify_session.execute(
                        select(Plan).where(Plan.user_id == user_id, Plan.type == PlanType.SPRINT)
                    )
                )
                .scalars()
                .all()
            )
            assert len(sprint_plans) == 1
            assert sprint_plans[0].id == single_plan_id
            assert bool(sprint_plans[0].is_active) is True
            assert sprint_plans[0].deleted_at is None

            plan_tasks = (
                (await verify_session.execute(select(Task.id).where(Task.plan_id == single_plan_id))).scalars().all()
            )
            plan_task_ids = {str(task_id) for task_id in plan_tasks}
            assert len(plan_task_ids) >= 1, "winner should have generated Day-1 tasks"
            assert all_reported_ids <= plan_task_ids, "phantom task ids leaked into launch payloads"

            day_one_count = (
                await verify_session.execute(
                    select(func.count())
                    .select_from(Task)
                    .where(Task.plan_id == single_plan_id, Task.order_index >= 1000, Task.order_index < 2000)
                )
            ).scalar_one()
            assert day_one_count >= 1
    finally:
        ExamSprintIntakeService._find_reusable_sprint_plan = original_find
        await engine.dispose()
