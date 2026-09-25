"""C-05 · Conflict Resolver 注入 Context 与 Clarification — 测试。

三面：
1. 纯函数面（conflict_resolution_context）：归因短语封闭词表、materiality
   规则、确定性澄清问句、One Best Question 选择、payload 形状与有界性；
2. 注入面（ContextPack）：冲突真实注入 + winner/loser 语义不稀释 +
   resolution refs（变异「拔注入→必红」的对立面即本文件的绿态断言）；
3. 消费面（SufficiencyChecker）：只对 material 冲突提问、缺省参数零行为
   变化、confirmation 流不被改写、澄清环路守卫仍然生效。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.aurora_stage20 import UnresolvedConflict
from app.models.user import User
from app.orchestration.sufficiency_checker import SufficiencyChecker, SufficiencyStatus
from app.services.conflict_resolution_context import (
    CLARIFICATION_CATEGORY_STEMS,
    CONFLICT_RESOLUTION_CONTEXT_VERSION,
    DIGEST_MAX_CHARS,
    PROMPT_NOTE_MAX_RESOLVED,
    RESOLUTION_REASON_PHRASES,
    build_clarification_question,
    build_conflict_resolution_context,
    build_record_index,
    digest_text,
    select_material_clarification,
    serialize_unresolved_for_context,
    to_prompt_payload,
)
from app.services.conflict_resolver_service import CLARIFICATION_QUESTION, ConflictCategory
from app.services.memory_service import MemoryService

# ---------------------------------------------------------------------------
# 1. 纯函数面
# ---------------------------------------------------------------------------


def test_attribution_phrases_frozen():
    """归因短语封闭词表冻结：新 reason code 必须显式登记（C-02/C-03 同纪律）。"""
    assert RESOLUTION_REASON_PHRASES == {
        "supersede_chain_head": "用户随后更新过此项，以取代链链头为准",
        "evidence_score": "以证据更强的记录为准",
        "updated_at": "以更新时间较新的记录为准",
        "confidence": "以置信度更高的记录为准",
        "tie_break_latest": "各项持平，以最新记录为准",
        "duplicate_title_overlap": "同名目标重叠，保留证据更强的一条",
        "similar_summary": "内容重复的回忆，保留更完整的一条",
        "goal_in_episodic": "目标与回忆记录重复，保留证据更强的一条",
    }


def test_clarification_stems_cover_m04_categories_except_scope():
    """模板类别 = M-04 类别去掉 SCOPE_DIFFERENCE（preserve-both 永不提问）与
    NONE（无类别旧行走 fallback stem，不注册专用模板）。"""
    categories = {category.value for category in ConflictCategory}
    assert set(CLARIFICATION_CATEGORY_STEMS) == categories - {"SCOPE_DIFFERENCE", "NONE"}


def test_digest_deterministic_and_bounded():
    long_text = "这是一个很长很长的记忆正文" * 20
    first = digest_text(long_text)
    assert first == digest_text(" ".join([long_text]))  # 空白折叠后一致
    assert len(first) <= DIGEST_MAX_CHARS
    assert first.endswith("…")
    assert digest_text("短句") == "短句"


def _pref_record(record_id, value, confidence=0.8):
    return SimpleNamespace(id=record_id, pref_value=value, confidence=confidence)


def _goal_record(record_id, title, score=0.7):
    return SimpleNamespace(id=record_id, title=title, evidence_score=score)


def test_resolved_fact_winner_semantics_not_diluted():
    """winner 为主句 + 归因短语；loser 以 id 归因、零原文回灌（V3-FIX-69）。"""
    winner_id, loser_id = uuid4(), uuid4()
    index = build_record_index(
        [_pref_record(winner_id, {"value": "soft"}), _pref_record(loser_id, {"value": "direct"})],
        [],
        [],
    )
    payload = build_conflict_resolution_context(
        conflict_notes=[
            {
                "type": "preference",
                "key": "feedback_tone",
                "reason": "supersede_chain_head",
                "winners": [str(winner_id)],
                "suppressed": [str(loser_id)],
            }
        ],
        record_index=index,
    )
    fact = payload["resolved_facts"][0]
    assert fact["winner_display"] == "soft"
    # 结构化面（进程内审计）保留 loser 原文投影
    assert fact["loser_displays"] == ["direct"]
    assert fact["attribution"] == RESOLUTION_REASON_PHRASES["supersede_chain_head"]
    assert fact["confidence"] == 0.8
    note = payload["prompt_note"]
    assert "以「soft」为准" in note
    # V3-FIX-69：prompt 面零 loser 原文；抑制事实以 id 归因保持可见（不静默）。
    assert "direct" not in note, "prompt_note 不得携带被抑制旧值原文"
    assert "不再采用" in note
    assert f"#{str(loser_id)[:8]}" in note
    assert "soft" in note


def test_prompt_note_suppressed_value_never_transits():
    """V3-FIX-69 契约锁：被 deny/supersede 抑制的旧偏好值不得经 prompt_note
    以原文形态过境——「越用越懂我」面上，被纠正的旧值零每轮 prompt 存在感。"""
    winner_id, loser_id = uuid4(), uuid4()
    loser_value = "晚上学习"
    index = build_record_index(
        [_pref_record(winner_id, {"value": "早上学习"}), _pref_record(loser_id, {"value": loser_value})],
        [],
        [],
    )
    payload = build_conflict_resolution_context(
        conflict_notes=[
            {
                "type": "preference",
                "key": "study_time",
                "reason": "supersede_chain_head",
                "winners": [str(winner_id)],
                "suppressed": [str(loser_id)],
            }
        ],
        record_index=index,
    )
    note = payload["prompt_note"]
    assert loser_value not in note, "被抑制旧值原文不得出现在 prompt_note"
    assert "早上学习" in note, "链头值必须在场"
    assert "不再采用" in note, "抑制事实本身保持可见（不静默）"
    # 投影面（to_prompt_payload = prompt 唯一出口）同样零旧值
    projected = to_prompt_payload(payload)["prompt_note"]
    assert loser_value not in projected


def test_materiality_rules_table():
    side_texts = ["我晚上通常能学一小时", "今天晚上只有二十分钟"]
    rules = [
        # (status, category, query, expect_material)
        ("resolved", "TEMPORAL_CHANGE", "晚上", False),
        ("pending_user", "SCOPE_DIFFERENCE", "晚上", False),
        ("pending_user", "UNSAFE_AMBIGUITY", None, True),
        ("pending_user", "UNSAFE_AMBIGUITY", "完全不相关的天气查询", True),
        ("pending_user", "TEMPORAL_CHANGE", "晚上能学多久", True),
        ("pending_user", "SOURCE_DISAGREEMENT", "晚上学习安排", True),
        ("pending_user", "TEMPORAL_CHANGE", "完全不相关的天气查询", False),
        ("pending_user", "TEMPORAL_CHANGE", None, False),
    ]
    for status, category, query, expect in rules:
        result = serialize_materiality(status, category, query, side_texts)
        assert result["material"] is expect, (status, category, query)


def serialize_materiality(status, category, query, side_texts):
    from app.services.conflict_resolution_context import assess_materiality

    return assess_materiality(status=status, category=category, query_text=query, side_texts=side_texts)


def test_clarification_question_deterministic_and_not_parroting():
    left, right = "我晚上通常能学习一小时", "今天晚上只有二十分钟"
    question = build_clarification_question(category="TEMPORAL_CHANGE", left_digest=left, right_digest=right)
    assert question == build_clarification_question(category="TEMPORAL_CHANGE", left_digest=left, right_digest=right)
    # 质量红线：不复读冲突原文（任一侧全文）、不复用 M-04 静态问句常量。
    assert question != left and question != right
    assert question != CLARIFICATION_QUESTION
    assert CLARIFICATION_CATEGORY_STEMS["TEMPORAL_CHANGE"] in question
    assert f"A：{left}" in question and f"B：{right}" in question
    # 未知类别 → 封闭 fallback（不抛错）。
    fallback = build_clarification_question(category="UNKNOWN", left_digest="a", right_digest="b")
    assert "有两种不一致的记录" in fallback


def test_unresolved_serialization_ask_flag():
    base = {
        "id": uuid4(),
        "conflict_key": "a" * 40,
        "status": "pending_user",
        "left_record_id": uuid4(),
        "right_record_id": None,
        "left_summary": "我晚上通常能学习一小时",
        "right_summary": "今天晚上只有二十分钟",
        "left_lane": "working_memory",
        "right_lane": "episodic",
        "surfaced_at": datetime(2026, 9, 1, 12, 0, 0),
    }

    def _row(category):
        payload = {
            "clarification": {
                "policy": "ask_once",
                "question": CLARIFICATION_QUESTION,
                "conflict_category": category,
                "options": [],
            }
        }
        return SimpleNamespace(left_payload=payload, right_payload={}, **base)

    unsafe = serialize_unresolved_for_context(_row("UNSAFE_AMBIGUITY"), query_text=None)
    assert unsafe["ask_if_material"] is True
    assert unsafe["clarification_question"]
    assert unsafe["materiality"]["reason_code"] == "unsafe_ambiguity_high_risk"
    assert unsafe["category"] == "UNSAFE_AMBIGUITY"

    temporal = serialize_unresolved_for_context(_row("TEMPORAL_CHANGE"), query_text="晚上学习")
    assert temporal["ask_if_material"] is True
    assert temporal["materiality"]["reason_code"] == "query_relevant"

    temporal_off = serialize_unresolved_for_context(_row("TEMPORAL_CHANGE"), query_text="天气如何")
    assert temporal_off["ask_if_material"] is False
    assert temporal_off["clarification_question"] is None

    # 缺 clarification payload 的旧行：按 M-04 ask_once 语义归 UNSAFE_AMBIGUITY。
    legacy = SimpleNamespace(left_payload={}, right_payload={}, **base)
    legacy_entry = serialize_unresolved_for_context(legacy, query_text=None)
    assert legacy_entry["category"] == "UNSAFE_AMBIGUITY"
    assert legacy_entry["ask_if_material"] is True


def test_select_material_clarification_one_best_question():
    unsafe = {
        "conflict_id": "unsafe-1",
        "category": "UNSAFE_AMBIGUITY",
        "ask_if_material": True,
        "surfaced_at": "2026-09-01T08:00:00",
        "clarification_question": "问句-unsafe",
    }
    temporal_newer = {
        "conflict_id": "temporal-2",
        "category": "TEMPORAL_CHANGE",
        "ask_if_material": True,
        "surfaced_at": "2026-09-02T08:00:00",
        "clarification_question": "问句-temporal",
    }
    payload = {"ask_if_material": True, "unresolved_conflicts": [temporal_newer, unsafe]}
    question, conflict_id, category = select_material_clarification(payload)
    # UNSAFE_AMBIGUITY 优先级高于更新的 TEMPORAL_CHANGE（One Best Question）。
    assert (question, conflict_id, category) == ("问句-unsafe", "unsafe-1", "UNSAFE_AMBIGUITY")
    # 无 material 冲突 → 全 None（确定性）。
    assert select_material_clarification({"ask_if_material": False, "unresolved_conflicts": [unsafe]}) == (
        None,
        None,
        None,
    )
    assert select_material_clarification(None) == (None, None, None)
    # ask_if_material=True 但条目全部非 material / 无问句 → 不产生问题。
    not_material = {
        "conflict_id": "temporal-2",
        "category": "TEMPORAL_CHANGE",
        "ask_if_material": False,
        "surfaced_at": "2026-09-02T08:00:00",
        "clarification_question": None,
    }
    assert select_material_clarification({"ask_if_material": True, "unresolved_conflicts": [not_material]}) == (
        None,
        None,
        None,
    )


def test_build_context_payload_shape_and_bounds():
    notes = []
    index = {}
    for i in range(PROMPT_NOTE_MAX_RESOLVED + 3):
        winner_id, loser_id = uuid4(), uuid4()
        notes.append(
            {
                "type": "preference",
                "key": f"key_{i}",
                "reason": "evidence_score",
                "winners": [str(winner_id)],
                "suppressed": [str(loser_id)],
            }
        )
        index[str(winner_id)] = {"kind": "preference", "display": f"win-{i}", "confidence": 0.9}
        index[str(loser_id)] = {"kind": "preference", "display": f"lose-{i}", "confidence": 0.1}
    payload = build_conflict_resolution_context(conflict_notes=notes, record_index=index)
    assert payload["version"] == CONFLICT_RESOLUTION_CONTEXT_VERSION
    assert len(payload["resolved_facts"]) == PROMPT_NOTE_MAX_RESOLVED + 3
    assert payload["ask_if_material"] is False
    assert len(payload["resolution_refs"]) == PROMPT_NOTE_MAX_RESOLVED + 3
    # prompt_note 有界：只渲染前 PROMPT_NOTE_MAX_RESOLVED 条。
    assert payload["prompt_note"].count("以「") == PROMPT_NOTE_MAX_RESOLVED
    assert all(ref["scope"] == "resolved" for ref in payload["resolution_refs"])
    # 未知 note kind 被封闭词表拒收。
    payload_bad_kind = build_conflict_resolution_context(
        conflict_notes=[{**notes[0], "type": "mystery"}], record_index=index
    )
    assert payload_bad_kind["resolved_facts"] == []


def test_prompt_note_never_carries_full_conflict_text():
    """长冲突原文不得整段进 prompt（卡面：避免把冲突文本全部塞进去）。"""
    winner_id, loser_id = uuid4(), uuid4()
    long_summary = "超长记忆正文" * 40
    index = {
        str(winner_id): {"kind": "episodic", "display": digest_text(long_summary), "confidence": None},
        str(loser_id): {"kind": "episodic", "display": digest_text(long_summary + "尾巴"), "confidence": None},
    }
    payload = build_conflict_resolution_context(
        conflict_notes=[
            {
                "type": "episodic",
                "key": str(winner_id),
                "reason": "similar_summary",
                "winners": [str(winner_id)],
                "suppressed": [str(loser_id)],
            }
        ],
        record_index=index,
    )
    assert long_summary not in payload["prompt_note"]
    assert all(len(entry["winner_display"] or "") <= DIGEST_MAX_CHARS for entry in payload["resolved_facts"])


# ---------------------------------------------------------------------------
# 2. 注入面（ContextPack，hermetic sqlite）
# ---------------------------------------------------------------------------


async def _make_user(db_session) -> User:
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user


def _unresolved_row(user_id, category, left, right, surfaced_at):
    return UnresolvedConflict(
        user_id=user_id,
        conflict_key=uuid4().hex,
        left_record_id=None,
        right_record_id=None,
        left_summary=left,
        right_summary=right,
        left_lane="working_memory",
        right_lane="episodic",
        left_payload={
            "clarification": {
                "policy": "ask_once",
                "question": CLARIFICATION_QUESTION,
                "conflict_category": category,
                "options": [],
            }
        },
        right_payload={},
        surfaced_at=surfaced_at,
    )


@pytest.mark.asyncio
async def test_context_pack_injects_conflict_resolution(db_session, monkeypatch):
    """注入真实发生 + winner/loser 语义保留 + unresolved 面带 ask-if-material。"""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_RANKING_SOFT_CAP_EPISODIC", 10, raising=False)
    monkeypatch.setattr(settings, "CONTEXT_RANKING_SOFT_CAP_GOALS", 10, raising=False)

    user = await _make_user(db_session)
    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user.id,
        pref_key="feedback_tone",
        pref_value={"value": "direct"},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user.id,
        pref_key="feedback_tone",
        pref_value={"value": "soft"},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )
    db_session.add(
        _unresolved_row(
            user.id,
            "UNSAFE_AMBIGUITY",
            "我晚上通常能学习一小时",
            "今天晚上只有二十分钟",
            datetime(2026, 9, 1, 12, 0, 0),
        )
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user.id, intent="chat", query_text="今晚怎么安排学习")

    # --- 注入真实发生（拔注入变异 → 本断言必红） ---
    assert pack.conflict_resolution is not None
    assert pack.conflict_resolution["version"] == CONFLICT_RESOLUTION_CONTEXT_VERSION
    prompt_payload = pack.to_prompt_context()["conflict_resolution"]
    assert prompt_payload["prompt_note"]
    # prompt 面是有界投影：结构化明细不整包进 prompt（token 纪律）。
    assert "resolved_facts" not in prompt_payload
    assert "unresolved_conflicts" not in prompt_payload
    assert set(prompt_payload) == {"version", "ask_if_material", "material_conflict_ids", "prompt_note"}
    assert pack.metadata is not None
    assert pack.metadata["conflict_resolution_refs"]

    # --- resolved 面：supersede 链 winner 归因 + loser 已知分歧 ---
    pref_facts = [f for f in pack.conflict_resolution["resolved_facts"] if f["kind"] == "preference"]
    assert pref_facts and pref_facts[0]["reason_code"] == "supersede_chain_head"
    assert pref_facts[0]["winner_display"] == "soft"  # V3-FIX-35 链头胜出
    assert "direct" in pref_facts[0]["loser_displays"]
    assert pack.preferences["feedback_tone"]["value"] == "soft"

    # --- unresolved 面：material 问句 + 两边均为「已知分歧」表述 ---
    unresolved = pack.conflict_resolution["unresolved_conflicts"]
    assert unresolved and unresolved[0]["ask_if_material"] is True
    assert unresolved[0]["clarification_question"]
    assert pack.conflict_resolution["ask_if_material"] is True
    assert pack.conflict_resolution["material_conflict_ids"] == [unresolved[0]["conflict_id"]]
    note = pack.conflict_resolution["prompt_note"]
    assert "以「soft」为准" in note
    # V3-FIX-69：resolved 面 loser 以 id 归因零原文；抑制从句在场。
    assert "不再采用" in note and "direct" not in note
    assert "待确认" in note


@pytest.mark.asyncio
async def test_context_pack_no_conflict_no_injection(db_session, monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)

    user = await _make_user(db_session)
    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user.id,
        pref_key="study_time_preference",
        pref_value={"value": "dark"},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user.id, intent="chat")

    assert pack.conflict_resolution is None
    assert "conflict_resolution" not in pack.to_prompt_context()
    assert "conflict_resolution_refs" not in (pack.metadata or {})


@pytest.mark.asyncio
async def test_context_pack_conflict_disabled_zero_injection(db_session, monkeypatch):
    """resolver 分支关闭时零注入（含 unresolved 面不被取回）。"""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    user = await _make_user(db_session)
    db_session.add(_unresolved_row(user.id, "UNSAFE_AMBIGUITY", "说法A", "说法B", datetime(2026, 9, 1, 12, 0, 0)))
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user.id, intent="chat")
    assert pack.conflict_resolution is None


@pytest.mark.asyncio
async def test_context_pack_query_relevance_gates_material(db_session, monkeypatch):
    """material 由「与当前 query 相关」确定性门控（不必要 clarification 率下降）。"""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)

    user = await _make_user(db_session)
    db_session.add(
        _unresolved_row(
            user.id,
            "TEMPORAL_CHANGE",
            "我晚上通常能学习一小时",
            "今天晚上只有二十分钟",
            datetime(2026, 9, 1, 12, 0, 0),
        )
    )
    await db_session.commit()

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)

    relevant = await builder.build(user.id, intent="chat", query_text="今晚的学习安排")
    assert relevant.conflict_resolution is not None
    entry = relevant.conflict_resolution["unresolved_conflicts"][0]
    assert entry["ask_if_material"] is True
    assert entry["materiality"]["reason_code"] == "query_relevant"

    irrelevant = await builder.build(user.id, intent="chat", query_text="食堂菜单怎么样")
    entry = irrelevant.conflict_resolution["unresolved_conflicts"][0]
    assert entry["ask_if_material"] is False
    assert irrelevant.conflict_resolution["ask_if_material"] is False
    assert irrelevant.conflict_resolution["material_conflict_ids"] == []


@pytest.mark.asyncio
async def test_context_pack_unresolved_fetch_failure_is_fail_soft(db_session, monkeypatch):
    """unresolved 查询故障 → 降级为无 unresolved 面，resolved 注入不受影响。"""
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", False, raising=False)

    user = await _make_user(db_session)
    memory_service = MemoryService(db_session)
    await memory_service.upsert_preference(
        user_id=user.id,
        pref_key="feedback_tone",
        pref_value={"value": "direct"},
        evidence_refs=[{"type": "event", "id": "evt_1"}],
    )
    await memory_service.upsert_preference(
        user_id=user.id,
        pref_key="feedback_tone",
        pref_value={"value": "soft"},
        evidence_refs=[{"type": "event", "id": "evt_2"}],
    )
    await db_session.commit()

    class _BoomService:
        def __init__(self, db):
            pass

        async def list_unresolved_conflicts(self, *, user_id):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        "app.core.context_pack.ConflictResolverService",
        _BoomService,
        raising=True,
    )

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 50, "goals": 50, "episodic": 50}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user.id, intent="chat")
    assert pack.conflict_resolution is not None
    assert pack.conflict_resolution["unresolved_conflicts"] == []
    assert pack.conflict_resolution["resolved_facts"]


# ---------------------------------------------------------------------------
# 3. 消费面（SufficiencyChecker）
# ---------------------------------------------------------------------------


def _material_payload():
    return {
        "ask_if_material": True,
        "unresolved_conflicts": [
            {
                "conflict_id": "conflict-1",
                "category": "UNSAFE_AMBIGUITY",
                "ask_if_material": True,
                "surfaced_at": "2026-09-01T08:00:00",
                "clarification_question": "我的记录里有两种相互矛盾的说法，需要你确认现在哪一种符合实际情况。A：甲；B：乙。请回复 A 或 B（如果都不对，直接告诉我实际情况即可）。",
            },
            {
                "conflict_id": "conflict-2",
                "category": "TEMPORAL_CHANGE",
                "ask_if_material": False,
                "surfaced_at": "2026-09-02T08:00:00",
                "clarification_question": None,
            },
        ],
    }


@pytest.mark.asyncio
async def test_sufficiency_asks_material_conflict_only():
    checker = SufficiencyChecker()
    complete = {"task_title": "背单词", "due_date": "明天", "task_type": "学习", "priority": 2}
    result = await checker.check(
        intent="create_task",
        extracted_entities=complete,
        conversation_context=[],
        conflict_resolution=_material_payload(),
    )
    assert result.status == SufficiencyStatus.NEED_CLARIFICATION
    assert result.recommended_action == "ask"
    assert result.clarification_questions[0].startswith("我的记录里有两种相互矛盾的说法")
    assert result.conflict_clarification_ref == "conflict-1"
    assert "memory_conflict" in result.missing_fields


@pytest.mark.asyncio
async def test_sufficiency_ignores_non_material_conflict():
    checker = SufficiencyChecker()
    complete = {"task_title": "背单词"}
    payload = {
        "ask_if_material": False,
        "unresolved_conflicts": [
            {
                "conflict_id": "conflict-2",
                "category": "TEMPORAL_CHANGE",
                "ask_if_material": False,
                "surfaced_at": "2026-09-02T08:00:00",
                "clarification_question": None,
            }
        ],
    }
    result = await checker.check(
        intent="create_task",
        extracted_entities=complete,
        conversation_context=[],
        conflict_resolution=payload,
    )
    assert result.status == SufficiencyStatus.SUFFICIENT
    assert result.clarification_questions == []

    # 防御性反转：payload 级 ask_if_material=False 时，即使条目误带问句，
    # SufficiencyChecker 也绝不提问（「只对 material 冲突提问」的第二道门）。
    hostile_payload = {
        "ask_if_material": False,
        "unresolved_conflicts": [
            {
                "conflict_id": "conflict-3",
                "category": "UNSAFE_AMBIGUITY",
                "ask_if_material": True,
                "surfaced_at": "2026-09-03T08:00:00",
                "clarification_question": "误带问句",
            }
        ],
    }
    result = await checker.check(
        intent="create_task",
        extracted_entities=complete,
        conversation_context=[],
        conflict_resolution=hostile_payload,
    )
    assert result.status == SufficiencyStatus.SUFFICIENT
    assert result.clarification_questions == []
    assert result.conflict_clarification_ref is None
    assert result.conflict_clarification_ref is None


@pytest.mark.asyncio
async def test_sufficiency_default_param_unchanged():
    """缺省 conflict_resolution=None → 与基线行为逐位一致（守卫零弱化）。"""
    checker = SufficiencyChecker()
    result = await checker.check(
        intent="create_task",
        extracted_entities={},
        conversation_context=[],
    )
    assert result.status == SufficiencyStatus.NEED_CLARIFICATION
    assert result.clarification_questions == ["请问您想创建什么任务？"]
    assert result.conflict_clarification_ref is None


@pytest.mark.asyncio
async def test_sufficiency_confirmation_not_overridden_by_conflict():
    checker = SufficiencyChecker()
    result = await checker.check(
        intent="delete_task",
        extracted_entities={"task_id": "t1", "task_title": "背单词"},
        conversation_context=[],
        conflict_resolution=_material_payload(),
    )
    assert result.status == SufficiencyStatus.NEED_CONFIRMATION
    assert result.recommended_action == "confirm"
    assert result.conflict_clarification_ref is None


@pytest.mark.asyncio
async def test_sufficiency_loop_guard_covers_conflict_question():
    """同一冲突问句重复出现 → 既有环路守卫照常收敛（ask-once 不复读：
    CLARIFICATION_LOOP_THRESHOLD=2，第二次同指纹即压制）。"""
    checker = SufficiencyChecker()
    complete = {"task_title": "背单词", "due_date": "明天", "task_type": "学习", "priority": 2}
    tracking_key = "user:session:create_task"
    first = await checker.check(
        intent="create_task",
        extracted_entities=complete,
        conversation_context=[],
        tracking_key=tracking_key,
        conflict_resolution=_material_payload(),
    )
    assert first.status == SufficiencyStatus.NEED_CLARIFICATION
    assert first.conflict_clarification_ref == "conflict-1"
    second = await checker.check(
        intent="create_task",
        extracted_entities=complete,
        conversation_context=[],
        tracking_key=tracking_key,
        conflict_resolution=_material_payload(),
    )
    assert second.status == SufficiencyStatus.SUFFICIENT
    assert second.clarification_questions == []


def test_unresolved_ordering_newest_first_from_service_shape():
    """payload 内 surfaced_at 新者优先（同优先级下）——排序确定性钉子。"""
    older = {
        "conflict_id": "old",
        "category": "TEMPORAL_CHANGE",
        "ask_if_material": True,
        "surfaced_at": "2026-09-01T08:00:00",
        "clarification_question": "old-q",
    }
    newer = {
        "conflict_id": "new",
        "category": "SOURCE_DISAGREEMENT",
        "ask_if_material": True,
        "surfaced_at": "2026-09-03T08:00:00",
        "clarification_question": "new-q",
    }
    question, conflict_id, _ = select_material_clarification(
        {"ask_if_material": True, "unresolved_conflicts": [older, newer]}
    )
    assert (question, conflict_id) == ("new-q", "new")


def test_unresolved_fetch_limit_constant_registered():
    from app.services.conflict_resolution_context import UNRESOLVED_FETCH_LIMIT

    assert UNRESOLVED_FETCH_LIMIT == 5
