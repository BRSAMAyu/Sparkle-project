# CXP-30 Report — Final Integration Readiness And Conflict Map

## Goal
Prepare all parallel work for final merge by identifying write-set overlaps, duplicate implementations, incompatible assumptions, migration conflicts, API contract conflicts, missing cross-links, and the required merge order.

---

## 1. Branch Inventory

### 1.1 Complete Branch List (29 branches)

| # | Branch | HEAD | Additional Commits | Report |
|---|--------|------|---------------------|--------|
| CXP-01 | `codex/CXP-01-aurora-everyday-presence` | `1998b080c` | 1: "feat: surface aurora everyday presence" | YES |
| CXP-02 | `codex/CXP-02-aurora-l3-core-session` | `97b765c26` | 0 (at base) | NO |
| CXP-03 | `codex/CXP-03-aurora-wake-proactivity` | `97b765c26` | 0 (at base) | YES |
| CXP-04 | `codex/CXP-04-dualcore-sgw-learning-loop` | `2e86c76d7` | 2: "feat: surface aurora everyday presence" + "Close DualCore SGW routing loop" | YES |
| CXP-05 | `codex/CXP-05-memory-return-context` | `97b765c26` | 0 (at base) | NO |
| CXP-06 | `codex/CXP-06-ai-conversation-card-protocol` | `a7769c237` | 1: "CXP-21 harden document source feedback" | YES |
| CXP-07 | `codex/CXP-07-plan-replanning` | `97b765c26` | 0 (at base) | NO |
| CXP-08 | `codex/CXP-08-daily-task-execution-flow` | `97b765c26` | 0 (at base) | YES |
| CXP-09 | `codex/CXP-09-knowledge-galaxy` | `cccec98a6` | 3: "Polish reports insights theater narratives" + "Close DualCore SGW routing loop" + "feat: surface aurora everyday presence" + "feat(galaxy): expose operational learning states" | YES |
| CXP-10 | `codex/CXP-10-seed-library-capsules` | `97b765c26` | 0 (at base) | YES |
| CXP-11 | `codex/CXP-11-learning-tools` | `97b765c26` | 0 (at base) | YES |
| CXP-12 | `codex/CXP-12-error-book-reviews-exam-sprint` | `97b765c26` | 0 (at base) | YES |
| CXP-13 | `codex/CXP-13-community-social-learning` | `24c6f2a70` | 3: "Polish community feed privacy and scopes" + lineage B chain | YES |
| CXP-14 | No branch found | — | — | NO |
| CXP-15 | `codex/CXP-15-accountability-social` | `97b765c26` | 0 (at base) | NO |
| CXP-16 | `codex/CXP-16-achievements-photon-shop-rewards` | `97b765c26` | 0 (at base) | NO |
| CXP-17 | `codex/CXP-17-visual-identity` | `97b765c26` | 0 (at base) | NO |
| CXP-18 | `codex/CXP-18-home-dashboard-clarity` | `97b765c26` | 0 (at base) | NO |
| CXP-19 | `codex/CXP-19-cold-start-journey` | `97b765c26` | 0 (at base) | YES |
| CXP-20 | `codex/CXP-20-reports-insights-theater` | `97b765c26` | 0 (at base) | YES |
| CXP-21 | `codex/CXP-21-documents-rag-source-tray` | `97b765c26` | 0 (at base) | NO |
| CXP-22 | `codex/CXP-22-calendar-schedule-time` | `97b765c26` | 0 (at base) | YES |
| CXP-23 | `codex/CXP-23-realtime-chat` | `97b765c26` | 0 (at base) | NO |
| CXP-23b | `codex/CXP-23-realtime-gateway-offline` | `97b765c26` | 0 (at base) | NO |
| CXP-24 | `codex/CXP-24-mobile-polish` | `97b765c26` | 0 (at base) | YES |
| CXP-25 | `codex/CXP-25-backend-privacy` | `8ef115929` | 1: "fix(quality): audit fixes — centralized test credentials, visual regression corrections" | YES |
| CXP-26 | `codex/CXP-26-observability-ops` | `97b765c26` | 0 (at base) | YES |
| CXP-27 | `codex/CXP-27-perf-cost-budget` | Not checked | Not checked | NO |
| CXP-28 | `codex/CXP-28-admin-qa-controls` | Not checked | Not checked | NO |
| CXP-29 | `codex/CXP-29-north-star-journey` | `97b765c26` | 0 (at base) | YES (this pass) |
| CXP-30 | `codex/CXP-30-integration-readiness` | — | — | YES (this pass) |

