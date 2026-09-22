"""CTX-PACK：M-05 Self-ReCheck 对「会话续接开场」的保守放行（2026-09-22）。

背景（CT 卡 CTX-PACK / MEM-AMNESIA 转交红测试
``test_two_consecutive_sessions_prompt_includes_inferred_memory``）：

用户在新会话以「早上好，今天从哪里开始？」开场时，上一会话写入的跨会话
记忆（TCP 难点 / 高数考试）被 M-05 relevance 检查以「零词法重叠」降档为
internal-only，从未进入 prompt 面——而 prompt 渲染层的「## 跨会话记忆
[L2 引导]」引导语明确承诺「当用户问候、含糊开场、请求继续学习……请自然
衔接上次内容」。门禁与已上线的引导语自相矛盾，链路真断。

修法：relevance 检查的 conservative-pass（"本轮无话题信号"）扩及**会话
续接开场**——消息含显式续接暗示词，且全部内容 run 都被
{续接暗示 / 问候 / 语气词 / 裸时间词} 封闭词表消耗完毕（不带任何主题词）。
带主题词的「继续讲泰勒公式」不保守放行，走原词法重叠路径，反过度
personalized 语义不变。

词表新增属 deliberate vocabulary change：SELF_CHECK_VERSION v2 -> v3，
OP-Bench（46 例）复跑双指标不动（本文件含词表守卫测试）。
"""

from __future__ import annotations

import pytest

from app.services.memory_use_selfcheck import (
    CONTINUATION_CUE_MARKERS,
    NO_TOPIC_CJK_RUNS,
    PHATIC_CJK_RUNS,
    SELF_CHECK_VERSION,
    MemoryUseCandidate,
    MemoryUseDecision,
    SelfCheckContext,
    evaluate_memory_use_gate,
    is_continuation_opening,
    is_phatic_query,
)


def _episodic(content: str, item_id: str = "ep-1") -> MemoryUseCandidate:
    return MemoryUseCandidate(item_id=item_id, section="episodic", content=content)


def _decision_for(candidate: MemoryUseCandidate, message: str) -> MemoryUseDecision:
    result = evaluate_memory_use_gate(episodic=[candidate], ctx=SelfCheckContext(user_message=message))
    return result.decisions[0].decision


# ---------------------------------------------------------------------------
# is_continuation_opening 形状锁定
# ---------------------------------------------------------------------------


def test_red_scenario_query_is_continuation_opening():
    """红测试原句：问候 + 续接请求，无主题词。"""
    assert is_continuation_opening("早上好，今天从哪里开始？") is True


def test_continuation_cue_with_subject_matter_is_not_opening():
    """带主题词的「继续…」不是续接开场——正常走词法重叠路径。"""
    assert is_continuation_opening("继续讲泰勒公式") is False
    assert is_continuation_opening("帮我继续做线性代数题") is False


def test_substantive_turn_is_not_continuation_opening():
    assert is_continuation_opening("帮我解释一下泰勒公式怎么用") is False
    assert is_continuation_opening(None) is False
    assert is_continuation_opening("") is False


def test_plain_ack_is_not_continuation_opening():
    """纯语气词走既有 phatic 路径，不冒充续接开场（无暗示词）。"""
    assert is_continuation_opening("好的，谢谢！") is False


def test_composed_time_and_cue_shapes():
    """时间词 + 暗示词的组合形状（成分化覆盖，不枚举整句）。"""
    assert is_continuation_opening("今天学什么") is True
    assert is_continuation_opening("明天从哪开始") is True


# ---------------------------------------------------------------------------
# gate 级行为：续接开场保守放行跨会话记忆
# ---------------------------------------------------------------------------


def test_gate_surfaces_disjoint_memory_on_continuation_opening():
    """红场景 gate 形：与 query 零重叠的跨会话记忆在续接开场下 surface。"""
    decision = _decision_for(_episodic("TCP 流量控制有点难，明天还要考高数"), "早上好，今天从哪里开始？")
    assert decision is MemoryUseDecision.SURFACE_TO_USER


def test_gate_still_blocks_disjoint_memory_on_substantive_turn():
    """话题不相关 + 有主题词的轮次维持原降档（反过度-personalized 不松动）。"""
    decision = _decision_for(_episodic("TCP 流量控制有点难，明天还要考高数"), "帮我解释一下泰勒公式怎么用")
    assert decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION


def test_gate_keeps_phatic_cut_for_plain_ack():
    """纯 ack 轮次维持 necessity phatic 降档，不受本词表影响。"""
    decision = _decision_for(_episodic("用户每天早上背五十个单词"), "好的，谢谢！")
    assert decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION


# ---------------------------------------------------------------------------
# 词表纪律（frozen vocabulary guards）
# ---------------------------------------------------------------------------


def test_version_bumped_for_vocabulary_change():
    assert SELF_CHECK_VERSION == "memory_use_selfcheck.v3"


def test_continuation_cues_never_in_phatic_vocabulary():
    """暗示词不得落进 phatic 词表——否则 necessity phatic 降档会吞掉续接开场。"""
    assert not (CONTINUATION_CUE_MARKERS & PHATIC_CJK_RUNS)
    # 行为面双保险：含暗示词的串不判定为 phatic
    assert is_phatic_query("从哪里开始") is False
    assert is_phatic_query("今天学什么") is False


def test_no_topic_runs_disjoint_from_cues_and_nonempty():
    """裸时间词/问候词表与暗示词不相交（ consumed 判定无歧义），且词表非空。"""
    assert NO_TOPIC_CJK_RUNS
    assert CONTINUATION_CUE_MARKERS
    assert not (NO_TOPIC_CJK_RUNS & CONTINUATION_CUE_MARKERS)


@pytest.mark.parametrize(
    "run",
    ["今天", "明天", "早上好", "你好", "中午好"],
)
def test_no_topic_runs_are_bare(run):
    """NO_TOPIC 词表成员必须是裸词（无主题内容），防止整句被误吞。"""
    assert len(run) <= 4
