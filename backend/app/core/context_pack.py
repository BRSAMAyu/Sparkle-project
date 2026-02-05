from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import tiktoken
except ImportError:  # pragma: no cover - optional runtime dependency
    tiktoken = None

from app.config import settings
from app.core.business_metrics import (
    CONTEXT_PACK_BUILD,
    CONTEXT_PACK_INTENT,
    CONTEXT_PACK_OVER_BUDGET,
)
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_ranker import RankedItem, rank_items
from app.core.plan_context import PlanContextBuilder
from app.services.context_pack_telemetry_service import ContextPackTelemetryService
from app.services.ltm_rollout_service import LtmRolloutService
from app.services.memory_conflict_resolver import MemoryConflictResolver
from app.services.memory_rank_policy_service import MemoryRankPolicyService
from app.services.memory_service import MemoryService


@lru_cache(maxsize=1)
def _get_token_encoding():
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    encoding = _get_token_encoding()
    if encoding:
        try:
            return len(encoding.encode(text))
        except Exception:
            pass
    return max(1, len(text) // 4)


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _trim_list(items: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    used = 0
    for item in items:
        item_tokens = estimate_tokens(_serialize(item))
        if used + item_tokens > budget:
            break
        trimmed.append(item)
        used += item_tokens
    return trimmed


def _trim_preferences(prefs: dict[str, Any], budget: int) -> dict[str, Any]:
    trimmed: dict[str, Any] = {}
    used = 0
    for key, value in prefs.items():
        item_tokens = estimate_tokens(_serialize({key: value}))
        if used + item_tokens > budget:
            break
        trimmed[key] = value
        used += item_tokens
    return trimmed


def _trim_ranked_preferences(
    ranked: list[RankedItem[Any]],
    budget: int,
) -> tuple[dict[str, Any], dict[str, float]]:
    items: list[dict[str, Any]] = []
    total = 0
    for entry in ranked:
        key = entry.item.pref_key
        value = entry.item.pref_value
        tokens = estimate_tokens(_serialize({key: value}))
        items.append({"key": key, "value": value, "score": entry.score, "tokens": tokens})
        total += tokens

    if total > budget:
        items.sort(key=lambda item: item["score"])
        while total > budget and items:
            dropped = items.pop(0)
            total -= dropped["tokens"]

    items.sort(key=lambda item: item["score"], reverse=True)
    trimmed = {item["key"]: item["value"] for item in items}
    scores = {item["key"]: item["score"] for item in items}
    return trimmed, scores


def _trim_ranked_list(
    payloads: list[dict[str, Any]],
    scores: dict[str, float],
    budget: int,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    entries: list[dict[str, Any]] = []
    total = 0
    for payload in payloads:
        item_id = payload.get("id")
        score = scores.get(item_id, 0.0)
        tokens = estimate_tokens(_serialize(payload))
        entries.append({"payload": payload, "score": score, "tokens": tokens, "id": item_id})
        total += tokens

    if total > budget:
        entries.sort(key=lambda item: item["score"])
        while total > budget and entries:
            dropped = entries.pop(0)
            total -= dropped["tokens"]

    entries.sort(key=lambda item: item["score"], reverse=True)
    trimmed = [entry["payload"] for entry in entries]
    trimmed_scores = {entry["id"]: entry["score"] for entry in entries if entry["id"]}
    return trimmed, trimmed_scores


def _select_with_diversity(
    ranked: list[RankedItem[Any]],
    cap: int,
    diversity_key,
) -> list[RankedItem[Any]]:
    if cap <= 0:
        return []
    selected: list[RankedItem[Any]] = []
    seen = set()
    remaining: list[RankedItem[Any]] = []

    for entry in ranked:
        key = diversity_key(entry.item)
        if key and key not in seen:
            selected.append(entry)
            seen.add(key)
        else:
            remaining.append(entry)
        if len(selected) >= cap:
            return selected

    for entry in remaining:
        if len(selected) >= cap:
            break
        selected.append(entry)
    return selected


@dataclass
class ContextPack:
    user_id: UUID
    intent: str
    preferences: dict[str, Any]
    goals: list[dict[str, Any]]
    episodic_memories: list[dict[str, Any]]
    budgets: dict[str, int]
    token_usage: dict[str, int]
    budget_remaining: dict[str, int]
    pack_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    plan_context: dict[str, Any] | None = None  # PlanScope context

    def to_prompt_context(self) -> dict[str, Any]:
        result = {
            "preferences": self.preferences,
            "active_goals": self.goals,
            "episodic_memories": self.episodic_memories,
            "context_pack": {
                "intent": self.intent,
                "budgets": self.budgets,
                "token_usage": self.token_usage,
                "budget_remaining": self.budget_remaining,
                "pack_id": str(self.pack_id) if self.pack_id else None,
                "metadata": self.metadata or {},
            },
        }
        # Include plan_context if present (non-empty)
        if self.plan_context:
            result["plan_context"] = self.plan_context
        return result


class ContextPackBuilder:
    def __init__(
        self,
        db: AsyncSession,
        scheduler: ContextBudgetScheduler | None = None,
        redis=None,
    ) -> None:
        self.db = db
        self.memory_service = MemoryService(db)
        self.scheduler = scheduler or ContextBudgetScheduler(db=db)
        self.redis = redis

    async def build(
        self,
        user_id: UUID,
        intent: str,
        request_id: str | None = None,
        trace_id: str | None = None,
        plan_id: UUID | None = None,
    ) -> ContextPack:
        rollout_enabled = True
        if settings.ENABLE_LTM_ROLLOUT:
            rollout_service = LtmRolloutService(self.db)
            rollout_enabled = await rollout_service.is_enabled(user_id)

        budgets = await self.scheduler.allocate(intent, user_id=user_id)
        CONTEXT_PACK_BUILD.labels(intent=intent).inc()
        CONTEXT_PACK_INTENT.labels(intent=intent).inc()

        # Build enriched plan context with UserScope cognitive profile if plan_id is provided
        plan_context: dict[str, Any] | None = None
        if plan_id:
            try:
                plan_builder = PlanContextBuilder(self.db, self.redis)
                # Use build_enriched to include UserScope cognitive insights
                plan_context = await plan_builder.build_enriched(
                    user_id,
                    plan_id,
                    include_cognitive_profile=True,
                    include_behavior_patterns=True,
                )
            except Exception as e:
                logger.warning(f"Failed to build enriched plan context: {e}")
                # Fallback to basic plan context
                try:
                    plan_context = await plan_builder.build(user_id, plan_id)
                except Exception as e2:
                    logger.warning(f"Failed to build basic plan context: {e2}")
                    plan_context = None

        conflict_enabled = settings.ENABLE_MEMORY_CONFLICT_RESOLUTION and rollout_enabled
        resolver = MemoryConflictResolver() if conflict_enabled else None

        preference_records = await self.memory_service.list_preference_records(user_id)
        goals = await self.memory_service.list_active_goals(user_id)
        episodic = await self.memory_service.list_recent_episodic(user_id, limit=20)
        pref_history: list[Any] = []
        if conflict_enabled:
            pref_history = await self.memory_service.list_preference_history(user_id)

        metadata: dict[str, Any] = {}
        ranking_enabled = settings.ENABLE_CONTEXT_RANKING and rollout_enabled
        conflicts: list[dict[str, Any]] = []
        weights: dict[str, float] | None = None
        if ranking_enabled and settings.ENABLE_PERSONALIZED_RANKING and rollout_enabled:
            policy_service = MemoryRankPolicyService(self.db)
            weights = await policy_service.get_policy(intent, user_id)

        if ranking_enabled:
            ranked_preferences = rank_items(preference_records, kind="preferences", weights=weights)
            ranked_goals = rank_items(goals, kind="goals", weights=weights)
            ranked_episodic = rank_items(episodic, kind="episodic", weights=weights)

            cap_goals = settings.CONTEXT_RANKING_SOFT_CAP_GOALS
            cap_episodic = settings.CONTEXT_RANKING_SOFT_CAP_EPISODIC

            selected_goals = _select_with_diversity(
                ranked_goals,
                cap_goals,
                lambda item: item.status,
            )
            selected_episodic = _select_with_diversity(
                ranked_episodic,
                cap_episodic,
                lambda item: (item.tags or [None])[0],
            )

            resolved_pref_records = preference_records
            resolved_goals = [entry.item for entry in selected_goals]
            resolved_episodic = [entry.item for entry in selected_episodic]

            if conflict_enabled and resolver is not None:
                preferences, resolved_pref_records, pref_conflicts = resolver.resolve_preferences(
                    {item.pref_key: item.pref_value for item in preference_records},
                    pref_history or resolved_pref_records,
                )
                resolved_goals, goal_conflicts = resolver.resolve_goals(resolved_goals)
                resolved_episodic, episodic_conflicts = resolver.resolve_episodic(resolved_episodic)
                resolved_goals, resolved_episodic, cross_conflicts = resolver.resolve_cross_type(
                    resolved_goals,
                    resolved_episodic,
                )
                conflicts.extend(pref_conflicts)
                conflicts.extend(goal_conflicts)
                conflicts.extend(episodic_conflicts)
                conflicts.extend(cross_conflicts)
            else:
                preferences = {item.pref_key: item.pref_value for item in preference_records}

            ranked_preferences = rank_items(resolved_pref_records, kind="preferences", weights=weights)
            ranked_goals = rank_items(resolved_goals, kind="goals", weights=weights)
            ranked_episodic = rank_items(resolved_episodic, kind="episodic", weights=weights)

            goal_payloads = [
                {
                    "id": str(entry.item.id),
                    "title": entry.item.title,
                    "status": entry.item.status,
                    "target_date": entry.item.target_date,
                }
                for entry in ranked_goals
            ]
            episodic_payloads = [
                {
                    "id": str(entry.item.id),
                    "summary": entry.item.summary,
                    "occurred_at": entry.item.occurred_at,
                    "importance_score": entry.item.importance_score,
                }
                for entry in ranked_episodic
            ]

            pref_scores = {entry.item.pref_key: entry.score for entry in ranked_preferences}
            goal_scores = {str(entry.item.id): entry.score for entry in ranked_goals}
            episodic_scores = {str(entry.item.id): entry.score for entry in ranked_episodic}
        else:
            preference_records.sort(
                key=lambda item: (item.evidence_score or 0.0, item.updated_at),
                reverse=True,
            )
            goals.sort(
                key=lambda item: (item.evidence_score or 0.0, item.updated_at),
                reverse=True,
            )
            episodic.sort(
                key=lambda item: (item.evidence_score or 0.0, item.occurred_at),
                reverse=True,
            )

            resolved_pref_records = preference_records
            resolved_goals = goals
            resolved_episodic = episodic

            if conflict_enabled and resolver is not None:
                preferences, resolved_pref_records, pref_conflicts = resolver.resolve_preferences(
                    {item.pref_key: item.pref_value for item in preference_records},
                    pref_history or resolved_pref_records,
                )
                resolved_goals, goal_conflicts = resolver.resolve_goals(resolved_goals)
                resolved_episodic, episodic_conflicts = resolver.resolve_episodic(resolved_episodic)
                resolved_goals, resolved_episodic, cross_conflicts = resolver.resolve_cross_type(
                    resolved_goals,
                    resolved_episodic,
                )
                conflicts.extend(pref_conflicts)
                conflicts.extend(goal_conflicts)
                conflicts.extend(episodic_conflicts)
                conflicts.extend(cross_conflicts)
            else:
                preferences = {item.pref_key: item.pref_value for item in preference_records}

            goal_payloads = [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "status": item.status,
                    "target_date": item.target_date,
                }
                for item in resolved_goals
            ]
            episodic_payloads = [
                {
                    "id": str(item.id),
                    "summary": item.summary,
                    "occurred_at": item.occurred_at,
                    "importance_score": item.importance_score,
                }
                for item in resolved_episodic
            ]

            pref_scores = {}
            goal_scores = {}
            episodic_scores = {}

        pref_budget = budgets.get("preferences", 0)
        goals_budget = budgets.get("goals", 0)
        episodic_budget = budgets.get("episodic", 0)

        original_usage = {
            "preferences": estimate_tokens(_serialize(preferences)),
            "goals": estimate_tokens(_serialize(goal_payloads)),
            "episodic": estimate_tokens(_serialize(episodic_payloads)),
        }

        if ranking_enabled:
            trimmed_preferences, pref_scores = _trim_ranked_preferences(ranked_preferences, pref_budget)
            trimmed_goals, goal_scores = _trim_ranked_list(goal_payloads, goal_scores, goals_budget)
            trimmed_episodic, episodic_scores = _trim_ranked_list(
                episodic_payloads,
                episodic_scores,
                episodic_budget,
            )
            trimmed_pref_scores = {key: pref_scores.get(key, 0.0) for key in trimmed_preferences}
        else:
            trimmed_preferences = _trim_preferences(preferences, pref_budget)
            trimmed_goals = _trim_list(goal_payloads, goals_budget)
            trimmed_episodic = _trim_list(episodic_payloads, episodic_budget)
            trimmed_pref_scores = {}

        token_usage = {
            "preferences": estimate_tokens(_serialize(trimmed_preferences)),
            "goals": estimate_tokens(_serialize(trimmed_goals)),
            "episodic": estimate_tokens(_serialize(trimmed_episodic)),
        }
        budget_remaining = {
            "preferences": pref_budget - token_usage["preferences"],
            "goals": goals_budget - token_usage["goals"],
            "episodic": episodic_budget - token_usage["episodic"],
        }

        if ranking_enabled:
            metadata["ranking"] = {
                "preferences": [
                    {"key": key, "score": trimmed_pref_scores.get(key, 0.0)}
                    for key in list(trimmed_preferences.keys())[:10]
                ],
                "goals": [
                    {"id": payload.get("id"), "score": goal_scores.get(payload.get("id"), 0.0)}
                    for payload in trimmed_goals[:10]
                ],
                "episodic": [
                    {"id": payload.get("id"), "score": episodic_scores.get(payload.get("id"), 0.0)}
                    for payload in trimmed_episodic[:10]
                ],
            }
        if conflicts:
            metadata["conflicts"] = conflicts

        preference_source_records = resolved_pref_records if conflict_enabled else preference_records
        goal_source_records = resolved_goals if conflict_enabled else goals
        episodic_source_records = resolved_episodic if conflict_enabled else episodic

        def _iso(dt_value):
            return dt_value.isoformat() if dt_value else None

        def _top_by_score(items, limit=3):
            return sorted(items, key=lambda item: getattr(item, "evidence_score", 0.0), reverse=True)[:limit]

        evidence_summary = {
            "preferences": [
                {
                    "key": item.pref_key,
                    "score": item.evidence_score,
                    "updated_at": _iso(getattr(item, "updated_at", None)),
                }
                for item in _top_by_score(preference_source_records)
            ],
            "goals": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "score": item.evidence_score,
                    "updated_at": _iso(getattr(item, "updated_at", None)),
                    "target_date": _iso(item.target_date),
                }
                for item in _top_by_score(goal_source_records)
            ],
            "episodic": [
                {
                    "id": str(item.id),
                    "summary": item.summary[:60],
                    "score": item.evidence_score,
                    "updated_at": _iso(getattr(item, "updated_at", None)),
                    "occurred_at": _iso(item.occurred_at),
                }
                for item in _top_by_score(episodic_source_records)
            ],
        }

        if evidence_summary["preferences"] or evidence_summary["goals"] or evidence_summary["episodic"]:
            metadata["evidence_summary"] = evidence_summary

        pack_id = None
        if settings.ENABLE_CONTEXT_PACK_TELEMETRY:
            trimmed_goal_ids = {payload.get("id") for payload in trimmed_goals}
            trimmed_episodic_ids = {payload.get("id") for payload in trimmed_episodic}
            pref_scores = [
                item.evidence_score
                for item in preference_source_records
                if item.pref_key in trimmed_preferences
            ]
            goal_scores = [
                item.evidence_score
                for item in goal_source_records
                if str(item.id) in trimmed_goal_ids
            ]
            episodic_scores = [
                item.evidence_score
                for item in episodic_source_records
                if str(item.id) in trimmed_episodic_ids
            ]
            scores = [score for score in pref_scores + goal_scores + episodic_scores if score is not None]
            evidence_avg = (sum(scores) / len(scores)) if scores else None

            telemetry = ContextPackTelemetryService(self.db)
            pack_id = await telemetry.record_run(
                user_id=user_id,
                intent=intent,
                budgets=budgets,
                token_usage=token_usage,
                memory_counts={
                    "preferences": len(trimmed_preferences),
                    "goals": len(trimmed_goals),
                    "episodic": len(trimmed_episodic),
                },
                evidence_score_avg=evidence_avg,
                request_id=request_id,
                trace_id=trace_id,
            )

        for section, usage in original_usage.items():
            budget = budgets.get(section, 0)
            if usage > budget:
                CONTEXT_PACK_OVER_BUDGET.labels(intent=intent, section=section).inc()
                logger.info(
                    "Context pack trimmed {section}: usage={usage} budget={budget}",
                    section=section,
                    usage=usage,
                    budget=budget,
                )

        return ContextPack(
            user_id=user_id,
            intent=intent,
            preferences=trimmed_preferences,
            goals=trimmed_goals,
            episodic_memories=trimmed_episodic,
            budgets=budgets,
            token_usage=token_usage,
            budget_remaining=budget_remaining,
            pack_id=pack_id,
            metadata=metadata or None,
            plan_context=plan_context,
        )
