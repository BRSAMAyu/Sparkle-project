"""Stage 4 Aurora execution context and tier-sidecar helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Generic, TypeVar

from app.aurora.config import DEFAULT_AURORA_CONFIG
from app.aurora.schemas import AuroraPolicyVersion, SignalSnapshot


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class AuroraTier(StrEnum):
    """Internal Stage 4 time-tier tags."""

    INLINE = "inline"
    NEARLINE = "nearline"
    LONG_HORIZON = "long_horizon"


class AuroraTierStatus(StrEnum):
    """Execution status for tier-local work."""

    SUCCESS = "success"
    MISS = "miss"
    FAILURE = "failure"


@dataclass(frozen=True)
class AuroraAsyncFlags:
    """Stage 4 async-substrate flags.

    These remain local sidecar flags during Wave 1a so flags-off behavior keeps
    the Stage 3 runtime unchanged.
    """

    async_substrate_enabled: bool = field(default_factory=lambda: _env_flag("AURORA_ASYNC_SUBSTRATE_ENABLED", False))
    nearline_enabled: bool = field(default_factory=lambda: _env_flag("AURORA_NEARLINE_ENABLED", False))
    long_horizon_enabled: bool = field(default_factory=lambda: _env_flag("AURORA_LONG_HORIZON_ENABLED", False))
    inline_benchmark_enabled: bool = field(default_factory=lambda: _env_flag("AURORA_INLINE_BENCHMARK_ENABLED", False))
    nearline_queue: str = field(default_factory=lambda: os.getenv("AURORA_NEARLINE_QUEUE", "default"))
    long_horizon_queue: str = field(default_factory=lambda: os.getenv("AURORA_LONG_HORIZON_QUEUE", "low_priority"))

    @property
    def any_enabled(self) -> bool:
        return any(
            [
                self.async_substrate_enabled,
                self.nearline_enabled,
                self.long_horizon_enabled,
                self.inline_benchmark_enabled,
            ]
        )

    def enabled_for(self, tier: AuroraTier) -> bool:
        if tier == AuroraTier.INLINE:
            return self.async_substrate_enabled
        if tier == AuroraTier.NEARLINE:
            return self.async_substrate_enabled and self.nearline_enabled
        if tier == AuroraTier.LONG_HORIZON:
            return self.async_substrate_enabled and self.long_horizon_enabled
        return False


@dataclass(frozen=True)
class AuroraDecisionContext:
    """Input bundle for Aurora routing helpers."""

    snapshot: SignalSnapshot | None
    trigger_point: str
    current_node: str
    policy_version: AuroraPolicyVersion | None = None
    candidate_node: str | None = None
    mode: str = field(default_factory=lambda: DEFAULT_AURORA_CONFIG.mode)
    prior_outputs: dict[str, Any] = field(default_factory=dict)
    tier: AuroraTier = AuroraTier.INLINE
    async_flags: AuroraAsyncFlags = field(default_factory=AuroraAsyncFlags)
    benchmark_case_id: str | None = None

    def with_tier(self, tier: AuroraTier) -> AuroraDecisionContext:
        return replace(self, tier=tier)

    def with_benchmark_case(self, case_id: str | None) -> AuroraDecisionContext:
        return replace(self, benchmark_case_id=case_id)

    def to_payload(self) -> dict[str, Any]:
        return {
            "snapshot": None if self.snapshot is None else self.snapshot.model_dump(mode="json"),
            "trigger_point": self.trigger_point,
            "current_node": self.current_node,
            "policy_version": None if self.policy_version is None else self.policy_version.model_dump(mode="json"),
            "candidate_node": self.candidate_node,
            "mode": self.mode,
            "prior_outputs": self.prior_outputs,
            "tier": self.tier.value,
            "benchmark_case_id": self.benchmark_case_id,
        }

    @classmethod
    def from_payload(
        cls,
        payload: dict[str, Any],
        *,
        async_flags: AuroraAsyncFlags | None = None,
    ) -> AuroraDecisionContext:
        snapshot_payload = payload.get("snapshot")
        policy_payload = payload.get("policy_version")
        return cls(
            snapshot=None if snapshot_payload is None else SignalSnapshot.model_validate(snapshot_payload),
            trigger_point=str(payload["trigger_point"]),
            current_node=str(payload["current_node"]),
            policy_version=None if policy_payload is None else AuroraPolicyVersion.model_validate(policy_payload),
            candidate_node=payload.get("candidate_node"),
            mode=str(payload.get("mode", "disabled")),
            prior_outputs=dict(payload.get("prior_outputs") or {}),
            tier=AuroraTier(str(payload.get("tier", AuroraTier.INLINE.value))),
            async_flags=async_flags or AuroraAsyncFlags(),
            benchmark_case_id=payload.get("benchmark_case_id"),
        )


PayloadT = TypeVar("PayloadT")


@dataclass(frozen=True)
class AuroraTierExecution(Generic[PayloadT]):
    """Tier-local execution result with miss/failure semantics."""

    tier: AuroraTier
    status: AuroraTierStatus
    trigger_point: str
    payload: PayloadT | None = None
    reason: str | None = None
    task_name: str | None = None
    task_id: str | None = None
    duration_ms: float | None = None
    error: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "tier": self.tier.value,
            "status": self.status.value,
            "trigger_point": self.trigger_point,
            "payload": self.payload,
            "reason": self.reason,
            "task_name": self.task_name,
            "task_id": self.task_id,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }
