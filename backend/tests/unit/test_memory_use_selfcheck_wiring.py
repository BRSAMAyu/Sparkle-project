"""M-05 · Self-ReCheck 接线守卫（变异「去掉 final-gate」必红；C-02/C-03 W 系同型）。

三个输出装配面，每面 AST 钉 + 行为级守卫：

- **W-G1**（``context_pack.ContextPackBuilder.build``——主聊天链路的权威
  final-gate）：合法召回但「不该 surface」的记忆在 pack 字段（prompt 面）
  被拦下，但保留在 decision_context（内部决策面）与 metadata（ids/reasons
  only，无正文回灌）。变异：删 ``evaluate_memory_use_gate`` 调用 → 无关
  记忆正文进入 pack.episodic_memories → 红。
- **W-G2**（``context_builder._attach_stage34_memory_context``——主聊天
  payload 的 episodic 注入面，M-03 R1-F2 同位）：包内近重复 episodic 在
  payload["episodic_memories"]（prompts.format_user_context 渲染进系统
  prompt 的 section）被降档。变异：删调用 → 重复正文进入渲染 prompt → 红。
- **W-G3**（``context_manager._get_past_session_memory``——past-session
  记忆拉取面）：同型 final-gate。变异：删调用 → 近重复行进入返回列表 → 红。

kill-switch（settings.ENABLE_MEMORY_USE_SELFCHECK=False）→ 全部 passthrough
且不写 metadata（豁免面不是静默：默认开，关闭是显式运维动作）。
"""

from __future__ import annotations

import ast
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.context_builder import ContextBuilderMixin

BACKEND = Path(__file__).resolve().parents[2] / "app"

USER_UUID = uuid4()


# ---------------------------------------------------------------------------
# AST 钉法（C-02/C-03 同型：常量假守卫剪枝——删除与 if False: 禁用都必红）
# ---------------------------------------------------------------------------


def _live_call_names(func_node: ast.AST) -> set[str]:
    names: set[str] = set()

    def _is_constant_falsy(test: ast.AST) -> bool:
        return isinstance(test, ast.Constant) and not test.value

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
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == func_name:
            return _live_call_names(node)
    raise AssertionError(f"function {func_name!r} not found in {path}")


def test_wg1_ast_context_pack_build_wires_selfcheck_gate():
    """变异：删 context_pack.build 的 evaluate_memory_use_gate → 红。"""
    names = _called_names(BACKEND / "core" / "context_pack.py", "build")
    assert "evaluate_memory_use_gate" in names


def test_wg2_ast_stage34_wires_selfcheck_gate():
    names = _called_names(BACKEND / "orchestration" / "context_builder.py", "_attach_stage34_memory_context")
    assert "evaluate_memory_use_gate" in names


def test_wg3_ast_context_manager_wires_selfcheck_gate():
    names = _called_names(BACKEND / "core" / "context_manager.py", "_get_past_session_memory")
    assert "evaluate_memory_use_gate" in names


# ---------------------------------------------------------------------------
# W-G1 行为级：context_pack —— 无关记忆可召回但不进入输出（两档用途）
# ---------------------------------------------------------------------------


async def _create_user(db_session: AsyncSession):
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
    return user_id


def _episodic_row(user_id, summary: str, importance: float = 0.7) -> EpisodicMemory:
    from app.core.time_utils import utcnow

    return EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary=summary,
        source_type="chat_turn",
        source_lane="direct_capture",
        subject_type="self",
        occurred_at=utcnow() - timedelta(hours=1),
        importance_score=importance,
        evidence_refs=[{"type": "user_state", "id": "t"}],
    )


