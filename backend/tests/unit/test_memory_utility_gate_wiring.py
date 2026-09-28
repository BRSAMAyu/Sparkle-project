"""V4-I02 · utility gate 接线守卫 + context_pack 集成测试。

三面守卫（变异必红，C-03/test_context_hard_filter_wiring 同型）：
- AST 钉：``context_pack.build`` 必须调用 ``apply_history_utility_gate``、派生
  ``derive_current_type_anchors``（一审 R1 整改：集成面类型锚接线）且引用
  ``ENABLE_MEMORY_UTILITY_GATE`` 旗标（删除接线 / 删锚派生 / 摘旗标变异都红）；
- flag OFF（默认）：零行为变化——不产生 ``memory_utility_gate`` metadata，
  预筛后候选原样进 pack；
- flag ON 行为：验收①异类型失败不进 prompt（含一审探针同形态高相关 0.75/1.0
  回归）/ 验收②required-memory 全拒 bypass 不静默清空 / 验收③越权（wrong-user）
  条目不得复活（M-03 预筛在门上游）/ 无锚路径行为不变 + anchors_unavailable
  如实登记（不静默）。
"""

from __future__ import annotations

import ast
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.services.memory_service import MemoryService

BACKEND = Path(__file__).resolve().parents[2] / "app"
CONTEXT_PACK_PATH = BACKEND / "core" / "context_pack.py"


# ---------------------------------------------------------------------------
# AST 钉法（常量假守卫剪枝；删除与 `if False:` 禁用两种变异都必红）
# ---------------------------------------------------------------------------


def _live_call_and_flag_names(func_node: ast.AST) -> tuple[set[str], set[str]]:
    """收集存活（非常量假守卫剪枝）调用名与引用名。"""
    calls: set[str] = set()
    names: set[str] = set()

    def _is_constant_falsy(test: ast.AST) -> bool:
        return isinstance(test, ast.Constant) and not test.value

    def _visit(node: ast.AST) -> None:
        if isinstance(node, ast.If) and _is_constant_falsy(node.test):
            return
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                calls.add(func.attr)
            elif isinstance(func, ast.Name):
                calls.add(func.id)
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        for child in ast.iter_child_nodes(node):
            _visit(child)

    _visit(func_node)
    return calls, names


def _build_analysis() -> tuple[set[str], set[str]]:
    tree = ast.parse(CONTEXT_PACK_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "build":
            return _live_call_and_flag_names(node)
    raise AssertionError("context_pack.build not found")


def test_ast_build_wires_utility_gate():
    """变异：删 build 的 apply_history_utility_gate 调用 → 红。"""
    calls, _ = _build_analysis()
    assert "apply_history_utility_gate" in calls


def test_ast_build_derives_current_type_anchors():
    """变异（一审 R1 整改钉）：删 build 的 derive_current_type_anchors 派生与传参
    → 硬门集成面退化为恒不触发（CHALLENGE-1 复发）→ 红。"""
    calls, _ = _build_analysis()
    assert "derive_current_type_anchors" in calls


def test_ast_build_references_gate_flag():
    """变异：摘掉 ENABLE_MEMORY_UTILITY_GATE 旗标判断（无条件开门）→ 红。"""
    _, names = _build_analysis()
    assert "ENABLE_MEMORY_UTILITY_GATE" in names


# ---------------------------------------------------------------------------
# 集成（in-memory SQLite db_session；沿 test_context_pack 同款装配）
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _make_user(db_session) -> tuple[User, UUID]:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user, user_id


async def _add_episodic(
    db_session,
    *,
    user_id: UUID,
    summary: str,
    tag: str,
    hours_ago: float,
    due_hours_ago: float | None = None,
    resolved: bool = False,
) -> None:
    now = _utcnow()
    memory_service = MemoryService(db_session)
    await memory_service.create_episodic_memory(
        user_id=user_id,
        summary=summary,
        source_type="analysis",
        source_id=f"src_{uuid4().hex[:8]}",
        occurred_at=now - timedelta(hours=hours_ago),
        importance_score=0.5,
        tags=[f"task_type:{tag}"],
        evidence_refs=[{"type": "event", "id": f"evt_{uuid4().hex[:8]}"}],
        due_at=now - timedelta(hours=due_hours_ago) if due_hours_ago is not None else None,
        resolved_at=now - timedelta(hours=1) if resolved else None,
    )


@pytest.mark.asyncio
async def test_flag_off_default_keeps_v3_behavior(db_session, monkeypatch):
    """旗标默认关：零行为变化——无 gate metadata，预筛后候选原样进 pack。"""
    _, user_id = await _make_user(db_session)
    await _add_episodic(
        db_session,
        user_id=user_id,
        summary="单词背诵任务到期未完成，连续失败",
        tag="vocab_memorization",
        hours_ago=4,
        due_hours_ago=2,
    )
    # 隔离 M-05 selfcheck（独立下游词法门）：本文件只测效用门变量，selfcheck 行为归其自有测试。
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text="继续上次的数学练习")
    assert "memory_utility_gate" not in (pack.metadata or {})
    assert any("单词背诵" in str(entry.get("summary") or "") for entry in pack.episodic_memories)


