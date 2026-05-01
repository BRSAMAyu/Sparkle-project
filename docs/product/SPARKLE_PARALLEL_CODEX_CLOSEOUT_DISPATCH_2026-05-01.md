# Sparkle Parallel Codex Closeout Dispatch

> Created: 2026-05-01  
> Purpose: A dispatch-ready work plan for parallel Codex agents to close the remaining Sparkle roadmap, audit, architecture, Aurora, UX, infra, and production-readiness gaps.  
> Primary workflow documents: `docs/product/SPARKLE_ROADMAP_v3_2026-04-28.md`, `docs/product/SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md`, `docs/product/SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md`.

---

## 0. Executive Decision

Yes, Sparkle can use 20-30 Codex agents in parallel, but only if the work is split by ownership boundary and then integrated by one final closeout owner.

The right model is not "30 agents all fix everything." The right model is:

1. Each agent owns one bounded subsystem or experience chain.
2. Each agent verifies the audit claim before changing code.
3. Each agent updates the assigned docs/tracker section with evidence.
4. Each agent commits a focused branch/commit.
5. A final integrator reconciles protocol contracts, route collisions, migration order, tests, and product experience consistency.

Important: Some audit claims may already be stale or partially fixed. Every agent must re-check current code before implementing. Do not blindly rewrite working systems because a report says they are broken.

---

## 1. Non-Negotiable Rules For Every Agent

1. Read `AGENTS.md`, Roadmap v3, Tracker, Final Acceptance Ledger, and this dispatch file before editing.
2. Inspect `git status --short` before editing. Never revert unrelated user or agent changes.
3. Prefer existing architecture and local patterns. Do not invent a second framework for a solved local problem.
4. For protocol boundaries, update source of truth first:
   - gRPC: `proto/agent_service.proto`, then generated code.
   - DB: Alembic migration + schema/query updates where needed.
   - Flutter localization: ARB/source l10n flow, not hardcoded strings.
5. Every claim must end with evidence:
   - tests run,
   - lint/analyze result,
   - files changed,
   - remaining risk.
6. Every agent must update docs:
   - Append status to this file under the assigned agent section if working in a shared branch.
   - Update `SPARKLE_ROADMAP_v3_TRACKER_2026-04-28.md` or `SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md` when closing/reopening a finding.
7. Commit only your own scope. Do not include unrelated dirty files.
8. If a task reveals a larger architectural conflict, stop at a written design note and mark it `Needs Integrator Decision`.

---

## 2. Parallel Safety Map

### Safe To Run In Parallel

These can run concurrently with low conflict risk:

- Infra/ops docs and compose hardening.
- Flutter i18n/accessibility/design-system sweeps by feature folder.
- Go middleware tests and error-sanitization.
- Python exception handling by package.
- North Star metrics service and dashboard work.
- Legal/privacy docs.
- CI/CD version and dependency scanning.

### Needs Sequencing Or Strong Coordination

These touch central files and must be coordinated:

- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/services/agent_grpc_service.py`
- `backend/gateway/internal/handler/chat_orchestrator*.go`
- `mobile/lib/app/routes.dart`
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`
- `proto/agent_service.proto`

For these, agents should produce small focused commits and clearly state expected integration order.

---

## 3. Definition Of Done

A task is not done when code compiles. It is done when:

1. The target user-visible or production behavior is achieved.
2. Tests cover the failure mode that caused the task.
3. The tracker/ledger says what changed and why it is now safe.
4. No unrelated files were modified.
5. Existing roadmap claims are corrected if reality changed.

For Aurora-related tasks, "done" means the user experience becomes measurably better: Sparkle should feel like it noticed, understood, remembered, and adjusted.

---

## 4. Agent Task Index

