"""Guided goal creation and deterministic milestone preview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.goal import Goal


@dataclass(frozen=True)
class GoalMilestoneDraft:
    id: str
    title: str
    description: str
    estimated_days: int
    acceptance_criteria: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "estimated_days": self.estimated_days,
            "acceptance_criteria": self.acceptance_criteria,
        }


@dataclass(frozen=True)
class GoalDecompositionPreview:
    goal_type: str
    time_horizon: str
    suggested_target_date: date
    rationale: str
    milestones: list[GoalMilestoneDraft]

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_type": self.goal_type,
            "time_horizon": self.time_horizon,
            "suggested_target_date": self.suggested_target_date.isoformat(),
            "rationale": self.rationale,
            "milestones": [milestone.to_dict() for milestone in self.milestones],
        }


class GoalDecompositionService:
    """Build an editable milestone scaffold for the goal wizard."""

    _TEMPLATES: dict[str, list[tuple[str, str]]] = {
        "academic": [
            ("Map the baseline", "Confirm scope, weak topics, and the first measurable benchmark."),
            ("Repair the core gaps", "Practice the prerequisites that block progress most often."),
            ("Timed practice loop", "Run short drills and review mistakes after each round."),
            ("Readiness check", "Complete a mock or rubric check before the deadline."),
        ],
        "skill": [
            ("Learn the fundamentals", "Cover the minimum concepts needed to build something small."),
            ("Build a first artifact", "Create a concrete project that proves the skill is usable."),
            ("Feedback and iteration", "Use feedback to refine technique and fix recurring errors."),
            ("Showcase the skill", "Package the result so progress is visible and reusable."),
        ],
        "habit": [
            ("Design the trigger", "Pick the cue, time, and environment that make the habit easy to start."),
            ("Stabilize the first streak", "Keep the daily action small enough to repeat consistently."),
            ("Handle interruptions", "Define recovery rules for missed days and high-friction moments."),
            ("Review and lock in", "Measure whether the habit still supports the original motivation."),
        ],
        "project": [
            ("Define the scope", "Write the outcome, constraints, and the smallest useful version."),
            ("Prototype the core", "Build the main workflow before polishing secondary details."),
            ("Test with real use", "Validate the prototype with realistic inputs or users."),
            ("Ship and review", "Release the outcome and capture follow-up improvements."),
        ],
        "other": [
            ("Clarify the outcome", "Turn the goal into observable success conditions."),
            ("Create the first plan", "Pick the first sequence of actions and a review cadence."),
            ("Execute and adjust", "Run the plan, then adjust based on evidence."),
        ],
    }

    _HORIZON_DAYS = {
        "short": 21,
        "medium": 75,
        "long": 150,
    }

    def preview(
        self,
        *,
        title: str,
        goal_type: str,
        motivation: str,
        time_horizon: str,
        target_date: date | None = None,
    ) -> GoalDecompositionPreview:
        normalized_type = self._normalize_goal_type(goal_type)
        normalized_horizon = self._normalize_horizon(time_horizon)
        total_days = self._days_until(target_date) if target_date else self._HORIZON_DAYS[normalized_horizon]
        suggested_target_date = target_date or datetime.now(UTC).date() + timedelta(days=total_days)
        templates = self._TEMPLATES[normalized_type]
        step_days = max(3, total_days // max(1, len(templates)))

        milestones = [
            GoalMilestoneDraft(
                id=f"m{index + 1}",
                title=label,
                description=self._personalize_description(description, title=title, motivation=motivation),
                estimated_days=min(total_days, step_days * (index + 1)),
                acceptance_criteria=[
                    f"Produce visible evidence for: {label}",
                    "Review progress and decide the next adjustment.",
                ],
            )
            for index, (label, description) in enumerate(templates)
        ]
        return GoalDecompositionPreview(
            goal_type=normalized_type,
            time_horizon=normalized_horizon,
            suggested_target_date=suggested_target_date,
            rationale=self._rationale(normalized_type, normalized_horizon),
            milestones=milestones,
        )

    async def create_goal(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        title: str,
        goal_type: str,
        motivation: str,
        time_horizon: str,
        description: str | None,
        target_date: date | None,
        milestones: list[dict[str, Any]],
    ) -> Goal:
        normalized_type = self._normalize_goal_type(goal_type)
        normalized_milestones = [self._normalize_milestone(item, index) for index, item in enumerate(milestones)]
        minimum_criteria = [
            {
                "id": milestone["id"],
                "label": milestone["title"],
                "metric": "milestone_completed",
                "threshold": "1",
                "unit": "boolean",
                "met": False,
            }
            for milestone in normalized_milestones
        ]
        goal = Goal(
            user_id=user_id,
            title=title.strip(),
            goal_type=normalized_type,
            description=(description or motivation).strip() or None,
            status="active",
            target_date=target_date,
            priority="normal",
            source="manual",
            minimum_acceptance_criteria=minimum_criteria,
            metadata_payload={
                "creation_wizard": {
                    "motivation": motivation.strip(),
                    "time_horizon": self._normalize_horizon(time_horizon),
                    "milestones": normalized_milestones,
                    "created_at": datetime.now(UTC).isoformat(),
                }
            },
        )
        db.add(goal)
        await db.flush()
        await db.refresh(goal)
        return goal

    def _normalize_goal_type(self, goal_type: str) -> str:
        value = goal_type.strip().lower()
        aliases = {
            "exam": "academic",
            "school": "academic",
            "study": "academic",
            "skills": "skill",
            "habits": "habit",
            "general": "other",
        }
        value = aliases.get(value, value)
        return value if value in self._TEMPLATES else "other"

    def _normalize_horizon(self, time_horizon: str) -> str:
        value = time_horizon.strip().lower()
        return value if value in self._HORIZON_DAYS else "medium"

    def _days_until(self, target_date: date) -> int:
        return max(7, (target_date - datetime.now(UTC).date()).days)

    def _personalize_description(self, description: str, *, title: str, motivation: str) -> str:
        if motivation.strip():
            return f"{description} Keep it tied to why this matters: {motivation.strip()}"
        return f"{description} Target goal: {title.strip()}."

    def _rationale(self, goal_type: str, time_horizon: str) -> str:
        horizon_label = {
            "short": "short-term",
            "medium": "medium-term",
            "long": "long-term",
        }[time_horizon]
        return f"A {horizon_label} {goal_type} goal works best with visible checkpoints and editable evidence."

    def _normalize_milestone(self, raw: dict[str, Any], index: int) -> dict[str, Any]:
        title = str(raw.get("title") or f"Milestone {index + 1}").strip()
        criteria = raw.get("acceptance_criteria")
        if not isinstance(criteria, list):
            criteria = ["Show visible progress."]
        return {
            "id": str(raw.get("id") or f"m{index + 1}").strip(),
            "title": title,
            "description": str(raw.get("description") or "").strip(),
            "estimated_days": int(raw.get("estimated_days") or (index + 1) * 14),
            "acceptance_criteria": [str(item).strip() for item in criteria if str(item).strip()],
        }


goal_decomposition_service = GoalDecompositionService()
