"""Memory V3 over-personalization Self-ReCheck (task M-05, MEMORY_V3 §3 step 9 / §4).

Single authority for the OUTPUT-FACE use gate that runs after legal recall has
survived M-03 (pool-entry hard prefilter) and C-03 (context hard-filter ->
semantic retrieval). Division of labor, pinned by wiring guards in
``tests/unit/test_memory_use_selfcheck_wiring.py``:

    M-03 / C-03  — "may this candidate enter the pool at all" (identity /
                   status / TTL / scope / permission / knowledge legality)
    M-05 (here)  — "given a legally recalled candidate, may it be SAID to the
                   user this turn, or only used for internal decisions"

Two usage tiers (MEMORY_V3 §4: "allow recall but decide do_not_surface"):

    SURFACE_TO_USER             — content may enter the rendered prompt face
    USE_FOR_INTERNAL_DECISION   — content stays available to internal decision
                                  surfaces (decision_context etc.); only
                                  ids + closed reason codes are observable

Four checks in FIXED order (``USE_CHECK_KINDS`` — first failing check owns the
downgrade attribution, same law as M-03's ``FILTER_DIMENSIONS``):

    1. relevance    — topically disjoint memory must not be surfaced into an
                      unrelated answer (``selfcheck:irrelevant_to_query``).
                      Conservative-pass when the turn carries no topical
                      signal (no message / phatic turn) — necessity owns that
                      case — and meta communication-form preferences are
                      exempt from topical matching entirely.
    2. necessity    — phatic turns and echo turns do not need any memory
                      surfaced (``selfcheck:phatic_query`` /
                      ``selfcheck:echoed_in_query``). Meta preferences and
                      safety pins survive (style shapes every reply; safety
                      never degrades).
    3. repetition   — a memory whose content was already conveyed by a recent
                      assistant message (``selfcheck:recently_surfaced``), or
                      a near-duplicate of a higher-priority item already in
                      the same pack (``selfcheck:duplicate_in_pack``), is
                      downgraded so one fact is not repeated every response
                      (PERSONALIZATION_EVAL adversarial: "repeatedly mentioned
                      preference should not appear in every response").
    4. sycophancy   — agreement-bias preference classes (feedback/coaching
                      style) must not steer a validation-seeking turn
                      (``selfcheck:agreement_bias_risk``); on substantive
                      turns they shape tone as usual.

Safety pins (allergy / anaphylaxis / dietary-harm facts) are exempt from all
topical checks — the physical cost of withholding them outweighs lexical
relevance gaps. In-pack near-duplicate collapsing still applies (one surfaced
copy is sufficient).

Design rules (aligned with M-03/C-02/C-03 code style):

- **Rule layer is pure and deterministic** — no I/O, no LLM. A fast-model
  hook (``run_memory_use_selfcheck``) exists for a future semantic relevance /
  agreement-bias pass: default off at every wiring, consulted only for
  rule-passing candidates, TIGHTEN-ONLY (it can downgrade, never resurrect),
  and its reason must come from the frozen ``FAST_MODEL_REASONS`` vocabulary.
- **Closed vocabularies, frozen.** ``SELF_CHECK_REASONS`` /
  ``FAST_MODEL_REASONS`` / ``USE_CHECK_KINDS`` / ``SELF_CHECK_SECTIONS`` /
  ``META_PREF_KEYS`` / ``AGREEMENT_BIAS_PREF_KEYS`` / marker sets /
  thresholds are the single source of truth. Any addition is a deliberate
  vocabulary change: bump ``SELF_CHECK_VERSION`` and re-run the OP-Bench
  (``backend/tests/fixtures/op_bench_memory_use_v1.json``) so both tradeoff
  metrics move on purpose, not by drift. ``META_PREF_KEYS`` is guarded to stay
  a subset of the writer vocabulary ``memory_constants.PREFERENCE_KEYS``.
- **Token model:** CJK character bigrams + lowercase ASCII alphanumeric
  words. Known lexical limitation (registered in the OP-Bench as
  ``known_limitation`` polarity, not headline): zero CJK/EN cross-lingual
  overlap — the fast-model hook is the designed remedy, and stays off until
  an eval justifies turning it on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Iterable, Sequence

from app.core.memory_constants import PREFERENCE_KEYS

SELF_CHECK_VERSION = "memory_use_selfcheck.v1"

# ---------------------------------------------------------------------------
# Closed vocabularies (frozen — see module docstring)
# ---------------------------------------------------------------------------

SELF_CHECK_SECTIONS: tuple[str, ...] = ("preferences", "goals", "episodic")


class UseCheckKind(StrEnum):
    RELEVANCE = "relevance"
    NECESSITY = "necessity"
    REPETITION = "repetition"
    SYCOPHANCY = "sycophancy"


# Fixed evaluation order — first failing check owns the attribution.
USE_CHECK_KINDS: tuple[UseCheckKind, ...] = (
    UseCheckKind.RELEVANCE,
    UseCheckKind.NECESSITY,
    UseCheckKind.REPETITION,
    UseCheckKind.SYCOPHANCY,
)

SELF_CHECK_REASONS: frozenset[str] = frozenset(
    {
        "selfcheck:irrelevant_to_query",
        "selfcheck:phatic_query",
        "selfcheck:echoed_in_query",
        "selfcheck:recently_surfaced",
        "selfcheck:duplicate_in_pack",
        "selfcheck:agreement_bias_risk",
    }
)

# Fast-model hook reasons — disjoint from the rule layer so metric payloads
# can attribute rule cuts vs model cuts without ambiguity.
FAST_MODEL_REASONS: frozenset[str] = frozenset(
    {
        "selfcheck:fm_semantic_irrelevant",
        "selfcheck:fm_agreement_bias",
    }
)

_FAST_MODEL_REASON_CHECKS: dict[str, UseCheckKind] = {
    "selfcheck:fm_semantic_irrelevant": UseCheckKind.RELEVANCE,
    "selfcheck:fm_agreement_bias": UseCheckKind.SYCOPHANCY,
}

# Meta (communication-form) preference keys: always relevant to reply shape,
# exempt from phatic/echo downgrade (every turn, incl. short acks, is shaped
# by them) and from repetition (style consistency is not repetitive harm) —
# but NOT from sycophancy, which binds the agreement-bias subclass below.
# Guarded subset of the writer vocabulary (memory_constants.PREFERENCE_KEYS):
# a writer-side key removal/rename turns the subset guard red.
META_PREF_KEYS: frozenset[str] = frozenset(
    {
        "ai_verbosity",
        "response_style",
        "feedback_style",
        "feedback_tone",
        "coaching_style",
        "language",
        "learning_style",
        "timezone",
        "focus_duration_preference",
        "preferred_focus_duration",
        "depth_preference",
    }
)

# Agreement-bias-prone preference classes (subset of META_PREF_KEYS): an
# affirmative-shaped value here must not steer validation-seeking turns.
AGREEMENT_BIAS_PREF_KEYS: frozenset[str] = frozenset(
    {
        "feedback_style",
        "feedback_tone",
        "coaching_style",
    }
)

# Safety-pin content markers (closed set, matched case-insensitively against
# candidate content): allergy / anaphylaxis / dietary-harm / seizure-class
# facts are exempt from topical checks — withholding them over a lexical gap
# can cost physical harm. Deliberately content-based (writer-agnostic): the
# profile write path has an open key vocabulary, so pref_key-based pinning
# would silently miss spellings it does not know.
SAFETY_PIN_CONTENT_MARKERS: frozenset[str] = frozenset(
    {
        "过敏",
        "休克",
        "麸质",
        "gluten",
        "allergic",
        "allergy",
        "anaphyla",
        "哮喘",
        "癫痫",
        "糖尿病",
        "胰岛素",
        "肾上腺素",
    }
)

# Phatic turn vocabulary: the message consists ONLY of acknowledgements /
# thanks — every CJK run and every ASCII word must be inside the closed set.
# Validation cues (对吧 / 是不是 / right? ...) are deliberately NOT phatic:
# they request a substantive answer.
PHATIC_CJK_RUNS: frozenset[str] = frozenset(
    {
        "好",
        "好的",
        "好吧",
        "好呀",
        "好嘞",
        "好滴",
        "嗯",
        "嗯嗯",
        "哦",
        "噢",
        "哈",
        "哈哈",
        "哈哈哈",
        "谢谢",
        "多谢",
        "感谢",
        "收到",
        "明白",
        "了解了",
        "了解",
        "知道了",
        "辛苦了",
        "麻烦你了",
        "不客气",
        "没事",
        "行",
    }
)
PHATIC_ASCII_WORDS: frozenset[str] = frozenset(
    {
        "ok",
        "okay",
        "oks",
        "k",
        "thanks",
        "thank",
        "you",
        "thx",
        "ty",
        "great",
        "nice",
        "good",
        "cool",
        "sure",
        "fine",
        "gotcha",
        "gotit",
        "alright",
        "bye",
    }
)

# Validation-seeking cues (closed set, substring match on the lowercased
# message): the user is fishing for agreement about their own work/state.
VALIDATION_CUE_MARKERS: frozenset[str] = frozenset(
    {
        "不用改",
        "不用再",
        "已经很好",
        "很好了",
        "没问题",
        "对吧",
        "对吗",
        "对不对",
        "没错",
        "是不是",
        "行了吧",
        "好了吧",
        "right?",
        "correct?",
        "correctly",
    }
)

# Affirmative-shaped preference values (closed set): agreement-bias risk only
# when the preference VALUE pushes unconditional positivity.
AFFIRMATIVE_VALUE_MARKERS: frozenset[str] = frozenset(
    {
        "鼓励",
        "表扬",
        "夸奖",
        "赞美",
        "打气",
        "只夸",
        "多夸",
        "encouraging",
        "supportive",
        "affirming",
        "affirmative",
        "praise",
        "hype",
    }
)

# Trailing particles stripped before phatic-run matching ("谢谢啦" -> "谢谢",
# "收到了" -> "收到"). Deliberately excludes 吧/吗 — "对吧"/"对吗" are
# validation cues requesting a substantive answer, never phatic.
_PHATIC_TAIL_PARTICLES = "啦了呀哦哈呢~！!。，,。"


def _phatic_run_core(run: str) -> str:
    stripped = run.rstrip(_PHATIC_TAIL_PARTICLES)
    return stripped if stripped in PHATIC_CJK_RUNS else run


# ---------------------------------------------------------------------------
# Frozen thresholds (tuning these moves BOTH tradeoff metrics — re-run
# OP-Bench and record the pair in the M-05 report; see REPORT.md)
# ---------------------------------------------------------------------------

# In-pack near-duplicate ratio. Jaccard-style containment over the SMALLER
# token set: |A ∩ B| / min(|A|, |B|). Plain |A∩B|/|A∪B| punishes the shorter
# restatement for every extra clause the winner carries ("...考试" vs
# "...考试，正在复习链表" scores 11/14 = 0.79 and would slip through); the
# smaller-set form asks "is this a restatement of what is already in the
# pack", which is the question repetition here means.
DUPLICATE_JACCARD_RATIO: float = 0.8

# Echo ratio: fraction of the candidate's tokens already stated verbatim by
# the user THIS turn (containment |C ∩ Q| / |C|), computed after stripping
# the conventional leading "用户" address marker (the memory system's own
# framing, not part of the fact). At/above it, surfacing the memory back
# adds no information (echo). Two guards keep topic MENTIONS from being
# misread as echo restatements (C-03 W-M compatibility case):
#   - |C| >= ECHO_MIN_CANDIDATE_TOKENS: a 2-token topic-tag memory
#     ("LEGAL-EVENT") is named by the query, not echoed by it;
#   - ratio 0.85 (not 0.80): a memory that still carries a substantive
#     uncovered token ("...-NOTES" beyond "linear algebra exam review") has
#     increment, and surfacing it is legal personalization.
ECHO_CONTAINMENT_RATIO: float = 0.85
ECHO_MIN_CANDIDATE_TOKENS: int = 4

# Memory summaries conventionally start with the "用户..." address marker.
_ECHO_ADDRESS_PREFIX = "用户"

# Recently-surfaced ratio: fraction of the candidate's tokens contained in a
# SINGLE recent assistant message. The assistant having already conveyed most
# of the memory's content once makes this turn's re-mention repetitive.
RECENTLY_SURFACED_CONTAINMENT_RATIO: float = 0.6

# ---------------------------------------------------------------------------
# Token model: CJK bigrams + ASCII words
# ---------------------------------------------------------------------------

_CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def lexical_tokens(text: str | None) -> frozenset[str]:
    """CJK runs -> character bigrams; ASCII runs -> lowercase alnum words."""
    if not text:
        return frozenset()
    tokens: set[str] = set()
    for run in _CJK_RUN_RE.findall(text):
        if len(run) >= 2:
            tokens.update(run[i : i + 2] for i in range(len(run) - 1))
        else:
            tokens.add(run)
    for word in _ASCII_WORD_RE.findall(text):
        tokens.add(word.lower())
    return frozenset(tokens)


def _overlap_ratio(candidate_tokens: frozenset[str], other_tokens: frozenset[str]) -> float:
    """|A ∩ B| / |A| — how much of A is covered by B (0.0 when A is empty)."""
    if not candidate_tokens:
        return 0.0
    return len(candidate_tokens & other_tokens) / len(candidate_tokens)


def _containment_over_smaller(a: frozenset[str], b: frozenset[str]) -> float:
    """|A ∩ B| / min(|A|, |B|) — restatement detection symmetric in which side is longer."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def is_phatic_query(text: str | None) -> bool:
    """True iff every content run of the message is a closed-vocabulary
    acknowledgement/thanks token (好的/嗯嗯/ok/thank you...). None/empty ->
    False (no turn, not a phatic turn)."""
    if not text:
        return False
    saw_token = False
    for run in _CJK_RUN_RE.findall(text):
        saw_token = True
        if _phatic_run_core(run) not in PHATIC_CJK_RUNS:
            return False
    for word in _ASCII_WORD_RE.findall(text):
        saw_token = True
        if word.lower() not in PHATIC_ASCII_WORDS:
            return False
    return saw_token


