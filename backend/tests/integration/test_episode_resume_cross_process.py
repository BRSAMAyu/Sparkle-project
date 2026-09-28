"""V4-I01 · 接续视图跨会话/进程重开集成测（文件级 sqlite，双引擎模拟双进程）。

卡验收「跨会话/进程重开恢复同一对象；已删对象不复活」的可失败实现：
- 进程 A（engine A）落权威行：goal/plan/task(+V3 计划)/subtask/agent_run；
- 进程 B（engine B，新引擎新连接——零共享内存态）重建视图：
  同权威 + 同输入 → 逐键同一对象（goal_ref/task_ref/run_ref/step/outcome ref）；
- B 侧软删 task 后重建 → ``object_not_found``——已删对象不复活；
- B 侧 bump memory epoch → 计算时钉住的视图判 stale（重算出口，不就地修补）。

数据源全部为既有权威表（goals/plans/tasks/subtasks/agent_runs/user_memory_settings
+ outcome 账本读面），零第二真值表、零写路径新增。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 显式注册本链路触碰的全部权威表（outcome 账本五源 + epoch 设置表）。
import app.models.base  # noqa: F401 — Base metadata
from app.core.action_plan import ActionPlanContract, CompletionEvidenceSpec, SmallestUsefulStep
from app.core.episode_resume_view import resume_view_stale_reason
from app.core.run_state_machine import RunStatus
from app.models.agent_run import AgentRun, AgentRunKind  # noqa: F401
from app.models.execution_intent import ExecutionMode
from app.models.file_storage import StoredFile  # noqa: F401
from app.models.focus import FocusSession  # noqa: F401
from app.models.galaxy import ExpansionFeedback, StudyRecord  # noqa: F401
from app.models.goal import Goal  # noqa: F401
from app.models.intervention_adaptive import BehavioralOutcome  # noqa: F401
from app.models.plan import Plan  # noqa: F401
from app.models.task import CognitiveOwnership, SubTask, SubTaskStatus, Task, TaskType  # noqa: F401
from app.models.task_document import TaskDocument  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_memory_settings import UserMemorySettings  # noqa: F401
from app.services.episode_resume_service import EpisodeResumeService

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 9, 28, 8, 55, 0)
_RECEIPT = "context_selection://csr_i01_cross_process"

pytest.importorskip("aiosqlite")


def _make_sessionmaker(db_path: Path) -> async_sessionmaker:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _create_all(db_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        from app.models.base import Base

        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(name="db_path")
async def _db_path(tmp_path: Path) -> Path:
    path = tmp_path / "i01_cross_process.sqlite3"
    await _create_all(path)
    return path


async def _seed_authorities(db_path: Path) -> tuple[str, str]:
    """进程 A：落权威行（goal/plan/task/subtask/run）。返回 (user_id, task_id)。"""
    maker = _make_sessionmaker(db_path)
    async with maker() as db:
        user = User(username=f"i01cp{uuid4().hex[:8]}", email=f"i01cp{uuid4().hex[:8]}@t.co", hashed_password="x")
        db.add(user)
        await db.flush()
        goal = Goal(user_id=user.id, title="考研数学", goal_type="exam", status="active")
        db.add(goal)
        await db.flush()
        plan = Plan(user_id=user.id, goal_id=goal.id, name="数学冲刺", type="sprint")
        db.add(plan)
        await db.flush()
        task = Task(
            user_id=user.id,
            plan_id=plan.id,
            title="极限专题",
            type=TaskType.LEARNING,
            estimated_minutes=30,
            status="IN_PROGRESS",
        )
        contract = ActionPlanContract(
            desired_outcome="独立完成 1 道同型题",
            smallest_useful_step=SmallestUsefulStep(
                description="独立完成 1 道同型题并通过自查清单", useful_because=("builds_capability",)
            ),
            completion_evidence=(CompletionEvidenceSpec(evidence_kind="quiz_result"),),
            execution_mode=ExecutionMode.HYBRID,
            cognitive_ownership=CognitiveOwnership.USER_CORE,
            source_refs=(f"goal://{goal.id}",),
        )
        contract.apply_to_task(task)
        db.add(task)
        await db.flush()
        db.add(
            SubTask(
                parent_task_id=task.id,
                title="看示例题",
                order=1,
                status=SubTaskStatus.COMPLETED,
                completed_at=_NOW - timedelta(hours=1),
            )
        )
        db.add(
            AgentRun(
                user_id=user.id,
                kind=AgentRunKind.EXECUTION,
                objective="准备同型题",
                heartbeat_at=_NOW,
                status=RunStatus.AWAITING_USER,
                task_id=task.id,
            )
        )
        await db.commit()
        return str(user.id), str(task.id)


async def _build(db_path: Path, user_id: str, task_id: str, *, now: datetime = _NOW) -> dict:
    """一次「进程重启」：新引擎新连接重建视图（读模型按需聚合，无内存残留）。"""
    maker = _make_sessionmaker(db_path)
    async with maker() as db:
        result = await EpisodeResumeService(db).build_resume_view(
            user_id=user_id, task_id=task_id, context_receipt_ref=_RECEIPT, now=now
        )
        await db.rollback()  # 显式只读：视图聚合不落任何行
        return result


async def test_cross_process_reopen_restores_same_object(db_path):
    user_id, task_id = await _seed_authorities(db_path)

    first = await _build(db_path, user_id, task_id)
    assert first.degraded is False, first.reason_code

    # 「进程重启」：换引擎重开——恢复的是同一组权威对象引用。
    reopened = await _build(db_path, user_id, task_id)
    assert reopened.degraded is False
    assert reopened.view == first.view  # 同权威 + 同输入 → 逐键同一视图（含 computed_at/expires_at）
    view = reopened.view
    assert view["task_ref"] == f"task://{task_id}"
    assert view["goal_ref"].startswith("goal://")
    assert view["run_ref"].startswith("run://")  # 在途 run 从持久真源恢复，不靠内存
    assert view["last_confirmed_step"]["step_ref"].startswith("subtask://")
    assert view["pending_human_step"]["description"] == "独立完成 1 道同型题并通过自查清单"
    assert view["freshness"]["memory_epoch_at_compute"] == 1  # 未 bump 过的默认 epoch


async def test_deleted_task_not_revived_after_process_reopen(db_path):
    user_id, task_id = await _seed_authorities(db_path)
    first = await _build(db_path, user_id, task_id)
    assert first.view is not None

    # 「另一个进程」里删对象（软删，既有 SoftDelete 语义）
    maker = _make_sessionmaker(db_path)
    async with maker() as db:
        row = await db.get(Task, uuid.UUID(task_id))
        row.soft_delete()
        await db.commit()

    reopened = await _build(db_path, user_id, task_id)
    assert reopened.view is None
    assert reopened.reason_code == "object_not_found"  # 已删对象不复活


async def test_epoch_bump_after_reopen_marks_view_stale(db_path):
    user_id, task_id = await _seed_authorities(db_path)
    stale_before_bump = await _build(db_path, user_id, task_id)
    assert stale_before_bump.view is not None

    # 「另一个进程」里发生破坏性记忆变更 → epoch bump（既有 M-01 契约）
    maker = _make_sessionmaker(db_path)
    async with maker() as db:
        from app.core.time_utils import utcnow

        db.add(
            UserMemorySettings(
                user_id=uuid.UUID(user_id),
                memory_epoch=2,
                memory_epoch_bumped_at=utcnow(),
                memory_epoch_reason="test-destructive-change",
            )
        )
        await db.commit()

    reopened = await _build(db_path, user_id, task_id)
    assert reopened.view is not None
    assert reopened.view["freshness"]["memory_epoch_at_compute"] == 2  # 重算视图钉新 epoch
    # 旧视图（计算时 epoch=1）判 stale：消费方重算，不就地修补、不静默续跑
    assert resume_view_stale_reason(stale_before_bump.view, now=_NOW, current_memory_epoch=2) == "memory_epoch_changed"
    assert resume_view_stale_reason(reopened.view, now=_NOW, current_memory_epoch=2) is None


async def test_view_build_persists_no_rows(db_path):
    """读模型铁律：聚合不写任何行（无第二真值表）。"""
    import sqlalchemy as sa

    user_id, task_id = await _seed_authorities(db_path)
    maker = _make_sessionmaker(db_path)
    async with maker() as db:
        await EpisodeResumeService(db).build_resume_view(
            user_id=user_id, task_id=task_id, context_receipt_ref=_RECEIPT, now=_NOW
        )

    # 用 SQL 摸底：DB 中不存在 ORM metadata 之外的新表（即视图未落任何第二真值表）
    from app.models.base import Base

    orm_tables = {t.name for t in Base.metadata.tables.values()}
    async with maker() as db:
        tables = {
            row[0]
            for row in (await db.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table'"))).fetchall()
        }
        assert tables - orm_tables == set()  # 零新表
        task_count = (await db.execute(sa.text("SELECT COUNT(*) FROM tasks"))).scalar()
        assert task_count == 1
