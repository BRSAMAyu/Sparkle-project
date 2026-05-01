from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.services.plan_outcome_service import (
    EVIDENCE_LEVEL_HUMAN_TRUTH,
    EVIDENCE_LEVEL_TURN_REACTION,
    PlanOutcomeService,
)

STALE_AFTER_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    raw = _strip(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _bounded_score(value: Any, *, fallback: float = 0.6) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 4)
    except (TypeError, ValueError):
        return fallback


def _normalize_direction(record: dict[str, Any]) -> str:
    observed = _strip(record.get("observed_outcome")).lower()
    if any(token in observed for token in ("effective", "success", "progress", "helped", "completed", "started", "worked")):
        return "success"
    if any(token in observed for token in ("ineffective", "fail", "stalled", "overload", "too_difficult", "too_long", "unclear", "rejected", "wrong")):
        return "failure"
    signal = _as_dict(record.get("planning_implications"))
    if signal.get("preserve_success_pattern") is True:
        return "success"
    if signal.get("lighter_first_step") is True or signal.get("scaffold_level") == "high":
        return "failure"
    return "mixed"


def _learning_key(record: dict[str, Any]) -> str:
    target = _strip(record.get("target_hypothesis"))
    if target:
        return target.lower()
    base = [
        _strip(record.get("learning_domain")).lower() or "plan",
        _strip(record.get("source_family")).lower() or "unknown",
        _strip(record.get("target_type")).lower() or "unknown",
        _strip(record.get("observed_outcome")).lower() or "unknown",
    ]
    return "::".join(base)


def _freshness_status(record: dict[str, Any], *, now: datetime) -> str:
    deadline = _parse_dt(record.get("freshness_deadline"))
    if deadline is not None:
        return "stale" if deadline < now else "fresh"
    recorded_at = _parse_dt(record.get("recorded_at"))
    if recorded_at is None:
        return "unknown"
    return "stale" if recorded_at < (now - timedelta(days=STALE_AFTER_DAYS)) else "fresh"


def _stable_unique_count(values: list[str]) -> int:
    return len({item for item in values if item})


def _supports_profile_promotion(record: dict[str, Any]) -> bool:
    metadata = _as_dict(record.get("metadata"))
    return bool(metadata.get("persist_profile_ledger"))


@dataclass(frozen=True)
class OutcomeLearningItem:
    learning_key: str
    learning_domain: str
    direction: str
    summary: str
    sample_count: int
    unique_sessions: int
    confidence: float
    source_families: tuple[str, ...] = field(default_factory=tuple)
    evidence_record_ids: tuple[str, ...] = field(default_factory=tuple)
    planning_bias_constraints: dict[str, Any] = field(default_factory=dict)
    known_failure_avoidance_rules: tuple[str, ...] = field(default_factory=tuple)
    known_success_patterns: tuple[str, ...] = field(default_factory=tuple)
    plan_generation_hints_from_outcomes: tuple[str, ...] = field(default_factory=tuple)
    suggested_layer: str = "episode"
    freshness_status: str = "fresh"

    def to_dict(self) -> dict[str, Any]:
        return {
            "learning_key": self.learning_key,
            "learning_domain": self.learning_domain,
            "direction": self.direction,
            "summary": self.summary,
            "sample_count": self.sample_count,
            "unique_sessions": self.unique_sessions,
            "confidence": self.confidence,
            "source_families": list(self.source_families),
            "evidence_record_ids": list(self.evidence_record_ids),
            "planning_bias_constraints": dict(self.planning_bias_constraints),
            "known_failure_avoidance_rules": list(self.known_failure_avoidance_rules),
            "known_success_patterns": list(self.known_success_patterns),
            "plan_generation_hints_from_outcomes": list(self.plan_generation_hints_from_outcomes),
            "suggested_layer": self.suggested_layer,
            "freshness_status": self.freshness_status,
        }


