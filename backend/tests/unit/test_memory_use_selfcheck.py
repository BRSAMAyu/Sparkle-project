"""M-05 · Over-personalization Self-ReCheck —— 检查器单元测试（红→绿基线）。

纯函数面：四检查（relevance/necessity/repetition/sycophancy）× 两档用途
（surface_to_user / use_for_internal_decision）× 封闭词表冻结 × fast-model
钩子契约（默认关；只收紧不放松）。

与 M-03/C-03 的分工（守卫对象）：它们是候选池前的硬过滤（能不能进来），
本模块是合法候选在输出装配面的使用自检（该不该用/该不该说出来）。
真实 LLM 零依赖——fast-model 路径全部用注入 mock 验证契约。
"""

from __future__ import annotations

import pytest

from app.core.memory_constants import PREFERENCE_KEYS
from app.services.memory_use_selfcheck import (
    AFFIRMATIVE_VALUE_MARKERS,
    AGREEMENT_BIAS_PREF_KEYS,
    DUPLICATE_JACCARD_RATIO,
    FAST_MODEL_REASONS,
    META_PREF_KEYS,
    MemoryUseCandidate,
    MemoryUseDecision,
    SELF_CHECK_REASONS,
    SELF_CHECK_SECTIONS,
    SELF_CHECK_VERSION,
    SELFCHECK_PAYLOAD_KEYS,
    SelfCheckContext,
    USE_CHECK_KINDS,
    UseCheckKind,
    evaluate_memory_use_gate,
    is_phatic_query,
    lexical_tokens,
    run_memory_use_selfcheck,
)


def _ep(item_id: str, content: str) -> MemoryUseCandidate:
    return MemoryUseCandidate(item_id=item_id, section="episodic", content=content)


def _pref(item_id: str, pref_key: str, value: str) -> MemoryUseCandidate:
    return MemoryUseCandidate(item_id=item_id, section="preferences", content=value, pref_key=pref_key)


def _goal(item_id: str, title: str) -> MemoryUseCandidate:
    return MemoryUseCandidate(item_id=item_id, section="goals", content=title)


# ---------------------------------------------------------------------------
# 1. 封闭词表冻结（新增任何 code 必须同步版本号与冻结测试）
# ---------------------------------------------------------------------------


def test_reason_vocabulary_is_frozen():
    assert SELF_CHECK_REASONS == frozenset(
        {
            "selfcheck:irrelevant_to_query",
            "selfcheck:phatic_query",
            "selfcheck:echoed_in_query",
            "selfcheck:recently_surfaced",
            "selfcheck:duplicate_in_pack",
            "selfcheck:agreement_bias_risk",
        }
    )


def test_fast_model_reason_vocabulary_is_frozen_and_disjoint_from_rules():
    assert FAST_MODEL_REASONS == frozenset({"selfcheck:fm_semantic_irrelevant", "selfcheck:fm_agreement_bias"})
    assert FAST_MODEL_REASONS & SELF_CHECK_REASONS == frozenset()


def test_check_kinds_evaluation_order_is_pinned():
    assert tuple(USE_CHECK_KINDS) == (
        UseCheckKind.RELEVANCE,
        UseCheckKind.NECESSITY,
        UseCheckKind.REPETITION,
        UseCheckKind.SYCOPHANCY,
    )


def test_sections_vocabulary_is_frozen():
    assert SELF_CHECK_SECTIONS == ("preferences", "goals", "episodic")


def test_meta_pref_keys_are_subset_of_writer_vocabulary():
    """M-05 的 meta 分类必须落在 memory_constants.PREFERENCE_KEYS（写方词表）
    之内——写方删 key / 改名时本守卫转红，防止 meta 白名单漂移成死词表。"""
    assert META_PREF_KEYS <= PREFERENCE_KEYS, f"meta keys outside writer vocab: {META_PREF_KEYS - PREFERENCE_KEYS}"
    assert AGREEMENT_BIAS_PREF_KEYS <= META_PREF_KEYS


def test_metric_payload_keys_are_frozen():
    assert tuple(SELFCHECK_PAYLOAD_KEYS) == (
        "version",
        "input_count",
        "surfaced_count",
        "internal_only_count",
        "check_counts",
        "reason_counts",
    )


# ---------------------------------------------------------------------------
# 2. 词法层（CJK bigram + ASCII word）与 phatic 判定
# ---------------------------------------------------------------------------


def test_lexical_tokens_cjk_bigrams_and_ascii_words():
    tokens = lexical_tokens("线性代数 linear algebra 101")
    assert "线性" in tokens and "代数" in tokens
    assert "linear" in tokens and "algebra" in tokens and "101" in tokens
    assert all(len(t) >= 1 for t in tokens)
    assert lexical_tokens("  ") == frozenset()


