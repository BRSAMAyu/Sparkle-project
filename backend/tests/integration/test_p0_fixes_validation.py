# FIXED: 2026-04-25 - Integration DB schema was behind task planning migrations - verified Task ORM insert after Alembic head.
"""
P0修复验证测试脚本

验证三个关键修复:
1. Celery worker中dashscope模块可用
2. DecisionRecordService优雅处理None session
3. FocusService正确使用TaskStatus枚举
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.models.base import Base as AppBase
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.decision_record_service import DecisionRecordService
from app.services.focus_service import focus_service


@pytest.mark.asyncio
async def test_dashscope_in_worker():
    """验证dashscope在worker环境中可用"""
    import dashscope

    # 验证模块可导入
    assert hasattr(dashscope, "AioGeneration")
    print("✅ Test 1 passed: dashscope模块可用")


@pytest.mark.asyncio
async def test_decision_record_service_with_none_session():
    """验证DecisionRecordService优雅处理None session"""
    # 测试None session场景
    decision_service = DecisionRecordService(db=None)

    # 不应该抛出异常
    await decision_service.record_decision(
        user_id=uuid4(),
        module="test",
        action="test_action",
        preference_version=1,
        preferences_snapshot={},
        outcome="test_outcome",
    )
    print("✅ Test 2 passed: DecisionRecordService优雅处理None session")


@pytest_asyncio.fixture
async def decision_record_session() -> AsyncGenerator[AsyncSession, None]:
    """自含建表的 sqlite 内存会话（对齐顶层 conftest db_session 纪律）。

    V3-FIX-325：原实现裸 ``async for db in get_db()`` 走进程级全局 engine，其
    背后库是否有表完全取决于环境——单 job 全量 CI（postgres+迁移先行）成立；
    裸 worktree/sqlite 形态下全局库为空 schema，恒 ``no such table: users``
    （wt487 即记录的 base 既有形态，wt592 分片化后进入片绿核算而暴露；wt590
    conftest autouse 0b2273b3 只治理 LLM 全局态、wt598 迁移是 postgres alembic
    面，均与此无关）。本测语义是「有效 AsyncSession 下服务可记录并读回」，
    不承载 get_db 依赖链语义——改用测试自管建表会话，环境无关，不弱化其他
    测试的隔离性。
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_decision_record_service_with_valid_session(decision_record_session):
    """验证DecisionRecordService在有效session下正常工作"""
    db = decision_record_session
    decision_service = DecisionRecordService(db=db)
    test_user_id = uuid4()
    db.add(
        User(
            id=test_user_id,
            username=f"p0_user_{test_user_id.hex[:8]}",
            email=f"p0_{test_user_id.hex[:8]}@example.com",
            hashed_password="hash",
            is_active=True,
        )
    )
    await db.commit()

    # 记录决策
    await decision_service.record_decision(
        user_id=test_user_id,
        module="test",
        action="test_action_valid",
        preference_version=1,
        preferences_snapshot={"test": "data"},
        outcome="success",
    )

    # 验证记录已保存
    records = await decision_service.get_recent_records(test_user_id, limit=1)
    assert len(records) == 1
    assert records[0].action == "test_action_valid"
    print("✅ Test 3 passed: DecisionRecordService在有效session下正常记录")


