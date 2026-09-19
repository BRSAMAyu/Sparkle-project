"""M-03 integration tests —— red→green guard for the retrieval pull paths.

Three attack surfaces, the first two asserted BEFORE any semantic/ranking
stage and the third (review rework R1-F2) at the rendered prompt:

1. ``ContextOrchestrator._get_past_session_memory`` (context_manager pull
   path feeding ``past_session_memory`` into the LLM context);
2. ``ContextPackBuilder.build`` (the semantic retrieval path: candidates ->
   rank_items -> semantic gating -> budget trim);
3. ``ContextBuilderMixin._attach_stage34_memory_context`` (main chat payload
   ``episodic_memories`` -> ``format_user_context`` renders the section into
   the system prompt).

RED-phase evidence (captured at base 6f488636 before wiring the prefilter,
see v3-output/M-03/REPORT.md §4; surface 3 red re-captured at 43942d23 in
the review-rework round):
- superseded episodic rows (superseded_by_id) pass ``list_recent_episodic``
  SQL (no such filter) and reach the stage;
- expired commitments (decay_policy="due_at+7d", past horizon) have NO
  consumer anywhere (D4 ledger) and reach the stage;
- superseded preference versions compete with the chain head for injection;
- goals anchored to another plan reach a plan-scoped pack build;
- wrong-user / revoked rows injected at the candidate boundary (any
  non-SQL candidate source) reach the stage unguarded;
- stage34 rendered the same illegal rows into the system prompt section
  【近期相关记忆】(prompts.py ``format_user_context``).

GREEN: after the M-03 prefilter is wired, all of the above are 0.
"""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_manager import ContextOrchestrator
from app.core.context_pack import ContextPackBuilder
from app.models.memory import EpisodicMemory
from app.models.user import User
from app.orchestration.context_builder import ContextBuilderMixin
from app.services.memory_service import MemoryService

NOW_LABEL = "now"


def _utcnow():
    from app.core.time_utils import utcnow

    return utcnow()


async def _create_user(db_session):
    user_id = uuid4()
    user = User(
        id=user_id,
        username=f"user_{user_id.hex[:8]}",
        email=f"{user_id.hex[:8]}@example.com",
        hashed_password="test",
    )
    db_session.add(user)
    await db_session.commit()
    return user_id


async def _add_episodic(db_session, user_id, *, summary, importance=0.9, **overrides):
    record = EpisodicMemory(
        user_id=user_id,
        summary=summary,
        source_type=overrides.pop("source_type", "chat_turn"),
        source_lane=overrides.pop("source_lane", "direct_capture"),
        subject_type=overrides.pop("subject_type", "self"),
        occurred_at=overrides.pop("occurred_at", _utcnow() - timedelta(hours=1)),
        importance_score=importance,
        evidence_refs=[{"type": "user_state", "id": "t"}],
        **overrides,
    )
    db_session.add(record)
    await db_session.commit()
    return record


# ---------------------------------------------------------------------------
# Surface 1: ContextOrchestrator._get_past_session_memory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_live_leaks_superseded_and_expired_commitment(db_session):
    """Rows that TODAY's SQL genuinely returns (real leaks, not mocks):
    superseded + expired commitment must not reach past_session_memory."""
    user_id = await _create_user(db_session)
    now = _utcnow()

    legal = await _add_episodic(db_session, user_id, summary="LEGAL-episodic", importance=0.4)
    superseded = await _add_episodic(db_session, user_id, summary="SUPERSEDED-episodic", importance=0.95)
    superseded.superseded_by_id = uuid4()
    await db_session.commit()
    await _add_episodic(
        db_session,
        user_id,
        summary="EXPIRED-COMMITMENT",
        importance=0.95,
        subject_type="commitment",
        decay_policy="due_at+7d",
        due_at=now - timedelta(days=10),
    )
    fresh_commitment = await _add_episodic(
        db_session,
        user_id,
        summary="FRESH-COMMITMENT",
        importance=0.95,
        subject_type="commitment",
        decay_policy="due_at+7d",
        due_at=now - timedelta(days=2),
    )

    orchestrator = ContextOrchestrator(db_session, None)
    memories = await orchestrator._get_past_session_memory(user_id, limit=10)
    summaries = [m["summary"] for m in memories]

    # M-03 acceptance: illegal candidates are 0 at the semantic input.
    assert "SUPERSEDED-episodic" not in summaries, f"superseded row leaked: {summaries}"
    assert "EXPIRED-COMMITMENT" not in summaries, f"expired commitment leaked: {summaries}"
    # legal candidates survive (both fresh rows).
    assert "LEGAL-episodic" in summaries
    assert "FRESH-COMMITMENT" in summaries
    assert legal is not None and fresh_commitment is not None


