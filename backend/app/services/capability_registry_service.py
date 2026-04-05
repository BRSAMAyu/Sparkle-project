from __future__ import annotations

from datetime import timezone, datetime
from typing import Any

from app.config import settings
from app.core.agent_profiles import agent_profile_registry, get_public_agent_catalog, get_public_mode_catalog
from app.core.llm_router import llm_router


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
            "activation_cues": ["primary conversation loop", "diagnosis", "user-facing explanation"],
            "risk_hint": "Can become theatrical if it expands scope without user benefit.",
            "permissions": {"read": ["conversation", "plan", "profile"], "write": ["session", "episode_candidate"]},
        },
        {
            "id": "openclaw",
            "label": "OpenClaw Pipeline",
            "kind": "execution_pipeline",
            "purpose": "Delegate bounded execution work when the task is ready for action.",
            "state": "configured" if bool(settings.OPENCLAW_ENABLED and settings.OPENCLAW_GATEWAY_URL) else "not_configured",
            "cost_hint": "variable",
            "activation_cues": ["bounded execution", "tool-backed delivery", "task-ready action"],
            "risk_hint": "Should not be implied when gateway or rights are unavailable.",
            "permissions": {"read": ["execution_probe"], "write": ["execution_artifacts"]},
        },
        {
            "id": "prediction",
            "label": "Prediction Systems",
            "kind": "forecasting",
            "purpose": "Forecast likely next actions, engagement windows, and risk trends.",
            "state": "active",
            "cost_hint": "low",
            "activation_cues": ["timing optimization", "risk forecasting", "next-move selection"],
            "risk_hint": "Forecasts should inform, not silently steer against user intent.",
            "permissions": {"read": ["behavior", "focus", "plan"], "write": []},
        },
        {
            "id": "galaxy",
            "label": "Galaxy Knowledge Systems",
            "kind": "knowledge_graph",
            "purpose": "Ground learning structure, node mastery, and prerequisite maps.",
            "state": "active",
            "cost_hint": "medium",
            "activation_cues": ["knowledge grounding", "user materials", "mastery structure"],
            "risk_hint": "Weak or stale graph state can create false confidence if not grounded.",
            "permissions": {"read": ["knowledge_graph", "study_records"], "write": ["knowledge_state"]},
        },
        {
            "id": "feedback_binding",
            "label": "Feedback and Intervention Binding",
            "kind": "adaptation_loop",
            "purpose": "Bind user feedback to interventions and keep adaptations reversible.",
            "state": "active",
            "cost_hint": "low",
            "activation_cues": ["visible adaptation", "intervention feedback", "reversibility"],
            "risk_hint": "Adaptations lose trust if they are invisible or feel non-reversible.",
            "permissions": {"read": ["active_interventions", "session_feedback"], "write": ["intervention_state"]},
        },
        {
            "id": "community",
            "label": "Community Systems",
            "kind": "social_surface",
            "purpose": "Support community interactions and social accountability loops.",
            "state": "active",
            "cost_hint": "medium",
            "activation_cues": ["accountability", "shared momentum", "social support"],
            "risk_hint": "Community should not be invoked when privacy or timing makes it burdensome.",
            "permissions": {"read": ["community_threads"], "write": ["community_posts"]},
        },
        {
            "id": "achievements",
            "label": "Achievement Systems",
            "kind": "motivation_surface",
            "purpose": "Reflect progress and reinforce durable movement without overpowering the core loop.",
            "state": "active",
            "cost_hint": "low",
            "activation_cues": ["progress reflection", "celebration", "motivation support"],
            "risk_hint": "Achievement surfaces can cheapen the loop if they replace true diagnosis.",
            "permissions": {"read": ["progress_events"], "write": ["achievement_updates"]},
        },
        {
            "id": "visual_bgm",
            "label": "Visual and BGM Systems",
            "kind": "ambient_surface",
            "purpose": "Shape atmosphere and continuity across chat, focus, and home surfaces.",
            "state": "active",
            "cost_hint": "low",
            "activation_cues": ["mood support", "continuity", "ambient adaptation"],
            "risk_hint": "Ambient changes should support the moment, not distract from it.",
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
        from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

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

    def evaluate_system_change_request(
        self,
        *,
        knob_id: str,
        reason: str,
        reversible: bool,
        target_subsystem_id: str | None = None,
    ) -> dict[str, Any]:
        knob = next((item for item in self._SYSTEM_LAYER_KNOBS if item["id"] == knob_id), None)
        subsystem = next((item for item in self._SUBSYSTEMS if item["id"] == target_subsystem_id), None)
        if knob is None:
            return {
                "allowed": False,
                "reason": "Unknown system-layer knob.",
                "knob_id": knob_id,
            }

        normalized_reason = str(reason or "").strip()
        if not normalized_reason:
            return {
                "allowed": False,
                "reason": "System-layer changes require an explicit user-benefit reason.",
                "knob_id": knob_id,
            }
        if not reversible and knob_id != "model_tier_selection":
            return {
                "allowed": False,
                "reason": "Non-reversible changes are blocked for bounded system-layer knobs.",
                "knob_id": knob_id,
            }
        if subsystem and subsystem["state"] not in {"active", "configured"}:
            return {
                "allowed": False,
                "reason": f"{subsystem['label']} is not available.",
                "knob_id": knob_id,
            }
        return {
            "allowed": True,
            "reason": knob["may_change_when"],
            "knob_id": knob_id,
            "target_subsystem_id": target_subsystem_id,
        }

    @staticmethod
    def _append_unique_entry(
        collection: list[dict[str, Any]],
        entry: dict[str, Any],
    ) -> None:
        entry_id = str(entry.get("id") or "").strip()
        if entry_id and any(str(item.get("id") or "").strip() == entry_id for item in collection):
            return
        collection.append(entry)

    def recommend_runtime_capabilities(
        self,
        *,
        route_intent: str | None,
        experience_mode: str | None,
        grounding_priority: list[str] | None = None,
        active_plan: str | None = None,
    ) -> dict[str, Any]:
        """Return bounded body-awareness guidance for one runtime decision."""
        grounding = [str(item).strip() for item in (grounding_priority or []) if str(item or "").strip()]
        normalized_intent = str(route_intent or "").strip().lower()
        normalized_mode = str(experience_mode or "").strip().lower()

        primary_subsystem = {
            "id": "chat_orchestrator",
            "label": "Chat Orchestrator",
            "why": "Sparkle should stay on the primary diagnosis-decide-act loop for this turn.",
        }
        supporting_subsystems: list[dict[str, Any]] = []
        risk_notes: list[str] = []
        activation_surfaces: list[dict[str, Any]] = []
        evidence_sources: list[str] = ["conversation"]

        if "user_materials" in grounding or normalized_intent in {"knowledge", "translation", "learn", "review"}:
            primary_subsystem = {
                "id": "galaxy",
                "label": "Galaxy Knowledge Systems",
                "why": "This turn benefits from grounded retrieval and structure-aware knowledge support.",
            }
            self._append_unique_entry(
                supporting_subsystems,
                {
                    "id": "chat_orchestrator",
                    "label": "Chat Orchestrator",
                    "why": "The orchestrator should still own explanation quality and user-facing pacing.",
                },
            )
            evidence_sources.extend(["user_materials", "knowledge_graph"])
        elif normalized_intent in {"plan", "planning", "sprint_plan", "task"} or active_plan:
            primary_subsystem = {
                "id": "chat_orchestrator",
                "label": "Chat Orchestrator",
                "why": "This turn is primarily about sequencing and next-move judgment on the active growth path.",
            }
            self._append_unique_entry(
                supporting_subsystems,
                {
                    "id": "prediction",
                    "label": "Prediction Systems",
                    "why": "Prediction can help choose a lighter next move or a better timing window.",
                },
            )
            evidence_sources.extend(["active_plan", "behavioral_timing"])
        elif normalized_mode in {"stabilize", "mobilize", "reframe"}:
            primary_subsystem = {
                "id": "feedback_binding",
                "label": "Feedback and Intervention Binding",
                "why": "This turn is adaptation-heavy and should stay reversible and feedback-aware.",
            }
            self._append_unique_entry(
                supporting_subsystems,
                {
                    "id": "chat_orchestrator",
                    "label": "Chat Orchestrator",
                    "why": "The orchestrator still needs to express the adaptation in human language.",
                },
            )
            self._append_unique_entry(
                activation_surfaces,
                {
                    "id": "visual_bgm",
                    "label": "Visual and BGM Systems",
                    "why": "Ambient support can reinforce the lighter or steadier posture without changing the core plan.",
                },
            )

        if normalized_intent in {"execution", "delegate", "openclaw"}:
            openclaw_state = next(
                (subsystem for subsystem in self._SUBSYSTEMS if subsystem["id"] == "openclaw"),
                None,
            )
            if openclaw_state and openclaw_state["state"] == "configured":
                self._append_unique_entry(
                    supporting_subsystems,
                    {
                        "id": "openclaw",
                        "label": "OpenClaw Pipeline",
                        "why": "Execution can be delegated in a bounded way when the task is ready for action.",
                    },
                )
            else:
                risk_notes.append("OpenClaw is not configured, so Sparkle should avoid pretending execution is available.")

        if normalized_mode in {"mobilize", "celebrate"}:
            self._append_unique_entry(
                activation_surfaces,
                {
                    "id": "achievements",
                    "label": "Achievement Systems",
                    "why": "Progress reflection can reinforce momentum after a real movement signal.",
                },
            )
        if normalized_intent in {"community", "accountability", "group"}:
            self._append_unique_entry(
                activation_surfaces,
                {
                    "id": "community",
                    "label": "Community Systems",
                    "why": "This turn explicitly benefits from social accountability or shared support.",
                },
            )

        knob_decisions = [
            self.evaluate_system_change_request(
                knob_id="tool_surface_selection",
                reason="Grounding and runtime subsystem choice should stay tied to user benefit.",
                reversible=True,
                target_subsystem_id=primary_subsystem["id"],
            )
        ]
        if supporting_subsystems:
            knob_decisions.append(
                self.evaluate_system_change_request(
                    knob_id="agent_mix_selection",
                    reason="Supporting subsystems are only warranted when they improve the current user outcome.",
                    reversible=True,
                    target_subsystem_id=supporting_subsystems[0]["id"],
                )
            )

        return {
            "primary_subsystem": primary_subsystem,
            "supporting_subsystems": supporting_subsystems,
            "activation_surfaces": activation_surfaces,
            "evidence_sources": sorted(set(evidence_sources)),
            "bounded_knob_decisions": knob_decisions,
            "grounding_priority": grounding,
            "cost_posture": "medium" if primary_subsystem["id"] in {"galaxy", "openclaw"} else "low",
            "risk_notes": risk_notes,
            "rights_note": "System choice is advisory and bounded; Sparkle should not silently expand write scope.",
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
        from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

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
