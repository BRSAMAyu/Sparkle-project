from __future__ import annotations

import json

import pytest

from app.celery_schedule import setup_periodic_tasks
from app.signals.goal_world_graph import GoalWorldGraph, GoalWorldGraphService, GraphNode
from app.signals.growth_chronicle import ChronicleEntry, GrowthChronicleService
from app.signals.recall_opportunity import RecallOpportunityDetector
from app.signals.skill_lifecycle import SkillLifecycleManager
from app.signals.types import SkillEntry
from tests.unit.spine._helpers import FakeRedis


class _Sender:
    def __init__(self) -> None:
        self.names: list[str] = []

    def add_periodic_task(self, interval, signature, name: str) -> None:
        del interval, signature
        self.names.append(name)


class _Result:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _FakeDb:
    def __init__(self, value=None) -> None:
        self.value = value
        self.added = []
        self.commits = 0

    async def execute(self, statement):
        del statement
        return _Result(self.value)

    def add(self, record) -> None:
        self.added.append(record)

    async def commit(self) -> None:
        self.commits += 1


def test_celery_schedule_runs_l4_reflection_and_decay_jobs():
    sender = _Sender()

    setup_periodic_tasks(sender)

    assert "run-daily-goal-reflections-every-day" in sender.names
    assert "spine-expire-stale-states-every-6h" in sender.names
    assert "spine-auto-deprecate-skills-every-day" in sender.names
    assert "apply-memory-decay-every-day" in sender.names


def test_skill_contraindications_block_inapplicable_reuse():
    skill = SkillEntry(
        skill_id="skill-1",
        scope="personal",
        source_policy_key="repair_knowledge_gap",
        strategy={"intervention_summary": "先诊断前置缺口"},
        applicable_when={"goal_mode": "exam"},
        evidence={"avg_confidence": 0.91},
        privacy={"contains_personal_data": True, "shareable": False},
        contraindications=["avoid_if:user_explicitly_declines", "avoid_if:current_context=free_exploration"],
        effective_count=5,
        sample_size=6,
    )
    manager = SkillLifecycleManager(FakeRedis())

    assert manager.find_applicable_skills([skill], {"goal_mode": "exam"})
    assert manager.find_applicable_skills([skill], {"goal_mode": "exam", "user_explicitly_declines": True}) == []
    assert manager.find_applicable_skills([skill], {"goal_mode": "exam", "current_context": "free_exploration"}) == []
    assert manager.validate_extraction(skill)["valid"] is True


def test_recall_trigger_exposes_user_visible_value_reason_and_score():
    trigger = RecallOpportunityDetector().check_task_missed(
        user_id="u1",
        task_id="task-1",
        deadline_hours=-3,
        is_completed=False,
    )

    assert trigger is not None
    payload = trigger.to_dict()
    assert payload["value_reason"]
    assert payload["recall_score"] > 0.7
    signal = RecallOpportunityDetector().to_actionable_signal(trigger)
    assert signal.confidence == payload["recall_score"]
    assert "计划健康" in signal.evidence_summary


@pytest.mark.asyncio
async def test_goal_world_graph_persists_to_durable_snapshot():
    service = GoalWorldGraphService(FakeRedis(), db_session=_FakeDb())
    graph = GoalWorldGraph(
        graph_id="gwg-1",
        user_id="u1",
        goal_id="goal-1",
        goal_type="exam",
        nodes=[GraphNode(node_id="n1", label="TCP", status="pending")],
    )

    await service._save(graph)

    assert service.db.commits == 1
    record = service.db.added[0]
    assert record.user_id == "u1"
    assert record.goal_id == "goal-1"
    assert record.payload["nodes"][0]["label"] == "TCP"


@pytest.mark.asyncio
async def test_goal_world_graph_loads_from_durable_snapshot_on_redis_miss():
    from app.aurora.runtime_v1.models import GoalWorldGraphSnapshot

    record = GoalWorldGraphSnapshot(user_id="u1", goal_id="goal-1")
    record.payload = {
        "graph_id": "gwg-1",
        "user_id": "u1",
        "goal_id": "goal-1",
        "goal_type": "exam",
        "nodes": [{"node_id": "n1", "label": "TCP"}],
        "coverage": 0.0,
    }
    service = GoalWorldGraphService(FakeRedis(), db_session=_FakeDb(record))

    graph = await service.get_graph("u1", "goal-1")

    assert graph is not None
    assert graph.nodes[0].label == "TCP"


@pytest.mark.asyncio
async def test_growth_chronicle_persists_and_loads_from_durable_snapshot():
    redis = FakeRedis()
    service = GrowthChronicleService(redis, db_session=_FakeDb())
    entry = ChronicleEntry(
        entry_id="chron-1",
        user_id="u1",
        entry_type="milestone",
        timestamp="2026-05-02T00:00:00Z",
        title="第一次完成",
        narrative="你完成了第一张任务卡。",
        evidence_refs=["task-1"],
        user_editable=True,
        user_status="confirmed",
    )

    await service._save_entries("u1", [entry])

    assert service.db.commits == 1
    record = service.db.added[0]
    assert record.confirmed_count == 1

    redis_empty = FakeRedis()
    loader = GrowthChronicleService(redis_empty, db_session=_FakeDb(record))
    loaded = await loader.get_chronicle("u1")

    assert loaded[0].title == "第一次完成"
    cached_raw = await redis_empty.get("spine:chronicle:u1")
    assert json.loads(cached_raw)[0]["entry_id"] == "chron-1"
