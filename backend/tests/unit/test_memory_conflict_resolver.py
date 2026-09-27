from datetime import datetime, timedelta
from uuid import uuid4

from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.services.memory_conflict_resolver import MemoryConflictResolver

# wt611 时钟加固（V3-FIX-321 批一）：MemoryConflictResolver 本身不读宿主钟
# （仅 updated_at/occurred_at 的相对比较与 datetime.min 兜底），goal 播种的
# target_date 原为 date.today() 宿主钟——改冻结常数，pairwise 同值语义不变；
# _utcnow 相对偏移种子（now − days/hours）改为冻结常数基准，同表达式自洽。
FROZEN_UTC_NOW = datetime(2026, 9, 25, 20, 0)  # naive UTC（上海本地 09-26 04:00）
FROZEN_TODAY = FROZEN_UTC_NOW.date()


def _utcnow() -> datetime:
    """测试钟冻结常数（原 datetime.now(timezone.utc)）。"""
    return FROZEN_UTC_NOW


def test_preference_conflict_resolution():
    resolver = MemoryConflictResolver()
    user_id = uuid4()
    now = _utcnow()
    winner = MemoryPreference(
        id=uuid4(),
        user_id=user_id,
        pref_key="tone",
        pref_value={"value": "direct"},
        version=1,
        evidence_score=0.8,
        confidence=0.4,
        evidence_refs=[{"type": "event", "id": "evt_1"}],
        updated_at=now - timedelta(days=5),
    )
    loser = MemoryPreference(
        id=uuid4(),
        user_id=user_id,
        pref_key="tone",
        pref_value={"value": "soft"},
        version=2,
        evidence_score=0.4,
        confidence=0.9,
        evidence_refs=[{"type": "event", "id": "evt_2"}],
        updated_at=now,
    )

    resolved, winners, conflicts = resolver.resolve_preferences(
        {"tone": {"value": "soft"}},
        [winner, loser],
    )

    assert resolved["tone"] == {"value": "direct"}
    assert winners[0].id == winner.id
    assert conflicts


def test_goal_conflict_resolution():
    resolver = MemoryConflictResolver()
    user_id = uuid4()
    now = _utcnow()
    goal_a = MemoryGoal(
        id=uuid4(),
        user_id=user_id,
        title="Learn Rust",
        status="active",
        target_date=FROZEN_TODAY,
        evidence_score=0.7,
        evidence_refs=[{"type": "event", "id": "evt_1"}],
        updated_at=now - timedelta(days=1),
    )
    goal_b = MemoryGoal(
        id=uuid4(),
        user_id=user_id,
        title="learn rust",
        status="active",
        target_date=FROZEN_TODAY,
        evidence_score=0.5,
        evidence_refs=[{"type": "event", "id": "evt_2"}],
        updated_at=now,
    )

    resolved, conflicts = resolver.resolve_goals([goal_a, goal_b])

    assert len(resolved) == 1
    assert resolved[0].id == goal_a.id
    assert conflicts


def test_episodic_deduplication():
    resolver = MemoryConflictResolver()
    user_id = uuid4()
    now = _utcnow()
    winner = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary="Completed the sprint planning session",
        source_type="analysis",
        source_id="s1",
        occurred_at=now - timedelta(hours=2),
        evidence_score=0.9,
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    loser = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary="Completed the sprint planning session with the team",
        source_type="analysis",
        source_id="s2",
        occurred_at=now - timedelta(hours=1),
        evidence_score=0.5,
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    resolved, conflicts = resolver.resolve_episodic([loser, winner])

    assert len(resolved) == 1
    assert resolved[0].id == winner.id
    assert conflicts
