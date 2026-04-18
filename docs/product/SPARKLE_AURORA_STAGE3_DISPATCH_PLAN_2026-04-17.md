# SPARKLE Stage 3 — Parallel Dispatch Plan

> **Version**: 1.1 (incorporating Claude + Codex Wave 0 review)
> **Date**: 2026-04-17
> **Status**: ACTIVE
> **Depends on**: `SPARKLE_AURORA_GATE0_SCHEMA_2026-04-17.md` (v1.0-frozen)
> **Constitutional principle**: "可治理优于更聪明" (Governability over cleverness)

---

## 0. Hard Rules (All Workstreams MUST Follow)

### Rule A: File Ownership

Every workstream declares exclusive-write directories/files. No two workstreams may write the same file. If a shared file must be modified, ONE workstream owns the modification and others consume via import. Conflicts = re-cut the workstream.

### Rule B: Interrupt Point Semantics

Every task card declares its interrupt state:
- `deployable`: can ship at any completion %
- `behind_flag`: compiles and runs but is inert until feature flag flipped
- `atomic`: must reach 100% or it's broken; requires branch isolation

No task without this declaration may be assigned.

### Rule C: Gate 0 Schema Authority

All Pydantic models from Gate 0 (11 primitives + 18 enums) are frozen. Workstreams implement against these schemas — they do not modify them. Schema changes require a formal Gate 0.1 amendment.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FLUTTER (Presentation)                 │
│  Mirror Bar │ Chat UI │ Profile UI │ Scenario Pack UI    │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket + gRPC
┌──────────────────────────┴──────────────────────────────┐
│                    GO GATEWAY (Coordination)              │
│  Auth │ WS Proxy │ Routing │ Rate Limit                  │
└──────────────────────────┬──────────────────────────────┘
                           │ gRPC
┌──────────────────────────┴──────────────────────────────┐
│                 PYTHON ENGINE (Intelligence)               │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Aurora     │  │  Interaction │  │  Scenario Pack   │ │
│  │   Runtime    │→ │  Layer       │  │  System          │ │
│  │  (Control)   │  │  (Variants)  │  │  (Templates)     │ │
│  └──────┬───────┘  └──────────────┘  └──────────────────┘ │
│         │ reads/writes via                              │
│  ┌──────┴───────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Signal     │  │  Graph       │  │  Social Layer    │ │
│  │  Pipeline    │  │  Runtime     │  │  (Accountability) │ │
│  │ (Aggregator  │  │ (Node/Edge/  │  │  (Partners)      │ │
│  │  +Processor) │  │  Transition) │  │                  │ │
│  └──────┬───────┘  └──────────────┘  └──────────────────┘ │
│         │                                                 │
│  ┌──────┴───────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │  Continuous  │  │  Profile &   │  │  Aurora          │ │
│  │  Learning    │  │  Transparent │  │  Observability   │ │
│  │  (Distill)   │  │  (Mirror)    │  │  (Monitoring)    │ │
│  └──────────────┘  └──────────────┘  └──────────────────┘ │
└───────────────────────────────────────────────────────────┘
         ↕ PostgreSQL 16 + pgvector    ↕ Redis Stack
```

---

## 2. Mid-Flight Migration Strategy

**Decision: Shadow → Gradual Cutover (option b→c)**

### Phase M1: Shadow Mode
- Aurora + new systems run in parallel, reading existing data
- All new system outputs go to shadow tables (not production)
- Users continue on existing path; no behavior change
- Validation: compare Aurora decisions against existing dual-core-router decisions

### Phase M2: Gradual Cutover
- Users opt-in or are auto-selected when `UserScenarioState.pack_id` is set (i.e., they enter a Scenario Pack)
- Users without a pack remain on legacy path
- Migration is per-user, not global

### Phase M3: Legacy Deprecation
- After all users migrated, legacy dual-core-router and expert system are deprecated
- Old code remains behind feature flags for 30 days, then removed

### Migration Data Map

| Legacy | New | Migration Action |
|--------|-----|-----------------|
| `UserInsightState` | `InsightClaim` + `SparkleRelationshipState` | One-time ETL: extract claims from insight signals |
| `dual_core_router.py` | `Aurora Runtime` | Shadow comparison, then swap |
| `agent_profiles.py` | `ScenarioPackManifest.NodeConfig` | Compile into first pack |
| `expert_auto` | `Aurora.impact_class` + node routing | Route through Aurora |
| Seed Library | `DistilledStrategy` | Import with `source: human_authored` |
| Existing profile data | `UserScenarioState` | Backfill from current profile tables |

---

## 3. Wave Plan

```
WAVE 0 (Foundation) — 4-5 days
  ├─ W0.1: Deploy Gate 0 schemas to codebase (Pydantic models)
  ├─ W0.2: DB migration for new tables (with verified downgrade paths)
  ├─ W0.3: Feature flag infrastructure for shadow mode
  ├─ W0.4: Common utilities (enum imports, base classes)
  ├─ W0.5: Reference flow test harness skeleton (WS8-T1 front-loaded)
  └─ W0.6: Orchestrator ↔ Aurora integration contract document (WS1-T9 front-loaded)

