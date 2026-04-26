"""Agent activity event definitions and display configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from app.core.i18n import I18n


AGENT_DISPLAY_I18N_KEYS: dict[str, dict[str, str]] = {
    "orchestrator": {
        "display_name": "agent_activity.orchestrator_name",
        "description": "agent_activity.orchestrator_desc",
    },
    "synthesis": {
        "display_name": "agent_activity.synthesis_name",
        "description": "agent_activity.synthesis_desc",
    },
    "galaxy_guide": {
        "display_name": "agent_activity.galaxy_guide_name",
        "description": "agent_activity.galaxy_guide_desc",
    },
    "exam_oracle": {
        "display_name": "agent_activity.exam_oracle_name",
        "description": "agent_activity.exam_oracle_desc",
    },
    "time_tutor": {
        "display_name": "agent_activity.time_tutor_name",
        "description": "agent_activity.time_tutor_desc",
    },
    "deep_analyst": {
        "display_name": "agent_activity.deep_analyst_name",
        "description": "agent_activity.deep_analyst_desc",
    },
    "error_analyst": {
        "display_name": "agent_activity.error_analyst_name",
        "description": "agent_activity.error_analyst_desc",
    },
    "study_buddy": {
        "display_name": "agent_activity.study_buddy_name",
        "description": "agent_activity.study_buddy_desc",
    },
    "math_expert": {
        "display_name": "agent_activity.math_expert_name",
        "description": "agent_activity.math_expert_desc",
    },
    "math_agent": {
        "display_name": "agent_activity.math_expert_name",
        "description": "agent_activity.math_expert_desc",
    },
    "code_expert": {
        "display_name": "agent_activity.code_expert_name",
        "description": "agent_activity.code_expert_desc",
    },
    "code_agent": {
        "display_name": "agent_activity.code_expert_name",
        "description": "agent_activity.code_expert_desc",
    },
    "writing_expert": {
        "display_name": "agent_activity.writing_expert_name",
        "description": "agent_activity.writing_expert_desc",
    },
    "writing_agent": {
        "display_name": "agent_activity.writing_expert_name",
        "description": "agent_activity.writing_expert_desc",
    },
    "science_expert": {
        "display_name": "agent_activity.science_expert_name",
        "description": "agent_activity.science_expert_desc",
    },
    "science_agent": {
        "display_name": "agent_activity.science_expert_name",
        "description": "agent_activity.science_expert_desc",
    },
    "search_expert": {
        "display_name": "agent_activity.search_expert_name",
        "description": "agent_activity.search_expert_desc",
    },
    "search_agent": {
        "display_name": "agent_activity.search_expert_name",
        "description": "agent_activity.search_expert_desc",
    },
}

def _get_default_icon(agent_id: str) -> str:
    icons = {
        "orchestrator": "layers", "synthesis": "layers", "galaxy_guide": "constellation",
        "exam_oracle": "target", "time_tutor": "clock", "deep_analyst": "microscope",
        "error_analyst": "debug", "study_buddy": "handshake", "math_expert": "calculator",
        "math_agent": "calculator", "code_expert": "code", "code_agent": "code",
        "writing_expert": "pen", "writing_agent": "pen", "science_expert": "flask",
        "science_agent": "flask", "search_expert": "search", "search_agent": "search",
    }
    return icons.get(agent_id, "bot")


def _get_default_color(agent_id: str) -> str:
    colors = {
        "orchestrator": "#5F6CAF", "synthesis": "#5F6CAF", "galaxy_guide": "#6C5CE7",
        "exam_oracle": "#E17055", "time_tutor": "#00B894", "deep_analyst": "#0984E3",
        "error_analyst": "#D63031", "study_buddy": "#FDCB6E", "math_expert": "#6C5CE7",
        "math_agent": "#6C5CE7", "code_expert": "#00CEC9", "code_agent": "#00CEC9",
        "writing_expert": "#E84393", "writing_agent": "#E84393", "science_expert": "#00B894",
        "science_agent": "#00B894", "search_expert": "#636E72", "search_agent": "#636E72",
    }
    return colors.get(agent_id, "#636E72")


AGENT_DISPLAY_CONFIG: dict[str, dict[str, str]] = {}
for _agent_id, _keys in AGENT_DISPLAY_I18N_KEYS.items():
    AGENT_DISPLAY_CONFIG[_agent_id] = {
        "display_name": I18n.t(_keys["display_name"], locale="zh"),
        "icon": _get_default_icon(_agent_id),
        "color": _get_default_color(_agent_id),
        "description": I18n.t(_keys["description"], locale="zh"),
    }


@dataclass
class AgentActivityEvent:
    """Single agent activity event emitted during graph execution."""

    agent_id: str
    status: Literal["pending", "active", "completed", "error"]
    display_name: str = ""
    icon: str = ""
    color: str = ""
    description: str = ""
    duration_ms: float | None = None
    result_summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        config = AGENT_DISPLAY_CONFIG.get(self.agent_id, {})
        if not self.display_name:
            self.display_name = config.get("display_name", self.agent_id)
        if not self.icon:
            self.icon = config.get("icon", "bot")
        if not self.color:
            self.color = config.get("color", "#636E72")
        if not self.description:
            self.description = config.get("description", "")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {key: value for key, value in payload.items() if value is not None}


async def emit_agent_activity(
    stream_callback: Any | None,
    *,
    agent_id: str,
    status: Literal["pending", "active", "completed", "error"],
    duration_ms: float | None = None,
    result_summary: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Emit an agent_activity event through the stream callback."""
    if stream_callback is None:
        return

    event = AgentActivityEvent(
        agent_id=agent_id,
        status=status,
        duration_ms=duration_ms,
        result_summary=result_summary,
        metadata=metadata or {},
    )

    from app.gen.agent.v1 import agent_service_pb2
    import json

    await stream_callback(
        agent_service_pb2.ChatResponse(
            metadata={
                "event_type": "agent_activity",
                "payload": json.dumps(event.to_dict(), ensure_ascii=False),
            }
        )
    )