@pytest.mark.asyncio
async def test_stage_level_no_guard_for_wrong_user_and_revoked(db_session, monkeypatch):
    """Candidate-source boundary guard: a non-SQL source (or a SQL regression)
    handing wrong-user/revoked rows to the pull path must get 0 through.
    At base 6f488636 this leaks (RED evidence in the M-03 report)."""
    user_id = await _create_user(db_session)
    now = _utcnow()

    wrong_user = await _add_episodic(db_session, uuid4(), summary="WRONG-USER", importance=0.99)
    revoked = await _add_episodic(db_session, user_id, summary="REVOKED", importance=0.99)
    revoked.revoked_at = now
    await db_session.commit()
    legal = await _add_episodic(db_session, user_id, summary="STAGE-LEGAL", importance=0.5)

    async def _fake_pull(self, uid, limit=10, **kwargs):
        return [wrong_user, revoked, legal]

    monkeypatch.setattr(MemoryService, "get_recent_episodic", _fake_pull)

    orchestrator = ContextOrchestrator(db_session, None)
    memories = await orchestrator._get_past_session_memory(user_id, limit=10)
    summaries = [m["summary"] for m in memories]

    assert "WRONG-USER" not in summaries, f"wrong-user row leaked: {summaries}"
    assert "REVOKED" not in summaries, f"revoked row leaked: {summaries}"
    assert "STAGE-LEGAL" in summaries


@pytest.mark.asyncio
async def test_user_settings_permission_layer_enforced_on_read(db_session):
    """user_memory_settings is enforced on writes today but never on reads:
    allow_episodic=False must empty the LLM pull (MEMORY_V3 §3 step 3)."""
    from app.models.user_memory_settings import UserMemorySettings

    user_id = await _create_user(db_session)
    await _add_episodic(db_session, user_id, summary="SHOULD-NOT-SURFACE", importance=0.9)
    db_session.add(
        UserMemorySettings(
            user_id=user_id,
            enabled=True,
            allow_preferences=True,
            allow_goals=True,
            allow_episodic=False,
        )
    )
    await db_session.commit()

    orchestrator = ContextOrchestrator(db_session, None)
    memories = await orchestrator._get_past_session_memory(user_id, limit=10)
    assert memories == [], f"episodic memory injected despite allow_episodic=False: {memories}"


# ---------------------------------------------------------------------------
# Surface 2: ContextPackBuilder.build (semantic retrieval path)
# ---------------------------------------------------------------------------


class _RankCapture:
    """Spy around context_pack.rank_items capturing the candidate lists that
    reach the ranking (== semantic retrieval input)."""

    def __init__(self, original):
        self.original = original
        self.inputs: dict[str, list] = {}

    def __call__(self, items, kind, **kwargs):
        seen = self.inputs.setdefault(kind, [])
        seen_ids = {str(getattr(i, "id", id(i))) for i in seen}
        for item in items:  # rank runs twice (pre/post conflict resolution)
            key = str(getattr(item, "id", id(item)))
            if key not in seen_ids:
                seen.append(item)
                seen_ids.add(key)
        return self.original(items, kind, **kwargs)

    def summaries(self, kind):
        return [str(getattr(i, "summary", "") or "") for i in self.inputs.get(kind, [])]

    def titles(self, kind):
        return [str(getattr(i, "title", "") or "") for i in self.inputs.get(kind, [])]

    def pref_versions(self, kind, pref_key):
        return [i for i in self.inputs.get(kind, []) if getattr(i, "pref_key", None) == pref_key]


