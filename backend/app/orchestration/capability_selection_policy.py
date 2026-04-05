from __future__ import annotations

from typing import Any

from app.core.agent_profiles import ModelTier


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json")
        return dumped if isinstance(dumped, dict) else {}
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _strip(value: Any) -> str:
    return str(value or "").strip()


class CapabilitySelectionPolicy:
    """Select runtime organs from the Phase D body map and requirements."""

    _BLOCKED_AVAILABILITY = {"disabled", "unavailable", "blocked", "not_configured"}
    _HEALTHY_AVAILABILITY = {"available", "healthy", "configured", "active"}
    _DEFAULT_SPECIALIST_ORDER = [
        "agent:error_analyst",
        "agent:deep_analyst",
        "agent:math_agent",
        "agent:science_agent",
        "agent:search_agent",
        "agent:galaxy_guide",
        "agent:time_tutor",
        "agent:study_buddy",
        "agent:writing_agent",
        "agent:code_agent",
    ]
    _COST_BAND_TO_TIERS = {
        "low": [ModelTier.FAST.value, ModelTier.STANDARD.value],
        "balanced": [ModelTier.STANDARD.value, ModelTier.FAST.value, ModelTier.PLUS.value],
        "medium": [ModelTier.PLUS.value, ModelTier.STANDARD.value, ModelTier.PRO.value],
        "high": [ModelTier.PRO.value, ModelTier.PLUS.value, ModelTier.MAX.value],
    }
    _FALLBACK_TIER_ORDER = [
        ModelTier.FAST.value,
        ModelTier.STANDARD.value,
        ModelTier.PLUS.value,
        ModelTier.PRO.value,
        ModelTier.MAX.value,
    ]

    def build_body_map(
        self,
        *,
        registry: dict[str, Any],
        route_intent: str | None,
        capability_requirements: dict[str, Any] | None,
    ) -> dict[str, Any]:
        registry = _as_dict(registry)
        capabilities = [
            item
            for item in _as_list(registry.get("canonical_capabilities"))
            if isinstance(item, dict) and _strip(item.get("capability_id"))
        ]
        capabilities_by_id = {
            _strip(item["capability_id"]): dict(item)
            for item in capabilities
        }
        requirements = _as_dict(capability_requirements)
        normalized_intent = _strip(route_intent).lower()

        model_catalog: dict[str, dict[str, Any]] = {}
        models_by_tier: dict[str, list[str]] = {}
        for model in _as_list(registry.get("models")):
            if not isinstance(model, dict):
                continue
            capability_id = f"model:{_strip(model.get('key'))}"
            if capability_id == "model:":
                continue
            tier = _strip(model.get("tier")).lower()
            model_catalog[capability_id] = {
                "capability_id": capability_id,
                "tier": tier,
                "state": _strip(model.get("state")).lower(),
                "provider": _strip(model.get("provider")).lower(),
                "model_name": _strip(model.get("model_name")),
                "cost_per_1k_tokens": model.get("cost_per_1k_tokens"),
                "avg_latency_ms": model.get("avg_latency_ms"),
            }
            models_by_tier.setdefault(tier, []).append(capability_id)

        available_organs: list[str] = []
        healthy_organs: list[str] = []
        blocked_organs: list[str] = []
        evidence_relevant_organs: list[str] = []
        cost_sensitive_organs: list[str] = []
        candidate_organs_for_turn: list[str] = []
        recommended_organs: list[str] = []
        surface_constraints: list[str] = []

        for capability_id, item in capabilities_by_id.items():
            availability = _strip(item.get("availability")).lower()
            if availability not in self._BLOCKED_AVAILABILITY:
                available_organs.append(capability_id)
            if availability in self._HEALTHY_AVAILABILITY:
                healthy_organs.append(capability_id)
            if availability in self._BLOCKED_AVAILABILITY:
                blocked_organs.append(capability_id)

            when_to_use = " ".join(str(part).lower() for part in _as_list(item.get("when_to_use")))
            if any(marker in when_to_use for marker in ("material", "ground", "knowledge", "retrieval")):
                evidence_relevant_organs.append(capability_id)
            if _strip(item.get("cost_hint")).lower() in {"low", "medium"}:
                cost_sensitive_organs.append(capability_id)
            if normalized_intent and normalized_intent in when_to_use:
                candidate_organs_for_turn.append(capability_id)
            if _strip(item.get("capability_kind")) == "surface":
                surface_constraints.append(f"{capability_id}:{availability}")

        recommended_organs.extend(self._recommended_organs_for_turn(normalized_intent, requirements))
        candidate_organs_for_turn.extend(self._candidate_organs_for_turn(normalized_intent, requirements))

        return {
            "capabilities_by_id": capabilities_by_id,
            "available_organs": sorted(set(available_organs)),
            "healthy_organs": sorted(set(healthy_organs)),
            "blocked_organs": sorted(set(blocked_organs)),
            "candidate_organs_for_turn": sorted(set(candidate_organs_for_turn)),
            "surface_constraints": sorted(set(surface_constraints)),
            "evidence_relevant_organs": sorted(set(evidence_relevant_organs)),
            "cost_sensitive_organs": sorted(set(cost_sensitive_organs)),
            "recommended_organs": sorted(set(recommended_organs)),
            "model_catalog": model_catalog,
            "models_by_tier": {tier: list(ids) for tier, ids in models_by_tier.items()},
        }

    def select(
        self,
        *,
        body_map: dict[str, Any] | None,
        capability_requirements: dict[str, Any] | None,
        route_intent: str | None,
        mode_strategy: dict[str, Any] | None = None,
        route_decision: dict[str, Any] | None = None,
        current_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        requirements = _as_dict(capability_requirements)
        body_map = _as_dict(body_map)
        mode_strategy = _as_dict(mode_strategy)
        route_decision = _as_dict(route_decision)
        current_context = _as_dict(current_context)
        normalized_intent = _strip(route_intent).lower()

        selected_capabilities: list[dict[str, Any]] = []
        rejected_capabilities: list[dict[str, Any]] = []
        selection_rationale: list[str] = []
        fallback_plan: list[dict[str, Any]] = []
        bounded_adjustments: list[dict[str, Any]] = []
        audit_notes: list[str] = []
        degraded_selection_notes: list[str] = []

        retrieval_result = self._select_retrieval(
            body_map=body_map,
            capability_requirements=requirements,
            route_intent=normalized_intent,
            current_context=current_context,
        )
        specialist_result = self._select_specialist(
            body_map=body_map,
            capability_requirements=requirements,
            route_intent=normalized_intent,
            current_context=current_context,
        )
        model_result = self._select_model(
            body_map=body_map,
            capability_requirements=requirements,
        )

        selected_capabilities.extend(retrieval_result["selected_capabilities"])
        selected_capabilities.extend(specialist_result["selected_capabilities"])
        selected_capabilities.extend(model_result["selected_capabilities"])

        rejected_capabilities.extend(retrieval_result["rejected_capabilities"])
        rejected_capabilities.extend(specialist_result["rejected_capabilities"])
        rejected_capabilities.extend(model_result["rejected_capabilities"])

        selection_rationale.extend(retrieval_result["selection_rationale"])
        selection_rationale.extend(specialist_result["selection_rationale"])
        selection_rationale.extend(model_result["selection_rationale"])

        fallback_plan.extend(retrieval_result["fallback_plan"])
        fallback_plan.extend(specialist_result["fallback_plan"])
        fallback_plan.extend(model_result["fallback_plan"])

        degraded_selection_notes.extend(retrieval_result["degraded_selection_notes"])
        degraded_selection_notes.extend(specialist_result["degraded_selection_notes"])
        degraded_selection_notes.extend(model_result["degraded_selection_notes"])

        planning_depth = _strip(requirements.get("planning_depth_required")).lower()
        if planning_depth == "light" and normalized_intent in {"chat", "plan", "planning"}:
            bounded_adjustments.append(
                {
                    "field": "session_mode",
                    "recommended_value": "guided" if _strip(mode_strategy.get("strategy_mode")) != "recovery" else "recovery",
                    "target_layer": "session",
                    "reversible": True,
                    "reason": "The simpler path should stay easy to follow for this turn.",
                    "source": "capability_selection_policy",
                }
            )
        if _strip(current_context.get("experience_mode")).lower() == "stabilize":
            bounded_adjustments.append(
                {
                    "field": "intervention_intensity",
                    "recommended_value": "low",
                    "target_layer": "session",
                    "reversible": True,
                    "reason": "Stabilization contexts should keep the intervention reversible and light.",
                    "source": "capability_selection_policy",
                }
            )
        if retrieval_result["summary"]["retrieval_mode"] in {"user_materials_first", "user_materials_tool_only"}:
            bounded_adjustments.append(
                {
                    "field": "retrieval_emphasis",
                    "recommended_value": "user_materials",
                    "target_layer": "session",
                    "reversible": True,
                    "reason": "Grounded material support should stay aligned with user materials for this turn.",
                    "source": "capability_selection_policy",
                }
            )

        why_this_path = self._build_why_this_path(
            retrieval_result=retrieval_result,
            specialist_result=specialist_result,
            model_result=model_result,
        )

        summary = {
            "retrieval_mode": retrieval_result["summary"]["retrieval_mode"],
            "specialist_strategy": specialist_result["summary"]["specialist_strategy"],
            "preferred_model_tier": model_result["summary"]["preferred_model_tier"],
            "selected_model_capability_id": model_result["summary"]["selected_model_capability_id"],
            "selected_experts": list(specialist_result["summary"]["selected_experts"]),
            "degraded_selection": bool(degraded_selection_notes),
        }
        body_awareness_guidance = self._build_legacy_guidance(
            retrieval_result=retrieval_result,
            specialist_result=specialist_result,
            body_map=body_map,
            selection_rationale=selection_rationale,
        )

        audit_notes.extend(self._build_rejected_path_audit(rejected_capabilities))
        if route_decision:
            audit_notes.append(f"route_decision_reason={_strip(route_decision.get('reason'))}")
        audit_notes.extend(f"degraded:{note}" for note in degraded_selection_notes)

        return {
            "selected_capabilities": selected_capabilities,
            "rejected_capabilities": rejected_capabilities,
            "selection_rationale": selection_rationale,
            "fallback_plan": fallback_plan,
            "bounded_adjustments": self._dedupe_adjustments(bounded_adjustments),
            "audit_notes": audit_notes,
            "degraded_selection_notes": degraded_selection_notes,
            "summary": summary,
            "why_this_path": why_this_path,
            "body_awareness_guidance": body_awareness_guidance,
            "model_selection": {
                "preferred_tier": model_result["summary"]["preferred_model_tier"],
                "selected_capability_id": model_result["summary"]["selected_model_capability_id"],
                "cost_band": _strip(requirements.get("cost_band")).lower() or "balanced",
                "fallback_used": bool(model_result["fallback_plan"]),
            },
            "tool_selection": {
                "retrieval_mode": retrieval_result["summary"]["retrieval_mode"],
                "selected_capability_id": retrieval_result["summary"]["selected_retrieval_capability_id"],
                "inject_query_knowledge": retrieval_result["summary"]["selected_retrieval_capability_id"] == "tool:query_knowledge",
                "ground_with_user_materials": retrieval_result["summary"]["selected_retrieval_capability_id"] in {
                    "path:user_material_grounding",
                    "tool:retrieve_user_material",
                },
            },
            "specialist_selection": {
                "strategy": specialist_result["summary"]["specialist_strategy"],
                "selected_experts": list(specialist_result["summary"]["selected_experts"]),
                "fallback_used": bool(specialist_result["fallback_plan"]),
            },
        }

    def choose_pre_context_tools(
        self,
        *,
        route_intent: str | None,
        user_message: str,
        requested_tools: list[str] | None,
    ) -> list[str]:
        requested = [str(item).strip() for item in _as_list(requested_tools) if str(item).strip()]
        lowered = user_message.lower()
        if route_intent in {"knowledge", "learn", "review", "translation"} and "query_knowledge" not in requested:
            requested.append("query_knowledge")
        if any(marker in lowered for marker in ("upload", "uploaded", "笔记", "资料", "notes", "slides")):
            if "query_knowledge" not in requested:
                requested.append("query_knowledge")
        return requested

    def apply_availability_overrides(
        self,
        *,
        body_map: dict[str, Any],
        blocked_capability_ids: list[str] | None = None,
        degraded_capability_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        body_map = {
            key: (dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value)
            for key, value in _as_dict(body_map).items()
        }
        capabilities_by_id = {
            capability_id: dict(item)
            for capability_id, item in _as_dict(body_map.get("capabilities_by_id")).items()
            if isinstance(item, dict)
        }
        blocked_ids = {str(item).strip() for item in _as_list(blocked_capability_ids) if str(item).strip()}
        degraded_ids = {str(item).strip() for item in _as_list(degraded_capability_ids) if str(item).strip()}
        available = {
            str(item).strip()
            for item in _as_list(body_map.get("available_organs"))
            if str(item).strip()
        }
        healthy = {
            str(item).strip()
            for item in _as_list(body_map.get("healthy_organs"))
            if str(item).strip()
        }
        blocked = {
            str(item).strip()
            for item in _as_list(body_map.get("blocked_organs"))
            if str(item).strip()
        }

        for capability_id in blocked_ids:
            available.discard(capability_id)
            healthy.discard(capability_id)
            blocked.add(capability_id)
            if capability_id in capabilities_by_id:
                capabilities_by_id[capability_id]["availability"] = "blocked"
        for capability_id in degraded_ids:
            if capability_id in blocked:
                continue
            available.add(capability_id)
            healthy.discard(capability_id)
            if capability_id in capabilities_by_id:
                capabilities_by_id[capability_id]["availability"] = "degraded"

        body_map["capabilities_by_id"] = capabilities_by_id
        body_map["available_organs"] = sorted(available)
        body_map["healthy_organs"] = sorted(healthy)
        body_map["blocked_organs"] = sorted(blocked)
        return body_map

    def _select_retrieval(
        self,
        *,
        body_map: dict[str, Any],
        capability_requirements: dict[str, Any],
        route_intent: str,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        grounding_required = _strip(capability_requirements.get("grounding_required")).lower()
        selected_capabilities: list[dict[str, Any]] = []
        rejected_capabilities: list[dict[str, Any]] = []
        selection_rationale: list[str] = []
        fallback_plan: list[dict[str, Any]] = []
        degraded_selection_notes: list[str] = []

        can_degrade_grounding = grounding_required not in {"mandatory"} or bool(
            current_context.get("allow_grounding_degradation")
        )
        if grounding_required in {"mandatory", "required_from_profile"}:
            preferred_chain = [
                "path:user_material_grounding",
                "tool:retrieve_user_material",
            ]
            if can_degrade_grounding:
                preferred_chain.append("tool:query_knowledge")
            preferred_chain.append("path:no_retrieval")
        elif grounding_required == "helpful" or route_intent in {"knowledge", "learn", "review", "translation"}:
            preferred_chain = [
                "tool:query_knowledge",
                "path:no_retrieval",
            ]
        else:
            preferred_chain = ["path:no_retrieval"]

        chosen_id, fallback_reason = self._choose_capability_from_chain(
            body_map=body_map,
            preferred_chain=preferred_chain,
        )
        retrieval_mode = self._retrieval_mode_for_capability(chosen_id)
        selected_capabilities.append(
            {
                "capability_id": chosen_id,
                "decision_class": "retrieval",
                "selection_mode": "hard_governed",
            }
        )

        if chosen_id == "path:user_material_grounding":
            selection_rationale.append("The live body could satisfy grounded user-material retrieval directly.")
        elif chosen_id == "tool:retrieve_user_material":
            selection_rationale.append("The primary grounding path was unavailable, so the selector fell back to the available user-material retrieval tool.")
            degraded_selection_notes.append("Grounding downgraded from the dedicated path to the retrieval tool.")
        elif chosen_id == "tool:query_knowledge":
            selection_rationale.append("The selector fell back to light knowledge retrieval because user-material grounding was unavailable.")
            degraded_selection_notes.append("Grounding degraded to general knowledge retrieval.")
        else:
            selection_rationale.append("No authorized retrieval organ could satisfy this turn, so the selector stayed on a bounded no-retrieval fallback.")
            if grounding_required in {"mandatory", "required_from_profile"}:
                degraded_selection_notes.append("Mandatory grounding could not be satisfied by the live body.")

        for capability_id in preferred_chain:
            if capability_id == chosen_id:
                continue
            rejection_reason = self._capability_unavailability_reason(body_map, capability_id)
            if not rejection_reason and preferred_chain.index(capability_id) < preferred_chain.index(chosen_id):
                rejection_reason = "preferred_but_replaced_by_available_fallback"
            if rejection_reason:
                rejected_capabilities.append(
                    {
                        "capability_id": capability_id,
                        "decision_class": "retrieval",
                        "reason": rejection_reason,
                    }
                )

        if fallback_reason:
            fallback_plan.append(
                {
                    "decision_class": "retrieval",
                    "preferred_capability_id": preferred_chain[0],
                    "reason": fallback_reason,
                    "fallback_capability_id": chosen_id,
                    "requirement_satisfaction": self._retrieval_satisfaction(chosen_id, grounding_required),
                }
            )

        return {
            "selected_capabilities": selected_capabilities,
            "rejected_capabilities": rejected_capabilities,
            "selection_rationale": selection_rationale,
            "fallback_plan": fallback_plan,
            "degraded_selection_notes": degraded_selection_notes,
            "summary": {
                "retrieval_mode": retrieval_mode,
                "selected_retrieval_capability_id": chosen_id,
            },
        }

    def _select_specialist(
        self,
        *,
        body_map: dict[str, Any],
        capability_requirements: dict[str, Any],
        route_intent: str,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        selected_capabilities: list[dict[str, Any]] = []
        rejected_capabilities: list[dict[str, Any]] = []
        selection_rationale: list[str] = []
        fallback_plan: list[dict[str, Any]] = []
        degraded_selection_notes: list[str] = []

        if not bool(capability_requirements.get("specialization_required")):
            selected_capabilities.append(
                {
                    "capability_id": "subsystem:chat_orchestrator",
                    "decision_class": "specialist",
                    "selection_mode": "hard_governed",
                }
            )
            rejected_capabilities.append(
                {
                    "capability_id": "path:specialist_expert_path",
                    "decision_class": "specialist",
                    "reason": "specialist_not_needed",
                }
            )
            selection_rationale.append("A simple orchestrator path is sufficient for this turn.")
            return {
                "selected_capabilities": selected_capabilities,
                "rejected_capabilities": rejected_capabilities,
                "selection_rationale": selection_rationale,
                "fallback_plan": fallback_plan,
                "degraded_selection_notes": degraded_selection_notes,
                "summary": {
                    "specialist_strategy": "simple_path",
                    "selected_experts": [],
                },
            }

        preferred_experts = self._preferred_specialists(current_context=current_context, route_intent=route_intent)
        live_preferred = [capability_id for capability_id in preferred_experts if self._is_available(body_map, capability_id)]
        live_compatible = [
            capability_id
            for capability_id in self._compatible_specialists(route_intent=route_intent, preferred_experts=preferred_experts)
            if self._is_available(body_map, capability_id)
        ]
        path_available = self._is_available(body_map, "path:specialist_expert_path")

        if path_available and live_preferred:
            selected_capabilities.append(
                {
                    "capability_id": "path:specialist_expert_path",
                    "decision_class": "specialist",
                    "selection_mode": "hard_governed",
                }
            )
            for capability_id in live_preferred:
                selected_capabilities.append(
                    {
                        "capability_id": capability_id,
                        "decision_class": "specialist",
                        "selection_mode": "hard_governed",
                    }
                )
            blocked_preferred = [
                capability_id for capability_id in preferred_experts if capability_id not in live_preferred
            ]
            for capability_id in blocked_preferred:
                rejected_capabilities.append(
                    {
                        "capability_id": capability_id,
                        "decision_class": "specialist",
                        "reason": self._capability_unavailability_reason(body_map, capability_id) or "specialist_unavailable",
                    }
                )
            selection_rationale.append("The live body supports the specialist path and at least one preferred specialist agent.")
            return {
                "selected_capabilities": selected_capabilities,
                "rejected_capabilities": rejected_capabilities,
                "selection_rationale": selection_rationale,
                "fallback_plan": fallback_plan,
                "degraded_selection_notes": degraded_selection_notes,
                "summary": {
                    "specialist_strategy": "specialist_required",
                    "selected_experts": [self._agent_id_from_capability(item) for item in live_preferred],
                },
            }

        if path_available and live_compatible:
            selected_capabilities.append(
                {
                    "capability_id": "path:specialist_expert_path",
                    "decision_class": "specialist",
                    "selection_mode": "hard_governed",
                }
            )
            selected_capabilities.append(
                {
                    "capability_id": live_compatible[0],
                    "decision_class": "specialist",
                    "selection_mode": "hard_governed",
                }
            )
            fallback_plan.append(
                {
                    "decision_class": "specialist",
                    "preferred_capability_id": preferred_experts[0] if preferred_experts else "path:specialist_expert_path",
                    "reason": "preferred_specialist_unavailable",
                    "fallback_capability_id": live_compatible[0],
                    "requirement_satisfaction": "partial",
                }
            )
            degraded_selection_notes.append("Specialist path stayed live, but the preferred specialist was unavailable.")
            selection_rationale.append("The selector kept the specialist path but downgraded to the best available compatible expert.")
            for capability_id in preferred_experts:
                if capability_id not in {live_compatible[0]}:
                    rejected_capabilities.append(
                        {
                            "capability_id": capability_id,
                            "decision_class": "specialist",
                            "reason": self._capability_unavailability_reason(body_map, capability_id) or "preferred_specialist_replaced",
                        }
                    )
            return {
                "selected_capabilities": selected_capabilities,
                "rejected_capabilities": rejected_capabilities,
                "selection_rationale": selection_rationale,
                "fallback_plan": fallback_plan,
                "degraded_selection_notes": degraded_selection_notes,
                "summary": {
                    "specialist_strategy": "fallback_specialist",
                    "selected_experts": [self._agent_id_from_capability(live_compatible[0])],
                },
            }

        selected_capabilities.append(
            {
                "capability_id": "subsystem:chat_orchestrator",
                "decision_class": "specialist",
                "selection_mode": "hard_governed",
            }
        )
        rejected_capabilities.append(
            {
                "capability_id": "path:specialist_expert_path",
                "decision_class": "specialist",
                "reason": self._capability_unavailability_reason(body_map, "path:specialist_expert_path") or "no_compatible_specialist_available",
            }
        )
        for capability_id in preferred_experts:
            rejected_capabilities.append(
                {
                    "capability_id": capability_id,
                    "decision_class": "specialist",
                    "reason": self._capability_unavailability_reason(body_map, capability_id) or "no_compatible_specialist_available",
                }
            )
        fallback_plan.append(
            {
                "decision_class": "specialist",
                "preferred_capability_id": "path:specialist_expert_path",
                "reason": "specialist_path_or_agents_unavailable",
                "fallback_capability_id": "subsystem:chat_orchestrator",
                "requirement_satisfaction": "not_satisfied",
            }
        )
        degraded_selection_notes.append("Specialist reasoning was required but the live body could not supply a compatible specialist.")
        selection_rationale.append("The selector fell back to the simple orchestrator path because the specialist path was not live.")
        return {
            "selected_capabilities": selected_capabilities,
            "rejected_capabilities": rejected_capabilities,
            "selection_rationale": selection_rationale,
            "fallback_plan": fallback_plan,
            "degraded_selection_notes": degraded_selection_notes,
            "summary": {
                "specialist_strategy": "simple_path",
                "selected_experts": [],
            },
        }

    def _select_model(
        self,
        *,
        body_map: dict[str, Any],
        capability_requirements: dict[str, Any],
    ) -> dict[str, Any]:
        cost_band = _strip(capability_requirements.get("cost_band")).lower() or "balanced"
        preferred_tiers = list(self._COST_BAND_TO_TIERS.get(cost_band, self._COST_BAND_TO_TIERS["balanced"]))
        selected_capabilities: list[dict[str, Any]] = []
        rejected_capabilities: list[dict[str, Any]] = []
        selection_rationale: list[str] = []
        fallback_plan: list[dict[str, Any]] = []
        degraded_selection_notes: list[str] = []

        model_catalog = _as_dict(body_map.get("model_catalog"))
        models_by_tier = {
            _strip(tier): [str(item).strip() for item in _as_list(ids) if str(item).strip()]
            for tier, ids in _as_dict(body_map.get("models_by_tier")).items()
        }
        chosen_id = self._choose_model_in_tiers(
            body_map=body_map,
            model_catalog=model_catalog,
            models_by_tier=models_by_tier,
            tier_order=preferred_tiers,
        )
        used_fallback = False
        if not chosen_id:
            fallback_tiers = [
                tier for tier in self._FALLBACK_TIER_ORDER if tier not in preferred_tiers
            ]
            chosen_id = self._choose_model_in_tiers(
                body_map=body_map,
                model_catalog=model_catalog,
                models_by_tier=models_by_tier,
                tier_order=fallback_tiers,
            )
            used_fallback = True

        if not chosen_id:
            chosen_id = next(iter(model_catalog.keys()), "")

        selected_capabilities.append(
            {
                "capability_id": chosen_id,
                "decision_class": "model_tier",
                "selection_mode": "hard_governed",
            }
        )
        selected_tier = _strip(_as_dict(model_catalog.get(chosen_id)).get("tier")).lower()
        selected_tier_index = preferred_tiers.index(selected_tier) if selected_tier in preferred_tiers else -1
        higher_priority_candidates = [
            capability_id
            for tier in preferred_tiers[:selected_tier_index]
            for capability_id in models_by_tier.get(tier, [])
        ]
        if used_fallback or selected_tier not in preferred_tiers:
            fallback_plan.append(
                {
                    "decision_class": "model_tier",
                    "preferred_capability_id": f"cost_band:{cost_band}",
                    "reason": "no_live_model_in_cost_band",
                    "fallback_capability_id": chosen_id,
                    "requirement_satisfaction": "partial",
                }
            )
            degraded_selection_notes.append("The selector had to leave the preferred cost band because no live model was available inside it.")
            selection_rationale.append("No healthy in-band model was available, so the selector chose the closest live fallback model.")
        elif higher_priority_candidates:
            fallback_plan.append(
                {
                    "decision_class": "model_tier",
                    "preferred_capability_id": higher_priority_candidates[0],
                    "reason": "higher_priority_in_band_model_unavailable",
                    "fallback_capability_id": chosen_id,
                    "requirement_satisfaction": "full",
                }
            )
            selection_rationale.append(
                "The selector stayed inside the cost band but downgraded to the best live in-band model because a higher-priority model was unavailable."
            )
        else:
            selection_rationale.append(f"The selector chose a live model inside the {cost_band} cost band.")

        higher_cost_models = [
            capability_id
            for capability_id, model in model_catalog.items()
            if self._tier_cost_rank(_strip(model.get("tier")).lower()) > self._tier_cost_rank(selected_tier)
        ]
        for capability_id in higher_cost_models[:3]:
            rejected_capabilities.append(
                {
                    "capability_id": capability_id,
                    "decision_class": "model_tier",
                    "reason": "higher_cost_than_selected_model",
                }
            )

        return {
            "selected_capabilities": selected_capabilities,
            "rejected_capabilities": rejected_capabilities,
            "selection_rationale": selection_rationale,
            "fallback_plan": fallback_plan,
            "degraded_selection_notes": degraded_selection_notes,
            "summary": {
                "preferred_model_tier": selected_tier or preferred_tiers[0],
                "selected_model_capability_id": chosen_id,
            },
        }

    def _choose_capability_from_chain(
        self,
        *,
        body_map: dict[str, Any],
        preferred_chain: list[str],
    ) -> tuple[str, str | None]:
        for index, capability_id in enumerate(preferred_chain):
            if not capability_id:
                continue
            if self._is_blocked(body_map, capability_id):
                continue
            if self._is_available(body_map, capability_id):
                fallback_reason = None
                if index > 0:
                    fallback_reason = self._capability_unavailability_reason(body_map, preferred_chain[0]) or "preferred_capability_unavailable"
                return capability_id, fallback_reason
        return preferred_chain[-1], "preferred_capability_unavailable"

    def _choose_model_in_tiers(
        self,
        *,
        body_map: dict[str, Any],
        model_catalog: dict[str, Any],
        models_by_tier: dict[str, list[str]],
        tier_order: list[str],
    ) -> str:
        for tier in tier_order:
            candidates = list(models_by_tier.get(tier, []))
            if not candidates:
                continue
            healthy_candidates = [capability_id for capability_id in candidates if self._is_healthy(body_map, capability_id)]
            available_candidates = [capability_id for capability_id in candidates if self._is_available(body_map, capability_id)]
            ordered_candidates = healthy_candidates or available_candidates
            if ordered_candidates:
                ordered_candidates.sort(
                    key=lambda capability_id: (
                        float(_as_dict(model_catalog.get(capability_id)).get("cost_per_1k_tokens") or 0.0),
                        float(_as_dict(model_catalog.get(capability_id)).get("avg_latency_ms") or 0.0),
                    )
                )
                return ordered_candidates[0]
        return ""

    def _compatible_specialists(self, *, route_intent: str, preferred_experts: list[str]) -> list[str]:
        ordered = list(dict.fromkeys([*preferred_experts, *self._DEFAULT_SPECIALIST_ORDER]))
        if route_intent == "prediction":
            ordered = list(dict.fromkeys(["agent:deep_analyst", *ordered]))
        if route_intent == "error_diagnosis":
            ordered = list(dict.fromkeys(["agent:error_analyst", "agent:deep_analyst", *ordered]))
        return ordered

    def _preferred_specialists(self, *, current_context: dict[str, Any], route_intent: str) -> list[str]:
        preferred: list[str] = []
        raw_preferred = current_context.get("preferred_specialists")
        if isinstance(raw_preferred, list):
            for item in raw_preferred:
                normalized = _strip(item)
                if not normalized:
                    continue
                preferred.append(normalized if normalized.startswith("agent:") else f"agent:{normalized}")
        query = _strip(current_context.get("query")).lower()
        if any(marker in query for marker in ("error", "debug", "报错", "根因")):
            preferred.append("agent:error_analyst")
        if any(marker in query for marker in ("math", "积分", "方程", "热力学")):
            preferred.append("agent:math_agent")
        if route_intent == "prediction":
            preferred.append("agent:deep_analyst")
        if not preferred:
            preferred = self._compatible_specialists(route_intent=route_intent, preferred_experts=[])
        return list(dict.fromkeys(preferred))

    def _build_why_this_path(
        self,
        *,
        retrieval_result: dict[str, Any],
        specialist_result: dict[str, Any],
        model_result: dict[str, Any],
    ) -> str:
        retrieval_capability = retrieval_result["summary"]["selected_retrieval_capability_id"]
        specialist_strategy = specialist_result["summary"]["specialist_strategy"]
        selected_model_capability_id = model_result["summary"]["selected_model_capability_id"]
        if retrieval_capability == "path:user_material_grounding":
            return "Used your materials first because this turn needed grounded evidence."
        if specialist_strategy in {"specialist_required", "fallback_specialist"} and specialist_result["summary"]["selected_experts"]:
            return (
                f"Escalated to {specialist_result['summary']['selected_experts'][0]} "
                "because the request matched a specialist problem pattern."
            )
        if selected_model_capability_id and model_result["summary"]["preferred_model_tier"] == ModelTier.FAST.value:
            return "Stayed on a lighter live model because a fast-enough path was sufficient."
        return ""

    def _build_legacy_guidance(
        self,
        *,
        retrieval_result: dict[str, Any],
        specialist_result: dict[str, Any],
        body_map: dict[str, Any],
        selection_rationale: list[str],
    ) -> dict[str, Any]:
        retrieval_capability_id = retrieval_result["summary"]["selected_retrieval_capability_id"]
        specialist_strategy = specialist_result["summary"]["specialist_strategy"]
        selected_experts = specialist_result["summary"]["selected_experts"]
        if retrieval_capability_id in {"path:user_material_grounding", "tool:retrieve_user_material", "tool:query_knowledge"}:
            primary_subsystem = {
                "id": "galaxy",
                "label": "Galaxy Knowledge Systems",
                "why": "This turn stays grounded through the live retrieval organ family.",
            }
        elif specialist_strategy in {"specialist_required", "fallback_specialist"}:
            primary_subsystem = {
                "id": "chat_orchestrator",
                "label": "Chat Orchestrator",
                "why": "The orchestrator should coordinate the specialist path for this turn.",
            }
        else:
            primary_subsystem = {
                "id": "chat_orchestrator",
                "label": "Chat Orchestrator",
                "why": "A simpler orchestration path is sufficient for this turn.",
            }

        supporting_subsystems = []
        if retrieval_capability_id in {"path:user_material_grounding", "tool:retrieve_user_material", "tool:query_knowledge"}:
            supporting_subsystems.append(
                {
                    "id": "galaxy",
                    "label": "Galaxy Knowledge Systems",
                    "why": "Retrieval remains relevant even when the orchestrator owns the user-facing answer.",
                }
            )
        if specialist_strategy in {"specialist_required", "fallback_specialist"}:
            supporting_subsystems.extend(
                {
                    "id": expert_id,
                    "label": expert_id,
                    "why": "Selected as a live specialist for this turn.",
                }
                for expert_id in selected_experts
            )

        evidence_sources = ["conversation"]
        if retrieval_capability_id in {"path:user_material_grounding", "tool:retrieve_user_material"}:
            evidence_sources.append("user_materials")
        elif retrieval_capability_id == "tool:query_knowledge":
            evidence_sources.append("knowledge")

        return {
            "primary_subsystem": primary_subsystem,
            "supporting_subsystems": supporting_subsystems,
            "activation_surfaces": [],
            "evidence_sources": evidence_sources,
            "bounded_knob_decisions": [],
            "grounding_priority": ["user_materials"] if "user_materials" in evidence_sources else ["general_knowledge"],
            "cost_posture": "medium" if "user_materials" in evidence_sources else "low",
            "risk_notes": list(_as_list(body_map.get("blocked_organs"))[:2]),
            "rights_note": selection_rationale[0] if selection_rationale else "System choice remains bounded and reversible.",
        }

    def _recommended_organs_for_turn(
        self,
        normalized_intent: str,
        requirements: dict[str, Any],
    ) -> list[str]:
        recommended: list[str] = []
        if _strip(requirements.get("grounding_required")).lower() in {"mandatory", "required_from_profile"}:
            recommended.extend(["path:user_material_grounding", "tool:retrieve_user_material"])
        elif _strip(requirements.get("grounding_required")).lower() == "helpful" or normalized_intent in {"knowledge", "learn", "review", "translation"}:
            recommended.append("tool:query_knowledge")
        if bool(requirements.get("specialization_required")):
            recommended.append("path:specialist_expert_path")
        if normalized_intent in {"community", "accountability", "group"}:
            recommended.append("surface:community")
        return recommended

    def _candidate_organs_for_turn(
        self,
        normalized_intent: str,
        requirements: dict[str, Any],
    ) -> list[str]:
        candidates = ["subsystem:chat_orchestrator"]
        if normalized_intent in {"knowledge", "learn", "review", "translation"}:
            candidates.extend(["tool:query_knowledge", "subsystem:galaxy"])
        if _strip(requirements.get("grounding_required")).lower() in {"mandatory", "required_from_profile"}:
            candidates.extend(["path:user_material_grounding", "tool:retrieve_user_material"])
        if bool(requirements.get("specialization_required")):
            candidates.append("path:specialist_expert_path")
        return candidates

    def _retrieval_mode_for_capability(self, capability_id: str) -> str:
        if capability_id == "path:user_material_grounding":
            return "user_materials_first"
        if capability_id == "tool:retrieve_user_material":
            return "user_materials_tool_only"
        if capability_id == "tool:query_knowledge":
            return "light_query_knowledge"
        return "no_retrieval"

    def _retrieval_satisfaction(self, capability_id: str, grounding_required: str) -> str:
        if capability_id == "path:user_material_grounding":
            return "full"
        if capability_id == "tool:retrieve_user_material":
            return "partial" if grounding_required == "mandatory" else "full"
        if capability_id == "tool:query_knowledge":
            return "partial"
        return "not_satisfied"

    def _capability_unavailability_reason(self, body_map: dict[str, Any], capability_id: str) -> str:
        if self._is_blocked(body_map, capability_id):
            return "blocked_in_live_body"
        if not self._is_available(body_map, capability_id):
            return "not_available_in_live_body"
        if not self._is_healthy(body_map, capability_id):
            return "degraded_in_live_body"
        return ""

    def _is_available(self, body_map: dict[str, Any], capability_id: str) -> bool:
        capability_id = _strip(capability_id)
        return capability_id in {
            str(item).strip()
            for item in _as_list(body_map.get("available_organs"))
            if str(item).strip()
        }

    def _is_healthy(self, body_map: dict[str, Any], capability_id: str) -> bool:
        capability_id = _strip(capability_id)
        return capability_id in {
            str(item).strip()
            for item in _as_list(body_map.get("healthy_organs"))
            if str(item).strip()
        }

    def _is_blocked(self, body_map: dict[str, Any], capability_id: str) -> bool:
        capability_id = _strip(capability_id)
        return capability_id in {
            str(item).strip()
            for item in _as_list(body_map.get("blocked_organs"))
            if str(item).strip()
        }

    @staticmethod
    def _tier_cost_rank(tier: str) -> int:
        ordered = {
            ModelTier.FAST.value: 1,
            ModelTier.STANDARD.value: 2,
            ModelTier.PLUS.value: 3,
            ModelTier.PRO.value: 4,
            ModelTier.MAX.value: 5,
        }
        return ordered.get(tier, 99)

    @staticmethod
    def _agent_id_from_capability(capability_id: str) -> str:
        normalized = _strip(capability_id)
        if normalized.startswith("agent:"):
            return normalized.split(":", 1)[1]
        return normalized

    @staticmethod
    def _dedupe_adjustments(adjustments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in adjustments:
            field = _strip(item.get("field"))
            value = _strip(item.get("recommended_value"))
            layer = _strip(item.get("target_layer"))
            key = (field, value, layer)
            if not field or key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _build_rejected_path_audit(rejected_capabilities: list[dict[str, Any]]) -> list[str]:
        audit_entries: list[str] = []
        for item in rejected_capabilities:
            decision_class = _strip(item.get("decision_class"))
            capability_id = _strip(item.get("capability_id"))
            if decision_class in {"retrieval", "specialist", "model_tier"} and capability_id:
                audit_entries.append(f"rejected:{decision_class}:{capability_id}")
        return audit_entries
