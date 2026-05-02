"""
Core: execution
Phase: plan→adapt
Stage: Signal-to-Action Spine P3-1 GoalWorldGraph — generalized node types

Per ruling Section 13: upgrade Knowledge Star Map to general GoalWorldGraph.
10 node types: Knowledge, Capability, Artifact, Milestone, Habit,
Risk, Constraint, Resource, Feedback, Relationship.

Each goal_type gets its own node_schema via DomainPack.
Exam Sprint backward-compatible — defaults to KnowledgeNode.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import select

from app.signals.types import _uid

_GRAPH_KEY = "spine:goal_graph:{user_id}:{goal_id}"
_GRAPH_TTL = 90 * 24 * 3600  # 90 days

# P3-1: Generalized node types per ruling
NODE_TYPES = frozenset({
    "knowledge",    # 知识点 (default for exam_sprint)
    "capability",   # 能力
    "artifact",     # 交付物
    "milestone",    # 里程碑
    "habit",        # 习惯
    "risk",         # 风险
    "constraint",   # 限制
    "resource",     # 资源
    "feedback",     # 反馈来源
    "relationship", # 伙伴/导师/协作者
})

# Node types that track mastery (0-1 progress)
_MASTERY_TRACKED_TYPES = frozenset({"knowledge", "capability", "habit"})
# Node types that are binary (done/not-done)
_BINARY_TYPES = frozenset({"artifact", "milestone", "resource"})
# Node types that are informational (no mastery)
_INFORMATIONAL_TYPES = frozenset({"risk", "constraint", "feedback", "relationship"})


@dataclass
class GraphNode:
    node_id: str
    label: str
    node_type: str = "knowledge"  # P3-1: one of NODE_TYPES
    mastery: float = 0.0  # 0-1 (meaningful for _MASTERY_TRACKED_TYPES)
    dependency_ids: list[str] = field(default_factory=list)
    status: str = "pending"  # "pending" | "in_progress" | "mastered" | "blocked" | "done"
    metadata: dict[str, Any] = field(default_factory=dict)
    # KG-001: Extended node attributes
    exam_weight: float = 0.0  # 考试权重 0-1 (how important for exam)
    difficulty: float = 0.5  # 难度 0-1
    trainability: float = 0.5  # 可训练性 0-1 (how responsive to practice)
    mistakes: int = 0  # 累计错误次数
    # KG-004: Persisted focus priority
    focus_priority: float = 0.0  # 运行时计算后持久化的优先级

    @property
    def tracks_mastery(self) -> bool:
        return self.node_type in _MASTERY_TRACKED_TYPES

    @property
    def is_binary(self) -> bool:
        return self.node_type in _BINARY_TYPES

    @property
    def is_informational(self) -> bool:
        return self.node_type in _INFORMATIONAL_TYPES

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "node_type": self.node_type,
            "mastery": self.mastery,
            "dependency_ids": self.dependency_ids,
            "status": self.status,
            "metadata": self.metadata,
            "exam_weight": self.exam_weight,
            "difficulty": self.difficulty,
            "trainability": self.trainability,
            "mistakes": self.mistakes,
            "focus_priority": self.focus_priority,
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

    def __init__(self, redis_client: Any, db_session: Any | None = None):
        self.redis = redis_client
        self.db = db_session

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
        if raw:
            return GoalWorldGraph.from_dict(json.loads(raw if isinstance(raw, str) else raw.decode()))
        graph = await self._load_durable(user_id, goal_id)
        if graph is not None:
            await self.redis.set(key, json.dumps(graph.to_dict()), ex=_GRAPH_TTL)
        return graph

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
                mastery = max(0.0, min(1.0, mastery))
                if node.is_binary:
                    # Binary nodes: mastery >= 0.5 means done
                    node.mastery = 1.0 if mastery >= 0.5 else 0.0
                    node.status = "done" if mastery >= 0.5 else "pending"
                elif node.tracks_mastery:
                    node.mastery = mastery
                    if mastery >= 0.8:
                        node.status = "mastered"
                    elif mastery > 0.0:
                        node.status = "in_progress"
                else:
                    node.mastery = mastery
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
        """Find the node that blocks the most other nodes and isn't completed."""
        blocked_by: dict[str, int] = {}
        node_map = {n.node_id: n for n in graph.nodes}

        for node in graph.nodes:
            if node.status in ("mastered", "done"):
                continue
            for dep_id in node.dependency_ids:
                dep = node_map.get(dep_id)
                if dep and dep.status not in ("mastered", "done"):
                    blocked_by[dep_id] = blocked_by.get(dep_id, 0) + 1

        if not blocked_by:
            return None

        bottleneck_id = max(blocked_by, key=blocked_by.get)
        return node_map.get(bottleneck_id)

    def suggest_focus_nodes(self, graph: GoalWorldGraph, limit: int = 3) -> list[dict[str, Any]]:
        """Suggest which nodes the user should focus on next.

        Priority: bottleneck > unblocked in-progress > unblocked pending.
        """
        completed_ids = {
            n.node_id for n in graph.nodes
            if n.status in ("mastered", "done")
        }
        {n.node_id: n for n in graph.nodes}
        suggestions: list[dict[str, Any]] = []

        # 1. Bottleneck first
        bottleneck = self.find_bottleneck(graph)
        if bottleneck:
            suggestions.append({
                "node_id": bottleneck.node_id,
                "label": bottleneck.label,
                "node_type": bottleneck.node_type,
                "reason": "bottleneck",
                "blocks_count": sum(
                    1 for n in graph.nodes
                    if bottleneck.node_id in n.dependency_ids and n.status not in ("mastered", "done")
                ),
            })

        # 2. Unblocked nodes (all deps completed), by mastery (lowest first)
        unblocked = []
        for node in graph.nodes:
            if node.status in ("mastered", "done"):
                continue
            if suggestions and node.node_id == suggestions[0]["node_id"]:
                continue
            deps_ok = all(d in completed_ids for d in node.dependency_ids)
            if deps_ok:
                unblocked.append(node)

        unblocked.sort(key=lambda n: n.mastery)
        for node in unblocked[:limit - len(suggestions)]:
            suggestions.append({
                "node_id": node.node_id,
                "label": node.label,
                "node_type": node.node_type,
                "reason": "ready_to_advance" if node.mastery > 0 else "ready_to_start",
                "current_mastery": round(node.mastery, 2),
            })

        return suggestions[:limit]

    def _recompute(self, graph: GoalWorldGraph) -> None:
        """Recompute derived fields: coverage, bottleneck, blocked status."""
        completed = [
            n for n in graph.nodes
            if n.status in ("mastered", "done")
        ]
        completed_ids = {n.node_id for n in completed}
        graph.coverage = round(len(completed) / max(len(graph.nodes), 1), 3)

        # Mark nodes as blocked if they have unmet deps, or unblock if deps resolved
        for node in graph.nodes:
            if node.status in ("mastered", "done"):
                continue
            unmet = [d for d in node.dependency_ids if d not in completed_ids]
            if unmet:
                if node.status not in ("in_progress",):
                    node.status = "blocked"
            elif node.status == "blocked":
                node.status = "pending"

        graph.bottleneck_node_id = None
        bn = self.find_bottleneck(graph)
        if bn:
            graph.bottleneck_node_id = bn.node_id

        # KG-004: Persist computed focus priorities on nodes
        suggestions = self.suggest_focus_nodes(graph, limit=len(graph.nodes))
        for i, sug in enumerate(suggestions):
            node_id = sug["node_id"]
            for node in graph.nodes:
                if node.node_id == node_id:
                    node.focus_priority = round(1.0 - (i * 0.1), 2)
                    break

    async def _save(self, graph: GoalWorldGraph) -> None:
        key = _GRAPH_KEY.format(user_id=graph.user_id, goal_id=graph.goal_id)
        await self.redis.set(key, json.dumps(graph.to_dict()), ex=_GRAPH_TTL)
        await self._save_durable(graph)

    async def _save_durable(self, graph: GoalWorldGraph) -> None:
        if self.db is None:
            return
        try:
            from app.aurora.runtime_v1.models import GoalWorldGraphSnapshot

            result = await self.db.execute(
                select(GoalWorldGraphSnapshot).where(
                    GoalWorldGraphSnapshot.user_id == graph.user_id,
                    GoalWorldGraphSnapshot.goal_id == graph.goal_id,
                    GoalWorldGraphSnapshot.deleted_at.is_(None),
                )
            )
            record = result.scalar_one_or_none()
            if record is None:
                record = GoalWorldGraphSnapshot(user_id=graph.user_id, goal_id=graph.goal_id)
            record.graph_id = graph.graph_id
            record.goal_type = graph.goal_type
            record.coverage = graph.coverage
            record.payload = graph.to_dict()
            record.last_saved_at = datetime.now(UTC).replace(tzinfo=None)
            record.runtime_metadata = {
                "source": "goal_world_graph_service",
                "node_count": len(graph.nodes),
                "bottleneck_node_id": graph.bottleneck_node_id,
            }
            self.db.add(record)
            await self.db.commit()
        except Exception as exc:
            logger.warning("GoalWorldGraph durable save skipped user={} goal={}: {}", graph.user_id, graph.goal_id, exc)

    async def _load_durable(self, user_id: str, goal_id: str) -> GoalWorldGraph | None:
        if self.db is None:
            return None
        try:
            from app.aurora.runtime_v1.models import GoalWorldGraphSnapshot

            result = await self.db.execute(
                select(GoalWorldGraphSnapshot)
                .where(
                    GoalWorldGraphSnapshot.user_id == user_id,
                    GoalWorldGraphSnapshot.goal_id == goal_id,
                    GoalWorldGraphSnapshot.deleted_at.is_(None),
                )
                .order_by(GoalWorldGraphSnapshot.last_saved_at.desc())
                .limit(1)
            )
            record = result.scalar_one_or_none()
            if record is None or not isinstance(record.payload, dict):
                return None
            return GoalWorldGraph.from_dict(record.payload)
        except Exception as exc:
            logger.warning("GoalWorldGraph durable load skipped user={} goal={}: {}", user_id, goal_id, exc)
            return None

    # GOAL-006: Deferred nodes with explainable reasons

    def get_deferred_nodes(
        self,
        graph: GoalWorldGraph,
        *,
        focus_ids: set[str] | None = None,
        high_mastery_threshold: float = 0.8,
    ) -> list[dict[str, Any]]:
        focus_ids = focus_ids or set()
        deferred: list[dict[str, Any]] = []

        for node in graph.nodes:
            if node.node_id in focus_ids:
                continue
            if node.status in ("mastered", "done"):
                continue

            why = None
            if node.status == "blocked":
                why = f"「{node.label}」被阻塞 — 依赖项尚未完成"
            elif node.mastery >= high_mastery_threshold:
                why = f"「{node.label}」掌握度已高（{node.mastery:.0%}），优先级降低"
            elif node.status == "pending" and node.dependency_ids:
                unmet = list(node.dependency_ids)
                why = f"「{node.label}」等待 {len(unmet)} 个前置节点"

            if why:
                deferred.append({
                    "node_id": node.node_id,
                    "label": node.label,
                    "status": node.status,
                    "mastery": node.mastery,
                    "why_deferred": why,
                })

        return deferred