@pytest.mark.asyncio
async def test_context_pack_semantic_input_is_prefiltered(db_session, monkeypatch):
    user_id = await _create_user(db_session)
    now = _utcnow()
    plan_a, plan_b = uuid4(), uuid4()

    service = MemoryService(db_session)
    # preference chain: v1 superseded (high evidence) + v2 head
    v1 = await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": "superseded-old"},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    v2 = await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": "head-new"},
        evidence_refs=[{"type": "user_state", "id": "ui", "schema_version": "ui.v1"}],
        confidence=0.9,
        source_type="user_state",
    )
    assert v1 is not None and v2 is not None

    other_goal = await service.create_goal(
        user_id=user_id,
        title="GOAL-OTHER-PLAN",
        status="active",
        linked_plan_id=plan_a,
        evidence_refs=[{"type": "event", "id": "e1"}],
    )
    unlinked_goal = await service.create_goal(
        user_id=user_id,
        title="GOAL-UNLINKED",
        status="active",
        evidence_refs=[{"type": "event", "id": "e2"}],
    )
    this_plan_goal = await service.create_goal(
        user_id=user_id,
        title="GOAL-THIS-PLAN",
        status="active",
        linked_plan_id=plan_b,
        evidence_refs=[{"type": "event", "id": "e3"}],
    )
    assert other_goal and unlinked_goal and this_plan_goal

    expired_commitment = await _add_episodic(
        db_session,
        user_id,
        summary="PACK-EXPIRED-COMMITMENT",
        importance=0.95,
        subject_type="commitment",
        decay_policy="due_at+7d",
        due_at=now - timedelta(days=30),
    )
    superseded_episodic = await _add_episodic(db_session, user_id, summary="PACK-SUPERSEDED", importance=0.95)
    superseded_episodic.superseded_by_id = uuid4()
    await db_session.commit()
    legal_episodic = await _add_episodic(db_session, user_id, summary="PACK-LEGAL", importance=0.5)

    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_PERSONALIZED_RANKING", False, raising=False)

    import app.core.context_pack as context_pack_module

    capture = _RankCapture(context_pack_module.rank_items)
    monkeypatch.setattr(context_pack_module, "rank_items", capture)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 200}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", plan_id=plan_b)

    # --- semantic retrieval input assertions (the card's acceptance) ---
    pref_candidates = capture.pref_versions("preferences", "depth_preference")
    assert len(pref_candidates) == 1, (
        "only the chain head may compete for injection; "
        f"got {[ (p.version, p.pref_value) for p in pref_candidates ]}"
    )
    assert pref_candidates[0].version == v2.version

    goal_titles = capture.titles("goals")
    assert "GOAL-OTHER-PLAN" not in goal_titles, f"cross-plan goal leaked: {goal_titles}"
    assert "GOAL-THIS-PLAN" in goal_titles
    assert "GOAL-UNLINKED" in goal_titles  # unanchored goal behaves user-global

    episodic_summaries = capture.summaries("episodic")
    assert "PACK-EXPIRED-COMMITMENT" not in episodic_summaries
    assert "PACK-SUPERSEDED" not in episodic_summaries
    assert "PACK-LEGAL" in episodic_summaries
    assert legal_episodic is not None and expired_commitment is not None

    # --- end-to-end payload follows the same law ---
    assert pack.preferences.get("depth_preference") == {"value": "head-new"}
    pack_goal_titles = [g["title"] for g in pack.goals]
    assert "GOAL-OTHER-PLAN" not in pack_goal_titles
    pack_episodic = [m["summary"] for m in pack.episodic_memories]
    assert "PACK-EXPIRED-COMMITMENT" not in pack_episodic
    assert "PACK-SUPERSEDED" not in pack_episodic


