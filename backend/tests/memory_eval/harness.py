"""M-09 harness — drives the REAL merged memory chain on isolated sqlite.

Nothing in the memory chain is mocked. The harness only:

1. owns the sqlite environment (in-memory engine, ``Base.metadata.create_all``,
   one fresh deterministic user per case);
2. replays the case timeline through the production write/correction/delete
   entrypoints (``MemoryService`` / ``MemoryInferredWriteLaneService``), which
   internally run the M-02 storage gate, M-04 conflict arbitration and the
   M-07 invalidation pipeline;
3. probes the production read chain (``ContextPackBuilder.build`` = SQL pull ->
   M-03 prefilter -> rank -> budget -> M-05 selfcheck) and renders the real
   prompt section via ``format_user_context``;
4. runs the paired no-history arm (fresh user, same probe, empty memory);
5. simulates the passage of wall-clock time (``time_advance``) by shifting a
   case's already-written rows backwards — the ONLY harness-side DB mutation
   besides the real service writes. Memory behavior is never mocked.

The simulated layer is exactly the LLM extraction decision (which candidate a
chat turn yields — encoded in the case JSON) — see module docstring of
``memory_eval_schema``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Circular-import guard: importing app.models FIRST (before app.core.
# context_pack) fully initializes the model registry and avoids the
# context_pack -> plan_context -> models -> aurora -> prompts -> plan_context
# cycle — the same order the pytest conftest relies on. Keep this import
# statement above the from-imports (sorter-compliant position).
import app.models  # noqa: F401
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.core.time_utils import utcnow
from app.models.base import Base
from app.models.memory import EpisodicMemory, MemoryGoal, MemoryPreference
from app.models.user import User
from app.models.user_memory_settings import UserMemorySettings
from app.orchestration.prompts import format_user_context
from app.services.memory_inferred_write_lane import (
    InferredEpisodicCandidate,
    MemoryInferredWriteLaneService,
)
from app.services.memory_service import MemoryService

from .memory_eval_schema import Case

# Deterministic user ids: the suite is identity-reproducible across runs.
_EVAL_NAMESPACE = uuid.UUID("a5d0f7de-09c9-4f0a-9b6b-11f0e6d09c09")

# Budgets are generous on purpose: budget trimming is NOT the eval target —
# the prefilter / arbitration / selfcheck decisions are. A must_use marker
# lost to budget would be a false signal.
PROBE_BUDGETS = {"chat": {"preferences": 600, "goals": 300, "episodic": 600}}


def _ensure_full_model_registry() -> None:
    """``Base.metadata.create_all`` needs every model registered. The pytest
    conftest performs that registration for test runs; mirror it for CLI/runner
    invocations by importing the conftest module (idempotent)."""
    import tests.conftest  # noqa: F401  (side-effect: completes model registry)


@dataclass
class WriteTrace:
    alias: str
    event_type: str
    outcome: str  # stored | vetoed | rejected | duplicate | none | applied
    record_id: str | None = None
    detail: str = ""


@dataclass
class ProbeSnapshot:
    query: str
    rendered_prompt: str
    face_preferences: dict[str, Any]
    face_episodic_summaries: list[str]
    face_goal_titles: list[str]
    selfcheck_internal_only: int
    prefilter_rejections: int
    decision_item_count: int = 0

    def corpus(self) -> str:
        """The LLM-layer boundary: everything the memory chain surfaced for
        this turn — the structured face (``pack.to_prompt_context()``:
        preference values / episodic summaries / goal titles — the same
        boundary M-05's OP-Bench grades) PLUS the rendered prompt text.
        Forbidden content must appear in neither; required content counts if
        present in either. ``metadata`` is excluded: internal_only entries
        are ids+closed reasons by design (M-05 content-free contract), and
        decision-context recall is the sanctioned two-tier use, not a leak."""
        import json as _json

        parts: list[str] = [self.rendered_prompt]
        for key, value in self.face_preferences.items():
            parts.append(f"{key}={_json.dumps(value, ensure_ascii=False, default=str)}")
        parts.extend(self.face_episodic_summaries)
        parts.extend(self.face_goal_titles)
        return "\n".join(parts)


@dataclass
class CaseOutcome:
    case: Case
    user_id: str
    with_memory: ProbeSnapshot | None = None
    no_history: ProbeSnapshot | None = None
    writes: list[WriteTrace] = field(default_factory=list)
    error: str | None = None

    @property
    def case_id(self) -> str:
        return self.case.case_id


class EvalEnvironment:
    """Shared in-memory sqlite engine; one AsyncSession per case."""

    def __init__(self) -> None:
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        self._created = False
        # Deterministic clock anchor: every case offset is relative to this.
        self.run_started_at = utcnow()

    async def ensure_schema(self) -> None:
        if not self._created:
            _ensure_full_model_registry()
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._created = True

    def clock_at(self, offset_h: float) -> datetime:
        return self.run_started_at + timedelta(hours=float(offset_h))

    def new_session(self) -> AsyncSession:
        return self.session_factory()

    async def create_user(self, db: AsyncSession, key: str) -> uuid.UUID:
        user_id = uuid.uuid5(_EVAL_NAMESPACE, key)
        db.add(
            User(
                id=user_id,
                username=f"m09_{key.lower()}",
                email=f"{key.lower()}@m09.eval",
                hashed_password="m09-eval",
            )
        )
        await db.commit()
        return user_id

    async def dispose(self) -> None:
        await self.engine.dispose()


class TimelineExecutor:
    """Replays one case's session timeline through the production services."""

    def __init__(self, env: EvalEnvironment, case: Case, other_user_id: uuid.UUID | None = None):
        self.env = env
        self.case = case
        self.traces: list[WriteTrace] = []
        self._records: dict[str, tuple[str, uuid.UUID]] = {}  # alias -> (kind, id)
        # Secondary user for shared-device (wrong-user) shapes: events with
        # ``owner: "other"`` write to this user; the probe always runs on the
        # primary user, asserting cross-user isolation end-to-end.
        self.other_user_id = other_user_id

    async def run(self, db: AsyncSession, user_id: uuid.UUID) -> list[WriteTrace]:
        for session in self.case.sessions:
            for event in session.get("events", []):
                owner_id = user_id
                if str(event.get("owner", "self")) == "other":
                    if self.other_user_id is None:
                        raise ValueError("owner=other used without a shared-device other user")
                    owner_id = self.other_user_id
                await self._apply(db, owner_id, str(session["session_id"]), event)
        return self.traces

    # --- event application ----------------------------------------------------

    async def _apply(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: str,
        event: dict[str, Any],
    ) -> None:
        etype = event["type"]
        handler = getattr(self, f"_evt_{etype}")
        await handler(db, user_id, session_id, event)

    def _evidence_refs(self, session_id: str, alias: str) -> list[dict[str, str]]:
        return [
            {
                "type": "user_state",
                "id": f"{self.case.case_id}:{session_id}:{alias}",
                "schema_version": "m09.eval.v1",
            }
        ]

    async def _evt_write_preference(
        self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]
    ) -> None:
        service = MemoryService(db)
        record = await service.upsert_preference(
            user_id=user_id,
            pref_key=event["pref_key"],
            pref_value={"value": event["value"]},
            evidence_refs=self._evidence_refs(session_id, event["alias"]),
            confidence=event.get("confidence", 0.92),
            source_type=event.get("source_type", "user_state"),
        )
        outcome = "stored" if record is not None else "none"
        self.traces.append(
            WriteTrace(
                alias=event["alias"],
                event_type="write_preference",
                outcome=outcome,
                record_id=str(record.id) if record else None,
            )
        )
        if record is not None:
            self._records[event["alias"]] = ("preference", record.id)

    async def _evt_write_episodic(
        self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]
    ) -> None:
        occurred_at = self.env.clock_at(event.get("occurred_at_offset_h", self._session_offset(session_id)))
        due_at = self.env.clock_at(event["due_at_offset_h"]) if event.get("due_at_offset_h") is not None else None
        summary = event["summary"]
        if event.get("via") == "lane":
            await self._write_via_lane(db, user_id, session_id, event, summary, occurred_at, due_at)
            return
        service = MemoryService(db)
        record = await service.create_episodic_memory(
            user_id=user_id,
            summary=summary,
            source_type="user_state",
            source_id=f"{self.case.case_id}:{session_id}",
            occurred_at=occurred_at,
            importance_score=event.get("confidence", 0.92),
            tags=[f"m09:{self.case.case_id}"],
            evidence_refs=self._evidence_refs(session_id, event["alias"]),
            confidence=event.get("confidence", 0.92),
            decay_policy=event.get("decay_policy"),
            semantic_key=event.get("semantic_key"),
            subject_type=event.get("subject_type", "self"),
            due_at=due_at,
            mentioned_entity_hash=event.get("mentioned_entity_hash"),
            emit_system_update=False,
        )
        self.traces.append(
            WriteTrace(
                alias=event["alias"],
                event_type="write_episodic",
                outcome="stored" if record is not None else "vetoed",
                record_id=str(record.id) if record else None,
            )
        )
        if record is not None:
            self._records[event["alias"]] = ("episodic", record.id)

    async def _write_via_lane(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: str,
        event: dict[str, Any],
        summary: str,
        occurred_at: datetime,
        due_at: datetime | None,
    ) -> None:
        """Production inferred lane: RuleY validation -> dedup -> M-04 conflict
        arbitration -> M-02 storage gate -> L1."""
        alias = event["alias"]
        evidence_token = f"m09:{self.case.case_id}:{alias}"
        semantic_key = event.get("semantic_key") or f"m09:{self.case.case_id}:{alias}"
        candidate = InferredEpisodicCandidate(
            candidate_text=summary,
            subject_type=event.get("subject_type", "self"),
            confidence=float(event.get("confidence", 0.92)),
            evidence_token=evidence_token,
            decay_policy=event.get("decay_policy", "30d"),
            source_lane=MemoryInferredWriteLaneService.SOURCE_LANE,
            semantic_key=semantic_key,
            evidence_refs=self._evidence_refs(session_id, alias),
            occurred_at=occurred_at,
            due_at=due_at,
            mentioned_entity_hash=event.get("mentioned_entity_hash"),
            mentioned_entity_owner_user_id=None,
        )
        lane = MemoryInferredWriteLaneService(db)
        record = await lane.write_candidate_to_l1(
            user_id=user_id,
            session_id=uuid.uuid5(_EVAL_NAMESPACE, f"{self.case.case_id}:{session_id}"),
            candidate=candidate,
            bypass_min_confidence=False,
            source_type="chat",
        )
        if record is not None:
            outcome = "stored"
        elif event.get("expect_veto"):
            outcome = "vetoed"
        else:
            outcome = "rejected"
        self.traces.append(
            WriteTrace(
                alias=alias,
                event_type="write_episodic",
                outcome=outcome,
                record_id=str(record.id) if record else None,
            )
        )
        if record is not None:
            self._records[alias] = ("episodic", record.id)

    async def _evt_write_goal(
        self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]
    ) -> None:
        service = MemoryService(db)
        expires_at = (
            self.env.clock_at(event["expires_at_offset_h"]) if event.get("expires_at_offset_h") is not None else None
        )
        record = await service.create_goal(
            user_id=user_id,
            title=event["title"],
            status="active",
            expires_at=expires_at,
            evidence_refs=self._evidence_refs(session_id, event["alias"]),
            source_type="user_state",
        )
        self.traces.append(
            WriteTrace(
                alias=event["alias"],
                event_type="write_goal",
                outcome="stored" if record is not None else "none",
                record_id=str(record.id) if record else None,
            )
        )
        if record is not None:
            self._records[event["alias"]] = ("goal", record.id)

    async def _evt_correct(self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]) -> None:
        kind, memory_id = self._records[event["target"]]
        service = MemoryService(db)
        record = await service.apply_correction(
            kind=kind,
            memory_id=memory_id,
            user_id=user_id,
            action=event["action"],
            reason=event.get("reason"),
        )
        self.traces.append(
            WriteTrace(
                alias=event["target"],
                event_type="correct",
                outcome="applied" if record is not None else "none",
            )
        )

    async def _evt_revoke(self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]) -> None:
        kind, memory_id = self._records[event["target"]]
        _require_episodic(kind, "revoke")
        service = MemoryService(db)
        record = await service.revoke_episodic_memory(user_id=user_id, memory_id=memory_id, reason=event.get("reason"))
        self.traces.append(
            WriteTrace(
                alias=event["target"],
                event_type="revoke",
                outcome="applied" if record is not None else "none",
            )
        )

    async def _evt_retract(self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]) -> None:
        kind, memory_id = self._records[event["target"]]
        service = MemoryService(db)
        ok = await service.retract_memory(kind=kind, memory_id=memory_id, user_id=user_id, reason=event.get("reason"))
        self.traces.append(
            WriteTrace(
                alias=event["target"],
                event_type="retract",
                outcome="applied" if ok else "none",
            )
        )

    async def _evt_memory_settings(
        self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]
    ) -> None:
        row = UserMemorySettings(
            user_id=user_id,
            enabled=True,
            allow_preferences=event.get("allow_preferences", True),
            allow_goals=event.get("allow_goals", True),
            allow_episodic=event.get("allow_episodic", True),
            allow_inferred_episodic=event.get("allow_inferred_episodic", True),
            blocked_pref_keys=list(event.get("blocked_pref_keys", [])),
            blocked_sources=[],
        )
        db.add(row)
        await db.commit()
        self.traces.append(WriteTrace(alias="(settings)", event_type="memory_settings", outcome="applied"))

    async def _evt_time_advance(
        self, db: AsyncSession, user_id: uuid.UUID, session_id: str, event: dict[str, Any]
    ) -> None:
        """Wall-clock simulation: shift this case's rows back by N days so the
        read-side TTL/status logic (M-03 ttl:expired / ttl:today_only_expired,
        M-01 status machine) observes elapsed time. This mutates only
        timestamps of rows that the REAL services wrote (ORM per-row: sqlite
        has no datetime column arithmetic); it never fabricates or alters
        memory content/decisions."""
        from datetime import timedelta as _td

        from sqlalchemy import select

        delta = _td(days=float(event["days"]))
        touched = 0
        for model in (EpisodicMemory, MemoryPreference, MemoryGoal):
            rows = (await db.execute(select(model).where(model.user_id == user_id))).scalars().all()
            for row in rows:
                for column in ("created_at", "updated_at", "occurred_at", "due_at", "expires_at"):
                    value = getattr(row, column, None)
                    if isinstance(value, datetime):
                        setattr(row, column, value - delta)
                        touched += 1
        await db.commit()
        self.traces.append(
            WriteTrace(
                alias="(clock)",
                event_type="time_advance",
                outcome=f"shifted -{event['days']}d on {touched} timestamps",
            )
        )

    def _session_offset(self, session_id: str) -> float:
        for session in self.case.sessions:
            if session["session_id"] == session_id:
                return float(session["at_offset_h"])
        return 0.0


