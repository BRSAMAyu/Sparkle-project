"""V3-FIX-146/147 · 否定窗口无标点串染 + 英文无撇号缩写否定漏判（红测先行）.

wt450 审查轮 CONFIRMED（DYNAMIC_ISSUES V3-FIX-146 P3 / V3-FIX-147 P3）：

- FIX-146：``_clause_spans`` 按标点切子句，无标点长句 = 单一子句，首个否定
  标记毒化其后全部词牌——「不是没时间是太难了」（无逗号）→ ``太`` 难了`` 与
  ``没时间`` 双双判否定、正向证据清零（utterance_matches=None），chat 面
  FIX-49 词牌门吞掉真实摩擦自报。修复 = 子句级否定作用域：一标记至多否定
  其**最近的一个**后继词牌出现；落在词牌出现内部的否定标记是内容不是算子。
- FIX-147：``FRICTION_NEGATION_RE_EN`` 只收撇号形（don't/can't/won't...），
  漏高频口语无撇号拼写 dont/cant/wont——「i dont feel burnout」错误出面
  act/energy（侵入向）。修复 = ``n'?t`` 词形族（撇号形保持覆盖）。

契约锁（可证伪判据来自 wt450 /tmp 探针，另含自造对照与反例）：
1. 无标点长句与带逗号对照同判（太难了正向 + 没时间否定）；
2. 无撇号缩写形与撇号形同判（否定注记 + 非 act 出面）；
3. wt428 既有回归底线：带标点否定、词牌内否定字、wordmark-internal no
   全部行为不变。
"""

from __future__ import annotations

import pytest

from app.aurora.friction_diagnosis import (
    FRICTION_NEGATION_RE_EN,
    FrictionDiagnosisInput,
    diagnose_friction,
)

# ---------------------------------------------------------------------------
# FIX-146 · 无标点长句否定串染
# ---------------------------------------------------------------------------


class TestUnpunctuatedNegationPoisoning:
    def test_unpunctuated_long_sentence_matches_punctuated_control(self) -> None:
        """红证（wt450 探针）：无逗号 → 双词牌全灭、utterance_matches=None。

        修后与带逗号对照同判：太难了正向驱动（act/difficulty）、没时间否定注记。
        """
        unpunctuated = diagnose_friction(FrictionDiagnosisInput(utterance="不是没时间是太难了"))
        punctuated = diagnose_friction(FrictionDiagnosisInput(utterance="不是没时间，是太难了"))
        assert unpunctuated.annotations.get("utterance_matches") == ["difficulty:太难了"], (
            "无标点长句的太字面正向证据不得被首个否定标记串染清零"
        )
        assert "time:没时间" in (unpunctuated.annotations.get("utterance_negated_matches") or [])
        assert (unpunctuated.outcome, unpunctuated.friction_type) == (
            punctuated.outcome,
            punctuated.friction_type,
        ), "无标点与带逗号对照必须同判"
        assert (unpunctuated.outcome, unpunctuated.friction_type) == ("act", "difficulty")

    def test_post_positioned_negation_keeps_leading_wordmark(self) -> None:
        """后置否定（wt450 探针场景 5）：「太难了不是没时间」→ 太难了正向。"""
        result = diagnose_friction(FrictionDiagnosisInput(utterance="太难了不是没时间"))
        assert "difficulty:太难了" in (result.annotations.get("utterance_matches") or [])
        assert "time:没时间" in (result.annotations.get("utterance_negated_matches") or [])
        assert result.outcome == "act"

    def test_wordmark_internal_negation_char_not_leak_to_later_wordmark(self) -> None:
        """词牌内否定字是内容不是算子：「没时间太难了」的「没」不得否定太难了。"""
        result = diagnose_friction(FrictionDiagnosisInput(utterance="没时间太难了"))
        assert "time:没时间" in (result.annotations.get("utterance_matches") or [])
        assert "difficulty:太难了" in (result.annotations.get("utterance_matches") or [])

    def test_negated_annotation_remains_auditable(self) -> None:
        """无标点修复不丢否定注记（观察档可审计，零证据权重）。"""
        result = diagnose_friction(FrictionDiagnosisInput(utterance="不是没时间是太难了"))
        assert result.annotations.get("utterance_negated_matches") == ["time:没时间"]