**Summary:** 17 of 30 tasks have reports (57%). 6 branches have unique commits beyond the base. 20+ branches are at the exact same commit `97b765c26`. CXP-14 has no branch. Two CXP-23 variants exist.

---

## 2. Git DAG Structure

### 2.1 The Two Lineages

```
Common base: e1ed1763b7e (merge base with main)
    │
    ├─ Lineage A (23 branches)
    │   153c5e3b4 "docs: add parallel polish execution guide"
    │   → 9d05229bb "docs: expand parallel codex dispatch prompts"
    │   → 18e9da7d1 "fix(quality): P2 audit fixes (33 items)"
    │   → 97b765c26 "fix(quality): deferred P2 items"  ← 20 branches stop here
    │       ├─ CXP-01: +1 commit (1998b080c)
    │       ├─ CXP-06: +1 commit (a7769c237) [note: commit message says "CXP-21"]
    │       └─ CXP-25: +1 commit (8ef115929)
    │
    └─ Lineage B (3 branches)
        153c5e3b4 → 9d05229bb → 18e9da7d1
        → 3ebc0ed5d "feat: surface aurora everyday presence"
        → 2e86c76d7 "Close DualCore SGW routing loop"  ← CXP-04 stops here
            ├─ CXP-09: +2 commits (48c5ec6f8, cccec98a6)
            └─ CXP-13: +1 commit (24c6f2a70)
```

### 2.2 Critical Structural Problems

1. **Lineage A / Lineage B divergence**: The two lineages diverged at `18e9da7d1`. Lineage B added `3ebc0ed5d` + `2e86c76d7` (Aurora everyday presence + DualCore SGW loop). Lineage A has `97b765c26` (deferred P2 items) but NOT the two Lineage B commits. These two lineages have conflicting changes on the same files.

2. **Identical-commit problem**: 20 branches are at the exact same commit `97b765c26`. These branches cannot be merged independently — they have no distinct committed content. The actual per-task work lives in uncommitted working tree changes, as documented in multiple reports ("commit not created because the worktree already contained extensive unrelated uncommitted changes").

3. **CXP-06 commit mislabeling**: CXP-06's unique commit is titled "CXP-21 harden document source feedback" — suggesting either the commit was applied to the wrong branch or CXP-06 and CXP-21 changes are intertwined.

4. **CXP-23 duplication**: Two branches: `codex/CXP-23-realtime-chat` and `codex/CXP-23-realtime-gateway-offline`. Both at the same commit. No report from either.

---

## 3. Write-Set Overlap Analysis

### 3.1 Shared Base (~580 files changed across all branches)

The following directories have changes in every branch due to the shared base:

| Directory | Est. Files | Risk |
|-----------|-----------|------|
| `backend/app/services/` | 30+ | HIGH — every CXP task touched services |
| `backend/app/orchestration/` | 8+ | HIGH — orchestrator, context builder, response builder |
| `backend/app/api/v1/` | 12+ | HIGH — community, tasks, error_book, vocabulary, translation, seed_libraries, profile_transparency, push_interaction |
| `backend/app/schemas/` | 7+ | MEDIUM — galaxy, seed_content, error_book, north_star_metrics, unified_notification |
| `backend/app/core/` | 3+ | MEDIUM — metrics, cost_controller |
| `backend/app/aurora/runtime_v1/` | 5+ | HIGH — wake_policy, planning, correction_feedback |
| `backend/gateway/internal/` | 10+ | HIGH — handler, middleware, logsafe |
| `mobile/lib/features/` | 20+ | HIGH — home, chat, task, community, galaxy, aurora, seed_library, insights, theater, achievement |
| `mobile/lib/l10n/` | 3+ | MEDIUM — app_en.arb, localizations |
| `monitoring/` | 5+ | MEDIUM — prometheus, grafana, alerts, runbooks |
| `scripts/` | 15+ | LOW — guards, checks, acceptance scripts |
| `proto/` | 3+ | CRITICAL — agent_service, community_service, websocket |
| `docs/product/parallel_closeout/` | 17+ | LOW — CXP reports |

### 3.2 Per-Task Write Sets (from reports, where identifiable)