| Agent | Priority | Theme | Primary Outcome |
|---|---:|---|---|
| C00 | P0 | Integration commander | Final merge and cross-system acceptance |
| C01 | P0 | DualCoreRouter wiring | Dual-core routing actually affects orchestration |
| C02 | P0 | Clarify stage | Sufficiency and goal quality checks gate clarification |
| C03 | P0 | Adapt stage | AdaptiveReplanner has real triggers and outcomes |
| C04 | P0 | Cognitive/Profile services | CognitiveService and ProfileWriteService enter production loop |
| C05 | P0 | Secret exposure | Real secrets removed, ignored, rotated, and documented |
| C06 | P0 | Privacy/PII | Shadow/privacy modes never leak raw sensitive text |
| C07 | P0 | Container security | API containers run non-root in prod/local where viable |
| C08 | P0 | gRPC registration | Proto-defined services are registered or explicitly deprecated |
| C09 | P0 | Disaster recovery | RTO/RPO, backup, restore, and regional failure runbook exist |
| C10 | P1 | North Star metrics | Exam pass and 7-day goal completion are tracked end-to-end |
| C11 | P1 | Aurora Bayesian learner | Stage 23 learner becomes real and persistent |
| C12 | P1 | Aurora correction UX | Freeform and chip corrections truly reach learning loop |
| C13 | P1 | Aurora proactive experience | Multi-device proactive interaction becomes coherent |
| C14 | P1 | Go WS/STT hardening | Rate limits, races, raw error leaks closed |
| C15 | P1 | Go test coverage | Critical middleware and gateway coverage improved |
| C16 | P1 | Flutter failures | Typed failure model and user-facing recovery patterns |
| C17 | P1 | Design system/dark mode | Raw black/white colors migrated by feature groups |
| C18 | P1 | Accessibility | Semantics and keyboard/screen-reader basics added |
| C19 | P1 | OpenClaw module | Module has route, screen, provider, and real user flow |
| C20 | P1 | Reviews route | Implemented reviews module becomes reachable |
| C21 | P1 | Provider lifecycle | State retention strategy prevents destructive refreshes |
| C22 | P1 | i18n | Remaining hardcoded Chinese strings are localized |
| C23 | P1 | Monitoring config | Prometheus/Alertmanager/Grafana secret/rule gaps closed |
| C24 | P1 | Production workers | Celery, Tempo retention, backup posture productionized |
| C25 | P1 | Compliance | Privacy policy, ToS, GDPR/export/delete flow mapped |
| C26 | P2 | Event system | Dual event systems reconciled or clearly separated |
| C27 | P2 | Python exceptions | Silent exception debt reduced by risk category |
| C28 | P2 | Flutter technical debt | BGM split, SSE UTF-8, API catch/rethrow, offline indicators |
| C29 | P2 | CI/CD | Version consistency, lockfiles/scanning, Actions modernization |
| C30 | P2 | Final E2E acceptance | Cross-system scenario tests and launch checklist |

---

## 5. Detailed Dispatch Packets

### C00 — Integration Commander

**Goal**: Make parallel output converge into one coherent product and architecture.

**Owns**:
- Final merge order.
- Conflict resolution.
- Cross-agent regression plan.
- Final acceptance ledger update.

**Expected final effect**:
Sparkle has no contradictory route/proto/config behavior across agents. The Roadmap Tracker matches actual code reality.

**Must do**:
- Before merging agent work, run `git status`, inspect each diff, and check docs evidence.
- Re-run at least:
  - `cd backend && pytest` targeted suites for changed Python paths.
  - `cd backend/gateway && go test ./...` or scoped equivalent.
  - `cd mobile && flutter analyze --no-fatal-infos`.
  - Key Flutter smoke/widget tests affected by mobile agents.
- Update final closeout section in `SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md`.

**Done when**:
All accepted branches are integrated, critical tests pass, and remaining risks are explicitly listed.

---

### C01 — DualCoreRouter Production Wiring

**Audit basis**: `DualCoreRouter.route()` may be instantiated/imported but not meaningfully called.

**Goal**:
Dual-core routing must influence live orchestration decisions, not sit as a decorative module.