def test_phatic_detection_cjk_and_ascii():
    assert is_phatic_query("好的，谢谢！")
    assert is_phatic_query("嗯嗯")
    assert is_phatic_query("ok")
    assert is_phatic_query("thank you")
    assert not is_phatic_query("好的，那我们继续学线性代数吧")
    assert not is_phatic_query("帮我解释一下泰勒公式")
    assert not is_phatic_query("I keep failing dynamic programming problems")
    assert not is_phatic_query(None)
    assert not is_phatic_query("")


# ---------------------------------------------------------------------------
# 3. relevance —— 无关记忆可召回但不进入 surface 档
# ---------------------------------------------------------------------------


def test_relevance_blocks_topically_disjoint_episodic():
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户养了一只猫，名字叫雪球")],
        ctx=SelfCheckContext(user_message="帮我解释一下泰勒公式怎么用"),
    )
    decision = result.decisions[0]
    assert decision.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert decision.flag is not None
    assert decision.flag.check == "relevance"
    assert decision.flag.reason == "selfcheck:irrelevant_to_query"


def test_relevance_passes_on_token_overlap():
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户明天上午有高数期中考试")],
        ctx=SelfCheckContext(user_message="高数期中考试之前我该怎么复习"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER
    assert "e1" in result.surfaced_ids("episodic")


def test_relevance_meta_pref_passes_without_overlap():
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "ai_verbosity", "concise")],
        ctx=SelfCheckContext(user_message="量子隧穿效应是什么"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_relevance_pref_key_tokens_count_as_content_for_overlap():
    """pref_key 本身是内容面（用户以 key 域提及域时也应放行）。"""
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "study_time_preference", "晚上十点后学习效率最高")],
        ctx=SelfCheckContext(user_message="study_time_preference 是什么意思"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_relevance_unconstrained_query_conservative_pass():
    """无当前消息（非对话驱动面，如 capsule/proactive）→ 不凭空砍
    （对齐 M-03「unconstrained 维度保守放行」法）。"""
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户参加了学校的机器人社团")],
        ctx=SelfCheckContext(),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_relevance_safety_pin_bypasses_topical_checks():
    """安全钉（过敏/药物类事实）不受词法相关性误伤——把它挡在
    surface 外的代价是物理伤害，词法 gap 不允许造成这种回归。"""
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户对花生过敏，严重时会休克")],
        ctx=SelfCheckContext(user_message="坚果类零食推荐几个"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER
    # phatic turn 也不豁免安全钉
    result2 = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户对花生过敏，严重时会休克")],
        ctx=SelfCheckContext(user_message="谢谢！"),
    )
    assert result2.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


# ---------------------------------------------------------------------------
# 4. necessity —— phatic 轮与 echo 轮不需要 surface
# ---------------------------------------------------------------------------


def test_necessity_blocks_all_topical_memory_on_phatic_turn():
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户下周三有数据结构期末考试")],
        ctx=SelfCheckContext(user_message="好的，谢谢！"),
    )
    decision = result.decisions[0]
    assert decision.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    # phatic 轮 relevance 无话题信号 → 不定 → necessity 独占归因
    assert decision.flag.check == "necessity"
    assert decision.flag.reason == "selfcheck:phatic_query"


def test_necessity_meta_pref_survives_phatic_turn():
    """风格/沟通类偏好塑造每轮回复形态（含短应答），不因 phatic 降档。"""
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "ai_verbosity", "concise")],
        ctx=SelfCheckContext(user_message="谢谢！"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_necessity_blocks_echo_of_user_statement():
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户下周三有数据结构期末考试")],
        ctx=SelfCheckContext(user_message="我下周三有数据结构期末考试，好紧张啊"),
    )
    decision = result.decisions[0]
    assert decision.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert decision.flag.reason == "selfcheck:echoed_in_query"


def test_necessity_partial_echo_still_surfaces():
    """记忆比用户刚说的话多出实质内容 → 不是回声，放行。"""
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户下周三有数据结构期末考试，正在复习链表章节")],
        ctx=SelfCheckContext(user_message="我下周三有数据结构期末考试"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


# ---------------------------------------------------------------------------
# 5. repetition —— 近期已 surface / 包内近重复
# ---------------------------------------------------------------------------


def test_repetition_blocks_recently_surfaced_memory():
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户在准备考研数学")],
        ctx=SelfCheckContext(
            user_message="考研数学帮我排一个复习时间表",
            recent_assistant_messages=("考虑到你正在准备考研数学，建议每天固定两小时",),
        ),
    )
    decision = result.decisions[0]
    assert decision.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert decision.flag.check == "repetition"
    assert decision.flag.reason == "selfcheck:recently_surfaced"


