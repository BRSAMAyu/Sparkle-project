# Sparkle Phase D Contract Freeze

> Date: 2026-04-05  
> Scope: Stable Phase D runtime contracts after the durability pass, with the earlier provisional freeze now re-confirmed by strict fallback-aware evaluation

## Freeze Status

- previous state: `provisional`
- current state: `frozen_for_v1`
- freeze gate:
  - live-body selector enforcement implemented
  - canonical capability IDs unified across registry, body map, selector, evaluator, and response metadata
  - strict-runtime blocked-organ regression pack passing

## Stable Interfaces

Treat these as stable Phase D interfaces until a later explicit phase changes them with a compatibility note:

- `schema_version = phase_d.v1`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/backend/app/services/capability_registry_service.py`
- `CapabilityRegistryEntry`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/docs/contracts/phase_d_body_awareness_contract.md`
- `CompiledBodyMap`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/docs/contracts/phase_d_body_awareness_contract.md`
- `CapabilityRequirementProfile`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/docs/contracts/phase_d_body_awareness_contract.md`
- `CapabilitySelectionReport`
  Source: `/Users/brsama/code/GitHub/Sparkle-project/docs/contracts/phase_d_body_awareness_contract.md`
- canonical capability identifiers
  `model:<model_key>`, `agent:<agent_id>`, `tool:<tool_name>`, `subsystem:<subsystem_id>`, `surface:<surface_id>`, `path:<path_id>`, `knob:<knob_id>`
- D6 allowlist
  `retrieval_emphasis`, `session_mode`, `intervention_intensity`, `explanation_style`, `difficulty_level`, `push_vs_support`

## Governance Freeze

Phase D v1 hard-governs these runtime decisions:

- user-material grounding vs lighter retrieval
- specialist escalation vs simple path
- model-tier selection within the allowed cost band, including in-band and cross-band fallback reporting when the preferred live model is unavailable

Phase D v1 keeps these areas advisory or soft-guided:

- visible surface activation for `community`, `achievements`, `visual_bgm`
- broader execution-path promotion beyond existing runtime checks
- episode/profile strategy writes outside the already evidence-gated outcome-promotion flows

## Change Policy

- Field additions require a short compatibility note and Phase D regression updates.
- Field renames or removals are disallowed unless a later phase defines a migration plan.
- `decision_context["body_awareness_guidance"]` remains a compatibility projection and must not be removed in Phase D v1.
- No new persistent strategy knobs may be added without a later explicit governance phase.
- `capability_selection_evaluator.py` remains a regression harness v1, not a substitute for live product evaluation or human review.
