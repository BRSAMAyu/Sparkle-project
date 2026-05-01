"""
Core: execution
Phase: plan→adapt
Stage: v2.5 Multi Goal Arbitration — resolve conflicts when user has multiple active goals

When a user has multiple goals competing for time and attention, this module
determines which goal should be prioritized in the current context based on
deadline pressure, momentum, and bottleneck severity.

All decisions are advisory — the user always has final say via PredictedReplyOptions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

_GOALS_KEY = "spine:goals:{user_id}"
_GOAL_KEY = "spine:goal:{user_id}:{goal_id}"
_GOAL_TTL = 90 * 24 * 3600
_MAX_ACTIVE_GOALS = 5


@dataclass
class ActiveGoal:
    goal_id: str
    goal_type: str
    title: str
    deadline_days: int | None = None  # days until deadline (None = no deadline)
    mastery: float = 0.0  # overall mastery 0-1
    momentum: float = 0.5  # 0-1 (from achievement system)
    bottleneck_severity: float = 0.0  # 0-1 (from GoalWorldGraph)
    last_active_hours: float = 0.0  # hours since last activity
    priority_override: str | None = None  # user can manually set "high"/"low"/"pause"

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "title": self.title,
            "deadline_days": self.deadline_days,
            "mastery": self.mastery,
            "momentum": self.momentum,
            "bottleneck_severity": self.bottleneck_severity,
            "last_active_hours": self.last_active_hours,
            "priority_override": self.priority_override,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ActiveGoal:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GoalArbitrationResult:
    primary_goal_id: str
    reason: str
    priority_scores: dict[str, float]  # goal_id → score
    suggested_time_split: dict[str, float]  # goal_id → fraction
    conflicts: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_goal_id": self.primary_goal_id,
            "reason": self.reason,
            "priority_scores": self.priority_scores,
            "suggested_time_split": self.suggested_time_split,
            "conflicts": self.conflicts,
        }


class MultiGoalArbitrator:
    """Arbitrate between multiple active goals."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def register_goal(self, user_id: str, goal: ActiveGoal) -> None:
        key = _GOAL_KEY.format(user_id=user_id, goal_id=goal.goal_id)
        await self.redis.set(key, json.dumps(goal.to_dict()), ex=_GOAL_TTL)
        idx_key = _GOALS_KEY.format(user_id=user_id)
        await self.redis.sadd(idx_key, goal.goal_id)
        await self.redis.expire(idx_key, _GOAL_TTL)

    async def get_active_goals(self, user_id: str) -> list[ActiveGoal]:
        idx_key = _GOALS_KEY.format(user_id=user_id)
        goal_ids = await self.redis.smembers(idx_key)
        goals = []
        for gid in goal_ids:
            gid_str = gid if isinstance(gid, str) else gid.decode()
            raw = await self.redis.get(_GOAL_KEY.format(user_id=user_id, goal_id=gid_str))
            if raw:
                goals.append(ActiveGoal.from_dict(json.loads(raw if isinstance(raw, str) else raw.decode())))
        return goals

    async def remove_goal(self, user_id: str, goal_id: str) -> None:
        await self.redis.delete(_GOAL_KEY.format(user_id=user_id, goal_id=goal_id))
        idx_key = _GOALS_KEY.format(user_id=user_id)
        await self.redis.srem(idx_key, goal_id)

    async def update_goal(self, user_id: str, goal_id: str, updates: dict[str, Any]) -> ActiveGoal | None:
        key = _GOAL_KEY.format(user_id=user_id, goal_id=goal_id)
        raw = await self.redis.get(key)
        if not raw:
            return None
        data = json.loads(raw if isinstance(raw, str) else raw.decode())
        for k, v in updates.items():
            if k in ActiveGoal.__dataclass_fields__:
                data[k] = v
        goal = ActiveGoal.from_dict(data)
        await self.redis.set(key, json.dumps(goal.to_dict()), ex=_GOAL_TTL)
        return goal

    def arbitrate(self, goals: list[ActiveGoal]) -> GoalArbitrationResult | None:
        """Determine which goal should be primary and how to split time."""
        if not goals:
            return None

        if len(goals) == 1:
            g = goals[0]
            return GoalArbitrationResult(
                primary_goal_id=g.goal_id,
                reason="single_active_goal",
                priority_scores={g.goal_id: 1.0},
                suggested_time_split={g.goal_id: 1.0},
                conflicts=[],
            )

        # Check for user overrides
        [g for g in goals if g.priority_override == "pause"]
        active = [g for g in goals if g.priority_override != "pause"]
        forced_high = [g for g in active if g.priority_override == "high"]

        if not active:
            return GoalArbitrationResult(
                primary_goal_id=goals[0].goal_id,
                reason="all_goals_paused",
                priority_scores={g.goal_id: 0.5 for g in goals},
                suggested_time_split={g.goal_id: 1.0 / len(goals) for g in goals},
                conflicts=["all_goals_paused"],
            )

        if forced_high:
            primary = forced_high[0]
            reason = "user_priority_override"
        else:
            scores = {g.goal_id: self._compute_priority(g) for g in active}
            primary = max(active, key=lambda g: scores[g.goal_id])
            reason = self._arbitration_reason(primary, scores)

        # Compute time split proportional to priority
        scores = {g.goal_id: self._compute_priority(g) for g in active}
        total_score = sum(scores.values())
        time_split = {}
        for g in active:
            time_split[g.goal_id] = round(scores[g.goal_id] / max(total_score, 0.01), 2)

        # Detect conflicts
        conflicts = self._detect_conflicts(goals)

        return GoalArbitrationResult(
            primary_goal_id=primary.goal_id,
            reason=reason,
            priority_scores=scores,
            suggested_time_split=time_split,
            conflicts=conflicts,
        )

    def _compute_priority(self, goal: ActiveGoal) -> float:
        """Compute priority score for a goal.

        Factors:
          - Deadline proximity: 0-0.4 (closer = higher)
          - Bottleneck severity: 0-0.2 (severe bottleneck = focus)
          - Momentum: 0-0.2 (low momentum = needs attention)
          - Mastery gap: 0-0.2 (low mastery = needs work)
        """
        # Deadline proximity
        deadline_score = 0.0
        if goal.deadline_days is not None and goal.deadline_days >= 0:
            if goal.deadline_days <= 3:
                deadline_score = 0.4
            elif goal.deadline_days <= 7:
                deadline_score = 0.3
            elif goal.deadline_days <= 14:
                deadline_score = 0.2
            elif goal.deadline_days <= 30:
                deadline_score = 0.1

        # Bottleneck severity (high = needs focus)
        bottleneck_score = goal.bottleneck_severity * 0.2

        # Low momentum = needs attention
        momentum_score = (1.0 - goal.momentum) * 0.2

        # Mastery gap (low mastery = needs work)
        mastery_score = (1.0 - goal.mastery) * 0.2

        total = deadline_score + bottleneck_score + momentum_score + mastery_score
        return round(total, 3)

    def _arbitration_reason(self, primary: ActiveGoal, scores: dict[str, float]) -> str:
        if primary.deadline_days is not None and primary.deadline_days <= 7:
            return "deadline_urgent"
        if primary.bottleneck_severity >= 0.7:
            return "critical_bottleneck"
        if primary.momentum <= 0.3:
            return "momentum_at_risk"
        if primary.mastery <= 0.3:
            return "mastery_gap"
        return "highest_priority_score"

    def _detect_conflicts(self, goals: list[ActiveGoal]) -> list[str]:
        conflicts = []
        deadline_goals = [g for g in goals if g.deadline_days is not None and g.deadline_days <= 7]
        if len(deadline_goals) >= 2:
            conflicts.append("multiple_urgent_deadlines")

        high_severity = [g for g in goals if g.bottleneck_severity >= 0.7]
        if high_severity:
            conflicts.append("bottleneck_goals_exist")

        stalled = [g for g in goals if g.momentum <= 0.3 and g.mastery > 0]
        if stalled:
            conflicts.append("stalled_goals_exist")

        return conflicts
