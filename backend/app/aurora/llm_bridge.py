"""LLM bridge for Aurora hybrid decisions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.aurora.config import DEFAULT_AURORA_CONFIG


@dataclass(frozen=True)
class LLMBridgeRequest:
    """Structured request that may be forwarded to an LLM in hybrid mode."""

    trigger_point: str
    snapshot_ref: str
    prompt_facts: dict[str, Any]


class AuroraLLMBridge:
    """Thin, inert bridge that can be injected with a provider client later."""

    def __init__(self, client: Callable[[LLMBridgeRequest], Awaitable[dict[str, Any]]] | None = None) -> None:
        self._client = client

    async def maybe_request(self, request: LLMBridgeRequest) -> dict[str, Any] | None:
        if not DEFAULT_AURORA_CONFIG.active or self._client is None:
            return None
        return await self._client(request)

