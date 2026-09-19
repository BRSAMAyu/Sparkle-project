"""C-02 · ContextPack 四分 source manifest 集成测试（sqlite）。

验证：
- pack.metadata["sources"] 四类分节齐全，state/memory 计量与注入内容一致；
- decision items 逐条经封闭投影归类（item_category_counts）——「每 item source type 正确」；
- seed/demo（startup_seed episodic）计数；
- telemetry memory_counts 附加 "sources"（context_pack_runs JSONB 可查）；
- 非resolver 分支 preference 同 key 折叠显式登记（读路径上游已按 M-01 版本链去重，
  此处为装配表达式的防线验证）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.services.memory_service import MemoryService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _seed_user_with_sources(db_session) -> tuple:
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()

    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.7},
        evidence_refs=[{"type": "event", "id": "evt_src_1"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Goal C02",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_src_2"}],
    )
    now = _utcnow()
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="real episodic memory",
        source_type="analysis",
        source_id="src_c02_a",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.7,
        tags=["study"],
        evidence_refs=[{"type": "event", "id": "evt_src_3"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="seeded episodic memory",
        source_type="startup_seed",
        source_id="src_c02_b",
        occurred_at=now - timedelta(hours=2),
        importance_score=0.9,
        tags=["seed"],
        evidence_refs=[{"type": "event", "id": "evt_src_4"}],
    )
    return user_id


def _builder(db_session) -> ContextPackBuilder:
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 400}})
    return ContextPackBuilder(db_session, scheduler=scheduler)


@pytest.mark.asyncio
async def test_pack_carries_four_category_source_manifest(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False)
    monkeypatch.setattr(settings, "ENABLE_DECISION_CONTEXT", True)
    user_id = await _seed_user_with_sources(db_session)

    pack = await _builder(db_session).build(user_id, intent="chat", query_text="复习高数")

    sources = (pack.metadata or {}).get("sources")
    assert isinstance(sources, dict)
    assert sources["schema_version"] == "context_sources.v1"

    sections = sources["sections"]
    for category in ("state", "memory", "knowledge", "events"):
        assert category in sections
        assert sections[category]["enabled"] is True
        assert "item_count" in sections[category] and "token_estimate" in sections[category]

    # memory：1 preference + 2 episodic（含 1 条 startup_seed）：
    assert sections["memory"]["item_count"] == 3
    assert sections["memory"]["seed_or_demo"] == 1
    assert len(sections["memory"]["seed_or_demo_items"]) == 1
    assert sources["seed_or_demo_items_total"] == 1  # R2-F1：两面同 key（值由 sections 汇总）

    # R2-F1：pack 面不适用的值为 None/空（key 恒在，形状由 contract 文件钉死）：
    assert sources["user_is_seed_or_demo"] is None  # pack 面不 fetch 用户行
    assert sources["late_stage_writers"] == {}
    assert sources["control_keys"] == []
    assert sources["unclassified"] == []

    # state：goal（Current State）+ signals（sqlite 下可能降级为 0，不硬断言数量）：
    assert sections["state"]["item_count"] >= 1
    assert sections["state"]["token_estimate"] >= 0

    # knowledge/events：pack 不携带，显式 0 + channel note（不静默空缺）：
    assert sections["knowledge"]["item_count"] == 0
    assert "note" in sections["knowledge"]
    assert sections["events"]["item_count"] == 0
    assert "note" in sections["events"]

    # decision items 封闭投影：goal→state、preference/episodic→memory：
    counts = sources["item_category_counts"]
    assert counts.get("state", 0) >= 1  # 1 goal
    assert counts.get("memory", 0) >= 2  # 1 preference + 1-2 episodic
    # token 口径：memory = preferences + episodic 注入 token：
    assert sections["memory"]["token_estimate"] == pack.token_usage["preferences"] + pack.token_usage["episodic"]


@pytest.mark.asyncio
async def test_pack_decision_items_all_classify(db_session, monkeypatch):
    """每个 decision_context item 的 type 都能投影到四类（封闭全覆盖）。"""
    from app.core.decision_context import DECISION_ITEM_TYPES
    from app.orchestration.context_sources import SOURCE_CATEGORIES, item_source_category

    for item_type in DECISION_ITEM_TYPES:
        assert item_source_category(item_type) in SOURCE_CATEGORIES

    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False)
    user_id = await _seed_user_with_sources(db_session)
    pack = await _builder(db_session).build(user_id, intent="chat")
    assert pack.decision_context is not None
    for item in pack.decision_context.items:
        assert item_source_category(item.type)  # 不抛 KeyError 即封闭词表内


@pytest.mark.asyncio
async def test_pack_telemetry_carries_sources(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", True)
    user_id = await _seed_user_with_sources(db_session)

    pack = await _builder(db_session).build(user_id, intent="chat")
    assert pack.pack_id is not None

    from sqlalchemy import select

    from app.models.context_pack import ContextPackRun

    result = await db_session.execute(select(ContextPackRun).where(ContextPackRun.id == pack.pack_id))
    run = result.scalar_one()
    assert "sources" in run.memory_counts
    sources = run.memory_counts["sources"]
    for category in ("state", "memory", "knowledge", "events"):
        assert category in sources
        assert "item_count" in sources[category]
        assert "token_estimate" in sources[category]
    assert sources["memory"]["item_count"] == 3
    # 既有读者口径不受附加键影响：
    from app.services.understanding_depth_metric_service import normalize_memory_counts

    assert (
        normalize_memory_counts(run.memory_counts)
        == run.memory_counts["preferences"] + run.memory_counts["goals"] + run.memory_counts["episodic"]
    )


@pytest.mark.asyncio
async def test_pack_preference_collapse_visible_when_records_share_key(db_session, monkeypatch):
    """非resolver 分支：同 key 多记录折叠显式登记（防线：当前读路径上游已去重）。"""
    from app.orchestration.context_sources import detect_preference_key_overrides

    class _Record:
        def __init__(self, rid, key, value):
            self.id = rid
            self.pref_key = key
            self.pref_value = value

    overrides = detect_preference_key_overrides(
        [
            _Record("r1", "depth_preference", {"value": 0.3}),
            _Record("r2", "depth_preference", {"value": 0.9}),
        ]
    )
    assert len(overrides) == 1
    assert overrides[0].resolution == "last_write_wins_visible"

    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False)
    user_id = await _seed_user_with_sources(db_session)
    pack = await _builder(db_session).build(user_id, intent="chat")
    sources = (pack.metadata or {})["sources"]
    # 读路径单 key 单记录 → 无折叠覆盖（显式为空，而不是无此面）：
    assert sources["overrides"] == []