WAVE 1 (Core Engine) — 10-14 days
  ├─ WS1: Aurora Runtime (control plane)
  ├─ WS2: Graph Runtime (node/edge/transition)
  ├─ WS3: Signal Pipeline (aggregator + processor + ledger)
  └─ WS10: Aurora Observability (runtime monitoring)

WAVE 2 (User Experience) — 10-14 days
  ├─ WS4: Scenario Pack System
  ├─ WS5: Interaction Layer (multi-variant models)
  ├─ WS6: Profile & Mirror Bar (transparent profile + mirror bar UI)
  └─ WS9: Social Layer (accountability partners)

WAVE 3 (Evolution & Validation) — 7-10 days
  ├─ WS7: Continuous Learning (DistilledStrategy pipeline)
  ├─ WS8: End-to-end Integration & Validation
  └─ WS-M: Migration execution (shadow → cutover)

TOTAL ESTIMATE: 30-42 days
```

---

## 4. Workstream Definitions

### WS1: Aurora Runtime

**Goal**: Implement the Aurora control plane as a pure decision function.

**Exclusive Write Directories**:
- `backend/app/aurora/` (new)
  - `engine.py` — main deliberation loop
  - `decision_fns/` — deterministic rules
  - `bayesian/` — Bayesian update modules
  - `llm_bridge.py` — LLM call interface (for hybrid/LLM decisions)
  - `policy_loader.py` — loads AuroraPolicyVersion
  - `config.py` — Aurora-specific configuration

**Read-Only Dependencies**:
- `backend/app/orchestration/dual_core_router.py` (shadow comparison only)
- All Gate 0 schema models (from `backend/app/aurora/schemas/`)

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS1-T0 | Author `AuroraPolicyVersion v1.0` initial content as YAML fixture at `backend/app/aurora/policies/v1.0.yaml`. Must include all sub-policies with initial values + rationale. | `deployable` | Policy loads via policy_loader, all decision functions find required thresholds |
| WS1-T1 | Create `backend/app/aurora/` module structure with schema imports | `deployable` | Module loads, schemas importable |
| WS1-T2 | Implement deterministic decision functions for backbone routing (stay on current node unless strong signal) | `behind_flag` | Unit test: given SignalSnapshot + no-conflict → stay decision |
| WS1-T3 | Implement materiality check (signal vs threshold from policy) | `deployable` | Unit test: low-impact message → skip; commitment conflict → pass |
| WS1-T4 | Implement Aurora.deliberate() main loop: input snapshot → policy lookup → decision function → emit TDR + Claims | `atomic` | Integration test: full deliberation produces valid TDR with all mandatory fields |
| WS1-T5 | Implement 3-tier trigger (reactive/scheduled/on_demand) dispatch | `deployable` | Unit tests per trigger type |
| WS1-T6 | Implement policy loader (read AuroraPolicyVersion from DB/config) | `deployable` | Loads v1.0 policy with all sub-policies |
| WS1-T7 | Shadow comparison mode: run Aurora alongside dual_core_router, log agreement/divergence | `behind_flag` | Shadow comparison runs for 100 test scenarios, produces diff report |
| WS1-T8 | Implement Aurora fallback decision: any deliberation failure (timeout / policy missing / snapshot corrupted / LLM error) → emit `TransitionDecisionRecord(decision_type=NO_OP, decision_basis=fallback, decision_mechanism=deterministic)` + stay on current node + alert to observability. No uncaught exceptions to orchestrator. | `deployable` | Unit test: corrupt snapshot → fallback TDR emitted, no exception propagated |
| WS1-T9 | Define and document orchestrator ↔ Aurora integration contract at `docs/product/SPARKLE_AURORA_ORCHESTRATOR_INTEGRATION.md`. Specify: (a) which FSM edges trigger Aurora (pre-node-routing, pre-tool-selection, pre-response-formatting); (b) 6 outputs × 3 trigger points matrix; (c) shadow vs active call differences; (d) timeout/wait strategy. | `deployable` | Contract doc reviewed and signed off before WS1-T4 implementation |

**Validation**: Run 3 Gate 0 reference flows through Aurora.deliberate(). Each produces correctly structured output.

---

### WS2: Graph Runtime

**Goal**: Implement production graph engine with node/edge/transition primitives.

**Exclusive Write Directories**:
- `backend/app/graph/` (new)
  - `runtime.py` — graph execution engine
  - `nodes.py` — node base class and implementations
  - `transitions.py` — transition policy engine
  - `backbone.py` — backbone path resolver
  - `focus_contract_manager.py` — FocusContract lifecycle
  - `commitment_engine.py` — Commitment lifecycle + window management

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS2-T1 | Define Node/Edge base abstractions matching NodeConfig schema | `deployable` | Node base class loads from ScenarioPackManifest.backbone_nodes |
| WS2-T2 | Implement backbone path resolver (given current node → default next node) | `deployable` | Unit test: day3 → day4 on exam_prep_14d backbone |
| WS2-T3 | Implement transition policy engine (evaluate transition conditions from node config) | `deployable` | Unit test: strong signal → off-backbone transition allowed |
| WS2-T4 | Implement FocusContract lifecycle (create, version, lookup current) | `deployable` | Unit test: version chain builds correctly, O(1) current lookup |
| WS2-T5 | Implement Commitment lifecycle + WindowState management | `deployable` | Unit test: pending→active→fulfilled; window override per commitment |
| WS2-T6 | Integrate with Aurora: graph runtime receives TDR decisions, executes node transitions | `atomic` | Integration test: Aurora TDR with transition → graph executes, FocusContract versions increment |
| WS2-T7 | Implement rollback: given rollback_anchor, restore FocusContract + Commitment state | `behind_flag` | Unit test: rollback restores previous state correctly |

**Validation**: Exam prep backbone (14 nodes) loads and executes. User can traverse day1→day14 with correct node transitions.

---

### WS3: Signal Pipeline

**Goal**: Implement SignalAggregator (input) + SignalProcessor (output) + Ledger management.

**Exclusive Write Directories**:
- `backend/app/aurora/signal_aggregator.py` (new)
- `backend/app/aurora/signal_processor.py` (new)
- `backend/app/aurora/ledger.py` (new)

**Read-Only Dependencies**:
- All existing service files (`memory_service.py`, `cognitive_service.py`, `achievement_engine.py`, etc.)

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS3-T1 | Implement SignalSnapshot assembler: pull from 9 existing services, tier signals (core/enhanced/optional), compute freshness | `deployable` | Produces valid SignalSnapshot with hash, all 3 tiers populated |
| WS3-T2 | Implement budget management: total snapshot ≤ budget_limit, prioritize by tier | `deployable` | Test: 10K tokens of signals → trimmed to budget with core preserved |
| WS3-T3 | Implement SignalProcessor: consume Aurora output (TDR + Claims), execute writes to downstream | `atomic` | Integration test: TDR with commitment update → Commitment table updated |
| WS3-T4 | Implement Ledger manager: append-only writes for all primitives, query by user_id/time range | `deployable` | Can write and read back FocusContract, Commitment, TDR, Claim records |
| WS3-T5 | Implement InsightClaim lifecycle manager (open→probed→confirmed/refuted/contextualized) | `deployable` | Unit test: claim created → probe outcome received → status updated |
| WS3-T6 | Implement dev-facing rollback CLI: read ledger + execute rollback by decision_id | `behind_flag` | CLI tool can list decisions and execute rollback, creating rollback_event record |
| WS3-T7 | Fix existing prompt pipeline data leakage (render error_summary, recent_errors, recent_mastery_changes in prompts.py) | `deployable` | Before/after test: context dict 75% → prompt rendered 75%+ (up from ~50%). All new Alembic migrations have verified downgrade paths tested on throwaway DB. |

**Validation**: SignalSnapshot produced for test user. Aurora receives it and produces valid decision. SignalProcessor executes the decision's writes.

---

### WS4: Scenario Pack System

**Goal**: Implement ScenarioPackManifest CRUD + first pack (14-day exam prep) + readiness criteria.

**Exclusive Write Directories**:
- `backend/app/scenario_packs/` (new)
  - `registry.py` — pack CRUD
  - `exam_prep_14d.py` — first pack definition
  - `readiness.py` — readiness criteria evaluator
- `backend/app/aurora/schemas/` (for pack-related Pydantic models only)

**Read-Only Dependencies**:
- `backend/app/core/agent_profiles.py` (migrate FROM, not modify)

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS4-T1 | Implement ScenarioPackManifest CRUD (load, list, get by id) | `deployable` | Pack loads from YAML/JSON config |
| WS4-T2 | Define exam_prep_14d@v1.0 pack: 14 backbone nodes, readiness criteria, node configs | `deployable` | Pack validates against ScenarioPackManifest schema |
| WS4-T3 | Migrate expert content: extract top 5 expert prompts from agent_profiles.py → compile into exam pack node configs | `deployable` | Node configs contain migrated persona + prompt data |
| WS4-T4 | Implement readiness evaluator: given user signals + pack.readiness_criteria → ready/not_ready + missing signals | `deployable` | Test: user with 3/5 criteria → not ready, lists missing 2 |
| WS4-T5 | Implement pack-aware context assembly: when user has active pack, prioritize pack-relevant context in SignalSnapshot | `behind_flag` | Test: exam pack active → task completion signals promoted to core tier |

**Validation**: Full exam_prep_14d pack loads. User with complete readiness criteria passes check. User without is directed to conversational modeling.

---

### WS5: Interaction Layer

**Goal**: Implement multi-variant interaction model system + Aurora UX projection.

**Exclusive Write Directories**:
- `backend/app/interaction/` (new)
  - `variant_router.py` — selects variant based on Aurora output
  - `variants/` — one file per variant
    - `default_conversation.py`
    - `task_execution.py`
    - `meta_reflection.py`
    - `holding_mode.py`
  - `ux_renderer.py` — translates Aurora presence to UX signals
- `mobile/lib/features/chat/presentation/widgets/aurora_indicator.dart` (new)

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS5-T1 | Define InteractionModelConfig loading from AuroraPolicyVersion.interaction_model_registry | `deployable` | 4 variant configs load correctly |
| WS5-T2 | Implement variant_router: given TDR.interaction_model_variant + ux_intent + aurora_presence → select variant + load config | `deployable` | Unit test: TDR with meta_reflection → correct variant selected |
| WS5-T3 | Implement default_conversation variant: standard chat with Aurora context injection (InferenceKnobs → prompt params) | `deployable` | Produces LLM call with correct temperature/tone/context budget |
| WS5-T4 | Implement meta_reflection variant: deeper context budget, lower temperature, identity/reconciliation prompts | `behind_flag` | Produces distinctly different LLM call from default |
| WS5-T5 | Implement holding_mode variant: minimal task tools, emotional support focus, no achievement/task pushes | `behind_flag` | Crisis flow produces holding-mode response |
| WS5-T6 | Implement task_execution variant: structured output, tool use enabled, concise responses | `behind_flag` | Task flow produces structured output |
| WS5-T7 | Implement UX renderer: aurora_presence + ux_intent → Flutter-side signals (mirror bar pulse, conversation frame) | `behind_flag` | TDR with aurora_presence=active → mirror bar pulse visible |
| WS5-T8 | Implement Aurora indicator widget in Flutter (3 levels: ambient/active/meta_surface) | `behind_flag` | Visual indicator changes based on Aurora presence level |

**Validation**: Same user message produces different response characteristics under different variants. Aurora indicator reflects presence level.

---

### WS6: Profile & Mirror Bar (Transparent Profile)

**Goal**: Implement transparent profile + mirror bar + user-facing rollback.

**Exclusive Write Directories**:
- `backend/app/aurora/profile_translator.py` (new) — LM-mediated profile rendering
- `backend/app/aurora/relationship_state.py` (new) — SparkleRelationshipState management
- `mobile/lib/features/user/presentation/widgets/mirror_bar.dart` (new)
- `mobile/lib/features/user/presentation/pages/profile_transparent.dart` (new)

**Read-Only Dependencies**:
- `backend/app/core/user_insight_state.py` (read signals, don't modify)
- All Gate 0 schemas

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS6-T1 | Implement SparkleRelationshipState manager (derived view from InsightClaims + IdentityEvidence + interaction metadata) | `deployable` | Computes relationship maturity, emergent style from existing data |
| WS6-T2 | Implement profile_translator: given user's InsightClaims + IdentityEvidence → user-readable profile summary (LM-mediated) | `deployable` | Raw claim → "你最近在学习上比较自律，连续完成了5天的计划" style output |
| WS6-T3 | Implement projection_policy filter: given list of claims → filter by projection_policy before rendering | `deployable` | internal claims excluded, sensitive_mediated only shown in appropriate context |
| WS6-T4 | Implement dialogue-mediated profile correction: user says "我最近状态其实不错" → new InsightClaim(user_correction) + contextualize old claim | `behind_flag` | Reconciliation flow: user correction → claim contextualized, not deleted |
| WS6-T5 | Implement user-facing parameter revert: in transparent profile, show Aurora-mediated changes with revert button | `behind_flag` | User can see "Sparkle 因为你 X 调了 Y" and click revert |
| WS6-T6 | Implement mirror bar widget: 4 dimensions (Focus/Energy/Commitment/Memory) with Aurora presence indicator | `behind_flag` | Mirror bar renders across chat/home/profile pages |
| WS6-T7 | Implement mirror bar data binding: connect to UserScenarioState + FocusContract + SparkleRelationshipState | `behind_flag` | Mirror bar shows live data, updates on Aurora decisions |

**Validation**: User opens transparent profile. Sees human-readable summary of their profile. Can click to discuss/correct any item. Mirror bar shows current state.

---

### WS7: Continuous Learning (DistilledStrategy)

**Goal**: Implement attribution → distillation → review → sharing pipeline.

**Exclusive Write Directories**:
- `backend/app/learning/` (new)
  - `attributor.py` — causal attribution on successful outcomes
  - `distiller.py` — extract strategy from attribution
  - `quality_gate.py` — evidence_strength, diversity_score, safety_audit
  - `deidentifier.py` — PII removal
  - `pipeline.py` — orchestrates the full learning pipeline
  - `seed_bridge.py` — integration with existing Seed Library

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS7-T1 | Implement DistilledStrategy CRUD (create, lifecycle transitions, query) | `deployable` | Strategy created in DISTILLED status, transitions to USER_REVIEWED |
| WS7-T2 | Implement attribution detector: identify successful outcomes (goal achieved + positive feedback + behavioral improvement) | `deployable` | Unit test: task completion streak + positive feedback → attribution event |
| WS7-T3 | Implement strategy distiller: extract high-density strategy from attribution + conversation context | `behind_flag` | Produces DistilledStrategy with title, description, applicability_scope |
| WS7-T4 | Implement quality gate: evidence_strength + diversity_score + safety_audit checks | `deployable` | Test: strategy with evidence_strength=0.3 → fails quality gate |
| WS7-T5 | Implement deidentifier: remove time/place/relationship/identity markers from distilled content | `deployable` | Test: "东北大三学生备考期..." → "大学生在备考期..." |
| WS7-T6 | Implement user review flow: present distilled strategy to source user for confirmation | `behind_flag` | User sees strategy summary, can approve/reject/edit |
| WS7-T7 | Implement retrieval integration: DistilledStrategy searchable by Aurora via SignalSnapshot.distilled_strategy_refs | `behind_flag` | Aurora decision includes relevant strategies in snapshot |
| WS7-T8 | Import existing Seed Library content as DistilledStrategy(human_authored) | `deployable` | All existing seeds importable with correct lifecycle status |

**Validation**: A simulated success trajectory produces an attribution. Distiller extracts a strategy. User reviews it. Strategy becomes searchable by Aurora.

---

### WS8: Integration & Validation

**Goal**: End-to-end integration testing + reference flow validation + acceptance.

**Exclusive Write Directories**:
- `backend/tests/aurora/` (new)
  - `test_reference_flows.py`
  - `test_shadow_comparison.py`
  - `test_acceptance.py`

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS8-T1 | Implement reference flow test harness: replay Gate 0 flows against live system | `deployable` | All 3 reference flows produce expected object sequences |
| WS8-T2 | Run shadow comparison: Aurora vs legacy dual_core_router on 50+ scenarios | `deployable` | Agreement rate > 80% on routine decisions; divergence documented |
| WS8-T3 | End-to-end test: user cold start → conversational modeling → plan creation → task execution → reflection → model update | `atomic` | Full loop completes without errors, all primitives populated |
| WS8-T4 | Performance baseline: Aurora deliberation < 500ms for deterministic, < 2s for LLM-assisted | `deployable` | Benchmark results documented |

---

### WS9: Social Layer (Accountability Partners)

**Goal**: Implement accountability partner system as Aurora input source + commitment witness.

**Exclusive Write Directories**:
- `backend/app/social/` (new)
  - `accountability.py` — partner matching, binding, check-in
  - `witness.py` — commitment witnessing
  - `check_in.py` — ritualized check-in scheduling
  - `recovery.py` — graceful failure handling when partner drops
  - `signal_bridge.py` — partner signals → Aurora InsightClaims
- `mobile/lib/features/community/presentation/widgets/accountability/` (new)

**Read-Only Dependencies**:
- `backend/app/services/community_service.py` (read existing social data)

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS9-T1 | Implement Commitment.witness_ids binding + unbinding | `deployable` | Partner can be added/removed from commitment |
| WS9-T2 | Implement partner_report as ClaimSource: partner observation → InsightClaim(partner_report) | `deployable` | Partner signal creates claim with correct provenance |
| WS9-T3 | Implement ritualized check-in scheduling (weekly, bound to commitment milestones) | `behind_flag` | Check-in created at milestone boundary, reminder sent |
| WS9-T4 | Implement recovery protocol: partner goes inactive → system detects → creates InsightClaim → Aurora adjusts | `behind_flag` | 7-day partner inactivity → recovery claim generated |
| WS9-T5 | Implement partner-matched context: partner can see commitment status (asymmetric visibility) | `behind_flag` | Partner sees "X completed 3/5 tasks this week" but not full profile |

**Validation**: Partner bound to commitment. Partner reports concern. Aurora receives signal and produces TDR.

---

### WS10: Aurora Observability

**Goal**: Runtime monitoring for Aurora decisions, policy usage, signal freshness.

**Exclusive Write Directories**:
- `backend/app/aurora/observability/` (new)
  - `metrics.py` — Prometheus-compatible metrics
  - `decision_logger.py` — structured human+machine readable logs
  - `policy_usage_tracker.py` — track which policies fire how often
- `monitoring/aurora_dashboards/` (new)

**Tasks**:

| ID | Task | Interrupt | Acceptance |
|----|------|-----------|------------|
| WS10-T1 | Implement decision_logger: every TDR → structured log (JSON + human-readable summary) | `deployable` | Decision log queryable by user_id, time range, decision_type |
| WS10-T2 | Implement Prometheus metrics: decision_count by mechanism, basis, impact_class; latency histogram; rollback_count | `deployable` | Metrics scrapeable at /metrics endpoint |
| WS10-T3 | Implement policy usage tracker: AuroraPolicyVersion usage stats, rollback frequency, rule hit rates | `deployable` | Dashboard shows policy v1.0 usage distribution |
| WS10-T4 | Implement SignalSnapshot freshness monitor: alert when core signals stale > threshold | `deployable` | Alert fires when user profile signal > 24h old |
| WS10-T5 | Build minimal Grafana dashboard for Aurora metrics | `deployable` | Dashboard shows decision volume, mechanism distribution, latency, rollback rate |

**Validation**: Aurora runs 100 test decisions. All appear in decision log. Grafana dashboard shows correct metrics.

---

## 5. File Ownership Matrix

| Workstream | Exclusive Write Paths | Reads From (no write) |
|------------|----------------------|----------------------|
| WS1 Aurora Runtime | `backend/app/aurora/engine.py`, `decision_fns/`, `bayesian/`, `llm_bridge.py`, `policy_loader.py`, `config.py` | Gate 0 schemas, dual_core_router (shadow) |
| WS2 Graph Runtime | `backend/app/graph/` | Gate 0 schemas, ScenarioPackManifest |
| WS3 Signal Pipeline | `backend/app/aurora/signal_aggregator.py`, `signal_processor.py`, `ledger.py` | All existing services (read-only), prompts.py (WS3-T7 writes) |
| WS4 Scenario Pack | `backend/app/scenario_packs/`, `backend/app/aurora/schemas/` (pack models) | agent_profiles.py (read, migrate from) |
| WS5 Interaction Layer | `backend/app/interaction/`, `mobile/.../aurora_indicator.dart` | Aurora output, AuroraPolicyVersion |
| WS6 Profile & Mirror | `backend/app/aurora/profile_translator.py`, `relationship_state.py`, `mobile/.../mirror_bar.dart`, `mobile/.../profile_transparent.dart` | user_insight_state.py (read), Gate 0 schemas |
| WS7 Continuous Learning | `backend/app/learning/` | Seed Library models (read), Aurora output |
| WS8 Integration | `backend/tests/aurora/` | Everything (test only) |
| WS9 Social Layer | `backend/app/social/` | community_service.py (read), Commitment schema |
| WS10 Observability | `backend/app/aurora/observability/`, `monitoring/aurora_dashboards/` | Aurora output (read metrics from) |

**Hotspot Conflict Resolution**:
- `backend/app/orchestration/orchestrator.py`: WS1 owns migration (move Aurora calls into orchestrator). Others read-only.
- `backend/app/orchestration/prompts.py`: WS3-T7 owns the data leakage fix. WS5 reads prompt templates for variant configs.
- `backend/app/core/user_insight_state.py`: WS6 reads only. WS3 SignalAggregator reads only. No workstream writes to this file.
- `backend/app/core/agent_profiles.py`: WS4 reads and migrates content. File itself is not modified — content is compiled into pack configs.

---

## 6. Wave Execution Sequence

### Wave 0: Foundation (4-5 days, Sequential)

Single agent executes. No parallelism needed.

```
W0.1 → Deploy Gate 0 Pydantic models to backend/app/aurora/schemas/
W0.2 → Create DB migration for new tables (FocusContract, Commitment, TDR, InsightClaim, etc.)
       + Verify all migrations have tested downgrade paths on throwaway DB
