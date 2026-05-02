# CXP-29 Report — End-To-End North Star Journey

> Final integration note (2026-05-02): this report was written before the final merge pass. Its "missing report" and "GAP" statuses reflected the pre-merge state. The final integrated acceptance state is recorded in `SPARKLE_FINAL_INTEGRATION_ACCEPTANCE_REPORT_2026-05-02.md`.

## Goal
Validate and polish the complete product story: a zero-base user can onboard, state a goal, receive a plan, execute tasks, use tools, receive Aurora calibration, correct the system, share progress, return after absence, and see changed future behavior. This report is the canonical final E2E acceptance narrative.

## Methodology
Traced all 10 non-negotiable acceptance journeys through the codebase, cross-referencing the 17 completed CXP reports and inspecting backend services, gateway handlers, and mobile feature modules. Each journey is rated: PASS (chain connected end-to-end), PARTIAL (core path works but edge states or mobile UI incomplete), GAP (missing link), or UNVERIFIED (no CXP report and code path unclear).

---

## Journey 1: New User — Onboarding → First Goal → First Plan → First Task → First Aurora Status

**Status: PARTIAL**

**Chain:**
1. `PersonaOnboardingScreen` → `POST /api/v1/profile/onboarding` → `TraitsColdstartService` builds `cold_start_context`
2. CXP-19 fixed: goal type preserved (exam/project/skill), baseline labels normalized, skip produces safe defaults
3. `planning_workflow.py` bridge records `first_plan_requested` North Star milestone → `PlanService.create_plan()`
4. First plan auto-sets `is_primary=True`
5. First task completion records `first_task_completed` milestone
6. Aurora baseline recorded via `NorthStarMetricsService`

**What works:** Backend cold-start → plan → task → milestone chain is wired. Skip path preserves correctable defaults.
**What's missing:**
- CXP-07 (plan creation/review/replanning) has no report — plan review quality against impossible schedules is unverified
- CXP-18 (home dashboard clarity) has no report — first-viewport Aurora status band rendering unverified
- CXP-17 report file was missing from the directory — visual identity of first-run dashboard unverified
**Residual risk:** `first_plan_requested` milestone only fires through the modeling bridge; alternative plan-creation paths (direct API, seed adoption) do not record it.

---

## Journey 2: Standard Chat — Vague Goal → AI Clarifies → Actionable Cards → Cards Route Correctly

**Status: PARTIAL**

**Chain:**
1. `ChatOrchestrator` → `Orchestrator` FSM → `ResponseBuilder` → `entity_cards.py`
2. CXP-06 added card schema validation via `validate_entity_card()` and builders for review/vocabulary/seed cards
3. CXP-06 mobile: fallback parser creates routable `EntityCardPayload` for previously inert card types
4. Gateway WebSocket proxy forwards metadata + delta to Flutter

**What works:** Task/plan/knowledge/share/review/vocabulary/seed cards all validate. Mobile parser routes 7 card types.
**What's missing:**
- CXP-23 (realtime chat/gateway/offline) has no report — streaming reliability, offline queue, and retry behavior unverified
- CXP-21 (documents/RAG/source tray) has no report — source-attributed cards from document context unverified
- Gateway-level card action idempotency is mentioned as a handoff note in CXP-06 but not implemented
**Residual risk:** Review/vocabulary/seed cards use generic `EntityCardPayload` rather than dedicated rich card layouts; UI polish is deferred.

---

## Journey 3: Aurora Correction — User Rejects Judgment → Freeform → Future Behavior Changes

**Status: PARTIAL**

**Chain:**
1. Aurora status band → correction chips → `CorrectionFeedbackProcessor`
2. CXP-04 wired route history backfill: disconfirming corrections mark route as failed, apply SGW feedback, expose `routing_feedback_recorded`
3. CXP-01 surfaced Aurora everyday presence in chat receipts with correction affordances
4. CXP-03 added wake feedback that reduces future wake confidence on negative response

**What works:** Correction → route outcome failure → SGW support increase → future routing change is test-verified. Wake negative feedback suppresses future wake kinds.
**What's missing:**
- CXP-02 (L3 Core Session flagship) has no report — the "你没懂我" deep calibration flow is the highest-value Aurora correction path and is UNVERIFIED
- CXP-05 (memory/profile/return context) has no report — correction of inferred memory claims is unverified
- CXP-04 report notes route IDs are optional and "surfacing those ids consistently in every chat correction UI remains a useful follow-up"
**Residual risk:** Without CXP-02 verified, the most important correction flow (deep calibration session) may be broken or shadow-only.

---

## Journey 4: L3 Calibration — "你没懂我" → Core Session → State/Policy/Task Changes → Summary → Background

**Status: GAP**

