# SPARKLE Aurora Stage 10 EVD1 Evidence ID Resolution (2026-04-20)

> **Status**: pre-implementation artifact for `WS-EVD1`
> **Purpose**: freeze the claim-to-`L0` evidence resolution path before clickable evidence lands in the profile front door.

## 1. Why This Exists

Stage 9 made profile claims legible by evidence class, but not yet clickable by concrete raw evidence references.
Stage 10 upgrades that gap without leaking non-raw internal state.

## 2. Core Rule

**Clickable evidence must resolve to allowed `L0` evidence references or explicit redaction states, not to `L1 / L2 / L3` internals pretending to be facts.**

## 3. Resolution Path

```mermaid
flowchart LR
    C["Profile Claim / Prediction"] --> M["Evidence Ref Mapping"]
    M --> R["Existing Evidence Resolve API"]
    R --> L["Allowed L0 Payload or Redaction"]
    L --> U["Chat / Mobile Clickable Evidence Surface"]
```

## 4. Allowed Evidence Shapes

Initial Stage 10 allowed evidence refs may reuse the current evidence resolver's supported `L0`-or-raw-facing types:

1. `event`
2. `user_state`
3. `error`
4. `concept`
5. `strategy`
6. `task`
7. `nightly_review` if already supported by the resolver path during implementation

Any unsupported ref must degrade to:

1. `not_found`
2. `redacted`
3. `unsupported_ref`

## 5. Mapping Discipline

Stage 10 may synthesize claim-linked evidence refs from:

1. transparency payload source markers
2. known front-door source families
3. explicit correction records already represented as raw-facing refs

Stage 10 may not synthesize fake raw ids for:

1. compiled claims
2. inference-only projections
3. Aurora / L3 metadata

## 6. User-Facing Contract

Each clickable claim or prediction may expose:

1. `evidence_refs`
2. `evidence_resolution`
3. `evidence_summary`
4. `evidence_cta`

If no resolvable refs exist, the payload must say so honestly.

## 7. Privacy Boundary

The resolution surface must preserve:

1. per-user access checks
2. deleted-content redaction
3. unsupported-type redaction

The front door may display a compact excerpt or typed payload summary, but must not dump unrelated raw internals.

## 8. Minimum Acceptance Shape

`WS-EVD1` is accepted only if:

1. at least one canonical profile claim exposes clickable evidence refs
2. the refs resolve through the existing evidence resolve seam or a direct extension of that seam
3. redacted / missing cases remain explicit
4. payload advertises `l0_clickable_refs` rather than `source_markers_only`
