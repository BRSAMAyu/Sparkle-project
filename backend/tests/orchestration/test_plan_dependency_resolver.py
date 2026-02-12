from app.orchestration.plan_dependency_resolver import PlanDependencyResolver
from app.orchestration.schemas import ToolCallSpec


def test_dependency_resolver_links_semantic_and_reference_dependencies() -> None:
    tool_calls = [
        ToolCallSpec(
            id="call_create_plan",
            name="create_plan",
            params={"title": "Math Sprint"},
        ),
        ToolCallSpec(
            id="call_generate",
            name="generate_tasks_for_plan",
            params={"plan_id": "{{call_create_plan.plan_id}}"},
        ),
    ]

    result = PlanDependencyResolver().resolve(tool_calls)

    assert result.total_dependencies >= 1
    assert "call_create_plan" in tool_calls[1].depends_on
    assert tool_calls[0].output_key is not None
