from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.galaxy import KnowledgeNode
from app.models.memory import EpisodicMemory
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_feedback import TaskFeedback
from app.models.task_resources import TaskKnowledgeLink
from app.models.user import User
from app.services.task_reflection_service import TaskReflectionService


@pytest.mark.asyncio
async def test_maybe_enqueue_reflection_prompt_for_difficult_feedback(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=uuid4(),
        user_id=user_id,
        plan_id=uuid4(),
        title="多元函数练习",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=25,
        actual_minutes=30,
        difficulty=4,
        energy_cost=2,
        tags=[],
    )
    feedback = TaskFeedback(
        id=uuid4(),
        user_id=user_id,
        task_id=task.id,
        category="too_difficult",
        feedback_text="太难了",
    )
    db_session.add_all([user, task, feedback])
    await db_session.commit()

    service = TaskReflectionService(db_session, redis=None)
    prompt = await service.maybe_enqueue_reflection_prompt(
        user_id=user_id,
        task=task,
        feedback=feedback,
        category="too_difficult",
        time_spent_minutes=30,
    )

    assert prompt is not None
    assert prompt["feedback_id"] == str(feedback.id)
    assert "概念没理解" in prompt["options"]


@pytest.mark.asyncio
async def test_submit_reflection_answer_persists_payload_and_creates_fragment(
    db_session,
    monkeypatch,
):
    user_id = uuid4()
    task_id = uuid4()
    feedback_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    task = Task(
        id=task_id,
        user_id=user_id,
        plan_id=uuid4(),
        title="线性代数补课",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=20,
        actual_minutes=22,
        difficulty=3,
        energy_cost=2,
        tags=[],
    )
    feedback = TaskFeedback(
        id=feedback_id,
        user_id=user_id,
        task_id=task_id,
        category="too_difficult",
    )
    db_session.add_all([user, task, feedback])
    await db_session.commit()

    created = {}

    async def fake_create_fragment(self, **kwargs):
        created["content"] = kwargs["content"]
        return SimpleNamespace(id=uuid4())

    async def fake_analyze_behavior(self, user_id, fragment_id):
        created["analyzed"] = True
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.create_fragment",
        fake_create_fragment,
    )
    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.analyze_behavior",
        fake_analyze_behavior,
    )

    service = TaskReflectionService(db_session, redis=None)
    payload = await service.submit_reflection_answer(
        user_id=user_id,
        feedback_id=feedback_id,
        selected_option="概念没理解",
        free_text="矩阵变换这块完全没跟上",
    )

    assert payload["status"] == "completed"
    await db_session.refresh(feedback)
    assert feedback.reflection_payload["selected_option"] == "概念没理解"
    assert feedback.reflection_payload["memory_id"]
    assert created["analyzed"] is True

    memory = await db_session.get(EpisodicMemory, feedback.reflection_payload["memory_id"])
    assert memory is not None
    assert memory.source_type == "reflection"
    assert "矩阵变换" in memory.summary


@pytest.mark.asyncio
async def test_submit_structured_reflection_links_galaxy_node_and_writes_connection(
    db_session,
    monkeypatch,
):
    user_id = uuid4()
    task_id = uuid4()
    feedback_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    node = KnowledgeNode(
        id=uuid4(),
        name="热力学",
        description="能量、状态量和热过程",
        keywords=["热力学", "状态方程"],
        is_seed=True,
        source_type="seed",
        importance_level=3,
    )
    previous = EpisodicMemory(
        user_id=user_id,
        summary="任务《热力学例题》反思；卡点：状态方程不知道何时使用",
        source_type="reflection",
        source_id="previous-reflection",
        source_lane="direct_capture",
        subject_type="reflection",
        occurred_at=datetime.now(UTC).replace(tzinfo=None),
        importance_score=0.7,
        confidence=0.8,
        tags=["task_reflection"],
        evidence_refs=[{"type": "summary", "id": "previous-reflection", "schema_version": "test.v1"}],
    )
    task = Task(
        id=task_id,
        user_id=user_id,
        plan_id=uuid4(),
        title="热力学公式练习",
        type=TaskType.LEARNING,
        status=TaskStatus.COMPLETED,
        estimated_minutes=20,
        actual_minutes=22,
        difficulty=3,
        energy_cost=2,
        tags=[],
    )
    feedback = TaskFeedback(
        id=feedback_id,
        user_id=user_id,
        task_id=task_id,
        category="too_difficult",
    )
    db_session.add_all([user, node, previous, task, feedback])
    await db_session.commit()

    async def fake_create_fragment(self, **kwargs):
        return SimpleNamespace(id=uuid4())

    async def fake_analyze_behavior(self, user_id, fragment_id):
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.create_fragment",
        fake_create_fragment,
    )
    monkeypatch.setattr(
        "app.services.task_reflection_service.CognitiveService.analyze_behavior",
        fake_analyze_behavior,
    )

    service = TaskReflectionService(db_session, redis=None)
    payload = await service.submit_reflection_answer(
        user_id=user_id,
        feedback_id=feedback_id,
        selected_option=None,
        free_text=None,
        stuck_point="热力学公式会背，但不知道什么时候套用",
        effective_method="先画状态图",
        adjustment_intention="下次先做一道代表题",
    )

    assert payload["memory_id"]
    assert "热力学" in payload["ai_response"]
    assert payload["linked_knowledge_nodes"][0]["id"] == str(node.id)

    link_result = await db_session.execute(
        select(TaskKnowledgeLink).where(
            TaskKnowledgeLink.task_id == task_id,
            TaskKnowledgeLink.knowledge_node_id == node.id,
        )
    )
    assert link_result.scalar_one().relation_type == "reflection_stuck_point"
