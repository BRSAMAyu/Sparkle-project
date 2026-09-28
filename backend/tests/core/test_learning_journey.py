"""V4-U10 · learning-journey 契约层守卫（纯函数面，每验收一正一反可失败）。

覆盖（卡 V4-U10 验收三条 + 边界面）：
1. **不会从目标跳入无上下文的工具空页** → 旅程段映射保守（脏 stage → practice，
   绝不把未到检验的用户推到检验空页）+ 检验入口证据门（不支持 → HOLD）；
2. **答案不泄漏到检验用户可读状态** → 判分载荷零答案材料（正：判分成立；
   反：载荷内出现 independent_check 节点/答案键 → 出口探针 raise）+ 红化
   消费 I07 权威（键集钉死不漂移）；
3. **真实文件/图片失败无伪造解析，来源版本正确** → failed/unsupported 构造期
   拒绝携带文本（正：诚实结果可构造；反：带 text 即 ValueError）+ 版本
   新鲜门（正：一致放行；反：陈旧声明拒绝）。
"""

from __future__ import annotations

import pytest

from app.core.hybrid_policy import (
    GOAL_PURPOSE_BLOCK_KEY,
    HINT_FULL,
    HYBRID_POLICY_VERSION,
    SCAFFOLD_STAGE_ATTEMPT,
    SCAFFOLD_STAGE_EXAMPLE,
    SCAFFOLD_STAGE_INDEPENDENT_CHECK,
    contains_independent_check_answer,
)
from app.core.learning_journey import (
    CHECK_REASON_CORRECT,
    CHECK_REASON_HOLD_EVIDENCE,
    LEARNING_JOURNEY_SCHEMA_VERSION,
    PARSE_FAILED,
    PARSE_PARSED,
    PARSE_PENDING,
    PARSE_UNSUPPORTED,
    JourneySourceRef,
    MaterialParseOutcome,
    SourceVersionMismatchError,
    assert_client_payload_clean,
    ensure_source_version_current,
    grade_independent_check,
    journey_segment_for_scaffold,
    redact_for_client,
    request_independent_check,
)

_CHECK_AUTHORITY = {
    # I07 约定：检验权威子结构自带 kind 标记（红化触发面）；判分权威 = answer
    # 单键（I07 冻结答案键集成员，红化门覆盖），留在服务端 guide_json。
    "kind": "independent_check",
    "question": "独立解释：为什么滑动摩擦力与接触面积无关？",
    "answer": "压力决定摩擦力，而非面积",
    "explanation": "因为摩擦力公式 μN 中不含面积项。",
}


# ---------------------------------------------------------------------------
# 验收1 面：旅程段映射与检验入口证据门
# ---------------------------------------------------------------------------


def test_journey_segment_maps_scaffold_check_to_check_segment():
    # 正：检验段用户主操作落在检验段（I07 链终点）。
    assert journey_segment_for_scaffold(SCAFFOLD_STAGE_INDEPENDENT_CHECK) == "independent_check"


def test_journey_segment_dirty_stage_falls_back_to_practice_never_check():
    # 反（可失败面）：脏/未知 stage 绝不映射到检验段（检验空页不可能由脏态跳入）。
    assert journey_segment_for_scaffold("garbage_stage") == "practice"
    assert journey_segment_for_scaffold("") == "practice"


def test_request_check_advances_with_evidence():
    decision, hold = request_independent_check(
        stage=SCAFFOLD_STAGE_ATTEMPT, hint_level=HINT_FULL, evidence_supported=True
    )
    assert decision.stage == SCAFFOLD_STAGE_INDEPENDENT_CHECK
    assert hold is None


def test_request_check_without_evidence_holds_and_never_reaches_check():
    # 反（可失败面）：证据不支持 → 原地 + 类型化 HOLD；绝不放行检验。
    decision, hold = request_independent_check(
        stage=SCAFFOLD_STAGE_ATTEMPT, hint_level=HINT_FULL, evidence_supported=False
    )
    assert decision.stage == SCAFFOLD_STAGE_ATTEMPT  # 阶段不回退不跳进
    assert hold == CHECK_REASON_HOLD_EVIDENCE


# ---------------------------------------------------------------------------
# 验收2 面：判分与答案泄漏
# ---------------------------------------------------------------------------


def test_grade_independent_check_correct_on_normalized_match():
    result = grade_independent_check(_CHECK_AUTHORITY, "  压力决定摩擦力，而非面积 \n")
    assert result.graded is True
    assert result.correct is True
    assert result.reason == CHECK_REASON_CORRECT


def test_grade_independent_check_incorrect_without_grading_answer_back():
    result = grade_independent_check(_CHECK_AUTHORITY, "接触面积越大摩擦力越大")
    assert result.graded is True
    assert result.correct is False
    payload = result.to_client_payload()
    # 反（可失败面）：任何反馈都不含答案/解析材料；判分权威原样留在服务端。
    serialized = str(payload)
    assert "压力决定摩擦力" not in serialized
    assert "μN" not in serialized
    assert "answer" not in payload


def test_client_payload_probe_raises_on_leaked_answer_node():
    # 反（可失败面）：载荷里出现 independent_check 节点 + 答案键 → 出口探针 raise。
    leaked = {"check": {"independent_check": True, "answer": "压力决定摩擦力"}}
    with pytest.raises(ValueError, match="leaks"):
        assert_client_payload_clean(leaked)