def _require_episodic(kind: str, action: str) -> None:
    if kind != "episodic":
        raise ValueError(f"{action} is only defined for episodic aliases, got {kind}")


# --- probe ---------------------------------------------------------------------


async def probe(
    env: EvalEnvironment,
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
) -> ProbeSnapshot:
    """Run the production read chain for one probe turn."""
    scheduler = ContextBudgetScheduler(budgets=dict(PROBE_BUDGETS))
    builder = ContextPackBuilder(db, scheduler=scheduler)
    pack = await builder.build(user_id, intent="chat", query_text=query)
    rendered = format_user_context(pack.to_prompt_context())
    metadata = pack.metadata or {}
    selfcheck = metadata.get("memory_selfcheck") or {}
    prefilter_sections = (metadata.get("memory_prefilter") or {}).get("sections") or {}
    prefilter_rejections = sum(
        max(0, int(section.get("input_count", 0)) - int(section.get("allowed_count", 0)))
        for section in prefilter_sections.values()
        if isinstance(section, dict)
    )
    decision = pack.decision_context
    decision_items = list(decision.items) if decision is not None else []
    return ProbeSnapshot(
        query=query,
        rendered_prompt=rendered,
        face_preferences=dict(pack.preferences),
        face_episodic_summaries=[str(m.get("summary", "")) for m in pack.episodic_memories],
        face_goal_titles=[str(g.get("title", "")) for g in pack.goals],
        selfcheck_internal_only=len(selfcheck.get("internal_only", [])),
        prefilter_rejections=prefilter_rejections,
        decision_item_count=len(decision_items),
    )