def _has_marker(text: str | None, markers: frozenset[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


class MemoryUseDecision(StrEnum):
    SURFACE_TO_USER = "surface_to_user"
    USE_FOR_INTERNAL_DECISION = "use_for_internal_decision"


@dataclass(frozen=True)
class MemoryUseCandidate:
    """One legally-recalled memory item entering the output-assembly face."""

    item_id: str
    section: str
    content: str
    pref_key: str | None = None


@dataclass(frozen=True)
class SelfCheckContext:
    """Turn context the gate sees. Missing pieces are UNCONSTRAINED — checks
    that need them sleep rather than guess (conservative-pass, M-03 law)."""

    user_message: str | None = None
    recent_assistant_messages: tuple[str, ...] = ()


@dataclass(frozen=True)
class SelfCheckFlag:
    check: str  # UseCheckKind value owning the downgrade
    reason: str  # SELF_CHECK_REASONS / FAST_MODEL_REASONS member
    detail: str | None = None


@dataclass(frozen=True)
class MemoryUseDecisionRecord:
    candidate: MemoryUseCandidate
    decision: MemoryUseDecision
    flag: SelfCheckFlag | None = None  # None iff SURFACE_TO_USER


SELFCHECK_PAYLOAD_KEYS: tuple[str, ...] = (
    "version",
    "input_count",
    "surfaced_count",
    "internal_only_count",
    "check_counts",
    "reason_counts",
)


@dataclass(frozen=True)
class MemoryUseGateResult:
    version: str
    decisions: list[MemoryUseDecisionRecord] = field(default_factory=list)

    @property
    def input_count(self) -> int:
        return len(self.decisions)

    @property
    def surfaced_count(self) -> int:
        return sum(1 for record in self.decisions if record.decision is MemoryUseDecision.SURFACE_TO_USER)

    @property
    def internal_only_count(self) -> int:
        return sum(1 for record in self.decisions if record.decision is MemoryUseDecision.USE_FOR_INTERNAL_DECISION)

    def surfaced_ids(self, section: str) -> frozenset[str]:
        return frozenset(
            record.candidate.item_id
            for record in self.decisions
            if record.candidate.section == section and record.decision is MemoryUseDecision.SURFACE_TO_USER
        )

    @property
    def reason_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.decisions:
            if record.flag is not None:
                counts[record.flag.reason] = counts.get(record.flag.reason, 0) + 1
        return counts

    @property
    def check_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for record in self.decisions:
            if record.flag is not None:
                counts[record.flag.check] = counts.get(record.flag.check, 0) + 1
        return counts

    def internal_only_entries(self) -> list[dict[str, str]]:
        """ids + closed reasons only — NO content re-injection (the metadata
        face reaches the prompt via to_prompt_context, so summaries must
        never travel here)."""
        return [
            {
                "id": record.candidate.item_id,
                "section": record.candidate.section,
                "reason": record.flag.reason,
            }
            for record in self.decisions
            if record.flag is not None
        ]

    def to_metric_payload(self) -> dict[str, object]:
        return {
            "version": self.version,
            "input_count": self.input_count,
            "surfaced_count": self.surfaced_count,
            "internal_only_count": self.internal_only_count,
            "check_counts": self.check_counts,
            "reason_counts": self.reason_counts,
        }


# ---------------------------------------------------------------------------
# Rule layer (pure, deterministic)
# ---------------------------------------------------------------------------


def _is_meta_pref(candidate: MemoryUseCandidate) -> bool:
    return candidate.section == "preferences" and candidate.pref_key in META_PREF_KEYS


def _is_safety_pin(candidate: MemoryUseCandidate) -> bool:
    return _has_marker(candidate.content, SAFETY_PIN_CONTENT_MARKERS)


def _relevance_flag(candidate: MemoryUseCandidate, ctx: SelfCheckContext) -> SelfCheckFlag | None:
    message = (ctx.user_message or "").strip()
    if not message or is_phatic_query(message):
        # No topical signal to constrain against — conservative-pass; the
        # phatic case is owned by necessity below.
        return None
    if _is_safety_pin(candidate) or _is_meta_pref(candidate):
        return None
    candidate_tokens = lexical_tokens(candidate.content)
    if candidate.section == "preferences" and candidate.pref_key:
        # The preference DOMAIN itself is content: naming the domain in the
        # query (e.g. "study_time_preference 是什么意思") earns relevance.
        candidate_tokens = candidate_tokens | lexical_tokens(candidate.pref_key)
    if not candidate_tokens:
        return None
    if candidate_tokens & lexical_tokens(message):
        return None
    return SelfCheckFlag(
        check=UseCheckKind.RELEVANCE.value,
        reason="selfcheck:irrelevant_to_query",
        detail=f"zero lexical overlap with turn (tokens={len(candidate_tokens)})",
    )


def _necessity_flag(candidate: MemoryUseCandidate, ctx: SelfCheckContext) -> SelfCheckFlag | None:
    if _is_safety_pin(candidate) or _is_meta_pref(candidate):
        return None
    message = (ctx.user_message or "").strip()
    if not message:
        return None
    if is_phatic_query(message):
        return SelfCheckFlag(
            check=UseCheckKind.NECESSITY.value,
            reason="selfcheck:phatic_query",
            detail="acknowledgement turn — no memory needs surfacing",
        )
    candidate_tokens = lexical_tokens(
        candidate.content.removeprefix(_ECHO_ADDRESS_PREFIX)
        if candidate.content.startswith(_ECHO_ADDRESS_PREFIX)
        else candidate.content
    )
    if (
        len(candidate_tokens) >= ECHO_MIN_CANDIDATE_TOKENS
        and _overlap_ratio(candidate_tokens, lexical_tokens(message)) >= ECHO_CONTAINMENT_RATIO
    ):
        return SelfCheckFlag(
            check=UseCheckKind.NECESSITY.value,
            reason="selfcheck:echoed_in_query",
            detail=f">={ECHO_CONTAINMENT_RATIO:.2f} of memory tokens already stated this turn",
        )
    return None


def _repetition_flag(
    candidate: MemoryUseCandidate,
    ctx: SelfCheckContext,
    surfaced_peers: Sequence[MemoryUseCandidate],
) -> SelfCheckFlag | None:
    candidate_tokens = lexical_tokens(candidate.content)
    if not candidate_tokens:
        return None
    # Cross-turn repetition: any single recent assistant message that already
    # conveyed this memory's content.
    if not _is_safety_pin(candidate) and not _is_meta_pref(candidate):
        for turn_index, message in enumerate(ctx.recent_assistant_messages):
            ratio = _overlap_ratio(candidate_tokens, lexical_tokens(message))
            if ratio >= RECENTLY_SURFACED_CONTAINMENT_RATIO:
                return SelfCheckFlag(
                    check=UseCheckKind.REPETITION.value,
                    reason="selfcheck:recently_surfaced",
                    detail=f"assistant window turn {turn_index} already conveyed >= "
                    f"{RECENTLY_SURFACED_CONTAINMENT_RATIO:.2f} of this memory",
                )
    # In-pack near-duplicate: a higher-priority same-section item already in
    # the surfaced face carries the same content (applies to safety pins too —
    # one surfaced copy is sufficient).
    for peer in surfaced_peers:
        if peer.section != candidate.section:
            continue
        ratio = _containment_over_smaller(candidate_tokens, lexical_tokens(peer.content))
        if ratio >= DUPLICATE_JACCARD_RATIO:
            return SelfCheckFlag(
                check=UseCheckKind.REPETITION.value,
                reason="selfcheck:duplicate_in_pack",
                detail=f"duplicate of {peer.item_id}",
            )
    return None


def _sycophancy_flag(candidate: MemoryUseCandidate, ctx: SelfCheckContext) -> SelfCheckFlag | None:
    if candidate.section != "preferences" or candidate.pref_key not in AGREEMENT_BIAS_PREF_KEYS:
        return None
    message = (ctx.user_message or "").strip()
    if not message or not _has_marker(message, VALIDATION_CUE_MARKERS):
        return None
    if not _has_marker(candidate.content, AFFIRMATIVE_VALUE_MARKERS):
        return None
    return SelfCheckFlag(
        check=UseCheckKind.SYCOPHANCY.value,
        reason="selfcheck:agreement_bias_risk",
        detail=f"affirmative {candidate.pref_key} on a validation-seeking turn",
    )


def _evaluate_candidate(
    candidate: MemoryUseCandidate,
    ctx: SelfCheckContext,
    surfaced_peers: Sequence[MemoryUseCandidate],
) -> MemoryUseDecisionRecord:
    for kind in USE_CHECK_KINDS:
        flag: SelfCheckFlag | None
        if kind is UseCheckKind.RELEVANCE:
            flag = _relevance_flag(candidate, ctx)
        elif kind is UseCheckKind.NECESSITY:
            flag = _necessity_flag(candidate, ctx)
        elif kind is UseCheckKind.REPETITION:
            flag = _repetition_flag(candidate, ctx, surfaced_peers)
        else:
            flag = _sycophancy_flag(candidate, ctx)
        if flag is not None:
            return MemoryUseDecisionRecord(
                candidate=candidate,
                decision=MemoryUseDecision.USE_FOR_INTERNAL_DECISION,
                flag=flag,
            )
    return MemoryUseDecisionRecord(candidate=candidate, decision=MemoryUseDecision.SURFACE_TO_USER)


def evaluate_memory_use_gate(
    *,
    preferences: Iterable[MemoryUseCandidate] = (),
    goals: Iterable[MemoryUseCandidate] = (),
    episodic: Iterable[MemoryUseCandidate] = (),
    ctx: SelfCheckContext | None = None,
) -> MemoryUseGateResult:
    """Run the four-check rule layer over legally-recalled candidates.

    Pure and synchronous — no I/O, no LLM (this card runs real models zero
    times). Candidates keep their caller-given priority order: in-pack
    duplicate attribution is "first/highest-priority surfaced item wins".
    """
    context = ctx or SelfCheckContext()
    decisions: list[MemoryUseDecisionRecord] = []
    surfaced_peers: list[MemoryUseCandidate] = []
    for candidate in list(preferences) + list(goals) + list(episodic):
        record = _evaluate_candidate(candidate, context, surfaced_peers)
        decisions.append(record)
        if record.decision is MemoryUseDecision.SURFACE_TO_USER:
            surfaced_peers.append(candidate)
    return MemoryUseGateResult(version=SELF_CHECK_VERSION, decisions=decisions)


# ---------------------------------------------------------------------------
# Fast-model hook (default OFF at every wiring; tighten-only)
# ---------------------------------------------------------------------------

FastModelHook = Callable[[MemoryUseCandidate, SelfCheckContext], "object"]


async def run_memory_use_selfcheck(
    *,
    preferences: Iterable[MemoryUseCandidate] = (),
    goals: Iterable[MemoryUseCandidate] = (),
    episodic: Iterable[MemoryUseCandidate] = (),
    ctx: SelfCheckContext | None = None,
    fast_model_hook: FastModelHook | None = None,
) -> MemoryUseGateResult:
    """Rule layer + optional fast-model semantic pass.

    The hook is consulted ONLY for rule-passing (surfaced) candidates, may
    only TIGHTEN (return a downgrade reason or None), and its reason must be
    a member of the frozen ``FAST_MODEL_REASONS`` vocabulary — anything else
    raises ``ValueError`` so an uncontrolled reason can never leak into
    metrics.
    """
    result = evaluate_memory_use_gate(preferences=preferences, goals=goals, episodic=episodic, ctx=ctx)
    if fast_model_hook is None:
        return result
    context = ctx or SelfCheckContext()
    decisions: list[MemoryUseDecisionRecord] = list(result.decisions)
    for index, record in enumerate(decisions):
        if record.decision is not MemoryUseDecision.SURFACE_TO_USER:
            continue
        reason = await fast_model_hook(record.candidate, context)
        if reason is None:
            continue
        reason = str(reason)
        if reason not in FAST_MODEL_REASONS:
            raise ValueError(
                f"fast_model_hook reason {reason!r} not in closed vocabulary FAST_MODEL_REASONS "
                f"({sorted(FAST_MODEL_REASONS)})"
            )
        decisions[index] = MemoryUseDecisionRecord(
            candidate=record.candidate,
            decision=MemoryUseDecision.USE_FOR_INTERNAL_DECISION,
            flag=SelfCheckFlag(
                check=_FAST_MODEL_REASON_CHECKS[reason].value,
                reason=reason,
                detail="fast-model downgrade (tighten-only)",
            ),
        )
    return MemoryUseGateResult(version=SELF_CHECK_VERSION, decisions=decisions)


# Startup-time vocabulary guard (cheap; real enforcement lives in the frozen
# unit tests, this catches import-order drift early in any process).
assert (
    META_PREF_KEYS <= PREFERENCE_KEYS
), f"M-05 META_PREF_KEYS drifted outside the writer vocabulary: {META_PREF_KEYS - PREFERENCE_KEYS}"
assert AGREEMENT_BIAS_PREF_KEYS <= META_PREF_KEYS
assert not (FAST_MODEL_REASONS & SELF_CHECK_REASONS)