def get_stream_callback(config: dict[str, Any] | None) -> Any | None:
    """Extract stream_callback from LangGraph RunnableConfig."""
    if config is None:
        return None
    configurable = config.get("configurable", {})
    return configurable.get("stream_callback")


def build_routing_preview(
    *,
    selected_experts: list[str],
    complexity_score: float,
    complexity_tier: str,
    route_confidence: float,
    routing_strategy: str,
) -> dict[str, Any]:
    expert_cards = []
    for expert_id in selected_experts:
        config = AGENT_DISPLAY_CONFIG.get(expert_id, {})
        expert_cards.append(
            {
                "agent_id": expert_id,
                "display_name": config.get("display_name", expert_id),
                "icon": config.get("icon", "bot"),
                "color": config.get("color", "#636E72"),
            }
        )
    eta_seconds = 3 if len(selected_experts) <= 1 else 4 + max(0, len(selected_experts) - 2) * 2
    return {
        "complexity_score": round(float(complexity_score or 0.0), 2),
        "complexity_tier": str(complexity_tier or "low"),
        "route_confidence": round(float(route_confidence or 0.0), 2),
        "routing_strategy": str(routing_strategy or ""),
        "selected_experts": selected_experts,
        "experts": expert_cards,
        "eta_seconds_min": max(2, eta_seconds - 1),
        "eta_seconds_max": eta_seconds + 2,
    }


async def emit_routing_preview(
    stream_callback: Any | None,
    *,
    selected_experts: list[str],
    complexity_score: float,
    complexity_tier: str,
    route_confidence: float,
    routing_strategy: str,
) -> dict[str, Any]:
    if stream_callback is None:
        return build_routing_preview(
            selected_experts=selected_experts,
            complexity_score=complexity_score,
            complexity_tier=complexity_tier,
            route_confidence=route_confidence,
            routing_strategy=routing_strategy,
        )

    payload = build_routing_preview(
        selected_experts=selected_experts,
        complexity_score=complexity_score,
        complexity_tier=complexity_tier,
        route_confidence=route_confidence,
        routing_strategy=routing_strategy,
    )

    from app.gen.agent.v1 import agent_service_pb2
    import json

    await stream_callback(
        agent_service_pb2.ChatResponse(
            metadata={
                "event_type": "routing_preview",
                "payload": json.dumps(payload, ensure_ascii=False),
            }
        )
    )
    return payload


async def emit_agent_turn(
    stream_callback: Any | None,
    *,
    agent_id: str,
    turn_index: int,
    content: str,
    turn_type: Literal["analysis", "rebuttal", "synthesis", "question"] = "analysis",
    references: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = AGENT_DISPLAY_CONFIG.get(agent_id, {})
    payload = {
        "agent_id": agent_id,
        "display_name": config.get("display_name", agent_id),
        "icon": config.get("icon", "bot"),
        "color": config.get("color", "#636E72"),
        "turn_index": turn_index,
        "turn_type": turn_type,
        "content": str(content or "").strip(),
        "references": list(references or []),
        "metadata": dict(metadata or {}),
    }
    if stream_callback is None:
        return payload

    from app.gen.agent.v1 import agent_service_pb2
    import json

    await stream_callback(
        agent_service_pb2.ChatResponse(
            metadata={
                "event_type": "agent_turn",
                "payload": json.dumps(payload, ensure_ascii=False),
            }
        )
    )
    return payload