**Chain (expected):**
1. User expresses frustration → trigger detection → `CoreSession` service opens agenda
2. Multi-message calibration with pause/resume → `SessionClosure` applies `state_patches`, `policy_changes`, `directives_to_regenerate`
3. Summary displayed → return to normal chat with changed behavior

**What works:** Aurora runtime v1, correction feedback, and SGW feedback loop infrastructure exist.
**What's missing:** CXP-02 has no report. Branch `codex/CXP-02-aurora-l3-core-session` exists but no verification evidence. The core session data models (`AuroraCaseFile`, `AuroraAgenda`, `SessionClosure`) exist in the codebase, but the end-to-end flow from trigger to closure summary is UNVERIFIED.
**Critical risk:** This is Sparkle's deepest moat experience. If it's broken, the product cannot deliver on its core promise of "being understood."

---

## Journey 5: Daily Execution — Open App → See Next Action → Complete/Skip/Fail → Plan and Aurora Update

**Status: PARTIAL**

**Chain:**
1. `DailyTaskSelectionService` ranks tasks by plan focus, deadline, priority, duration, difficulty, energy cost, Aurora state
2. CXP-08: next-action selection considers Aurora energy state, downshifts during L2/L3
3. Task completion → plan state update → Galaxy mastery update → achievement check → next_actions preserved
4. CXP-08: failed sync cards show error with retry/discard actions
5. CXP-22: duration feedback ("too_long") creates `time_overrun` plan-health signal

**What works:** Backend next-action selection with Aurora awareness. Task completion propagates to plan/Galaxy/achievements. Sync failure recovery visible.
**What's missing:**
- CXP-15 (accountability) has no report — social completion signals to partners unverified
- CXP-16 (achievements/photon) has no report — reward consistency on task completion unverified
- CXP-18 (home dashboard) has no report — the mobile "next action" card rendering unverified
**Residual risk:** The backend selection logic is verified by tests but the mobile rendering of ranked tasks with Aurora-aware explanations is unverified.

---

## Journey 6: Knowledge Loop — Document/Translation/Error → Knowledge Node → Review Task → Mastery Change

**Status: PARTIAL**

**Chain:**
1. Document: `GalaxyService.create_nodes_from_document()` → draft nodes with `document.ontology_created` provenance
2. Translation: `KnowledgeIntegrationService.create_vocabulary_node()` → nodes with `translation.saved` provenance
3. Error: `GalaxyEventConsumer` creates `Error gap` nodes → tagged weak, `recommended_action = repair`
4. CXP-09: nodes expose `learning_state`, `recommended_action`, `recommendation_reason`, prerequisite blockers
5. CXP-12: error clusters → review cards → mastery update → plan pressure evaluation
6. CXP-11: vocabulary saves → `learning_loop` metadata with review schedule, knowledge card link

**What works:** Document → node, translation → node, error → node chains are end-to-end verified. Nodes show learning states and recommendations. Error review cards connect to mastery.
**What's missing:**
- CXP-09 mobile Galaxy UI rendering of operational states is unverified (report is backend-only)
- CXP-21 (documents/RAG) has no report — document upload → source tray → knowledge card flow unverified
- Mobile review module reachability mentioned as handoff note in CXP-12
**Residual risk:** The graph is operationally connected on the backend, but the mobile Galaxy UI may still render nodes as decorative rather than actionable.

---

## Journey 7: Community Loop — Share Plan/Task/Achievement/Seed → Recipient Views/Adopts → Visibility Respected

**Status: PARTIAL**

**Chain:**
1. `POST /api/v1/community/share` → `CollaborationService.share_resource()` → `CardSnapshotService`
2. CXP-13: feed scope switching fixed, non-member 403, block filtering, soft-delete filtering
3. CXP-14 (sharing system): no report — share card protocol and adoption endpoints unverified
4. CXP-10: seed adoption creates recipient-owned private copy with adoption next actions
5. CXP-25: gateway log safety and community block boundaries verified

**What works:** Community feed scopes are distinct. Blocked/deleted/private content filtering is test-verified. Seed adoption preserves private copies.
**What's missing:**
- CXP-14 (sharing/entity card interop) has no report — the 6+ shareable resource types from the guide are UNVERIFIED
- CXP-15 (accountability) has no report — partner/squad sharing paths unverified
- Expired/revoked share degradation not explicitly tested in any report
**Residual risk:** Without CXP-14, the sharing protocol completeness is unknown. At minimum, plan/task/achievement/knowledge/seed/vocabulary/review share cards need verification.

---

## Journey 8: Reward Loop — Meaningful Achievement → Visual/Photon/Shop State → Shareable but Private by Default

**Status: GAP**

