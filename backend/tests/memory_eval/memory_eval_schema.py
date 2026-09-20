"""M-09 evaluation case schema — FROZEN.

``SCHEMA_VERSION`` pins the machine-readable case contract. Any change to
the vocabularies below is a schema change: bump the version, regenerate the
matrix guard expectations, and re-run the full suite (same discipline as
M-05 ``SELF_CHECK_VERSION``).

Case file layout (one file per persona under ``cases/``)::

    {
      "schema_version": "m09-memory-eval.v1",
      "persona": {"persona_id": "P01", "name": "...", "domain": "..."},
      "cases": [ <case>, ... ]
    }

Case::

    {
      "case_id": "P01-D1-evening_plan",        # ^P\\d{2}-D[1-5]-[a-z0-9_]+$
      "dimension": "D1_valid_use",             # frozen vocabulary
      "description": "...",
      "sessions": [                            # 2..4 sessions, chronological
        {
          "session_id": "s1",
          "at_offset_h": -72,                  # hours relative to eval run start
          "events": [ <event>, ... ]
        }, ...
      ],
      "probe": {"query": "...", "at_offset_h": 0},
      "expectations": {
        "must_use": ["晚上"],                   # MUST appear in rendered prompt
        "must_not_use": ["清晨五点"],            # MUST NOT appear (invalid use)
        "may_use": [],                          # either way; counts as valid use
        "overpersonalization_watch": false,     # probe is phatic / off-topic:
        "personal_watch_markers": []            # any of these surfacing = overpersonalization
      },
      "paired": {"enabled": true},
      "real_model": {"key_case": false, "must_mention": [], "must_not_mention": []}
    }

Event vocabulary (frozen)::

    write_preference {alias, pref_key, value, source_type?, confidence?}
        -> MemoryService.upsert_preference (real M-01 guard + M-07 supersede chain)
    write_episodic  {alias, summary, via: lane|explicit, confidence?, semantic_key?,
                     subject_type?, decay_policy?, due_at_offset_h?, occurred_at_offset_h?,
                     mentioned_entity_hash?}
        via=lane     -> MemoryInferredWriteLaneService.write_candidate_to_l1
                        (real M-02 rule tier + M-04 arbitration + M-02 gate)
        via=explicit -> MemoryService.create_episodic_memory(source_lane=direct_capture,
                        source_type=user_state) — the explicit user-stated lane
    write_goal      {alias, title, linked_plan_key?, expires_at_offset_h?}
    correct         {target, action: reject|no_longer_applicable|lower_confidence, reason?}
                        -> MemoryService.apply_correction (real M-07 pipeline)
    revoke          {target, reason?}
                        -> MemoryService.revoke_episodic_memory (user delete, real M-07)
    retract         {target, reason?}
                        -> MemoryService.retract_memory (panel delete, real M-07)
    memory_settings {allow_episodic?, blocked_pref_keys?}
                        -> user_memory_settings row (read-side M-03 permission input)
    time_advance    {days}
                        -> wall-clock simulation: shifts the case's already-written
                           rows (created_at / occurred_at / due_at) back by N days so
                           read-side TTL logic observes elapsed time. This is the ONLY
                           harness-side DB mutation besides real service writes; memory
                           behavior is never mocked.

The only simulated layer is the LLM extraction decision (which candidate a
chat turn yields — encoded in the case JSON by the author) and, for the 25
budgeted calls, the real-model answer probe.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "m09-memory-eval.v1"

# --- frozen vocabularies -----------------------------------------------------

DIMENSIONS: frozenset[str] = frozenset(
    {
        "D1_valid_use",  # 正确使用：应该用的记忆被用于回答
        "D2_correct_non_use",  # 正确不用：不该用的记忆没有出现
        "D3_correction_effective",  # 纠正生效：纠正后旧值不再出现、新值生效
        "D4_deletion_effective",  # 删除生效：删除后内容不再复活（含诱导找回）
        "D5_preference_change_tracked",  # 偏好变化跟踪：版本链推进、链头胜出
    }
)

DIMENSION_ORDER: tuple[str, ...] = (
    "D1_valid_use",
    "D2_correct_non_use",
    "D3_correction_effective",
    "D4_deletion_effective",
    "D5_preference_change_tracked",
)

EVENT_TYPES: frozenset[str] = frozenset(
    {
        "write_preference",
        "write_episodic",
        "write_goal",
        "correct",
        "revoke",
        "retract",
        "memory_settings",
        "time_advance",
    }
)

EPISODIC_WRITE_VIAS: frozenset[str] = frozenset({"lane", "explicit"})
CORRECTION_ACTIONS: frozenset[str] = frozenset({"reject", "no_longer_applicable", "lower_confidence"})

MAX_SESSIONS = 4
MIN_SESSIONS = 2
MAX_EVENTS_PER_SESSION = 8

_CASE_ID_RE = re.compile(r"^P\d{2}-D[1-5]-[a-z0-9_]+$")
_SESSION_ID_RE = re.compile(r"^s\d+$")
_ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]*$")

REQUIRED_PERSONA_COUNT = 10
MIN_TOTAL_CASES = 80


class SchemaError(ValueError):
    """Raised when a case file deviates from the frozen schema."""


@dataclass(frozen=True)
class Persona:
    persona_id: str
    name: str
    domain: str


@dataclass
class Expectations:
    must_use: list[str]
    must_not_use: list[str]
    may_use: list[str]
    overpersonalization_watch: bool = False
    personal_watch_markers: list[str] = field(default_factory=list)


@dataclass
class RealModelSpec:
    key_case: bool = False
    must_mention: list[str] = field(default_factory=list)
    must_not_mention: list[str] = field(default_factory=list)


@dataclass
class Case:
    case_id: str
    persona_id: str
    dimension: str
    description: str
    sessions: list[dict[str, Any]]
    probe: dict[str, Any]
    expectations: Expectations
    paired_enabled: bool = True
    real_model: RealModelSpec = field(default_factory=RealModelSpec)

    @property
    def session_count(self) -> int:
        return len(self.sessions)

    @property
    def event_count(self) -> int:
        return sum(len(s.get("events", [])) for s in self.sessions)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SchemaError(message)


def _validate_markers(markers: Any, label: str, case_id: str) -> list[str]:
    _require(isinstance(markers, list), f"{case_id}: expectations.{label} must be a list")
    result: list[str] = []
    for marker in markers:
        _require(
            isinstance(marker, str) and marker.strip() and len(marker) >= 2,
            f"{case_id}: {label} marker must be a non-empty string of >=2 chars, got {marker!r}",
        )
        result.append(marker)
    _require(len(set(result)) == len(result), f"{case_id}: {label} contains duplicate markers")
    return result


def parse_case(raw: dict[str, Any], persona_id: str) -> Case:
    case_id = raw.get("case_id")
    _require(isinstance(case_id, str) and _CASE_ID_RE.match(case_id), f"bad case_id: {case_id!r}")
    _require(
        case_id.startswith(f"{persona_id}-"),
        f"{case_id}: case_id prefix must match persona {persona_id}",
    )
    dimension = raw.get("dimension")
    _require(dimension in DIMENSIONS, f"{case_id}: unknown dimension {dimension!r}")
    _require(isinstance(raw.get("description"), str) and raw["description"].strip(), f"{case_id}: description required")

    sessions = raw.get("sessions")
    _require(
        isinstance(sessions, list) and MIN_SESSIONS <= len(sessions) <= MAX_SESSIONS,
        f"{case_id}: sessions must be a list of {MIN_SESSIONS}..{MAX_SESSIONS}",
    )
    seen_sessions: set[str] = set()
    last_offset = None
    aliases: dict[str, str] = {}  # alias -> event type kind
    for session in sessions:
        _require(isinstance(session, dict), f"{case_id}: session must be an object")
        sid = session.get("session_id")
        _require(isinstance(sid, str) and _SESSION_ID_RE.match(sid), f"{case_id}: bad session_id {sid!r}")
        _require(sid not in seen_sessions, f"{case_id}: duplicate session_id {sid}")
        seen_sessions.add(sid)
        offset = session.get("at_offset_h")
        _require(isinstance(offset, (int, float)), f"{case_id}/{sid}: at_offset_h must be numeric")
        _require(last_offset is None or offset >= last_offset, f"{case_id}/{sid}: sessions must be chronological")
        last_offset = offset
        events = session.get("events", [])
        _require(
            isinstance(events, list) and len(events) <= MAX_EVENTS_PER_SESSION,
            f"{case_id}/{sid}: events must be a list of <= {MAX_EVENTS_PER_SESSION}",
        )
        for event in events:
            _validate_event(event, case_id, sid, aliases)

    probe = raw.get("probe")
    _require(isinstance(probe, dict), f"{case_id}: probe required")
    _require(isinstance(probe.get("query"), str) and probe["query"].strip(), f"{case_id}: probe.query required")
    probe_offset = probe.get("at_offset_h", 0)
    _require(isinstance(probe_offset, (int, float)), f"{case_id}: probe.at_offset_h must be numeric")
    _require(last_offset is None or probe_offset >= last_offset, f"{case_id}: probe must not precede the last session")

    exp_raw = raw.get("expectations")
    _require(isinstance(exp_raw, dict), f"{case_id}: expectations required")
    must_use = _validate_markers(exp_raw.get("must_use", []), "must_use", case_id)
    must_not_use = _validate_markers(exp_raw.get("must_not_use", []), "must_not_use", case_id)
    may_use = _validate_markers(exp_raw.get("may_use", []), "may_use", case_id)
    overlap = (set(must_use) & set(must_not_use)) | (set(may_use) & set(must_not_use)) | (set(must_use) & set(may_use))
    _require(not overlap, f"{case_id}: expectation marker sets overlap: {sorted(overlap)}")
    watch = bool(exp_raw.get("overpersonalization_watch", False))
    watch_markers = _validate_markers(exp_raw.get("personal_watch_markers", []), "personal_watch_markers", case_id)
    _require(not watch or watch_markers, f"{case_id}: overpersonalization_watch requires personal_watch_markers")

    rm_raw = raw.get("real_model", {}) or {}
    _require(isinstance(rm_raw, dict), f"{case_id}: real_model must be an object")
    real_model = RealModelSpec(
        key_case=bool(rm_raw.get("key_case", False)),
        must_mention=_validate_markers(rm_raw.get("must_mention", []), "real_model.must_mention", case_id),
        must_not_mention=_validate_markers(rm_raw.get("must_not_mention", []), "real_model.must_not_mention", case_id),
    )
    _require(
        not real_model.key_case or real_model.must_not_mention,
        f"{case_id}: key_case needs must_not_mention for answer grading "
        "(must_mention may be empty for pure avoid-cases, e.g. D2 phatic probes)",
    )

    return Case(
        case_id=case_id,
        persona_id=persona_id,
        dimension=dimension,
        description=str(raw["description"]),
        sessions=sessions,
        probe=probe,
        expectations=Expectations(
            must_use=must_use,
            must_not_use=must_not_use,
            may_use=may_use,
            overpersonalization_watch=watch,
            personal_watch_markers=watch_markers,
        ),
        paired_enabled=bool(raw.get("paired", {}).get("enabled", True)),
        real_model=real_model,
    )


def _validate_event(event: dict[str, Any], case_id: str, sid: str, aliases: dict[str, str]) -> None:
    etype = event.get("type")
    _require(etype in EVENT_TYPES, f"{case_id}/{sid}: unknown event type {etype!r}")
    if etype in {"write_preference", "write_episodic", "write_goal"}:
        alias = event.get("alias")
        _require(isinstance(alias, str) and _ALIAS_RE.match(alias), f"{case_id}/{sid}: bad alias {alias!r}")
        _require(alias not in aliases, f"{case_id}/{sid}: duplicate alias {alias}")
        aliases[alias] = etype
        owner = event.get("owner", "self")
        _require(owner in {"self", "other"}, f"{case_id}/{sid}: owner must be self|other")
    elif etype in {"correct", "revoke", "retract"}:
        target = event.get("target")
        _require(
            isinstance(target, str) and target in aliases,
            f"{case_id}/{sid}: {etype} target {target!r} must reference an earlier alias",
        )
    if etype == "write_preference":
        _require(isinstance(event.get("pref_key"), str) and event["pref_key"], f"{case_id}/{sid}: pref_key required")
        _require(event.get("value") is not None, f"{case_id}/{sid}: value required")
        if "confidence" in event:
            _require(isinstance(event["confidence"], (int, float)), f"{case_id}/{sid}: confidence numeric")
    if etype == "write_episodic":
        _require(
            isinstance(event.get("summary"), str) and event["summary"].strip(), f"{case_id}/{sid}: summary required"
        )
        _require(event.get("via") in EPISODIC_WRITE_VIAS, f"{case_id}/{sid}: via must be lane|explicit")
        if "semantic_key" in event:
            _require(
                isinstance(event["semantic_key"], str) and event["semantic_key"].strip(),
                f"{case_id}/{sid}: semantic_key must be a non-empty string",
            )
        for key in ("due_at_offset_h", "occurred_at_offset_h"):
            if key in event:
                _require(isinstance(event[key], (int, float)), f"{case_id}/{sid}: {key} numeric")
    if etype == "correct":
        _require(event.get("action") in CORRECTION_ACTIONS, f"{case_id}/{sid}: bad correction action")
    if etype == "time_advance":
        days = event.get("days")
        _require(isinstance(days, (int, float)) and 0 < days <= 60, f"{case_id}/{sid}: time_advance.days in (0,60]")


# --- suite loading -------------------------------------------------------------

CASES_DIR = Path(__file__).parent / "cases"


def load_suite(cases_dir: Path | None = None) -> tuple[list[Persona], list[Case]]:
    """Load and validate every persona case file. Raises SchemaError on any
    deviation from the frozen schema."""
    directory = cases_dir or CASES_DIR
    files = sorted(directory.glob("p*.json"))
    personas: list[Persona] = []
    cases: list[Case] = []
    seen_ids: set[str] = set()
    for path in files:
        raw = json.loads(path.read_text(encoding="utf-8"))
        _require(raw.get("schema_version") == SCHEMA_VERSION, f"{path.name}: schema_version must be {SCHEMA_VERSION}")
        persona_raw = raw.get("persona")
        _require(isinstance(persona_raw, dict), f"{path.name}: persona object required")
        persona = Persona(
            persona_id=str(persona_raw["persona_id"]),
            name=str(persona_raw["name"]),
            domain=str(persona_raw.get("domain", "")),
        )
        _require(_CASE_ID_RE is not None, "unreachable")
        personas.append(persona)
        for raw_case in raw.get("cases", []):
            case = parse_case(raw_case, persona.persona_id)
            _require(case.case_id not in seen_ids, f"duplicate case_id {case.case_id}")
            seen_ids.add(case.case_id)
            cases.append(case)
    return personas, cases


def coverage_matrix(cases: list[Case]) -> dict[str, dict[str, int]]:
    """persona_id -> dimension -> case count (machine-checkable coverage)."""
    matrix: dict[str, dict[str, int]] = {}
    for case in cases:
        matrix.setdefault(case.persona_id, dict.fromkeys(DIMENSION_ORDER, 0))
        matrix[case.persona_id][case.dimension] += 1
    return matrix


def coverage_report(personas: list[Persona], cases: list[Case]) -> dict[str, Any]:
    matrix = coverage_matrix(cases)
    holes = [
        {"persona": pid, "dimension": dim}
        for pid in [p.persona_id for p in personas]
        for dim in DIMENSION_ORDER
        if matrix.get(pid, {}).get(dim, 0) == 0
    ]
    multi_session = all(case.session_count >= MIN_SESSIONS for case in cases)
    return {
        "schema_version": SCHEMA_VERSION,
        "persona_count": len(personas),
        "case_count": len(cases),
        "cases_per_dimension": {dim: sum(1 for c in cases if c.dimension == dim) for dim in DIMENSION_ORDER},
        "matrix": matrix,
        "matrix_holes": holes,
        "all_multi_session": multi_session,
        "total_events": sum(c.event_count for c in cases),
        "meets_minimum": (
            len(personas) >= REQUIRED_PERSONA_COUNT and len(cases) >= MIN_TOTAL_CASES and not holes and multi_session
        ),
    }
