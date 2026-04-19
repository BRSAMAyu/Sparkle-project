# SPARKLE Aurora Stage 10 Dispatch Plan (2026-04-20)

> **Status**: Stage 10 dispatch baseline v0 after Stage 9 final-accept
> **Authority**: `SPARKLE_AURORA_STAGE9_HANDOFF_2026-04-20.md` is the only Stage 9 truth source; this plan starts from that frozen baseline and must not reopen completed Stage 5 / Stage 6 / Stage 7 / Stage 8 / Stage 9 work.
> **Depends on**:
> - `SPARKLE_VISION_ANCHOR_LIST_2026-04-19.md`
> - `SPARKLE_USER_MODEL_LAYERED_ARCHITECTURE_2026-04-19.md`
> - `SPARKLE_AURORA_STAGE9_HANDOFF_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE10_EV3_LLM_JUDGE_CONTRACT_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE10_EVD1_EVIDENCE_ID_RESOLUTION_2026-04-20.md`
> - `SPARKLE_AURORA_STAGE10_G2D_DIAGNOSTIC_SURFACE_SCOPE_2026-04-20.md`
> **Scope**: Stage 10 execution design. Converts Stage 9's explicit leftovers into dispatchable deepening workstreams without widening write authority.

## 0. Stage 10 Positioning

Stage 9 made the profile system chat-native.
Stage 10 exists to deepen trust and diagnostic power around those already-landed seams.

### One-sentence definition

**Stage 10 is the stage where Sparkle's chat-native front door becomes evidence-clickable, evaluator-backed, and graph-diagnostic without opening any new truth-write lanes.**

### What Stage 10 must treat as already settled

The following are frozen baseline facts unless new regression evidence proves otherwise:

1. chat-native profile read exists through `get_profile_front_door`
2. chat-native profile correction exists through the User Correction lane only
3. `WS-IC2` is structurally isolated from Aurora / L3 / strategy lane
4. evaluator outputs remain read-only with `write_scope = evaluation_records_only`
5. prompt / inference utilization has a formal Stage 9 carrier

### Stage 10 starting gaps

Per Stage 9 handoff and accepted Stage 10 design notes, Stage 10 starts from exactly three work items:

1. `WS-EV3` real LLM-judge wiring on top of the Stage 9 evaluator hook
2. `WS-EVD1` upgrade from source markers to clickable `L0`-traceable evidence references
3. `WS-G2D` graph-as-diagnostic productization as a user-visible "where am I weak" surface

## 1. Rule Layering Marker

Stage 10 keeps the Stage 9 governance set intact and only adds the new rules required by the new risk surfaces.

| Category | Rules | Essence |
| --- | --- | --- |
| write | `K / N / P` | who may write, where they may write, and how violations are blocked |
| closure | `G / I / J` | single-WS commits, handoff completeness, and user-value closure |
| boundary | `H / M / O` | allowlists, compiler count, and no silent whitelist expansion |
| runtime | `L / R` | consumer / runner closure and evaluator read-only discipline |
| readability | `Q` | evidence must stay legible |
| stage-10 additions | `S / T` | LLM-judge isolation and graph diagnostic read-only discipline |

No merge or rewrite is attempted in Stage 10. If Stage 10 / 11 add more rules, Stage 12 becomes the first consolidation point.

## 2. Stage 10 Principles

### Principle A: Deepen Existing Seams Before Inventing New Ones

Stage 10 must stand on the structures landed in Stage 9:

1. `WS-EV3` extends the current `ProfileEvalRunner`
2. `WS-EVD1` extends the current canonical front door payload
3. `WS-G2D` consumes current galaxy / graph / mastery data instead of creating a second graph stack

### Principle B: Clickable Evidence Must Still Respect Truth Boundaries

Making evidence clickable is not permission to leak raw internal inference state.

### Principle C: Diagnostic Surfaces Consume, They Do Not Mutate

Stage 10 may explain weakness, risk, and next review targets, but it may not create a new write plane from those explanations.

