"""V3-FIX-35 (second mode) regression: CJK domain glosses in the M-05
relevance check.

M-09 residuals P09-D5-difficulty_chain / P10-D3-retention_style_supersede
stayed red after the supersede-chain fix: the chain HEAD now won resolution,
but ``_relevance_flag`` downgraded it as topically irrelevant — the English
pref key carries zero token overlap with a Chinese query naming the same
domain ("给我出几道统计学习的练习题" for ``preferred_expansion_depth``).

The remedy is a frozen, guarded, VALUE-FREE domain-gloss vocabulary
(``PREFERENCE_KEY_DOMAIN_GLOSSES``): naming the preference's service domain
in Chinese earns the same domain-level relevance the English key already
earns. Topically-bound preferences WITHOUT a gloss (e.g. ``knowledge_gaps``,
OP-Bench op-rel-pref-01) keep the strict downgrade.
"""

from __future__ import annotations

from app.services.memory_use_selfcheck import (
    PREFERENCE_KEY_DOMAIN_GLOSSES,
    SELF_CHECK_VERSION,
    MemoryUseCandidate,
    MemoryUseGateResult,
    MemoryUseDecision,
    SelfCheckContext,
    evaluate_memory_use_gate,
    lexical_tokens,
)
from app.core.memory_constants import PREFERENCE_KEYS


def _pref(key: str, value: str) -> MemoryUseCandidate:
    return MemoryUseCandidate(
        item_id=key,
        section="preferences",
        content=value,
        pref_key=key,
    )


def _decision_for(candidate: MemoryUseCandidate, message: str) -> MemoryUseDecision:
    result = evaluate_memory_use_gate(preferences=[candidate], ctx=SelfCheckContext(user_message=message))
    return result.decisions[0].decision


def test_version_bumped_for_vocabulary_change():
    assert SELF_CHECK_VERSION == "memory_use_selfcheck.v2"


def test_gloss_vocabulary_guards():
    assert set(PREFERENCE_KEY_DOMAIN_GLOSSES) <= PREFERENCE_KEYS


def test_glossed_domain_earns_cjk_relevance_p09_shape():
    """P09-D5 shape: practice-difficulty preference vs practice-set request."""
    candidate = _pref(
        "preferred_expansion_depth",
        "现在要竞赛难度的题，基础的没挑战",
    )
    assert _decision_for(candidate, "给我出几道统计学习的练习题") is MemoryUseDecision.SURFACE_TO_USER


def test_glossed_domain_earns_cjk_relevance_p10_shape():
    """P10-D3 shape: memorization-method preference vs memory-method request."""
    candidate = _pref(
        "vocabulary_retention_style",
        "改用思维导图串联记，卡片太碎了",
    )
    assert _decision_for(candidate, "帮我安排解剖名词的记忆方法") is MemoryUseDecision.SURFACE_TO_USER


def test_unglossed_topically_bound_preference_still_downgrades():
    """OP-Bench op-rel-pref-01 shape: knowledge_gaps has NO gloss — a Greek
    mythology gap stays irrelevant to a linear algebra plan."""
    candidate = _pref("knowledge_gaps", "希腊神话诸神谱系")
    record = evaluate_memory_use_gate(
        preferences=[candidate],
        ctx=SelfCheckContext(user_message="帮我制定线性代数三周复习计划"),
    ).decisions[0]
    assert record.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert record.flag is not None and record.flag.reason == "selfcheck:irrelevant_to_query"


def test_gloss_does_not_earn_relevance_for_unrelated_query():
    """The gloss closes the DOMAIN gap, not the value gap: a glossed key on a
    query outside its domain still downgrades."""
    candidate = _pref("preferred_expansion_depth", "现在要竞赛难度的题")
    record = evaluate_memory_use_gate(
        preferences=[candidate],
        ctx=SelfCheckContext(user_message="帮我写一封给导师的请假邮件"),
    ).decisions[0]
    assert record.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert record.flag is not None and record.flag.reason == "selfcheck:irrelevant_to_query"


def test_gloss_is_value_free():
    """Glosses express the SERVICE DOMAIN only — no specific values, so they
    cannot fabricate personalization; tokenized gloss must be part of the
    closed map, not derived from any user content."""
    for key, gloss in PREFERENCE_KEY_DOMAIN_GLOSSES.items():
        tokens = lexical_tokens(gloss)
        assert tokens, f"gloss for {key} tokenizes to nothing"
        # gloss tokens must NOT appear in the English key (sanity: they are
        # the CJK side of the domain, not a copy of the identifier rule)
        assert not (tokens & lexical_tokens(key))


def test_necessity_echo_paths_unaffected_by_gloss():
    """Phatic turns still downgrade glossed preferences (necessity owns them)
    — the gloss only feeds the relevance check, never the phatic gate.
    ("好的" is in the frozen PHATIC_CJK_RUNS vocabulary; note "嗯嗯好的" is
    deliberately NOT phatic — trailing 的 blocks it, M-05 frozen behavior.)"""
    candidate = _pref("vocabulary_retention_style", "改用思维导图串联记")
    record = evaluate_memory_use_gate(
        preferences=[candidate],
        ctx=SelfCheckContext(user_message="好的"),
    ).decisions[0]
    assert record.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION
    assert record.flag is not None and record.flag.reason == "selfcheck:phatic_query"


def test_gate_result_carries_version():
    result: MemoryUseGateResult = evaluate_memory_use_gate()
    assert result.version == SELF_CHECK_VERSION