def test_repetition_checks_whole_window_any_turn():
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户报名了半程马拉松")],
        ctx=SelfCheckContext(
            user_message="半程马拉松之前怎么吃",
            recent_assistant_messages=("嗯嗯", "上次说到你报名了半程马拉松，训练计划我发你了", "好的"),
        ),
    )
    assert result.decisions[0].flag is not None
    assert result.decisions[0].flag.reason == "selfcheck:recently_surfaced"


def test_repetition_passes_when_window_empty():
    """窗口不可得（接线面暂无 assistant 历史）→ 检查休眠不误伤
    （known-boundary：跨会话 repetition 窗口语义见 REPORT）。"""
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户在准备考研数学")],
        ctx=SelfCheckContext(user_message="考研数学真题从哪年开始刷"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_repetition_meta_pref_exempt_for_style_consistency():
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "ai_verbosity", "concise")],
        ctx=SelfCheckContext(
            user_message="帮我总结这篇论文",
            recent_assistant_messages=("好的，我会保持 concise 的回答风格",),
        ),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_repetition_blocks_in_pack_near_duplicate_lower_priority():
    result = evaluate_memory_use_gate(
        episodic=[
            _ep("e-first", "用户开始每天背五十个英语单词了"),
            _ep("e-dup", "用户开始每天背五十个英语单词"),
        ],
        ctx=SelfCheckContext(user_message="英语单词背了几天了"),
    )
    first = next(d for d in result.decisions if d.candidate.item_id == "e-first")
    dup = next(d for d in result.decisions if d.candidate.item_id == "e-dup")
    assert first.decision is MemoryUseDecision.SURFACE_TO_USER
    assert dup.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert dup.flag is not None
    assert dup.flag.reason == "selfcheck:duplicate_in_pack"
    assert "e-first" in dup.flag.detail


def test_repetition_distinct_memories_not_flagged_as_duplicate():
    result = evaluate_memory_use_gate(
        episodic=[
            _ep("e1", "用户参加了校园摄影社"),
            _ep("e2", "用户在准备考研数学"),
        ],
        ctx=SelfCheckContext(user_message="考研数学和摄影社的时间冲突吗"),
    )
    assert result.internal_only_count == 0


# ---------------------------------------------------------------------------
# 6. sycophancy —— 认同偏好在求认同轮不得裹挟回答
# ---------------------------------------------------------------------------


def test_sycophancy_flags_agreement_bias_pref_on_validation_query():
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "feedback_style", "always encouraging")],
        ctx=SelfCheckContext(user_message="我觉得论文已经很好了，不用改了吧？"),
    )
    decision = result.decisions[0]
    assert decision.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert decision.flag.check == "sycophancy"
    assert decision.flag.reason == "selfcheck:agreement_bias_risk"


def test_sycophancy_requires_validation_cue():
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "feedback_style", "always encouraging")],
        ctx=SelfCheckContext(user_message="帮我看看这段代码哪里有bug"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_sycophancy_requires_affirmative_value():
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "feedback_style", "balanced")],
        ctx=SelfCheckContext(user_message="我是不是不用改了？"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_sycophancy_binds_only_agreement_bias_pref_class():
    """非认同类偏好（哪怕是 meta）不触发 sycophancy。"""
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "ai_verbosity", "concise")],
        ctx=SelfCheckContext(user_message="我的理解对吧？"),
    )
    assert result.decisions[0].decision is MemoryUseDecision.SURFACE_TO_USER


def test_sycophancy_cjk_value_markers():
    assert any("鼓励" == m or "鼓励" in m for m in AFFIRMATIVE_VALUE_MARKERS)
    result = evaluate_memory_use_gate(
        preferences=[_pref("p1", "coaching_style", "以鼓励和表扬为主")],
        ctx=SelfCheckContext(user_message="我这样的复习方法是不是没问题？"),
    )
    assert result.decisions[0].flag is not None
    assert result.decisions[0].flag.reason == "selfcheck:agreement_bias_risk"


# ---------------------------------------------------------------------------
# 7. 首失败独占归因（确定性指标；M-03 同法）
# ---------------------------------------------------------------------------


def test_first_failing_check_owns_attribution():
    """同时满足 relevance 失败与（假想的）其它失败时，只有 relevance 归因。
    用 relevance+repetition 双失败候选验证：relevance 先判，独占。"""
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户养了一只猫")],
        ctx=SelfCheckContext(
            user_message="泰勒公式怎么用",
            recent_assistant_messages=("你养了一只猫",),
        ),
    )
    decision = result.decisions[0]
    assert decision.flag is not None and decision.flag.check == "relevance"
    assert result.reason_counts == {"selfcheck:irrelevant_to_query": 1}