**Do not hardcode an implementation before reading**:
Start by tracing `orchestrator.py`, `orchestrator_production.py`, `dual_core_router.py`, `routing_engine.py`, and tests.

**Expected final effect**:
For a real chat/request path, the system produces a `DualCoreDecision` or equivalent routing artifact, stores it in state/context, and downstream prompt/UX/metadata can observe it.

**Likely touchpoints**:
- `backend/app/orchestration/orchestrator.py`
- `backend/app/orchestration/orchestrator_production.py`
- `backend/app/orchestration/dual_core_router.py`
- routing tests

**Acceptance criteria**:
- A test proves a live orchestration path invokes dual-core routing.
- A test proves the routing decision affects prompt, mode, constraints, or metadata.
- If current architecture already routes elsewhere, document the real path and remove stale/dead imports instead of duplicating logic.

---

### C02 — Clarify Stage: Sufficiency + Goal Quality

**Audit basis**: `SufficiencyChecker` and `GoalQualityEvaluator` may be imported but not used.

**Goal**:
Clarify phase should detect underspecified goals and weak goal quality before execution/planning proceeds.

**Expected final effect**:
When the user request lacks enough information, Sparkle asks high-value clarification or creates a safe provisional plan with explicit assumptions. When a goal is low quality, the system improves or flags it.

**Likely touchpoints**:
- `backend/app/orchestration/orchestrator.py`
- sufficiency/goal quality modules
- response builder or UX envelope if clarification is user-visible

**Acceptance criteria**:
- Tests for underspecified request, sufficient request, and weak goal.
- No extra clarification spam for normal chat.
- Tracker records the exact clarify gate behavior.

---

### C03 — Adapt Stage: AdaptiveReplanner

**Audit basis**: `AdaptiveReplanner` has no production trigger path.

**Goal**:
Adapt stage must react when actual progress diverges from plan, user corrections, repeated failure, or context change.

**Expected final effect**:
When outcome/telemetry indicates the current strategy is failing, Sparkle proposes or applies a revised plan with a traceable reason.

**Likely touchpoints**:
- adaptive replanner service/module
- outcome tracker/learning guard
- task/plan services
- orchestration state

**Acceptance criteria**:
- A failing outcome triggers replanning in a test.
- Replan includes reason/evidence and does not overwrite user-owned plan fields silently.
- User-visible response distinguishes "I changed the plan because..." from normal suggestions.

---

### C04 — CognitiveService + ProfileWriteService Production Loop

**Audit basis**: Cognitive and profile writing may exist but not feed live orchestration.

**Goal**:
User model updates and cognitive prism insights should be read and written by the real loop.

**Expected final effect**:
Sparkle should learn durable user preferences/constraints from interaction, apply them later, and expose enough explanation for trust.

**Likely touchpoints**:
- `backend/app/services/cognitive_service.py`
- `backend/app/services/profile_write_service.py`
- memory/profile APIs
- orchestration context builder

**Acceptance criteria**:
- Test: user correction/preference writes profile update.
- Test: later request reads that profile and changes behavior.
- Guardrails: low-confidence inferred preferences are marked tentative or require confirmation.

---

### C05 — Secret Exposure Remediation

**Audit basis**: `.env` may contain real API keys and be git-tracked.

**Goal**:
No real secrets remain in tracked files or logs. Rotation plan exists.

**Important**:
This task may require human rotation outside code. Do not print secret values in logs or docs.

**Expected final effect**:
Repo contains examples/placeholders only; production starts fail-fast if secrets are missing; leaked keys are recorded for rotation without copying values.

**Likely touchpoints**:
- `.gitignore`
- `.env.example`
- secret validation scripts
- docs/ops secret rotation runbook

**Acceptance criteria**:
- `git ls-files` does not include real `.env`.
- Secret scanner or grep shows no known provider key patterns in tracked files.
- Runbook says which providers must be rotated.

---

### C06 — Privacy / PII Shadow Mode

**Audit basis**: PII shadow mode may return raw text.

