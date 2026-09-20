"""FIX-16 ②（E-05 N1 残余）检索失效事务后钩子测试。

缺陷（REVIEW_RECEIPT_2.md N1 + DYNAMIC_ISSUES V3-FIX-16 ②）：
``invalidate_source_retrieval`` 在四条生命周期路径中均先于 ``db.flush()``/commit
执行——DEL→commit 窗口内并发检索以 READ COMMITTED 旧快照重播删除前
knowledge_version 并再缓存 30s，已删内容在删除完成后仍可命中语义缓存。

修复：失效计划在事务内捕获（群组身份在软删前解析），经会话 ``after_commit``
事件在提交后执行；``after_rollback`` 丢弃计划。

全部测试不触真实 Redis：执行器整体被替换，sqlite 内存库提供真实会话事件
（after_commit/after_rollback 走真实触发路径）。
"""
from __future__ import annotations

import asyncio
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.models.document_chunks import DocumentChunk
from app.models.file_storage import SourceLifecycleStatus, StoredFile
from app.models.group_files import GroupFile
from app.models.user import User
from app.services import source_lifecycle as sl
from app.services.source_lifecycle import (
    _RetrievalInvalidationPlan,
    source_lifecycle_service,
    wait_for_pending_post_commit_invalidation,
)


async def _source(db_session, user_id, *, file_name: str = "lecture.pdf") -> StoredFile:
    stored_file = StoredFile(
        user_id=user_id,
        file_name=file_name,
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"{uuid4()}/lecture.pdf",
        status="processed",
        visibility="private",
        retention_policy="standard",
    )
    db_session.add(stored_file)
    await db_session.flush()
    chunk = DocumentChunk(
        file_id=stored_file.id,
        user_id=user_id,
        chunk_index=0,
        content="Post-commit invalidation probe chunk.",
    )
    db_session.add(chunk)
    await db_session.flush()
    return stored_file


@pytest.fixture()
def invalidation_calls(monkeypatch) -> list[_RetrievalInvalidationPlan]:
    """拦截执行器本体：同时覆盖「立即失效」与「提交后失效」两条路径。"""
    calls: list[_RetrievalInvalidationPlan] = []

    async def fake_execute(plan, *, redis=None):
        calls.append(plan)
        return 3

    monkeypatch.setattr(source_lifecycle_service, "_execute_retrieval_invalidation", fake_execute)
    return calls


@pytest.fixture()
def no_redis(monkeypatch):
    """rag redis 客户端置 None（计划内群组解析随之跳过，无网络副作用）。"""
    monkeypatch.setattr(sl, "get_rag_redis", AsyncMock(return_value=None))


@pytest.mark.asyncio
async def test_archive_invalidation_deferred_until_commit(
    db_session, test_user: User, invalidation_calls, no_redis
) -> None:
    """变异对照核心断言：提交前执行器零调用；commit 后恰一次、计划身份正确。"""
    stored_file = await _source(db_session, test_user.id)

    result = await source_lifecycle_service.archive(db_session, source=stored_file, reason="n1_probe")
    await db_session.flush()

    # 提交前：一次都不许失效（旧实现此处已经 DEL —— N1 缺陷本体）
    await wait_for_pending_post_commit_invalidation()
    assert invalidation_calls == [], "invalidation must NOT run before commit (N1)"

    await db_session.commit()
    await wait_for_pending_post_commit_invalidation()

    assert len(invalidation_calls) == 1
    plan = invalidation_calls[0]
    assert plan.source_id == stored_file.id
    assert plan.user_id == test_user.id
    # invalidated_keys = 排期失效单元数（1 源 + 0 群组）
    assert result.invalidated_keys == 1


@pytest.mark.asyncio
async def test_rollback_discards_scheduled_invalidation(
    db_session, test_user: User, invalidation_calls, no_redis
) -> None:
    stored_file = await _source(db_session, test_user.id)

    await source_lifecycle_service.archive(db_session, source=stored_file, reason="n1_rollback")
    await db_session.rollback()
    await wait_for_pending_post_commit_invalidation()
    # 给误排期的任务一个暴露窗口
    await asyncio.sleep(0.05)

    assert invalidation_calls == [], "rolled-back transaction must not invalidate"