@pytest.mark.asyncio
async def test_context_pack_user_settings_permissions(db_session, monkeypatch):
    from app.models.user_memory_settings import UserMemorySettings

    user_id = await _create_user(db_session)
    service = MemoryService(db_session)
    await service.upsert_preference(
        user_id=user_id,
        pref_key="depth_preference",
        pref_value={"value": "blocked-key"},
        evidence_refs=[{"type": "user_state", "id": "ui"}],
        source_type="user_state",
    )
    await service.upsert_preference(
        user_id=user_id,
        pref_key="curiosity_preference",
        pref_value={"value": "allowed-key"},
        evidence_refs=[{"type": "user_state", "id": "ui"}],
        source_type="user_state",
    )
    db_session.add(
        UserMemorySettings(
            user_id=user_id,
            enabled=True,
            allow_preferences=True,
            allow_goals=True,
            allow_episodic=True,
            blocked_pref_keys=["depth_preference"],
        )
    )
    await db_session.commit()

    monkeypatch.setattr(settings, "ENABLE_LTM_ROLLOUT", False, raising=False)
    monkeypatch.setattr(settings, "ENABLE_CONTEXT_RANKING", True, raising=False)
    monkeypatch.setattr(settings, "ENABLE_MEMORY_CONFLICT_RESOLUTION", False, raising=False)

    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 200}})
    builder = ContextPackBuilder(db_session, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat")

    assert "curiosity_preference" in pack.preferences
    assert "depth_preference" not in pack.preferences, f"blocked_pref_keys leaked into LLM context: {pack.preferences}"


# ---------------------------------------------------------------------------
# Surface 3 (review rework R1-F2): stage34 context_builder -> system prompt
# ---------------------------------------------------------------------------


class _Stage34Host(ContextBuilderMixin):
    """Minimal mixin host: _attach_stage34_memory_context only needs .redis
    (MemoryService(db_session, self.redis)); plan/goal pulls return empty on
    a clean DB and the kill-switch payload has a settings fallback."""

    def __init__(self):
        self.redis = None


@pytest.mark.asyncio
async def test_stage34_episodic_prompt_injection_is_prefiltered(db_session):
    """stage34 writes payload["episodic_memories"], which the main chat prompt
    renders verbatim into the system prompt section 【近期相关记忆】
    (prompts.format_user_context). superseded / expired-commitment rows must
    be 0 at BOTH the payload and the rendered prompt."""
    user_id = await _create_user(db_session)
    now = _utcnow()

    superseded = await _add_episodic(db_session, user_id, summary="STAGE34-SUPERSEDED", importance=0.99)
    superseded.superseded_by_id = uuid4()
    await db_session.commit()
    await _add_episodic(
        db_session,
        user_id,
        summary="STAGE34-EXPIRED",
        importance=0.99,
        subject_type="commitment",
        decay_policy="due_at+7d",
        due_at=now - timedelta(days=30),
    )
    legal = await _add_episodic(db_session, user_id, summary="STAGE34-LEGAL", importance=0.5)

    host = _Stage34Host()
    payload = await host._attach_stage34_memory_context(
        {"cognitive_context": {}},
        user_id=str(user_id),
        db_session=db_session,
    )

    summaries = [m["summary"] for m in payload["episodic_memories"]]
    assert "STAGE34-SUPERSEDED" not in summaries, f"superseded row leaked into stage34 prompt payload: {summaries}"
    assert "STAGE34-EXPIRED" not in summaries, f"expired commitment leaked into stage34 prompt payload: {summaries}"
    assert "STAGE34-LEGAL" in summaries

    from app.orchestration.prompts import format_user_context

    rendered = format_user_context({"episodic_memories": payload["episodic_memories"]})
    assert "STAGE34-SUPERSEDED" not in rendered, "superseded row reached the rendered system prompt"
    assert "STAGE34-EXPIRED" not in rendered, "expired commitment reached the rendered system prompt"
    assert "STAGE34-LEGAL" in rendered
    assert legal is not None


@pytest.mark.asyncio
async def test_stage34_user_settings_permissions(db_session):
    """allow_episodic=False must empty the stage34 episodic prompt section
    (read-side permission enforcement on the third LLM injection surface)."""
    from app.models.user_memory_settings import UserMemorySettings

    user_id = await _create_user(db_session)
    await _add_episodic(db_session, user_id, summary="STAGE34-SHOULD-NOT-SURFACE", importance=0.9)
    db_session.add(
        UserMemorySettings(
            user_id=user_id,
            enabled=True,
            allow_preferences=True,
            allow_goals=True,
            allow_episodic=False,
        )
    )
    await db_session.commit()

    host = _Stage34Host()
    payload = await host._attach_stage34_memory_context({}, user_id=str(user_id), db_session=db_session)
    assert payload["episodic_memories"] == [], (
        f"episodic memory reached the stage34 prompt payload despite allow_episodic=False: "
        f"{payload['episodic_memories']}"
    )