**Goal**:
Privacy modes must never leak raw sensitive text when configured to redact, even in shadow/test mode.

**Expected final effect**:
Shadow mode can record comparison telemetry internally, but external outputs use safe text.

**Likely touchpoints**:
- `backend/app/aurora/privacy.py`
- privacy tests
- telemetry/audit logs

**Acceptance criteria**:
- Tests for email, phone, name-like tokens, and mixed Chinese/English PII.
- Shadow mode test proves returned text is redacted or explicitly safe.
- Logs do not store raw PII unless a documented secure audit sink exists.

---

### C07 — Container Non-Root Hardening

**Audit basis**: compose may override Dockerfile non-root settings.

**Goal**:
Production and local containers should run as non-root unless there is a documented reason.

**Likely touchpoints**:
- `docker-compose.yml`
- `docker-compose.prod.yml`
- backend Dockerfiles
- volume permission scripts

**Acceptance criteria**:
- API container runs as non-root in prod compose.
- Required write dirs have correct ownership.
- Healthchecks still pass.

---

### C08 — gRPC Service Registration / Deprecation

**Audit basis**: Community/STT/Inference services may be in proto but not registered in `grpc_server.py`.

**Goal**:
Every proto service is either implemented and registered, or explicitly marked REST-only/deprecated with generated client expectations updated.

**Expected final effect**:
No client believes an RPC exists when the server cannot serve it.

**Likely touchpoints**:
- `proto/agent_service.proto`
- `backend/app/grpc_server.py`
- generated Go/Python code
- gateway client code
- docs/API

**Acceptance criteria**:
- `grpcurl list` or equivalent test proves registered services.
- If deprecating, docs and clients no longer depend on the RPC.
- Integration tests cover at least one method per registered service.

---

### C09 — Disaster Recovery Plan

**Goal**:
Sparkle has an operational RTO/RPO target, backup/restore runbook, and regional failure procedure.

**Expected final effect**:
An operator can answer: what data can be lost, how long recovery takes, and exactly what command/procedure to run.

**Likely touchpoints**:
- `docs/ops/`
- backup scripts
- monitoring runbooks

**Acceptance criteria**:
- RTO/RPO documented by subsystem: Postgres, Redis, object storage, vector/index data, uploaded files.
- Restore drill checklist exists.
- Missing automation is tracked as a follow-up with priority.

---

### C10 — North Star Metrics

**Goal**:
Track exam pass probability/outcomes and 7-day goal completion as first-class metrics.

**Expected final effect**:
Sparkle can tell whether the product helps a zero-base learner pass quickly and complete goals.

**Likely touchpoints**:
- backend metrics/events
- task/plan outcome models
- analytics dashboard
- Grafana/Prometheus or product analytics

**Acceptance criteria**:
- Metric definitions are documented.
- Backend emits/records events.
- Dashboard/API can query trend.
- Tests cover event write and aggregation.

---

### C11 — Aurora Bayesian Learner

**Audit basis**: Bayesian learner may be a stub.

**Goal**:
Replace placeholder posterior updates with a small but real Bayesian learner.

**Expected final effect**:
Aurora confidence updates from observed outcomes/corrections, persists posterior state, and uses it to calibrate future interventions.

**Likely touchpoints**:
- Aurora Stage 23 modules
- outcome/correction feedback
- Redis/Postgres persistence

**Acceptance criteria**:
- Beta/Bernoulli or appropriately documented model exists.
- Sequential update tests prove posterior changes.
- Persistence tests prove state survives process restart.
- Downstream policy uses posterior uncertainty, not just hardcoded confidence.

---

### C12 — Aurora Correction UX And Learning Loop

**Current known gap**:
Dashboard freeform correction now captures text in UI, but `AuroraTelemetryService.recordStatusBandCorrection()` does not send `freeform_text`. Chat chips now send `option.label`, but the whole correction path needs tests and cleanup.

