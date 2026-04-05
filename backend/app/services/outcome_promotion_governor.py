from __future__ import annotations

import inspect
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.business_metrics import (
    OUTCOME_LEARNING_CONFLICTS_TOTAL,
    OUTCOME_LEARNING_PLANNING_CONSTRAINTS_TOTAL,
    PROFILE_LEDGER_PENDING_SYNTHESIS,
    VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL,
)
from app.services.outcome_learning_service import OutcomeLearningReport, OutcomeLearningService
from app.services.personalization.preference_service import PreferenceService
from app.services.plan_state_service import PlanStateService
from app.services.user_strategy_state_service import UserStrategyStateService

SESSION_OUTCOME_LEARNING_KEY_PREFIX = "session:outcome_learning:"
SESSION_OUTCOME_LEARNING_TTL_SECONDS = 14 * 24 * 60 * 60
EPISODE_OUTCOME_LEARNING_KEY = "validated_outcome_learning"
PROFILE_OUTCOME_LEARNING_KEY = "validated_outcome_learning"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _utcnow_iso() -> str:
    return _utcnow().isoformat()


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
    raw = _strip(value)
    if not raw:
        return None
    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(tzinfo=None)


class OutcomePromotionGovernor:
    """Govern promotion, conflict handling, and planning bridge compilation for outcome learnings."""

    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.redis = redis
        self.outcome_learning_service = OutcomeLearningService(db, redis)
        self.plan_state_service = PlanStateService(db, redis)
        self.preference_service = PreferenceService(db, redis)
        self.user_strategy_state_service = UserStrategyStateService(db, redis)

    async def get_effective_learning_state(
        self,
        user_id: UUID,
        *,
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        profile_state = await self._load_profile_state(user_id)
        episode_state = await self._load_episode_state(user_id, plan_id)
        session_state = await self._load_session_state(session_id)

        merged_learnings: dict[str, dict[str, Any]] = {}
        conflicts: list[dict[str, Any]] = []
        for layer_name, state in (
            ("profile", profile_state),
            ("episode", episode_state),
            ("session", session_state),
        ):
            for item in _as_list(state.get("validated_learnings")):
                if not isinstance(item, dict):
                    continue
                learning_key = _strip(item.get("learning_key"))
                if not learning_key:
                    continue
                existing = merged_learnings.get(learning_key)
                if existing and _strip(existing.get("direction")) != _strip(item.get("direction")):
                    conflicts.append(
                        {
                            "learning_key": learning_key,
                            "existing_direction": existing.get("direction"),
                            "incoming_direction": item.get("direction"),
                            "incoming_layer": layer_name,
                        }
                    )
                merged_learnings[learning_key] = {**dict(item), "active_layer": layer_name}

        bridge = self.compile_planning_bridge(
            {"validated_learnings": list(merged_learnings.values()), "conflicts": conflicts}
        )
        return {
            "validated_learnings": list(merged_learnings.values()),
            "conflicts": conflicts,
            "planning_bridge": bridge,
            "profile_layer_active": bool(profile_state.get("validated_learnings")),
            "episode_layer_active": bool(episode_state.get("validated_learnings")),
            "session_layer_active": bool(session_state.get("validated_learnings")),
        }

    async def apply_learning_report(
        self,
        user_id: UUID,
        *,
        report: OutcomeLearningReport | dict[str, Any],
        plan_id: UUID | str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        payload = report.to_dict() if isinstance(report, OutcomeLearningReport) else _as_dict(report)
        session_state = {
            "validated_learnings": [
                *[dict(item) for item in _as_list(payload.get("validated_plan_learnings")) if isinstance(item, dict)],
                *[dict(item) for item in _as_list(payload.get("validated_insight_learnings")) if isinstance(item, dict)],
            ],
            "promotion_candidates": [dict(item) for item in _as_list(payload.get("promotion_candidates")) if isinstance(item, dict)],
            "demotion_candidates": [dict(item) for item in _as_list(payload.get("demotion_candidates")) if isinstance(item, dict)],
            "conflicts": [dict(item) for item in _as_list(payload.get("conflict_report")) if isinstance(item, dict)],
            "planning_bridge": self.compile_planning_bridge(payload),
            "updated_at": _utcnow_iso(),
        }
        if session_id:
            await self._write_session_state(session_id, session_state)

        promotion_decisions: list[dict[str, Any]] = []
        if plan_id is not None:
            promotion_decisions.extend(await self._apply_episode_promotions(user_id, plan_id, session_state))
        promotion_decisions.extend(await self._apply_profile_promotions(user_id, session_state))
        self._record_promotion_metrics(
            promotion_decisions=promotion_decisions,
            conflict_report=list(session_state["conflicts"]),
            demotion_candidates=list(session_state["demotion_candidates"]),
        )
        self._record_planning_constraint_metrics(session_state["planning_bridge"])

        await self._apply_strategy_adjustments(
            user_id=user_id,
            session_id=session_id,
            plan_id=plan_id,
            promotion_decisions=promotion_decisions,
            planning_bridge=session_state["planning_bridge"],
        )
        effective_state = await self.get_effective_learning_state(user_id, plan_id=plan_id, session_id=session_id)
        return {
            "promotion_decision": promotion_decisions,
            "conflict_report": list(session_state["conflicts"]),
            "evidence_threshold_result": {
                "episode_candidates": [
                    item for item in _as_list(session_state.get("promotion_candidates")) if item.get("suggested_layer") == "episode"
                ],
                "profile_candidates": [
                    item for item in _as_list(session_state.get("promotion_candidates")) if item.get("suggested_layer") == "profile"
                ],
            },
            "expiry_or_review_window": "review_validated_learnings_every_30_days_or_on_new_conflict",
            "effective_learning_state": effective_state,
        }

    async def synthesize_profile_ledger_learning(
        self,
        user_id: UUID,
        *,
        session_id: str | None = None,
        trigger_source: str = "manual",
    ) -> dict[str, Any]:
        pending_before = await self._count_pending_profile_ledger_records(user_id)
        PROFILE_LEDGER_PENDING_SYNTHESIS.set(float(pending_before))
        if pending_before <= 0:
            return {
                "trigger_source": _strip(trigger_source) or "manual",
                "profile_ledger_records": 0,
                "pending_records_before": 0,
                "pending_records_after": 0,
                "status": "noop",
            }

        current_learning_state = await self.get_effective_learning_state(user_id, session_id=session_id)
        report = await self.outcome_learning_service.build_report_for_scope(
            user_id,
            session_id=session_id,
            include_profile_ledger=True,
            current_learning_state=current_learning_state,
        )
        applied = await self.apply_learning_report(
            user_id,
            report=report,
            plan_id=None,
            session_id=session_id,
        )
        pending_after = await self._count_pending_profile_ledger_records(user_id)
        PROFILE_LEDGER_PENDING_SYNTHESIS.set(float(pending_after))
        return {
            "trigger_source": _strip(trigger_source) or "manual",
            "profile_ledger_records": pending_before,
            "pending_records_before": pending_before,
            "pending_records_after": pending_after,
            "validated_learning_count": len(applied["effective_learning_state"].get("validated_learnings") or []),
            "promotion_decision": list(applied.get("promotion_decision") or []),
            "effective_learning_state": dict(applied.get("effective_learning_state") or {}),
            "status": "applied",
        }

    async def sweep_profile_ledger_learning(
        self,
        *,
        user_ids: list[UUID] | tuple[UUID, ...],
        trigger_source: str = "scheduled_profile_ledger_sweep",
    ) -> dict[str, Any]:
        stats = {
            "users_scanned": 0,
            "users_with_pending": 0,
            "pending_records_before": 0,
            "pending_records_after": 0,
            "promoted_profile_learnings": 0,
            "results": [],
        }
        for user_id in user_ids:
            stats["users_scanned"] += 1
            result = await self.synthesize_profile_ledger_learning(
                user_id,
                trigger_source=trigger_source,
            )
            pending_before = int(result.get("pending_records_before") or 0)
            pending_after = int(result.get("pending_records_after") or 0)
            if pending_before > 0:
                stats["users_with_pending"] += 1
            stats["pending_records_before"] += pending_before
            stats["pending_records_after"] += pending_after
            stats["promoted_profile_learnings"] += sum(
                1
                for item in list(result.get("promotion_decision") or [])
                if item.get("layer") == "profile" and item.get("decision") == "promoted"
            )
            stats["results"].append({"user_id": str(user_id), **result})
        PROFILE_LEDGER_PENDING_SYNTHESIS.set(float(stats["pending_records_after"]))
        return stats

    def compile_planning_bridge(self, learning_state: dict[str, Any] | OutcomeLearningReport) -> dict[str, Any]:
        payload = learning_state.to_dict() if isinstance(learning_state, OutcomeLearningReport) else _as_dict(learning_state)
        validated = [dict(item) for item in _as_list(payload.get("validated_learnings")) if isinstance(item, dict)]
        if not validated:
            validated = [
                *[dict(item) for item in _as_list(payload.get("validated_plan_learnings")) if isinstance(item, dict)],
                *[dict(item) for item in _as_list(payload.get("validated_insight_learnings")) if isinstance(item, dict)],
            ]

        constraints: dict[str, Any] = {}
        failure_rules: list[str] = []
        success_patterns: list[str] = []
        hints: list[str] = []
        for item in validated:
            for key, value in _as_dict(item.get("planning_bias_constraints")).items():
                if key not in constraints:
                    constraints[key] = value
                elif isinstance(value, bool):
                    constraints[key] = bool(constraints[key]) or value
            failure_rules.extend(_strip(rule) for rule in _as_list(item.get("known_failure_avoidance_rules")) if _strip(rule))
            success_patterns.extend(_strip(rule) for rule in _as_list(item.get("known_success_patterns")) if _strip(rule))
            hints.extend(_strip(rule) for rule in _as_list(item.get("plan_generation_hints_from_outcomes")) if _strip(rule))

        return {
            "planning_bias_constraints": constraints,
            "known_failure_avoidance_rules": self._dedupe_strings(failure_rules),
            "known_success_patterns": self._dedupe_strings(success_patterns),
            "plan_generation_hints_from_outcomes": self._dedupe_strings(hints),
        }

    async def _apply_episode_promotions(
        self,
        user_id: UUID,
        plan_id: UUID | str,
        session_state: dict[str, Any],
    ) -> list[dict[str, Any]]:
        plan_uuid = plan_id if isinstance(plan_id, UUID) else UUID(str(plan_id))
        state = await self.plan_state_service.get_or_create_plan_state(user_id, plan_uuid)
        facts = dict(state.facts or {})
        existing_state = _as_dict(facts.get(EPISODE_OUTCOME_LEARNING_KEY))
        validated = [dict(item) for item in _as_list(existing_state.get("validated_learnings")) if isinstance(item, dict)]
        decisions: list[dict[str, Any]] = []
        for item in _as_list(session_state.get("validated_learnings")):
            if not isinstance(item, dict):
                continue
            if _strip(item.get("suggested_layer")) not in {"episode", "profile"}:
                continue
            conflict = self._find_conflict(validated, item)
            if conflict:
                decisions.append(
                    {
                        "layer": "episode",
                        "learning_key": item.get("learning_key"),
                        "decision": "blocked_conflict",
                        "direction": item.get("direction"),
                        "conflict": conflict,
                    }
                )
                continue
            validated = self._upsert_learning(validated, item, layer="episode")
            decisions.append(
                {
                    "layer": "episode",
                    "learning_key": item.get("learning_key"),
                    "decision": "promoted",
                    "direction": item.get("direction"),
                }
            )
        facts[EPISODE_OUTCOME_LEARNING_KEY] = {
            "validated_learnings": validated,
            "conflicts": [dict(item) for item in _as_list(session_state.get("conflicts")) if isinstance(item, dict)],
            "planning_bridge": dict(session_state.get("planning_bridge") or {}),
            "updated_at": _utcnow_iso(),
        }
        await self.plan_state_service.upsert_plan_state(user_id, plan_uuid, {"facts": facts}, bump_version=True)
        return decisions

    async def _apply_profile_promotions(self, user_id: UUID, session_state: dict[str, Any]) -> list[dict[str, Any]]:
        prefs = await self.preference_service.get_preferences(user_id)
        inferred = dict(prefs.inferred or {})
        existing_state = _as_dict(inferred.get(PROFILE_OUTCOME_LEARNING_KEY))
        validated = [dict(item) for item in _as_list(existing_state.get("validated_learnings")) if isinstance(item, dict)]
        decisions: list[dict[str, Any]] = []
        for item in _as_list(session_state.get("validated_learnings")):
            if not isinstance(item, dict) or _strip(item.get("suggested_layer")) != "profile":
                continue
            if int(item.get("sample_count") or 0) < 3:
                decisions.append(
                    {
                        "layer": "profile",
                        "learning_key": item.get("learning_key"),
                        "decision": "insufficient_profile_evidence",
                        "direction": item.get("direction"),
                    }
                )
                continue
            conflict = self._find_conflict(validated, item)
            if conflict:
                decisions.append(
                    {
                        "layer": "profile",
                        "learning_key": item.get("learning_key"),
                        "decision": "blocked_conflict",
                        "direction": item.get("direction"),
                        "conflict": conflict,
                    }
                )
                continue
            validated = self._upsert_learning(validated, item, layer="profile")
            decisions.append(
                {
                    "layer": "profile",
                    "learning_key": item.get("learning_key"),
                    "decision": "promoted",
                    "direction": item.get("direction"),
                }
            )
        await self.preference_service.update_inferred(
            user_id,
            {
                PROFILE_OUTCOME_LEARNING_KEY: {
                    "validated_learnings": validated,
                    "conflicts": [dict(item) for item in _as_list(session_state.get("conflicts")) if isinstance(item, dict)],
                    "planning_bridge": dict(session_state.get("planning_bridge") or {}),
                    "updated_at": _utcnow_iso(),
                }
            },
        )
        return decisions

    async def _apply_strategy_adjustments(
        self,
        *,
        user_id: UUID,
        session_id: str | None,
        plan_id: UUID | str | None,
        promotion_decisions: list[dict[str, Any]],
        planning_bridge: dict[str, Any],
    ) -> None:
        successful_layers = {str(item.get("layer")) for item in promotion_decisions if item.get("decision") == "promoted"}
        if not successful_layers:
            return
        constraints = _as_dict(planning_bridge.get("planning_bias_constraints"))
        if not constraints:
            return
        if constraints.get("grounding_mode") == "mandatory":
            for layer in successful_layers:
                if layer == "episode" and plan_id is not None:
                    await self.user_strategy_state_service.apply_adjustment(
                        user_id,
                        {"retrieval_emphasis": "user_materials"},
                        layer="episode",
                        reason="Validated outcome learning showed grounded planning works better here.",
                        evidence={"source": "outcome_learning", "measurable_effect": True},
                        confidence=0.82,
                        plan_id=plan_id if isinstance(plan_id, UUID) else UUID(str(plan_id)),
                    )
                elif layer == "profile":
                    await self.user_strategy_state_service.apply_adjustment(
                        user_id,
                        {"retrieval_emphasis": "user_materials"},
                        layer="profile",
                        reason="Repeated outcome learning showed grounded planning works better across sessions.",
                        evidence={"source": "outcome_learning", "measurable_effect": True},
                        confidence=0.84,
                    )

    async def _load_profile_state(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.preference_service.get_preferences(user_id)
        return _as_dict((prefs.inferred or {}).get(PROFILE_OUTCOME_LEARNING_KEY))

    async def _count_pending_profile_ledger_records(self, user_id: UUID) -> int:
        records = await self.outcome_learning_service.plan_outcome_service.list_records(
            user_id,
            include_profile_ledger=True,
        )
        if not records:
            return 0
        profile_state = await self._load_profile_state(user_id)
        updated_at = _parse_dt(profile_state.get("updated_at"))
        if updated_at is None:
            return len(records)
        pending = 0
        for item in records:
            recorded_at = _parse_dt(item.get("recorded_at"))
            if recorded_at is None or recorded_at > updated_at:
                pending += 1
        return pending

    async def _load_episode_state(self, user_id: UUID, plan_id: UUID | str | None) -> dict[str, Any]:
        if plan_id is None:
            return {}
        state = await self.plan_state_service.get_plan_state(
            user_id,
            plan_id if isinstance(plan_id, UUID) else UUID(str(plan_id)),
        )
        if state is None or not isinstance(state.facts, dict):
            return {}
        return _as_dict(state.facts.get(EPISODE_OUTCOME_LEARNING_KEY))

    async def _load_session_state(self, session_id: str | None) -> dict[str, Any]:
        if not self.redis or not _strip(session_id):
            return {}
        payload = await self._read_json_key(f"{SESSION_OUTCOME_LEARNING_KEY_PREFIX}{session_id}")
        return payload if isinstance(payload, dict) else {}

    async def _write_session_state(self, session_id: str, payload: dict[str, Any]) -> None:
        if not self.redis or not _strip(session_id):
            return
        dumped = json.dumps(payload, ensure_ascii=False)
        if hasattr(self.redis, "setex"):
            result = self.redis.setex(
                f"{SESSION_OUTCOME_LEARNING_KEY_PREFIX}{session_id}",
                SESSION_OUTCOME_LEARNING_TTL_SECONDS,
                dumped,
            )
            if inspect.isawaitable(result):
                await result
            return
        result = self.redis.set(f"{SESSION_OUTCOME_LEARNING_KEY_PREFIX}{session_id}", dumped)
        if inspect.isawaitable(result):
            await result
        if hasattr(self.redis, "expire"):
            expire_result = self.redis.expire(
                f"{SESSION_OUTCOME_LEARNING_KEY_PREFIX}{session_id}",
                SESSION_OUTCOME_LEARNING_TTL_SECONDS,
            )
            if inspect.isawaitable(expire_result):
                await expire_result

    async def _read_json_key(self, key: str) -> dict[str, Any] | list[Any] | None:
        try:
            raw = self.redis.get(key)
            if inspect.isawaitable(raw):
                raw = await raw
            if not raw:
                return None
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if isinstance(raw, (dict, list)):
                return raw
            if isinstance(raw, str):
                parsed = json.loads(raw)
                if isinstance(parsed, (dict, list)):
                    return parsed
        except Exception:
            return None
        return None

    @staticmethod
    def _find_conflict(existing: list[dict[str, Any]], incoming: dict[str, Any]) -> dict[str, Any] | None:
        learning_key = _strip(incoming.get("learning_key"))
        direction = _strip(incoming.get("direction"))
        for item in existing:
            if _strip(item.get("learning_key")) != learning_key:
                continue
            if _strip(item.get("direction")) != direction:
                return {"existing": dict(item), "incoming": dict(incoming)}
        return None

    @staticmethod
    def _upsert_learning(existing: list[dict[str, Any]], incoming: dict[str, Any], *, layer: str) -> list[dict[str, Any]]:
        learning_key = _strip(incoming.get("learning_key"))
        updated: list[dict[str, Any]] = []
        replaced = False
        for item in existing:
            if _strip(item.get("learning_key")) == learning_key:
                merged = {**dict(item), **dict(incoming)}
                merged["active_layer"] = layer
                merged["promoted_at"] = _utcnow_iso()
                updated.append(merged)
                replaced = True
            else:
                updated.append(dict(item))
        if not replaced:
            fresh = dict(incoming)
            fresh["active_layer"] = layer
            fresh["promoted_at"] = _utcnow_iso()
            updated.append(fresh)
        return updated[-50:]

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

    @staticmethod
    def _record_promotion_metrics(
        *,
        promotion_decisions: list[dict[str, Any]],
        conflict_report: list[dict[str, Any]],
        demotion_candidates: list[dict[str, Any]],
    ) -> None:
        for item in promotion_decisions:
            if item.get("decision") == "promoted":
                VALIDATED_OUTCOME_LEARNING_PROMOTIONS_TOTAL.labels(
                    layer=_strip(item.get("layer")) or "unknown",
                    direction=_strip(item.get("direction")) or "unknown",
                ).inc()
            elif "conflict" in _strip(item.get("decision")):
                OUTCOME_LEARNING_CONFLICTS_TOTAL.labels(
                    layer=_strip(item.get("layer")) or "unknown",
                    reason=_strip(item.get("decision")) or "conflict",
                ).inc()
        for item in conflict_report:
            OUTCOME_LEARNING_CONFLICTS_TOTAL.labels(
                layer="synthesis",
                reason=_strip(item.get("reason")) or "conflict",
            ).inc()
        for item in demotion_candidates:
            OUTCOME_LEARNING_CONFLICTS_TOTAL.labels(
                layer="synthesis",
                reason=_strip(item.get("reason")) or "demotion",
            ).inc()

    @staticmethod
    def _record_planning_constraint_metrics(planning_bridge: dict[str, Any]) -> None:
        constraints = _as_dict(planning_bridge.get("planning_bias_constraints"))
        for key, value in constraints.items():
            OUTCOME_LEARNING_PLANNING_CONSTRAINTS_TOTAL.labels(
                constraint_key=_strip(key) or "unknown",
                constraint_value=_strip(value) or "true",
            ).inc()