W0.3 → Add feature flags: AURORA_SHADOW_MODE, AURORA_ACTIVE, INTERACTION_VARIANTS
W0.4 → Create common enum imports from Gate 0
W0.5 → Build reference flow test harness skeleton (WS8-T1 front-loaded)
       - Skeleton depends only on Gate 0 schemas, not on live system
       - Wave 1 agents fill in data against this harness
W0.6 → Author orchestrator ↔ Aurora integration contract (WS1-T9 front-loaded)
       - docs/product/SPARKLE_AURORA_ORCHESTRATOR_INTEGRATION.md
       - Must be signed off before Wave 1 agents begin WS1-T4
```

### Wave 1: Core Engine (10-14 days, 4 Parallel Agents)

```
Agent A: WS1 (Aurora Runtime) + WS10 (Observability)
  - Aurora is the control plane; observability is its natural companion
  - WS10 can start as soon as WS1-T1 produces the module structure

Agent B: WS2 (Graph Runtime)
  - Independent of Aurora internals; only needs schema definitions

Agent C: WS3 (Signal Pipeline)
  - Independent of Aurora and Graph; only needs schema definitions
  - WS3-T7 (prompt fix) can run immediately

Agent D: WS4 (Scenario Pack) + WS7-T8 (Seed Library import to DistilledStrategy)
  - Independent; produces the first pack that everything validates against
  - WS7-T8 imported here so Wave 1 validation finds strategies in retrieval
