from app.agents.standard_workflow import _update_feedback_binding_runtime_state
from app.orchestration.statechart_engine import WorkflowState


def test_feedback_binding_runtime_state_clears_stale_values_when_unbound() -> None:
    state = WorkflowState(
        context_data={
            "active_interventions": [{"intervention_id": "old-id"}],
            "active_intervention_id": "old-id",
            "last_feedback_binding": {"message_id": "old-msg"},
        }
    )

    _update_feedback_binding_runtime_state(
        state,
        {
            "bound": False,
            "active_interventions": [],
            "reason": "no_active_intervention",
        },
    )

    assert state.context_data["active_interventions"] == []
    assert "active_intervention_id" not in state.context_data
    assert "last_feedback_binding" not in state.context_data
