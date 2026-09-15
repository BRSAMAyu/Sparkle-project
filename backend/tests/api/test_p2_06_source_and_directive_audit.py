from __future__ import annotations

from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1.insights import router as insights_router
from app.api.v1.tasks import router as tasks_router
from app.core.cache import cache_service
from app.models.file_storage import StoredFile
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.task_resources import TaskResourceLink, TaskResourceType
from app.models.user import User
from app.signals.causal_trace_store import CausalTraceStore
from app.signals.types import (
    ActionableSignal,
    DirectiveApplicationAudit,
    ExecutionDirective,
    NotificationDirective,
    PolicyDecision,
)


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

    async def set(self, key, value, ex=None):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)

    async def delete(self, key):
        self.values.pop(key, None)

    async def lrem(self, key, count, value):
        self.lists[key] = [item for item in self.lists.get(key, []) if item != value]

    async def lpush(self, key, *values):
        current = self.lists.setdefault(key, [])
        for value in values:
            current.insert(0, value)

    async def lrange(self, key, start, end):
        current = self.lists.get(key, [])
        stop = None if end == -1 else end + 1
        return current[start:stop]

    async def ltrim(self, key, start, end):
        current = self.lists.get(key, [])
        stop = None if end == -1 else end + 1
        self.lists[key] = current[start:stop]

    async def expire(self, key, ttl):
        return True


@pytest.fixture
def p2_06_client(db_session, monkeypatch):
    app = FastAPI()
    app.include_router(tasks_router, prefix="/tasks")
    app.include_router(insights_router, prefix="/insights")

    state = {"current_user": None}
    fake_redis = FakeRedis()

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user
    monkeypatch.setattr(cache_service, "redis", fake_redis)

    with TestClient(app) as client:
        yield client, state, fake_redis