**Goal**:
When a user says Aurora is wrong, Sparkle must capture what was wrong, send structured telemetry, continue the conversation naturally, and improve future behavior.

**Likely touchpoints**:
- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- `mobile/lib/features/chat/presentation/widgets/contextual_correction_bar.dart`
- `mobile/lib/features/aurora/data/services/aurora_telemetry_service.dart`
- `backend/app/api/v1/aurora.py`
- `backend/app/aurora/runtime_v1/correction_feedback.py`

**Expected final effect**:
- Freeform correction dialog returns text only on submit; cancel sends nothing.
- Telemetry payload includes `freeform_text` for freeform correction.
- Chat receives user-readable text, not internal semantic tokens.
- Backend correction processor receives enough evidence to update/retract/learn.

**Acceptance criteria**:
- Flutter tests prove cancel does not send telemetry.
- Flutter tests prove freeform sends `freeform_text`.
- Backend test proves freeform text reaches correction processor.
- Chat chip test proves semantic token is not displayed as user message.

---

### C13 — Aurora Proactive Multi-Device Experience

**Goal**:
Make Aurora proactive nudges feel timely, respectful, multi-device aware, and controllable.

**Expected final effect**:
Aurora should not feel like random push notifications. It should feel like a perceptive layer that knows when to stay quiet, when to surface, and how to explain itself.

**Scope**:
- Proactive wake policy.
- Push/deep-link behavior.
- Cooldown/quiet hours.
- Cross-device state consistency.
- User controls and correction feedback.

**Acceptance criteria**:
- One end-to-end proactive scenario documented and tested:
  "user is stuck -> Aurora notices -> sends/raises nudge -> user corrects/accepts -> system records outcome."
- User can understand why Aurora appeared.
- Repeated dismissals reduce future intrusiveness.

---

### C14 — Go Gateway WS/STT Hardening

**Audit basis**:
Idle timer/write race, missing per-connection rate limits in STT/proxy, raw error leakage.

**Goal**:
Gateway WS/STT behavior is safe under slow, noisy, or malicious clients.

**Likely touchpoints**:
- `backend/gateway/internal/handler/chat_orchestrator.go`
- `backend/gateway/internal/handler/stt_handler.go`
- `backend/gateway/internal/handler/websocket_proxy.go`
- handler error responses

**Acceptance criteria**:
- Per-connection rate limits for STT/proxy or documented equivalent.
- Raw internal errors are mapped to safe public messages.
- Tests for rate-limit rejection and safe error response.
- Race-sensitive changes tested with `go test -race` where feasible.

---

### C15 — Go Critical Middleware Coverage

**Goal**:
Add tests for `ws_auth.go`, `distributed_rate_limiter.go`, and other security middleware.

**Expected final effect**:
Auth/rate-limit regressions are caught before deployment.

**Acceptance criteria**:
- Tests cover valid token, invalid token, missing token, query token policy, rate-limit allow/reject, Redis failure behavior.
- Coverage improves for gateway critical path.

---

### C16 — Flutter Typed Failure Model

**Audit basis**: `core/errors/failures.dart` may be empty and errors are bare exceptions.

**Goal**:
Introduce typed failures that let UI show better recovery paths without massive rewrites.

**Expected final effect**:
Network/auth/offline/server/validation failures are distinguishable and can map to user-facing copy.

**Acceptance criteria**:
- Failure types exist with a conservative mapper.
- At least two high-impact repositories/providers adopt them.
- UI shows different recovery for offline vs auth vs server.

---

### C17 — Flutter Design System / Dark Mode

**Goal**:
Reduce raw `Colors.white/black` usage and align surfaces with design system tokens.

**Scope guidance**:
Split by feature folder. Do not run a blind global replace.

**Expected final effect**:
Dark mode and theme consistency improve without visual regressions.

**Acceptance criteria**:
- Feature-scoped migration PR/commit.
- Before/after screenshots or widget tests for representative screens.
- Raw colors remain only where intentionally documented.

---

