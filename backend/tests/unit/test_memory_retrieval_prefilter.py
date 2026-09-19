"""M-03 deterministic retrieval prefilter —— unit tests.

Covers (card acceptance):
- scope lattice FULL compatibility matrix (closed structure + parity guard:
  matrix keys == SCOPE_LEVELS x states, and the evaluator agrees with the
  table on every cell);
- today-only TTL semantics on naive-UTC day boundaries;
- every filter dimension: user / status (incl. revoked via M-01 precedence) /
  TTL / scope / purpose (user_memory_settings permission layer + descriptor
  purpose restrictions) / sensitivity;
- filter reason metrics: per-dimension and per-reason counts + payload shape.

Review-rework guards (dual-review CHANGES round):
- R2-F1: unknown derive_scope levels fail closed on the DERIVED path (never
  lifted to user-global) + derive_scope <-> SCOPE_LEVELS vocabulary parity;
- R2-F2: FILTER_DIMENSIONS order pinned + all five adjacent-pair attributions
  pinned (reorder turns red — D-06 attribution drift guard).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.services.memory_retrieval_prefilter import (
    CTX_ANCHOR_VALUES,
    FILTER_DIMENSIONS,
    LEVEL_ANCHOR_KEYS,
    MEMORY_PREFILTER_VERSION,
    RETRIEVAL_PURPOSES,
    SCOPE_COMPATIBILITY,
    SCOPE_LEVELS,
    MemoryScopeDescriptor,
    PrefilterResult,
    RetrievalContext,
    UserMemoryPermissions,
    prefilter_candidates,
    record_kind,
    scope_compatible,
    scope_of_record,
)

NOW = datetime(2026, 9, 19, 12, 0, 0)
USER = str(uuid4())


def _ctx(**overrides) -> RetrievalContext:
    defaults = {"user_id": USER, "purpose": "llm_context", "now": NOW}
    defaults.update(overrides)
    return RetrievalContext(**defaults)


def _episodic(**overrides):
    """Real ORM shape (no DB) —— derive_scope/derive_status key off
    ``__tablename__`` and real column attributes."""
    base = {
        "id": uuid4(),
        "user_id": uuid4(),
        "summary": "s",
        "source_type": "chat_turn",
        "source_lane": "direct_capture",
        "subject_type": "self",
        "occurred_at": NOW - timedelta(days=1),
        "created_at": NOW - timedelta(days=1),
        "importance_score": 0.5,
        "confidence": 0.5,
        "evidence_score": 0.5,
        "correction_count": 0,
    }
    base.update(overrides)
    return EpisodicMemory(**base)


def _preference(**overrides):
    base = {
        "id": uuid4(),
        "user_id": uuid4(),
        "pref_key": "depth_preference",
        "pref_value": {"value": 1},
        "version": 1,
        "evidence_refs": [{"type": "user_state", "id": "t"}],
    }
    base.update(overrides)
    return MemoryPreference(**base)


def _goal(**overrides):
    base = {
        "id": uuid4(),
        "user_id": uuid4(),
        "title": "g",
        "status": "active",
        "created_at": NOW - timedelta(days=1),
        "updated_at": NOW - timedelta(days=1),
    }
    base.update(overrides)
    return MemoryGoal(**base)


# ---------------------------------------------------------------------------
# Closed-vocabulary structure guards
# ---------------------------------------------------------------------------


def test_scope_compatibility_matrix_is_total_and_closed():
    """The matrix must cover the full cross product (no undefined cell, no
    stray cell) —— the closed-data-structure acceptance."""
    expected = {(level, state) for level in SCOPE_LEVELS for state in ("unconstrained", "match", "mismatch")}
    assert set(SCOPE_COMPATIBILITY.keys()) == expected
    assert all(isinstance(v, bool) for v in SCOPE_COMPATIBILITY.values())


def test_level_anchor_keys_cover_all_scoped_levels():
    assert set(LEVEL_ANCHOR_KEYS.keys()) == set(SCOPE_LEVELS)
    assert LEVEL_ANCHOR_KEYS["global"] == ()


def test_retrieval_context_rejects_unknown_purpose_and_sensitivity():
    with pytest.raises(ValueError):
        _ctx(purpose="not_a_purpose")
    with pytest.raises(ValueError):
        _ctx(max_sensitivity="ultra")


def test_retrieval_purposes_vocabulary_is_closed():
    assert frozenset({"llm_context", "personalization", "analytics", "export", "governance"}) == RETRIEVAL_PURPOSES


# ---------------------------------------------------------------------------
# Scope lattice: full matrix parity (evaluator vs table)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("level", SCOPE_LEVELS)
@pytest.mark.parametrize("state", ["unconstrained", "match", "mismatch"])
def test_scope_matrix_parity(level, state):
    """For every (level, state) cell, construct a descriptor + ctx pair that
    the evaluator maps to exactly that state, and assert the verdict equals
    the table.

    ``global`` has no anchor keys (LEVEL_ANCHOR_KEYS["global"] == ()), so its
    match/mismatch columns are structurally unreachable: every global record
    evaluates to ``unconstrained``. Those two cells still exist in the closed
    table and must be True (dead-but-safe), which this test asserts.
    """
    anchor_key_by_level = {
        "goal": "goal_id",
        "domain": "domain_key",
        "task_type": "task_type",
        "session": "session_id",
    }
    if level == "global":
        assert SCOPE_COMPATIBILITY[("global", state)] is True
        if state != "unconstrained":
            # unreachable by construction; the evaluator can only produce the
            # unconstrained column for anchor-less levels.
            assert _classify_state(MemoryScopeDescriptor(level="global"), _ctx()) == "unconstrained"
            return
    anchor_value = "anchor-1"
    other_value = "anchor-other"

    descriptor_kwargs: dict = {"level": level}
    ctx_kwargs: dict = {}
    if level in anchor_key_by_level:
        key = anchor_key_by_level[level]
        if state == "match":
            descriptor_kwargs[key] = anchor_value
            ctx_kwargs = _ctx_anchor(key, anchor_value)
        elif state == "mismatch":
            descriptor_kwargs[key] = anchor_value
            ctx_kwargs = _ctx_anchor(key, other_value)
        # unconstrained: no ctx anchor, no record anchor
    descriptor = MemoryScopeDescriptor(**descriptor_kwargs)
    ctx = _ctx(**ctx_kwargs)

    # sanity: the evaluator really classified the intended state
    assert _classify_state(descriptor, ctx) == state
    allowed, reason = scope_compatible(descriptor, ctx)
    assert allowed is SCOPE_COMPATIBILITY[(level, state)]
    if SCOPE_COMPATIBILITY[(level, state)]:
        assert reason is None
    else:
        assert reason == "scope:mismatch"


def _ctx_anchor(key: str, value: str) -> dict:
    """Build RetrievalContext kwargs that constrain exactly one anchor key."""
    if key == "goal_id":
        return {"goal_ids": frozenset({value})}
    if key == "task_id":
        return {"task_ids": frozenset({value})}
    if key == "plan_id":
        return {"plan_ids": frozenset({value})}
    if key == "domain_key":
        return {"domain_keys": frozenset({value})}
    if key == "task_type":
        return {"task_type": value}
    if key == "session_id":
        return {"session_id": value}
    raise AssertionError(key)


def _classify_state(descriptor, ctx) -> str:
    from app.services.memory_retrieval_prefilter import _ctx_constraint_state

    return _ctx_constraint_state(descriptor, ctx)


def test_unanchored_scoped_record_behaves_user_global():
    """A goal/domain record with no anchor never mismatches (its restrictions
    are undefined -> only the unconstrained column applies)."""
    descriptor = MemoryScopeDescriptor(level="goal")  # no goal/task/plan anchor
    ctx = _ctx(plan_ids=frozenset({"some-plan"}), goal_ids=frozenset({"some-goal"}))
    assert _classify_state(descriptor, ctx) == "unconstrained"
    assert scope_compatible(descriptor, ctx) == (True, None)


def test_goal_anchor_matches_via_task_or_plan():
    descriptor = MemoryScopeDescriptor(level="goal", plan_id="p1")
    assert scope_compatible(descriptor, _ctx(plan_ids=frozenset({"p1", "p2"})))[0] is True
    descriptor_task = MemoryScopeDescriptor(level="goal", task_id="t1")
    assert scope_compatible(descriptor_task, _ctx(task_ids=frozenset({"t1"})))[0] is True
    assert scope_compatible(descriptor_task, _ctx(plan_ids=frozenset({"p1"})))[0] is False


def test_global_record_passes_even_on_mismatch():
    descriptor = MemoryScopeDescriptor(level="global")
    ctx = _ctx(plan_ids=frozenset({"p1"}), domain_keys=frozenset({"math"}), task_type="quiz")
    assert scope_compatible(descriptor, ctx) == (True, None)


def test_session_scope_is_fail_closed():
    """Session-scoped (transient/working-memory) records never leak outside
    their own session —— even when ctx carries no session anchor."""
    descriptor = MemoryScopeDescriptor(level="session", session_id="s1")
    assert scope_compatible(descriptor, _ctx())[0] is False  # unconstrained -> cut
    assert scope_compatible(descriptor, _ctx(session_id="s2"))[0] is False
    assert scope_compatible(descriptor, _ctx(session_id="s1"))[0] is True


def test_unknown_level_fails_closed():
    descriptor = MemoryScopeDescriptor(level="weird")
    assert scope_compatible(descriptor, _ctx()) == (False, "scope:unknown_level")


# ---------------------------------------------------------------------------
# scope_of_record derivation (M-01 projection -> typed descriptor)
# ---------------------------------------------------------------------------


def test_scope_of_record_episodic_is_domain_with_subject():
    record = _episodic(subject_type="commitment", decay_policy="due_at+7d", due_at=NOW + timedelta(days=1))
    descriptor = scope_of_record(record)
    assert descriptor.level == "domain"
    assert descriptor.domain_key == "commitment"
    assert descriptor.today_only is False


def test_scope_of_record_preference_is_global():
    record = _preference()
    assert record_kind(record) == "preference"
    assert scope_of_record(record).level == "global"


def test_scope_of_record_goal_carries_plan_anchor():
    record = _goal(linked_plan_id=uuid4())
    descriptor = scope_of_record(record)
    assert descriptor.level == "goal"
    assert descriptor.plan_id is not None


def test_scope_of_record_today_only_from_decay_policy():
    record = _episodic(decay_policy="1d")
    assert scope_of_record(record).today_only is True
    record_30d = _episodic(decay_policy="30d")
    assert scope_of_record(record_30d).today_only is False


# ---------------------------------------------------------------------------
# Dimension: user
# ---------------------------------------------------------------------------


def test_wrong_user_is_cut_and_missing_user_id_fails_closed():
    legal = _episodic()
    wrong = _episodic()
    legal.user_id = USER
    wrong.user_id = str(uuid4())
    no_user = SimpleNamespace(summary="x", source_type="chat_turn", occurred_at=NOW)

    result = prefilter_candidates([legal, wrong, no_user], _ctx())
    assert result.allowed == [legal]
    assert [r.reason for r in result.rejections] == ["user:wrong_user", "user:wrong_user"]
    assert result.dimension_counts["user"] == 2
    assert result.reason_counts["user:wrong_user"] == 2


# ---------------------------------------------------------------------------
# Dimension: status (M-01 precedence machine)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "attr,value,expected_status",
    [
        ("revoked_at", NOW, "revoked"),
        ("superseded_by_id", uuid4(), "superseded"),
        ("retracted_at", NOW, "retracted"),
        ("archived_at", NOW, "archived"),
    ],
)
def test_non_active_status_is_cut(attr, value, expected_status):
    record = _episodic(**{attr: value})
    record.user_id = USER
    result = prefilter_candidates([record], _ctx())
    assert result.allowed == []
    assert result.rejections[0].reason == f"status:{expected_status}"
    assert result.dimension_counts["status"] == 1


def test_superseded_preference_version_is_cut():
    """memory_preferences chain: any non-head version (replaced_by_id set)
    must not compete for LLM injection."""
    head = _preference(user_id=USER, version=2)
    superseded = _preference(user_id=USER, version=1, replaced_by_id=uuid4())
    result = prefilter_candidates([head, superseded], _ctx())
    assert result.allowed == [head]
    assert result.rejections[0].reason == "status:superseded"


def test_expired_goal_status_is_cut_via_status_dimension():
    record = SimpleNamespace(
        id=uuid4(),
        user_id=USER,
        title="g",
        status="active",
        expires_at=NOW - timedelta(days=1),
        created_at=NOW - timedelta(days=10),
    )
    result = prefilter_candidates([record], _ctx())
    assert result.rejections[0].reason == "status:expired"


def test_status_precedence_revoked_beats_superseded():
    record = _episodic(revoked_at=NOW, superseded_by_id=uuid4(), archived_at=NOW)
    record.user_id = USER
    result = prefilter_candidates([record], _ctx())
    assert result.rejections[0].reason == "status:revoked"


def test_active_record_passes_all_hard_dimensions():
    record = _episodic()
    record.user_id = USER
    result = prefilter_candidates([record], _ctx())
    assert result.allowed == [record]
    assert result.rejections == []


# ---------------------------------------------------------------------------
# Dimension: TTL (today-only + due_at+7d + not_yet_valid)
# ---------------------------------------------------------------------------


def test_today_only_passes_same_utc_day_and_cuts_next_day():
    same_day = _episodic(decay_policy="1d", created_at=datetime(2026, 9, 19, 0, 30))
    same_day.user_id = USER
    next_day = _episodic(decay_policy="today", created_at=datetime(2026, 9, 18, 23, 59))
    next_day.user_id = USER

    result = prefilter_candidates([same_day, next_day], _ctx(now=datetime(2026, 9, 19, 23, 59)))
    assert result.allowed == [same_day]
    assert result.rejections[0].reason == "ttl:today_only_expired"
    assert result.dimension_counts["ttl"] == 1


def test_today_only_midnight_boundary_is_naive_utc():
    record = _episodic(decay_policy="1d", created_at=datetime(2026, 9, 19, 18, 0))
    record.user_id = USER
    just_before = prefilter_candidates([record], _ctx(now=datetime(2026, 9, 19, 23, 59, 59)))
    at_midnight = prefilter_candidates([record], _ctx(now=datetime(2026, 9, 20, 0, 0, 0)))
    assert just_before.allowed == [record]
    assert at_midnight.allowed == []
    assert at_midnight.rejections[0].reason == "ttl:today_only_expired"


def test_commitment_due_at_plus_7d_hard_ttl():
    fresh = _episodic(decay_policy="due_at+7d", due_at=NOW - timedelta(days=6))
    fresh.user_id = USER
    expired = _episodic(decay_policy="due_at+7d", due_at=NOW - timedelta(days=8))
    expired.user_id = USER

    result = prefilter_candidates([fresh, expired], _ctx())
    assert result.allowed == [fresh]
    assert result.rejections[0].reason == "ttl:expired"
    assert "due_at+7d" in result.rejections[0].detail


def test_soft_decay_policies_are_not_hard_ttl():
    """7d/30d half-life policies belong to the decay job (archival), not the
    deterministic prefilter."""
    old_7d = _episodic(decay_policy="7d", occurred_at=NOW - timedelta(days=90))
    old_7d.user_id = USER
    assert prefilter_candidates([old_7d], _ctx()).allowed == [old_7d]


def test_valid_from_future_is_not_yet_valid():
    descriptor = MemoryScopeDescriptor(level="global", valid_from=NOW + timedelta(hours=1))
    record = _episodic()
    record.user_id = USER
    from app.services.memory_retrieval_prefilter import _reject_ttl

    rejection = _reject_ttl(record, _ctx(), descriptor)
    assert rejection is not None and rejection.reason == "ttl:not_yet_valid"


# ---------------------------------------------------------------------------
# Dimension: purpose (permission layer + declared purposes)
# ---------------------------------------------------------------------------


def test_memory_disabled_cuts_everything():
    record = _episodic()
    record.user_id = USER
    ctx = _ctx(permissions=UserMemoryPermissions(enabled=False))
    result = prefilter_candidates([record], ctx)
    assert result.rejections[0].reason == "purpose:memory_disabled"


def test_type_level_toggles_cut_the_right_family():
    pref = _preference(user_id=USER)
    goal = _goal(user_id=USER)
    epi = _episodic(user_id=USER)

    ctx = _ctx(permissions=UserMemoryPermissions(allow_preferences=False, allow_goals=False, allow_episodic=False))
    result = prefilter_candidates([pref, goal, epi], ctx)
    assert result.allowed == []
    assert [r.reason for r in result.rejections] == ["purpose:type_disabled"] * 3


def test_inferred_episodic_toggle_cuts_hypothesis_class_only():
    inferred = _episodic(user_id=USER, source_lane="llm")  # M-01: unknown lane -> HYPOTHESIS
    explicit = _episodic(user_id=USER, source_lane="user_confirmed")  # M-01: FACT

    ctx = _ctx(permissions=UserMemoryPermissions(allow_inferred_episodic=False))
    result = prefilter_candidates([inferred, explicit], ctx)
    assert result.allowed == [explicit]
    assert result.rejections[0].reason == "purpose:inferred_episodic_disabled"


def test_blocked_pref_keys_and_sources_cut_records():
    pref = _preference(user_id=USER)
    epi = _episodic(user_id=USER, source_type="error_analysis")

    ctx = _ctx(
        permissions=UserMemoryPermissions(
            blocked_pref_keys=frozenset({"depth_preference"}),
            blocked_sources=frozenset({"error_analysis"}),
        )
    )
    result = prefilter_candidates([pref, epi], ctx)
    assert result.allowed == []
    assert {r.reason for r in result.rejections} == {
        "purpose:blocked_pref_key",
        "purpose:blocked_source",
    }


def test_descriptor_declared_purpose_restriction_is_enforced():
    record = _episodic()
    record.user_id = USER
    descriptor_only = MemoryScopeDescriptor(level="global", allowed_purposes=frozenset({"export"}))
    # wire the descriptor through scope_of_record by monkey-patching per-record
    original = scope_of_record
    import app.services.memory_retrieval_prefilter as module

    try:
        module.scope_of_record = lambda r: descriptor_only
        result = prefilter_candidates([record], _ctx(purpose="llm_context"))
        assert result.rejections[0].reason == "purpose:not_allowed"
        result_export = prefilter_candidates([record], _ctx(purpose="export"))
        assert result_export.allowed == [record]
    finally:
        module.scope_of_record = original


# ---------------------------------------------------------------------------
# Dimension: sensitivity
# ---------------------------------------------------------------------------


def test_sensitivity_ceiling_cut_and_pass():
    record = _episodic()
    record.user_id = USER
    descriptor_only = MemoryScopeDescriptor(level="global", sensitivity="sensitive")
    import app.services.memory_retrieval_prefilter as module

    original = module.scope_of_record
    try:
        module.scope_of_record = lambda r: descriptor_only
        normal_ctx = _ctx(max_sensitivity="normal")
        result = prefilter_candidates([record], normal_ctx)
        assert result.rejections[0].reason == "sensitivity:exceeded"
        assert result.dimension_counts["sensitivity"] == 1

        elevated_ctx = _ctx(max_sensitivity="sensitive")
        assert prefilter_candidates([record], elevated_ctx).allowed == [record]
    finally:
        module.scope_of_record = original


def test_default_sensitivity_is_normal_so_live_records_are_untouched():
    record = _episodic()
    record.user_id = USER
    assert prefilter_candidates([record], _ctx()).allowed == [record]


# ---------------------------------------------------------------------------
# Metrics + result shape
# ---------------------------------------------------------------------------


def test_metric_payload_shape_and_counts():
    legal = _episodic()
    legal.user_id = USER
    revoked = _episodic(revoked_at=NOW)
    revoked.user_id = USER
    wrong = _episodic()
    wrong.user_id = str(uuid4())

    result = prefilter_candidates([legal, revoked, wrong], _ctx())
    assert isinstance(result, PrefilterResult)
    assert result.input_count == 3
    assert result.allowed_count == 1
    assert result.dimension_counts == {
        "user": 1,
        "status": 1,
        "ttl": 0,
        "scope": 0,
        "purpose": 0,
        "sensitivity": 0,
    }
    assert result.reason_counts == {"user:wrong_user": 1, "status:revoked": 1}
    payload = result.to_metric_payload()
    assert payload["version"] == MEMORY_PREFILTER_VERSION
    assert payload["input_count"] == 3
    assert payload["allowed_count"] == 1
    assert payload["reason_counts"]["status:revoked"] == 1


def test_evaluation_order_user_owns_rejection_before_status():
    """Deterministic attribution: user check runs before status check."""
    record = _episodic(revoked_at=NOW)
    record.user_id = str(uuid4())
    result = prefilter_candidates([record], _ctx())
    assert result.rejections[0].dimension == "user"


def test_empty_input_returns_empty_result():
    result = prefilter_candidates([], _ctx())
    assert result.allowed == []
    assert result.input_count == 0
    assert all(v == 0 for v in result.dimension_counts.values())


def test_ctx_anchor_values_mapping_matches_level_anchor_keys():
    """CTX_ANCHOR_VALUES must cover every anchor key used by the lattice."""
    used_keys = {key for keys in LEVEL_ANCHOR_KEYS.values() for key in keys}
    assert used_keys <= set(CTX_ANCHOR_VALUES.keys())


# ---------------------------------------------------------------------------
# R2-F1: unknown scope level fails closed on the DERIVED path
# + derive_scope vocabulary parity guard (M-01 <-> SCOPE_LEVELS)
# ---------------------------------------------------------------------------


def test_unknown_level_from_derive_scope_is_fail_closed(monkeypatch):
    """A level derive_scope emits that this module cannot interpret must NOT
    be lifted to user-global (fail-open). It flows into the descriptor and
    scope_compatible cuts it: scope:unknown_level, metric-observable."""
    import app.services.memory_retrieval_prefilter as module

    record = _episodic()
    record.user_id = USER
    monkeypatch.setattr(module, "derive_scope", lambda r: {"level": "subject"})  # future M-01 vocab

    descriptor = module.scope_of_record(record)
    assert descriptor.level == "subject"  # preserved, never normalized away

    result = prefilter_candidates([record], _ctx())
    assert result.allowed == []
    assert result.rejections[0].dimension == "scope"
    assert result.rejections[0].reason == "scope:unknown_level"
    assert result.dimension_counts["scope"] == 1


def test_derive_scope_level_vocabulary_parity_with_prefilter():
    """Vocabulary parity guard: every scope level M-01's derive_scope can emit
    must be interpretable here. Statically scans the REAL M-01 source (not a
    duplicate constant), so M-01 adding a new level turns this red before any
    record can fail open or be silently cut."""
    import inspect
    import re

    import app.services.memory_epistemic_contract as contract

    source = inspect.getsource(contract.derive_scope)
    literals = set(re.findall(r'["\']level["\']\]\s*=\s*"([a-z_]+)"', source))
    literals |= set(re.findall(r'"level":\s*"([a-z_]+)"', source))
    assert literals, "source scan found no level literals — derive_scope was refactored, update this guard"
    unknown = literals - set(SCOPE_LEVELS)
    assert not unknown, (
        f"M-01 derive_scope now emits scope level(s) {sorted(unknown)} that the M-03 "
        "prefilter cannot interpret — extend SCOPE_LEVELS + SCOPE_COMPATIBILITY "
        "(records with unknown levels fail closed until then)."
    )


# ---------------------------------------------------------------------------
# R2-F2: evaluation order pinned — implementation order is the single authority
# ---------------------------------------------------------------------------


def test_filter_dimensions_order_is_pinned():
    """Reordering FILTER_DIMENSIONS shifts D-06/O-02 dimension_counts
    attribution (same records, different first-failure dimension) and requires
    bumping MEMORY_PREFILTER_VERSION."""
    assert [dimension.value for dimension in FILTER_DIMENSIONS] == [
        "user",
        "status",
        "ttl",
        "scope",
        "purpose",
        "sensitivity",
    ]


def _run_user_before_status_case():
    record = _episodic(revoked_at=NOW)
    record.user_id = str(uuid4())
    return prefilter_candidates([record], _ctx())


def _run_status_before_ttl_case():
    record = _episodic(
        revoked_at=NOW,
        subject_type="commitment",
        decay_policy="due_at+7d",
        due_at=NOW - timedelta(days=30),
    )
    record.user_id = USER
    return prefilter_candidates([record], _ctx())


def _run_ttl_before_scope_case():
    record = _episodic(
        subject_type="self",
        decay_policy="1d",
        created_at=NOW - timedelta(days=1),
    )
    record.user_id = USER
    ctx = _ctx(domain_keys=frozenset({"sports"}))  # self != sports -> scope mismatch too
    return prefilter_candidates([record], ctx)


def _run_scope_before_purpose_case():
    record = _goal(user_id=USER, linked_plan_id=uuid4())
    ctx = _ctx(
        plan_ids=frozenset({str(uuid4())}),  # different plan -> scope mismatch
        permissions=UserMemoryPermissions(enabled=False),  # purpose violation too
    )
    return prefilter_candidates([record], ctx)


def _run_purpose_before_sensitivity_case():
    record = _preference(user_id=USER, pref_key="depth_preference")
    descriptor = MemoryScopeDescriptor(level="global", sensitivity="sensitive")
    import app.services.memory_retrieval_prefilter as module

    original = module.scope_of_record
    try:
        module.scope_of_record = lambda r: descriptor
        return prefilter_candidates(
            [record],
            _ctx(permissions=UserMemoryPermissions(blocked_pref_keys=frozenset({"depth_preference"}))),
        )
    finally:
        module.scope_of_record = original


_ADJACENT_PAIR_RUNNERS = {
    "user_before_status": _run_user_before_status_case,
    "status_before_ttl": _run_status_before_ttl_case,
    "ttl_before_scope": _run_ttl_before_scope_case,
    "scope_before_purpose": _run_scope_before_purpose_case,
    "purpose_before_sensitivity": _run_purpose_before_sensitivity_case,
}


@pytest.mark.parametrize(
    "expected_dimension,case",
    [
        ("user", "user_before_status"),
        ("status", "status_before_ttl"),
        ("ttl", "ttl_before_scope"),
        ("scope", "scope_before_purpose"),
        ("purpose", "purpose_before_sensitivity"),
    ],
)
def test_evaluation_order_adjacent_pairs_are_pinned(expected_dimension, case):
    """Each record violates EXACTLY two adjacent dimensions; the earlier one
    must own the rejection. Any reorder of the evaluation chain flips at least
    one attribution and turns this red (R2-F2: attribution drift guard)."""
    result = _ADJACENT_PAIR_RUNNERS[case]()
    assert len(result.rejections) == 1
    assert result.rejections[0].dimension == expected_dimension
