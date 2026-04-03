from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.event_types import EXECUTION_RESULT_INGESTED
from app.models.execution_intent import (
    ExecutionIntent,
    ExecutionIntentStatus,
    ExecutionMode,
    ExecutionTargetEnv,
    ExecutorType,
    TrustLevel,
)
from app.models.execution_record import ExecutionRecord
from app.models.galaxy import KnowledgeNode
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.achievement_engine import AchievementEvent
from app.services.achievement_event_consumer import AchievementEventConsumer
from app.services.galaxy_execution_consumer import GalaxyExecutionConsumer
from app.orchestration.plan_review_service import PlanReviewService


@pytest.mark.asyncio
async def test_galaxy_execution_consumer_promotes_chat_control_results(db_session, monkeypatch):
    user = User(
        id=uuid4(),
        username="galaxy_exec_user",
        email="galaxy_exec_user@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="隐藏浏览器委派",
        type=TaskType.LEARNING,
        tags=["openclaw", "chat_control"],
        estimated_minutes=20,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.IN_PROGRESS,
    )
    intent = ExecutionIntent(
        id=uuid4(),
        user_id=user.id,
        task_id=task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="整理 TCP 协议握手的关键点",
        instructions=["输出 3 条要点"],
        target_env=ExecutionTargetEnv.BROWSER,
        policy={"chat_control": True},
        success_criteria={"summary": True},
        result_contract={},
        timeout_seconds=300,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"intent-{uuid4()}",
        completed_at=datetime.utcnow(),
    )
    record = ExecutionRecord(
        id=uuid4(),
        execution_intent_id=intent.id,
        user_id=user.id,
        task_id=task.id,
        executor_type="openclaw",
        raw_response={
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "TCP 三次握手依次完成 SYN、SYN-ACK、ACK 的连接确认。",
                        }
                    ],
                }
            ],
        },
        parsed_output={"summary": "TCP 三次握手依次完成 SYN、SYN-ACK、ACK 的连接确认。"},
        trust_level="trusted",
        duration_ms=180000,
    )
    db_session.add_all([user, task, intent, record])
    await db_session.commit()

    @asynccontextmanager
    async def fake_session_local():
        yield db_session

    monkeypatch.setattr("app.services.galaxy_execution_consumer.AsyncSessionLocal", fake_session_local)

    consumer = GalaxyExecutionConsumer(event_bus=object())  # type: ignore[arg-type]
    await consumer.handle_event(
        {
            "event_type": EXECUTION_RESULT_INGESTED,
            "user_id": str(user.id),
            "execution_intent_id": str(intent.id),
            "execution_record_id": str(record.id),
            "task_id": str(task.id),
            "success": True,
        }
    )

    nodes = (await db_session.execute(select(KnowledgeNode).where(KnowledgeNode.source_type == "openclaw_execution"))).scalars().all()
    links = (await db_session.execute(select(TaskKnowledgeLink).where(TaskKnowledgeLink.task_id == task.id))).scalars().all()
    await db_session.refresh(task)

    assert len(nodes) == 1
    assert "OpenClaw 执行沉淀" in nodes[0].name
    assert task.knowledge_node_id == nodes[0].id
    assert len(links) == 1
    assert links[0].knowledge_node_id == nodes[0].id


@pytest.mark.asyncio
async def test_achievement_event_consumer_processes_chat_control_execution_success(db_session, monkeypatch):
    user = User(
        id=uuid4(),
        username="achievement_exec_user",
        email="achievement_exec_user@example.com",
        hashed_password="hashed",
        is_active=True,
    )
    task = Task(
        id=uuid4(),
        user_id=user.id,
        title="隐藏终端委派",
        type=TaskType.LEARNING,
        tags=["openclaw", "chat_control"],
        estimated_minutes=15,
        difficulty=3,
        energy_cost=2,
        status=TaskStatus.IN_PROGRESS,
    )
    intent = ExecutionIntent(
        id=uuid4(),
        user_id=user.id,
        task_id=task.id,
        execution_mode=ExecutionMode.AGENT,
        executor=ExecutorType.OPENCLAW,
        goal="运行 pwd 并总结工作目录",
        instructions=["输出当前目录"],
        target_env=ExecutionTargetEnv.SHELL,
        policy={"chat_control": True},
        success_criteria={},
        result_contract={},
        timeout_seconds=120,
        status=ExecutionIntentStatus.SUCCEEDED,
        trust_level=TrustLevel.TRUSTED,
        idempotency_key=f"intent-{uuid4()}",
        completed_at=datetime.utcnow(),
    )
    record = ExecutionRecord(
        id=uuid4(),
        execution_intent_id=intent.id,
        user_id=user.id,
        task_id=task.id,
        executor_type="openclaw",
        raw_response={"status": "completed", "output": "pwd"},
        trust_level="trusted",
        duration_ms=61000,
    )
    db_session.add_all([user, task, intent, record])
    await db_session.commit()

    captured: list[dict[str, object]] = []

    @asynccontextmanager
    async def fake_session_local():
        yield db_session

    async def fake_process_event(self, user_id: str, event_type: str, **kwargs):
        captured.append(
            {
                "user_id": user_id,
                "event_type": event_type,
                **kwargs,
            }
        )
        return []

    monkeypatch.setattr("app.services.achievement_event_consumer.AsyncSessionLocal", fake_session_local)
    monkeypatch.setattr("app.services.achievement_event_consumer.AchievementEngine.process_event", fake_process_event)

    consumer = AchievementEventConsumer(event_bus=object())  # type: ignore[arg-type]
    await consumer.handle_event(
        {
            "event_type": EXECUTION_RESULT_INGESTED,
            "user_id": str(user.id),
            "execution_intent_id": str(intent.id),
            "execution_record_id": str(record.id),
            "task_id": str(task.id),
            "success": True,
        }
    )

    assert len(captured) == 1
    assert captured[0]["event_type"] == AchievementEvent.TASK_COMPLETED
    assert captured[0]["source"] == "execution_chat_control"
    assert captured[0]["task_id"] == str(task.id)


@pytest.mark.asyncio
async def test_plan_review_auto_delegate_generated_tasks_uses_execution_batch(db_session, monkeypatch):
    delegated_task_ids = []

    async def fake_classify_task(self, *, task_id, user_id):
        return SimpleNamespace(execution_mode=ExecutionMode.AGENT)

    async def fake_handoff_tasks_batch(self, *, task_ids, user_id, execution_strategy="auto"):
        delegated_task_ids.extend(task_ids)
        return {
            "items": [{"task_id": str(task_id), "status": "queued"} for task_id in task_ids],
        }

    monkeypatch.setattr(
        "app.services.execution_service.ExecutionService.classify_task",
        fake_classify_task,
    )
    monkeypatch.setattr(
        "app.services.execution_service.ExecutionService.handoff_tasks_batch",
        fake_handoff_tasks_batch,
    )

    task_a = uuid4()
    task_b = uuid4()

    service = PlanReviewService()
    await service._auto_delegate_generated_tasks(
        db_session=db_session,
        user_id=str(uuid4()),
        plan_id="plan-auto-delegate",
        tasks=[
            {"id": str(task_a)},
            {"id": str(task_b)},
        ],
    )

    assert delegated_task_ids == [task_a, task_b]
