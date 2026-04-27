"""
Core: execution
Phase: plan→adapt
Stage: v2.5 Goal World Graph — per-goal dependency and prerequisite tracking

Lightweight graph structure for tracking prerequisite relationships between
knowledge nodes within a goal scope. Identifies bottlenecks and suggests
focus areas based on dependency coverage.

NOT a replacement for the full Galaxy knowledge graph. This is goal-scoped
and optimized for sprint-level planning decisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.signals.types import _uid


_GRAPH_KEY = "spine:goal_graph:{user_id}:{goal_id}"
_GRAPH_TTL = 90 * 24 * 3600  # 90 days


@dataclass
class GraphNode:
    node_id: str
    label: str
    mastery: float = 0.0  # 0-1
    dependency_ids: list[str] = field(default_factory=list)
    status: str = "pending"  # "pending" | "in_progress" | "mastered" | "blocked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "mastery": self.mastery,
            "dependency_ids": self.dependency_ids,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GraphNode:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class GoalWorldGraph:
    graph_id: str
    user_id: str
    goal_id: str
    goal_type: str
    nodes: list[GraphNode] = field(default_factory=list)
    bottleneck_node_id: str | None = None
    coverage: float = 0.0  # % of nodes mastered

    def to_dict(self) -> dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "user_id": self.user_id,
            "goal_id": self.goal_id,
            "goal_type": self.goal_type,
            "nodes": [n.to_dict() for n in self.nodes],
            "bottleneck_node_id": self.bottleneck_node_id,
            "coverage": self.coverage,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GoalWorldGraph:
        nodes = [GraphNode.from_dict(n) for n in d.get("nodes", [])]
        return cls(
            graph_id=d.get("graph_id", ""),
            user_id=d.get("user_id", ""),
            goal_id=d.get("goal_id", ""),
            goal_type=d.get("goal_type", "general"),
            nodes=nodes,
            bottleneck_node_id=d.get("bottleneck_node_id"),
            coverage=d.get("coverage", 0.0),
        )


class GoalWorldGraphService:
    """Manage per-goal dependency graphs for the Signal Spine."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def create_graph(
        self,
        *,
        user_id: str,
        goal_id: str,
        goal_type: str,
        node_specs: list[dict[str, Any]],
    ) -> GoalWorldGraph:
        graph = GoalWorldGraph(
            graph_id=_uid("gwg"),
            user_id=user_id,
            goal_id=goal_id,
            goal_type=goal_type,
            nodes=[GraphNode(**spec) for spec in node_specs],
        )
        self._recompute(graph)
        await self._save(graph)
        return graph

    async def get_graph(self, user_id: str, goal_id: str) -> GoalWorldGraph | None:
        key = _GRAPH_KEY.format(user_id=user_id, goal_id=goal_id)
        raw = await self.redis.get(key)
        if not raw:
            return None
        return GoalWorldGraph.from_dict(json.loads(raw if isinstance(raw, str) else raw.decode()))

    async def update_node_mastery(
        self,
        user_id: str,
        goal_id: str,
        node_id: str,
        mastery: float,
    ) -> GoalWorldGraph | None:
        graph = await self.get_graph(user_id, goal_id)
        if not graph:
            return None

        for node in graph.nodes:
            if node.node_id == node_id:
                node.mastery = max(0.0, min(1.0, mastery))
                if mastery >= 0.8:
                    node.status = "mastered"
                elif mastery > 0.0:
                    node.status = "in_progress"
                break

        self._recompute(graph)
        await self._save(graph)
        return graph

    async def add_dependency(
        self,
        user_id: str,
        goal_id: str,
        node_id: str,
        depends_on_id: str,
    ) -> GoalWorldGraph | None:
        graph = await self.get_graph(user_id, goal_id)
        if not graph:
            return None

        for node in graph.nodes:
            if node.node_id == node_id and depends_on_id not in node.dependency_ids:
                node.dependency_ids.append(depends_on_id)
                break

        self._recompute(graph)
        await self._save(graph)
        return graph

    def find_bottleneck(self, graph: GoalWorldGraph) -> GraphNode | None:
        """Find the node that blocks the most other nodes and isn't mastered."""
        blocked_by: dict[str, int] = {}
        node_map = {n.node_id: n for n in graph.nodes}

        for node in graph.nodes:
            if node.status == "mastered":
                continue
            for dep_id in node.dependency_ids:
                dep = node_map.get(dep_id)
                if dep and dep.status != "mastered":
                    blocked_by[dep_id] = blocked_by.get(dep_id, 0) + 1

        if not blocked_by:
            return None

        bottleneck_id = max(blocked_by, key=blocked_by.get)
        return node_map.get(bottleneck_id)

    def suggest_focus_nodes(self, graph: GoalWorldGraph, limit: int = 3) -> list[dict[str, Any]]:
        """Suggest which nodes the user should focus on next.

        Priority: bottleneck > unblocked in-progress > unblocked pending.
        """
        mastered_ids = {n.node_id for n in graph.nodes if n.status == "mastered"}
        node_map = {n.node_id: n for n in graph.nodes}
        suggestions: list[dict[str, Any]] = []

        # 1. Bottleneck first
        bottleneck = self.find_bottleneck(graph)
        if bottleneck:
            suggestions.append({
                "node_id": bottleneck.node_id,
                "label": bottleneck.label,
                "reason": "bottleneck",
                "blocks_count": sum(
                    1 for n in graph.nodes
                    if bottleneck.node_id in n.dependency_ids and n.status != "mastered"
                ),
            })

        # 2. Unblocked nodes (all deps mastered), by mastery (lowest first)
        unblocked = []
        for node in graph.nodes:
            if node.status == "mastered":
                continue
            if suggestions and node.node_id == suggestions[0]["node_id"]:
                continue
            deps_ok = all(d in mastered_ids for d in node.dependency_ids)
            if deps_ok:
                unblocked.append(node)

        unblocked.sort(key=lambda n: n.mastery)
        for node in unblocked[:limit - len(suggestions)]:
            suggestions.append({
                "node_id": node.node_id,
                "label": node.label,
                "reason": "ready_to_advance" if node.mastery > 0 else "ready_to_start",
                "current_mastery": round(node.mastery, 2),
            })

        return suggestions[:limit]

    def _recompute(self, graph: GoalWorldGraph) -> None:
        """Recompute derived fields: coverage, bottleneck, blocked status."""
        mastered = [n for n in graph.nodes if n.status == "mastered"]
        mastered_ids = {n.node_id for n in mastered}
        graph.coverage = round(len(mastered) / max(len(graph.nodes), 1), 3)

        # Mark nodes as blocked if they have unmet deps
        for node in graph.nodes:
            if node.status == "mastered":
                continue
            unmet = [d for d in node.dependency_ids if d not in mastered_ids]
            if unmet and node.status not in ("in_progress",):
                node.status = "blocked"

        graph.bottleneck_node_id = None
        bn = self.find_bottleneck(graph)
        if bn:
            graph.bottleneck_node_id = bn.node_id

    async def _save(self, graph: GoalWorldGraph) -> None:
        key = _GRAPH_KEY.format(user_id=graph.user_id, goal_id=graph.goal_id)
        await self.redis.set(key, json.dumps(graph.to_dict()), ex=_GRAPH_TTL)