class TestNegationRegressionFloor:
    """wt428 既有回归底线：带标点正常 case 不得被作用域收紧改坏。"""

    @pytest.mark.parametrize(
        ("utterance", "negated_phrase"),
        [
            ("不是没时间，是效率低", "time:没时间"),
            ("这次不太难了，其实挺顺利的", "difficulty:太难了"),
            ("不像之前那么看不懂了，好多了", "knowledge:看不懂"),
        ],
    )
    def test_punctuated_negations_unchanged(self, utterance: str, negated_phrase: str) -> None:
        result = diagnose_friction(FrictionDiagnosisInput(utterance=utterance))
        assert negated_phrase in (result.annotations.get("utterance_negated_matches") or [])
        assert negated_phrase not in (result.annotations.get("utterance_matches") or [])
        assert result.outcome != "act"

    def test_genuine_reports_with_clause_negation_unaffected(self) -> None:
        result = diagnose_friction(FrictionDiagnosisInput(utterance="完全没时间，挤不出时间"))
        assert "time:没时间" in (result.annotations.get("utterance_matches") or [])
        assert result.friction_type == "time"

    def test_wordmark_internal_no_not_self_negating(self) -> None:
        result = diagnose_friction(FrictionDiagnosisInput(utterance="i have no time for practice"))
        assert "time:no time" in (result.annotations.get("utterance_matches") or [])
        assert result.outcome == "act"

    def test_negated_only_still_never_acts(self) -> None:
        result = diagnose_friction(FrictionDiagnosisInput(utterance="不是没时间，是效率低"))
        assert result.outcome in ("ask", "no_action", "unknown")

    def test_negation_path_deterministic(self) -> None:
        a = diagnose_friction(FrictionDiagnosisInput(utterance="不是没时间是太难了")).to_dict()
        b = diagnose_friction(FrictionDiagnosisInput(utterance="不是没时间是太难了")).to_dict()
        assert a == b


# ---------------------------------------------------------------------------
# FIX-147 · 英文无撇号缩写否定漏判
# ---------------------------------------------------------------------------


class TestApostropheLessNegationForms:
    def test_dont_feel_burnout_not_invasive_act(self) -> None:
        """红证（wt450 探针）：「i dont feel burnout」修前 act/energy 侵入出面。"""
        result = diagnose_friction(FrictionDiagnosisInput(utterance="i dont feel burnout"))
        assert result.outcome != "act", "无撇号否定形不得驱动 act 出面"
        assert "energy: burnout" in (result.annotations.get("utterance_negated_matches") or [])
        assert "energy: burnout" not in (result.annotations.get("utterance_matches") or [])

    @pytest.mark.parametrize(
        ("utterance", "negated_phrase"),
        [
            ("i dont feel burnout", "energy: burnout"),
            ("i dont think this is too hard", "difficulty:too hard"),
            ("i cant do this it is too hard", "difficulty:too hard"),
            ("this isnt too hard honestly", "difficulty:too hard"),
            ("it doesnt seem too hard now", "difficulty:too hard"),
            ("i wont claim it is too hard", "difficulty:too hard"),
            ("i shouldnt say this but it is too hard", "difficulty:too hard"),
        ],
    )
    def test_negation_forms_negate_following_wordmark(self, utterance: str, negated_phrase: str) -> None:
        result = diagnose_friction(FrictionDiagnosisInput(utterance=utterance))
        assert negated_phrase in (result.annotations.get("utterance_negated_matches") or []), (
            f"{utterance!r} 的词牌必须判否定"
        )
        assert negated_phrase not in (result.annotations.get("utterance_matches") or [])
        assert result.outcome != "act"

    def test_apostrophe_forms_still_covered(self) -> None:
        """撇号形保持（回归锁）：正则族对撇号/无撇号两形同覆盖。"""
        result = diagnose_friction(FrictionDiagnosisInput(utterance="i don't feel burnout"))
        assert "energy: burnout" in (result.annotations.get("utterance_negated_matches") or [])
        assert result.outcome != "act"
        for form in (
            "don't",
            "doesn't",
            "didn't",
            "isn't",
            "wasn't",
            "aren't",
            "weren't",
            "can't",
            "cannot",
            "couldn't",
            "won't",
            "shouldn't",
            # FIX-147 无撇号族
            "dont",
            "doesnt",
            "didnt",
            "isnt",
            "wasnt",
            "arent",
            "werent",
            "cant",
            "couldnt",
            "wont",
            "shouldnt",
        ):
            assert FRICTION_NEGATION_RE_EN.search(f"i {form} go") is not None, (
                f"否定形 {form!r} 必须被 FRICTION_NEGATION_RE_EN 覆盖"
            )
        # 词边界守卫：无撇号形不得子串误伤（noted/another/wonton 类）
        assert FRICTION_NEGATION_RE_EN.search("the wonton soup noted another no show") is None or all(
            m.group() in ("no",) for m in FRICTION_NEGATION_RE_EN.finditer("the wonton soup noted another no show")
        ), "词边界守卫保持：wonton/noted/another 不得误伤"

    def test_positive_english_reports_unaffected(self) -> None:
        assert diagnose_friction(FrictionDiagnosisInput(utterance="i feel burnout")).outcome == "act"
        assert (
            FRICTION_NEGATION_RE_EN.search("i have no idea but it is notable") is not None
        ), "词边界守卫保持：no/not 不做子串误伤"


# ---------------------------------------------------------------------------
# 双修复交集：英文无标点长句（FIX-146 场景 6）
# ---------------------------------------------------------------------------


def test_en_unpunctuated_multiclause_never_acts_on_negated_only() -> None:
    """「i dont have time it is too hard」：dont 否定最近后继词牌（too hard），
    无正向词牌 → 不出面 act（保守方向），否定注记可审计。"""
    result = diagnose_friction(FrictionDiagnosisInput(utterance="i dont have time it is too hard"))
    assert "difficulty:too hard" in (result.annotations.get("utterance_negated_matches") or [])
    assert result.outcome != "act"