```

**Wave 1 Gate**: All 4 workstreams complete their `deployable` tasks. Aurora can produce a TDR given a hand-crafted SignalSnapshot. Graph can traverse a backbone. SignalPipeline can assemble a snapshot. **Additionally: at least 1 reference flow (Main Flow) runs end-to-end with real SignalAggregator → real Aurora.deliberate() → real Graph execution → real Ledger write. Pack may be a minimal 1-node stub, but no component may be mocked.**

### Wave 2: User Experience (10-14 days, 4 Parallel Agents)

```
Agent E: WS5 (Interaction Layer)
  - Depends on: WS1 (Aurora output format), WS4 (pack node configs)
  - Can start WS5-T1/T2 once WS1-T4 delivers Aurora.deliberate()

Agent F: WS6 (Profile & Mirror Bar)
  - Depends on: WS3 (SignalPipeline), WS1 (Aurora claims)
  - Can start WS6-T1/T2 once WS3 delivers InsightClaim lifecycle

Agent G: WS9 (Social Layer)
  - Depends on: WS2 (Commitment lifecycle), WS3 (SignalProcessor)
  - Can start WS9-T1 once WS2-T5 delivers Commitment engine

Agent H: Integration prep (WS8-T1 preparation)
  - Build reference flow test harness
  - Depends on: WS1 + WS2 + WS3 for test harness wiring
