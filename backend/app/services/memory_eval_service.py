from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.business_metrics import LTM_EVAL_AVG_SCORE, LTM_EVAL_CASE_TOTAL, LTM_EVAL_TOTAL
from app.core.context_pack import ContextPackBuilder
from app.services.memory_service import MemoryService


@dataclass
class EvalCase:
    case_id: str
    user_id: UUID
    intent: str
    expected_pref_keys: list[str]
    expected_goal_titles: list[str]
    expected_episodic_contains: list[str]
    forbidden_contains: list[str]
    max_episodic_age_days: int | None = None
    notes: str | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def load_dataset(path: str | Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    dataset_path = Path(path)
    if not dataset_path.exists():
        path_text = str(dataset_path)
        if path_text.startswith("backend/"):
            alt = Path(path_text.removeprefix("backend/"))
            if alt.exists():
                dataset_path = alt
    with dataset_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            cases.append(
                EvalCase(
                    case_id=payload["case_id"],
                    user_id=UUID(payload["user_id"]),
                    intent=payload["intent"],
                    expected_pref_keys=list(payload.get("expected_pref_keys", [])),
                    expected_goal_titles=list(payload.get("expected_goal_titles", [])),
                    expected_episodic_contains=list(payload.get("expected_episodic_contains", [])),
                    forbidden_contains=list(payload.get("forbidden_contains", [])),
                    max_episodic_age_days=payload.get("max_episodic_age_days"),
                    notes=payload.get("notes"),
                )
            )
    return cases


def _safe_lower(value: str | None) -> str:
    if not value:
        return ""
    return value.lower()


def _hit_rate(expected: list[str], matched: int) -> float:
    if not expected:
        return 1.0
    return matched / len(expected)


def _case_score(metrics: dict[str, float]) -> float:
    return (
        metrics["pref_hit_rate"]
        + metrics["goal_hit_rate"]
        + metrics["episodic_hit_rate"]
        + (1.0 - metrics["over_inclusion_rate"])
        + metrics["evidence_quality"]
        + (1.0 - metrics["staleness_rate"])
    ) / 6.0


class MemoryEvalService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.memory_service = MemoryService(db)
        self.context_builder = ContextPackBuilder(db)

    async def run_case(self, case: EvalCase) -> dict[str, Any]:
        context_pack = await self.context_builder.build(case.user_id, intent=case.intent)

        preference_records = await self.memory_service.list_preference_records(case.user_id)
        goals = await self.memory_service.list_active_goals(case.user_id)
        episodic = await self.memory_service.list_recent_episodic(case.user_id, limit=50)

        pref_map = {item.pref_key: item for item in preference_records}
        goal_map = {str(item.id): item for item in goals}
        episodic_map = {str(item.id): item for item in episodic}

        pref_keys = list(context_pack.preferences.keys())
        goal_titles = [item.get("title", "") for item in context_pack.goals]
        episodic_summaries = [item.get("summary", "") for item in context_pack.episodic_memories]

        expected_pref_keys = case.expected_pref_keys
        expected_goal_titles = case.expected_goal_titles
        expected_episodic_contains = case.expected_episodic_contains

        matched_pref_keys = sum(1 for key in expected_pref_keys if key in pref_keys)
        matched_goals = 0
        goal_titles_lower = [_safe_lower(title) for title in goal_titles]
        for expected in expected_goal_titles:
            expected_lower = _safe_lower(expected)
            if any(expected_lower in title for title in goal_titles_lower):
                matched_goals += 1

        matched_episodic = 0
        episodic_lower = [_safe_lower(summary) for summary in episodic_summaries]
        for expected in expected_episodic_contains:
            expected_lower = _safe_lower(expected)
            if any(expected_lower in summary for summary in episodic_lower):
                matched_episodic += 1

        forbidden_hits = 0
        forbidden_lower = [_safe_lower(item) for item in case.forbidden_contains]
        for text in pref_keys + goal_titles + episodic_summaries:
            candidate = _safe_lower(text)
            if any(token and token in candidate for token in forbidden_lower):
                forbidden_hits += 1

        total_returned = len(pref_keys) + len(goal_titles) + len(episodic_summaries)
        over_inclusion_rate = (forbidden_hits / total_returned) if total_returned else 0.0

        evidence_scores: list[float] = []
        for key in pref_keys:
            record = pref_map.get(key)
            if record is not None:
                evidence_scores.append(record.evidence_score or 0.0)
        for item in context_pack.goals:
            record = goal_map.get(item.get("id", ""))
            if record is not None:
                evidence_scores.append(record.evidence_score or 0.0)
        for item in context_pack.episodic_memories:
            record = episodic_map.get(item.get("id", ""))
            if record is not None:
                evidence_scores.append(record.evidence_score or 0.0)

        evidence_quality = sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0

        staleness_rate = 0.0
        if case.max_episodic_age_days:
            cutoff = _utcnow() - timedelta(days=case.max_episodic_age_days)
            stale_count = 0
            for item in context_pack.episodic_memories:
                record = episodic_map.get(item.get("id", ""))
                if record is not None and record.occurred_at < cutoff:
                    stale_count += 1
            if context_pack.episodic_memories:
                staleness_rate = stale_count / len(context_pack.episodic_memories)

        metrics = {
            "pref_hit_rate": _hit_rate(expected_pref_keys, matched_pref_keys),
            "goal_hit_rate": _hit_rate(expected_goal_titles, matched_goals),
            "episodic_hit_rate": _hit_rate(expected_episodic_contains, matched_episodic),
            "over_inclusion_rate": over_inclusion_rate,
            "evidence_quality": evidence_quality,
            "staleness_rate": staleness_rate,
        }

        metrics["score"] = _case_score(metrics)
        metrics["returned_counts"] = {
            "preferences": len(pref_keys),
            "goals": len(goal_titles),
            "episodic": len(episodic_summaries),
        }
        return metrics

    async def run_dataset(
        self,
        path: str | Path,
        intent: str | None = None,
        user_id: UUID | None = None,
        threshold: float | None = None,
    ) -> dict[str, Any]:
        cases = load_dataset(path)
        filtered: list[EvalCase] = []
        for case in cases:
            if intent and case.intent != intent:
                continue
            if user_id and case.user_id != user_id:
                continue
            filtered.append(case)

        threshold = threshold if threshold is not None else settings.LTM_EVAL_FAIL_THRESHOLD
        case_results = []
        scores: list[float] = []
        for case in filtered:
            metrics = await self.run_case(case)
            scores.append(metrics["score"])
            status = "ok" if metrics["score"] >= threshold else "fail"
            LTM_EVAL_CASE_TOTAL.labels(case_id=case.case_id, status=status).inc()
            case_results.append(
                {
                    "case_id": case.case_id,
                    "intent": case.intent,
                    "user_id": str(case.user_id),
                    "metrics": metrics,
                    "status": status,
                }
            )

        avg_score = sum(scores) / len(scores) if scores else 0.0
        overall_status = "ok" if avg_score >= threshold else "fail"
        LTM_EVAL_TOTAL.labels(status=overall_status).inc()
        if scores:
            LTM_EVAL_AVG_SCORE.set(avg_score)

        return {
            "status": overall_status,
            "avg_score": avg_score,
            "threshold": threshold,
            "case_count": len(case_results),
            "cases": case_results,
        }
