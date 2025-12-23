import pytest
import pytest_asyncio
from datetime import date, datetime, timedelta
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import select

from app.models.base import Base
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskType
from app.models.galaxy import StudyRecord
from app.models.analytics import UserDailyMetric
from app.services.analytics_service import AnalyticsService

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(name="engine")
async def engine_fixture():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture(name="db")
async def db_fixture(engine):
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_analytics_service(db: AsyncSession):
    # 1. Setup Data
    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        username="test_analytics",
        email="analytics@test.com",
        hashed_password="hash",
        flame_level=5,
        flame_brightness=0.8
    )
    db.add(user)
    
    # Task 1: Completed today (Focus 30 min)
    task1 = Task(
        user_id=user_id,
        title="Task 1",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        actual_minutes=30,
        status=TaskStatus.COMPLETED,
        completed_at=datetime.utcnow()
    )
    db.add(task1)
    
    # Task 2: Completed today (Focus 20 min)
    task2 = Task(
        user_id=user_id,
        title="Task 2",
        type=TaskType.TRAINING,
        estimated_minutes=20,
        actual_minutes=20,
        status=TaskStatus.COMPLETED,
        completed_at=datetime.utcnow()
    )
    db.add(task2)
    
    # Study Record (Mastery +10)
    # Note: StudyRecord requires node_id. We need a KnowledgeNode if FK constraint is enforced.
    # Base.metadata.create_all creates all tables with FKs.
    # So we need a Subject and a Node.
    
    from app.models.subject import Subject
    from app.models.galaxy import KnowledgeNode
    
    subject = Subject(name="Math")
    db.add(subject)
    await db.flush()
    
    node = KnowledgeNode(name="Calculus", subject_id=subject.id, importance_level=3)
    db.add(node)
    await db.flush()
    
    record = StudyRecord(
        user_id=user_id,
        node_id=node.id,
        study_minutes=15,
        mastery_delta=10.0,
        record_type="review"
    )
    db.add(record)
    
    await db.commit()
    
    # 2. Run Analysis
    service = AnalyticsService(db)
    target_date = date.today()
    metric = await service.calculate_daily_metrics(user_id, target_date)
    
    # 3. Verify
    assert metric is not None
    assert metric.user_id == user_id
    assert metric.date == target_date
    assert metric.tasks_completed == 2
    assert metric.total_focus_minutes == 50 # 30 + 20
    assert metric.mastery_gained == 10.0
    assert metric.review_count == 1 # Based on record_type="review"
    
    # 4. Verify Summary
    summary = await service.get_user_profile_summary(user_id)
    print(summary)
    assert "User Profile Analysis" in summary
    assert "Total Focus Time: 50" in summary
    assert "Flame Level: 5" in summary

    # 5. Idempotency Check (Run again)
    metric_2 = await service.calculate_daily_metrics(user_id, target_date)
    assert metric_2.id == metric.id
    assert metric_2.total_focus_minutes == 50
