from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.agents.graph.nodes.deep_analyst import deep_analyst_node
from app.agents.graph.nodes.error_analyst import error_analyst_node
from app.agents.graph.nodes.exam_oracle import exam_oracle_node
from app.agents.graph.nodes.expert_node_factory import create_specialist_node
from app.agents.graph.nodes.galaxy_guide import galaxy_guide_node
from app.agents.graph.nodes.registry_tools import create_task, query_knowledge
from app.agents.graph.nodes.study_buddy import study_buddy_node
from app.agents.graph.nodes.time_tutor import time_tutor_node
from app.agents.graph.state import SparkleState


@dataclass(frozen=True)
class GraphExpertSpec:
    expert_id: str
    node_name: str
    node_handler: Callable[[SparkleState], dict]
    aliases: tuple[str, ...] = ()
    default_rank: int = 100
    supports_collaboration: bool = True


_math_node = create_specialist_node(
    agent_id="math_agent",
    planning_prompt=(
        "You are in planning-only mode as Math Expert. Use tool calls to retrieve relevant "
        "knowledge and create practice tasks when needed."
    ),
    task_prompt_prefix="Math expert context",
    toolset=[query_knowledge, create_task],
)

_code_node = create_specialist_node(
    agent_id="code_agent",
    planning_prompt=(
        "You are in planning-only mode as Code Expert. Use tool calls to retrieve references "
        "and create executable coding tasks."
    ),
    task_prompt_prefix="Code expert context",
    toolset=[query_knowledge, create_task],
)

_writing_node = create_specialist_node(
    agent_id="writing_agent",
    planning_prompt=(
        "You are in planning-only mode as Writing Expert. Generate structured writing guidance "
        "and optional practice tasks with tool calls."
    ),
    task_prompt_prefix="Writing expert context",
    toolset=[create_task],
)

_science_node = create_specialist_node(
    agent_id="science_agent",
    planning_prompt=(
        "You are in planning-only mode as Science Expert. Use tool calls for evidence retrieval "
        "and follow-up task creation."
    ),
    task_prompt_prefix="Science expert context",
    toolset=[query_knowledge, create_task],
)

_search_node = create_specialist_node(
    agent_id="search_agent",
    planning_prompt=(
        "You are in planning-only mode as Search Expert. Focus on evidence gathering using "
        "query_knowledge tool calls."
    ),
    task_prompt_prefix="Search expert context",
    toolset=[query_knowledge],
)


GRAPH_EXPERT_SPECS: tuple[GraphExpertSpec, ...] = (
    GraphExpertSpec("galaxy_guide", "galaxy_guide", galaxy_guide_node, aliases=("knowledge_agent",), default_rank=10),
    GraphExpertSpec("exam_oracle", "exam_oracle", exam_oracle_node, default_rank=20),
    GraphExpertSpec("time_tutor", "time_tutor", time_tutor_node, default_rank=30),
    GraphExpertSpec("deep_analyst", "deep_analyst", deep_analyst_node, default_rank=40),
    GraphExpertSpec("error_analyst", "error_analyst", error_analyst_node, default_rank=50),
    GraphExpertSpec("study_buddy", "study_buddy", study_buddy_node, aliases=("general_chat",), default_rank=60),
    GraphExpertSpec("math_agent", "math_agent", _math_node, aliases=("math",), default_rank=70),
    GraphExpertSpec("code_agent", "code_agent", _code_node, aliases=("code",), default_rank=80),
    GraphExpertSpec("writing_agent", "writing_agent", _writing_node, aliases=("writing",), default_rank=90),
    GraphExpertSpec("science_agent", "science_agent", _science_node, aliases=("science",), default_rank=100),
    GraphExpertSpec("search_agent", "search_agent", _search_node, aliases=("search",), default_rank=110),
)


def get_graph_expert_specs() -> tuple[GraphExpertSpec, ...]:
    return GRAPH_EXPERT_SPECS


def get_graph_routable_targets() -> tuple[str, ...]:
    targets: list[str] = []
    for spec in GRAPH_EXPERT_SPECS:
        targets.append(spec.node_name)
        targets.extend(spec.aliases)
    targets.extend(["human_assist"])
    return tuple(dict.fromkeys(targets))


def resolve_node_name(target: str | None) -> str | None:
    if not target:
        return None
    target_norm = target.strip().lower()
    for spec in GRAPH_EXPERT_SPECS:
        if target_norm == spec.node_name:
            return spec.node_name
        if target_norm == spec.expert_id:
            return spec.node_name
        if target_norm in spec.aliases:
            return spec.node_name
    return None


def get_node_function(target: str | None):
    resolved = resolve_node_name(target)
    if not resolved:
        return None
    for spec in GRAPH_EXPERT_SPECS:
        if spec.node_name == resolved:
            return spec.node_handler
    return None
