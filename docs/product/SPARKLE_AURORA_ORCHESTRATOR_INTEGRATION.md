# SPARKLE Aurora Orchestrator Integration Contract

> **Status**: Wave 0 contract, frozen for WS1/WS5 implementation
> **Depends on**: `SPARKLE_AURORA_GATE0_SCHEMA_2026-04-17.md`
> **Feature gates**: `AURORA_SHADOW_MODE`, `AURORA_ACTIVE`, `INTERACTION_VARIANTS`

## 1. Scope

Aurora is a control bus, not a response renderer. The orchestrator may call Aurora at three explicit FSM edges:

1. `pre-node-routing`
2. `pre-tool-selection`
3. `pre-response-formatting`

Aurora consumes `SignalSnapshot` plus the current orchestration context and returns schema-shaped outputs only. User-facing text still comes from the interaction layer.

## 2. Trigger Points

### 2.1 `pre-node-routing`

Call this after the snapshot is assembled and before the graph chooses the next node.

Use it for:

- stay vs transition decisions
- proactive initiation decisions
- initial impact assessment
- focus/window updates when a material state change is needed

### 2.2 `pre-tool-selection`

Call this after the node is selected and before tool permissions are finalized.

Use it for:

- capability gating
- window adjustments
- reinforcing or narrowing the current focus
- late material correction if the selected node is still safe but needs a tighter frame

### 2.3 `pre-response-formatting`

Call this after the response skeleton exists and before rendering.

Use it for:

- inference knob tuning
- capability gating for the interaction layer
- UX intent and Aurora presence selection

This edge must not change graph state.

## 3. Output Matrix

Legend:

- `R` = expected/required if Aurora is invoked at that edge
- `O` = optional
- `-` = not allowed at that edge

### 3.1 Direct Aurora Returns (6 outputs)

These are the six schema-shaped outputs returned directly from Aurora deliberation and consumed by the orchestrator / interaction layer.

| Aurora output | pre-node-routing | pre-tool-selection | pre-response-formatting |
| --- | --- | --- | --- |
| `ImpactClass` | R | O | O |
| `TransitionDecisionRecord` | R | O | - |
| `InferenceKnobs` | O | R | R |
| `CapabilityGate` | O | R | R |
| `UXIntent` | O | O | R |
| `AuroraPresenceLevel` | O | O | R |

### 3.2 Ledger Side-Effect Primitives

These are append-only primitives that Aurora may cause SignalProcessor to write after deliberation. They are not part of the direct six-output return contract.

| Primitive | pre-node-routing | pre-tool-selection | pre-response-formatting |
| --- | --- | --- | --- |
| `FocusContract` (new version) | Allowed | Allowed | Forbidden |
| `WindowState` (new record) | Allowed | Allowed | Forbidden |
| `InsightClaim` (new or update) | Allowed | Allowed | Allowed |
| `ProbeOutcome` (new record) | Allowed | Allowed | Allowed |
| `IdentityEvidence` (new record) | Allowed | Allowed | Allowed |

Implementation note:

- `pre-node-routing` is the only edge that may create a new `TransitionDecisionRecord` that changes the node.
- `pre-tool-selection` may emit a decision record only when the selected node or window needs a material correction before tools are finalized.
- `pre-response-formatting` must never mutate focus or window state.
- `IdentityEvidence` is persisted as its own ledger-backed table (`identity_evidence`), not folded into `InsightClaim`.

## 4. Shadow vs Active

### 4.1 Shadow mode

Shadow mode is enabled when `AURORA_SHADOW_MODE=true` and `AURORA_ACTIVE=false`.

Behavior:

- Aurora runs alongside the legacy path.
- Outputs are written to shadow storage or logs only.
- The orchestrator never blocks on a shadow result past the soft budget.
- A missing shadow result must not affect the user path.

### 4.2 Active mode

Active mode is enabled when `AURORA_ACTIVE=true`.

Behavior:

- Aurora outputs are allowed to drive routing and write-path updates.
- The orchestrator waits for Aurora only within the edge budget.
- If Aurora returns an invalid payload, times out, or cannot load policy, the orchestrator falls back to the legacy path and stays on the current node.

`INTERACTION_VARIANTS` is an allowlist for the interaction layer. If the selected variant is not enabled, the orchestrator must fall back to `default_conversation`.

## 5. Wait Strategy

Budgets are per edge and should be treated as hard upper bounds for the active path. Shadow waits should be shorter and never user-visible.

| Trigger point | Shadow soft budget | Shadow hard budget | Active soft budget | Active hard budget |
| --- | --- | --- | --- | --- |
| `pre-node-routing` | 100 ms | 200 ms | 500 ms | 900 ms |
| `pre-tool-selection` | 75 ms | 150 ms | 250 ms | 500 ms |
| `pre-response-formatting` | 50 ms | 120 ms | 120 ms | 240 ms |

Rules:

- If the soft budget expires in shadow mode, cancel the wait and continue.
- If the hard budget expires in active mode, fall back to the legacy path and emit an internal alert.
- Timeout handling must not surface as an exception to the orchestrator caller.

## 6. Minimal Call Contract

The orchestrator should pass the following shape to Aurora:

- `snapshot`
- `policy_version`
- `trigger_point`
- `current_node`
- `candidate_node` when available
- `mode` (`shadow` or `active`)
- `prior_outputs` when a later edge is chained to an earlier Aurora result

Aurora returns schema objects only. The orchestrator is responsible for persistence, routing, and rendering.

`prior_outputs` is a chained-read envelope for later edges. It may contain only direct Aurora returns from earlier edges in the same request cycle:

- `pre-tool-selection` may read `ImpactClass` and `TransitionDecisionRecord` from `pre-node-routing`
- `pre-response-formatting` may read `ImpactClass`, `TransitionDecisionRecord`, `InferenceKnobs`, and `CapabilityGate` produced earlier in the same cycle
- `prior_outputs` expires at the end of the request cycle and must not be reused across turns

## 7. WS1/WS5 Implementation Boundary

WS1 may implement decision logic against this contract, but it must not change the contract shape.

WS5 may render `ux_intent`, `aurora_presence`, and the interaction-model variant selected from the policy registry, but it must not infer its own routing semantics.