```

**Wave 2 Gate**: Full user flow works end-to-end in shadow mode. Mirror bar renders. Interaction variants produce different responses. Partner can be bound to commitment.

### Wave 3: Evolution & Validation (7-10 days, 3 Parallel Agents)

```
Agent I: WS7 (Continuous Learning)
  - Depends on: WS3 (InsightClaim + attribution signals), WS6 (user review flow)
  - Produces DistilledStrategy pipeline

Agent J: WS8 (Integration & Validation)
  - Full reference flow validation
  - Shadow comparison report
  - Performance baseline

Agent K: Migration (WS-M)
  - Depends on: WS8 validation passing
  - Execute shadow → gradual cutover for first user cohort
```

**Wave 3 Gate**: All 3 reference flows pass. Shadow comparison < 20% divergence on routine decisions. First user cohort running on Aurora.

---

## 7. Acceptance Criteria (Stage 3 Complete)

### Must Have (P0)

- [ ] Aurora produces valid TransitionDecisionRecords for all 3 reference flows
- [ ] Graph runtime traverses exam_prep_14d backbone correctly
- [ ] SignalSnapshot assembles from existing services without errors
- [ ] Interaction variants produce measurably different responses (tone/tools/budget)
- [ ] Mirror bar renders live data across chat/home/profile pages
- [ ] Transparent profile shows human-readable profile summary
- [ ] Dev CLI can execute rollbacks
- [ ] Aurora observability dashboard shows decision metrics
- [ ] Accountability partner can be bound to commitment and report signals
- [ ] Prompt pipeline data leakage fixed (render rate > 75%)

### Should Have (P1)

- [ ] DistilledStrategy pipeline produces at least 1 user-reviewed strategy
- [ ] User-facing parameter revert works in transparent profile
- [ ] Shadow comparison agreement rate > 80% with legacy system
- [ ] First user cohort migrated to Aurora path

### Nice to Have (P2)

- [ ] 2nd scenario pack (e.g., thesis writing)
- [ ] Aurora presence meta-surface animation (full immersive)
- [ ] Cross-user learning base with 5+ community-shared strategies

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Aurora LLM calls too slow | Medium | High | Default to deterministic; LLM only for hybrid/critical decisions |
| Aurora self-failure cascades to block user | Low | Critical | WS1-T8 fallback TDR + WS10 alert on fallback_count > threshold |
| SignalSnapshot assembly fails silently | Medium | High | WS10 freshness monitor alerts on stale core signals |
| Workstream file conflict | Low | High | File ownership matrix + CI check that no two PRs touch same file |
| Graph runtime too complex for MVP | Medium | Medium | First version: if-else backbone traversal only, no dynamic graph |
| Migration breaks existing users | Low | Critical | Shadow mode + feature flags + per-user cutover |
| DistilledStrategy quality poor | High | Low | Human review gate for first 100 items; auto-downgrade monitoring |

---

## 9. Agent Assignment Template

When dispatching to an agent (Codex or Claude Code), use this template:

```
WORKSTREAM: [WS# - Name]
WAVE: [0/1/2/3]
AGENT: [codex-1 / claude-code-2 / ...]

CONTEXT FILES (READ FIRST):
- docs/product/SPARKLE_AURORA_GATE0_SCHEMA_2026-04-17.md (v1.0-frozen)
- docs/product/SPARKLE_AURORA_STAGE3_DISPATCH_PLAN_2026-04-17.md (this file)
- [Workstream-specific files]

YOUR EXCLUSIVE WRITE PATHS:
- [List from File Ownership Matrix]

YOUR TASKS:
- [Task IDs from workstream definition]

INTERRUPT SEMANTICS:
- [Per task]

ACCEPTANCE CRITERIA:
- [From task table]

DO NOT:
- Modify any Gate 0 schema (file a Gate 0.1 amendment request instead)
- Write to files owned by another workstream
- Introduce new concepts not in Gate 0 (use provisional tag if needed)
- Skip append-only invariant on primitives
```