### Principle D: LLM-Judge Is a Reader, Not a Writer

The judge may grade, summarize, and attach rationale inside evaluation records only.

### Principle E: Productization Must Stay Honest

If a graph diagnosis is based on mastery score and dependency structure, the UI and payload must say so.
If a claim is backed by `L0` evidence ids, the payload must say so.
If an evaluator score is a rubric-plus-judge blend, the payload must say so.

## 3. Explicitly Out of Scope

The following are not Stage 10 scope unless a later amendment says otherwise:

1. continuous-learning / distillation user-facing rollout
2. dual interaction mode rollout
3. new truth-write lanes from graph surfaces
4. evaluator-triggered writes outside `evaluation_records_only`
5. profile correction redesign
6. bounded-steering whitelist expansion
7. graph-powered interventions that bypass existing correction or intervention lanes

## 4. Workstream Overview

| Workstream | Focus | Primary lane | User value | Priority | Risk |
| --- | --- | --- | --- | --- | --- |
| `WS-EV3` | real LLM-judge wiring | evaluation | indirect but trust-critical | highest | medium |
| `WS-EVD1` | clickable evidence resolution | canonical front door read path | high | highest | medium |
| `WS-G2D` | graph-as-diagnostic surface | graph / galaxy read path | high | high | high |

### Wave Order

1. `WS-EV3` closes first because it is the narrowest seam and unlocks stronger diagnostic confidence.
2. `WS-EVD1` may implement in parallel once its path document is frozen.
3. `WS-G2D` may not start implementation until its scope artifact is committed.

Hard interpretation:

1. `WS-G2D` cannot enter implementation before the scope artifact lands.
2. `WS-EV3` must keep graceful downgrade to `rubric_only`.
3. `WS-EVD1` must resolve only to allowed `L0` evidence shapes or explicit redactions.

## 5. Dispatch Rules

Stage 10 inherits Rule G, Rule H, Rule I, Rule J, Rule K, Rule L, Rule M, Rule N, Rule O, Rule P, Rule Q, and Rule R.

### Rule S · LLM-Judge Output Isolation

Any LLM-judge output may only write inside evaluation records.

Hard interpretation:

1. `WS-EV3` may not write `L0`, `L1`, `L2`, `L3`, profile, preference, or strategy state
2. the LLM-judge prompt contract must be artifact-locked before code lands
3. if the judge is unavailable, the runner must degrade to `rubric_only` rather than fail closed
4. the evaluator payload must declare whether scoring is `rubric_only` or `llm_attached`

### Rule T · Graph Diagnostic Read-Only Discipline

Graph-as-diagnostic may consume current graph and mastery data only.

Hard interpretation:

1. `WS-G2D` may not add a new write channel
2. any follow-up action from the diagnostic surface must route through an already-existing lane
3. graph diagnosis may recommend, navigate, or prompt, but not mutate truth

## 6. Review Lanes

| Workstream | Review lane | Reason |
| --- | --- | --- |
| `WS-EV3` | medium-risk | first real LLM-judge attachment but still evaluation-only |
| `WS-EVD1` | medium-risk | user-visible evidence deepening with privacy / redaction boundaries |
| `WS-G2D` | high-risk | new product surface with graph-derived weak-point diagnosis |

### Stage 10 high-risk triggers

Any task touching one of the following is automatically high-risk:

1. new graph-diagnostic API routes
2. any graph surface attempting to write mastery / preference / strategy state
3. any evaluator path attempting to persist outside evaluation records
4. any evidence-resolution path attempting to expose `L1 / L2 / L3` internals as if they were raw facts

## 7. Hotspot Ownership

