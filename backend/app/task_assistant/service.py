"""Task assistant dormant-mode service helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from loguru import logger

from app.aurora.context import AuroraDecisionContext
from app.aurora.tasks import enqueue_nearline_context
from app.aurora.schemas import SignalSnapshot
from app.task_assistant.schemas import TaskAssistantContextPayload


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_task_assistant_context(raw_context: dict[str, Any] | None) -> TaskAssistantContextPayload | None:
    """Parse the optional dormant-mode task-assistant payload from request context."""

    if not isinstance(raw_context, dict):
        return None
    payload = raw_context.get("task_assistant")
    if payload is None:
        return None
    try:
        return TaskAssistantContextPayload.model_validate(payload)
    except Exception as exc:  # pragma: no cover - defensive parsing only
        logger.warning(f"Invalid task assistant context ignored: {exc}")
        return None


def build_task_assistant_system_appendix(context: TaskAssistantContextPayload | None) -> str:
    """Render dormant-mode context into a compact prompt appendix."""

    if context is None:
        return ""

    injection = context.injection
    claims = "\n".join(f"- {claim}" for claim in injection.active_claims[:3]) or "- none"
    probes = "\n".join(f"- {probe}" for probe in injection.recent_probe_outcomes[:3]) or "- none"
    guidance = (injection.guidance_content or "").strip()
    if len(guidance) > 1200:
        guidance = f"{guidance[:1200].rstrip()}…"
    if not guidance:
        guidance = "No pre-generated TaskGuidance was available; rely on the focus summary and current task context."

    return (
        "\n\nTASK ASSISTANT DORMANT CONTEXT:\n"
        f"- session_mode: {context.session_mode}\n"
        f"- cold_start: {context.cold_start}\n"
        f"- refresh_reason: {context.refresh_reason or 'session_start'}\n"
        f"- strong_signal: {context.strong_signal or 'none'}\n"
        f"- focus_summary: {injection.focus_summary or 'Current task focus only'}\n"
        f"- guidance_source: {injection.guidance_source}\n"
        f"- latest_ux_intent: {injection.latest_ux_intent}\n"
        f"- latest_aurora_presence: {injection.latest_aurora_presence}\n"
        "Use this only as a one-shot dormant-mode grounding layer.\n"
        "Do not pretend Aurora is continuously steering this session.\n"
        "Only shift into heavier scaffolding if the user shows a strong blockage or explicitly asks for planning.\n"
        "Guidance grounding:\n"
        f"{guidance}\n"
        "Projection-allowed active claims:\n"
        f"{claims}\n"
        "Recent probe outcomes:\n"
        f"{probes}\n"
    )


def enqueue_task_assistant_nearline(
    *,
    user_id: UUID,
    task_id: UUID,
    task_title: str,
    user_message: str,
    assistant_message: str,
    conversation_id: str | None,
    context: TaskAssistantContextPayload | None,
) -> dict[str, Any] | None:
    """Schedule a nearline task-assistant outcome optimization pass when possible."""

    if context is None:
        return None

    digest = hashlib.sha256(
        f"{user_id}|{task_id}|{conversation_id or 'new'}|{user_message}|{assistant_message}".encode("utf-8")
    ).hexdigest()[:16]
    snapshot = SignalSnapshot(
        snapshot_hash=f"task_assistant_{digest}",
        user_id=user_id,
        collected_at=_utcnow(),
        scenario_pack_id="stage4_task_assistant@v1",
        policy_version="aurora_policy@v1.0",
        core_signals={
            "user_message": user_message,
            "task_id": str(task_id),
            "task_title": task_title,
        },
        enhanced_signals={
            "task_assistant_dormant": True,
            "frustration_signal": bool(context.strong_signal == "frustration"),
        },
        optional_signals={
            "conversation_id": conversation_id or "",
            "task_assistant_refresh_reason": context.refresh_reason or "session_start",
            "task_assistant_guidance_source": context.injection.guidance_source,
            "task_card_id": str(task_id),
        },
        total_tokens=max(len(user_message) + len(assistant_message), 1),
        budget_limit=4000,
    )
    execution = enqueue_nearline_context(
        AuroraDecisionContext(
            snapshot=snapshot,
            trigger_point="task-assistant-nearline",
            current_node="task_assistant_dormant",
            candidate_node=None,
            mode="nearline",
            prior_outputs={
                "task_assistant_outcome": {
                    "turn_index": context.outcome.turn_index if context.outcome else 0,
                    "refresh_reason": context.refresh_reason or "session_start",
                    "strong_signal": context.strong_signal,
                    "used_cold_start_fallback": bool(
                        context.outcome.used_cold_start_fallback if context.outcome else False
                    ),
                }
            },
        )
    )
    return execution.to_payload()