### C18 — Accessibility / Semantics

**Goal**:
Core flows become usable with screen readers and semantic navigation.

**Priority flows**:
- Login/onboarding.
- Dashboard/Aurora status band.
- Chat correction chips.
- Task execution.
- Community feed.

**Acceptance criteria**:
- Semantics labels for icon-only controls and critical status chips.
- Tap targets meet size expectations.
- Widget tests inspect critical semantics nodes where practical.

---

### C19 — OpenClaw Module Completion

**Goal**:
OpenClaw should stop being a placeholder and become a reachable, understandable module.

**Expected final effect**:
User can navigate to OpenClaw, understand connection/execution status, and perform at least one meaningful action or see a clear setup path.

**Acceptance criteria**:
- Route, screen, provider/state, empty/error/loading states.
- If backend is not ready, product-grade disabled/setup state with docs link.
- Tests for route and basic UI.

---

### C20 — Reviews Route Integration

**Goal**:
Implemented reviews functionality must be reachable from the app.

**Expected final effect**:
Users can navigate into reviews from the relevant context, not only via dead code.

**Acceptance criteria**:
- GoRouter route exists.
- Entry point exists from task/chat/learning surface as appropriate.
- State and error handling tested.

---

### C21 — Provider Lifecycle / State Retention

**Audit basis**: providers may refresh destructively when tabs switch.

**Goal**:
Important user state should survive normal tab navigation without stale data becoming permanent.

**Expected final effect**:
No unnecessary reload flicker for dashboard/chat/task/community core state.

**Acceptance criteria**:
- Identify providers that should use `keepAlive` or cache policy.
- Add lifecycle strategy per major feature.
- Tests or manual evidence for tab switch retention.

---

### C22 — i18n Completion

**Goal**:
Remove remaining hardcoded user-facing Chinese/English strings from launch-critical flows.

**Scope guidance**:
Prioritize first viewport and failure paths. Do not chase debug strings/comments.

**Acceptance criteria**:
- Script/search report before and after.
- ARB entries added.
- Generated localization code updated.
- `flutter analyze` has no new errors.

---

### C23 — Monitoring Configuration

**Audit basis**:
Prometheus missing mounted rule files; Alertmanager/Prometheus may hardcode credentials.

**Goal**:
Monitoring stack starts cleanly and secrets are environment-driven.

**Acceptance criteria**:
- Referenced rules exist or config no longer references them.
- No hardcoded SMTP/password secrets.
- Compose config validates.
- Runbook explains required env vars.

---

### C24 — Production Workers, Tempo, Backup

**Goal**:
Production deployment includes required async workers, adequate trace retention, and credible backup posture.

**Scope**:
- Celery worker in prod compose/K8s manifests.
- Tempo retention policy.
- Postgres backup/WAL/encryption/offsite plan.

**Acceptance criteria**:
- Worker service defined and healthchecked.
- Trace retention documented and configured for production.
- Backup restore drill documented or scripted.

---

### C25 — Privacy / Legal / GDPR Framework

**Goal**:
Give Sparkle a basic launch-grade compliance frame.

**Expected final effect**:
Users can understand data use, request export/delete, and see privacy controls.

**Acceptance criteria**:
- Privacy policy draft.
- Terms/service draft.
- Data export/delete flow mapped to existing APIs or tracked gaps.
- Sensitive AI memory/profile behavior explained plainly.

---

### C26 — Event System Reconciliation

**Audit basis**:
`event_bus.py` and `event_types.py` may represent two partially overlapping event systems.

**Goal**:
Clarify or unify event type ownership so signals do not disappear in translation.

**Acceptance criteria**:
- Inventory of event types and consumers.
- Unused types removed or documented.
- Tests prove critical event routing to Spine/Aurora/task/community.

---

### C27 — Python Silent Exception Cleanup

**Goal**:
Reduce `except Exception: pass` in user-impacting and data-impacting paths.