@pytest.mark.asyncio
async def test_delete_captures_group_ids_before_soft_delete(db_session, test_user: User, monkeypatch) -> None:
    """delete() 的群组链接在计划捕获后被软删——计划必须在软删前拿到活跃群组身份。"""
    stored_file = await _source(db_session, test_user.id)
    group_file = GroupFile(
        group_id=uuid4(),
        file_id=stored_file.id,
        shared_by_id=test_user.id,
    )
    db_session.add(group_file)
    await db_session.flush()

    sentinel_redis = object()
    monkeypatch.setattr(sl, "get_rag_redis", AsyncMock(return_value=sentinel_redis))
    doc_key_calls: list[object] = []
    group_key_calls: list[tuple[object, object, object]] = []

    async def fake_delete_doc_keys(redis, file_id):
        doc_key_calls.append((redis, file_id))
        return 5

    async def fake_delete_group_keys(redis, group_id, file_id):
        group_key_calls.append((redis, group_id, file_id))
        return 2

    monkeypatch.setattr(sl, "delete_document_chunk_keys", fake_delete_doc_keys)
    monkeypatch.setattr(sl, "delete_group_document_chunk_keys", fake_delete_group_keys)

    plans: list[_RetrievalInvalidationPlan] = []

    async def executor_stub(plan, *, redis=None):
        """真实执行器的最小替身：按计划群组逐个调用（被替换后的）删除器。"""
        plans.append(plan)
        await sl.delete_document_chunk_keys(sentinel_redis, plan.source_id)
        for group_id in plan.group_ids:
            await sl.delete_group_document_chunk_keys(sentinel_redis, group_id, plan.source_id)
        return 7

    monkeypatch.setattr(source_lifecycle_service, "_execute_retrieval_invalidation", executor_stub)

    result = await source_lifecycle_service.delete(db_session, source=stored_file, erase_object=False)
    await db_session.flush()
    assert result.status == SourceLifecycleStatus.REVOKED

    # 执行发生在 commit 之后（提交前执行器零调用）
    await wait_for_pending_post_commit_invalidation()
    assert plans == []

    await db_session.commit()
    await wait_for_pending_post_commit_invalidation()

    assert len(plans) == 1
    assert plans[0].group_ids == (group_file.group_id,)
    assert group_key_calls == [(sentinel_redis, group_file.group_id, stored_file.id)]
    assert doc_key_calls == [(sentinel_redis, stored_file.id)]
    # 排期单元 = 1 源 + 1 群组
    assert result.invalidated_keys == 2


@pytest.mark.asyncio
async def test_goal_close_cleanup_batches_plans_single_commit(
    db_session, test_user: User, invalidation_calls, no_redis
) -> None:
    """同事务多源批删：每源一个计划，同一 commit 后批量各执行一次。"""
    from app.models.task import Task, TaskStatus, TaskType
    from app.models.task_document import TaskDocument

    goal_id = uuid4()
    sources = [await _source(db_session, test_user.id, file_name=f"s{i}.pdf") for i in range(3)]
    for i, source in enumerate(sources):
        task = Task(
            user_id=test_user.id,
            title=f"goal task {i}",
            type=TaskType.LEARNING,
            estimated_minutes=20,
            difficulty=2,
            energy_cost=1,
            status=TaskStatus.PENDING,
            plan_id=goal_id,
        )
        db_session.add(task)
        await db_session.flush()
        db_session.add(TaskDocument(task_id=task.id, file_id=source.id, linked_by="user"))
        await db_session.flush()

    results = await source_lifecycle_service.goal_close_cleanup(
        db_session, user_id=test_user.id, goal_id=goal_id, reason="n1_batch"
    )
    await db_session.flush()
    assert len(results) == 3

    await db_session.commit()
    await wait_for_pending_post_commit_invalidation()

    assert len(invalidation_calls) == 3
    assert {p.source_id for p in invalidation_calls} == {s.id for s in sources}


@pytest.mark.asyncio
async def test_invalidation_plan_is_frozen() -> None:
    """计划数据形状冻结：不可变、字段封闭（供审计/回放）。"""
    sid, uid, gid = uuid4(), uuid4(), uuid4()
    plan = _RetrievalInvalidationPlan(source_id=sid, user_id=uid, group_ids=(gid,))
    with pytest.raises(FrozenInstanceError):
        plan.source_id = uuid4()  # type: ignore[misc]
    assert plan.source_id == sid and plan.group_ids == (gid,)


@pytest.mark.asyncio
async def test_direct_invalidate_entry_still_immediate(db_session, test_user: User, monkeypatch) -> None:
    """公开直调入口语义保持「立即执行」（隔离测试/外部直调方依赖）。"""
    stored_file = await _source(db_session, test_user.id)
    calls: list[_RetrievalInvalidationPlan] = []

    async def fake_execute(plan, *, redis=None):
        calls.append(plan)
        return 0

    monkeypatch.setattr(source_lifecycle_service, "_execute_retrieval_invalidation", fake_execute)
    monkeypatch.setattr(sl, "get_rag_redis", AsyncMock(return_value=None))

    deleted = await source_lifecycle_service.invalidate_source_retrieval(db_session, stored_file)

    assert deleted == 0
    assert len(calls) == 1 and calls[0].source_id == stored_file.id
