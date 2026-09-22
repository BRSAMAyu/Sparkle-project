"""D-COMM-1 · 自我 7 日锚视图 API 测试（排行榜 P1 债务 #3 裁决落地）。

覆盖（验收红线）：
- 鉴权：无凭据 → 401（排行榜域端点全部鉴权的既有约定）；
- 诚实空态：窗口内零记录 → 全零 7 日序列 + has_any_data=False（不造数据）；
- 按日聚合正确性：冲刺完成度（任务账本口径）与掌握度增量（study_records）
  落日分桶、合计、旧→新排序；
- 语义排除：ABANDONED 任务（abandon 也会写 completed_at，task_service.py:1238）、
  软删任务、窗口外数据、他用户数据（跨用户隔离）一律不可见。

数据源复用既有面：sprint_ledger_condition（BP-4 单一事实源）+ StudyRecord；
in-memory sqlite（DATABASE_URL 由 conftest/环境前缀给定），零迁移。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.leaderboards import router as leaderboards_router
from app.db.session import get_db
from app.models.galaxy import StudyRecord
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User

UTC_NOW = None  # set per-test via _utcnow()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.fixture
def anchor_client(db_session):
    """Leaderboards router under test with real db_session and injectable user."""
    app = FastAPI()
    app.include_router(leaderboards_router, prefix="/leaderboards")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        if state["current_user"] is None:
            raise RuntimeError("test bug: current_user not set")
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.fixture
def no_auth_client(db_session):
    """No get_current_user override → real dependency → 401 without credentials."""
    app = FastAPI()
    app.include_router(leaderboards_router, prefix="/leaderboards")

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _make_user(db_session, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="hashed",
        nickname=username,
    )
    db_session.add(user)
    return user


def _make_completed_task(
    db_session, user_id, completed_at: datetime, *, status=TaskStatus.COMPLETED, deleted=False
) -> Task:
    task = Task(
        user_id=user_id,
        title=f"task-{uuid4().hex[:8]}",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        status=status,
        completed_at=completed_at,
    )
    if deleted:
        task.deleted_at = completed_at
    db_session.add(task)
    return task


def _make_study_record(db_session, user_id, created_at: datetime, delta: float) -> StudyRecord:
    return StudyRecord(
        user_id=user_id,
        node_id=uuid4(),
        study_minutes=20,
        mastery_delta=delta,
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_self_anchor_requires_auth(no_auth_client):
    """无凭据访问自我锚视图 → 401（鉴权语义）。"""
    response = no_auth_client.get("/leaderboards/self-anchor")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_self_anchor_empty_window_is_honest_zeros(anchor_client, db_session):
    """窗口内零记录 → 7 日全零序列 + has_any_data=False（诚实空态）。"""
    user = _make_user(db_session, "anchor_empty_user")
    await db_session.commit()
    anchor_client[1]["current_user"] = user

    response = anchor_client[0].get("/leaderboards/self-anchor")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert len(data["series"]) == 7
    assert data["has_any_data"] is False
    assert data["total_tasks_completed"] == 0
    assert data["total_mastery_delta"] == 0.0
    # 窗口语义：结束日=今天（UTC），7 天连续，旧→新
    today = _utcnow().date().isoformat()
    assert data["window_end"] == today
    assert data["series"][-1]["date"] == today
    dates = [point["date"] for point in data["series"]]
    assert dates == sorted(dates)
    assert all(point["tasks_completed"] == 0 for point in data["series"])
    assert all(point["mastery_delta"] == 0.0 for point in data["series"])


@pytest.mark.asyncio
async def test_self_anchor_buckets_tasks_and_mastery_by_day(anchor_client, db_session):
    """按日分桶：完成度落 completed_at、掌握度落 created_at；合计与排序正确。"""
    user = _make_user(db_session, "anchor_bucket_user")
    await db_session.commit()
    anchor_client[1]["current_user"] = user

    now = _utcnow()

    # 完成面：今天 2 单 + 2 天前 1 单（应计入）；噪声：ABANDONED（写过 completed_at）、
    # 软删完成、窗口外（8 天前）——均不得计入
    _make_completed_task(db_session, user.id, now)
    _make_completed_task(db_session, user.id, now - timedelta(hours=1))
    _make_completed_task(db_session, user.id, now - timedelta(days=2))
    _make_completed_task(db_session, user.id, now - timedelta(days=3), status=TaskStatus.ABANDONED)
    _make_completed_task(db_session, user.id, now - timedelta(days=1), deleted=True)
    _make_completed_task(db_session, user.id, now - timedelta(days=8))

    # 掌握度面：今天 +12.5/-2.5、2 天前 +3.5（应计入）；窗口外 8 天前不计入
    db_session.add_all(
        [
            _make_study_record(db_session, user.id, now, 12.5),
            _make_study_record(db_session, user.id, now - timedelta(hours=2), -2.5),
            _make_study_record(db_session, user.id, now - timedelta(days=2), 3.5),
            _make_study_record(db_session, user.id, now - timedelta(days=8), 99.0),
        ]
    )
    await db_session.commit()

    response = anchor_client[0].get("/leaderboards/self-anchor")

    assert response.status_code == 200
    data = response.json()["data"]
    series = data["series"]

    today_point = series[-1]
    assert today_point["tasks_completed"] == 2
    assert today_point["mastery_delta"] == pytest.approx(10.0)

    two_days_ago = series[-3]
    assert two_days_ago["tasks_completed"] == 1
    assert two_days_ago["mastery_delta"] == pytest.approx(3.5)

    # ABANDONED 落 3 天前那天必须为 0（状态过滤不可省）
    assert series[-4]["tasks_completed"] == 0

    assert data["total_tasks_completed"] == 3
    assert data["total_mastery_delta"] == pytest.approx(13.5)
    assert data["has_any_data"] is True


@pytest.mark.asyncio
async def test_self_anchor_excludes_other_users_data(anchor_client, db_session):
    """跨用户隔离：他人的完成/掌握度事件不影响我的自我视图。"""
    me = _make_user(db_session, "anchor_me")
    other = _make_user(db_session, "anchor_other")
    await db_session.commit()
    anchor_client[1]["current_user"] = me

    now = _utcnow()
    _make_completed_task(db_session, other.id, now)
    db_session.add(_make_study_record(db_session, other.id, now, 50.0))
    await db_session.commit()

    response = anchor_client[0].get("/leaderboards/self-anchor")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["has_any_data"] is False
    assert data["total_tasks_completed"] == 0
    assert data["total_mastery_delta"] == 0.0
