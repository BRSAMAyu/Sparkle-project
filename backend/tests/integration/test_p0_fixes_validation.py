"""
P0修复验证测试脚本

验证三个关键修复:
1. Celery worker中dashscope模块可用
2. DecisionRecordService优雅处理None session
3. FocusService正确使用TaskStatus枚举
"""
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, get_db
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.decision_record_service import DecisionRecordService
from app.services.focus_service import focus_service


@pytest.mark.asyncio
async def test_dashscope_in_worker():
    """验证dashscope在worker环境中可用"""
    import dashscope
    # 验证模块可导入
    assert hasattr(dashscope, 'AioGeneration')
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
        outcome="test_outcome"
    )
    print("✅ Test 2 passed: DecisionRecordService优雅处理None session")


@pytest.mark.asyncio
async def test_decision_record_service_with_valid_session():
    """验证DecisionRecordService在有效session下正常工作"""
    async for db in get_db():
        decision_service = DecisionRecordService(db=db)
        test_user_id = uuid4()

        # 记录决策
        await decision_service.record_decision(
            user_id=test_user_id,
            module="test",
            action="test_action_valid",
            preference_version=1,
            preferences_snapshot={"test": "data"},
            outcome="success"
        )

        # 验证记录已保存
        records = await decision_service.get_recent_records(test_user_id, limit=1)
        assert len(records) == 1
        assert records[0].action == "test_action_valid"
        print("✅ Test 3 passed: DecisionRecordService在有效session下正常记录")
        break


@pytest.mark.asyncio
async def test_task_status_enum_in_focus_service():
    """验证FocusService使用TaskStatus枚举而非字符串"""
    async for db in get_async_db():
        # 创建测试用户
        test_user = User(
            id=uuid4(),
            username=f"test_user_{uuid4().hex[:8]}",
            email=f"test_{uuid4().hex[:8]}@example.com",
            hashed_password="hash",
            is_active=True
        )
        db.add(test_user)
        await db.flush()

        # 创建PENDING任务
        test_task = Task(
            id=uuid4(),
            user_id=test_user.id,
            title="验证任务状态枚举",
            type="study",
            status=TaskStatus.PENDING,
            priority=1,
            estimated_minutes=25
        )
        db.add(test_task)
        await db.flush()

        # 记录一个专注会话（应该将任务状态改为IN_PROGRESS）
        start_time = datetime.now() - timedelta(minutes=25)
        end_time = datetime.now()

        result = await focus_service.log_session(
            db=db,
            user_id=test_user.id,
            task_id=test_task.id,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=25,
            status="completed"
        )

        # 刷新并验证任务状态
        await db.refresh(test_task)
        assert test_task.status == TaskStatus.IN_PROGRESS, \
            f"Expected status IN_PROGRESS, got {test_task.status}"
        assert test_task.started_at is not None

        print("✅ Test 4 passed: FocusService正确使用TaskStatus枚举")

        # 清理测试数据
        await db.rollback()
        break


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
    print("\n" + "="*60)
    print("开始P0修复验证测试")
    print("="*60 + "\n")

    try:
        # Test 1: dashscope可用性
        import dashscope
        print("✅ Test 1: dashscope模块可用性")

        # Test 2: None session处理
        decision_service_none = DecisionRecordService(db=None)
        await decision_service_none.record_decision(
            user_id=uuid4(),
            module="test",
            action="test_none",
            preference_version=1,
            preferences_snapshot={},
            outcome="test"
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
                outcome="validated"
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
                is_active=True
            )
            db.add(test_user)
            await db.flush()

            test_task = Task(
                id=uuid4(),
                user_id=test_user.id,
                title="P0验证任务",
                type="study",
                status=TaskStatus.PENDING,
                priority=5,
                estimated_minutes=30
            )
            db.add(test_task)
            await db.flush()

            initial_status = test_task.status
            await focus_service.log_session(
                db=db,
                user_id=test_user.id,
                task_id=test_task.id,
                start_time=datetime.now() - timedelta(minutes=30),
                end_time=datetime.now(),
                duration_minutes=30,
                status="completed"
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

        print("\n" + "="*60)
        print("🎉 所有P0修复验证测试通过!")
        print("="*60 + "\n")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