def _pack_harness_flags(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PERSONALIZED_RANKING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_FOCUSING", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_PACK_TELEMETRY", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_DECISION_CONTEXT", True, raising=False)


@pytest.mark.asyncio
async def test_wg1_irrelevant_memory_recalled_but_not_surfaced(db_session, monkeypatch):
    """红条件：无关 episodic 正文出现在 pack.episodic_memories（prompt 面）。
    绿形态：被降档进 metadata（ids/reasons）+ decision_context 保留（内部档）。"""
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    relevant = _episodic_row(user_id, "LINEAR-ALGEBRA-EXAM-REVIEW-NOTES")
    irrelevant = _episodic_row(user_id, "CAT-GROOMING-HOBBY-EVENT")

    async def _fake_list_recent_episodic(self, uid, limit=20, **kwargs):
        return [relevant, irrelevant]

    monkeypatch.setattr(MemoryService, "list_recent_episodic", _fake_list_recent_episodic)
    _pack_harness_flags(monkeypatch)

    decision_ctx_inputs: dict[str, list] = {}
    original_build_decision = ContextPackBuilder._build_decision_context

    async def spy_build_decision(self, **kwargs):
        decision_ctx_inputs["episodic"] = list(kwargs.get("trimmed_episodic") or [])
        return await original_build_decision(self, **kwargs)

    monkeypatch.setattr(ContextPackBuilder, "_build_decision_context", spy_build_decision)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text="linear algebra exam review")

    summaries = [m["summary"] for m in pack.episodic_memories]
    assert "LINEAR-ALGEBRA-EXAM-REVIEW-NOTES" in summaries, "relevant memory must still surface"
    assert "CAT-GROOMING-HOBBY-EVENT" not in summaries, "irrelevant memory surfaced into prompt face (gate removed?)"

    # 降档可观测：ids + 封闭 reason（无正文回灌）
    selfcheck = (pack.metadata or {}).get("memory_selfcheck")
    assert isinstance(selfcheck, dict), "selfcheck metadata missing"
    assert selfcheck["internal_only_count"] == 1
    assert selfcheck["reason_counts"] == {"selfcheck:irrelevant_to_query": 1}
    internal_ids = {entry["id"] for entry in selfcheck["internal_only"]}
    assert str(irrelevant.id) in internal_ids
    assert str(relevant.id) not in internal_ids

    # 两档用途：内部决策面保留全部召回（relevant + irrelevant 都进 decision_ctx）
    ctx_episodic_ids = {str(p.get("id")) for p in decision_ctx_inputs.get("episodic", [])}
    assert str(relevant.id) in ctx_episodic_ids, "internal-decision tier must retain recalled memory"
    assert str(irrelevant.id) in ctx_episodic_ids, "internal-decision tier must retain recalled memory"


@pytest.mark.asyncio
async def test_wg1_kill_switch_passthrough(db_session, monkeypatch):
    """ENABLE_MEMORY_USE_SELFCHECK=False → gate 不拦、无 metadata 键（显式豁免）。"""
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    irrelevant = _episodic_row(user_id, "CAT-GROOMING-HOBBY-EVENT")

    async def _fake_list_recent_episodic(self, uid, limit=20, **kwargs):
        return [irrelevant]

    monkeypatch.setattr(MemoryService, "list_recent_episodic", _fake_list_recent_episodic)
    _pack_harness_flags(monkeypatch)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text="linear algebra exam review")

    summaries = [m["summary"] for m in pack.episodic_memories]
    assert "CAT-GROOMING-HOBBY-EVENT" in summaries, "kill-switch must passthrough untouched"
    assert "memory_selfcheck" not in (pack.metadata or {})


@pytest.mark.asyncio
async def test_wg1_metadata_claims_do_not_resurrect_downgraded_content(db_session, monkeypatch):
    """metadata 经 to_prompt_context() 进入 prompt（context_pack.metadata 注入
    context_pack.metadata）——降档条目不得经 memory_claims/evidence_summary
    把正文带回 prompt。"""
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    relevant = _episodic_row(user_id, "LINEAR-ALGEBRA-EXAM-REVIEW-NOTES")
    irrelevant = _episodic_row(user_id, "CAT-GROOMING-HOBBY-EVENT")

    async def _fake_list_recent_episodic(self, uid, limit=20, **kwargs):
        return [relevant, irrelevant]

    monkeypatch.setattr(MemoryService, "list_recent_episodic", _fake_list_recent_episodic)
    _pack_harness_flags(monkeypatch)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text="linear algebra exam review")

    rendered = str(pack.to_prompt_context())
    assert (
        "CAT-GROOMING-HOBBY-EVENT" not in rendered
    ), "downgraded memory content resurrected into the prompt via metadata (claims/evidence_summary)"
    assert "LINEAR-ALGEBRA-EXAM-REVIEW-NOTES" in rendered


# ---------------------------------------------------------------------------
# W-G2 行为级：stage34 —— 近重复 episodic 不进渲染 prompt
# ---------------------------------------------------------------------------


class _Stage34Host(ContextBuilderMixin):
    def __init__(self):
        self.redis = None