async def run_case(env: EvalEnvironment, case: Case) -> CaseOutcome:
    """With-memory arm + paired no-history arm for one case."""
    await env.ensure_schema()
    outcome = CaseOutcome(case=case, user_id="")
    try:
        async with env.new_session() as db:
            user_key = f"{case.persona_id}:{case.case_id}"
            user_id = await env.create_user(db, user_key)
            outcome.user_id = str(user_id)
            has_other_owner = any(
                str(event.get("owner", "self")) == "other"
                for session in case.sessions
                for event in session.get("events", [])
            )
            other_user_id = await env.create_user(db, f"{user_key}:other") if has_other_owner else None
            executor = TimelineExecutor(env, case, other_user_id=other_user_id)
            outcome.writes = await executor.run(db, user_id)
            outcome.with_memory = await probe(env, db, user_id, case.probe["query"])
        if case.paired_enabled:
            async with env.new_session() as db:
                baseline_user = await env.create_user(db, f"{case.persona_id}:{case.case_id}:nohistory")
                outcome.no_history = await probe(env, db, baseline_user, case.probe["query"])
    except Exception as exc:  # noqa: BLE001 — outcome must carry the failure, not crash the suite
        outcome.error = f"{type(exc).__name__}: {exc}"
    return outcome


async def run_suite(env: EvalEnvironment | None, cases: list[Case]) -> list[CaseOutcome]:
    owned = env is None
    environment = env or EvalEnvironment()
    try:
        outcomes = []
        for case in cases:
            outcomes.append(await run_case(environment, case))
        return outcomes
    finally:
        if owned:
            await environment.dispose()


def write_traces_summary(outcome: CaseOutcome) -> list[dict[str, str]]:
    return [{"alias": t.alias, "type": t.event_type, "outcome": t.outcome} for t in outcome.writes]