**Scope guidance**:
Do not remove all silent catches. Categorize:
- user action,
- data write,
- telemetry/best-effort,
- optional UI/formatting.

**Acceptance criteria**:
- Top risk paths log or surface errors.
- Best-effort paths remain safe and documented.
- Tests for at least five fixed failure paths.

---

### C28 — Flutter Technical Debt: BGM / SSE / API / Offline UX

**Goal**:
Improve reliability and maintainability in high-impact mobile technical debt.

**Subtasks**:
- Split giant BGM service by responsibility.
- Fix SSE UTF-8 chunk boundary decoding.
- Audit API client catch/rethrow behavior.
- Add user-visible offline queue indicator for queued chat/messages.

**Acceptance criteria**:
- Each subtask can be separate commit.
- Tests for SSE multibyte boundary.
- Offline indicator is visible and localized.
- BGM split preserves behavior.

---

### C29 — CI/CD And Dependency Hygiene

**Goal**:
CI versions and dependency hygiene should match production reality.

**Scope**:
- Flutter version consistency.
- Postgres version consistency.
- Outdated Actions versions.
- Go vulnerability scanning.
- Python dependency locking strategy.

**Acceptance criteria**:
- CI matrix versions documented and aligned.
- Vulnerability scan added or documented.
- Dependency lock decision recorded.
- CI workflow validation passes.

---

### C30 — Final E2E Acceptance And Launch Checklist

**Goal**:
Create the final proof that the product is not just component-complete but experience-complete.

**Required scenarios**:
1. New user -> onboarding -> goal -> plan -> task card -> execution -> reflection.
2. Aurora notices risk -> user corrects -> Aurora learns -> future response changes.
3. Document upload -> knowledge/galaxy retrieval -> task material selection.
4. Community share -> feed/goal mates/following visibility -> board/task handoff.
5. Offline/poor network -> queued action -> recovery.
6. Production deploy smoke -> monitoring -> rollback/drain.

**Acceptance criteria**:
- Scenario checklist with exact commands/manual steps.
- Automated coverage where feasible.
- Remaining manual ops items clearly separated from code gaps.

---

## 6. Recommended Parallel Wave Plan

### Wave 1: Stop Launch Blockers

Run these first:

- C01, C02, C03, C04: core growth loop wiring.
- C05, C06, C07, C08, C09: security/proto/DR.
- C12: Aurora correction loop, because it is a core product trust path.

Do not merge C01-C04 independently without C00 review because they share orchestration state.

### Wave 2: Production Hardening And UX Trust

Run after Wave 1 is underway:

- C10, C11, C13, C14, C15.
- C16, C18, C21.
- C23, C24, C25.

### Wave 3: Broad Polish And Debt Reduction

Run once critical paths are stable:

- C17, C19, C20, C22.
- C26, C27, C28, C29.
- C30 begins collecting final scenario evidence.

---

## 7. Final Integrator Checklist

C00 should not accept the whole batch until:

1. Secrets are no longer tracked and rotation is documented.
2. DualCore/Clarify/Adapt/Profile loops have tests proving live invocation.
3. Aurora freeform correction sends real `freeform_text` and is consumed by backend learning.
4. gRPC proto/server/client reality is consistent.
5. Gateway/WebSocket/STT hardening has tests.
6. Launch-critical Flutter screens pass accessibility/i18n/design-system review.
7. Monitoring/worker/backup/legal launch docs exist.
8. E2E scenario checklist is updated with evidence.
9. Tracker and final acceptance ledger match code reality.

---

## 8. Current Known Dirty Worktree Warning

At the time this dispatch was created, these files had uncommitted local changes and should be treated as active Aurora correction work:

- `mobile/lib/features/home/presentation/screens/dashboard_screen.dart`
- `mobile/lib/features/chat/presentation/screens/chat_screen.dart`
- `mobile/lib/features/chat/presentation/widgets/contextual_correction_bar.dart`

Agents should not overwrite those files unless they are assigned C12 or explicitly coordinated by C00.

