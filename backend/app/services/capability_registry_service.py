from __future__ import annotations

from datetime import timezone, datetime
from typing import Any

from app.config import settings
from app.core.agent_profiles import agent_profile_registry, get_public_agent_catalog, get_public_mode_catalog
from app.core.llm_router import llm_router
from app.orchestration.dynamic_tool_registry import dynamic_tool_registry


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


class CapabilityRegistryService:
    """Structured body map for Sparkle's current capability surface."""

    _SUBSYSTEMS: tuple[dict[str, Any], ...] = (
        {
            "id": "chat_orchestrator",
            "label": "Chat Orchestrator",
            "kind": "core_runtime",
            "purpose": "Diagnose, decide, act, and explain on the primary user loop.",
            "state": "active",
            "cost_hint": "medium",
            "permissions": {"read": ["conversation", "plan", "profile"], "write": ["session", "episode_candidate"]},
        },
        {
            "id": "openclaw",
            "label": "OpenClaw Pipeline",
            "kind": "execution_pipeline",
            "purpose": "Delegate bounded execution work when the task is ready for action.",
            "state": "configured" if bool(settings.OPENCLAW_ENABLED and settings.OPENCLAW_GATEWAY_URL) else "not_configured",
            "cost_hint": "variable",
            "permissions": {"read": ["execution_probe"], "write": ["execution_artifacts"]},
        },
        {
            "id": "prediction",
            "label": "Prediction Systems",
            "kind": "forecasting",
            "purpose": "Forecast likely next actions, engagement windows, and risk trends.",
            "state": "active",
            "cost_hint": "low",
            "permissions": {"read": ["behavior", "focus", "plan"], "write": []},
        },
        {
            "id": "galaxy",
            "label": "Galaxy Knowledge Systems",
            "kind": "knowledge_graph",
            "purpose": "Ground learning structure, node mastery, and prerequisite maps.",
            "state": "active",
            "cost_hint": "medium",
            "permissions": {"read": ["knowledge_graph", "study_records"], "write": ["knowledge_state"]},
        },
        {
            "id": "feedback_binding",
            "label": "Feedback and Intervention Binding",
            "kind": "adaptation_loop",
            "purpose": "Bind user feedback to interventions and keep adaptations reversible.",
            "state": "active",
            "cost_hint": "low",
            "permissions": {"read": ["active_interventions", "session_feedback"], "write": ["intervention_state"]},
        },
        {
            "id": "community",
            "label": "Community Systems",
            "kind": "social_surface",
            "purpose": "Support community interactions and social accountability loops.",
            "state": "active",
            "cost_hint": "medium",
            "permissions": {"read": ["community_threads"], "write": ["community_posts"]},
        },
        {
            "id": "achievements",
            "label": "Achievement Systems",
            "kind": "motivation_surface",
            "purpose": "Reflect progress and reinforce durable movement without overpowering the core loop.",
            "state": "active",
            "cost_hint": "low",
            "permissions": {"read": ["progress_events"], "write": ["achievement_updates"]},
        },
        {
            "id": "visual_bgm",
            "label": "Visual and BGM Systems",
            "kind": "ambient_surface",
            "purpose": "Shape atmosphere and continuity across chat, focus, and home surfaces.",
            "state": "active",
            "cost_hint": "low",
            "permissions": {"read": ["experience_profile"], "write": ["ambient_state"]},
        },
    )

    _SYSTEM_LAYER_KNOBS: tuple[dict[str, Any], ...] = (
        {
            "id": "model_tier_selection",
            "layer": "system",
            "allowed_scope": "bounded",
            "may_change_when": "A higher-confidence routing or cost constraint justifies it.",
            "must_not_change_when": "User trust or safety would be reduced by a silent downgrade.",
        },
        {
            "id": "agent_mix_selection",
            "layer": "system",
            "allowed_scope": "bounded",
            "may_change_when": "The question clearly benefits from specialist collaboration.",
            "must_not_change_when": "The change would add theatrical complexity without user benefit.",
        },
        {
            "id": "tool_surface_selection",
            "layer": "system",
            "allowed_scope": "bounded",
            "may_change_when": "A tool can improve grounding, execution, or verification.",
            "must_not_change_when": "The tool is unavailable, unsafe, or would weaken reversibility.",
        },
    )

    def build_registry(self) -> dict[str, Any]:
        dynamic_tool_registry.ensure_package_registered("app.tools")
        return {
            "generated_at": _utcnow(),
            "summary": {
                "model_count": len(self._models()),
                "agent_count": len(self._agents()),
                "tool_count": len(self._tools()),
                "subsystem_count": len(self._SUBSYSTEMS),
            },
            "models": self._models(),
            "agents": self._agents(),
            "modes": get_public_mode_catalog(),
            "tools": self._tools(),
            "subsystems": list(self._SUBSYSTEMS),
            "configuration_layers": [
                {"id": "constitutional", "status": "mostly_built", "writes_allowed": False},
                {"id": "session", "status": "built_v1", "writes_allowed": True},
                {"id": "episode", "status": "partially_built", "writes_allowed": "promotion_only"},
                {"id": "profile", "status": "partially_built", "writes_allowed": "evidence_gated"},
                {"id": "system", "status": "design_substrate", "writes_allowed": "registry_gated_future"},
            ],
            "system_layer_knobs": list(self._SYSTEM_LAYER_KNOBS),
            "rights_model": {
                "core_rule": "Sparkle may only operate deeper system knobs through explicit bounded registries.",
                "guardrails": [
                    "User benefit outranks internal sophistication.",
                    "Reversibility is required for session-level adaptation.",
                    "System-level changes must declare cost, risk, and allowed write scope.",
                ],
            },
        }

    def _models(self) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        for key, config in sorted(llm_router._available_models.items()):  # noqa: SLF001 - internal registry surfacing
            health = llm_router._model_health.get(key)  # noqa: SLF001 - internal registry surfacing
            models.append(
                {
                    "key": key,
                    "provider": config.provider.value,
                    "tier": config.tier.value,
                    "model_name": config.model_name,
                    "cost_per_1k_tokens": config.cost_per_1k_tokens,
                    "avg_latency_ms": config.avg_latency_ms,
                    "state": "healthy" if (health is None or health.is_healthy) else "degraded",
                }
            )
        return models

    def _agents(self) -> list[dict[str, Any]]:
        public_catalog = {item["id"]: item for item in get_public_agent_catalog()}
        agents: list[dict[str, Any]] = []
        for role, payload in sorted(
            agent_profile_registry.list_all_profiles().items(),
            key=lambda item: item[0].value,
        ):
            routing_preview = None
            try:
                routing_preview = llm_router.describe_agent_routing(role)
            except Exception:
                routing_preview = None
            public_entry = public_catalog.get(role.value)
            agents.append(
                {
                    "id": role.value,
                    "display_name": payload["display_name"],
                    "persona_archetype": payload.get("persona_archetype"),
                    "expertise_domains": payload.get("expertise_domains") or [],
                    "model_tier": getattr(payload.get("model_tier"), "value", str(payload.get("model_tier") or "")),
                    "allowed_tools": payload.get("tools") or [],
                    "public_entry": public_entry is not None,
                    "routing_preview": routing_preview,
                }
            )
        return agents

    def _tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item["name"],
                "description": item["description"],
                "category": item["category"],
                "module": item.get("module"),
                "class": item.get("class"),
            }
            for item in dynamic_tool_registry.list_tools(verbose=True)
        ]