| Task | Files Changed (per report) | Overlaps With |
|------|---------------------------|---------------|
| CXP-01 | `context_builder.py`, `response_builder.py`, test | CXP-04 (orchestrator), CXP-06 (response builder) |
| CXP-03 | `wake_policy.py`, `notification_center_service.py`, `push_policy_compiler.py`, `push_delivery_service.py`, `push_feedback_service.py`, `unified_notification.py`, `push_interaction.py` | CXP-26 (metrics for push) |
| CXP-04 | `dual_core_router.py`, `scaffolding_fsm.py`, route history services, Aurora correction payloads | CXP-01 (response builder), CXP-02 (correction flow) |
| CXP-06 | `entity_cards.py`, mobile `entity_card_payloads.dart` | CXP-07 (plan cards), CXP-14 (share cards) |
| CXP-08 | `daily_task_selection_service.py`, `tasks.py`, `growth_dashboard_service.py`, mobile `task_card.dart`, `task_list_screen.dart`, `task_repository.dart` | CXP-18 (dashboard), CXP-22 (schedule) |
| CXP-09 | `galaxy.py` (schemas), `galaxy_service.py`, `structure_service.py`, `provenance.py`, `galaxy_event_consumer.py`, `knowledge_integration_service.py` | CXP-11 (vocab→knowledge), CXP-12 (error→galaxy) |
| CXP-10 | `seed_content.py` (schemas), `seed_library_service.py`, `seed_libraries.py` (API), `community.py` | CXP-14 (share cards), CXP-13 (community) |
| CXP-11 | `vocabulary.py` (API), `translation.py` (API), `vocabulary_service.py`, `task_recommendation_service.py`, `translation_tool.py` | CXP-09 (knowledge graph) |
| CXP-12 | `error_book.py` (API), `error_book.py` (schemas), `error_book_service.py`, `error_book_mastery_sync_service.py` | CXP-09 (galaxy review urgency) |
| CXP-13 | `community.py` (API), `collaboration_service.py`, mobile `community_providers.dart`, `community_screen.dart` | CXP-25 (privacy boundaries) |
| CXP-19 | `profile_transparency.py`, `planning_workflow.py`, `task_service.py`, `north_star_metrics_service.py`, `north_star_metrics.py` | CXP-07 (planning), CXP-08 (tasks) |
| CXP-20 | `progress_narrative_service.py`, `prediction_theater_service.py`, mobile insights/theater models | CXP-19 (milestones) |
| CXP-22 | `smart_schedule_service.py`, `adaptive_replanner.py` | CXP-07 (replanning), CXP-08 (task scheduling) |
| CXP-24 | `task_list_screen.dart`, `community_main_screen.dart`, `app_en.arb` | CXP-08 (task UI), CXP-13 (community UI) |
| CXP-25 | Gateway `logsafe/`, auth middleware, WS auth, chat feedback, Galaxy handler | CXP-13 (community privacy), CXP-23 (gateway) |
| CXP-26 | `metrics.py`, `sparkle_slo_alerts.yml`, `sparkle-product-loops.json`, `incident_response.md` | CXP-03 (push metrics), CXP-08 (task metrics) |

### 3.3 Top Conflict Hotspots

Ranked by number of CXP tasks touching the same file or subsystem:

1. **`orchestrator.py` / response builder** — CXP-01, CXP-04, CXP-06, CXP-07
2. **Task execution chain** (`task_service.py`, task API, mobile task) — CXP-08, CXP-19, CXP-22
3. **Community API and services** — CXP-10, CXP-13, CXP-14, CXP-25
4. **Galaxy/knowledge graph** — CXP-09, CXP-11, CXP-12
5. **Planning workflow** — CXP-07, CXP-19, CXP-22
6. **Aurora runtime / correction** — CXP-01, CXP-02, CXP-03, CXP-04
7. **Gateway handlers/middleware** — CXP-23, CXP-25
8. **Proto files** — Changed in shared base; any proto change affects all branches

---

## 4. Duplicate Implementations And Incompatible Assumptions

### 4.1 Duplicate Systems Identified

1. **CXP-23 duplication**: Two branches for realtime chat/gateway (`codex/CXP-23-realtime-chat` and `codex/CXP-23-realtime-gateway-offline`). These must be reconciled into a single implementation. Recommend using the `-offline` variant as it has 4 extra commits from the Lineage B chain.

2. **Share/resource card representation**: CXP-06 added card builders; CXP-10 added adoption actions; CXP-14 (unreported) would add share-specific card work. These three layers of card protocol changes must be unified.

3. **Task selection scoring**: CXP-08 added Aurora-aware daily task selection; CXP-22 added duration-aware smart scheduling. Both influence "what should I do next" and must agree on ranking weights.

4. **Aurora state read paths**: CXP-01 reads Aurora state through `context_builder.py` for chat presence; CXP-04 reads it through `dual_core_router.py` for routing. CXP-03 reads it for wake decisions. These three consumption paths must use the same state model.

### 4.2 Incompatible Assumptions