async def _create_user(db_session, suffix: str = "p206") -> User:
    user = User(
        username=f"user_{suffix}",
        email=f"user_{suffix}@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_task(db_session, user_id: UUID, title: str = "Bound source task") -> Task:
    task = Task(
        user_id=user_id,
        title=title,
        type=TaskType.LEARNING,
        tags=[],
        estimated_minutes=25,
        difficulty=2,
        energy_cost=1,
        status=TaskStatus.PENDING,
        priority=1,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


async def _create_file(db_session, user_id: UUID, *, name: str, lifecycle_status: str) -> StoredFile:
    file_record = StoredFile(
        user_id=user_id,
        file_name=name,
        mime_type="application/pdf",
        file_size=1024,
        bucket="test",
        object_key=f"test/{name}",
        status="parsed",
        lifecycle_status=lifecycle_status,
    )
    db_session.add(file_record)
    await db_session.commit()
    await db_session.refresh(file_record)
    return file_record


@pytest.mark.asyncio
async def test_get_task_returns_revoked_bound_source(p2_06_client, db_session):
    client, state, _redis = p2_06_client
    user = await _create_user(db_session, "source_revoked")
    task = await _create_task(db_session, user.id)
    source = await _create_file(
        db_session,
        user.id,
        name="revoked-notes.pdf",
        lifecycle_status="revoked",
    )
    db_session.add(TaskDocument(task_id=task.id, file_id=source.id, linked_by="ai"))
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    bound_sources = response.json()["data"]["bound_sources"]
    assert bound_sources[0]["title"] == "revoked-notes.pdf"
    assert bound_sources[0]["lifecycle_status"] == "revoked"


@pytest.mark.asyncio
async def test_list_tasks_returns_archived_legacy_file_resource(p2_06_client, db_session):
    client, state, _redis = p2_06_client
    user = await _create_user(db_session, "source_archived")
    task = await _create_task(db_session, user.id, title="Legacy resource task")
    source = await _create_file(
        db_session,
        user.id,
        name="archived-pack.pdf",
        lifecycle_status="archived",
    )
    db_session.add(
        TaskResourceLink(
            task_id=task.id,
            resource_type=TaskResourceType.FILE.value,
            resource_id=source.id,
            summary="legacy file",
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.get("/tasks")

    assert response.status_code == 200
    payload = response.json()["data"][0]
    assert payload["bound_sources"][0]["title"] == "archived-pack.pdf"
    assert payload["bound_sources"][0]["lifecycle_status"] == "archived"


@pytest.mark.asyncio
async def test_recent_directives_returns_signal_policy_and_audit(p2_06_client):
    client, state, redis = p2_06_client
    user = User(id=UUID("00000000-0000-0000-0000-000000000201"), username="trace_user", email="trace@example.com")
    state["current_user"] = user
    store = CausalTraceStore(redis)
    trace = await store.create_trace("trace-1")
    await store.link_to_user(str(user.id), trace.trace_id)
    signal = ActionableSignal(
        signal_id="sig-1",
        source_event_ids=["evt-1"],
        source_system="task_service",
        state_key="recent_task_overrun",
        claim="two long tasks overran",
        confidence=0.82,
        scope="today",
        ttl_hours=24,
        evidence_summary="2/2 recent tasks ran long",
        possible_effects=["smaller_task"],
        priority="high",
    )
    policy = PolicyDecision(
        policy_decision_id="pol-1",
        primary_strategy="recover_execution_rhythm",
        secondary_strategy=None,
        hard_constraints={"max_task_duration_min": 25},
        soft_biases={},
        visibility="log",
        requires_user_confirmation=False,
        reasoning_summary="Recent tasks exceeded planned duration.",
    )
    directive = ExecutionDirective(
        directive_id="ed-1",
        policy_decision_id="pol-1",
        target_module="task_generator",
        scope="today",
        hard_constraints={"max_task_duration_min": 25},
        user_visible_reason="Recent tasks ran long, so this one was reduced.",
    )
    audit = DirectiveApplicationAudit(
        audit_id="audit-1",
        directive_id="ed-1",
        target_module="task_generator",
        applied=True,
        applied_constraints=["max_task_duration_min"],
        violations=[],
        generated_output_id="task-1",
        generated_output_summary={"duration_min": 25},
    )
    await store.append_signal(trace.trace_id, signal)
    await store.store_signal(signal)
    await store.append_policy(trace.trace_id, policy)
    await store.append_directive(trace.trace_id, directive)
    await store.append_audit(trace.trace_id, audit)

    response = client.get("/insights/recent-directives")

    assert response.status_code == 200
    item = response.json()["data"][0]
    assert item["display_type"] == "DowngradeIntensity"
    assert item["trigger_signal"]["claim"] == "two long tasks overran"
    assert item["policy"]["primary_strategy"] == "recover_execution_rhythm"
    assert item["actual_result"]["applied"] is True


@pytest.mark.asyncio
async def test_recent_directives_filters_by_display_type(p2_06_client):
    client, state, redis = p2_06_client
    user = User(id=UUID("00000000-0000-0000-0000-000000000202"), username="notify_user", email="notify@example.com")
    state["current_user"] = user
    store = CausalTraceStore(redis)
    trace = await store.create_trace("trace-2")
    await store.link_to_user(str(user.id), trace.trace_id)
    notify = NotificationDirective(
        directive_id="nd-1",
        policy_decision_id="pol-2",
        allowed=True,
        trigger="first_task_not_started",
    )
    skip = NotificationDirective(
        directive_id="nd-2",
        policy_decision_id="pol-2",
        allowed=False,
        trigger="quiet_hours",
    )
    await store.store_directive_by_id(notify.directive_id, notify.to_dict())
    await store.store_directive_by_id(skip.directive_id, skip.to_dict())
    trace.directive_ids.extend([notify.directive_id, skip.directive_id])
    await store._save_trace(trace)

    response = client.get("/insights/recent-directives?directive_type=SkipReminder")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["directive_id"] == "nd-2"
    assert data[0]["display_type"] == "SkipReminder"