def test_counts_and_payload_are_consistent():
    result = evaluate_memory_use_gate(
        episodic=[
            _ep("e-irrelevant", "用户养了一只猫"),
            _ep("e-relevant", "用户明天有泰勒公式辅导课"),
        ],
        preferences=[_pref("p-meta", "ai_verbosity", "concise")],
        goals=[_goal("g1", "期末线性代数90分")],
        ctx=SelfCheckContext(user_message="泰勒公式和线性代数期末怎么复习"),
    )
    payload = result.to_metric_payload()
    assert set(payload) == set(SELFCHECK_PAYLOAD_KEYS)
    assert payload["version"] == SELF_CHECK_VERSION
    assert payload["input_count"] == 4
    assert payload["surfaced_count"] == result.surfaced_count
    assert payload["internal_only_count"] == result.internal_only_count
    assert payload["surfaced_count"] + payload["internal_only_count"] == payload["input_count"]
    assert sum(payload["reason_counts"].values()) == payload["internal_only_count"]


def test_empty_input_is_zero_cost():
    result = evaluate_memory_use_gate(ctx=SelfCheckContext(user_message="hi"))
    assert result.input_count == 0
    assert result.surfaced_count == 0
    assert result.decisions == []


# ---------------------------------------------------------------------------
# 8. fast-model 钩子（默认关；只收紧不放松；封闭 reason 强制）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_model_hook_tightens_surfaced_item():
    """钩子可以把规则放行的条目降档（语义相关性判定），reason 落封闭集。
    e1 与提问有一个共享 bigram（高数）→ 规则层放行，但语义上讲的是电影
    不是备考 —— fast-model 钩子的正是这种词法放行/语义不符的残余空间。"""

    async def hook(candidate, ctx):
        return "selfcheck:fm_semantic_irrelevant" if candidate.item_id == "e1" else None

    result = await run_memory_use_selfcheck(
        episodic=[
            _ep("e1", "用户看了电影星际穿越，对其中的高数彩蛋很好奇"),
            _ep("e2", "用户明天有高数期中考试"),
        ],
        ctx=SelfCheckContext(user_message="高数期中考试怎么复习"),
        fast_model_hook=hook,
    )
    downgraded = next(d for d in result.decisions if d.candidate.item_id == "e1")
    assert downgraded.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert downgraded.flag is not None
    assert downgraded.flag.reason == "selfcheck:fm_semantic_irrelevant"
    assert "e2" in result.surfaced_ids("episodic")


@pytest.mark.asyncio
async def test_fast_model_hook_never_resurrects():
    async def hook(candidate, ctx):
        return None

    result = await run_memory_use_selfcheck(
        episodic=[_ep("e1", "用户养了一只猫")],
        ctx=SelfCheckContext(user_message="泰勒公式怎么用"),
        fast_model_hook=hook,
    )
    assert result.decisions[0].decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION


@pytest.mark.asyncio
async def test_fast_model_hook_reason_must_be_in_closed_vocabulary():
    async def bad_hook(candidate, ctx):
        return "selfcheck:made_up_reason"

    with pytest.raises(ValueError, match="closed"):
        await run_memory_use_selfcheck(
            episodic=[_ep("e1", "用户明天有高数期中考试")],
            ctx=SelfCheckContext(user_message="高数期中考试怎么复习"),
            fast_model_hook=bad_hook,
        )


@pytest.mark.asyncio
async def test_fast_model_hook_consulted_only_for_rule_passing_items():
    consulted: list[str] = []

    async def hook(candidate, ctx):
        consulted.append(candidate.item_id)
        return None

    await run_memory_use_selfcheck(
        episodic=[
            _ep("e-blocked", "用户养了一只猫"),  # 规则层已降档
            _ep("e-pass", "用户明天有高数期中考试"),
        ],
        ctx=SelfCheckContext(user_message="高数期中考试怎么复习"),
        fast_model_hook=hook,
    )
    assert consulted == ["e-pass"]


def test_no_hook_is_pure_sync_path():
    """无钩子（默认）时 evaluate_memory_use_gate 是纯同步函数——本卡
    真实 LLM 0 次的守卫形态。"""
    result = evaluate_memory_use_gate(
        episodic=[_ep("e1", "用户明天有高数期中考试")],
        ctx=SelfCheckContext(user_message="高数期中考试怎么复习"),
    )
    assert result.surfaced_count == 1


# ---------------------------------------------------------------------------
# 9. 阈值冻结（调阈值 = 调 tradeoff，必须显式改常量并过 bench）
# ---------------------------------------------------------------------------


def test_duplicate_jaccard_threshold_is_frozen():
    assert DUPLICATE_JACCARD_RATIO == 0.8