@pytest.mark.asyncio
async def test_flag_on_suppresses_negative_transfer_keeps_good_recall(db_session, monkeypatch):
    """验收①+③：异类型失败不进 prompt；同题好经验有召回；wrong-user 不复活。"""
    _, user_id = await _make_user(db_session)
    other_id = uuid4()
    await _add_episodic(
        db_session,
        user_id=user_id,
        summary="上次数学练习用了错题本方法，效果不错",
        tag="math_practice",
        hours_ago=6,
    )
    await _add_episodic(
        db_session,
        user_id=user_id,
        summary="单词背诵任务到期未完成，连续失败",
        tag="vocab_memorization",
        hours_ago=4,
        due_hours_ago=2,
    )
    # 非法：wrong-user 行（越权）——M-03 预筛必须先砍，门不得复活。
    await _add_episodic(
        db_session,
        user_id=other_id,
        summary="他人用户的私有数学练习失败记录",
        tag="math_practice",
        hours_ago=1,
    )

    # 隔离 M-05 selfcheck（独立下游词法门）：本文件只测效用门变量，selfcheck 行为归其自有测试。
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    original_flag = settings.ENABLE_MEMORY_UTILITY_GATE
    try:
        settings.ENABLE_MEMORY_UTILITY_GATE = True
        pack = await builder.build(user_id, intent="chat", query_text="继续上次的数学练习")
    finally:
        settings.ENABLE_MEMORY_UTILITY_GATE = original_flag

    summaries = [str(entry.get("summary") or "") for entry in pack.episodic_memories]
    assert any("数学练习用了错题本方法" in summary for summary in summaries), summaries
    assert all("单词背诵" not in summary for summary in summaries), summaries
    assert all("他人用户" not in summary for summary in summaries), summaries
    gate_meta = (pack.metadata or {}).get("memory_utility_gate") or {}
    assert gate_meta.get("applied") is True
    assert gate_meta.get("passed") is True
    # 一审 R1 整改：集成面派生了当次类型锚（无 plan 时回退 route/intent 类别）
    # → 硬门已武装，异类型失败在此面走硬拒（不再退化为软路径低分拒）。
    assert gate_meta.get("current_type_anchors") == ["chat"]
    assert gate_meta.get("anchors_unavailable") is False
    assert any(
        decision.get("selected") and "confirmed_bonus" in decision.get("reasons", [])
        for decision in gate_meta.get("decisions", [])
    )
    # 异类型失败（vocab_memorization × chat 锚零交集）= FIX52 硬拒（验收①）。
    assert any(
        not decision.get("selected") and "negative_transfer_cross_type" in decision.get("reasons", [])
        for decision in gate_meta.get("decisions", [])
    )
    # prompt 面（to_prompt_context）同样不含被筛条目。
    prompt_context = pack.to_prompt_context()
    prompt_blob = str(prompt_context.get("episodic_memories"))
    assert "单词背诵" not in prompt_blob
    assert "他人用户" not in prompt_blob


@pytest.mark.asyncio
async def test_flag_on_required_memory_all_rejected_bypasses_without_silent_empty(db_session, monkeypatch):
    """验收②：required-memory 全拒不能过门——bypass 保召回 + miss 如实登记。"""
    _, user_id = await _make_user(db_session)
    # 唯一候选 = 异类型失败（对数学查询全拒）。
    await _add_episodic(
        db_session,
        user_id=user_id,
        summary="单词背诵任务到期未完成，连续失败",
        tag="vocab_memorization",
        hours_ago=4,
        due_hours_ago=2,
    )
    # 隔离 M-05 selfcheck（独立下游词法门）：本文件只测效用门变量，selfcheck 行为归其自有测试。
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    original_flag = settings.ENABLE_MEMORY_UTILITY_GATE
    try:
        settings.ENABLE_MEMORY_UTILITY_GATE = True
        pack = await builder.build(user_id, intent="chat", query_text="继续上次的数学练习，回顾上次错题")
    finally:
        settings.ENABLE_MEMORY_UTILITY_GATE = original_flag

    gate_meta = (pack.metadata or {}).get("memory_utility_gate") or {}
    assert gate_meta.get("passed") is False
    assert gate_meta.get("bypassed") is True
    assert gate_meta.get("verdict") == "required_memory_recall_miss_bypass"
    assert gate_meta.get("required_memory_recall") is False
    # bypass = 回退 V3 预筛后路径：候选保留（有召回），不是静默清空。
    assert any("单词背诵" in str(entry.get("summary") or "") for entry in pack.episodic_memories)


# ---------------------------------------------------------------------------
# 一审 R1 整改回归（review_r1.md CHALLENGE-1 探针同形态）
# ---------------------------------------------------------------------------

