from app.agents.graph.nodes.expert_node_factory import create_specialist_node


study_buddy_node = create_specialist_node(
    agent_id="study_buddy",
    planning_prompt=(
        "You are in planning-only mode as study buddy. Provide lightweight guidance or "
        "tool calls when needed, but avoid over-planning."
    ),
    task_prompt_prefix="Study buddy context",
    toolset=[],
)