def test_client_payload_probe_passes_clean_journey_view():
    clean_view = {
        "schema_version": LEARNING_JOURNEY_SCHEMA_VERSION,
        "goal": {"task_id": "t1", "title": "力学单元巩固"},
        "errors": [{"id": "e1", "question_text": "斜面上物体受力？"}],
    }
    assert_client_payload_clean(clean_view)  # 不 raise
    assert not contains_independent_check_answer(clean_view)


def test_redact_for_client_delegates_to_i07_authority_key_set():
    # 消费 I07 权威：题目示例与检验答案同载荷时，红化剥除检验子树答案键，
    # 非标记节点的用户自有材料（error_records.correct_answer）不动。
    payload = {
        "example": {"kind": "independent_check", "answer": "答案是X", "question": "Q?"},
        "error": {"correct_answer": "用户自有错题答案", "question_text": "错题面"},
    }
    clean, removed = redact_for_client(payload)
    assert removed == ("example.answer",)
    assert clean["example"]["question"] == "Q?"
    assert clean["error"]["correct_answer"] == "用户自有错题答案"


def test_policy_block_check_authority_redacted_via_kind_marker():
    # I07 约定回归锚：策略块 independent_check 子结构带 kind 标记 → 整树答案键
    # 在投影前剥除，题面保留（判分权威原地留在服务端 guide_json）。
    guide = {
        GOAL_PURPOSE_BLOCK_KEY: {
            "schema_version": HYBRID_POLICY_VERSION,
            "goal_purpose": "mastery",
            "human_required": True,
            "independent_check": dict(_CHECK_AUTHORITY),
        }
    }
    clean, removed = redact_for_client(guide)
    inner = clean[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]
    assert "answer" not in inner and "explanation" not in inner
    assert inner["question"] == _CHECK_AUTHORITY["question"]
    assert any("answer" in path for path in removed)


def test_grade_ungradeable_when_authority_incomplete():
    # 判分权威不完整（无任何预期答案）→ 不猜不伪造判分。
    result = grade_independent_check({"question": "Q?"}, "任意答案")
    assert result.graded is False
    assert result.correct is None


# ---------------------------------------------------------------------------
# 验收3 面：解析诚实与来源版本
# ---------------------------------------------------------------------------


def test_material_parse_outcome_failed_honest_without_text():
    # 正：失败解析 = 状态 + 手输替代标记，无任何文本。
    outcome = MaterialParseOutcome(status=PARSE_FAILED, text=None, reason="ocr_timeout", manual_input_required=True)
    assert outcome.parsed_ok is False
    assert outcome.to_dict()["text"] is None
    assert outcome.to_dict()["manual_input_required"] is True


def test_material_parse_outcome_failed_rejects_fabricated_text():
    # 反（可失败面）：失败状态带"解析文本" → 构造期 ValueError（伪造解析不可能存在）。
    with pytest.raises(ValueError, match="no fake parse"):
        MaterialParseOutcome(status=PARSE_FAILED, text="假装识别出了全文", manual_input_required=True)


def test_material_parse_outcome_parsed_requires_text():
    with pytest.raises(ValueError, match="requires non-empty text"):
        MaterialParseOutcome(status=PARSE_PARSED, text=None)


def test_material_parse_outcome_unsupported_and_pending_and_manual_faces():
    unsupported = MaterialParseOutcome(
        status=PARSE_UNSUPPORTED, text=None, reason="ocr_unavailable", manual_input_required=True
    )
    assert unsupported.to_dict()["manual_input_required"] is True
    pending = MaterialParseOutcome(status=PARSE_PENDING, text=None, reason="document_processing")
    assert pending.to_dict()["text"] is None
    manual = MaterialParseOutcome(status="manual", text="用户手输的题目文本")
    assert manual.to_dict()["manual_input_required"] is False
    with pytest.raises(ValueError, match="out of vocabulary"):
        MaterialParseOutcome(status="magically_parsed")


def test_source_ref_requires_id_and_version():
    with pytest.raises(ValueError, match="source_version"):
        JourneySourceRef(source_id="f1", source_version="   ")
    ref = JourneySourceRef(source_id="f1", source_version="2026-09-28T10:00:00", fragment_anchor="para-3")
    assert ref.to_dict()["fragment_anchor"] == "para-3"


def test_ensure_source_version_current_passes_and_rejects_stale_claim():
    # 正：声明版本 = 当前版本 → 放行并返回当前版本。
    assert (
        ensure_source_version_current(current_version="2026-09-28T10:00:00", claimed_version="2026-09-28T10:00:00")
        == "2026-09-28T10:00:00"
    )
    # 反（可失败面）：陈旧声明 → SourceVersionMismatchError（不臆测刷新）。
    with pytest.raises(SourceVersionMismatchError):
        ensure_source_version_current(current_version="2026-09-28T12:00:00", claimed_version="2026-09-28T10:00:00")


# ---------------------------------------------------------------------------
# 权威对齐（不造第二权威）
# ---------------------------------------------------------------------------


def test_alignment_with_i07_scaffold_and_policy_authority():
    # 旅程检验段与 I07 脚手架链终点同词；策略块版本同源（消费不复制）。
    guide = {
        GOAL_PURPOSE_BLOCK_KEY: {
            "schema_version": HYBRID_POLICY_VERSION,
            "goal_purpose": "mastery",
            "human_required": True,
            "independent_check": dict(_CHECK_AUTHORITY),
        }
    }
    clean, removed = redact_for_client(guide)
    assert f"{GOAL_PURPOSE_BLOCK_KEY}.independent_check.answer" in removed
    assert clean[GOAL_PURPOSE_BLOCK_KEY]["independent_check"]["question"] == _CHECK_AUTHORITY["question"]
    assert SCAFFOLD_STAGE_EXAMPLE == "example"