| File / Zone | Owner | Reason |
| --- | --- | --- |
| `backend/app/services/profile_eval_runner.py` | `WS-EV3` | Stage 9 left the real judge hook unconnected |
| `backend/app/services/llm_service.py` and evaluation helper seam | `WS-EV3` | real judge attachment must stay explicit and degradable |
| `backend/app/services/profile_front_door_service.py` | `WS-EVD1` | current payload still says `source_markers_only` |
| `backend/app/tools/growth_strategy_tools.py` | `WS-EVD1` | chat front door tool should return richer evidence links |
| `backend/app/api/v1/events.py` and evidence-resolve seam | `WS-EVD1` | existing resolver is the safest L0 read path to reuse |
| `backend/app/services/graph_reasoning_service.py` | `WS-G2D` | existing mastery / dependency read seam |
| `backend/app/api/v1/galaxy.py` | `WS-G2D` | likely user-facing graph diagnostic read route |
| `mobile/lib/features/chat/presentation/widgets/profile_front_door_card.dart` | `WS-EVD1` | clickable evidence surface |
| `mobile/lib/features/galaxy/` | `WS-G2D` | graph-diagnostic mobile surface |
| `docs/product/*STAGE10*` | `Codex` | sequencing, boundary artifacts, and closeout integration |

## 8. Workstream Cards

## 8.1 `WS-EV3` — Real LLM-Judge Wiring

**Goal**

Attach a real LLM judge to the existing Stage 9 evaluator hook and preserve `evaluation_records_only`.

**In-scope**

- real judge adapter on top of `ProfileEvalRunner(llm_judge=...)`
- contract-locked prompt and IO schema
- weighted `rubric 70 / judge 30` scoring path
- explicit downgrade to `rubric_only` when judge is disabled or unavailable
- tests for attached and downgraded modes

**Out-of-scope**

- writing any profile truth
- using judge outputs to mutate prompts, profile, or strategy state
- hidden prompt mutation outside the committed artifact

**Accept requires**

1. the judge contract artifact lands before code
2. the runner still reports `write_scope = evaluation_records_only`
3. attached mode is real, not a test-only lambda
4. disabled / unavailable mode degrades cleanly to `rubric_only`

## 8.2 `WS-EVD1` — Clickable Evidence Resolution

**Goal**

Upgrade in-chat profile claims from source markers to clickable evidence references that resolve to allowed `L0` evidence items.

**In-scope**

- claim / prediction payloads gain evidence refs or evidence ids
- payload declares `evidence_resolution = l0_clickable_refs`
- chat card supports evidence drill-down
- evidence resolution uses existing resolve APIs and explicit redaction states

**Out-of-scope**

- exposing raw `L1 / L2 / L3` inference internals as fact
- bypassing the current evidence resolver
- redesigning the correction lane

**Accept requires**

1. the evidence path artifact lands before code
2. at least one real front-door claim includes clickable refs
3. redacted / missing evidence is represented honestly
4. mobile tests prove evidence drill-down works

## 8.3 `WS-G2D` — Graph-as-Diagnostic Surface

**Goal**

Turn current galaxy / graph infrastructure into a user-visible "where am I weak" diagnostic surface.

**In-scope**

- graph-derived weak / at-risk / learning / strong slices based on current read data
- at least one user-facing payload and one mobile rendering path
- diagnostic answer path that can support prompts like "我哪里弱"
- navigation / recommendation affordances that stay inside existing lanes

**Out-of-scope**

- new graph write channels
- direct mastery mutation from the diagnostic surface
- continuous-learning rollout

**Accept requires**

1. the scope artifact lands before code
2. graph diagnosis consumes current graph / mastery services only
3. at least one end-to-end user scenario works
4. no new write plane exists

## 9. Entry Gate

Stage 10 may start only if the following Stage 9 baseline still holds:

1. Stage 9 frozen backend baseline remains `144 passed`
2. Stage 9 backend sweep remains `27 passed`
3. Stage 9 mobile sweep remains `15 tests passed`
4. Rule K guard remains `35 files scanned, 0 violations`

## 10. Close Gate

Stage 10 may claim closure only if:

1. all three workstreams are accepted
2. Stage 9 frozen baseline still passes
3. Stage 10 backend and mobile sweeps pass
4. handoff includes:
   - a real EV3 judge sample
   - a real clickable evidence sample
   - a real graph diagnostic sample
5. no Rule S or Rule T violation is introduced
