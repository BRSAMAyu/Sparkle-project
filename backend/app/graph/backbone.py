"""Backbone path resolution for the Aurora graph runtime."""

from __future__ import annotations

from dataclasses import dataclass

from app.aurora.schemas import ScenarioPackManifest
from app.graph.nodes import GraphNode


@dataclass(frozen=True, slots=True)
class BackboneResolution:
    """Resolved path step for a node."""

    current_node_id: str
    next_node_id: str | None
    is_terminal: bool


class BackbonePathResolver:
    """Resolve the default day-to-day path through a scenario pack backbone."""

    def __init__(self, manifest: ScenarioPackManifest) -> None:
        self._manifest = manifest
        self._nodes = tuple(GraphNode.from_config(config, order_index=index) for index, config in enumerate(manifest.backbone_nodes))
        self._node_by_id = {node.node_id: node for node in self._nodes}
        if len(self._node_by_id) != len(self._nodes):
            raise ValueError("Scenario pack backbone contains duplicate node ids")

    @property
    def manifest(self) -> ScenarioPackManifest:
        return self._manifest

    @property
    def backbone_node_ids(self) -> tuple[str, ...]:
        return tuple(node.node_id for node in self._nodes)

    def get_node(self, node_id: str) -> GraphNode:
        return self._node_by_id[node_id]

    def has_node(self, node_id: str) -> bool:
        return node_id in self._node_by_id

    def is_backbone_transition(self, current_node_id: str, target_node_id: str) -> bool:
        current_node = self.get_node(current_node_id)
        return current_node.default_next_node_id == target_node_id or current_node.has_neighbor(target_node_id)

    def resolve_next_node(self, current_node_id: str) -> str | None:
        node = self.get_node(current_node_id)
        if node.default_next_node_id is not None:
            return node.default_next_node_id

        next_index = node.order_index + 1
        if next_index < len(self._nodes):
            return self._nodes[next_index].node_id
        return None

    def resolve(self, current_node_id: str) -> BackboneResolution:
        next_node_id = self.resolve_next_node(current_node_id)
        return BackboneResolution(
            current_node_id=current_node_id,
            next_node_id=next_node_id,
            is_terminal=next_node_id is None,
        )

    def resolve_path(self, start_node_id: str, steps: int) -> list[str]:
        path = [start_node_id]
        current_node_id = start_node_id
        for _ in range(max(steps, 0)):
            next_node_id = self.resolve_next_node(current_node_id)
            if next_node_id is None:
                break
            path.append(next_node_id)
            current_node_id = next_node_id
        return path