@dataclass(frozen=True)
class OutcomeLearningReport:
    validated_plan_learnings: tuple[OutcomeLearningItem, ...] = field(default_factory=tuple)
    validated_insight_learnings: tuple[OutcomeLearningItem, ...] = field(default_factory=tuple)
    rejected_learnings: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    promotion_candidates: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    demotion_candidates: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    ignored_noise: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    conflict_report: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    planning_bias_constraints: dict[str, Any] = field(default_factory=dict)
    known_failure_avoidance_rules: tuple[str, ...] = field(default_factory=tuple)
    known_success_patterns: tuple[str, ...] = field(default_factory=tuple)
    plan_generation_hints_from_outcomes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "validated_plan_learnings": [item.to_dict() for item in self.validated_plan_learnings],
            "validated_insight_learnings": [item.to_dict() for item in self.validated_insight_learnings],
            "rejected_learnings": [dict(item) for item in self.rejected_learnings],
            "promotion_candidates": [dict(item) for item in self.promotion_candidates],
            "demotion_candidates": [dict(item) for item in self.demotion_candidates],
            "ignored_noise": [dict(item) for item in self.ignored_noise],
            "conflict_report": [dict(item) for item in self.conflict_report],
            "planning_bias_constraints": dict(self.planning_bias_constraints),
            "known_failure_avoidance_rules": list(self.known_failure_avoidance_rules),
            "known_success_patterns": list(self.known_success_patterns),
            "plan_generation_hints_from_outcomes": list(self.plan_generation_hints_from_outcomes),
        }


