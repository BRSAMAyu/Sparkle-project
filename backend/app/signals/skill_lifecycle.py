"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine — Skill Lifecycle

SkillLifecycleManager — manages extracted strategy assets from injection through
promotion and deprecation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from app.signals.types import SkillEntry


_SKILL_TTL_SECONDS = 30 * 24 * 3600
_STALE_DAYS = 30
_SCOPE_RANK = {"personal": 0, "cohort": 1, "system": 2}
_PROMOTION_RULES = {
    ("personal", "cohort"): {"effective_count": 10, "avg_confidence": 0.8},
    ("cohort", "system"): {"effective_count": 50, "avg_confidence": 0.85},
}


class SkillLifecycleManager:
    """Skill inject/recommend/extract lifecycle with promotion and deprecation."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def store_skill(self, user_id: str, skill: SkillEntry) -> None:
        """Store a skill under the user index and individual lookup key."""
        skills = await self.get_user_skills(user_id)
        by_id = {existing.skill_id: existing for existing in skills}
        by_id[skill.skill_id] = skill

        user_key = self._user_skills_key(user_id)
        await self.redis.set(
            user_key,
            json.dumps([entry.to_dict() for entry in by_id.values()]),
            ex=_SKILL_TTL_SECONDS,
        )
        await self.redis.set(
            self._skill_key(skill.skill_id),
            json.dumps(skill.to_dict()),
            ex=_SKILL_TTL_SECONDS,
        )

        logger.info(
            "SkillLifecycle: stored skill={} user={} scope={}",
            skill.skill_id,
            user_id,
            skill.scope,
        )

    async def get_user_skills(self, user_id: str) -> list[SkillEntry]:
        """Return all skills stored for a user."""
        raw = await self.redis.get(self._user_skills_key(user_id))
        if not raw:
            return []
        data = self._loads(raw, default=[])
        if not isinstance(data, list):
            return []
        return [SkillEntry.from_dict(item) for item in data if isinstance(item, dict)]

    async def get_skill(self, skill_id: str) -> SkillEntry | None:
        """Return a skill by ID from the individual skill index."""
        raw = await self.redis.get(self._skill_key(skill_id))
        if not raw:
            return None
        data = self._loads(raw, default=None)
        if not isinstance(data, dict):
            return None
        return SkillEntry.from_dict(data)

    def find_applicable_skills(
        self,
        skills: list[SkillEntry],
        context: dict[str, Any],
    ) -> list[SkillEntry]:
        """Find skills matching current context and minimum evidence."""
        applicable: list[SkillEntry] = []
        for skill in skills:
            if skill.effective_count < 3:
                continue
            if skill.evidence.get("deprecated") is True:
                continue
            if not self._matches_context(skill, context):
                continue
            applicable.append(skill)

        return sorted(
            applicable,
            key=lambda item: (
                _SCOPE_RANK.get(item.scope, 99),
                -item.effective_count,
                item.skill_id,
            ),
        )

    def build_worked_example_repair(
        self,
        skill: SkillEntry,
        task_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert a skill into a worked-example-repair task modification."""
        return {
            "task_type_override": "worked_example_then_drill",
            "strategy_summary": skill.strategy.get("intervention_summary", ""),
            "applies_to_nodes": skill.applicable_when.get("state_key"),
            "evidence": skill.evidence,
            "task_context": task_context,
        }

    def build_recommendation(self, skill: SkillEntry) -> dict[str, Any] | None:
        """Build a user-confirmable skill recommendation."""
        if skill.effective_count < 5 or skill.evidence.get("deprecated") is True:
            return None

        avg_confidence = self._avg_confidence(skill)
        user_options = [
            {"action": "confirm", "label": "Use this"},
            {"action": "not_now", "label": "Not now"},
            {"action": "dont_suggest_again", "label": "Don't suggest again"},
        ]
        return {
            "skill_id": skill.skill_id,
            "title": "发现一个对你有效的策略",
            "evidence_summary": (
                f"Worked {skill.effective_count}/{self._sample_size(skill)} times "
                f"(avg confidence {avg_confidence:.0%})."
            ),
            "strategy_summary": skill.strategy.get("intervention_summary", ""),
            "user_options": user_options,
            "options": user_options,
        }

    def validate_extraction(self, skill: SkillEntry) -> dict[str, Any]:
        """Validate a candidate skill before extraction."""
        issues: list[str] = []
        if not skill.skill_id:
            issues.append("missing_skill_id")
        if skill.scope not in _SCOPE_RANK:
            issues.append("invalid_scope")
        if not skill.source_policy_key:
            issues.append("missing_source_policy_key")
        if not skill.strategy:
            issues.append("missing_strategy")
            issues.append("missing_intervention_summary")
        elif not skill.strategy.get("intervention_summary"):
            issues.append("missing_intervention_summary")
        if skill.effective_count < 3:
            issues.append("insufficient_effective_count")
            issues.append("effective_count_below_threshold")
        if skill.sample_size < skill.effective_count:
            issues.append("sample_size_below_effective_count")
        if self._avg_confidence(skill) < 0.7:
            issues.append("low_confidence")
        if skill.scope != "personal" and not self._is_shareable(skill):
            issues.append("non_shareable_non_personal_skill")

        return {"valid": not issues, "issues": issues}

    async def promote_skill(
        self,
        user_id: str,
        skill_id: str,
        to_scope: str,
    ) -> SkillEntry | None:
        """Promote a skill from personal to cohort, or cohort to system."""
        skill = await self.get_skill(skill_id)
        if skill is None:
            return None

        rule = _PROMOTION_RULES.get((skill.scope, to_scope))
        if rule is None:
            return None
        if not self._is_shareable(skill):
            return None
        if skill.effective_count < rule["effective_count"]:
            return None
        if self._avg_confidence(skill) < rule["avg_confidence"]:
            return None

        now = self._now()
        previous_scope = skill.scope
        skill.scope = to_scope
        history = list(skill.evidence.get("promotion_history", []))
        history.append({"from": previous_scope, "to": to_scope, "promoted_at": now})
        skill.evidence["promotion_history"] = history
        skill.evidence["promoted_from"] = previous_scope
        skill.evidence["promoted_at"] = now

        await self.store_skill(user_id, skill)
        logger.info(
            "SkillLifecycle: promoted skill={} user={} {}→{}",
            skill.skill_id,
            user_id,
            previous_scope,
            to_scope,
        )
        return skill

    async def deprecate_skill(self, user_id: str, skill_id: str, reason: str) -> None:
        """Mark a skill as deprecated without deleting it."""
        skill = await self.get_skill(skill_id)
        if skill is None:
            return

        skill.evidence["deprecated"] = True
        skill.evidence["deprecation_reason"] = reason
        skill.evidence["deprecated_at"] = self._now()
        await self.store_skill(user_id, skill)

        logger.info(
            "SkillLifecycle: deprecated skill={} user={} reason={}",
            skill_id,
            user_id,
            reason,
        )

    async def auto_deprecate_check(self, user_id: str) -> list[str]:
        """Auto-deprecate stale or repeatedly insufficient skills."""
        deprecated: list[str] = []
        skills = await self.get_user_skills(user_id)
        for skill in skills:
            if skill.evidence.get("deprecated") is True:
                continue
            reason = self._auto_deprecation_reason(skill)
            if reason is None:
                continue
            await self.deprecate_skill(user_id, skill.skill_id, reason)
            deprecated.append(skill.skill_id)
        return deprecated

    def compute_skill_health(self, skill: SkillEntry) -> dict[str, Any]:
        """Compute health metrics for a skill."""
        sample_size = self._sample_size(skill)
        health_score = self._clamp(skill.effective_count / sample_size)
        trend = self._outcome_trend(skill)

        if skill.evidence.get("deprecated") is True:
            recommendation = "deprecated"
        elif trend == "declining" or health_score < 0.5:
            recommendation = "review_or_deprecate"
        elif health_score >= 0.8 and trend in ("improving", "stable"):
            recommendation = "promote_or_reuse"
        else:
            recommendation = "keep_observing"

        return {
            "health_score": round(health_score, 3),
            "trend": trend,
            "recommendation": recommendation,
        }

    @staticmethod
    def _user_skills_key(user_id: str) -> str:
        return f"spine:skills:{user_id}"

    @staticmethod
    def _skill_key(skill_id: str) -> str:
        return f"spine:skill:{skill_id}"

    @staticmethod
    def _loads(raw: Any, *, default: Any) -> Any:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    @staticmethod
    def _is_shareable(skill: SkillEntry) -> bool:
        return bool((skill.privacy or {}).get("shareable"))

    @staticmethod
    def _avg_confidence(skill: SkillEntry) -> float:
        value = skill.evidence.get("avg_confidence", skill.evidence.get("average_confidence", 0.0))
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _sample_size(skill: SkillEntry) -> int:
        evidence_size = skill.evidence.get("sample_size", skill.evidence.get("total_observed", 0))
        try:
            sample_size = int(skill.sample_size or evidence_size or 0)
        except (TypeError, ValueError):
            sample_size = 0
        return max(sample_size, skill.effective_count, 1)

    @staticmethod
    def _matches_context(skill: SkillEntry, context: dict[str, Any]) -> bool:
        for key in ("goal_mode", "state_key"):
            expected = skill.applicable_when.get(key)
            actual = context.get(key)
            if expected is not None and actual is not None and expected != actual:
                return False
        return True

    @staticmethod
    def _recent_outcomes(skill: SkillEntry) -> list[Any]:
        outcomes = skill.evidence.get("recent_outcomes", skill.evidence.get("outcomes", []))
        return outcomes if isinstance(outcomes, list) else []

    @classmethod
    def _outcome_label(cls, outcome: Any) -> str:
        if isinstance(outcome, str):
            return outcome
        if isinstance(outcome, dict):
            value = outcome.get("attribution", outcome.get("outcome", ""))
            return str(value)
        return ""

    @classmethod
    def _last_five_insufficient(cls, skill: SkillEntry) -> bool:
        outcomes = cls._recent_outcomes(skill)
        if len(outcomes) < 5:
            return False
        return all(cls._outcome_label(item) == "insufficient" for item in outcomes[-5:])

    @classmethod
    def _is_stale(cls, skill: SkillEntry) -> bool:
        timestamp = (
            skill.evidence.get("effective_count_updated_at")
            or skill.evidence.get("last_effective_at")
            or skill.evidence.get("last_improved_at")
        )
        parsed = cls._parse_datetime(timestamp)
        if parsed is None:
            return False
        age = datetime.now(timezone.utc) - parsed
        return age.days >= _STALE_DAYS

    @classmethod
    def _auto_deprecation_reason(cls, skill: SkillEntry) -> str | None:
        if cls._last_five_insufficient(skill):
            return "last_5_outcomes_insufficient"
        if cls._is_stale(skill):
            return "effective_count_stale_30_days"
        return None

    @classmethod
    def _outcome_trend(cls, skill: SkillEntry) -> str:
        outcomes = cls._recent_outcomes(skill)
        if len(outcomes) < 4:
            return "stable"

        midpoint = len(outcomes) // 2
        previous = outcomes[:midpoint]
        recent = outcomes[midpoint:]

        def effective_ratio(items: list[Any]) -> float:
            if not items:
                return 0.0
            effective = sum(1 for item in items if cls._outcome_label(item) == "effective")
            return effective / len(items)

        delta = effective_ratio(recent) - effective_ratio(previous)
        if delta > 0.1:
            return "improving"
        if delta < -0.1:
            return "declining"
        return "stable"