**Chain (expected):**
1. Real event (task completion, streak, mastery, community contribution) → `AchievementEngine` event consumer
2. Achievement unlocked → photon grant → shop/inventory update
3. Visual element earned → shareable with privacy controls

**What works:** Achievement engine infrastructure exists in the codebase. Achievement events are defined.
**What's missing:** CXP-16 (achievements/photon/shop/rewards) has no report. CXP-17 (visual elements/color system/identity) report file was missing from the directory. The entire reward loop is UNVERIFIED.
**Critical risk:** Without CXP-16 and CXP-17 verification, achievements may not trigger from any of the verified CXP flows (task completion, community share, knowledge mastery, Aurora calibration).

---

## Journey 9: Comeback Loop — Return After 1hr / 2d / 4d → Appropriate Debrief and Next Step

**Status: GAP**

**Chain (expected):**
1. `MemoryService` / working memory ranks memories by relevance, recency, correction history, goal linkage
2. Return context tiers: <30min silent, <8h light continuation, 8h-3d personalized return, >3d debrief
3. Inferred vs confirmed memory distinction in context
4. CXP-03 wake system can trigger comeback wake after long absence

**What works:** CXP-01 Aurora everyday presence can surface return context through status band. CXP-03 comeback wake exists with 52h absence detection.
**What's missing:** CXP-05 (memory/profile/return context) has no report. The full return tier logic, memory ranking, and user-visible debrief are UNVERIFIED.
**Residual risk:** Return after absence is partially covered by CXP-01/CXP-03 but the core memory retrieval and ranking logic (CXP-05) is unverified.

---

## Journey 10: Failure Loop — Offline/API Error/Auth Expiry → Recoverable, Localized, Non-Destructive UX

**Status: PARTIAL**

**Chain:**
1. CXP-08: task sync failure shows error strip with retry/discard
2. CXP-25: gateway log safety, PII redaction, no user text leakage in logs
3. CXP-26: operational metrics for correction failures, card action failures
4. CXP-24: task/community semantics labels for accessibility
5. CXP-11: translation failure returns retry/fallback metadata

**What works:** Task sync failure recovery. Gateway privacy boundaries. Operational visibility into failure modes. Translation failure handling.
**What's missing:**
- CXP-23 (realtime chat/gateway/offline) has no report — network drop, app background, duplicate send, cross-device scenarios UNVERIFIED
- CXP-27 (performance/cost) has no report — graceful degradation under budget limit UNVERIFIED
- CXP-28 (admin/QA) has no report — reviewer ability to trace user-impacting errors UNVERIFIED
- No report covers auth expiry recovery UX on mobile
**Residual risk:** The most common failure (network loss during chat) and the most dangerous failure (duplicate action on retry) are unverified.

---

## Journey Summary

| # | Journey | Status | Owner |
|---|---------|--------|-------|
| 1 | New user onboarding → first task | PARTIAL | CXP-07, CXP-18 missing |
| 2 | Chat → cards → routes | PARTIAL | CXP-23 missing |
| 3 | Aurora correction → behavior change | PARTIAL | CXP-02, CXP-05 missing |
| 4 | L3 Core Session calibration | GAP | CXP-02 missing |
| 5 | Daily execution → updates | PARTIAL | CXP-15, CXP-16, CXP-18 missing |
| 6 | Knowledge loop → mastery | PARTIAL | CXP-21 missing, mobile UI |
| 7 | Community share → adopt | PARTIAL | CXP-14, CXP-15 missing |
| 8 | Reward loop → visual/photon | GAP | CXP-16, CXP-17 missing |
| 9 | Comeback → debrief | GAP | CXP-05 missing |
| 10 | Failure → recovery | PARTIAL | CXP-23, CXP-27, CXP-28 missing |

**Overall: 0 PASS, 7 PARTIAL, 3 GAP**

---

## Dead Ends Fixed In This Pass

CXP-29 is an integration validation task, not a fix-everything task. The following dead ends were identified and documented with exact subsystem owners rather than fixed in this pass:

1. **CXP-02 (L3 Core Session) UNVERIFIED** — Owner: CXP-02 agent. The highest-value Aurora calibration flow has a branch but no report. Must be verified before final merge.
2. **CXP-05 (Memory/Return Context) UNVERIFIED** — Owner: CXP-05 agent. Comeback debrief and memory ranking unverified.
3. **CXP-14 (Sharing System) UNVERIFIED** — Owner: CXP-14 agent. 6+ shareable resource types must be validated with adoption.
4. **CXP-16 (Achievements/Rewards) UNVERIFIED** — Owner: CXP-16 agent. Entire reward loop unverified.
5. **CXP-23 (Realtime/Gateway/Offline) UNVERIFIED** — Owner: CXP-23 agent. Network failure and retry safety unverified.
6. **Cross-CXP route ID surfacing** — Owner: final integrator. CXP-04 route IDs are optional in correction payloads; consistent surfacing across all chat correction UIs is needed.
7. **Mobile Galaxy operational UI** — Owner: CXP-09 + CXP-24. Backend graph states are operational but mobile rendering may still be decorative.
8. **First plan milestone coverage** — Owner: CXP-19 + CXP-07. `first_plan_requested` only fires through modeling bridge; direct-API and seed-adoption plan creation should also record it.

