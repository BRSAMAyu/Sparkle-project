"""F-2 内部命名泄漏：标题清洗函数单测（红测先行）。

缺陷证据：星图详情页大标题呈现「TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与
错因回看」（v3-output/WT324-SIMEVIDENCE/REPORT.md §四 F-2，G03_sheet_loaded.png）。
内部 token 生成语义见 backend/tests/northstar_eval/feature_tour.py S7：
run = {run_id(uuid4 hex8)}-{冲刺序}-{uuid4 hex6}。
边界覆盖：完整证据串 / 嵌入描述 / 全内部 token / 无内部 token / 空 / 英文变体。
"""

from __future__ import annotations

import pytest

from app.services.galaxy.title_sanitizer import clean_display_title, strip_internal_tokens

EVIDENCE_TITLE = "TOUR 专题7-d91d5df0-10-5dc70d: 真题演练与错因回看"
EVIDENCE_TAIL = "真题演练与错因回看"


class TestStripInternalTokens:
    def test_evidence_title_keeps_only_semantic_tail(self):
        assert strip_internal_tokens(EVIDENCE_TITLE) == EVIDENCE_TAIL

    def test_embedded_in_description_keeps_prefix_and_tail(self):
        dirty = f"来自任务的学习主题：{EVIDENCE_TITLE}"
        assert strip_internal_tokens(dirty) == f"来自任务的学习主题：{EVIDENCE_TAIL}"

    def test_chinese_fullwidth_colon_variant(self):
        assert strip_internal_tokens("TOUR 专题3-ab12cd34-2-ef4567：动量守恒定律") == "动量守恒定律"

    def test_english_topic_variant(self):
        assert strip_internal_tokens("TOUR Topic 3-a1b2c3d4-2-9f8e7d: Work-energy theorem") == "Work-energy theorem"

    def test_normal_title_untouched(self):
        for clean in (
            "数据结构复习 — 二叉树专题",
            "导数应用专题练习",
            "TCP 拥塞控制",
            "复习 动量守恒题型",
            "Topic modeling: an introduction",
            "GDP 与货币政策：简述",
        ):
            assert strip_internal_tokens(clean) == clean, clean

    def test_empty_string(self):
        assert strip_internal_tokens("") == ""

    def test_token_only_with_empty_tail_drops_block(self):
        assert strip_internal_tokens("TOUR 专题7-d91d5df0-10-5dc70d: ") == ""


class TestCleanDisplayTitle:
    def test_evidence_title(self):
        assert clean_display_title(EVIDENCE_TITLE) == EVIDENCE_TAIL

    def test_all_internal_token_falls_back_to_topic_number(self):
        assert clean_display_title("TOUR 专题7-d91d5df0-10-5dc70d") == "专题 7"

    def test_normal_title_zero_rewrite(self):
        clean = "数据结构复习 — 二叉树专题"
        assert clean_display_title(clean) == clean

    def test_empty(self):
        assert clean_display_title("") == ""

    def test_whitespace_only_title_with_token_normalizes(self):
        assert clean_display_title(f"  {EVIDENCE_TITLE}  ") == EVIDENCE_TAIL

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("TOUR 专题1-d91d5df0-1-aaaaaa: 真题演练与错因回看", EVIDENCE_TAIL),
            ("TOUR 专题2-d91d5df0-1-bbbbbb: 真题演练与错因回看", EVIDENCE_TAIL),
            ("TOUR 专题7-e2f3a4b5-11-cccccc: 真题演练与错因回看", EVIDENCE_TAIL),
        ],
    )
    def test_same_tail_across_tokens_collapses_to_one_name(self, raw, expected):
        """不同 token 同语义尾必须清洗成同一可读名——同题一颗星的前提。"""
        assert clean_display_title(raw) == expected


# ---------------------------------------------------------------------------
# F-2 读取侧存量防御：NodeBase/NodeWithStatus 投影对存量脏行只在展示面清洗，
# 不重写库；正常数据零改写。fake 节点用真实 ORM 形（未持久化）。
# ---------------------------------------------------------------------------

from types import SimpleNamespace
from uuid import uuid4

from app.schemas.galaxy import NodeBase, sanitize_keywords


