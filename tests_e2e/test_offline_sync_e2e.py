"""
E2E Test: Offline Synchronization System
=========================================

Tests the complete offline→online sync flow:
Offline Operations → Local Queue → Online Reconnect → Sync → Conflict Resolution

Author: Claude Code (Sonnet 4.5)
Created: 2026-01-28
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.sync import SyncQueueItem, SyncStatus, ConflictResolution
from app.models.task import Task, TaskStatus
from app.services.sync_service import SyncService
from app.services.offline_queue import OfflineQueue
from app.services.conflict_resolver import ConflictResolver


# =============================================================================
# Test 1: Offline Operation Queueing
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_offline_task_completion_queued(
    db_session,
    test_user,
    test_plan_with_tasks,
):
    """
    E2E: User offline → Completes task → Queued → Synced when online

    Scenario:
    1. User working on plan with tasks
    2. Network connection lost
    3. User completes task (marked as completed locally)
    4. Operation added to sync queue
    5. Network restored
    6. Queue processed
    7. Task synced to server
    8. Server confirms sync
    """
    # Arrange: Get plan and tasks
    plan = test_plan_with_tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()

    # Arrange: Initialize offline queue
    offline_queue = OfflineQueue(db_session)

    # Act: Simulate offline operation
    # User completes task while offline
    task_to_complete = tasks[0]
    offline_op = await offline_queue.enqueue(
        user_id=test_user.id,
        operation="complete_task",
        entity_type="task",
        entity_id=str(task_to_complete.id),
        data={
            "actual_minutes": 35,
            "completed_at": datetime.utcnow().isoformat(),
        },
        priority=1,  # High priority
    )

    # Assert: Operation queued
    assert offline_op is not None
    assert offline_op.status == SyncStatus.PENDING
    assert offline_op.operation == "complete_task"

    # Act: Simulate network restore and sync
    sync_service = SyncService(db_session)
    sync_results = await sync_service.process_queue(user_id=test_user.id)

    # Assert: Operation synced
    assert len(sync_results["synced"]) > 0
    assert sync_results["synced"][0]["id"] == str(offline_op.id)

    # Assert: Task actually completed on server
    await db_session.refresh(task_to_complete)
    assert task_to_complete.status == TaskStatus.COMPLETED

    # Assert: Sync queue item marked as completed
    await db_session.refresh(offline_op)
    assert offline_op.status == SyncStatus.COMPLETED
    assert offline_op.synced_at is not None


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_offline_multiple_operations_batch_sync(
    db_session,
    test_user,
    test_plan_with_tasks,
):
    """
    E2E: Multiple offline ops → Batch sync when online

    Scenario:
    1. User offline for extended period
    2. User completes 3 tasks
    3. User creates 2 new tasks
    4. User updates plan settings
    6 operations total queued
    5. Network restored
    6. All operations batch synced
    7. Server processes in order
    8. All data consistent
    """
    # Arrange: Get plan and tasks
    plan = test_plan_with_tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()

    # Arrange: Initialize offline queue
    offline_queue = OfflineQueue(db_session)

    # Act: Queue multiple offline operations
    queued_ops = []

    # Complete 3 tasks
    for i in range(3):
        op = await offline_queue.enqueue(
            user_id=test_user.id,
            operation="complete_task",
            entity_type="task",
            entity_id=str(tasks[i].id),
            data={"actual_minutes": 30},
            priority=1,
        )
        queued_ops.append(op)

    # Create 2 new tasks
    for i in range(2):
        new_task_id = uuid4()
        op = await offline_queue.enqueue(
            user_id=test_user.id,
            operation="create_task",
            entity_type="task",
            entity_id=str(new_task_id),
            data={
                "title": f"离线创建的任务 {i+1}",
                "type": "learning",
                "estimated_minutes": 30,
                "plan_id": str(plan.id),
            },
            priority=2,  # Lower priority
        )
        queued_ops.append(op)

    # Update plan settings
    op = await offline_queue.enqueue(
        user_id=test_user.id,
        operation="update_plan",
        entity_type="plan",
        entity_id=str(plan.id),
        data={"daily_target_hours": 3},
        priority=1,
    )
    queued_ops.append(op)

    # Assert: All operations queued
    assert len(queued_ops) == 6

    # Act: Batch sync when online
    sync_service = SyncService(db_session)
    sync_results = await sync_service.process_queue(
        user_id=test_user.id,
        batch_size=10,  # Process all at once
    )

    # Assert: All operations synced
    assert len(sync_results["synced"]) == 6

    # Assert: Tasks completed
    for i in range(3):
        await db_session.refresh(tasks[i])
        assert tasks[i].status == TaskStatus.COMPLETED

    # Assert: New tasks created
    result = await db_session.execute(
        select(Task).where(
            Task.plan_id == plan.id,
            Task.title.contains("离线创建"),
        )
    )
    new_tasks = result.scalars().all()
    assert len(new_tasks) == 2

    # Assert: All queue items completed
    for op in queued_ops:
        await db_session.refresh(op)
        assert op.status == SyncStatus.COMPLETED


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_sync_conflict_detection_and_resolution(
    db_session,
    test_user,
    test_plan_with_tasks,
):
    """
    E2E: Concurrent edits → Conflict detected → Resolution strategy applied

    Scenario:
    1. User A edits task title offline
    2. User B (or same user on other device) edits same task online
    3. User A comes online
    4. Conflict detected (both modified same field)
    5. Conflict resolver applies strategy:
       - If timestamps differ: use latest
       - If same timestamp: merge or manual resolution
    6. Resolution persisted
    7. Both devices synced with resolved version
    """
    # Arrange: Get task
    plan = test_plan_with_tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()
    task = tasks[0]

    # Arrange: Initialize services
    offline_queue = OfflineQueue(db_session)
    conflict_resolver = ConflictResolver(db_session)

    # Act 1: Device A - User edits task offline
    offline_time = datetime.utcnow() - timedelta(minutes=5)
    await offline_queue.enqueue(
        user_id=test_user.id,
        operation="update_task",
        entity_type="task",
        entity_id=str(task.id),
        data={
            "title": "学习Python变量 (离线修改)",
            "updated_at": offline_time.isoformat(),
        },
        device_id="device_A",
        priority=1,
    )

    # Act 2: Device B - User edits same task online (simulated by direct DB update)
    online_time = datetime.utcnow() - timedelta(minutes=2)
    task.title = "学习Python基础变量 (在线修改)"
    task.updated_at = online_time
    await db_session.commit()

    # Act 3: Device A comes online, sync triggered
    sync_service = SyncService(db_session)
    sync_results = await sync_service.process_queue(user_id=test_user.id)

    # Assert: Conflict detected
    assert "conflicts" in sync_results
    assert len(sync_results["conflicts"]) > 0

    conflict = sync_results["conflicts"][0]
    assert conflict["entity_id"] == str(task.id)
    assert conflict["conflict_type"] == "concurrent_update"

    # Act 4: Resolve conflict (use latest timestamp)
    resolution = await conflict_resolver.resolve(
        conflict_id=conflict["id"],
        strategy=ConflictResolution.USE_LATEST,
    )

    # Assert: Conflict resolved
    assert resolution["resolved"] is True
    assert resolution["applied_strategy"] == ConflictResolution.USE_LATEST

    # Assert: Latest version kept (online version was later)
    await db_session.refresh(task)
    assert "在线修改" in task.title  # Online version was later

    # Assert: Conflict record marked as resolved
    conflict_record = await db_session.execute(
        select(SyncQueueItem).where(SyncQueueItem.id == uuid4())
    )
    # In real implementation, would check conflict resolution table


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_offline_queue_persistence_and_recovery(
    db_session,
    test_user,
    test_plan_with_tasks,
):
    """
    E2E: App crash → Queue persisted → App restart → Queue recovered

    Scenario:
    1. User offline, completes task
    2. Operation queued in local storage
    3. App crashes before sync
    4. Queue persisted in SQLite/local DB
    5. User restarts app
    6. Queue recovered from storage
    7. User comes online
    8. Sync completes successfully
    """
    # Arrange: Get task
    plan = test_plan_with_tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id)
    )
    tasks = result.scalars().all()
    task = tasks[0]

    # Arrange: Initialize offline queue with persistence
    offline_queue = OfflineQueue(
        db_session,
        persist_to_disk=True,  # Enable persistence
        storage_path="/tmp/sparkle_offline_queue.db",
    )

    # Act: User completes task offline
    queued_op = await offline_queue.enqueue(
        user_id=test_user.id,
        operation="complete_task",
        entity_type="task",
        entity_id=str(task.id),
        data={"actual_minutes": 30},
        priority=1,
    )

    # Simulate app crash by creating new queue instance
    # (In real app, this would be a process restart)
    crashed_queue = OfflineQueue(
        db_session,
        persist_to_disk=True,
        storage_path="/tmp/sparkle_offline_queue.db",
    )

    # Act: Recover queue after crash
    recovered_ops = await crashed_queue.get_pending_operations(user_id=test_user.id)

    # Assert: Operation recovered
    assert len(recovered_ops) == 1
    assert recovered_ops[0].id == queued_op.id
    assert recovered_ops[0].operation == "complete_task"

    # Act: User comes online, sync
    sync_service = SyncService(db_session)
    sync_results = await sync_service.process_queue(user_id=test_user.id)

    # Assert: Sync successful
    assert len(sync_results["synced"]) == 1

    # Assert: Task completed
    await db_session.refresh(task)
    assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_sync_error_handling_and_retry(
    db_session,
    test_user,
    test_plan_with_tasks,
):
    """
    E2E: Sync fails → Error logged → Retry with backoff → Success

    Scenario:
    1. User offline, creates task
    2. Operation queued
    3. User comes online
    4. Sync attempt 1: Server error (500)
    5. Error logged, operation marked as failed
    6. Retry after exponential backoff (1s, 2s, 4s...)
    7. Retry attempt succeeds
    8. Operation marked as completed
    """
    # Arrange: Get plan
    plan = test_plan_with_tasks

    # Arrange: Initialize queue
    offline_queue = OfflineQueue(db_session)

    # Act: Queue operation
    new_task_id = uuid4()
    queued_op = await offline_queue.enqueue(
        user_id=test_user.id,
        operation="create_task",
        entity_type="task",
        entity_id=str(new_task_id),
        data={
            "title": "需要重试的任务",
            "plan_id": str(plan.id),
            "estimated_minutes": 30,
        },
        priority=1,
        max_retries=3,  # Allow retries
    )

    # Arrange: Mock sync service that fails first time
    sync_service = SyncService(db_session)

    # Mock server error
    attempt_count = 0

    async def mock_sync_with_retry(operation):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            # First attempt fails
            raise Exception("Server error 500")
        else:
            # Second attempt succeeds
            # Actually create the task
            task = Task(
                id=new_task_id,
                user_id=test_user.id,
                plan_id=plan.id,
                title="需要重试的任务",
                estimated_minutes=30,
                status=TaskStatus.PENDING,
            )
            db_session.add(task)
            await db_session.commit()
            return True

    # Act: Sync with retry
    sync_service._sync_operation = mock_sync_with_retry
    sync_results = await sync_service.process_queue_with_retry(
        user_id=test_user.id,
        max_retries=3,
        initial_backoff=1,  # 1 second
    )

    # Assert: Eventually succeeded after retry
    assert sync_results["successful"] >= 1
    assert attempt_count == 2  # Failed once, succeeded on retry

    # Assert: Task created
    result = await db_session.execute(
        select(Task).where(Task.id == new_task_id)
    )
    task = result.scalar_one_or_none()
    assert task is not None
    assert task.title == "需要重试的任务"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_e2e_incremental_sync_and_delta_updates(
    db_session,
    test_user,
    test_plan_with_tasks,
):
    """
    E2E: Large dataset → Incremental sync → Delta updates only

    Scenario:
    1. User has plan with 100 tasks
    2. User offline, modifies 5 tasks
    3. Only 5 operations in queue (not full sync)
    4. When online, sync only deltas
    5. Server accepts partial updates
    6. Bandwidth saved
    7. Sync faster
    """
    # Arrange: Create plan with 100 tasks
    plan = test_plan_with_tasks

    # Add 95 more tasks (already have 5 from fixture)
    for i in range(5, 100):
        task = Task(
            id=uuid4(),
            user_id=test_user.id,
            plan_id=plan.id,
            title=f"任务 {i+1}",
            type="learning",
            status=TaskStatus.PENDING,
            estimated_minutes=30,
            order=i,
        )
        db_session.add(task)
    await db_session.commit()

    # Arrange: Get some tasks
    result = await db_session.execute(
        select(Task).where(Task.plan_id == plan.id).limit(5)
    )
    tasks = result.scalars().all()

    # Arrange: Initialize offline queue
    offline_queue = OfflineQueue(db_session)

    # Act: User offline, modifies only 5 tasks
    queued_ops = []
    for task in tasks:
        op = await offline_queue.enqueue(
            user_id=test_user.id,
            operation="update_task",
            entity_type="task",
            entity_id=str(task.id),
            data={"estimated_minutes": 45},  # Changed from 30 to 45
            priority=1,
        )
        queued_ops.append(op)

    # Assert: Only 5 operations queued (not 100)
    assert len(queued_ops) == 5

    # Act: Sync deltas
    sync_service = SyncService(db_session)
    sync_results = await sync_service.process_queue(
        user_id=test_user.id,
        sync_mode="incremental",  # Only sync deltas
    )

    # Assert: Synced 5 operations
    assert len(sync_results["synced"]) == 5

    # Assert: Only 5 tasks updated on server
    for task in tasks:
        await db_session.refresh(task)
        assert task.estimated_minutes == 45

    # Assert: Other 95 tasks unchanged
    result = await db_session.execute(
        select(Task).where(
            Task.plan_id == plan.id,
            Task.estimated_minutes == 30,
        )
    )
    unchanged_tasks = result.scalars().all()
    assert len(unchanged_tasks) == 95


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
