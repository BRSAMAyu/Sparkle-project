# Sparkle Phase D Body Awareness Contract

> Date: 2026-04-05  
> Scope: Durable Phase D v1 runtime contracts for body awareness and capability governance after the fallback-enforcement pass

## CapabilityRegistryEntry

- `capability_id`: stable canonical id such as `model:xiaomi_chat`, `agent:error_analyst`, `tool:query_knowledge`, `subsystem:galaxy`, `surface:community`, `path:specialist_expert_path`, `knob:retrieval_emphasis`
- `label`: human-readable label
- `capability_kind`: `model`, `agent`, `tool`, `subsystem`, `surface`, `orchestration_path`, `retrieval_path`, or `knob`
- `purpose`: concise operational purpose
- `availability`: current availability state
- `quality_hint`, `latency_hint`, `cost_hint`: bounded decision hints, not promises
- `read_scope`, `write_scope`: declared rights surface
- `required_preconditions`: conditions that must be true before selection
- `when_to_use`, `when_not_to_use`: explicit selection boundaries
- `rights_model`: runtime rights framing
- `reversible`: whether the capability choice or knob change is reversible in v1
- `declared_knobs`: bounded knobs related to that capability

Canonical source:
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_registry_service.py`

Compatibility guarantee:
- `build_registry()` keeps returning `models`, `agents`, `tools`, `subsystems`, `system_layer_knobs`, and other existing compatibility views.
- `schema_version` is frozen at `phase_d.v1` for this pass.

## CompiledBodyMap

- `capabilities_by_id`
- `available_organs`
- `healthy_organs`
- `blocked_organs`
- `candidate_organs_for_turn`
- `surface_constraints`
- `evidence_relevant_organs`
- `cost_sensitive_organs`
- `recommended_organs`
- `model_catalog`
- `models_by_tier`

Runtime sources:
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/capability_selection_policy.py`
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/situation_brief.py`

## CapabilityRequirementProfile

- `planning_depth_required`
- `grounding_required`
- `material_dependency`
- `specialization_required`
- `latency_sensitivity`
- `adaptation_visibility_required`
- `bounded_adjustments_allowed`
- `cost_band`
- `forbidden_paths`

Compiler source:
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/capability_requirement_compiler.py`

## CapabilitySelectionReport

- `selected_capabilities`
  Canonical-only capability selections. Every `capability_id` must join back to the registry.
- `rejected_capabilities`
  Canonical-only rejected paths with explicit reasons such as blocked, unavailable, or replaced by an authorized fallback.
- `selection_rationale`
- `fallback_plan`
  Each fallback entry contains:
  - `decision_class`
  - `preferred_capability_id`
  - `reason`
  - `fallback_capability_id`
  - `requirement_satisfaction`
- `bounded_adjustments`
- `audit_notes`
- `degraded_selection_notes`
- `summary`
  Includes compact derived fields such as:
  - `retrieval_mode`
  - `specialist_strategy`
  - `preferred_model_tier`
  - `selected_model_capability_id`
  - `selected_experts`
  - `degraded_selection`
- `why_this_path`
- `model_selection`
- `tool_selection`
- `specialist_selection`
- `body_awareness_guidance`

Selection source:
- `/Users/brsama/code/GitHub/Sparkle-project/backend/app/orchestration/capability_selection_policy.py`

Compatibility guarantee:
- `decision_context["body_awareness_guidance"]` remains available as a projection of the selection report.
- `SituationBrief` now also carries `body_map`, `capability_requirements`, and `capability_selection`.
- Human-readable summaries such as `retrieval_mode`, `specialist_strategy`, and `preferred_model_tier` remain derived metadata only. They are not canonical identifiers.