def _dirty_node() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        name=EVIDENCE_TITLE,
        name_en=None,
        description=f"来自任务的学习主题：{EVIDENCE_TITLE}",
        keywords=[EVIDENCE_TITLE],
        importance_level=3,
        is_seed=False,
        parent_id=None,
        parent=None,
        subject=None,
        sector_weights=None,
        dominant_sector_code=None,
        position_x=0.0,
        position_y=0.0,
        global_spark_count=0,
    )


def test_nodebase_projection_scrubs_dirty_name_description_keywords():
    projected = NodeBase.from_model(_dirty_node())
    assert projected.name == EVIDENCE_TAIL
    assert projected.description == f"来自任务的学习主题：{EVIDENCE_TAIL}"
    assert projected.keywords == [EVIDENCE_TAIL]
    assert EVIDENCE_TAIL in projected.tags, "tags fallback/keyword source must be scrubbed too"
    for tag in projected.tags:
        assert "d91d5df0" not in tag and "TOUR" not in tag


def test_nodebase_projection_keeps_clean_node_untouched():
    node = _dirty_node()
    node.name = "数据结构复习 — 二叉树专题"
    node.description = "二叉树的性质与遍历"
    node.keywords = ["二叉树", "数据结构"]
    projected = NodeBase.from_model(node)
    assert projected.name == "数据结构复习 — 二叉树专题"
    assert projected.description == "二叉树的性质与遍历"
    assert projected.keywords == ["二叉树", "数据结构"]


def test_sanitize_keywords_dedupes_after_scrub_and_drops_empty():
    assert sanitize_keywords([EVIDENCE_TITLE, EVIDENCE_TAIL, "  ", "TOUR 专题1-x-y: 真题演练与错因回看"]) == [
        EVIDENCE_TAIL
    ]


def test_sanitize_keywords_empty_list():
    assert sanitize_keywords([]) == []


# ---------------------------------------------------------------------------
# WT334 · plan 链路 subject 的内部 token 残留：feature_tour S7 以
# f"TOUR科目-{run}" 填计划 subject（subject 参与 uq_plans_user_sprint_goal_active
# 唯一键，token 是评测合法去重手段），plan 详情/日程推荐文案/Aurora 简报等展示面
# 原样透出。形态与任务标题的「专题N-…: 尾」不同：TAG 直接贴「科目/Subject」，
# 后跟唯一性 token 段，无语义尾。
# ---------------------------------------------------------------------------

from app.services.galaxy.title_sanitizer import clean_display_subject

EVIDENCE_SUBJECT = "TOUR科目-d91d5df0-10-5dc70d"


class TestSubjectTokenForms:
    def test_bare_subject_token_drops_to_empty(self):
        """纯 token 科目 → 空串，调用方走「无科目」文案兜底。"""
        assert clean_display_subject(EVIDENCE_SUBJECT) == ""
        assert strip_internal_tokens(EVIDENCE_SUBJECT) == ""

    def test_embedded_subject_token_stripped_from_stored_copy(self):
        dirty = f"小明，今天先做好这 7 件事，{EVIDENCE_SUBJECT} 的第一步就稳下来了。"
        cleaned = strip_internal_tokens(dirty)
        assert "TOUR科目" not in cleaned
        assert "d91d5df0" not in cleaned and "5dc70d" not in cleaned
        assert "第一步就稳下来了" in cleaned

    def test_normal_subject_zero_rewrite(self):
        for clean in (
            "离散数学",
            "高等数学",
            "计算机网络",
            "AI科目-期末",
            "CS科目-exam1",
            "TOUR 科目",
            "business Subject",
            "IT科目-2024-2025",
        ):
            assert clean_display_subject(clean) == clean, clean

    def test_none_and_empty(self):
        assert clean_display_subject(None) == ""
        assert clean_display_subject("") == ""

    def test_subject_form_alone_does_not_hijack_normal_titles(self):
        """科目形态扩展不得波及 wt330 已固化的标题清洗行为。"""
        assert strip_internal_tokens(EVIDENCE_TITLE) == EVIDENCE_TAIL
        assert clean_display_title("数据结构复习 — 二叉树专题") == "数据结构复习 — 二叉树专题"

    def test_mixed_topic_and_subject_blocks(self):
        dirty = f"TOUR 专题2-d91d5df0-3-ef4567: {EVIDENCE_SUBJECT}"
        assert strip_internal_tokens(dirty) == ""
