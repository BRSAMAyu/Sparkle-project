"""C-01 · DecisionContext / ContextPack 契约冻结测试（parity guard）。

冻结内容（任何变更都需要契约版本号 bump + 两位 reviewer）：
1. 三个契约 dataclass 的字段集（名称 + 顺序）；
2. ref URI scheme / scope / why_included / item type 封闭词表；
3. ttl_or_epoch 语义规则（每个 item 至少携带其一）；
4. ContextPack 向后兼容面（旧签名可构造、to_prompt_context 输出 key 集不变）；
5. ContextPackBuilder 必须为每次 build 填充 decision_context（含降级路径）。

纯 Python 消费（Aurora/Router/Planner 均在 backend/app 内进程消费），
故 parity guard 采用契约快照（字段集哈希 + 词表冻结）而非跨语言生成物对比。
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY

from app.config import settings
from app.core.cache import cache_service
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPack, ContextPackBuilder
from app.core.decision_context import (
    CONTEXT_ITEM_DESCRIPTOR_FIELDS,
    DECISION_CONTEXT_FIELDS,
    DECISION_CONTEXT_SCHEMA_VERSION,
    DECISION_DEGRADED_REASONS,
    DECISION_INCLUDE_REASONS,
    DECISION_ITEM_TYPES,
    DECISION_REF_SCHEMES,
    DECISION_SCOPES,
    DECISION_STATE_SIGNAL_FIELDS,
    DEFAULT_DECISION_SIGNAL_FIELDS,
    ContextItemDescriptor,
    DecisionContext,
    DecisionStateSignal,
    _default_signal_projection,
)

# 模块级导入确保 sqlite 建表覆盖聚合器所需的表（follow test_state_aggregator_service 惯例）
from app.models.achievement import UserStreakStats  # noqa: F401
from app.models.cognitive import CognitiveFragment  # noqa: F401
from app.models.focus import FocusSession  # noqa: F401
from app.models.memory import MemoryPreference
from app.models.srl_phase_state import SRLPhaseStateRecord  # noqa: F401
from app.models.user import User
from app.services.memory_service import MemoryService
from app.state_aggregator.service import StateAggregatorService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _field_names(cls) -> tuple[str, ...]:
    return tuple(field.name for field in dataclasses.fields(cls))


# ---------------------------------------------------------------------------
# Part A — 契约冻结（无 DB）
# ---------------------------------------------------------------------------


def test_contract_schema_version_frozen():
    assert DECISION_CONTEXT_SCHEMA_VERSION == "decision_context.v1"


def test_contract_field_sets_frozen():
    """字段集快照：名称、顺序、冻结哈希三者齐验，防任何静默漂移。"""
    assert _field_names(ContextItemDescriptor) == CONTEXT_ITEM_DESCRIPTOR_FIELDS
    assert _field_names(DecisionStateSignal) == DECISION_STATE_SIGNAL_FIELDS
    assert _field_names(DecisionContext) == DECISION_CONTEXT_FIELDS

    # 冻结哈希：三个 dataclass 的 (name, type) 序列的 sha256 截断
    fingerprint = hashlib.sha256(
        json.dumps(
            [
                [cls.__name__, [[f.name, str(f.type)] for f in dataclasses.fields(cls)]]
                for cls in (ContextItemDescriptor, DecisionStateSignal, DecisionContext)
            ],
            sort_keys=False,
        ).encode("utf-8")
    ).hexdigest()

    assert (
        fingerprint
        == hashlib.sha256(
            json.dumps(
                [
                    ["ContextItemDescriptor", [[n, t] for n, t in _DECLARED_ITEM_FIELDS]],
                    ["DecisionStateSignal", [[n, t] for n, t in _DECLARED_SIGNAL_FIELDS]],
                    ["DecisionContext", [[n, t] for n, t in _DECLARED_CONTEXT_FIELDS]],
                ],
                sort_keys=False,
            ).encode("utf-8")
        ).hexdigest()
    )


_DECLARED_ITEM_FIELDS = [
    ("ref", "str"),
    ("type", "str"),
    ("scope", "str"),
    ("why_included", "tuple[str, ...]"),
    ("ttl_seconds", "int | None"),
    ("epoch", "str | None"),
    ("relevance", "float | None"),
    ("version", "str"),
]
_DECLARED_SIGNAL_FIELDS = [
    ("name", "str"),
    ("ref", "str"),
    # V3-FIX-09/F3: value 只读化（构造时固化为 MappingProxyType），注解随之反映只读面
    ("value", "Mapping[str, Any]"),
    ("why_included", "tuple[str, ...]"),
    ("ttl_seconds", "int | None"),
    ("epoch", "str | None"),
    ("computed_at", "datetime | str | None"),
    ("freshness_seconds", "int | None"),
    ("source_snapshot_ids", "tuple[str, ...]"),
    ("version", "str"),
]
# 注意：无默认值字段（user_id/intent）必须前置于带默认值字段（dataclass 规则）
_DECLARED_CONTEXT_FIELDS = [
    ("user_id", "UUID"),
    ("intent", "str"),
    ("schema_version", "str"),
    ("route_intent", "str | None"),
    ("focus_mode", "str | None"),
    ("plan_id", "UUID | None"),
    ("query_text_hash", "str | None"),
    ("signals", "tuple[DecisionStateSignal, ...]"),
    ("items", "tuple[ContextItemDescriptor, ...]"),
    ("omitted_counts", "Mapping[str, int]"),
    ("degraded_fields", "tuple[str, ...]"),
    ("built_at", "datetime | None"),
    # V3-FIX-09/F1: 可选尾字段——降级原因封闭词表（治理模式与真降级可区分）
    ("degraded_reasons", "Mapping[str, str]"),
]


def test_closed_vocabularies_frozen():
    assert frozenset({"user", "session", "plan", "task", "global"}) == DECISION_SCOPES
    assert frozenset({"memory", "user_state", "plan", "document", "profile"}) == DECISION_REF_SCHEMES
    assert (
        frozenset(
            {
                "rank_policy",
                "evidence_order",
                "budget_carryover",
                "semantic_gate",
                "focus_mode",
                "plan_scope",
                "state_signal",
                "direct_request",
                "diversity",
                "fallback",
            }
        )
        == DECISION_INCLUDE_REASONS
    )
    assert (
        frozenset(
            {
                "preference",
                "goal",
                "episodic_memory",
                "plan",
                "user_state_signal",
                "document_chunk",
            }
        )
        == DECISION_ITEM_TYPES
    )


def test_default_signal_fields_frozen():
    """默认高信号字段集 = Router/Aurora 最小共同需要，属冻结契约一部分。"""
    assert DEFAULT_DECISION_SIGNAL_FIELDS == ("engagement_state", "emotion_hint", "srl_phase")


def test_item_descriptor_requires_ttl_or_epoch():
    good = ContextItemDescriptor(
        ref="memory://episodic/00000000-0000-0000-0000-000000000001",
        type="episodic_memory",
        scope="user",
        why_included=("rank_policy",),
        epoch="2026-09-19T00:00:00",
    )
    assert good.validate() == ()

    missing_both = ContextItemDescriptor(
        ref="memory://goal/00000000-0000-0000-0000-000000000002",
        type="goal",
        scope="user",
        why_included=("rank_policy",),
    )
    violations = missing_both.validate()
    assert any("ttl" in v and "epoch" in v for v in violations)

    ttl_only = ContextItemDescriptor(
        ref="user_state://engagement_state",
        type="user_state_signal",
        scope="user",
        why_included=("state_signal",),
        ttl_seconds=60,
    )
    assert ttl_only.validate() == ()


def test_item_descriptor_flags_unknown_vocabulary():
    bad = ContextItemDescriptor(
        ref="weird://thing/1",
        type="alien_type",
        scope="galaxy",
        why_included=(),
        ttl_seconds=1,
    )
    violations = bad.validate()
    assert any("ref scheme" in v for v in violations)
    assert any("type" in v for v in violations)
    assert any("scope" in v for v in violations)
    assert any("why_included" in v for v in violations)


def test_decision_context_validation_aggregates_and_dedupes():
    item = ContextItemDescriptor(
        ref="memory://goal/x",
        type="goal",
        scope="user",
        why_included=("rank_policy",),
        epoch="e1",
    )
    signal = DecisionStateSignal(
        name="engagement_state",
        ref="user_state://engagement_state",
        value={"streak": 3},
        ttl_seconds=60,
        epoch="user_state.v1.13",
    )
    ctx = DecisionContext(
        user_id=uuid4(),
        intent="chat",
        route_intent=None,
        focus_mode=None,
        plan_id=None,
        query_text_hash=None,
        signals=(signal,),
        items=(item,),
        omitted_counts={"goals": 0},
        degraded_fields=(),
        built_at=_utcnow(),
    )
    assert ctx.validate() == ()
    assert ctx.signal("engagement_state") is signal
    assert ctx.signal("emotion_hint") is None
    assert ctx.items_in_scope("user") == (item,)
    assert ctx.items_of_type("goal") == (item,)


def test_decision_context_serialization_is_json_safe():
    signal = DecisionStateSignal(
        name="srl_phase",
        ref="user_state://srl_phase",
        value={"current_phase": "forethought", "confidence": 0.8},
        ttl_seconds=30,
        epoch="user_state.v1.13",
        computed_at=_utcnow(),
        freshness_seconds=0,
        source_snapshot_ids=("srl:1",),
    )
    ctx = DecisionContext(
        user_id=uuid4(),
        intent="chat",
        route_intent="chat",
        focus_mode="chat_focus",
        plan_id=None,
        query_text_hash="ab12",
        signals=(signal,),
        items=(),
        omitted_counts={"preferences": 2},
        degraded_fields=("emotion_hint",),
        built_at=_utcnow(),
    )
    payload = ctx.to_dict()
    serialized = json.dumps(payload)  # 不得抛异常
    assert "ab12" in serialized
    # 序列化产物是普通 dict（可 JSON 化）；契约对象上的 omitted_counts 是只读 Mapping
    assert isinstance(payload["omitted_counts"], dict)
    with pytest.raises(TypeError):
        ctx.omitted_counts["goals"] = 99


def test_signal_value_is_immutable_projection():
    """V3-FIX-09/F3：signal value 构造后只读——进程内突变必须当场炸（mutation 必红）。"""
    signal = DecisionStateSignal(
        name="engagement_state",
        ref="user_state://engagement_state",
        value={"streak": 3},
        ttl_seconds=60,
        epoch="user_state.v1.13",
    )
    assert signal.validate() == ()
    with pytest.raises(TypeError):
        signal.value["streak"] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        signal.value["injected"] = True  # type: ignore[index]
    # 序列化面仍是普通 dict（JSON-safe），不泄漏 MappingProxyType
    payload = signal.to_dict()
    assert isinstance(payload["value"], dict)
    json.dumps(payload)  # 不得抛异常
    # 快照语义：构造后再改传入的源 dict 不得影响已冻结的投影
    source = {"streak": 3}
    snapshot = DecisionStateSignal(
        name="engagement_state",
        ref="user_state://engagement_state",
        value=source,
        ttl_seconds=60,
        epoch="user_state.v1.13",
    )
    source["streak"] = 777
    assert snapshot.value["streak"] == 3


def test_degraded_reasons_closed_vocabulary_and_readonly():
    """V3-FIX-09/F1：降级原因封闭词表；degraded_reasons 只读；未知原因码 validate 必报。"""
    assert frozenset({"governance_off", "governance_shadow", "unavailable"}) == DECISION_DEGRADED_REASONS

    ctx = DecisionContext(
        user_id=uuid4(),
        intent="chat",
        degraded_fields=("emotion_hint",),
        degraded_reasons={"emotion_hint": "governance_shadow"},
    )
    assert ctx.validate() == ()
    assert ctx.degraded_reasons["emotion_hint"] == "governance_shadow"
    with pytest.raises(TypeError):
        ctx.degraded_reasons["emotion_hint"] = "unavailable"  # type: ignore[index]
    # to_dict 流出普通 dict
    assert ctx.to_dict()["degraded_reasons"] == {"emotion_hint": "governance_shadow"}

    bad = DecisionContext(
        user_id=uuid4(),
        intent="chat",
        degraded_fields=("emotion_hint",),
        degraded_reasons={"emotion_hint": "mystery"},
    )
    assert any("degraded_reasons" in v for v in bad.validate())

    # 兼容面：不传 degraded_reasons 时默认空且 validate 通过（旧构造签名不变）
    legacy = DecisionContext(user_id=uuid4(), intent="chat")
    assert legacy.degraded_reasons == {}
    assert legacy.validate() == ()


def test_default_projection_is_json_safe_for_uuid_decimal():
    """V3-FIX-09/F6：默认投影把 UUID/Decimal 转 str，递归产物必须可 json.dumps。"""

    @dataclasses.dataclass
    class _ArbitraryState:
        raw_uuid: object
        raw_decimal: object
        nested: dict
        items: list

    payload_uuid = uuid4()
    payload_decimal = Decimal("3.14")
    state = _ArbitraryState(
        raw_uuid={"id": payload_uuid, "batch": [payload_uuid, Decimal("9.5")]},
        raw_decimal=payload_decimal,
        nested={"when": datetime(2026, 9, 19, 12, 0, 0)},
        items=(payload_uuid, payload_decimal),
    )

    projection = _default_signal_projection(state)
    serialized = json.dumps(projection)  # 不得抛异常（UUID/Decimal 穿透即炸）
    assert str(payload_uuid) in serialized
    assert "3.14" in serialized
    assert "9.5" in serialized

    # 非 dataclass 标量路径：包一层 {"value": ...} 且同样 JSON-safe
    scalar_projection = _default_signal_projection(Decimal("1.25"))
    assert scalar_projection == {"value": "1.25"}
    json.dumps(scalar_projection)


def test_omitted_counts_candidate_boundary_documented():
    """V3-FIX-09/F4：omitted_counts 候选集边界必须写入契约文档并钉住（防文档回退）。"""
    doc = DecisionContext.__doc__ or ""
    assert "omitted_counts" in doc
    assert "候选集" in doc
    assert "上游门控" in doc  # 明示：M-03 预筛/语义门控/多样性剔除不计入
    # 只读面保持（与 omitted_counts 契约一致）
    ctx = DecisionContext(user_id=uuid4(), intent="chat", omitted_counts={"goals": 2})
    with pytest.raises(TypeError):
        ctx.omitted_counts["goals"] = 0  # type: ignore[index]


def test_cache_key_components_are_deterministic():
    user_id = uuid4()
    signal = DecisionStateSignal(
        name="srl_phase",
        ref="user_state://srl_phase",
        value={},
        ttl_seconds=30,
        epoch="user_state.v1.13",
    )
    item = ContextItemDescriptor(
        ref="memory://goal/g1",
        type="goal",
        scope="user",
        why_included=("rank_policy",),
        epoch="e1",
    )

    def _build() -> DecisionContext:
        return DecisionContext(
            user_id=user_id,
            intent="chat",
            route_intent="chat",
            focus_mode=None,
            plan_id=None,
            query_text_hash="q1",
            signals=(signal,),
            items=(item,),
            omitted_counts={},
            degraded_fields=(),
            built_at=_utcnow(),
        )

    left, right = _build().cache_key_components(), _build().cache_key_components()
    assert left == right
    assert left["query_text_hash"] == "q1"
    assert "memory://goal/g1" in left["item_refs"]
    assert "user_state.v1.13" in left["epochs"]


def test_context_pack_backward_compatible_surface():
    """旧构造签名可用；decision_context 默认 None；prompt 面零变化。"""
    pack = ContextPack(
        user_id=uuid4(),
        intent="chat",
        preferences={"depth_preference": {"value": 0.5}},
        goals=[],
        episodic_memories=[],
        budgets={"preferences": 10, "goals": 10, "episodic": 10},
        token_usage={"preferences": 1, "goals": 0, "episodic": 0},
        budget_remaining={"preferences": 9, "goals": 10, "episodic": 10},
    )
    assert pack.decision_context is None

    prompt_context = pack.to_prompt_context()
    # prompt 面 key 集冻结：decision_context 不得进入 prompt（省 token，观测走对象/telemetry）
    assert set(prompt_context.keys()) == {
        "preferences",
        "active_goals",
        "episodic_memories",
        "past_session_memory",
        "context_pack",
    }
    assert set(prompt_context["context_pack"].keys()) == {
        "intent",
        "budgets",
        "token_usage",
        "budget_remaining",
        "pack_id",
        "metadata",
    }


# ---------------------------------------------------------------------------
# Part B — Builder 填充（sqlite）
# ---------------------------------------------------------------------------


async def _seed_user_with_memories(db_session) -> tuple:
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
        evidence_refs=[{"type": "event", "id": "evt_dc_1"}],
    )
    await memory_service.create_goal(
        user_id=user_id,
        title="Goal DC",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_dc_2"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="DC episodic memory",
        source_type="analysis",
        source_id="src_dc",
        occurred_at=_utcnow() - timedelta(hours=1),
        importance_score=0.6,
        tags=["execution"],
        evidence_refs=[{"type": "event", "id": "evt_dc_3"}],
    )
    return user_id


def _builder(db_session) -> ContextPackBuilder:
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 50}})
    return ContextPackBuilder(db_session, scheduler=scheduler)


@pytest.mark.asyncio
async def test_builder_populates_decision_context(db_session, monkeypatch):
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    pack = await _builder(db_session).build(user_id, intent="chat", query_text="帮我复习高数", route_intent="chat")

    decision = pack.decision_context
    assert decision is not None, "build() 必须默认填充 decision_context"
    assert decision.schema_version == DECISION_CONTEXT_SCHEMA_VERSION
    assert decision.intent == "chat"
    assert decision.route_intent == "chat"
    assert decision.user_id == user_id
    assert decision.query_text_hash is not None
    assert len(decision.query_text_hash) == 16
    assert decision.validate() == (), f"契约违规: {decision.validate()}"

    # items manifest 精确覆盖被注入的 section 内容（不多不少）
    pref_items = decision.items_of_type("preference")
    included_goal_ids = {item.ref.split("/")[-1] for item in decision.items_of_type("goal")}
    included_episodic_ids = {item.ref.split("/")[-1] for item in decision.items_of_type("episodic_memory")}
    assert len(pref_items) == len(pack.preferences)
    assert all(item.ref.startswith("memory://preference/") for item in pref_items)
    assert all(item.epoch is not None for item in pref_items)
    assert included_goal_ids == {payload["id"] for payload in pack.goals}
    assert included_episodic_ids == {payload["id"] for payload in pack.episodic_memories}

    for item in decision.items:
        assert item.ref.startswith("memory://")
        assert item.why_included, "why_included 不得为空"
        assert set(item.why_included) <= DECISION_INCLUDE_REASONS
        assert item.ttl_seconds is not None or item.epoch is not None
        assert item.version == DECISION_CONTEXT_SCHEMA_VERSION

    # 观测面：omitted_counts 覆盖三个 memory section
    assert set(decision.omitted_counts.keys()) >= {"preferences", "goals", "episodic"}

    # signals：UserStateV1 高信号投影，TTL 与聚合器权威 TTL 表一致
    assert {s.name for s in decision.signals} == set(DEFAULT_DECISION_SIGNAL_FIELDS)
    for signal in decision.signals:
        assert signal.ttl_seconds == StateAggregatorService.FIELD_TTLS_SECONDS[signal.name]
        assert signal.epoch == "user_state.v1.13"
        assert signal.ref == f"user_state://{signal.name}"
        assert signal.why_included == ("state_signal",)

    engagement = decision.signal("engagement_state")
    assert engagement is not None
    assert set(engagement.value.keys()) == {"last_active_at", "session_count_7d", "streak"}

    # C-01 R2-F2: 冻结其余两路信号的 value 形状（防静默漂移；三路必须同等钉死）
    emotion = decision.signal("emotion_hint")
    assert emotion is not None
    assert set(emotion.value.keys()) == {
        "dominant_sentiment",
        "sentiment_distribution",
        "emotional_block_detected",
    }
    srl = decision.signal("srl_phase")
    assert srl is not None
    assert set(srl.value.keys()) == {"current_phase", "phase_started_at", "confidence", "source"}


def _degraded_counter_value(reason: str) -> float:
    sample = REGISTRY.get_sample_value("sparkle_decision_context_signal_degraded_total", {"reason": reason})
    return float(sample or 0.0)


@pytest.mark.asyncio
async def test_builder_signals_degrade_gracefully(db_session, monkeypatch):
    """聚合器故障时 pack 必须照常构建：信号空 + degraded_fields 登记，不抛异常。"""
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    async def _explode(*args, **kwargs):
        raise RuntimeError("aggregator down")

    monkeypatch.setattr(StateAggregatorService, "get_user_state", _explode)

    unavailable_before = _degraded_counter_value("unavailable")
    pack = await _builder(db_session).build(user_id, intent="chat")
    assert pack.decision_context is not None
    assert pack.decision_context.signals == ()
    assert tuple(sorted(pack.decision_context.degraded_fields)) == tuple(sorted(DEFAULT_DECISION_SIGNAL_FIELDS))
    # V3-FIX-09/F1: 真降级（取数异常）必须编码为 unavailable，而非治理模式
    assert pack.decision_context.degraded_reasons == dict.fromkeys(DEFAULT_DECISION_SIGNAL_FIELDS, "unavailable")
    assert pack.decision_context.validate() == ()
    assert _degraded_counter_value("unavailable") == unavailable_before + len(DEFAULT_DECISION_SIGNAL_FIELDS)
    # items manifest 不受信号降级影响
    assert any(item.type == "preference" for item in pack.decision_context.items)


@pytest.mark.asyncio
async def test_builder_signals_governance_shadow_mode_observable(db_session, monkeypatch):
    """V3-FIX-09/F1：kill-switch=shadow 时信号缺失必须编码为 governance_shadow（不冒充数据降级），
    且降级可观测（结构化日志路径 + 降级计数器）。"""
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", "shadow", raising=False)
    # legacy bool 会把 fallback("off") 劫持回 live；显式关闭保证 shadow 解析的测试封闭性
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    shadow_before = _degraded_counter_value("governance_shadow")
    pack = await _builder(db_session).build(user_id, intent="chat")

    decision = pack.decision_context
    assert decision is not None
    assert decision.signals == ()
    assert tuple(sorted(decision.degraded_fields)) == tuple(sorted(DEFAULT_DECISION_SIGNAL_FIELDS))
    assert decision.degraded_reasons == dict.fromkeys(DEFAULT_DECISION_SIGNAL_FIELDS, "governance_shadow")
    assert decision.validate() == (), f"治理性降级不得产生契约违规: {decision.validate()}"
    # to_dict 面可观测（v2/落库路径安全）
    assert decision.to_dict()["degraded_reasons"] == dict.fromkeys(DEFAULT_DECISION_SIGNAL_FIELDS, "governance_shadow")
    # 降级计数器按原因码递增
    assert _degraded_counter_value("governance_shadow") == shadow_before + len(DEFAULT_DECISION_SIGNAL_FIELDS)
    # items manifest 与 pack 其余部分不受治理模式影响
    assert any(item.type == "preference" for item in decision.items)
    assert "depth_preference" in pack.preferences


@pytest.mark.asyncio
async def test_builder_signals_governance_off_mode_skips_fetch(db_session, monkeypatch):
    """V3-FIX-09/F1：kill-switch=off 时跳过取数（不做无效查询），原因编码为 governance_off。"""
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    monkeypatch.setattr(settings, "AURORA_STAGE18_AGGREGATOR_MODE", "off", raising=False)
    # legacy bool SPARKLE_AGGREGATOR_ENABLED=True 会把 "off" 配置劫持回 "live"
    # （resolve_settings_mode: configured==fallback 且 legacy 开启 → enabled_mode），必须一并关闭
    monkeypatch.setattr(settings, "SPARKLE_AGGREGATOR_ENABLED", False, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    fetch_calls: list[tuple] = []

    async def _must_not_fetch(*args, **kwargs):
        fetch_calls.append(args)
        raise AssertionError("aggregator kill-switch=off 时不得发起信号取数")

    monkeypatch.setattr(StateAggregatorService, "get_user_state", _must_not_fetch)

    off_before = _degraded_counter_value("governance_off")
    pack = await _builder(db_session).build(user_id, intent="chat")

    decision = pack.decision_context
    assert decision is not None
    assert decision.signals == ()
    assert fetch_calls == []
    assert decision.degraded_reasons == dict.fromkeys(DEFAULT_DECISION_SIGNAL_FIELDS, "governance_off")
    assert decision.validate() == ()
    assert _degraded_counter_value("governance_off") == off_before + len(DEFAULT_DECISION_SIGNAL_FIELDS)


@pytest.mark.asyncio
async def test_builder_decision_context_kill_switch(db_session, monkeypatch):
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    monkeypatch.setattr(settings, "ENABLE_DECISION_CONTEXT", False, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    pack = await _builder(db_session).build(user_id, intent="chat")
    assert pack.decision_context is None
    # 其余行为不受影响
    assert "depth_preference" in pack.preferences


@pytest.mark.asyncio
async def test_goal_item_scope_follows_plan_link(db_session, monkeypatch):
    """linked_plan_id 的 goal → scope=plan；无链接 → scope=user。"""
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    memory_service = MemoryService(db_session)
    plan_goal = await memory_service.create_goal(
        user_id=user_id,
        title="Plan linked goal",
        status="active",
        evidence_refs=[{"type": "event", "id": "evt_dc_plan"}],
    )
    # 直接把已注入 payload 标记为 plan 链接形态（复用 create_goal 后更新 linked_plan_id）
    from sqlalchemy import update

    from app.models.memory import MemoryGoal

    await db_session.execute(update(MemoryGoal).where(MemoryGoal.id == plan_goal.id).values(linked_plan_id=uuid4()))
    await db_session.commit()

    pack = await _builder(db_session).build(user_id, intent="chat")
    decision = pack.decision_context
    assert decision is not None

    goal_scopes = {item.ref: item.scope for item in decision.items_of_type("goal")}
    plan_linked_refs = {f"memory://goal/{payload['id']}" for payload in pack.goals if payload.get("linked_plan_id")}
    for ref, scope in goal_scopes.items():
        expected = "plan" if ref in plan_linked_refs else "user"
        assert scope == expected, f"{ref} scope 应为 {expected}"


@pytest.mark.asyncio
async def test_memory_governance_and_decision_context_coexist(db_session, monkeypatch):
    """decision_context 填充不得破坏既有治理行为（last_consumed_at 标记）。"""
    monkeypatch.setattr(cache_service, "redis", None, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_GOVERNANCE", True, raising=False)
    user_id = await _seed_user_with_memories(db_session)

    memory_service = MemoryService(db_session)
    pref = await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="curiosity_preference",
        pref_value={"value": 0.4},
        evidence_refs=[{"type": "event", "id": "evt_dc_gov"}],
    )

    pack = await _builder(db_session).build(user_id, intent="chat")
    assert pack.decision_context is not None

    refreshed = await db_session.get(MemoryPreference, pref.id)
    assert refreshed is not None
    assert refreshed.last_consumed_at is not None
