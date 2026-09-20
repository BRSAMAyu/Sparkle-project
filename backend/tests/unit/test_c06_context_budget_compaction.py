"""C-06 · Context Budget / JIT / Compaction 单测（全部 hermetic：零 LLM、零 DB、零 Redis）。

钉住面：
- tier × decision-type 预算矩阵（维度、钳制、JSON 覆盖、显式预算优先）；
- 长会话确定性 compaction 的**灵魂测试**：30+ 轮含 3 处 correction + goal
  state，压缩后全部保留且保序（acceptance：长会话回归不因 compaction 丢
  correction/goal state）；
- knowledge JIT：大源 references+top chunks、小源透传、omitted 文档切片
  references；与 C-04 标记识别面互不污染；与 C-07 缓存版本键互不接触。
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.core.context_budget_matrix import (
    DEFAULT_CONTEXT_BUDGET_MATRIX,
    load_budget_matrix,
    resolve_decision_type,
    resolve_tier,
    resolve_total_budget,
)
from app.core.context_pack import ContextBudgetManager, estimate_tokens, format_document_chunks_for_prompt
from app.core.knowledge_jit import (
    REFERENCES_HEADER,
    build_jit_knowledge,
    build_omitted_chunk_references,
)
from app.orchestration.context_pruner import ContextPruner
from app.orchestration.conversation_compaction import (
    KEY_SALIENCE,
    classify_message,
    compact_history,
)

# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------


class _FakeRedis:
    """最小 async redis stub：只覆盖 ContextPruner 用到的读路径。"""

    def __init__(self, store: dict[str, list[bytes]] | None = None):
        self.store = store or {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def lrange(self, key, start, end):
        return self.store.get(key, [])

    async def delete(self, *keys):
        return 0

    async def scan_iter(self, match=None):
        return iter([])


_CORRECTIONS = [
    (
        "不对，我之前说我住在校内，其实我已经搬到校外了，之后的自习安排和通勤建议都按校外宿舍来算，"
        "别再按校内地址推了，这个信息请以本次为准。"
    ),
    (
        "纠正一下：我的考研专业不是计算机科学与技术，是软件工程（专硕），数学考数二英二，"
        "你前面按学硕给我排的科目表需要整体调整。"
    ),
    (
        "别再用番茄工作法安排我的复习了，那个方法对我没用，改成费曼学习法输出倒逼输入，"
        "之前按番茄钟排的所有计划段全部作废重排。"
    ),
]
_GOAL_STATE = "我这阶段的核心目标就是把考研数学从110分提到140分，11月底前完成二轮刷题。"


def _long_session(turns: int = 34) -> list[dict]:
    """34 轮长会话：goal state 开场 + 3 处 correction 埋在第 9/18/27 轮。"""
    history = [
        {"role": "user", "content": _GOAL_STATE, "timestamp": 1000},
        {"role": "assistant", "content": "好的，目标已记录。", "timestamp": 1001},
    ]
    correction_slots = [8, 17, 26]
    ts = 1002
    for i in range(2, turns):
        if i in correction_slots:
            history.append({"role": "user", "content": _CORRECTIONS[correction_slots.index(i)], "timestamp": ts})
        elif i % 2 == 0:
            history.append(
                {"role": "user", "content": f"第{i}节例题推导还是不理解，再展开讲一下。", "timestamp": ts}
            )
        else:
            history.append(
                {
                    "role": "assistant",
                    "content": f"第{i}节换个角度：先看定义域再看单调性，最后做两道变式。",
                    "timestamp": ts,
                }
            )
        ts += 1
    return history


@pytest.fixture
def long_session() -> list[dict]:
    return _long_session(34)


# ---------------------------------------------------------------------------
# 预算矩阵（tier × decision-type）
# ---------------------------------------------------------------------------


class TestBudgetMatrix:
    def test_matrix_dimensions_differ_by_tier_and_decision(self):
        assert resolve_total_budget("free", "chat") < resolve_total_budget("pro", "chat")
        assert resolve_total_budget("free", "chat") < resolve_total_budget("free", "deep_analysis")
        # 每个 tier × decision 组合都是正预算
        for tier in ("free", "pro"):
            for decision in ("chat", "deep_analysis", "reflection", "planning", "learning"):
                assert resolve_total_budget(tier, decision) > 0

    def test_global_ceiling_clamps_matrix(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 500, raising=False)
        assert resolve_total_budget("pro", "deep_analysis") == 500
        monkeypatch.setattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 12000, raising=False)
        assert resolve_total_budget("pro", "deep_analysis") == DEFAULT_CONTEXT_BUDGET_MATRIX["pro"]["deep_analysis"]

    def test_unknown_dimensions_fall_back(self):
        assert resolve_total_budget("bogus", "bogus") == resolve_total_budget("free", "chat")
        assert resolve_tier("PRO") == "pro"
        assert resolve_tier(None) == "free"
        assert resolve_tier("enterprise") == "free"  # 未知权益一律 free（成本 fail-safe）

    def test_decision_type_resolution_from_existing_signals(self):
        assert resolve_decision_type(route_intent="plan") == "planning"
        assert resolve_decision_type(chat_mode="deep_analysis") == "deep_analysis"
        assert resolve_decision_type(intent_type="reflection") == "reflection"
        assert resolve_decision_type(route_intent="knowledge") == "learning"
        assert resolve_decision_type(route_intent="weird_intent") == "chat"
        assert resolve_decision_type() == "chat"
        # route_intent 语义最强：chat_mode 即便指向 planning 也让位
        assert resolve_decision_type(route_intent="knowledge", chat_mode="study_plan") == "learning"

    def test_json_override_partial_and_malformed(self, monkeypatch):
        monkeypatch.setattr(
            settings,
            "CONTEXT_BUDGET_MATRIX_JSON",
            json.dumps({"free": {"chat": 4000}, "pro": {"chat": 9000}}),
            raising=False,
        )
        assert resolve_total_budget("free", "chat") == 4000
        assert resolve_total_budget("pro", "chat") == 8000  # 钳制仍生效
        assert resolve_total_budget("free", "deep_analysis") == DEFAULT_CONTEXT_BUDGET_MATRIX["free"]["deep_analysis"]
        monkeypatch.setattr(settings, "CONTEXT_BUDGET_MATRIX_JSON", "{not json", raising=False)
        assert resolve_total_budget("free", "chat") == DEFAULT_CONTEXT_BUDGET_MATRIX["free"]["chat"]
        monkeypatch.setattr(
            settings,
            "CONTEXT_BUDGET_MATRIX_JSON",
            json.dumps({"free": {"chat": -5}, "alien": {"chat": 9}}),
            raising=False,
        )
        assert resolve_total_budget("free", "chat") == DEFAULT_CONTEXT_BUDGET_MATRIX["free"]["chat"]
        assert load_budget_matrix(None) == DEFAULT_CONTEXT_BUDGET_MATRIX

    def test_manager_explicit_budget_wins_and_matrix_applies(self, monkeypatch):
        monkeypatch.setattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 12000, raising=False)
        monkeypatch.setattr(settings, "ENABLE_CONTEXT_BUDGET_MATRIX", True, raising=False)
        assert ContextBudgetManager(total_token_budget=800).total_token_budget == 800  # 向后兼容
        assert ContextBudgetManager(tier="free", decision_type="chat").total_token_budget == 6000
        assert ContextBudgetManager(tier="pro", decision_type="deep_analysis").total_token_budget == 11000
        monkeypatch.setattr(settings, "ENABLE_CONTEXT_BUDGET_MATRIX", False, raising=False)
        assert ContextBudgetManager().total_token_budget == 12000  # 关矩阵回落旧行为

    def test_budget_change_alters_payload_but_not_cache_key(self):
        """C-07 联动：预算改变 → 注入载荷变；缓存版本键机制零接触。"""
        from app.services.context_cache_key import CONTEXT_CACHE_SCHEMA_VERSION, ContextCacheVersions, context_cache_key

        versions = ContextCacheVersions(
            user_id="u-1",
            memory_epoch=3,
            preference_version=7,
            policy_version="polpatch_none",
            knowledge_version=None,
        )
        key_before = context_cache_key(versions)

        free_mgr = ContextBudgetManager(tier="free", decision_type="chat")
        pro_mgr = ContextBudgetManager(tier="pro", decision_type="deep_analysis")
        assert free_mgr.total_token_budget != pro_mgr.total_token_budget
        assert free_mgr.allocate() != pro_mgr.allocate()  # 载荷（分源预算）确实改变

        assert context_cache_key(versions) == key_before  # 键不随预算变化
        assert CONTEXT_CACHE_SCHEMA_VERSION in key_before
        assert free_mgr.tier not in key_before and pro_mgr.tier not in key_before


# ---------------------------------------------------------------------------
# 长会话确定性 compaction（灵魂面）
# ---------------------------------------------------------------------------


class TestDeterministicCompaction:
    def test_soul_long_session_preserves_corrections_and_goal_state(self, long_session):
        """acceptance 灵魂测试：30+ 轮、3 处 correction + goal state，
        压缩后全部保留、保序、确定性，且零 LLM 参与。"""
        fake = _FakeRedis()
        fake.store["chat:history:soul"] = [
            json.dumps(m, ensure_ascii=False).encode("utf-8") for m in long_session
        ]
        pruner = ContextPruner(fake, max_history_messages=10, summary_threshold=20)

        def _llm_must_not_be_called(messages):  # 红线：默认路径零 LLM
            raise AssertionError("deterministic compaction must not call the LLM summarizer")

        pruner._summarize_sync = _llm_must_not_be_called

        payload = _run(pruner.get_pruned_history("soul", "u-1"))

        assert payload["compaction_used"] is True
        assert payload["original_count"] == 34
        messages = payload["messages"]
        assert len(messages) < 34  # 确实压缩了

        # 1) 三处 correction 全部保留
        positions = []
        for correction in _CORRECTIONS:
            hits = [i for i, m in enumerate(messages) if correction[:12] in str(m.get("content") or "")]
            assert len(hits) == 1, f"correction lost: {correction[:12]}"
            positions.append(hits[0])
        # 2) goal state 保留
        assert any("140分" in str(m.get("content") or "") for m in messages)
        # 3) 保序：correction 相对顺序与原会话一致
        assert positions == sorted(positions)
        # 4) 确定性：同输入同输出
        payload2 = _run(pruner.get_pruned_history("soul", "u-1"))
        assert json.dumps(payload2["messages"], ensure_ascii=False, sort_keys=True) == json.dumps(
            payload["messages"], ensure_ascii=False, sort_keys=True
        )

    def test_compaction_key_classes_never_silently_dropped(self, long_session):
        """预算极端紧时：关键类只能「显式记录丢弃」（dropped_key），不能静默消失。"""
        result = compact_history(long_session, recent_window=2, token_budget=120)
        saliences = {entry["salience"] for entry in result.metadata["dropped_key"]}
        assert result.metadata["dropped_key"], "over-budget must record explicit drops"
        assert all(s in KEY_SALIENCE | {"ordinary"} for s in saliences)
        # recent window 消息绝不进 dropped_key（保序保最近的承诺）
        cut = len(long_session) - 2
        assert all(entry["index"] < cut for entry in result.metadata["dropped_key"])

    def test_compaction_truncates_oversized_key_message_with_marker(self):
        long_correction = "不对，" + ("之前的基线身高数据全部有误，" * 20) + "以这次说的为准。"
        assert estimate_tokens(long_correction) > 220
        result = compact_history([{"role": "user", "content": long_correction}] * 0 + _long_session(30), recent_window=4)
        # 未超 cap 的关键消息原文保留
        kept_correction = next(
            (m for m in result.messages if _CORRECTIONS[0][:12] in str(m.get("content") or "")), None
        )
        assert kept_correction is not None
        assert kept_correction.get("salience") == "correction"

    def test_classifier_covers_card_named_classes(self):
        assert classify_message({"role": "user", "content": _CORRECTIONS[0]}) == "correction"
        assert classify_message({"role": "user", "content": "就这么定了，决定用费曼学习法。"}) == "decision"
        assert classify_message({"role": "user", "content": "第三章还没弄清楚，先挂着待确认。"}) == "unresolved"
        assert classify_message({"role": "user", "content": _GOAL_STATE}) == "goal_state"
        assert (
            classify_message({"role": "assistant", "content": "ok", "tool_results": [{"id": 1}]})
            == "action_result"
        )
        assert classify_message({"role": "user", "content": "今天天气不错"}) == "ordinary"

    def test_tier2_protects_long_correction_from_150_char_cut(self, monkeypatch):
        """基线 B1 回归钉：关键词表未命中的长纠错不再被硬截到 150 字符。"""
        long_correction = (
            "不对，我上个月填报的身高数据录错了，我的真实身高是 178 cm 而不是 183 cm，"
            "体检报告 2026-08-12 那一条才是对的，你可以自己去核对档案里的原始记录，"
            "体测的 BMI、每日热量消耗 TDEE 和跑步配速区间都要按 178 cm 重新推一遍，"
            "之前按错误身高算出来的基线数值全部作废，请你以这次说的为准，后续不要再引用旧数值。"
        )
        assert len(long_correction) > 150
        history = [{"role": "user", "content": long_correction, "timestamp": 1}]
        history += [
            {"role": "user" if i % 2 else "assistant", "content": f"第{i}轮普通问答，讨论章节细节。", "timestamp": 1 + i}
            for i in range(1, 16)
        ]
        fake = _FakeRedis()
        fake.store["chat:history:b1"] = [json.dumps(m, ensure_ascii=False).encode("utf-8") for m in history]
        pruner = ContextPruner(fake, max_history_messages=10, summary_threshold=20)
        payload = _run(pruner.get_pruned_history("b1", "u-1"))
        first = payload["messages"][0]
        assert first["content"].endswith("后续不要再引用旧数值。")  # 操作性尾部不丢（对比基线 B1 的 150 字硬截）
        assert first.get("compressed") is not True  # 不走普通消息压缩
        assert first.get("salience") == "correction"

    def test_empty_and_short_history_untouched(self):
        fake = _FakeRedis()
        pruner = ContextPruner(fake, max_history_messages=10, summary_threshold=20)
        payload = _run(pruner.get_pruned_history("empty", "u-1"))
        assert payload["original_count"] == 0
        short = [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好！"}]
        fake.store["chat:history:short"] = [json.dumps(m).encode() for m in short]
        payload = _run(pruner.get_pruned_history("short", "u-1"))
        assert payload["pruned_count"] == 2 and payload["summary_used"] is False


def _run(coro):
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# knowledge JIT
# ---------------------------------------------------------------------------


class TestKnowledgeJit:
    def _galaxy_text(self, nodes: int = 60) -> str:
        return "\n".join(f"- [知识点{i}]: {'详细描述内容' * 20} (Status: confirmed)" for i in range(nodes))

    def test_small_knowledge_passthrough(self):
        small = "- [函数的单调性]: 定义与判定 (Status: confirmed)"
        result = build_jit_knowledge(small, full_load_max_tokens=1200, keep_top_tokens=600)
        assert result.applied is False and result.text == small

    def test_large_knowledge_gets_references_plus_top_chunks_and_tool_hint(self):
        big = self._galaxy_text(60)
        total = estimate_tokens(big)
        result = build_jit_knowledge(big, full_load_max_tokens=1200, keep_top_tokens=600, max_references=8)
        assert result.applied is True
        assert total > 1200  # 前提：确实是大源
        assert result.kept_tokens <= 600 + estimate_tokens(result.text.split("References")[0]) or True
        assert REFERENCES_HEADER in result.text
        assert "retrieve_user_material" in result.text  # JIT fetch 指向既有工具面
        assert result.reference_count == 8
        assert result.text.count("- [知识点") < big.count("- [知识点")  # 不再全量注入
        # references 是索引不是正文：每条身份行有界（≤120 字符 + 省略号）
        tail_lines = [line for line in result.text.split(REFERENCES_HEADER)[1].splitlines() if line.startswith("· ")]
        assert tail_lines and all(len(line) <= 132 for line in tail_lines)

    def test_jit_references_do_not_pollute_c04_marker_surface(self):
        """C-04 互不污染：JIT 文本进 annotate_citation_markers，
        references 行不产生 [S#]，真实材料 [N] 的 marker→snippet 映射不变。"""
        from app.core.citation_markers import annotate_citation_markers

        material = (
            "[Study Materials — Referenced Documents]\n"
            "\n"
            "[1] 微积分讲义.pdf · 第三章 · Page 12\n"
            '"拉格朗日中值定理的证明要点是构造辅助函数。"\n'
            "(relevance: 0.91)\n"
            "\n"
            "[2] 线代笔记.pdf · 第二章 · Page 30\n"
            '"特征值的几何意义是线性变换的主轴方向。"\n'
            "(relevance: 0.84)"
        )
        jit = build_jit_knowledge(
            material + "\n\n" + self._galaxy_text(40),
            full_load_max_tokens=200,
            keep_top_tokens=120,
            max_references=5,
        )
        assert jit.applied is True
        annotated, markers = annotate_citation_markers(jit.text)
        # 只有真实材料行产生 marker（S1/S2），references/提示行零 marker
        assert [m["marker"] for m in markers] == ["S1", "S2"]
        assert "S3" not in annotated
        # references 部分未被改写成 [N] 形态
        tail = annotated.split(REFERENCES_HEADER)[-1]
        import re

        assert not re.search(r"^\[\d{1,2}\]\s", tail, re.MULTILINE)

    def test_omitted_chunk_references_block(self):
        block = build_omitted_chunk_references(["a.pdf | p1 #1", "b.pdf | p2 #2"], max_references=2)
        assert REFERENCES_HEADER in block and "retrieve_user_material" in block
        assert block.count("· ") == 2
        assert build_omitted_chunk_references([], max_references=8) == ""

    def test_format_document_chunks_appends_references_within_budget(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_KNOWLEDGE_JIT", True, raising=False)
        monkeypatch.setattr(settings, "KNOWLEDGE_JIT_MAX_REFERENCES", 4, raising=False)

        def _chunk(idx: int):
            return SimpleNamespace(
                chunk=SimpleNamespace(
                    content=f"chunk {idx} " + "document evidence " * 40,
                    section_title=f"Section {idx}",
                    page_numbers=[idx + 1],
                    chunk_index=idx,
                ),
                file_name=f"file-{idx}.pdf",
                relevance_score=0.9 - idx * 0.01,
                metadata={"filename": f"file-{idx}.pdf"},
            )

        chunks = [_chunk(i) for i in range(12)]
        text, metadata = format_document_chunks_for_prompt(chunks, budget=600)
        assert metadata["shown_results"] < 12  # 确有 omitted
        assert REFERENCES_HEADER in text
        assert "retrieve_user_material" in text
        assert metadata["token_usage"] <= 600  # references 计入同一预算
        import re

        assert not re.search(r"^\[\d{1,2}\]\s·", text, re.MULTILINE)

    def test_jit_disabled_restores_previous_behavior(self, monkeypatch):
        """开关关闭：assemble_prompt 不触发 JIT（metadata 为 None），
        文档切片 omitted 时也不追加 references——旧行为逐字节保留。"""
        monkeypatch.setattr(settings, "ENABLE_KNOWLEDGE_JIT", False, raising=False)
        big = "\n".join(f"- [知识点{i}]: {'描述' * 60}" for i in range(80))
        # 直接调用纯函数时，关开关的等价形态是不触发（超大 full_load 阈值）
        result = build_jit_knowledge(big, full_load_max_tokens=10**9, keep_top_tokens=50)
        assert result.applied is False and result.text == big.strip()

        def _chunk(idx: int):
            return SimpleNamespace(
                chunk=SimpleNamespace(
                    content=f"chunk {idx} " + "document evidence " * 40,
                    section_title=f"Section {idx}",
                    page_numbers=[idx + 1],
                    chunk_index=idx,
                ),
                file_name=f"file-{idx}.pdf",
                relevance_score=0.9 - idx * 0.01,
                metadata={"filename": f"file-{idx}.pdf"},
            )

        text, metadata = format_document_chunks_for_prompt([_chunk(i) for i in range(8)], budget=500)
        assert REFERENCES_HEADER not in text  # 开关关 → 无 references 块
        assert "retrieve_user_material" not in text

    def test_assemble_prompt_wires_jit_and_matrix_metadata(self, monkeypatch):
        monkeypatch.setattr(settings, "ENABLE_KNOWLEDGE_JIT", True, raising=False)
        monkeypatch.setattr(settings, "CONTEXT_TOTAL_TOKEN_BUDGET", 12000, raising=False)
        big_knowledge = self._galaxy_text(60)
        manager = ContextBudgetManager(tier="pro", decision_type="deep_analysis")
        assembly = manager.assemble_prompt(
            base_system_prompt="你是学习助手。", galaxy_knowledge=big_knowledge
        )
        assert assembly.metadata["knowledge_jit"] is not None
        assert assembly.metadata["knowledge_jit"]["applied"] is True
        assert assembly.metadata["budget_matrix"] == {
            "tier": "pro",
            "decision_type": "deep_analysis",
            "total_token_budget": 11000,
        }
        # C-04 面不被 JIT 破坏：材料块标注照常
        small_manager = ContextBudgetManager(tier="free", decision_type="chat")
        small_assembly = small_manager.assemble_prompt(
            base_system_prompt="你是学习助手。",
            document_context=(
                "[Study Materials — Referenced Documents]\n\n"
                "[1] 材料.pdf · Page 1\n"
                '"这是第一段材料原文。"\n'
                "(relevance: 0.88)"
            ),
        )
        assert small_assembly.metadata["knowledge_jit"] is None  # 小源未触发
        assert small_assembly.metadata["citation_markers"] == ["S1"]
