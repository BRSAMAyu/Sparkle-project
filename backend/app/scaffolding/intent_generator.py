"""Intent generation for adaptive interventions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InterventionIntent:
    intent_type: str
    urgency: float
    context_variables: dict[str, Any] = field(default_factory=dict)


class IntentGenerator:
    """Maps triggers and edge state to structured intervention intent."""

    def generate_intent(
        self,
        trigger_event: str,
        urgency: float,
        context: dict[str, Any],
        edge_state: dict[str, Any],
        scaffolding_state: dict[str, Any],
    ) -> InterventionIntent:
        intent_type = self._map_trigger(trigger_event)
        variables = {
            "task_name": context.get("task_name") or context.get("task") or "当前任务",
            "suggested_step": context.get("suggested_step") or "先从第一步开始",
            "break_duration": context.get("break_duration") or "5",
            "focus_duration": context.get("focus_duration") or "25",
            "estimated_time": context.get("estimated_time") or "20",
            "alternative_task": context.get("alternative_task") or "换一个任务",
            "relaxation_activity": context.get("relaxation_activity") or "深呼吸",
            "switch_count": context.get("switch_count") or str(edge_state.get("switch_count", 0)),
        }
        variables.update({
            "urgency": f"{urgency:.2f}",
            "support_level": str(scaffolding_state.get("support_level", 3)),
        })
        return InterventionIntent(
            intent_type=intent_type,
            urgency=max(0.0, min(urgency, 1.0)),
            context_variables=variables,
        )

    def _map_trigger(self, trigger_event: str) -> str:
        mapping = {
            "recover_attention": "recover_to_task",
            "idle_trigger": "recover_to_task",
            "resume_after_background": "recover_to_task",
            "task_stuck_no_start": "recover_to_task",
            "suggest_break": "suggest_break",
            "fatigue": "suggest_break",
            "reduce_stress": "reduce_stress",
            "stress": "reduce_stress",
            "distraction_pattern": "distraction_recovery",
            "distraction": "distraction_recovery",
            "encourage_start": "encourage_start",
        }
        return mapping.get(trigger_event, "recover_to_task")
