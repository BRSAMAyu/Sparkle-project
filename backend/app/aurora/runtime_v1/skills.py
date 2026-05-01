from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field

from app.aurora.common import AuroraSchemaBase


class SkillAffordance(AuroraSchemaBase):
    skill_id: str
    parameter: str
    title: str
    description: str
    surfaces: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class AuroraSkillRegistry:
    def __init__(self) -> None:
        self._registry = {
            "aurora.proactive_intensity": SkillAffordance(
                skill_id="aurora.proactive_intensity",
                parameter="proactive_intensity",
                title="Proactive Intensity",
                description="Tune how actively Aurora should keep pursuing unresolved informational tension.",
                surfaces=["aurora_modeling", "aurora_checkpoint"],
                tags=["control_surface", "follow_up"],
            ),
            "aurora.conversation_style": SkillAffordance(
                skill_id="aurora.conversation_style",
                parameter="conversation_style",
                title="Conversation Style",
                description="Adjust Aurora's current top-level tone between warm, structured, and exploratory.",
                surfaces=["aurora_modeling", "aurora_planning", "aurora_checkpoint"],
                tags=["control_surface", "style"],
            ),
            "aurora.task_density_hint": SkillAffordance(
                skill_id="aurora.task_density_hint",
                parameter="task_density_hint",
                title="Task Density Hint",
                description="Express how dense downstream execution suggestions should feel.",
                surfaces=["aurora_planning", "aurora_checkpoint"],
                tags=["control_surface", "execution_bridge"],
            ),
            "aurora.wake_scheduling": SkillAffordance(
                skill_id="aurora.wake_scheduling",
                parameter="next_wake_at",
                title="Wake Scheduling",
                description="Help Aurora decide whether a future self-wake is useful and acceptable.",
                surfaces=["aurora_checkpoint"],
                tags=["wake", "control_surface"],
            ),
            "aurora.agenda_priority": SkillAffordance(
                skill_id="aurora.agenda_priority",
                parameter="agenda_priority",
                title="Agenda Priority",
                description="Focus Aurora on the most valuable remaining information gap without hard-coding topic order.",
                surfaces=["aurora_modeling", "aurora_planning", "aurora_checkpoint"],
                tags=["control_surface", "tension"],
            ),
        }
        self._surface_candidates = {
            "aurora_modeling": [
                "aurora.proactive_intensity",
                "aurora.conversation_style",
                "aurora.agenda_priority",
            ],
            "aurora_planning": [
                "aurora.conversation_style",
                "aurora.agenda_priority",
                "aurora.task_density_hint",
            ],
            "aurora_checkpoint": [
                "aurora.conversation_style",
                "aurora.task_density_hint",
                "aurora.wake_scheduling",
                "aurora.agenda_priority",
            ],
        }

    def get(self, skill_id: str) -> SkillAffordance | None:
        return self._registry.get(skill_id)

    def list_all(self) -> list[SkillAffordance]:
        return list(self._registry.values())

    def surface_candidate_ids(self, surface: str) -> list[str]:
        return list(self._surface_candidates.get(surface, []))

    def load_candidate_affordances(
        self,
        surface: str,
        *,
        candidate_ids: Iterable[str] | None = None,
        exclude: Iterable[str] | None = None,
    ) -> list[SkillAffordance]:
        requested_ids = list(candidate_ids) if candidate_ids is not None else self.surface_candidate_ids(surface)
        excluded = {str(item) for item in (exclude or [])}
        seen: set[str] = set()
        candidates: list[SkillAffordance] = []

        for skill_id in requested_ids:
            if skill_id in seen or skill_id in excluded:
                continue
            affordance = self._registry.get(skill_id)
            if affordance is None or surface not in affordance.surfaces:
                continue
            seen.add(skill_id)
            candidates.append(affordance)

        return candidates