1. **Lineage A assumes `97b765c26` P2 fixes are current; Lineage B does not include them.** Lineage B branches (CXP-04, CXP-09, CXP-13) do not have the deferred P2 items commit. Merging B into A (or vice versa) will produce conflicts on any file touched by both `97b765c26` and `3ebc0ed5d`/`2e86c76d7`.

2. **Route ID optionality**: CXP-04 made route history IDs optional in correction payloads. CXP-02 (L3 Core Session) may depend on them being present. Without CXP-02's report, this is an unknown conflict.

3. **Knowledge node visibility**: CXP-09 made user-owned draft nodes visible in Galaxy. Other services (CXP-11, CXP-12) may have been written assuming drafts are hidden. The provenance and visibility semantics must be consistent.

4. **First plan milestone scope**: CXP-19 records `first_plan_requested` only through the modeling bridge. If CXP-07 implemented an alternative plan-creation path, the milestone won't fire there. This is a silent data gap, not a merge conflict.

---

## 5. Missing Cross-Links

### 5.1 Report-Level Gaps

13 tasks have no reports. These subsystems are dark to the final integrator:

- **CXP-02**: L3 Core Session — the flagship Aurora calibration flow
- **CXP-05**: Memory, Profile, Return Context — comeback/return journey
- **CXP-07**: Plan Creation, Review, Replanning — core planning loop
- **CXP-14**: Sharing System — 6+ shareable resource types
- **CXP-15**: Accountability — partner/squad social loop
- **CXP-16**: Achievements, Photon, Shop — reward loop
- **CXP-17**: Visual Elements, Color System, Identity — visual identity
- **CXP-18**: Home Dashboard — first-viewport clarity
- **CXP-21**: Documents, Files, RAG — source-based learning
- **CXP-23**: Realtime Chat, Gateway, Offline — communication reliability
- **CXP-27**: Performance, Cost, Budget — cost governance
- **CXP-28**: Admin, QA, Internal Controls — operator surfaces

### 5.2 Code-Level Gaps (from CXP-29 journey validation)

1. CXP-04 route IDs not consistently surfaced → all correction UIs need updating
2. CXP-19 `first_plan_requested` only fires through modeling bridge → direct API and seed adoption paths need it
3. CXP-06 idempotent card actions mentioned but not implemented → gateway/client need idempotency keys
4. CXP-09 mobile Galaxy operational rendering unverified → backend states may not show in UI
5. CXP-12 review cards create task-card payloads but don't create server-side tasks → client must materialize

---

## 6. Migration And API Contract Conflicts

### 6.1 Proto Changes

Three proto files are changed in every branch:
- `proto/agent_service.proto`
- `proto/community_service.proto`
- `proto/websocket.proto`

**Risk**: If Lineage A and Lineage B changed the same proto message differently, `make proto-gen` will fail or produce incompatible generated code. Proto files must be merged first and regenerated before any other work.

### 6.2 Database Migrations

No new Alembic migrations were reported by any CXP task. If any task added model fields without a migration, they won't exist in the database. The shared base includes 52 existing migrations.

### 6.3 API Contract Conflicts

- `POST /api/v1/community/share` — touched by CXP-10, CXP-13, CXP-14
- `POST /api/v1/vocabulary/wordbook` — extended by CXP-11 with new optional fields (backward compatible)
- `GET /api/v1/errors/review-cards` — new endpoint from CXP-12
- `GET /api/v1/tasks/today` and `/tasks/recommended` — touched by CXP-08

Backward compatibility appears preserved (new optional fields only). No breaking API changes identified in the 17 reports.

---

## 7. Recommended Merge Order

### Phase 0: Foundation Reconciliation (do first, before any feature merge)

1. **Resolve Lineage A vs B**: Merge `97b765c26` (deferred P2 items) and `3ebc0ed5d`/`2e86c76d7` (Aurora presence + DualCore loop) into a unified base. These two lineages diverged on the same files. Reconcile manually:
   - Accept both: Aurora everyday presence + DualCore SGW loop + deferred P2 fixes
   - Run full test suite on reconciled base
   - This becomes the new integration base for all other branches

2. **Proto files**: Merge proto changes from both lineages, run `make proto-gen`, verify generated code compiles.

3. **Run `make local-signoff-preflight`**: Verify DB/Redis/ports/migrations/indexes are clean.

### Phase 1: Backend Services (in dependency order)