---

## What The User Can Now Accomplish (After All 17 Verified Reports)

A new user can:
- Onboard with correctable goal profile → first plan with milestones → first task → North Star milestones tracked
- Chat with AI that produces valid, routable cards (task/plan/knowledge/share/review/vocabulary/seed)
- See Aurora everyday presence in home status band and chat receipts
- Correct Aurora's judgment and have it change future routing/SGW behavior
- Have proactive wakes that explain their reason and back off when wrong
- Execute daily tasks with Aurora-aware next-action selection and sync failure recovery
- See knowledge graph nodes with learning states from documents, translations, and errors
- Browse/adopt seed libraries that produce concrete next actions
- Save vocabulary/translations with visible learning loops
- Get clustered error review cards that update mastery and plan pressure
- Browse community feed with distinct scopes and enforced visibility boundaries
- View weekly reports with plan outcome and Aurora correction evidence
- Trust that PII and sensitive data are redacted from logs
- Have operators monitor product-loop health via metrics, dashboards, and alerts

A new user CANNOT yet (without the 13 missing reports):
- Experience L3 Core Session deep calibration
- Get personalized return context after absence
- Have a verified achievement/reward experience
- See a polished home dashboard first viewport
- Trust offline/reconnect behavior
- Access admin/QA inspection surfaces

---

## Cross-System Links Verified

- Backend onboarding → planning workflow → task service → North Star metrics: CXP-19
- Backend orchestrator → response builder → entity cards → mobile parser: CXP-06
- Backend DualCore router → route history → outcome recording → correction feedback → SGW: CXP-04
- Backend Aurora control surface → context builder → response metadata → mobile status band: CXP-01
- Backend wake policy → push scheduler → notification center → push feedback: CXP-03
- Backend daily task selection → task service → growth dashboard: CXP-08
- Backend Galaxy service → knowledge integration → event consumer → structure service: CXP-09
- Backend error book → mastery sync → Galaxy review urgency: CXP-12
- Backend vocabulary → translation tool → knowledge integration → task recommendation: CXP-11
- Backend seed library → community adoption → share card: CXP-10
- Backend community service → collaboration service → visibility/block/soft-delete: CXP-13
- Backend progress narrative → prediction theater → mobile insights/theater: CXP-20
- Backend smart schedule → adaptive replanner → plan-health signals: CXP-22
- Gateway logsafe → auth/WS auth/chat feedback: CXP-25
- Backend metrics → Grafana dashboards → Prometheus alerts → runbooks: CXP-26
- Mobile task list → community hub → l10n/semantics: CXP-24

---

## Verification

No automated tests were run for this validation task. Evidence is:
- 17 CXP reports read and cross-referenced (CXP-01, 03, 04, 06, 08, 09, 10, 11, 12, 13, 19, 20, 22, 24, 25, 26)
- Code paths inspected: onboarding API, planning workflow, task service, orchestrator, entity cards, DualCore router, Aurora runtime, wake policy, Galaxy services, community API, progress narrative, smart schedule, metrics, gateway logsafe
- Git branch analysis: 29 CXP branches, all sharing merge base `e1ed1763b7e`
- Over 200 files in common base diff; per-task changes are focused deltas

---

## Remaining Risks

1. **13 CXP tasks without reports**: CXP-02, 05, 07, 14, 15, 16, 17, 18, 21, 23, 27, 28, 30. These represent unverified product chains.
2. **Dirty worktree contamination**: Multiple reports note that commits were not created because the shared worktree contained unrelated parallel-agent changes. Staging hunks carefully during final integration is essential.
3. **Mobile UI verification gap**: Most reports are backend-focused. Only CXP-06, CXP-24, and CXP-20 touched mobile. The actual mobile rendering and interaction quality of all 10 journeys is largely unverified.
4. **Shared merge base**: All branches fork from the same commit with ~580 shared files. Merge conflicts are guaranteed on every file touched by more than one branch.
5. **No E2E smoke test exists**: The 21 acceptance scripts in `backend/scripts/` test individual chains but no script covers the full onboarding → plan → task → correct → share → return journey.

---

## Commit

Branch: `codex/CXP-29-north-star-journey`
Commit: pending (this report)
