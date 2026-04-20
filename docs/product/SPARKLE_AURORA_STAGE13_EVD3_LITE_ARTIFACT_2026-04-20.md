# SPARKLE Aurora Stage 13 WS-EVD3-LITE Artifact (2026-04-20)

> **Workstream**: `WS-EVD3-LITE`
> **Purpose**: add one new safe evidence type without touching any continuous-learning write lane.

## 1. Single New Evidence Type

`practice_outcome`

This evidence represents the user's latest review result for an error-book item.

## 2. Backend Boundary

### 2.1 Memory-Layer Write Path

Inside `ErrorBookService.submit_review()`:

1. keep the existing review scheduler and mastery sync flow unchanged
2. create one `EpisodicMemory` record with:
   - `source_type = "practice_outcome"`
   - `source_id = str(error.id)`
   - summary describing the review outcome
   - tags carrying the review performance marker
3. do not create or depend on a new event-bus event

### 2.2 Allowed Evidence Types

Extend `ALLOWED_EVIDENCE_TYPES` with:

- `practice_outcome`

### 2.3 Evidence Resolve Path

Resolver contract:

1. accept `EvidenceRef(type="practice_outcome", id=<error_id>)`
2. verify that a memory-layer `practice_outcome` record exists for that error
3. return a `practice_outcome` payload that includes:
   - `error_id`
   - `subject_code`
   - `review_performance`
   - `mastery_level`
   - `review_count`
   - `reviewed_at`
   - `summary`

### 2.4 Profile Front Door Legibility

The front door may expose `practice_outcome` refs only through the existing evidence-card drawer.

It must also add a new `evidence_legend` row:

- `id = "practice_outcome"`
- label and description following the Stage 10 EVD1 style

## 3. Frontend Boundary

`evidence_cards.dart` may add one narrow type branch:

1. render the `practice_outcome` payload
2. route through existing `onRouteTap`
3. route target:
   - `/errors/:id`

No broad refactor is allowed.

## 4. User-Visible Entry Path

To make the new type reachable without opening a new product surface:

1. reviewed error evidence in the profile front door may include `practice_outcome` refs ahead of raw `error` refs
2. unresolved or unsupported practice outcome refs must not silently masquerade as raw error evidence

## 5. Safety Statement

This work remains outside the continuous-learning lane because:

1. the only new write is a memory-layer episodic record
2. no learner or `strategy_store` receives the new type
3. no Aurora write lane is opened
4. the route target reuses the existing error-book detail screen

## 6. Proof Points

Backend proof:

1. `submit_review()` creates the memory-layer record
2. evidence resolve returns `practice_outcome`

Frontend proof:

1. widget test renders the new payload
2. widget test routes `/errors/:id`
3. unsupported evidence remains non-routable