class OutcomeLearningService:
    """Aggregate outcome records into validated learnings and planning bridge hints."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.plan_outcome_service = PlanOutcomeService(db, redis)

    async def build_report_for_scope(
        self,
        user_id: UUID,
        *,
        session_id: str | None = None,
        plan_id: UUID | str | None = None,
        include_profile_ledger: bool = False,
        current_learning_state: dict[str, Any] | None = None,
    ) -> OutcomeLearningReport:
        records = await self.plan_outcome_service.list_records(
            user_id,
            session_id=session_id,
            plan_id=plan_id,
            include_profile_ledger=include_profile_ledger,
        )
        return self.build_report(records, current_learning_state=current_learning_state)

    def build_report(
        self,
        records: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        *,
        current_learning_state: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> OutcomeLearningReport:
        now = now or _utcnow()
        learning_state = _as_dict(current_learning_state)
        existing_map = {
            _strip(item.get("learning_key")): dict(item)
            for item in _as_list(learning_state.get("validated_learnings"))
            if isinstance(item, dict) and _strip(item.get("learning_key"))
        }

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        ignored_noise: list[dict[str, Any]] = []
        rejected_learnings: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        demotion_candidates: list[dict[str, Any]] = []
        validated_plan: list[OutcomeLearningItem] = []
        validated_insight: list[OutcomeLearningItem] = []
        promotion_candidates: list[dict[str, Any]] = []

        for raw in records:
            record = _as_dict(raw)
            if not record:
                continue
            freshness = _freshness_status(record, now=now)
            direction = _normalize_direction(record)
            if record.get("evidence_level") == EVIDENCE_LEVEL_TURN_REACTION:
                ignored_noise.append({"record_id": record.get("record_id"), "reason": "turn_reaction_only"})
                continue
            if freshness == "stale":
                rejected_learnings.append(
                    {
                        "record_id": record.get("record_id"),
                        "learning_key": _learning_key(record),
                        "reason": "stale_signal",
                    }
                )
                continue
            confidence = _bounded_score(record.get("confidence"))
            if confidence < 0.55 or _strip(record.get("evidence_strength")) == "weak":
                ignored_noise.append({"record_id": record.get("record_id"), "reason": "weak_evidence"})
                continue
            record["_direction"] = direction
            record["_freshness_status"] = freshness
            grouped[_learning_key(record)].append(record)

        for learning_key, group in grouped.items():
            successes = [item for item in group if item["_direction"] == "success"]
            failures = [item for item in group if item["_direction"] == "failure"]
            confidence = round(
                sum(_bounded_score(item.get("confidence")) for item in group) / max(len(group), 1),
                4,
            )
            domain = _strip(group[0].get("learning_domain")).lower() or "plan"
            sessions = [_strip(item.get("session_id")) for item in group if _strip(item.get("session_id"))]

            decisive_group: list[dict[str, Any]]
            suggested_layer = "episode"

            if successes and failures:
                human_truth = [item for item in group if item.get("evidence_level") == EVIDENCE_LEVEL_HUMAN_TRUTH]
                if human_truth:
                    human_successes = [item for item in human_truth if item["_direction"] == "success"]
                    human_failures = [item for item in human_truth if item["_direction"] == "failure"]
                    if human_successes and human_failures:
                        conflict = {
                            "learning_key": learning_key,
                            "reason": "contradictory_human_truth",
                            "supporting_record_ids": [item.get("record_id") for item in human_successes],
                            "contradicting_record_ids": [item.get("record_id") for item in human_failures],
                        }
                        conflicts.append(conflict)
                        if learning_key in existing_map:
                            demotion_candidates.append(
                                {
                                    "learning_key": learning_key,
                                    "reason": "new_conflict_against_existing_learning",
                                    "existing_learning": dict(existing_map[learning_key]),
                                }
                            )
                        continue
                    decisive_group = human_successes or human_failures
                    conflicts.append(
                        {
                            "learning_key": learning_key,
                            "reason": "human_truth_overrides_weaker_evidence",
                            "supporting_record_ids": [item.get("record_id") for item in decisive_group],
                            "contradicting_record_ids": [
                                item.get("record_id")
                                for item in group
                                if item not in decisive_group and item["_direction"] in {"success", "failure"}
                            ],
                        }
                    )
                else:
                    conflict = {
                        "learning_key": learning_key,
                        "reason": "contradictory_evidence",
                        "supporting_record_ids": [item.get("record_id") for item in successes],
                        "contradicting_record_ids": [item.get("record_id") for item in failures],
                    }
                    conflicts.append(conflict)
                    if learning_key in existing_map:
                        demotion_candidates.append(
                            {
                                "learning_key": learning_key,
                                "reason": "new_conflict_against_existing_learning",
                                "existing_learning": dict(existing_map[learning_key]),
                            }
                        )
                    continue
            else:
                decisive_group = successes or failures

            min_repetition = 1 if all(
                item.get("evidence_level") == EVIDENCE_LEVEL_HUMAN_TRUTH for item in decisive_group
            ) else 2
            unique_sessions = _stable_unique_count(sessions)
            profile_eligible = any(_supports_profile_promotion(item) for item in decisive_group)
            if len(decisive_group) >= 3 and (unique_sessions >= 2 or profile_eligible):
                suggested_layer = "profile"

            if len(decisive_group) < min_repetition:
                ignored_noise.append(
                    {
                        "learning_key": learning_key,
                        "reason": "insufficient_repetition",
                        "sample_count": len(decisive_group),
                    }
                )
                continue

            direction = decisive_group[0]["_direction"]
            planning_bias_constraints = self._merge_planning_bias_constraints(decisive_group)
            failure_rules = tuple(self._build_failure_rules(decisive_group, direction=direction))
            success_patterns = tuple(self._build_success_patterns(decisive_group, direction=direction))
            hints = tuple(self._build_generation_hints(decisive_group, direction=direction))
            item = OutcomeLearningItem(
                learning_key=learning_key,
                learning_domain=domain,
                direction=direction,
                summary=self._build_summary(learning_key=learning_key, group=decisive_group, direction=direction),
                sample_count=len(decisive_group),
                unique_sessions=unique_sessions,
                confidence=confidence,
                source_families=tuple(
                    sorted({_strip(entry.get("source_family")) for entry in decisive_group if _strip(entry.get("source_family"))})
                ),
                evidence_record_ids=tuple(_strip(entry.get("record_id")) for entry in decisive_group if _strip(entry.get("record_id"))),
                planning_bias_constraints=planning_bias_constraints,
                known_failure_avoidance_rules=failure_rules,
                known_success_patterns=success_patterns,
                plan_generation_hints_from_outcomes=hints,
                suggested_layer=suggested_layer,
                freshness_status="fresh",
            )
            if domain == "insight":
                validated_insight.append(item)
            else:
                validated_plan.append(item)
            promotion_candidates.append(
                {
                    "learning_key": learning_key,
                    "learning_domain": domain,
                    "direction": direction,
                    "suggested_layer": suggested_layer,
                    "confidence": confidence,
                    "sample_count": len(decisive_group),
                }
            )

            existing = existing_map.get(learning_key)
            if existing and _strip(existing.get("direction")) != direction:
                demotion_candidates.append(
                    {
                        "learning_key": learning_key,
                        "reason": "validated_direction_changed",
                        "existing_learning": dict(existing),
                    }
                )

        validated_all = [*validated_plan, *validated_insight]
        return OutcomeLearningReport(
            validated_plan_learnings=tuple(validated_plan),
            validated_insight_learnings=tuple(validated_insight),
            rejected_learnings=tuple(rejected_learnings),
            promotion_candidates=tuple(promotion_candidates),
            demotion_candidates=tuple(demotion_candidates),
            ignored_noise=tuple(ignored_noise),
            conflict_report=tuple(conflicts),
            planning_bias_constraints=self._merge_planning_bias_constraints(
                [item.to_dict() for item in validated_all]
            ),
            known_failure_avoidance_rules=tuple(
                rule
                for rule in self._dedupe_strings(
                    [rule for item in validated_all for rule in item.known_failure_avoidance_rules]
                )
            ),
            known_success_patterns=tuple(
                pattern
                for pattern in self._dedupe_strings(
                    [pattern for item in validated_all for pattern in item.known_success_patterns]
                )
            ),
            plan_generation_hints_from_outcomes=tuple(
                hint
                for hint in self._dedupe_strings(
                    [hint for item in validated_all for hint in item.plan_generation_hints_from_outcomes]
                )
            ),
        )

    @staticmethod
    def _merge_planning_bias_constraints(records: list[dict[str, Any]]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for item in records:
            constraints = _as_dict(item.get("planning_implications") or item.get("planning_bias_constraints"))
            for key, value in constraints.items():
                if key not in merged:
                    merged[key] = value
                    continue
                if isinstance(value, bool):
                    merged[key] = bool(merged[key]) or value
                elif isinstance(value, str) and not _strip(merged[key]):
                    merged[key] = value
        return merged

    @staticmethod
    def _build_summary(*, learning_key: str, group: list[dict[str, Any]], direction: str) -> str:
        sample_count = len(group)
        observed = _strip(group[0].get("observed_outcome"))
        if direction == "failure":
            return f"Repeated evidence shows {learning_key} tends to fail ({sample_count} records, latest outcome: {observed})."
        if direction == "success":
            return f"Repeated evidence shows {learning_key} tends to work ({sample_count} records, latest outcome: {observed})."
        return f"Repeated evidence exists for {learning_key}, but the direction remains mixed."

    @staticmethod
    def _build_failure_rules(group: list[dict[str, Any]], *, direction: str) -> list[str]:
        if direction != "failure":
            return []
        rules: list[str] = []
        constraints = OutcomeLearningService._merge_planning_bias_constraints(group)
        if constraints.get("lighter_first_step") is True:
            rules.append("Avoid dense first steps when similar conditions recur.")
        if constraints.get("grounding_mode") == "mandatory":
            rules.append("Do not produce a confident plan without grounded user materials.")
        if constraints.get("checkpoint_cadence") == "short":
            rules.append("Use shorter checkpoints after repeated timing or overload failures.")
        return rules

    @staticmethod
    def _build_success_patterns(group: list[dict[str, Any]], *, direction: str) -> list[str]:
        if direction != "success":
            return []
        constraints = OutcomeLearningService._merge_planning_bias_constraints(group)
        patterns: list[str] = []
        if constraints.get("grounding_mode") == "mandatory":
            patterns.append("Grounded planning improved outcomes in similar scenarios.")
        if constraints.get("checkpoint_cadence") == "short":
            patterns.append("Short checkpoint cadence improved follow-through in similar scenarios.")
        if constraints.get("preserve_success_pattern") is True:
            patterns.append("Preserve the successful plan rhythm instead of widening scope too quickly.")
        return patterns

    @staticmethod
    def _build_generation_hints(group: list[dict[str, Any]], *, direction: str) -> list[str]:
        constraints = OutcomeLearningService._merge_planning_bias_constraints(group)
        hints: list[str] = []
        if constraints.get("lighter_first_step") is True:
            hints.append("Default to a lighter first step.")
        if constraints.get("scaffold_level") == "high":
            hints.append("Increase scaffold level for the next comparable plan.")
        if constraints.get("grounding_mode") == "mandatory":
            hints.append("Require user-material grounding before approving a full plan.")
        if constraints.get("checkpoint_cadence") == "short":
            hints.append("Prefer a shorter checkpoint cadence.")
        if direction == "success" and not hints:
            hints.append("Reuse the validated success pattern when context matches.")
        return hints

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for item in values:
            normalized = _strip(item)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(normalized)
        return deduped