@pytest.mark.asyncio
async def test_task_status_enum_in_focus_service(db_session: AsyncSession):
    """验证FocusService使用TaskStatus枚举而非字符串"""
    # 创建测试用户
    test_user = User(
        id=uuid4(),
        username=f"test_user_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        hashed_password="hash",
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.flush()

    # 创建PENDING任务
    test_task = Task(
        id=uuid4(),
        user_id=test_user.id,
        title="验证任务状态枚举",
        type=TaskType.LEARNING,
        status=TaskStatus.PENDING,
        priority=1,
        estimated_minutes=30,
    )
    db_session.add(test_task)
    await db_session.flush()

    # 记录一个专注会话（应该将任务状态改为IN_PROGRESS）
    start_time = datetime.now() - timedelta(minutes=25)
    end_time = datetime.now()

    await focus_service.log_session(
        db=db_session,
        user_id=test_user.id,
        task_id=test_task.id,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=25,
        status="completed",
    )

    # 刷新并验证任务状态
    await db_session.refresh(test_task)
    assert test_task.status == TaskStatus.IN_PROGRESS, f"Expected status IN_PROGRESS, got {test_task.status}"
    assert test_task.started_at is not None

    print("✅ Test 4 passed: FocusService正确使用TaskStatus枚举")

    await db_session.rollback()


@pytest.mark.asyncio
async def test_task_status_equality():
    """验证TaskStatus枚举比较正确性"""
    # 这应该通过（枚举比较）
    assert TaskStatus.PENDING == TaskStatus.PENDING
    assert TaskStatus.IN_PROGRESS == TaskStatus.IN_PROGRESS
    assert TaskStatus.PENDING != TaskStatus.IN_PROGRESS

    # 这些不应该通过（字符串 vs 枚举）
    assert TaskStatus.PENDING != "pending"
    assert TaskStatus.IN_PROGRESS != "in_progress"

    print("✅ Test 5 passed: TaskStatus枚举比较正确性")


async def run_all_tests():
    """运行所有验证测试"""
    print("\n" + "=" * 60)
    print("开始P0修复验证测试")
    print("=" * 60 + "\n")

    try:
        # Test 1: dashscope可用性
        import dashscope  # noqa: F401 — 探测模块可导入性本身即断言

        print("✅ Test 1: dashscope模块可用性")

        # Test 2: None session处理
        decision_service_none = DecisionRecordService(db=None)
        await decision_service_none.record_decision(
            user_id=uuid4(),
            module="test",
            action="test_none",
            preference_version=1,
            preferences_snapshot={},
            outcome="test",
        )
        print("✅ Test 2: DecisionRecordService优雅处理None session")

        # Test 3: 有效session处理
        async for db in get_db():
            decision_service = DecisionRecordService(db=db)
            test_user_id = uuid4()
            await decision_service.record_decision(
                user_id=test_user_id,
                module="test_validation",
                action="test_valid_session",
                preference_version=1,
                preferences_snapshot={"test": True},
                outcome="validated",
            )
            records = await decision_service.get_recent_records(test_user_id, limit=1)
            assert len(records) >= 1
            print("✅ Test 3: DecisionRecordService有效session正常工作")
            break

        # Test 4: TaskStatus枚举使用
        async for db in get_db():
            test_user = User(
                id=uuid4(),
                username=f"validation_user_{uuid4().hex[:8]}",
                email=f"validate_{uuid4().hex[:8]}@test.com",
                hashed_password="test_hash",
                is_active=True,
            )
            db.add(test_user)
            await db.flush()

            test_task = Task(
                id=uuid4(),
                user_id=test_user.id,
                title="P0验证任务",
                type=TaskType.LEARNING,
                status=TaskStatus.PENDING,
                priority=5,
                estimated_minutes=30,
            )
            db.add(test_task)
            await db.flush()

            initial_status = test_task.status
            await focus_service.log_session(
                db=db,
                user_id=test_user.id,
                task_id=test_task.id,
                start_time=datetime.now() - timedelta(minutes=25),
                end_time=datetime.now(),
                duration_minutes=25,
                status="completed",
            )
            await db.refresh(test_task)

            assert initial_status == TaskStatus.PENDING
            assert test_task.status == TaskStatus.IN_PROGRESS
            print("✅ Test 4: FocusService正确使用TaskStatus枚举 (PENDING→IN_PROGRESS)")

            await db.rollback()
            break

        # Test 5: 枚举比较验证
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != "pending"
        assert TaskStatus.IN_PROGRESS != "in_progress"
        print("✅ Test 5: TaskStatus枚举比较正确性")

        print("\n" + "=" * 60)
        print("🎉 所有P0修复验证测试通过!")
        print("=" * 60 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
