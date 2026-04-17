from __future__ import annotations

from datetime import timezone, datetime
from typing import Any

from app.config import settings
from app.core.agent_profiles import ModelTier, agent_profile_registry, get_public_agent_catalog, get_public_mode_catalog
from app.core.llm_router import llm_router
from app.services.constitutional_drift_firewall import ConstitutionalDriftFirewall
from app.services.five_layer_learning_contract import DEFAULT_FIVE_LAYER_CONTRACT


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


class CapabilityRegistryService:
    """Structured body map for Sparkle's current capability surface."""

    SCHEMA_VERSION = "phase_d.v1"

    def __init__(self) -> None:
        self.firewall = ConstitutionalDriftFirewall()
        self.contract = DEFAULT_FIVE_LAYER_CONTRACT

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
            "rights_model": "bounded_registry_only",
            "reversible": False,
            "approval_level": "human_review_for_non_default",
            "evidence_threshold": 0.8,
            "allowed_target_layers": ["system"],
            "constitutional_review_required": True,
            "forbidden_without_human_approval": True,
        },
        {
            "id": "agent_mix_selection",
            "layer": "system",
            "allowed_scope": "bounded",
            "may_change_when": "The question clearly benefits from specialist collaboration.",
            "must_not_change_when": "The change would add theatrical complexity without user benefit.",
            "rights_model": "bounded_registry_only",
            "reversible": True,
            "approval_level": "bounded_runtime",
            "evidence_threshold": 0.65,
            "allowed_target_layers": ["system", "session"],
            "constitutional_review_required": True,
            "forbidden_without_human_approval": False,
        },
        {
            "id": "tool_surface_selection",
            "layer": "system",
            "allowed_scope": "bounded",
            "may_change_when": "A tool can improve grounding, execution, or verification.",
            "must_not_change_when": "The tool is unavailable, unsafe, or would weaken reversibility.",
            "rights_model": "bounded_registry_only",
            "reversible": True,
            "approval_level": "bounded_runtime",
            "evidence_threshold": 0.6,
            "allowed_target_layers": ["system", "session"],
            "constitutional_review_required": True,
            "forbidden_without_human_approval": False,
        },
    )

    def build_registry(self) -> dict[str, Any]:
        from app.orchestration.dynamic_tool_registry import dynamic_tool_registry

        dynamic_tool_registry.ensure_package_registered("app.tools")
        models = self._models()
        agents = self._agents()
        tools = self._tools()
        canonical_capabilities = self._canonical_capabilities(
            models=models,
            agents=agents,
            tools=tools,
        )
        return {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": _utcnow(),
            "summary": {
                "model_count": len(models),
                "agent_count": len(agents),
                "tool_count": len(tools),
                "subsystem_count": len(self._SUBSYSTEMS),
                "canonical_capability_count": len(canonical_capabilities),
            },
            "canonical_capabilities": canonical_capabilities,
            "models": models,
            "agents": agents,
            "modes": get_public_mode_catalog(),
            "tools": tools,
            "subsystems": list(self._SUBSYSTEMS),
            "configuration_layers": [
                {"id": "constitutional", "status": "mostly_built", "writes_allowed": False, "contract_version": self.contract.version},
                {"id": "session", "status": "built_v1", "writes_allowed": True, "contract_version": self.contract.version},
                {"id": "episode", "status": "partially_built", "writes_allowed": "promotion_only", "contract_version": self.contract.version},
                {"id": "profile", "status": "partially_built", "writes_allowed": "evidence_gated", "contract_version": self.contract.version},
                {"id": "system", "status": "design_substrate", "writes_allowed": "registry_gated_future", "contract_version": self.contract.version},
            ],
            "system_layer_knobs": list(self._SYSTEM_LAYER_KNOBS),
            "rights_model": {
                "core_rule": "Sparkle may only operate deeper system knobs through explicit bounded registries.",
                "guardrails": [
                    "User benefit outranks internal sophistication.",
                    "Reversibility is required for session-level adaptation.",
                    "System-level changes must declare cost, risk, and allowed write scope.",
                    "System-layer rights remain contract-gated and constitution-reviewed.",
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
        evidence_strength: float | None = None,
        target_layer: str | None = None,
        approval_level: str | None = None,
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
        if not reversible and bool(knob.get("reversible")):
            return {
                "allowed": False,
                "reason": "Non-reversible changes are blocked for bounded system-layer knobs.",
                "knob_id": knob_id,
            }
        if approval_level and approval_level != knob.get("approval_level"):
            return {
                "allowed": False,
                "reason": "Approval level does not satisfy the knob contract.",
                "knob_id": knob_id,
            }
        if target_layer and target_layer not in list(knob.get("allowed_target_layers") or []):
            return {
                "allowed": False,
                "reason": "Target layer is outside the bounded rights model for this knob.",
                "knob_id": knob_id,
            }
        if evidence_strength is not None and float(evidence_strength) < float(knob.get("evidence_threshold") or 0.0):
            return {
                "allowed": False,
                "reason": "Evidence threshold not met for this system-layer change.",
                "knob_id": knob_id,
            }
        if subsystem and subsystem["state"] not in {"active", "configured"}:
            return {
                "allowed": False,
                "reason": f"{subsystem['label']} is not available.",
                "knob_id": knob_id,
            }
        safety_report = self.firewall.evaluate_system_change(
            knob_id=knob_id,
            reason=normalized_reason,
            rights_model=str(knob.get("rights_model") or "bounded_registry_only"),
            reversible=bool(knob.get("reversible")),
        ).to_dict()
        if not safety_report["allowed"]:
            return {
                "allowed": False,
                "reason": "Constitutional review blocked this system-layer change.",
                "knob_id": knob_id,
                "target_subsystem_id": target_subsystem_id,
                "safety_report": safety_report,
            }
        if safety_report["disposition"] == "escalate_review":
            return {
                "allowed": False,
                "reason": "System-layer change requires escalation review before activation.",
                "knob_id": knob_id,
                "target_subsystem_id": target_subsystem_id,
                "safety_report": safety_report,
            }
        return {
            "allowed": True,
            "reason": knob["may_change_when"],
            "knob_id": knob_id,
            "target_subsystem_id": target_subsystem_id,
            "rights_model": knob.get("rights_model"),
            "approval_level": knob.get("approval_level"),
            "evidence_threshold": knob.get("evidence_threshold"),
            "allowed_target_layers": list(knob.get("allowed_target_layers") or []),
            "constitutional_review_required": bool(knob.get("constitutional_review_required")),
            "forbidden_without_human_approval": bool(knob.get("forbidden_without_human_approval")),
            "safety_report": safety_report,
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

    def _canonical_capabilities(
        self,
        *,
        models: list[dict[str, Any]],
        agents: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        capabilities: list[dict[str, Any]] = []
        for item in models:
            tier = str(item.get("tier") or "")
            capabilities.append(
                {
                    "capability_id": f"model:{item['key']}",
                    "label": str(item.get("model_name") or item["key"]),
                    "capability_kind": "model",
                    "purpose": f"Generation and reasoning at the {tier or 'unknown'} tier.",
                    "availability": "healthy" if item.get("state") == "healthy" else "degraded",
                    "quality_hint": self._quality_hint_for_model_tier(tier),
                    "latency_hint": self._latency_hint(item.get("avg_latency_ms")),
                    "cost_hint": self._cost_hint_for_tier(tier, item.get("cost_per_1k_tokens")),
                    "read_scope": ["conversation", "tool_results"],
                    "write_scope": [],
                    "required_preconditions": ["provider_configured"],
                    "when_to_use": [f"{tier}_tier_generation", "llm_routing_selected"],
                    "when_not_to_use": ["provider_unhealthy", "cost_band_rejected"],
                    "rights_model": "read_only_generation",
                    "reversible": True,
                    "declared_knobs": ["model_tier_selection"],
                }
            )
        for item in agents:
            capabilities.append(
                {
                    "capability_id": f"agent:{item['id']}",
                    "label": str(item.get("display_name") or item["id"]),
                    "capability_kind": "agent",
                    "purpose": f"Specialized reasoning path for {item['id']}.",
                    "availability": "available" if item.get("public_entry") else "configured",
                    "quality_hint": "specialized" if item.get("expertise_domains") else "general",
                    "latency_hint": "medium",
                    "cost_hint": self._cost_hint_for_tier(item.get("model_tier"), None),
                    "read_scope": ["conversation", "context"],
                    "write_scope": [],
                    "required_preconditions": ["agent_profile_registered"],
                    "when_to_use": list(item.get("expertise_domains") or []) or ["expert_collaboration", item["id"]],
                    "when_not_to_use": ["specialist_not_needed"],
                    "rights_model": "read_only_reasoning",
                    "reversible": True,
                    "declared_knobs": ["agent_mix_selection"],
                }
            )
        for item in tools:
            tool_name = str(item.get("name") or "")
            capabilities.append(
                {
                    "capability_id": f"tool:{tool_name}",
                    "label": tool_name,
                    "capability_kind": "tool",
                    "purpose": str(item.get("description") or ""),
                    "availability": "available",
                    "quality_hint": "bounded" if tool_name in {"query_knowledge"} else "task_specific",
                    "latency_hint": "medium",
                    "cost_hint": "low",
                    "read_scope": ["conversation", "knowledge"] if tool_name == "query_knowledge" else ["conversation"],
                    "write_scope": [],
                    "required_preconditions": ["tool_registered"],
                    "when_to_use": [str(item.get("category") or ""), tool_name],
                    "when_not_to_use": ["tool_unavailable", "rights_blocked"],
                    "rights_model": "tool_registry_bounded",
                    "reversible": True,
                    "declared_knobs": ["tool_surface_selection"],
                }
            )
        for item in self._SUBSYSTEMS:
            kind = "surface" if item["id"] in {"community", "achievements", "visual_bgm"} else "subsystem"
            capabilities.append(
                {
                    "capability_id": f"{kind}:{item['id']}",
                    "label": item["label"],
                    "capability_kind": kind,
                    "purpose": item["purpose"],
                    "availability": self._normalize_subsystem_state(item.get("state")),
                    "quality_hint": "operational_now" if item["id"] not in {"community", "achievements", "visual_bgm"} else "soft_guided",
                    "latency_hint": "medium",
                    "cost_hint": str(item.get("cost_hint") or "medium"),
                    "read_scope": list((item.get("permissions") or {}).get("read") or []),
                    "write_scope": list((item.get("permissions") or {}).get("write") or []),
                    "required_preconditions": list(item.get("activation_cues") or []),
                    "when_to_use": list(item.get("activation_cues") or []),
                    "when_not_to_use": [str(item.get("risk_hint") or "")],
                    "rights_model": "declared_permissions_only",
                    "reversible": item["id"] not in {"openclaw", "community"},
                    "declared_knobs": ["tool_surface_selection"] if kind == "surface" else ["agent_mix_selection"],
                }
            )
        capabilities.extend(self._canonical_runtime_paths())
        for item in self._SYSTEM_LAYER_KNOBS:
            capabilities.append(
                {
                    "capability_id": f"knob:{item['id']}",
                    "label": item["id"],
                    "capability_kind": "knob",
                    "purpose": f"Bounded system knob for {item['id']}.",
                    "availability": "declared",
                    "quality_hint": "declared_but_not_governed",
                    "latency_hint": "n/a",
                    "cost_hint": "n/a",
                    "read_scope": [],
                    "write_scope": [str(item.get("layer") or "system")],
                    "required_preconditions": [str(item.get("may_change_when") or "")],
                    "when_to_use": [str(item.get("may_change_when") or "")],
                    "when_not_to_use": [str(item.get("must_not_change_when") or "")],
                    "rights_model": "bounded_registry_only",
                    "reversible": bool(item.get("reversible")),
                    "declared_knobs": [item["id"]],
                    "approval_level": item.get("approval_level"),
                    "evidence_threshold": item.get("evidence_threshold"),
                    "allowed_target_layers": list(item.get("allowed_target_layers") or []),
                    "constitutional_review_required": bool(item.get("constitutional_review_required")),
                    "forbidden_without_human_approval": bool(item.get("forbidden_without_human_approval")),
                }
            )
        return capabilities

    @staticmethod
    def _canonical_runtime_paths() -> list[dict[str, Any]]:
        return [
            {
                "capability_id": "path:body_awareness_guidance_projection",
                "label": "Body Awareness Guidance Projection",
                "capability_kind": "orchestration_path",
                "purpose": "Project current body-awareness decisions into decision_context for prompt/runtime consumers.",
                "availability": "available",
                "quality_hint": "compatibility_projection",
                "latency_hint": "low",
                "cost_hint": "low",
                "read_scope": ["decision_context"],
                "write_scope": ["decision_context"],
                "required_preconditions": ["situation_brief_compiled"],
                "when_to_use": ["prompt_guidance", "brief_projection"],
                "when_not_to_use": ["when_runtime_contract_is_missing"],
                "rights_model": "projection_only",
                "reversible": True,
                "declared_knobs": [],
            },
            {
                "capability_id": "path:specialist_expert_path",
                "label": "Specialist Expert Path",
                "capability_kind": "orchestration_path",
                "purpose": "Route the turn through specialist collaboration when the requirement profile justifies it.",
                "availability": "available",
                "quality_hint": "operational_now",
                "latency_hint": "medium",
                "cost_hint": "medium",
                "read_scope": ["conversation", "user_context"],
                "write_scope": ["state.context_data"],
                "required_preconditions": ["selected_experts_available"],
                "when_to_use": ["specialist_reasoning", "error_diagnosis", "prediction"],
                "when_not_to_use": ["specialist_not_needed", "cost_band_low"],
                "rights_model": "state_bounded",
                "reversible": True,
                "declared_knobs": ["agent_mix_selection"],
            },
            {
                "capability_id": "path:user_material_grounding",
                "label": "User Material Grounding Path",
                "capability_kind": "retrieval_path",
                "purpose": "Ground the turn in user-provided materials before answering.",
                "availability": "available",
                "quality_hint": "operational_now",
                "latency_hint": "medium",
                "cost_hint": "medium",
                "read_scope": ["conversation", "user_materials"],
                "write_scope": ["decision_context"],
                "required_preconditions": ["file_scope_available"],
                "when_to_use": ["mandatory_grounding", "user_materials"],
                "when_not_to_use": ["no_scoped_files"],
                "rights_model": "session_bounded",
                "reversible": True,
                "declared_knobs": ["tool_surface_selection"],
            },
            {
                "capability_id": "path:no_retrieval",
                "label": "No Retrieval Fallback Path",
                "capability_kind": "retrieval_path",
                "purpose": "Stay on a bounded no-retrieval path when no authorized retrieval organ is live.",
                "availability": "available",
                "quality_hint": "fallback_only",
                "latency_hint": "low",
                "cost_hint": "low",
                "read_scope": ["conversation"],
                "write_scope": [],
                "required_preconditions": ["retrieval_organs_unavailable_or_not_authorized"],
                "when_to_use": ["fallback_only", "no_live_retrieval", "cost_minimal"],
                "when_not_to_use": ["when_grounding_is_available"],
                "rights_model": "bounded_fallback_only",
                "reversible": True,
                "declared_knobs": [],
            },
        ]

    @staticmethod
    def _normalize_subsystem_state(value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"active", "configured"}:
            return "available"
        if normalized in {"not_configured", "blocked"}:
            return "blocked"
        return normalized or "unknown"

    @staticmethod
    def _quality_hint_for_model_tier(tier: Any) -> str:
        normalized = str(tier or "").strip().lower()
        if normalized in {ModelTier.FAST.value, ModelTier.FREE_FAST.value}:
            return "fast_enough"
        if normalized in {ModelTier.PRO.value, ModelTier.MAX.value}:
            return "deep_reasoning"
        return "balanced"

    @staticmethod
    def _cost_hint_for_tier(tier: Any, explicit_cost: Any) -> str:
        normalized = str(tier or "").strip().lower()
        if normalized in {ModelTier.FAST.value, ModelTier.FREE_FAST.value, ModelTier.FREE.value}:
            return "low"
        if normalized in {ModelTier.PRO.value, ModelTier.MAX.value}:
            return "high"
        if isinstance(explicit_cost, (int, float)) and float(explicit_cost) >= 0.001:
            return "medium"
        return "medium"

    @staticmethod
    def _latency_hint(avg_latency_ms: Any) -> str:
        try:
            latency = float(avg_latency_ms)
        except (TypeError, ValueError):
            return "unknown"
        if latency <= 400:
            return "low"
        if latency <= 1200:
            return "medium"
        return "high"