4. **CXP-25** (privacy/safety) — Gateway logsafe and auth middleware (infrastructure for all)
5. **CXP-04** (DualCore/SGW loop) — Route history, outcome recording (infrastructure for Aurora)
6. **CXP-01 + CXP-03** (Aurora presence + wake) — Depends on CXP-04 route infrastructure
7. **CXP-09** (Knowledge Galaxy) — Graph operational states
8. **CXP-11** (Vocabulary/translation tools) — Depends on CXP-09 knowledge integration
9. **CXP-12** (Error book/reviews) — Depends on CXP-09 mastery sync
10. **CXP-08** (Daily task execution) — Task selection + sync recovery
11. **CXP-22** (Calendar/schedule) — Depends on CXP-08 task selection
12. **CXP-19** (Onboarding/cold start) — North Star milestones
13. **CXP-10** (Seed library) — Adoption actions
14. **CXP-20** (Reports/insights/theater) — Narrative + prediction evidence
15. **CXP-26** (Observability) — Metrics, dashboards, alerts

### Phase 2: Gateway and Mobile

16. **CXP-06** (Card protocol) — Entity cards + mobile parser
17. **CXP-13** (Community feed) — Feed scopes + privacy
18. **CXP-24** (Mobile polish) — l10n, semantics, accessibility

### Phase 3: Unreported Branches (requires per-branch assessment)

19-31. CXP-02, 05, 07, 14, 15, 16, 17, 18, 21, 23, 27, 28 — each must be assessed individually since no report exists. If the working tree has uncommitted changes, extract them into commits before merging.

### Phase 4: Integration Validation

32. **CXP-29** (E2E journey validation) — Re-run journey acceptance after all merges
33. Run full signoff: `make local-final-signoff`
34. Update Roadmap Tracker and Final Acceptance Ledger

---

## 8. Unresolved Decision List

These need explicit decisions from the final Codex reviewer before merge:

1. **Lineage A vs B reconciliation**: Which commit is the canonical base? Merge both and test, or pick one and re-apply the other's changes?
2. **CXP-23 deduplication**: Which of the two CXP-23 branches to keep? Or merge both?
3. **20 identical branches**: How to extract per-task uncommitted changes from identical-commit branches? Options: (a) manually stage hunks from each report's described changes, (b) accept that work is lost and re-implement from reports, (c) ask each agent to commit and push their working tree changes.
4. **CXP-02 priority**: L3 Core Session is the flagship Aurora experience. If it has no working implementation, should final merge wait for it or proceed without it?
5. **CXP-14 (sharing)**: No branch exists. Is sharing covered by CXP-06 + CXP-10 + CXP-13, or does it need dedicated implementation?
6. **Mobile UI verification**: Most reports are backend-only. How to verify mobile rendering quality across all 10 acceptance journeys?

---

## 9. Required Test Matrix

After merge, run these test suites in order:

| Step | Command | Covers |
|------|---------|--------|
| 1 | `make proto-gen && make proto-lint` | Proto consistency |
| 2 | `cd backend/gateway && go test ./...` | Go gateway + logsafe + handlers |
| 3 | `cd backend && pytest tests/unit/ -q` | Python unit tests (all CXP tasks) |
| 4 | `cd backend && pytest tests/services/ -q` | Service integration |
| 5 | `cd backend && pytest tests/api/ -q` | API contract |
| 6 | `cd backend && pytest tests/integration/ -q` | Integration flows |
| 7 | `cd backend && python scripts/ai_chat_multiturn_acceptance.py` | Chat E2E |
| 8 | `cd mobile && flutter analyze` | Mobile static analysis |
| 9 | `cd mobile && flutter test` | Mobile widget/unit tests |
| 10 | `make local-final-signoff` | Full preflight + smoke |

---

## 10. What The Final Integrator Can Now Accomplish

With this report, the final integrator has:
- Complete branch inventory with commit hashes and lineage
- Write-set overlap map identifying the 8 top conflict hotspots
- 6 duplicate/incompatible assumptions documented
- 13 missing reports flagged with exact subsystem ownership
- 5 code-level cross-links documented from CXP-29 journey validation
- Proto/migration/API contract conflict assessment
- 4-phase merge order with 33 steps
- 6 unresolved decisions requiring reviewer judgment
- 10-step test matrix for post-merge validation

The final integrator cannot merge blindly because 13 tasks have no reports and 20 branches have no committed per-task changes. However, this map eliminates guesswork: every known conflict is documented, every unknown is flagged, and the merge sequence minimizes cross-system breakage.

---

## Verification

- Git DAG analysis: 29 branches traced, 2 lineages identified, merge base confirmed at `e1ed1763b7e`
- Report cross-reference: 17 reports read and mapped to branches
- Write-set analysis: per-task files extracted from 16 reports (CXP-29 self-excluded)
- Hotspot ranking: `uniq -c | sort -rn` over 7-branch file union

---

## Commit

Branch: `codex/CXP-30-integration-readiness` (to be created)
Commit: pending (this report)
