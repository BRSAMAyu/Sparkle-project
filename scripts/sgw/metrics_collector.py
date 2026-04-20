from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


@dataclass
class MetricsCollector:
    started_at: str = field(default_factory=utcnow_iso)
    peak_concurrency: int = 0
    current_claude_parallel: int = 0
    peak_claude_parallel: int = 0
    sessions_planned: int = 0
    sessions_completed: int = 0
    turns_completed: int = 0
    websocket_sessions: int = 0
    websocket_failures: int = 0
    audit_cases: int = 0
    audit_soft_violations: int = 0
    revoke_attempts: int = 0
    revoke_verified: int = 0
    rate_limit_events: int = 0
    quota_exhaustion_events: int = 0
    checkpoint_writes: int = 0
    resume_count: int = 0
    worker_restarts: int = 0
    db_pool_exhausted_events: int = 0
    db_pool_peak_in_use: int = 0
    queue_peak_depth: int = 0
    persona_sessions_completed: dict[str, int] = field(default_factory=dict)
    session_role_completed: dict[str, int] = field(default_factory=dict)
    hard_violations: list[dict[str, Any]] = field(default_factory=list)
    soft_violation_reasons: list[str] = field(default_factory=list)
    quota_cooldowns: list[dict[str, Any]] = field(default_factory=list)
    concurrency_adjustments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MetricsCollector":
        return cls(**payload)

    def observe_concurrency(self, current: int) -> None:
        self.peak_concurrency = max(self.peak_concurrency, current)

    def observe_claude_parallel(self, current: int) -> None:
        self.current_claude_parallel = current
        self.peak_claude_parallel = max(self.peak_claude_parallel, current)

    def observe_queue_depth(self, current: int) -> None:
        self.queue_peak_depth = max(self.queue_peak_depth, current)

    def record_session_planned(self) -> None:
        self.sessions_planned += 1

    def record_session_completed(self, role: str, persona_id: str | None) -> None:
        self.sessions_completed += 1
        self.session_role_completed[role] = self.session_role_completed.get(role, 0) + 1
        if persona_id:
            self.persona_sessions_completed[persona_id] = self.persona_sessions_completed.get(persona_id, 0) + 1

    def record_turn(self) -> None:
        self.turns_completed += 1

    def record_websocket_success(self) -> None:
        self.websocket_sessions += 1

    def record_websocket_failure(self) -> None:
        self.websocket_failures += 1

    def record_audit(self, soft_violation: bool, reason: str) -> None:
        self.audit_cases += 1
        if soft_violation:
            self.audit_soft_violations += 1
            self.soft_violation_reasons.append(reason)

    def record_revoke(self, verified: bool) -> None:
        self.revoke_attempts += 1
        if verified:
            self.revoke_verified += 1

    def record_rate_limit(self) -> None:
        self.rate_limit_events += 1

    def record_quota_exhaustion(self, cooldown_until: str, reason: str) -> None:
        self.quota_exhaustion_events += 1
        self.quota_cooldowns.append({"cooldown_until": cooldown_until, "reason": reason})

    def record_concurrency_adjustment(self, *, before: int, after: int, reason: str) -> None:
        self.current_claude_parallel = after
        self.peak_claude_parallel = max(self.peak_claude_parallel, after)
        self.concurrency_adjustments.append(
            {
                "at": utcnow_iso(),
                "before": before,
                "after": after,
                "reason": reason,
            }
        )

    def record_checkpoint(self) -> None:
        self.checkpoint_writes += 1

    def record_resume(self) -> None:
        self.resume_count += 1

    def record_worker_restart(self) -> None:
        self.worker_restarts += 1

    def record_db_pool_peak(self, in_use: int) -> None:
        self.db_pool_peak_in_use = max(self.db_pool_peak_in_use, in_use)

    def record_db_pool_exhausted(self) -> None:
        self.db_pool_exhausted_events += 1

    def record_hard_violation(self, payload: dict[str, Any]) -> None:
        self.hard_violations.append(payload)

    def soft_violation_rate(self) -> float:
        if self.audit_cases == 0:
            return 0.0
        return self.audit_soft_violations / self.audit_cases

    def to_markdown(self, *, wall_clock_hours: float, acceptance: dict[str, bool]) -> str:
        hard_count = len(self.hard_violations)
        lines = [
            "# SPARKLE Aurora Stage 16 SGW Report",
            "",
            f"- Context: `Pre-launch`",
            f"- Started At: `{self.started_at}`",
            f"- Wall-Clock Runtime (hours): `{wall_clock_hours:.2f}`",
            f"- Sessions Planned: `{self.sessions_planned}`",
            f"- Sessions Completed: `{self.sessions_completed}`",
            f"- Turns Completed: `{self.turns_completed}`",
            f"- Peak Concurrency: `{self.peak_concurrency}`",
            f"- Current Claude Parallelism: `{self.current_claude_parallel}`",
            f"- Peak Claude Parallelism: `{self.peak_claude_parallel}`",
            f"- WebSocket Success Count: `{self.websocket_sessions}`",
            f"- WebSocket Failure Count: `{self.websocket_failures}`",
            f"- Audit Cases: `{self.audit_cases}`",
            f"- Soft Violation Rate: `{self.soft_violation_rate():.4f}`",
            f"- Hard Violation Count: `{hard_count}`",
            "",
            "## Acceptance",
            "",
        ]
        for key, passed in acceptance.items():
            lines.append(f"- {key}: `{'PASS' if passed else 'FAIL'}`")
        lines.extend(
            [
                "",
                "## Revoke And Recovery",
                "",
                f"- Revoke Attempts: `{self.revoke_attempts}`",
                f"- Revoke Verified: `{self.revoke_verified}`",
                f"- Checkpoint Writes: `{self.checkpoint_writes}`",
                f"- Resume Count: `{self.resume_count}`",
                f"- Worker Restarts: `{self.worker_restarts}`",
                f"- Claude Rate Limit Events: `{self.rate_limit_events}`",
                f"- Claude Quota Exhaustion Events: `{self.quota_exhaustion_events}`",
                "",
                "## Concurrency Tuning",
                "",
            ]
        )
        if not self.concurrency_adjustments:
            lines.append("- None")
        else:
            for item in self.concurrency_adjustments[-50:]:
                lines.append(
                    f"- `{item['at']}` `{item['before']} -> {item['after']}` :: {item['reason']}"
                )
        lines.extend(
            [
                "",
                "## Infra",
                "",
                f"- DB Pool Peak In Use: `{self.db_pool_peak_in_use}`",
                f"- DB Pool Exhausted Events: `{self.db_pool_exhausted_events}`",
                f"- Queue Peak Depth: `{self.queue_peak_depth}`",
                "",
                "## Role Completion",
                "",
            ]
        )
        for role, count in sorted(self.session_role_completed.items()):
            lines.append(f"- {role}: `{count}`")
        lines.extend(["", "## Persona Coverage", ""])
        for persona_id, count in sorted(self.persona_sessions_completed.items()):
            lines.append(f"- {persona_id}: `{count}`")
        lines.extend(["", "## Hard Violations", ""])
        if hard_count == 0:
            lines.append("- None")
        else:
            for violation in self.hard_violations:
                lines.append(
                    f"- `{violation.get('code', 'UNKNOWN')}` {violation.get('message', '')} :: "
                    f"{violation.get('context', '')}"
                )
        lines.extend(["", "## Soft Violation Reasons", ""])
        if not self.soft_violation_reasons:
            lines.append("- None")
        else:
            for reason in self.soft_violation_reasons[:50]:
                lines.append(f"- {reason}")
        lines.extend(["", "## Quota Cooldowns", ""])
        if not self.quota_cooldowns:
            lines.append("- None")
        else:
            for cooldown in self.quota_cooldowns:
                lines.append(f"- until `{cooldown['cooldown_until']}` :: {cooldown['reason']}")
        return "\n".join(lines) + "\n"