_PROBE_QUERY = "math exercise plan with word count and progress"  # 恰 8 个词法项


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("summary", "expected_relevance"),
    [
        # 内容覆盖 query 6/8 项 → relevance 0.75（一审探针 score=+0.04 档）。
        ("math exercise plan with word count all failed overdue", "relevance:0.75"),
        # 内容覆盖 query 8/8 项 → relevance 1.0（一审探针极端档 score=+0.2925）。
        ("math exercise plan with word count and progress failed overdue", "relevance:1.0"),
    ],
)
async def test_flag_on_high_relevance_cross_type_failure_hard_rejected_at_pack_surface(
    db_session, monkeypatch, summary, expected_relevance
):
    """一审探针回归（验收①集成面）：essay_writing 失败经验对 math 查询高词法相关
    （relevance 0.75 / 1.0 两档各跑一轮，软分均在阈上）→ 集成面必须被 FIX52 硬拒，
    reason=negative_transfer_cross_type 落 metadata，不进 pack/prompt。

    一审实测（整改前）：同形态在集成面 SELECTED——硬门因 current_type_anchors
    恒空而不可触发。本测变异（删锚派生/删传参）必红。
    """
    _, user_id = await _make_user(db_session)
    await _add_episodic(
        db_session,
        user_id=user_id,
        summary=summary,
        tag="essay_writing",
        hours_ago=4,
        due_hours_ago=2,
    )
    # 隔离 M-05 selfcheck（独立下游词法门）：本文件只测效用门变量，selfcheck 行为归其自有测试。
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    original_flag = settings.ENABLE_MEMORY_UTILITY_GATE
    try:
        settings.ENABLE_MEMORY_UTILITY_GATE = True
        pack = await builder.build(user_id, intent="chat", query_text=_PROBE_QUERY)
    finally:
        settings.ENABLE_MEMORY_UTILITY_GATE = original_flag

    summaries = [str(entry.get("summary") or "") for entry in pack.episodic_memories]
    assert all("overdue" not in summary for summary in summaries), summaries
    # prompt 面（to_prompt_context）同样不含被硬拒条目。
    prompt_blob = str(pack.to_prompt_context().get("episodic_memories"))
    assert "overdue" not in prompt_blob

    gate_meta = (pack.metadata or {}).get("memory_utility_gate") or {}
    assert gate_meta.get("applied") is True
    # 锚派生如实登记：集成面已武装（route/intent 类别回退），非静默空锚。
    assert gate_meta.get("current_type_anchors") == ["chat"]
    assert gate_meta.get("anchors_unavailable") is False
    assert gate_meta.get("passed") is True  # 非 required-memory 场景

    decisions = gate_meta.get("decisions", [])
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.get("selected") is False
    assert "negative_transfer_cross_type" in decision.get("reasons", []), decision
    # 探针关键前提：软分在阈上（整改前会入选），只有硬门拦得住。
    assert decision.get("score", 0.0) > 0.0, decision
    assert expected_relevance in decision.get("reasons", []), decision


@pytest.mark.asyncio
async def test_flag_on_without_type_anchors_keeps_soft_path_and_records_unavailable(db_session, monkeypatch):
    """无锚路径行为不变（整改前集成面原行为钉）：无任何结构化类型声明
    （route/intent/plan 全空）→ 锚为空 + metadata anchors_unavailable=True 如实
    登记（不静默）→ 硬门不触发，异类型失败走软路径低分拒（与整改前一致）。"""
    _, user_id = await _make_user(db_session)
    await _add_episodic(
        db_session,
        user_id=user_id,
        summary="单词背诵任务到期未完成，连续失败",
        tag="vocab_memorization",
        hours_ago=4,
        due_hours_ago=2,
    )
    # 隔离 M-05 selfcheck（独立下游词法门）：本文件只测效用门变量，selfcheck 行为归其自有测试。
    monkeypatch.setattr(settings, "ENABLE_MEMORY_USE_SELFCHECK", False, raising=False)
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 600}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    original_flag = settings.ENABLE_MEMORY_UTILITY_GATE
    try:
        settings.ENABLE_MEMORY_UTILITY_GATE = True
        # query 不含 required-memory marker（非召回场景，避开 bypass 分支）。
        pack = await builder.build(user_id, intent="", query_text="开始今天的数学练习")
    finally:
        settings.ENABLE_MEMORY_UTILITY_GATE = original_flag

    gate_meta = (pack.metadata or {}).get("memory_utility_gate") or {}
    assert gate_meta.get("applied") is True
    assert gate_meta.get("current_type_anchors") == []
    assert gate_meta.get("anchors_unavailable") is True
    decision = (gate_meta.get("decisions") or [{}])[0]
    assert decision.get("selected") is False
    assert "negative_transfer_cross_type" not in decision.get("reasons", [])
    assert "utility_low_score" in decision.get("reasons", [])
    # 软路径结果不变：低相关失败仍被压下、不进 pack（与整改前该面行为一致）。
    assert all("单词背诵" not in str(entry.get("summary") or "") for entry in pack.episodic_memories)
