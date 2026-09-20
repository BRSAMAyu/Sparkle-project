"""C-02 · manifest 形状契约 + 接线钉住（R2 返修 P1-F1 / P1-F2）。

**F1 契约（C-01 式）**：pack 面与 orchestrator 面的 manifest 顶层 key 集与分节
key 集逐字钉死（``set(keys) == set(MANIFEST_*_KEYS)`` 精确相等，缺 key/多 key 必红）。
两面同 key 集（面间不适用值为 None），序列化唯一权威是
``assemble_manifest`` / ``normalize_section``。

**F2 接线钉住**：R2 变异实验 M3/M4/M4b/M5 证明三处安装面接线可整体删除而全部
测试仍绿——本文件为每处接线钉测试：
- W1（变异 M3）：context_pack.build 的 preference 折叠登记接线（行为级，sqlite）；
- W2（变异 M4/M4b）：_build_user_context 对 _attach_source_manifest 的调用（AST）；
- W3（变异 M5）：_build_full_context 的 grpc 覆盖检测 + history 附加接线（AST）；
- W4（R2-F5）：orchestrator process_stream / _attach_aurora_planning_sidecar 的
  post-manifest 登记（AST）+ pack build 对 _build_source_manifest 的调用（AST）。

AST 钉法与仓库治理守卫（scripts/guards 的 Rule AS attachment 扫描）同型，且对
**删除与常量假禁用（``if False:`` / ``if False and X:``）两种变异形态都必红**
（M5 的原变异是"禁用"而非删除——纯调用名存在性检查对禁用形态是盲的，故
``_live_call_names`` 把常量假守卫的 body 剪枝为不可达）。行为级测试（W1、真实
pack/sqlite）优先，AST 用于不可行为化的重宿主路径。
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.orchestration.context_sources import (
    KEY_CATEGORY_MAP,
    LATE_STAGE_WRITERS,
    MANIFEST_SECTION_KEYS,
    MANIFEST_TOP_LEVEL_KEYS,
    SOURCE_CATEGORIES,
    build_payload_source_manifest,
)
from app.services.memory_service import MemoryService

BACKEND = Path(__file__).resolve().parents[2] / "app"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# F1 — manifest 形状契约（两面 key 集逐字钉死）
# ---------------------------------------------------------------------------


def _payload_manifest() -> dict:
    return build_payload_source_manifest(
        {
            "user_context": {"nickname": "n"},
            "active_plans": [{"id": "p1"}],
            "episodic_memories": [{"id": "e1"}],
            "galaxy_snapshot": {"nodes": []},
            "recent_tool_usage": [{"tool": "x"}],
        },
        registration_source="email",
        conversation_stats={"messages": 2, "original_count": 5, "pruned_count": 2, "summary_used": True},
    )


async def _build_pack(db_session, monkeypatch) -> dict:
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False)
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
    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": 0.7},
        evidence_refs=[{"type": "event", "id": "evt_c1"}],
    )
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary="contract episodic",
        source_type="analysis",
        source_id="src_contract",
        occurred_at=_utcnow(),
        importance_score=0.7,
        tags=["c02"],
        evidence_refs=[{"type": "event", "id": "evt_c2"}],
    )
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 400}})
    pack = await ContextPackBuilder(db_session, scheduler=scheduler).build(user_id, intent="chat")
    return (pack.metadata or {})["sources"]


def test_manifest_top_level_keys_frozen_payload_face():
    manifest = _payload_manifest()
    assert set(manifest.keys()) == set(MANIFEST_TOP_LEVEL_KEYS)


@pytest.mark.asyncio
async def test_manifest_top_level_keys_frozen_pack_face(db_session, monkeypatch):
    sources = await _build_pack(db_session, monkeypatch)
    assert set(sources.keys()) == set(MANIFEST_TOP_LEVEL_KEYS)


def test_manifest_section_keys_frozen_payload_face():
    manifest = _payload_manifest()
    assert set(manifest["sections"].keys()) == set(SOURCE_CATEGORIES)
    for section in manifest["sections"].values():
        assert set(section.keys()) == set(MANIFEST_SECTION_KEYS)


@pytest.mark.asyncio
async def test_manifest_section_keys_frozen_pack_face(db_session, monkeypatch):
    sources = await _build_pack(db_session, monkeypatch)
    assert set(sources["sections"].keys()) == set(SOURCE_CATEGORIES)
    for section in sources["sections"].values():
        assert set(section.keys()) == set(MANIFEST_SECTION_KEYS)


def test_manifest_shape_identical_between_faces():
    """R2-F1 核心：两面的顶层/分节 key 集完全一致（同版本号同形状）。"""
    payload_manifest = _payload_manifest()
    assert set(payload_manifest.keys()) == set(MANIFEST_TOP_LEVEL_KEYS)
    # pack 面 key 集由上面两条 async 测试钉住；这里再证 payload 面 == 冻结常量，
    # 且冻结常量内容本身被钉死（防有人同时改常量与实现）：
    assert MANIFEST_TOP_LEVEL_KEYS == (
        "schema_version",
        "sections",
        "item_category_counts",
        "overrides",
        "unclassified",
        "user_is_seed_or_demo",
        "late_stage_writers",
        "control_keys",
        "seed_or_demo_items_total",
        "event_schema_version",
    )
    assert MANIFEST_SECTION_KEYS == (
        "category",
        "enabled",
        "adapter",
        "keys",
        "item_count",
        "token_estimate",
        "seed_or_demo",
        "seed_or_demo_items",
        "decision_items",
        "compaction",
        "note",
    )


# ---------------------------------------------------------------------------
# F9 / F8 — golden map（全表钉死，防部分键漂移）
# ---------------------------------------------------------------------------


def test_key_category_map_golden():
    """R2-F9：整表 golden 相等（此前仅 fixture 覆盖键被钉，~27/37）。"""
    assert dict(KEY_CATEGORY_MAP) == {
        "user_context": "state",
        "analytics_summary": "state",
        "preferences": "state",
        "preference_version": "state",
        "llm_profile": "state",
        "experiment_cohort": "state",
        "profile": "state",
        "profile_context": "state",
        "next_actions": "state",
        "active_plans": "state",
        "active_goals": "state",
        "focus_stats": "state",
        "task_status_summary": "state",
        "calendar_context": "state",
        "working_memory_snapshot": "state",
        "cognitive_context": "state",
        "self_model": "state",
        "scaffolding_fsm_snapshot": "state",
        "aurora_everyday_presence": "state",
        "plan_context": "state",
        "understanding_depth": "state",
        "episodic_memories": "memory",
        "experience_memories": "memory",  # WIRING-1（FIX-33）
        "past_session_memory": "memory",
        "last_session_mood": "memory",
        "cognitive_insights": "memory",
        "learning_gaps_summary": "memory",
        "preferred_tools": "memory",
        "seed_library": "knowledge",
        "galaxy_snapshot": "knowledge",
        "knowledge_context": "knowledge",
        "document_context": "knowledge",
        "recent_corrections": "events",
        "recent_tool_usage": "events",
        "returning_context": "events",
        "use_document_context": "control",
        "document_filter": "control",
        "selected_document_ids": "control",
        "effective_file_ids": "control",
        "conversation_settings": "control",
        "aurora_stage34_modes": "control",
        "aurora_stage39_modes": "control",
        "aurora_planning_sidecar": "control",
        "experience_memory_meta": "control",  # WIRING-1（FIX-33）
        "experience_memory_selfcheck": "control",  # WIRING-1（FIX-33）
    }


def test_late_stage_writers_golden():
    """R2-F8：静态写序表整表钉死（此前仅 2/7 键被钉）。"""
    assert dict(LATE_STAGE_WRITERS) == {
        "active_goals": ("stage34_memory",),
        "episodic_memories": ("stage34_memory",),
        "experience_memories": ("stage34_memory",),  # WIRING-1（FIX-33）
        "last_session_mood": ("stage34_memory",),
        "recent_corrections": ("stage34_memory",),
        "cognitive_context": ("stage34_memory", "stage39_scaffolding"),
        "galaxy_snapshot": ("stage39_scaffolding",),
        "scaffolding_fsm_snapshot": ("stage39_scaffolding",),
    }


# ---------------------------------------------------------------------------
# F2 — 接线钉住（变异 M3/M4/M4b/M5 必红）
# ---------------------------------------------------------------------------


def _is_constant_falsy(node: ast.AST) -> bool:
    """常量假判定：``if False:`` / ``if False and X:``（变异 M5 的"禁用"形态）。"""
    if isinstance(node, ast.Constant):
        return not bool(node.value)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
        return any(_is_constant_falsy(value) for value in node.values)
    return False


def _live_call_names(func_node: ast.AST) -> set[str]:
    """函数体内**可达**的调用名集合：常量假守卫的 body 剪枝为禁用接线。

    只剪枝（不会误杀活代码）：``if <常量假>:`` 的 body / ``while <常量假>:`` 的
    body；``else`` 分支仍然可达，照常遍历。settings 开关（``if settings.X:``）
    不是常量假——那是合法 kill-switch，不属"禁用"变异。
    """
    names: set[str] = set()

    def _visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_constant_falsy(node.test):
            for sub in node.orelse:
                _visit(sub)
            return
        if isinstance(node, ast.While) and _is_constant_falsy(node.test):
            return
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
        for child in ast.iter_child_nodes(node):
            _visit(child)

    _visit(func_node)
    return names


def _called_names(path: Path, func_name: str) -> set[str]:
    """AST：目标函数体内所有**未被禁用**的调用名集合（Rule AS 守卫同型手法 +
    常量假守卫剪枝——删除与禁用两种变异形态都必红）。"""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == func_name:
            return _live_call_names(node)
    raise AssertionError(f"function {func_name!r} not found in {path}")


@pytest.mark.asyncio
async def test_w1_pack_preference_collapse_registration_wired(db_session, monkeypatch):
    """变异 M3 反转：删 context_pack.build 的折叠登记接线（detect_preference_key_overrides
    调用）→ 同 key 双记录不再产生 overrides → 本测试红。真实 sqlite pack 路径。"""
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False)

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

    @dataclass
    class _StubPref:
        id: str
        pref_key: str
        pref_value: dict
        user_id: str  # M-03 user 维度 fail-closed：stub 必须带对 user_id 才能走到折叠面
        updated_at: datetime = field(default_factory=_utcnow)
        evidence_score: float = 0.5

    # id 用真 UUID：build() 的 _mark_consumed_memory_records 会拿 id 查
    # memory_preferences（GUID 绑定），非 UUID 字符串会炸（与真实记录形状一致）。
    stubs = [
        _StubPref(str(uuid4()), "depth_preference", {"value": 0.3}, str(user_id)),
        _StubPref(str(uuid4()), "depth_preference", {"value": 0.9}, str(user_id)),
    ]
    builder = ContextPackBuilder(
        db_session,
        scheduler=ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 50, "episodic": 400}}),
    )
    monkeypatch.setattr(builder.memory_service, "list_preference_records", lambda *_a, **_k: _async_return(stubs))

    pack = await builder.build(user_id, intent="chat")

    overrides = (pack.metadata or {})["sources"]["overrides"]
    assert overrides, "pack 折叠登记接线被删（变异 M3）：同 key 双记录的覆盖不再显式登记"
    assert overrides[0]["key"] == "depth_preference"
    assert overrides[0]["resolution"] == "last_write_wins_visible"
    # 值语义（真实代码 characterization，R2-F3）：折叠为单值（rank 重排决定胜者）；
    # 登记的 winner 必须与实际胜出值一致（detect 的 final_values 回溯契约）：
    final_value = pack.preferences["depth_preference"]
    assert final_value in ({"value": 0.3}, {"value": 0.9})
    winner_id = overrides[0]["new_writer"]
    winner_stub = next(s for s in stubs if s.id == winner_id)
    assert winner_stub.pref_value == final_value
    # 覆盖事实可见：全部参选记录都在 contenders 里（胜者可能是首记录——rank 重排），
    # 此时 previous_writer == new_writer，若无 contenders 该覆盖将不可见。
    assert set(overrides[0]["contenders"]) == {s.id for s in stubs}
    assert len(overrides[0]["contenders"]) == 2


async def _async_return(value):
    return value


def test_w1b_pack_build_calls_collapse_detector_and_manifest_builder():
    """M3/M4-pack 侧 AST 双保险：build() 必须调用折叠检测与 manifest 构建。"""
    names = _called_names(BACKEND / "core" / "context_pack.py", "build")
    assert "detect_preference_key_overrides" in names
    assert "_build_source_manifest" in names


def test_w2_build_user_context_awaits_source_manifest_attach():
    """变异 M4/M4b 反转：删 _build_user_context 里的 _attach_source_manifest 调用 → 红。"""
    names = _called_names(BACKEND / "orchestration" / "context_builder.py", "_build_user_context")
    assert "_attach_source_manifest" in names


def test_w3_build_full_context_wires_merge_detection_and_history_attach():
    """变异 M5 反转：禁用 grpc 覆盖检测 / history 附加接线 → 红。"""
    names = _called_names(BACKEND / "orchestration" / "context_builder.py", "_build_full_context")
    assert "detect_merge_overrides" in names
    assert "attach_conversation_history" in names


def test_w4_orchestrator_registers_post_manifest_writes():
    """R2-F5 接线钉住：process_stream 控制键后写与 sidecar 挂载后必须补登记。"""
    process_stream = _called_names(BACKEND / "orchestration" / "orchestrator.py", "process_stream")
    assert "register_post_manifest_writes" in process_stream

    sidecar = _called_names(BACKEND / "orchestration" / "orchestrator.py", "_attach_aurora_planning_sidecar")
    assert "register_post_manifest_writes" in sidecar
