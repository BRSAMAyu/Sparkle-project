"""COM-011: Similar goal pursuers — service + API tests."""
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user, get_db
from app.api.v1.community import router as community_router
from app.models.community import Friendship, FriendshipStatus
from app.models.goal import Goal
from app.models.user import User
from app.services.community_service import _cosine_sim, find_users_with_similar_goals
from app.schemas.community import SimilarGoalPursuer


# ---- helpers ----

class _FakeGoal(SimpleNamespace):
    pass


class _FakeUser(SimpleNamespace):
    pass


class _ScalarOneOrNone:
    def __init__(self, val):
        self._val = val

    def scalar_one_or_none(self):
        return self._val


class _AllResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _ScalarVal:
    def __init__(self, val):
        self._val = val

    def scalar(self):
        return self._val


def _make_db(goals_with_users=None, src_goal=None, mutual_count=0):
    """Build a fake AsyncSession that returns pre-canned results."""
    db = AsyncMock()

    # First call: fetch source goal
    # Second call: fetch candidates
    # Subsequent calls: mutual friend count
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return _ScalarOneOrNone(src_goal)
        elif call_count == 2:
            return _AllResult(goals_with_users or [])
        else:
            return _ScalarVal(mutual_count)

    db.execute = mock_execute
    return db


# ---- cosine similarity ----

def test_cosine_sim_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert _cosine_sim(v, v) == pytest.approx(1.0)


def test_cosine_sim_orthogonal_vectors():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert _cosine_sim(a, b) == pytest.approx(0.0)


def test_cosine_sim_zero_vector():
    assert _cosine_sim([0.0, 0.0], [1.0, 1.0]) == 0.0


# ---- find_users_with_similar_goals ----

@pytest.mark.asyncio
async def test_returns_empty_when_goal_not_found():
    db = _make_db(src_goal=None)
    result = await find_users_with_similar_goals(uuid4(), uuid4(), db)
    assert result == []


@pytest.mark.asyncio
@patch("app.services.embedding_service.embedding_service", new_callable=AsyncMock)
async def test_returns_scored_pursuers(mock_emb):
    """End-to-end: source goal + 2 candidates, embedding returns fixed vectors."""
    user_id = uuid4()
    goal_id = uuid4()

    src_goal = _FakeGoal(
        id=goal_id,
        title="Pass calculus exam",
        description="Final exam prep",
        goal_type="exam",
        target_date=None,
    )

    cand_user_1 = _FakeUser(
        id=uuid4(),
        nickname="Alice",
        username="alice",
        avatar_url=None,
    )
    cand_goal_1 = _FakeGoal(
        id=uuid4(),
        title="Pass calculus exam",
        description="Midterm review",
        goal_type="exam",
        target_date=None,
        progress=0.6,
        updated_at=None,
    )

    cand_user_2 = _FakeUser(
        id=uuid4(),
        nickname="Bob",
        username="bob",
        avatar_url=None,
    )
    cand_goal_2 = _FakeGoal(
        id=uuid4(),
        title="Learn guitar",
        description="Practice daily",
        goal_type="general",
        target_date=None,
        progress=0.2,
        updated_at=None,
    )

    candidates = [(cand_goal_1, cand_user_1), (cand_goal_2, cand_user_2)]

    # Mock embedding service: source gets [1,0], candidates get [1,0] and [0,1]
    mock_emb.get_embedding = AsyncMock(return_value=[1.0, 0.0])
    mock_emb.batch_embeddings = AsyncMock(
        return_value=[[1.0, 0.0], [0.0, 1.0]]
    )

    db = _make_db(src_goal=src_goal, goals_with_users=candidates, mutual_count=0)

    results = await find_users_with_similar_goals(user_id, goal_id, db, limit=5)

    assert len(results) == 2
    # Alice should rank higher (same type + same embedding direction)
    assert results[0]["display_name"] == "Alice"
    assert results[0]["goal_type"] == "exam"
    assert results[0]["similarity"] > results[1]["similarity"]


@pytest.mark.asyncio
@patch("app.services.embedding_service.embedding_service", new_callable=AsyncMock)
async def test_embedding_failure_graceful_fallback(mock_emb):
    """When embedding service fails, still returns results via type+time scoring."""
    user_id = uuid4()
    goal_id = uuid4()

    src_goal = _FakeGoal(
        id=goal_id, title="Test goal", description="",
        goal_type="exam", target_date=None,
    )
    cand_user = _FakeUser(id=uuid4(), nickname="X", username="x", avatar_url=None)
    cand_goal = _FakeGoal(
        id=uuid4(), title="Other goal", description="",
        goal_type="exam", target_date=None,
        progress=0.5, updated_at=None,
    )

    mock_emb.get_embedding = AsyncMock(side_effect=RuntimeError("API down"))
    mock_emb.batch_embeddings = AsyncMock(side_effect=RuntimeError("API down"))

    db = _make_db(src_goal=src_goal, goals_with_users=[(cand_goal, cand_user)], mutual_count=0)
    results = await find_users_with_similar_goals(user_id, goal_id, db, limit=5)

    assert len(results) == 1
    # Should still score via type_match (same goal_type "exam" → 1.0)
    assert results[0]["similarity"] > 0.0


