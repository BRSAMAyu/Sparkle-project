# Sparkle Body Map and Capability Registry Spec

> Date: 2026-04-04  
> Scope: Pack 4 / Phase D substrate

## Goal

Turn Sparkle from a pile of available organs into one coherent capability surface that the AI can reason over safely.

## Registry Shape

Every capability entry should declare:

- `id`
- `label`
- `kind`
- `purpose`
- `state`
- `cost_hint`
- `permissions`
- `read_scope`
- `write_scope`
- `when_to_use`
- `when_not_to_use`

## Current Runtime Sources

- Models: `LLMRouter`
- Agents: `AgentProfileRegistry`
- Tools: `DynamicToolRegistry`
- Public modes: `get_public_mode_catalog()`
- High-level subsystems: static curated registry until live health probes are reliable

## Required Registry Sections

- Models
- Agents
- Modes
- Tools
- Subsystems
- Configuration layers
- System-layer knobs
- Rights model

## Rights Model

- Constitutional layer is readable, not silently writable.
- Session layer is writable when changes are reversible.
- Episode layer is writable only through evidence-gated promotion.
- Profile layer is writable only through repeated evidence and conflict resolution.
- System layer is future-bounded and must only operate through explicit registry-declared knobs.

## Runtime Artifact

The first runtime artifact is the backend capability registry service and body-map endpoint:

- Service: `backend/app/services/capability_registry_service.py`
- API: `GET /api/v1/multi-agent/body-map`

## Near-Term Use Cases

- Let orchestration inspect which agents, tools, and model tiers exist before acting.
- Let Sparkle explain, internally, why it chose one subsystem instead of another.
- Gate future system-layer self-configuration behind declared permissions and costs.

## Non-Goal

This registry is not permission to let Sparkle rewrite itself freely. It is the structured precondition for bounded, auditable system awareness.
