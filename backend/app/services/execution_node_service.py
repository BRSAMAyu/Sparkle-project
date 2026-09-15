"""Node discovery and selection for OpenClaw Phase 4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.adapters.openclaw.client import OpenClawClient
from app.models.execution_intent import ExecutionIntent, ExecutionTargetEnv


@dataclass(frozen=True)
class ExecutionNode:
    node_id: str
    name: str
    platform: str
    connected: bool
    status: str
    active_runs: int
    last_seen: str | None
    commands: tuple[str, ...]
    caps: tuple[str, ...]
    raw: dict[str, Any]

    def supports(self, command: str | None) -> bool:
        if not command:
            return True
        return command in self.commands or command in self.caps

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "platform": self.platform,
            "connected": self.connected,
            "status": self.status,
            "active_runs": self.active_runs,
            "last_seen": self.last_seen,
            "commands": list(self.commands),
            "caps": list(self.caps),
        }


class ExecutionNodeService:
    """Select and invoke OpenClaw nodes when Gateway WS is available."""

    def __init__(self, client: OpenClawClient | None):
        self._client = client

    async def list_nodes(
        self,
        *,
        connected_only: bool = True,
        last_connected: str | None = None,
    ) -> list[ExecutionNode]:
        if not self._client:
            return []
        payload = await self._client.list_nodes(
            connected_only=connected_only,
            last_connected=last_connected,
        )
        items = payload.get("items") or payload.get("nodes") or payload.get("paired") or []
        nodes: list[ExecutionNode] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            node_id = str(item.get("nodeId") or item.get("id") or "")
            if not node_id:
                continue
            name = str(item.get("name") or item.get("label") or node_id)
            platform = str(item.get("platform") or item.get("os") or "unknown")
            connected = bool(item.get("connected", item.get("isConnected", False)))
            status = str(item.get("status") or ("online" if connected else "offline"))
            active_runs = int(
                item.get("activeRuns")
                or item.get("active_runs")
                or item.get("runningTasks")
                or item.get("running_tasks")
                or 0
            )
            last_seen_raw = item.get("lastSeenAt") or item.get("last_seen_at") or item.get("lastSeen")
            commands = tuple(str(cmd) for cmd in (item.get("commands") or []) if cmd)
            caps = tuple(str(cap) for cap in (item.get("caps") or item.get("capabilities") or []) if cap)
            nodes.append(
                ExecutionNode(
                    node_id=node_id,
                    name=name,
                    platform=platform,
                    connected=connected,
                    status=status,
                    active_runs=active_runs,
                    last_seen=str(last_seen_raw) if last_seen_raw else None,
                    commands=commands,
                    caps=caps,
                    raw=item,
                )
            )
        return nodes

    async def select_node(
        self,
        *,
        intent: ExecutionIntent | None = None,
        preferred_node_id: str | None = None,
        required_command: str | None = None,
        target_env: ExecutionTargetEnv | None = None,
    ) -> ExecutionNode | None:
        nodes = await self.list_nodes(connected_only=True)
        if not nodes:
            return None

        if preferred_node_id:
            for node in nodes:
                if node.node_id == preferred_node_id or node.name == preferred_node_id:
                    if node.supports(required_command):
                        return node
                    raise ValueError(f"Selected node does not support required command: {required_command}")

        if required_command:
            supporting = [node for node in nodes if node.supports(required_command)]
            if supporting:
                return supporting[0]

        if target_env == ExecutionTargetEnv.SHELL:
            for node in nodes:
                if node.supports("system.run"):
                    return node

        if intent:
            requested_platform = str((intent.policy or {}).get("target_platform") or "").lower()
            if requested_platform:
                for node in nodes:
                    if node.platform.lower() == requested_platform:
                        return node

        return nodes[0]

    def build_policy_patch(
        self,
        *,
        node: ExecutionNode,
        required_command: str | None = None,
    ) -> dict[str, Any]:
        return {
            "target_node_id": node.node_id,
            "target_node_label": node.name,
            "target_node_platform": node.platform,
            "target_node_command": required_command,
            "target_node_caps": list(node.caps),
            "target_node_commands": list(node.commands),
        }

    async def invoke_node(
        self,
        *,
        node_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        invoke_timeout_ms: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not self._client:
            raise ValueError("Node invocation requires OpenClaw Gateway WS transport")
        return await self._client.invoke_node(
            node_id=node_id,
            command=command,
            params=params or {},
            invoke_timeout_ms=invoke_timeout_ms,
            idempotency_key=idempotency_key,
        )
