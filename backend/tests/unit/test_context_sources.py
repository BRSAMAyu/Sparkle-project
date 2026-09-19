"""C-02 · State/Memory/Knowledge/Events 四分适配层 — 红绿测试（R2 返修版）。

红（真实代码 characterization，R2-F3 返修：调用产品代码而非测试体内手写 dict）：
- 真实 `_merge_user_contexts`：grpc 后写覆盖 local 值，函数自身零登记（检测层
  在调用方 `_build_full_context`，本测试锁定"合并函数本身仍是无痕值替换"的现状）。
- 真实 pack 非 resolver 折叠：见 test_context_pack_sources.py（sqlite，注入同 key
  双记录，断言后写值胜出 + 覆盖显式登记）。

绿（实现后）：
- SourceRegistry：跨类/同类同 key 覆盖显式登记 + 告警日志 + namespace 化 key；
- 封闭类别投影：C-01 冻结 item type → 四类 source category 全覆盖；
- 四类 adapter 独立 enable/disable + token/项数计量 + seed/demo 标记；
- Events adapter 走 D-01 词表（decision.recorded 为注册事件名）；
- Memory 预筛委托直调 M-03 真模块（permissions 经 build_retrieval_context 载入，
  委托异常不吞——R2-F4）；
- history 归 events 通道（含 compaction 边界），State 通道永不消费会话历史。

manifest 形状契约（R2-F1）与接线钉住（R2-F2）见 test_context_source_contract.py。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.config import settings


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Part 0 — RED characterization（真实代码路径，锁定现状语义）
# ---------------------------------------------------------------------------


class _MergeHost:
    """最小宿主：只混入 ContextBuilderMixin（_merge_user_contexts 不依赖 self 状态）。"""

    from app.orchestration.context_builder import ContextBuilderMixin


def test_red_real_merge_user_contexts_replaces_local_value():
    """真实 `_merge_user_contexts`：grpc 后写覆盖 local 值，函数自身零登记。

    这是 R2-M5 变异面的另一半：值替换语义由本测试锁定（兼容性语义），覆盖
    **检测**层在 `_build_full_context` 调用方（由 contract 文件的 wiring 测试钉住）。
    """
    host = _MergeHost()
    local = {"active_plans": [{"id": "plan-local"}], "focus_stats": {"minutes": 10}}
    grpc = {"active_plans": [{"id": "plan-gateway"}]}

    merged = _MergeHost.ContextBuilderMixin._merge_user_contexts(host, local, grpc)

    # 后写覆盖成立（真实代码现状，兼容语义保持）：
    assert merged["active_plans"] == [{"id": "plan-gateway"}]
    assert merged["focus_stats"] == {"minutes": 10}
    # 且合并函数本身不产出任何登记面（检测层在其调用方，分层事实）：
    assert "context_sources" not in merged
    assert not any(isinstance(value, dict) and "overrides" in value for value in merged.values())


# ---------------------------------------------------------------------------
# Part 1 — SourceRegistry：无静默覆盖保证
# ---------------------------------------------------------------------------

from app.orchestration.context_sources import (  # noqa: E402
    KEY_CATEGORY_MAP,
    SEED_REGISTRATION_SOURCES,
    SOURCE_CATEGORIES,
    SOURCE_CATEGORY_BY_ITEM_TYPE,
    SOURCE_SCHEMA_VERSION,
    EventSourceAdapter,
    KnowledgeSourceAdapter,
    MemorySourceAdapter,
    SourceRegistry,
    StateSourceAdapter,
    build_payload_source_manifest,
    detect_merge_overrides,
    detect_preference_key_overrides,
    event_name_for_decision_record,
    item_source_category,
    memory_record_is_seed,
    user_is_seed_or_demo,
)


def test_registry_detects_cross_category_same_key_overrides():
    """四类同名 key：登记 3 次覆盖，namespaced key 全部保留，无静默丢弃。"""
    registry = SourceRegistry()
    registry.register("state", "X", writer="base", item_count=1, payload={"v": 1})
    registry.register("memory", "X", writer="stage34", item_count=2, payload={"v": 2})
    registry.register("knowledge", "X", writer="galaxy", item_count=1, payload={"v": 3})
    registry.register("events", "X", writer="decision_records", item_count=1, payload={"v": 4})

    manifest = registry.manifest()
    overrides = manifest.overrides
    # state 之后每类写同名 key 都构成一次覆盖登记：
    assert len(overrides) == 3
    assert {(o.previous_category, o.new_category) for o in overrides} == {
        ("state", "memory"),
        ("memory", "knowledge"),
        ("knowledge", "events"),
    }
    # namespaced key 四类共存（消费方可按类别取数，互不覆盖）：
    namespaced = {registry.namespaced_key(o.new_category, "X") for o in overrides}
    namespaced.add(registry.namespaced_key("state", "X"))
    assert len(namespaced) == 4


def test_registry_warns_on_override():
    from loguru import logger

    captured: list[str] = []
    sink_id = logger.add(lambda msg: captured.append(str(msg)), level="WARNING", format="{message}")
    try:
        registry = SourceRegistry()
        registry.register("state", "preferences", writer="base", item_count=1)
        registry.register("memory", "preferences", writer="pack", item_count=1)
    finally:
        logger.remove(sink_id)
    assert any("context source override" in line for line in captured)


def test_registry_manifest_counts_and_tokens():
    registry = SourceRegistry(estimate_tokens_fn=lambda text: len(str(text)) // 4)
    registry.register("state", "active_plans", writer="base", item_count=3, payload={"plans": [1, 2, 3]})
    registry.register("memory", "episodic_memories", writer="stage34", item_count=5, payload={"m": "x" * 40})
    manifest = registry.manifest()
    assert manifest.sections["state"].item_count == 3
    assert manifest.sections["memory"].item_count == 5
    assert manifest.sections["memory"].token_estimate == len(json.dumps({"m": "x" * 40})) // 4
    assert manifest.sections["knowledge"].items == ()
    assert manifest.to_dict()["schema_version"] == SOURCE_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Part 2 — 封闭类别投影（C-01 冻结词表 → 四类）
# ---------------------------------------------------------------------------


def test_every_decision_item_type_maps_to_a_category():
    from app.core.decision_context import DECISION_ITEM_TYPES

    assert set(SOURCE_CATEGORY_BY_ITEM_TYPE) == set(DECISION_ITEM_TYPES)
    for item_type, category in SOURCE_CATEGORY_BY_ITEM_TYPE.items():
        assert item_source_category(item_type) == category
        assert category in SOURCE_CATEGORIES


def test_item_source_category_rejects_unknown_type():
    with pytest.raises(KeyError):
        item_source_category("definitely_not_a_type")


def test_goal_maps_to_state_per_user_world_model():
    """USER_WORLD_MODEL §1：Goal/Milestone/Action/Schedule 属 Current State。"""
    assert item_source_category("goal") == "state"
    assert item_source_category("plan") == "state"
    assert item_source_category("user_state_signal") == "state"
    assert item_source_category("preference") == "memory"
    assert item_source_category("episodic_memory") == "memory"
    assert item_source_category("document_chunk") == "knowledge"


# ---------------------------------------------------------------------------
# Part 3 — seed/demo 标记（与 registration_source 口径对齐）
# ---------------------------------------------------------------------------


def test_user_is_seed_or_demo_follows_registration_source():
    assert user_is_seed_or_demo("seed") is True
    assert user_is_seed_or_demo("system") is True
    assert user_is_seed_or_demo("guest") is True
    assert user_is_seed_or_demo("email") is False
    assert user_is_seed_or_demo(None) is False
    assert frozenset({"seed", "system", "guest"}) == SEED_REGISTRATION_SOURCES


def test_memory_record_is_seed_detects_startup_seed():

    @dataclass
    class _Mem:
        source_type: str = "conversation"

    assert memory_record_is_seed(_Mem(source_type="startup_seed")) is True
    assert memory_record_is_seed(_Mem(source_type="conversation")) is False


# ---------------------------------------------------------------------------
# Part 4 — payload manifest 纯函数（orchestrator 侧分类面）
# ---------------------------------------------------------------------------


def _fixture_payload() -> dict:
    return {
        "user_context": {"nickname": "n"},
        "analytics_summary": {"is_active": True},
        "preferences": {"depth_preference": 0.5},
        "next_actions": [{"id": "t1"}],
        "active_plans": [{"id": "p1"}],
        "focus_stats": {"minutes": 10},
        "task_status_summary": {"pending": 2},
        "profile": {"identity": {}},
        "calendar_context": {"today": []},
        "working_memory_snapshot": {"items": [1, 2]},
        "cognitive_context": {"has": True},
        "self_model": {"confidence": 0.7},
        "active_goals": [{"id": "g1"}],
        "episodic_memories": [{"id": "e1"}],
        "last_session_mood": {"mood": "good"},
        "recent_corrections": [{"id": "c1"}],
        "past_session_memory": [{"id": "pm1"}],
        "cognitive_insights": {"has_cognitive_patterns": True},
        "learning_gaps_summary": "gaps",
        "seed_library": {"has_seed_library": True, "example_count": 3},
        "galaxy_snapshot": {"nodes": [1, 2]},
        "recent_tool_usage": [{"tool": "x"}],
        "returning_context": {"resume_tier": "light_resume"},
        "aurora_stage34_modes": {"mode": "shadow"},
        "scaffolding_fsm_snapshot": {"stage": "flow"},
        "use_document_context": True,
        "document_filter": ["f1"],
    }


def test_payload_manifest_categories_and_metering():
    manifest = build_payload_source_manifest(_fixture_payload(), registration_source="email")
    sections = manifest["sections"]

    for category in SOURCE_CATEGORIES:
        assert category in sections
        assert sections[category]["enabled"] is True
        assert sections[category]["item_count"] > 0 or category == "events"

    assert "active_plans" in sections["state"]["keys"]
    assert "working_memory_snapshot" in sections["state"]["keys"]
    assert "episodic_memories" in sections["memory"]["keys"]
    assert "past_session_memory" in sections["memory"]["keys"]
    assert "cognitive_insights" in sections["memory"]["keys"]
    assert "seed_library" in sections["knowledge"]["keys"]
    assert "galaxy_snapshot" in sections["knowledge"]["keys"]
    assert "recent_tool_usage" in sections["events"]["keys"]
    assert "returning_context" in sections["events"]["keys"]

    for category in SOURCE_CATEGORIES:
        section = sections[category]
        assert section["token_estimate"] >= 0
        assert "seed_or_demo" in section

    # 请求参数/开关属控制面，不混入四类（control_keys 显式可见）：
    assert "use_document_context" not in sections["state"]["keys"]
    assert "use_document_context" not in sections["memory"]["keys"]
    assert "use_document_context" in manifest["control_keys"]
    assert manifest["unclassified"] == []


def test_payload_manifest_flags_seed_demo():
    manifest = build_payload_source_manifest(_fixture_payload(), registration_source="seed")
    assert manifest["user_is_seed_or_demo"] is True

    manifest_email = build_payload_source_manifest(_fixture_payload(), registration_source="email")
    assert manifest_email["user_is_seed_or_demo"] is False
    # 种子库 few-shot 内容本身按 seed/demo 标记（消费方可过滤）：
    knowledge = manifest_email["sections"]["knowledge"]
    seed_keys = [item["key"] for item in knowledge["seed_or_demo_items"]]
    assert "seed_library" in seed_keys


def test_payload_manifest_unknown_keys_do_not_silently_land():
    payload = _fixture_payload()
    payload["mystery_key"] = {"data": 1}
    manifest = build_payload_source_manifest(payload)
    assert "mystery_key" in manifest["unclassified"]


def test_payload_manifest_records_stage_overrides():
    """stage34/39 后写覆盖 base 同名 key 时，manifest 显式登记（不静默）。"""
    payload = _fixture_payload()
    payload["preferences"] = {"depth_preference": 0.9, "curiosity_preference": 0.8}
    manifest = build_payload_source_manifest(payload)
    assert isinstance(manifest["overrides"], list)
    # 静态写序事实：stage34/39 晚于 base 写的 key 全部带 writer 溯源：
    late = manifest["late_stage_writers"]
    assert "active_goals" in late and "stage34_memory" in late["active_goals"]
    assert "cognitive_context" in late and "stage39_scaffolding" in late["cognitive_context"]


def test_payload_manifest_disabled_category(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_SOURCE_MEMORY", False)
    payload = _fixture_payload()
    manifest = build_payload_source_manifest(payload)
    assert manifest["sections"]["memory"]["enabled"] is False
    assert manifest["sections"]["memory"]["keys"] == []
    assert manifest["sections"]["memory"]["token_estimate"] == 0


def test_payload_manifest_item_category_counts_not_applicable():
    """R2-F1：orchestrator 面不产 decision items——key 恒在，值为 None（不误导为 0）。"""
    manifest = build_payload_source_manifest(_fixture_payload())
    assert manifest["item_category_counts"] is None
    for section in manifest["sections"].values():
        assert section["decision_items"] is None


# ---------------------------------------------------------------------------
# Part 5 — 四类 adapter：独立开关 + 计量
# ---------------------------------------------------------------------------


def test_adapter_switches_default_on_and_independent(monkeypatch):
    assert StateSourceAdapter().enabled is True
    assert MemorySourceAdapter().enabled is True
    assert KnowledgeSourceAdapter().enabled is True
    assert EventSourceAdapter().enabled is True

    monkeypatch.setattr(settings, "ENABLE_CONTEXT_SOURCE_STATE", False)
    assert StateSourceAdapter().enabled is False
    assert MemorySourceAdapter().enabled is True  # 独立


# ---------------------------------------------------------------------------
# Part 6 — Events adapter 走 D-01 词表
# ---------------------------------------------------------------------------


@dataclass
class _DecisionRecord:
    id: str
    module: str
    action: str
    outcome: str
    created_at: datetime = field(default_factory=_utcnow)


def test_event_name_for_decision_record_is_registered():
    from app.core.event_registry import REGISTERED_EVENT_NAMES, classify_stage

    name = event_name_for_decision_record(_DecisionRecord(id="1", module="ai", action="a", outcome="o"))
    assert name in REGISTERED_EVENT_NAMES
    assert name == "decision.recorded"
    assert classify_stage(name).value == "decision"


def test_event_source_adapter_meters_decision_records(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_SOURCE_EVENTS", True)
    adapter = EventSourceAdapter(estimate_tokens_fn=lambda text: 4)
    records = [
        _DecisionRecord(id="1", module="ai", action="tone_adjust", outcome="ok"),
        _DecisionRecord(id="2", module="push", action="schedule", outcome="ok"),
    ]
    section = adapter.classify_records(records)
    assert section.category == "events"
    assert section.enabled is True
    assert section.item_count == 2
    assert all(item.event_name == "decision.recorded" for item in section.items)
    assert section.token_estimate > 0

    disabled = EventSourceAdapter(enabled=False)
    assert disabled.classify_records(records).items == ()


# ---------------------------------------------------------------------------
# Part 7 — Memory 预筛委托：直调 M-03 真模块（R2-F4）
# ---------------------------------------------------------------------------

import app.orchestration.context_sources as context_sources_module  # noqa: E402


def test_no_dual_name_dead_code_left_behind():
    """R2-F4：本地 apply_memory_prefilter / PrefilterOutcome 双义名死代码已删。"""
    assert not hasattr(context_sources_module, "apply_memory_prefilter")
    assert not hasattr(context_sources_module, "PrefilterOutcome")


@pytest.mark.asyncio
async def test_prefilter_delegate_end_to_end_with_real_module(db_session):
    """R2 delta 复核点：委托在主仓真模块下 end-to-end 生效（wrong-user fail-closed）。"""
    from app.models.user import User
    from app.services.memory_service import MemoryService

    user_id = uuid4()
    other_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"u_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="t",
        )
    )
    db_session.add(
        User(
            id=other_id,
            username=f"u_{other_id.hex[:8]}",
            email=f"{other_id.hex[:8]}@example.com",
            hashed_password="t",
        )
    )
    await db_session.commit()

    memory_service = MemoryService(db_session)
    own = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="own memory",
        source_type="analysis",
        source_id="src_c02_own",
        occurred_at=_utcnow(),
        importance_score=0.7,
        tags=["c02"],
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    foreign = await memory_service.create_episodic_memory(
        user_id=other_id,
        summary="someone else memory",
        source_type="analysis",
        source_id="src_c02_other",
        occurred_at=_utcnow(),
        importance_score=0.9,
        tags=["c02"],
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )

    allowed, metric = await context_sources_module.prefilter_memory_candidates_for_llm_context(
        db_session,
        [own, foreign],
        user_id=str(user_id),
    )
    assert [str(record.id) for record in allowed] == [str(own.id)]
    # M-03 metric payload 原样透传（差异信号保留，R2-F4）：
    assert metric["version"] == "memory-v3.m03.v1"
    assert metric["input_count"] == 2
    assert metric["allowed_count"] == 1
    assert metric["dimension_counts"].get("user", 0) == 1


@pytest.mark.asyncio
async def test_prefilter_delegate_respects_user_permissions(db_session):
    """R2-F4：permissions 经 build_retrieval_context 载入——allow_episodic=False 生效。"""
    from app.models.user import User
    from app.models.user_memory_settings import UserMemorySettings
    from app.services.memory_service import MemoryService

    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"u_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="t",
        )
    )
    await db_session.commit()

    # 先写记忆（此时 allow_episodic 默认 True，M-02 存储闸放行），再落隐私设置行
    # ——被测对象是**读侧**预筛的 permissions 维度，不是 M-02 写侧闸。
    memory_service = MemoryService(db_session)
    own = await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="blocked by settings",
        source_type="analysis",
        source_id="src_c02_perm",
        occurred_at=_utcnow(),
        importance_score=0.7,
        tags=["c02"],
        evidence_refs=[{"type": "event", "id": "evt_3"}],
    )
    db_session.add(UserMemorySettings(user_id=user_id, allow_episodic=False))
    await db_session.commit()

    allowed, metric = await context_sources_module.prefilter_memory_candidates_for_llm_context(
        db_session,
        [own],
        user_id=str(user_id),
    )
    assert allowed == []
    assert metric["dimension_counts"].get("purpose", 0) == 1


@pytest.mark.asyncio
async def test_prefilter_delegate_does_not_swallow_delegation_errors(monkeypatch):
    """R2-F4：委托异常向上抛（无静默透传——接口漂移必须以失败可见）。"""

    def _broken(candidates, ctx):
        raise RuntimeError("simulated interface drift")

    monkeypatch.setattr(context_sources_module, "prefilter_candidates", _broken)

    class _NullSession:
        pass

    with pytest.raises(RuntimeError, match="simulated interface drift"):
        await context_sources_module.prefilter_memory_candidates_for_llm_context(
            _NullSession(), [{"id": "m1"}], user_id="u1"
        )


def test_memory_source_adapter_classifies_and_flags_seed():
    adapter = MemorySourceAdapter(estimate_tokens_fn=lambda text: 4)

    @dataclass
    class _Episodic:
        id: str
        summary: str
        source_type: str = "conversation"

    rows = [_Episodic("e1", "real memory"), _Episodic("e2", "seeded memory", source_type="startup_seed")]
    section = adapter.classify_episodic(rows)
    assert section.category == "memory"
    assert section.item_count == 2
    assert section.seed_or_demo_count == 1
    assert section.items[1].is_seed_or_demo is True


# ---------------------------------------------------------------------------
# Part 8 — history 语义：归 events 通道 + compaction 边界，不替代 state
# ---------------------------------------------------------------------------


def test_history_stats_land_in_events_channel_with_compaction_boundary():
    payload = _fixture_payload()
    conversation_stats = {
        "messages": 8,
        "original_count": 30,
        "pruned_count": 8,
        "summary_used": True,
        "recent_window": 4,
    }
    manifest = build_payload_source_manifest(payload, conversation_stats=conversation_stats)
    events = manifest["sections"]["events"]
    assert "conversation_history" in events["keys"]
    assert events["compaction"] == {
        "original_count": 30,
        "pruned_count": 8,
        "summary_used": True,
        "recent_window": 4,
    }
    # 铁律：历史不进 state 通道（state 只来自 UserStateV1/计划/任务投影）：
    assert "conversation_history" not in manifest["sections"]["state"]["keys"]


def test_state_source_adapter_never_consumes_history():
    adapter = StateSourceAdapter(estimate_tokens_fn=lambda text: 4)
    section = adapter.classify_state_payload(
        {
            "active_plans": [{"id": "p1"}],
            "conversation_history": [{"role": "user", "content": "hi"}],  # 不属于 state
        }
    )
    assert "conversation_history" not in section.keys
    assert "active_plans" in section.keys


def test_conversation_stats_without_compaction_fields():
    manifest = build_payload_source_manifest(_fixture_payload(), conversation_stats={"messages": 3})
    assert manifest["sections"]["events"]["compaction"]["summary_used"] is False


# ---------------------------------------------------------------------------
# Part 9 — 覆盖检测辅助（merge 面 / preference 折叠面）
# ---------------------------------------------------------------------------


def test_detect_merge_overrides_flags_grpc_overwrite():
    local = {"active_plans": ["A"], "focus_stats": {"m": 1}, "preferences": {"d": 0.5}}
    merged = {"active_plans": ["B"], "focus_stats": {"m": 1}, "preferences": {"d": 0.5}}
    overrides = detect_merge_overrides(local, merged, keys=("active_plans", "focus_stats", "preferences"))
    assert len(overrides) == 1
    assert overrides[0].key == "active_plans"
    assert overrides[0].previous_writer == "local_context"
    assert overrides[0].new_writer == "grpc_context"


def test_detect_preference_key_overrides_records_both_records():

    @dataclass
    class _Pref:
        id: str
        pref_key: str
        pref_value: dict
        updated_at: datetime = field(default_factory=_utcnow)

    records = [
        _Pref("r1", "depth_preference", {"value": 0.3}),
        _Pref("r2", "depth_preference", {"value": 0.9}),
    ]
    overrides = detect_preference_key_overrides(records)
    assert len(overrides) == 1
    assert overrides[0].key == "depth_preference"
    # 折叠语义保持兼容（后写胜出），但覆盖被显式登记：
    assert overrides[0].resolution == "last_write_wins_visible"


def test_key_category_map_covers_all_source_categories_and_documents_control_plane():
    categories_in_map = set(KEY_CATEGORY_MAP.values())
    assert categories_in_map <= set(SOURCE_CATEGORIES) | {"control"}
    for category in SOURCE_CATEGORIES:
        assert category in categories_in_map, f"KEY_CATEGORY_MAP missing category {category}"
    assert KEY_CATEGORY_MAP["use_document_context"] == "control"
    assert KEY_CATEGORY_MAP["aurora_planning_sidecar"] == "control"  # R2-F5


# ---------------------------------------------------------------------------
# Part 10 — manifest 后置附加 helper（orchestrator 宿主路径使用）
# ---------------------------------------------------------------------------

from app.orchestration.context_sources import (  # noqa: E402
    attach_conversation_history,
    attach_overrides,
    register_post_manifest_writes,
)


def test_attach_conversation_history_updates_events_channel_only():
    manifest = build_payload_source_manifest(_fixture_payload())
    before_state = dict(manifest["sections"]["state"])
    updated = attach_conversation_history(
        manifest,
        {"messages": 6, "original_count": 40, "pruned_count": 6, "summary_used": True, "recent_window": 4},
    )
    events = updated["sections"]["events"]
    assert "conversation_history" in events["keys"]
    assert events["compaction"]["original_count"] == 40
    assert events["compaction"]["summary_used"] is True
    # state 通道不受历史附加影响（history 不替代 state）：
    assert updated["sections"]["state"] == before_state
    # copy-on-write：原 manifest 不被原地污染：
    assert "conversation_history" not in manifest["sections"]["events"]["keys"]


def test_attach_overrides_merges_into_manifest():
    from app.orchestration.context_sources import SourceOverride

    manifest = build_payload_source_manifest(_fixture_payload())
    overrides = [
        SourceOverride(
            key="active_plans",
            previous_category="state",
            previous_writer="local_context",
            new_category="state",
            new_writer="grpc_context",
            resolution="grpc_overrode_local",
        )
    ]
    updated = attach_overrides(manifest, overrides)
    assert updated["overrides"][-1]["key"] == "active_plans"
    assert manifest["overrides"] == []  # copy-on-write


def test_register_post_manifest_writes_control_and_unclassified():
    """R2-F5：manifest 附加后的后写 key 进 control_keys / unclassified（盲区闭合）。"""
    payload = {"active_plans": [{"id": "p1"}], "context_sources": build_payload_source_manifest({"active_plans": []})}
    payload["use_document_context"] = True
    payload["brand_new_late_key"] = {"x": 1}

    register_post_manifest_writes(payload, ("use_document_context", "brand_new_late_key"))

    manifest = payload["context_sources"]
    assert "use_document_context" in manifest["control_keys"]
    assert "brand_new_late_key" in manifest["unclassified"]


def test_register_post_manifest_writes_idempotent_and_missing_manifest():
    payload = {"context_sources": build_payload_source_manifest({})}
    payload["use_document_context"] = True
    register_post_manifest_writes(payload, ("use_document_context",))
    first = list(payload["context_sources"]["control_keys"])
    register_post_manifest_writes(payload, ("use_document_context",))
    assert payload["context_sources"]["control_keys"] == first  # 幂等

    bare = {"use_document_context": True}  # manifest 缺失（降级路径）→ 静默跳过
    register_post_manifest_writes(bare, ("use_document_context",))
    assert "context_sources" not in bare


# ---------------------------------------------------------------------------
# Part 11 — orchestrator 宿主方法（降级路径不阻断装配）
# ---------------------------------------------------------------------------


class _FailingSession:
    async def execute(self, *_args, **_kwargs):
        raise RuntimeError("db unavailable")


class _ManifestHost:
    """最小宿主：只混入 ContextBuilderMixin 供 _attach_source_manifest 调用。"""

    from app.orchestration.context_builder import ContextBuilderMixin  # noqa: F401

    def __init__(self):
        pass


@pytest.mark.asyncio
async def test_attach_source_manifest_degrades_without_db():
    host = _ManifestHost()
    payload = _fixture_payload()
    result = await host.ContextBuilderMixin._attach_source_manifest(
        host, payload, user_id="00000000-0000-0000-0000-000000000001", db_session=_FailingSession()
    )
    manifest = result["context_sources"]
    for category in SOURCE_CATEGORIES:
        assert category in manifest["sections"]
    assert manifest["user_is_seed_or_demo"] is False  # registration_source 降级为 None
    # 装配值零改动（manifest 只加 metadata 面）：
    assert result["active_plans"] == payload["active_plans"]
    assert result["episodic_memories"] == payload["episodic_memories"]
