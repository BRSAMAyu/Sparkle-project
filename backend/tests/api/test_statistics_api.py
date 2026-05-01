from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.statistics import router as statistics_router
from app.models.galaxy import KnowledgeNode, StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User


@pytest.fixture
def statistics_client(db_session):
    app = FastAPI()
    app.include_router(statistics_router, prefix="/stats")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_activity_heatmap_returns_90_days_with_learning_minutes_and_task_counts(
    statistics_client,
    db_session,
):
    client, state = statistics_client

    user = User(
        username="stats_user",
        email="stats_user@example.com",
        hashed_password="hashed",
    )
    other_user = User(
        username="other_stats_user",
        email="other_stats_user@example.com",
        hashed_password="hashed",
    )
    db_session.add_all([user, other_user])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(other_user)
    state["current_user"] = user

    node = KnowledgeNode(name="热力学", importance_level=3)
    other_node = KnowledgeNode(name="线性代数", importance_level=2)
    db_session.add_all([node, other_node])
    await db_session.commit()
    await db_session.refresh(node)
    await db_session.refresh(other_node)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_at_noon = now.replace(hour=12, minute=0, second=0, microsecond=0)
    yesterday_at_noon = today_at_noon - timedelta(days=1)

    linked_task = Task(
        user_id=user.id,
        title="完成热力学练习",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=45,
        actual_minutes=40,
        status=TaskStatus.COMPLETED,
        completed_at=today_at_noon,
        knowledge_node_id=node.id,
    )
    fallback_task = Task(
        user_id=user.id,
        title="整理错题笔记",
        type=TaskType.REFLECTION,
        tags=[],
        estimated_minutes=20,
        actual_minutes=15,
        status=TaskStatus.COMPLETED,
        completed_at=today_at_noon,
    )
    yesterday_task = Task(
        user_id=user.id,
        title="回顾昨天内容",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=25,
        actual_minutes=30,
        status=TaskStatus.COMPLETED,
        completed_at=yesterday_at_noon,
    )
    foreign_task = Task(
        user_id=other_user.id,
        title="别人的任务",
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=90,
        actual_minutes=90,
        status=TaskStatus.COMPLETED,
        completed_at=today_at_noon,
        knowledge_node_id=other_node.id,
    )
    db_session.add_all([linked_task, fallback_task, yesterday_task, foreign_task])
    await db_session.commit()
    await db_session.refresh(linked_task)
    await db_session.refresh(fallback_task)
    await db_session.refresh(yesterday_task)
    await db_session.refresh(foreign_task)

    db_session.add_all(
        [
            StudyRecord(
                user_id=user.id,
                node_id=node.id,
                task_id=linked_task.id,
                study_minutes=35,
                mastery_delta=5.0,
                record_type="task_complete",
                created_at=today_at_noon,
            ),
            StudyRecord(
                user_id=other_user.id,
                node_id=other_node.id,
                task_id=foreign_task.id,
                study_minutes=90,
                mastery_delta=8.0,
                record_type="task_complete",
                created_at=today_at_noon,
            ),
        ]
    )
    await db_session.commit()

    response = client.get(
        "/stats/activity/heatmap",
        params={"user_id": str(user.id), "days": 90},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 90

    expected_start = (today_at_noon.date() - timedelta(days=89)).isoformat()
    expected_today = today_at_noon.date().isoformat()
    expected_yesterday = yesterday_at_noon.date().isoformat()

    assert payload[0]["date"] == expected_start
    assert payload[-1]["date"] == expected_today

    today_entry = next(item for item in payload if item["date"] == expected_today)
    yesterday_entry = next(item for item in payload if item["date"] == expected_yesterday)

    assert today_entry == {
        "date": expected_today,
        "minutes": 50.0,
        "tasks_completed": 2,
    }
    assert yesterday_entry == {
        "date": expected_yesterday,
        "minutes": 30.0,
        "tasks_completed": 1,
    }

    empty_entry = next(
        item for item in payload if item["date"] == (today_at_noon.date() - timedelta(days=2)).isoformat()
    )
    assert empty_entry["minutes"] == 0.0
    assert empty_entry["tasks_completed"] == 0