@pytest.mark.asyncio
async def test_wg2_stage34_near_duplicate_not_in_payload(db_session, monkeypatch):
    from app.core.time_utils import utcnow
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    now = utcnow()

    first = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary="用户开始每天背五十个英语单词了",
        source_type="chat_turn",
        source_lane="direct_capture",
        subject_type="self",
        occurred_at=now - timedelta(hours=2),
        importance_score=0.8,
        evidence_refs=[],
    )
    dup = EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        summary="用户开始每天背五十个英语单词",
        source_type="chat_turn",
        source_lane="direct_capture",
        subject_type="self",
        occurred_at=now - timedelta(hours=1),
        importance_score=0.9,
        evidence_refs=[],
    )
    db_session.add_all([first, dup])
    await db_session.commit()

    async def _fake_list_recent_episodic(self, uid, limit=20, **kwargs):
        return [first, dup]

    monkeypatch.setattr(MemoryService, "list_recent_episodic", _fake_list_recent_episodic)

    host = _Stage34Host()
    payload = await host._attach_stage34_memory_context(
        {"cognitive_context": {}},
        user_id=str(user_id),
        db_session=db_session,
    )

    summaries = [m["summary"] for m in payload["episodic_memories"]]
    # importance 0.9 的 dup 排在前面（stage34 排序），first 成为其近重复 → first 降档
    assert summaries == ["用户开始每天背五十个英语单词"], f"near-duplicate surfaced into stage34 payload: {summaries}"

    from app.orchestration.prompts import format_user_context

    rendered = format_user_context({"episodic_memories": payload["episodic_memories"]})
    # 渲染器对每条记忆输出 content: 与 natural_line: 两行 → 1 条去重记忆 = 2 次；
    # 若 gate 被删（2 条近重复都进 payload）则为 4 次。
    assert (
        rendered.count("用户开始每天背五十个英语单词") == 2
    ), f"near-duplicate episodic rendered more than once into system prompt: {rendered.count('用户开始每天背五十个英语单词')}"

    note = payload.get("memory_selfcheck")
    assert isinstance(note, dict) and note.get("internal_only_count") == 1


# ---------------------------------------------------------------------------
# W-G3 行为级：context_manager —— past-session 记忆近重复去重
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wg3_past_session_memory_near_duplicate_cut(db_session, monkeypatch):
    from app.core.context_manager import ContextOrchestrator
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    from app.core.time_utils import utcnow

    now = utcnow()

    def _row(summary: str, importance: float) -> EpisodicMemory:
        return EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            summary=summary,
            source_type="chat_turn",
            source_lane="direct_capture",
            subject_type="self",
            occurred_at=now - timedelta(days=1),
            importance_score=importance,
            evidence_refs=[],
        )

    high = _row("用户通过了第一次模拟面试，表现不错", 0.9)
    dup = _row("用户通过了第一次模拟面试", 0.8)
    distinct = _row("用户加入了校篮球队", 0.7)

    async def _fake_get_recent_episodic(self, uid, limit=12, **kwargs):
        return [dup, distinct, high]  # 顺序无关：gate 按优先序（importance 排序后）判重复

    monkeypatch.setattr(MemoryService, "get_recent_episodic", _fake_get_recent_episodic)

    orchestrator = ContextOrchestrator(db_session, None)
    rows = await orchestrator._get_past_session_memory(user_id, db_session, limit=3)

    summaries = [m["summary"] for m in rows]
    assert "用户通过了第一次模拟面试，表现不错" in summaries, "higher-priority memory must survive"
    assert "用户加入了校篮球队" in summaries, "distinct memory must survive"
    assert "用户通过了第一次模拟面试" not in summaries, "near-duplicate past-session memory surfaced (gate removed?)"


# ---------------------------------------------------------------------------
# C-03 W-M 兼容：既有守卫在 M-05 gate 之下必须仍然绿（合法记忆不被误伤）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wg1_c03_wm_compatibility_legal_event_still_surfaces(db_session, monkeypatch):
    """C-03 test_wm_context_pack_never_ranks_or_embeds_illegal_memory 的合法
    条目（LEGAL-EVENT + query 'LEGAL-EVENT topic'）在 M-05 gate 下仍 surface
    （词法相关）——两卡接线叠加不回归。"""
    from app.services.memory_service import MemoryService

    user_id = await _create_user(db_session)
    legal_row = _episodic_row(user_id, "LEGAL-EVENT")

    async def _fake_list_recent_episodic(self, uid, limit=20, **kwargs):
        return [legal_row]

    monkeypatch.setattr(MemoryService, "list_recent_episodic", _fake_list_recent_episodic)
    _pack_harness_flags(monkeypatch)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 400}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text="LEGAL-EVENT topic")

    pack_summaries = [m["summary"] for m in pack.episodic_memories]
    assert "LEGAL-EVENT" in pack_summaries
