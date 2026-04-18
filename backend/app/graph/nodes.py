"""Node and edge abstractions for the Aurora graph runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.aurora.schemas import NodeConfig


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Runtime edge derived from a node configuration."""

    source_node_id: str
    target_node_id: str
    condition: str = "always"
    is_backbone: bool = True
    trigger_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Runtime wrapper around a frozen NodeConfig."""

    config: NodeConfig
    order_index: int = 0

    @classmethod
    def from_config(cls, config: NodeConfig, order_index: int = 0) -> "GraphNode":
        return cls(config=config, order_index=order_index)

    @property
    def node_id(self) -> str:
        return self.config.node_id

    @property
    def neighbors(self) -> tuple[str, ...]:
        return tuple(self.config.neighbors)

    @property
    def default_next_node_id(self) -> str | None:
        if self.config.neighbors:
            return self.config.neighbors[0]
        return None

    def edges(self) -> tuple[GraphEdge, ...]:
        """Return backbone and trigger edges derived from the schema."""

        backbone_edges = [
            GraphEdge(source_node_id=self.node_id, target_node_id=neighbor, is_backbone=True)
            for neighbor in self.config.neighbors
        ]
        trigger_edges = [
            GraphEdge(
                source_node_id=self.node_id,
                target_node_id=target,
                condition=trigger_name,
                is_backbone=False,
                trigger_name=trigger_name,
            )
            for trigger_name, target in self.config.transition_triggers.items()
        ]
        return tuple([*backbone_edges, *trigger_edges])

    def has_neighbor(self, node_id: str) -> bool:
        return node_id in self.config.neighbors