@pytest.mark.asyncio
async def test_respects_limit_parameter():
    user_id = uuid4()
    goal_id = uuid4()

    src_goal = _FakeGoal(
        id=goal_id, title="G", description="", goal_type="general", target_date=None,
    )

    candidates = []
    for i in range(5):
        u = _FakeUser(id=uuid4(), nickname=f"U{i}", username=f"u{i}", avatar_url=None)
        g = _FakeGoal(
            id=uuid4(), title=f"Goal {i}", description="",
            goal_type="general", target_date=None,
            progress=0.0, updated_at=None,
        )
        candidates.append((g, u))

    with patch("app.services.embedding_service.embedding_service", new_callable=AsyncMock) as mock_emb:
        mock_emb.get_embedding = AsyncMock(return_value=[1.0])
        mock_emb.batch_embeddings = AsyncMock(
            return_value=[[1.0]] * 5
        )
        db = _make_db(src_goal=src_goal, goals_with_users=candidates, mutual_count=0)
        results = await find_users_with_similar_goals(user_id, goal_id, db, limit=2)
        assert len(results) == 2


# ---- schema ----

def test_similar_goal_pursuer_schema():
    data = {
        "user_id": uuid4(),
        "display_name": "Test User",
        "avatar_url": "https://example.com/avatar.png",
        "goal_title": "Pass exam",
        "goal_type": "exam",
        "goal_progress": 0.75,
        "similarity": 0.85,
        "last_active": None,
        "mutual_friends_count": 3,
    }
    pursuer = SimilarGoalPursuer(**data)
    assert pursuer.display_name == "Test User"
    assert pursuer.goal_progress == 0.75
    assert pursuer.mutual_friends_count == 3


async def _commit_all(db_session, *objects):
    db_session.add_all(list(objects))
    await db_session.commit()
    for obj in objects:
        await db_session.refresh(obj)


def _user(username: str, *, last_login_at: datetime | None = None) -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@example.com",
        hashed_password="hashed",
        nickname=username,
        last_login_at=last_login_at,
        is_active=True,
    )


def _accepted_friendship(a: UUID, b: UUID, *, initiated_by: UUID | None = None) -> Friendship:
    left, right = sorted([a, b], key=lambda value: str(value))
    return Friendship(
        user_id=left,
        friend_id=right,
        initiated_by=initiated_by or a,
        status=FriendshipStatus.ACCEPTED,
    )


@pytest.mark.asyncio
async def test_real_service_uses_canonical_friendship_for_mutual_count(db_session):
    current = _user("current")
    candidate = _user("candidate", last_login_at=datetime(2026, 5, 1, 10))
    mutual = _user("mutual")
    await _commit_all(db_session, current, candidate, mutual)

    source_goal = Goal(
        user_id=current.id,
        title="Pass calculus exam",
        goal_type="exam",
        status="active",
        target_date=date(2026, 6, 1),
        progress=0.2,
    )
    candidate_goal = Goal(
        user_id=candidate.id,
        title="Pass calculus final",
        goal_type="exam",
        status="active",
        target_date=date(2026, 6, 3),
        progress=0.7,
    )
    await _commit_all(
        db_session,
        source_goal,
        candidate_goal,
        _accepted_friendship(current.id, mutual.id, initiated_by=current.id),
        _accepted_friendship(candidate.id, mutual.id, initiated_by=candidate.id),
    )

    with patch("app.services.embedding_service.embedding_service") as mock_emb:
        mock_emb.get_embedding = AsyncMock(return_value=[1.0, 0.0])
        mock_emb.batch_embeddings = AsyncMock(return_value=[[1.0, 0.0]])

        result = await find_users_with_similar_goals(
            current.id,
            source_goal.id,
            db_session,
        )

    assert result[0]["user_id"] == candidate.id
    assert result[0]["mutual_friends_count"] == 1
    assert result[0]["last_active"] == candidate.last_login_at


@pytest.mark.asyncio
async def test_similar_pursuers_api_returns_goal_matches(db_session):
    current = _user("api_current")
    candidate = _user("api_candidate")
    await _commit_all(db_session, current, candidate)

    source_goal = Goal(
        user_id=current.id,
        title="Learn operating systems",
        goal_type="academic",
        status="active",
    )
    candidate_goal = Goal(
        user_id=candidate.id,
        title="Study operating systems",
        goal_type="academic",
        status="active",
        progress=0.4,
    )
    await _commit_all(db_session, source_goal, candidate_goal)

    app = FastAPI()
    app.include_router(community_router, prefix="/community")

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return current

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with patch("app.services.embedding_service.embedding_service") as mock_emb:
        mock_emb.get_embedding = AsyncMock(return_value=[1.0, 0.0])
        mock_emb.batch_embeddings = AsyncMock(return_value=[[1.0, 0.0]])
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/community/goals/{source_goal.id}/similar-pursuers",
            )

    app.dependency_overrides = {}

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["display_name"].startswith("api_candidate")
    assert payload[0]["goal_progress"] == 0.4
