from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
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
from app.core.agent_capability_registry import get_expert_capability_catalog


@dataclass(frozen=True)
class GraphExpertSpec:
    expert_id: str
    node_name: str
    node_handler: Callable[[SparkleState], dict]
    aliases: tuple[str, ...] = ()
    default_rank: int = 100
    supports_collaboration: bool = True


_ALIASES: dict[str, tuple[str, ...]] = {
    "galaxy_guide": ("knowledge_agent",),
    "study_buddy": ("general_chat",),
    "math_agent": ("math",),
    "code_agent": ("code",),
    "writing_agent": ("writing",),
    "science_agent": ("science",),
    "search_agent": ("search",),
}


_SPECIALIZED_NODES: dict[str, Callable[[SparkleState], dict]] = {
    "galaxy_guide": galaxy_guide_node,
    "exam_oracle": exam_oracle_node,
    "time_tutor": time_tutor_node,
    "deep_analyst": deep_analyst_node,
    "error_analyst": error_analyst_node,
    "study_buddy": study_buddy_node,
}


_GENERIC_TOOLSET_BY_EXPERT: dict[str, list] = {
    "search_agent": [query_knowledge],
    "writing_agent": [create_task],
}


def _build_generic_node(expert_id: str) -> Callable[[SparkleState], dict]:
    toolset = _GENERIC_TOOLSET_BY_EXPERT.get(expert_id, [query_knowledge, create_task])
    return create_specialist_node(
        agent_id=expert_id,
        planning_prompt=(
            f"You are in planning-only mode as {expert_id}. Use tools when needed and "
            "produce concise, executable outputs."
        ),
        task_prompt_prefix=f"{expert_id} context",
        toolset=toolset,
    )


@lru_cache(maxsize=1)
def get_graph_expert_specs() -> tuple[GraphExpertSpec, ...]:
    specs: list[GraphExpertSpec] = []
    for expert in get_expert_capability_catalog():
        if not expert.get("enabled", False):
            continue
        expert_id = str(expert["id"])
        node_handler = _SPECIALIZED_NODES.get(expert_id) or _build_generic_node(expert_id)
        specs.append(
            GraphExpertSpec(
                expert_id=expert_id,
                node_name=expert_id,
                node_handler=node_handler,
                aliases=_ALIASES.get(expert_id, ()),
                default_rank=int(expert.get("rank", 100)),
                supports_collaboration=True,
            )
        )

    # Keep a safe fallback when all public experts are disabled.
    if not specs:
        specs.append(
            GraphExpertSpec(
                expert_id="study_buddy",
                node_name="study_buddy",
                node_handler=study_buddy_node,
                aliases=_ALIASES.get("study_buddy", ()),
                default_rank=999,
            )
        )

    specs.sort(key=lambda item: item.default_rank)
    return tuple(specs)


def get_graph_routable_targets() -> tuple[str, ...]:
    targets: list[str] = []
    for spec in get_graph_expert_specs():
        targets.append(spec.node_name)
        targets.extend(spec.aliases)
    targets.append("human_assist")
    return tuple(dict.fromkeys(targets))


def resolve_node_name(target: str | None) -> str | None:
    if not target:
        return None
    target_norm = target.strip().lower()
    for spec in get_graph_expert_specs():
        if target_norm in (spec.node_name, spec.expert_id):
            return spec.node_name
        if target_norm in spec.aliases:
            return spec.node_name
    return None


def reset_graph_expert_registry_cache() -> None:
    get_graph_expert_specs.cache_clear()
