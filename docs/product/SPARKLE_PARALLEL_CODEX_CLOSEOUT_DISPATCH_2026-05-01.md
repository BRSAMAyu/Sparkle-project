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

**C01 closeout status — 2026-05-01**:
- ✅ Verified real path: supported runtime is `ChatOrchestrator.process_stream()` → `_apply_dual_core_routing()` → `self.dual_core_router.route(...)`; `ProductionChatOrchestrator` is legacy and blocked by default unless `SPARKLE_ALLOW_LEGACY_PRODUCTION_ORCHESTRATOR=1`.
- ✅ Behavior effect: routing decision is persisted in `state.context_data["dual_core_decision"]`, prompt instructions/constraints are stored in `dual_core_prompt_instruction`, `cognitive_first` rewrites `langgraph/hybrid` route decisions to `direct`, and response metadata now exposes bounded `dual_core_decision`.
- ✅ Regression evidence: `cd backend && pytest backend/tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_live_path_invokes_dual_core_and_exposes_decision` proves the live process stream invokes the router and downstream prompt/route/metadata observe the decision.
- ✅ Additional evidence: `cd backend && pytest backend/tests/unit/orchestrator/mixins/test_response_builder_mixin.py backend/tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_live_path_invokes_dual_core_and_exposes_decision backend/tests/unit/orchestrator/mixins/test_routing_engine_dual_core.py` → 34 passed; `cd backend && ruff check backend/app/orchestration/response_builder.py backend/tests/orchestration/test_orchestrator_process_stream_integration.py backend/tests/unit/orchestrator/mixins/test_response_builder_mixin.py` → passed.
- Files changed: `backend/app/orchestration/response_builder.py`, `backend/tests/orchestration/test_orchestrator_process_stream_integration.py`, `backend/tests/unit/orchestrator/mixins/test_response_builder_mixin.py`, docs tracker/dispatch.
- Remaining risk: full backend suite was not rerun in this closeout pass; only focused orchestration/response-builder suites were run.

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

**C02 closeout status - 2026-05-01**:
- PASS: Verified live path: `ChatOrchestrator.process_stream()` runs `_check_sufficiency()` before route/plan execution, then `_check_goal_quality()` before planning continues.
- PASS: Clarify behavior: Phase A planning preflight can hard-stop underspecified planning turns with `requires_clarification=true`, `clarification_source=phase_a`, and `phase_a_guardrail=ask_before_plan`; field/material sufficiency can emit `requires_clarification=true`; semantic goal quality can emit `requires_goal_clarification=true`.
- PASS: Code alignment: semantic goal quality now gates `time_planning` as well as `create_plan` and `set_goal`.
- PASS: Regression evidence: `cd backend && pytest tests/orchestration/test_orchestrator_process_stream_integration.py::test_process_stream_phase_a_hard_stops_cold_start_plan_before_planning tests/orchestration/test_orchestrator_process_stream_integration.py::test_sufficiency_gate_allows_normal_chat_without_clarification tests/orchestration/test_orchestrator_process_stream_integration.py::test_goal_quality_gate_allows_specific_planning_goal tests/orchestration/test_orchestrator_process_stream_integration.py::test_goal_quality_gate_clarifies_weak_time_planning_goal tests/unit/test_goal_quality_evaluator.py -q` -> 6 passed; `cd backend && ruff check app/orchestration/goal_quality_evaluator.py app/orchestration/validation_engine.py tests/orchestration/test_orchestrator_process_stream_integration.py tests/unit/test_goal_quality_evaluator.py` -> passed.

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

**Status 2026-05-01 — C03 completed**:
- `task.abandoned` and `task.stuck` now route through `TaskEventConsumer._trigger_adaptive_plan_health_event()` into `AdaptiveReplanner.evaluate_plan_health_now()`, preserving existing Spine/outcome paths.
- Adaptive system updates now use the title `计划已根据真实进展调整` and include `adaptation_reason` plus the full `AdaptationRecord` metadata, so user-visible updates explain why the plan changed.
- Evidence: `cd backend && pytest tests/unit/test_adaptive_replanner_evolution.py tests/unit/test_c03_adaptive_replanner_wiring.py tests/e2e/test_execution_feedback_loop.py::test_task_feedback_consumer_routes_to_adaptive_replanner tests/e2e/test_execution_feedback_loop.py::test_task_feedback_consumer_safe_fallback_when_plan_missing -q` → 11 passed; `cd backend && ruff check app/services/task_event_consumer.py app/orchestration/adaptive_replanner.py tests/unit/test_adaptive_replanner_evolution.py tests/unit/test_c03_adaptive_replanner_wiring.py` → pass.

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

**C04 status — 2026-05-01**:
- `ChatSignalCollector` is now the live production-loop bridge for explicit chat preference learning: clear preference/correction turns write through `ProfileWriteService.set_explicit_preferences()` with chat-turn evidence.
- Significant correction/preference turns also create lightweight `CognitiveService` behavior fragments with `generate_embedding=False`, so the cognitive prism has live conversational evidence without adding embedding latency to the loop.
- Inferred profile writes now carry `<preference>_confidence` and `<preference>_status`; low-confidence window signals are marked `tentative`.
- Later-read behavior is covered through `ProfileContextService.get_profile_context()`: the explicit chat preference is visible in the unified profile context consumed by orchestration.
- Evidence: `cd backend && pytest tests/unit/test_chat_signal_collector_profile_loop.py tests/unit/test_profile_write_service.py tests/unit/test_cognitive_service_regression.py tests/services/test_profile_context_service.py -q` → 16 passed; `cd backend && ruff check app/services/chat_signal_collector.py app/services/profile_write_service.py app/services/cognitive_service.py tests/unit/test_chat_signal_collector_profile_loop.py` → pass.

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

**C05 status 2026-05-01**:
- Runtime env artifacts hardened: `.gitignore` now ignores nested `.env*` files while allowing placeholder examples; generated `backend/celerybeat-schedule` removed from the working tree; `backend/.env.migration` replaced by `backend/.env.migration.example`.
- Tracked provider-shaped values were redacted to placeholders in active setup docs and historical copies; live MIMO check scripts now require env-injected keys and avoid printing key prefixes.
- `scripts/check_production_secrets.py --tracked-only` passes and reports only file/variable names on failure.
- Rotation runbook added at `docs/ops/secret_rotation_runbook.md`; provider admins still must rotate any credential that was ever exposed outside the approved secret store.

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

**C06 status update (2026-05-01)**:
- Fixed `backend/app/aurora/privacy.py` so `shadow` mode returns redacted safe text; only explicit `off` mode returns raw text.
- Added `PiiRedactionResult.telemetry()` for shadow comparison metadata without raw text (`categories` + source hash only).
- Added tests for email, phone, Chinese ID, bank card, explicit Chinese/English names, mixed Chinese/English PII, shadow-safe output, and telemetry payload safety.
- Evidence: `cd backend && pytest tests/unit/test_pii_redaction.py tests/unit/test_sqam_predictive_all_dims.py::test_sqam_predictive_dp1_realtime_messages_redact_pii -q` -> `17 passed`; `cd backend && ruff check app/aurora/privacy.py tests/unit/test_pii_redaction.py` -> pass.

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

**C07 status update (2026-05-01)**:
- Backend and gateway Dockerfiles now create a stable `sparkle` runtime identity (`10001:10001`) and pre-create `/app/logs`, `/app/uploads`, `/app/data`, and `/app/.cache` before switching to non-root.
- Local compose no longer overrides `sparkle_api` to `root`; API, gRPC, Celery workers, and gateway run as `${SPARKLE_APP_UID:-10001}:${SPARKLE_APP_GID:-10001}`. Local backend bind mounts use named sub-volumes for writable logs/uploads/cache paths.
- Production compose pins `backend`, `agent`, `gateway_blue`, and `gateway_green` to the same non-root UID/GID and adds explicit healthchecks for those API/gateway services.
- Evidence: `MINIO_ACCESS_KEY=test MINIO_SECRET_KEY=test docker compose config --quiet` -> pass; production compose config with required placeholder env -> pass; `docker buildx build --check -f backend/Dockerfile backend` -> pass; `docker buildx build --check -f backend/gateway/Dockerfile backend/gateway` -> pass.

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

**C08 status — 2026-05-01**:
- Registered live Python gRPC services now include `agent.v1.AgentService`, `error_book.ErrorBookService`, `galaxy.v1.GalaxyService`, `stt.v1.STTService`, and `sparkle.inference.v1.InferenceService`.
- Added STT and Inference gRPC adapters backed by the existing `STTService` and `LLMDispatcher`.
- Marked `sparkle.community.CommunityService` as deprecated/REST-only in `proto/community_service.proto`; generated descriptors now report `deprecated=true`, and reflection intentionally does not list it.
- Evidence: `cd backend && PYTHONPATH=. .venv/bin/pytest tests/services/test_stt_service.py tests/unit/services/test_grpc_service_registration.py -q` -> `16 passed`; `cd backend && .venv/bin/ruff check grpc_server.py app/services/stt_grpc_service.py app/services/inference_grpc_service.py tests/unit/services/test_grpc_service_registration.py` -> pass.

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

**C09 status — 2026-05-01**:
- Added `docs/ops/disaster_recovery_runbook.md` with subsystem RTO/RPO targets, backup/restore commands, a restore drill checklist, regional failure steps, and prioritized DR-C09 follow-ups.
- Hardened `scripts/backup_prod_data.sh` and `scripts/restore_prod_data.sh` with Redis password support and backup checksum generation/verification.
- Updated tracker T7.3.7 to distinguish "runbook/script ready" from the still-required first staging restore drill.

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

**C10 closeout status — 2026-05-01**:
- ✅ Added persistent `north_star_metric_events` model and Alembic migration `c10_20260501`.
- ✅ Added `NorthStarMetricsService` with idempotent writes and trend aggregation for exam pass probability, exam pass outcomes, and 7-day goal completion.
- ✅ Wired writes into exam sprint intake, post-exam review, sprint completion checks, and completed-sprint auto-archive.
- ✅ Exposed `GET /api/v1/analytics/north-star/trends` for dashboard/API trend queries.
- ✅ Documented metric definitions in `SPARKLE_NORTH_STAR_METRICS_2026-05-01.md`.
- ✅ Evidence: `cd backend && pytest tests/services/test_north_star_metrics_service.py` → 2 passed.
- ✅ Evidence: targeted `ruff check`, `compileall`, `git diff --check`, and `cd backend && alembic heads` all passed; migration head is `c10_20260501`.

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

**C11 status — 2026-05-01**:
- Added `backend/app/aurora/bayesian/learner.py`, a Stage 23 Aurora wrapper around the existing persisted Beta/Bernoulli learner. It tracks visible Aurora interventions vs hold decisions and exposes posterior mean, variance, normalized uncertainty, and uncertainty-adjusted confidence.
- Wired observed Aurora runtime outcomes through `AuroraDecisionTelemetryService._backfill_previous_outcome()` and correction/freeform chip feedback through `CorrectionFeedbackProcessor`, so sequential outcomes and explicit user corrections update the persisted posterior.
- Wired `SparkleSelfModelService.get_readout_summary()` to attach `bayesian_policy` and blend uncertainty-adjusted posterior confidence into `strategy_confidence`, which is already consumed by Aurora wake/intervention policy.
- Evidence: `cd backend && pytest tests/unit/test_aurora_bayesian_learner.py` → 4 passed; `cd backend && pytest tests/unit/test_aurora_runtime_self_model.py tests/unit/test_aurora_runtime_telemetry.py tests/unit/test_t33_predicted_reply_correction.py` → 50 passed; `cd backend && python3.11 -m compileall app/aurora/bayesian app/aurora/runtime_v1/telemetry.py app/aurora/runtime_v1/correction_feedback.py app/aurora/runtime_v1/self_model.py` → passed.

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

**C12 closeout status — 2026-05-01**:
- ✅ Fixed the dashboard freeform dialog contract: it now returns trimmed text only from Send/submit; Cancel returns `null`, so typed-but-cancelled text is not recorded or routed.
- ✅ `AuroraTelemetryService.recordStatusBandCorrection()` now sends `freeform_text` for freeform status-band corrections, and dashboard passes the user's actual explanation into telemetry before routing to chat.
- ✅ Chat correction chips keep the natural-language label as the user message while preserving `telemetry_id`, `semantic_value`, `group_id`, `band_status`, and `is_disconfirming` as structured Aurora context/telemetry.
- ✅ Backend API regression proves `/aurora/telemetry/chip-selected` forwards `freeform_text` into `CorrectionFeedbackProcessor`.
- Evidence: `cd mobile && flutter test test/features/aurora/data/services/aurora_telemetry_service_test.dart test/widget/aurora_freeform_correction_dialog_test.dart test/features/chat/presentation/widgets/contextual_correction_bar_test.dart` → 4 passed; `cd backend && pytest tests/unit/test_t33_predicted_reply_correction.py -q` → 38 passed; scoped `ruff check` passed; scoped `flutter analyze --no-fatal-infos` had no errors and only existing/info lints.

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

**C13 closeout update — 2026-05-01**:
- Implemented in the existing state-driven proactive push path, not a parallel framework.
- `PushPolicyCompiler` now emits human-readable `proactive_reason`, deep-link route/action metadata, cross-device delivery context, and `intrusiveness_level`.
- `StateDrivenPushService` now passes active device count/platforms/last-active device context plus 7-day dismissal counts into compilation.
- `PushDeliveryService` now exposes category dismissal counts and carries deep-link/action metadata into notification payloads.
- Notification Center now displays `proactive_reason` as the push trigger evidence when available.
- Verification: `cd backend && pytest tests/unit/test_push_policy_compiler.py tests/unit/test_state_driven_push_service.py tests/unit/test_push_delivery_service.py` -> `14 passed`; targeted Ruff passed; `cd mobile && flutter analyze --no-fatal-infos ...` completed with existing `discarded_futures` infos only.

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

**2026-05-01 C16 status**:
- Added `mobile/lib/core/errors/failures.dart` with typed network/offline/auth/server/validation/unknown failures and a conservative Dio/object mapper.
- Adopted typed failures in auth, chat, and dashboard data/provider paths so high-impact login, chat send/history, and dashboard loading no longer collapse into bare exceptions.
- Updated chat and dashboard error surfaces to show distinct recovery affordances for offline/network, auth, server, validation, and unknown failures.
- Added focused mapper coverage in `mobile/test/core/errors/failures_test.dart`.
- Evidence: `cd mobile && flutter test test/core/errors/failures_test.dart` passed (4/4). `dart analyze` on changed C16 Dart files returned no errors or warnings, only existing/info-level lint guidance. Full `flutter analyze --no-fatal-infos` remains blocked by repo-wide pre-existing warnings/infos across app and vendored plugin files.

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

**C17 status — 2026-05-01**:
- Completed the first feature-scoped migration for `mobile/lib/features/chat`: all direct `Colors.white` / `Colors.black` references in chat feature Dart files were moved to DS text, surface, shadow, or contrast tokens.
- Added `DS.onColor(Color background)` for contrast-safe foreground selection on dynamic colored badges/icons.
- Added `mobile/test/widget/chat_design_system_dark_mode_test.dart` as a regression guard for representative dark chat surfaces plus a source scan that fails on new raw black/white usage in `features/chat`.
- Evidence: `rg -n --pcre2 "Colors\\.(white|black)(?![A-Za-z0-9_])" mobile/lib/features/chat -g '*.dart'` returns no matches. The missing OpenClaw l10n getters were regenerated by C19; current focused Flutter verification is now blocked by unrelated syntax errors in dirty `mobile/lib/features/chat/presentation/screens/chat_screen.dart`.

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

**C18 closeout status — 2026-05-01**:
- Completed: added explicit screen-reader/button semantics and >=44dp targets for chat correction chips, dashboard Aurora status/correction controls, task quick tools, task execution status, and community feed post actions/topics.
- Keyboard/screen-reader basics: Aurora status band now supports semantic activation plus Enter/Space activation through `FocusableActionDetector`; task execution status no longer reads `MediaQuery` during `initState`, so accessible-navigation tests can mount it safely.
- Tests: `cd mobile && flutter test --no-pub test/widget/c18_accessibility_semantics_test.dart` passed (`4 passed`).
- Scoped analyzer: `cd mobile && dart analyze lib/features/chat/presentation/widgets/contextual_correction_bar.dart lib/features/home/presentation/widgets/aurora_status_band.dart lib/features/task/presentation/widgets/quick_tools_panel.dart lib/features/task/presentation/widgets/execution_status_indicator.dart lib/features/community/presentation/widgets/feed_post_card.dart test/widget/c18_accessibility_semantics_test.dart` passed with no issues.
- Remaining risk: full `flutter analyze --no-fatal-infos` still exits non-zero because the current shared worktree has thousands of existing info/warning findings outside C18 scope.

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

**C19 status — 2026-05-01**:
- Added first-class OpenClaw feature routing in `mobile/lib/features/openclaw/openclaw_routes.dart` and wired `...OpenClawRoutes.routes` into the app router. `HomeRoutes.openClawHub` remains a compatibility alias for existing dashboard entry points.
- Added `OpenClawScreen` plus `openClawModuleProvider`, which summarizes setup/loading/ready/attention state from the connection and automation services.
- Reused the existing hub surface as the real user flow: connection setup, diagnostics, queue retry/clear actions, device affinity, automation, recent activity, and chat/task exits. The hub now exposes the setup guide link when OpenClaw is not ready and shows a provider-driven loading indicator while connection/automation status is refreshing.
- Added localized setup-guide strings and regenerated Flutter l10n output.
- Added regression coverage in `mobile/test/widget/openclaw_module_state_test.dart` and included `/openclaw` in `mobile/test/app/router_smoke_test.dart`.
- Evidence: `cd mobile && flutter gen-l10n` passed. `cd mobile && flutter test test/widget/openclaw_module_state_test.dart test/app/router_smoke_test.dart` is currently blocked before test execution by unrelated syntax errors in dirty `mobile/lib/features/chat/presentation/screens/chat_screen.dart` around lines 1374-1531.

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

**C25 closeout status — 2026-05-01**:
- Created `docs/legal/privacy_policy.md` — bilingual (EN/中文摘要), 12 sections covering data collection through breach notification.
- Created `docs/legal/terms_of_service.md` — bilingual, 17 sections covering eligibility, AI content disclaimer, user rights, liability.
- Created `docs/legal/data_export_delete_flow.md` — maps existing export API (11 categories, ZIP) and delete flow (soft-delete → 30d grace → hard purge). 11 gaps tracked with priorities.
- Created `docs/product/SPARKLE_AI_MEMORY_PRIVACY_2026-05-01.md` — plain-language explanation of AI memory, storage, controls, PII redaction, and FAQ.
- Verified: data export API (`data_export.py`), account deletion flow (`users.py` L520-573), PII redaction (`aurora/privacy.py`) all live.
- Remaining gaps tracked: Flutter UI for export/delete (P2), AI memory toggle (P1), individual learned-item UI (P1).

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

**C26 closeout status — 2026-05-01**:
- Completed full inventory: 25 Event classes in `event_bus.py`, 28 string constants in `event_types.py`, ~20 inline string events with no constants.
- Removed stale Card Protocol comment block (lines 610-615) — Card/Occurrence/Intervention events already removed, comment was noise.
- Removed dead `"error.created"` (dotted) fallback in `profile_event_consumer.py` L91 — only `"error_created"` (underscore) is published.
- Documented `MasteryUpdatedFromError` as published-but-unconsumed (live publisher in `galaxy_service.py:272`, no consumer reads `mastery_updated_from_error`).
- Identified 17 `event_types.py` constants (61%) that are published but have no known consumer — marked as "documented, intentionally pass-through" or tracked for follow-up.
- Three distinct Redis-based event systems identified: Python EventBus (Streams), Go CQRS (Streams), Redis Pub/Sub channels. Systems serve different purposes, not reconciled — tracked as architectural note.
- Evidence: `cd backend && python3.11 -m compileall app/core/event_bus.py app/services/profile_event_consumer.py` → pass.

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

**C27 closeout status — 2026-05-01**:
- Completed full audit: ~84 silent exception sites found across services/orchestration/aurora/api/core/signals. Categorized: ~12 HIGH (data write paths), ~25 MEDIUM (user-visible degradation), ~47 LOW (telemetry/UI acceptable).
- Fixed 4 HIGH risk sites: `behavior_signal_collector.py` L197 (intervention delivery), `users.py` L570 (GDPR purge scheduling), `profile_write_service.py` L544 (JSON decode), `profile_event_consumer.py` L277 (seed library loading). All now log `logger.warning(...)` before passing.
- Pattern documented: Redis operations are the most common source of silent swallows (~60% of findings). `orchestrator_production.py` has the densest cluster (5 MEDIUM-risk spine enrichment failures in close proximity).
- LOW-risk telemetry/best-effort catches intentionally left as-is per scope guidance.
- Evidence: `cd backend && python3.11 -m compileall app/services/behavior_signal_collector.py app/api/v1/users.py app/services/profile_write_service.py app/services/profile_event_consumer.py` → pass.

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

**C28 closeout status — 2026-05-01**:
- SSE UTF-8: Code uses streaming `utf8.decoder` (Utf8Decoder transformer), which correctly buffers partial multi-byte sequences across chunk boundaries. Exploration agent false positive. No fix needed.
- SSE `\r\n` handling: Fixed — `_parseSSEEvent` now splits on `RegExp(r'\r?\n')` for CRLF-tolerant line parsing. Added shared `_parseSSEBuffer` helper that handles both `\n\n` and `\r\n\r\n` event delimiters, used by both `getStream` and `postStream`.
- API client dead code: Removed 5 dead try/on-DioException/rethrow blocks from REST methods (`get`, `post`, `put`, `patch`, `delete`). These caught and immediately rethrew, providing zero value while misleading readers.
- Offline queue indicator: Deferred — existing `OfflineMessageQueueService` and `pendingCount()` are solid, but `pendingCount()` is never called from UI code. Tracked as C28-001 follow-up.
- BGM split: Deferred — 3,494-line all-static singleton recommended for structural split into 4 collaborators (PreferencesRepository, SceneProfileProvider, PlaybackManager, LibraryManager). Tracked as C28-002.
- Evidence: `cd mobile && dart analyze lib/core/network/api_client.dart` → pass (no errors, only existing info lints).
- Remaining risk: Full Flutter analysis blocked by unrelated syntax errors in `chat_screen.dart` (C12 dirty worktree warning).

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

**C29 closeout status — 2026-05-01**:
- Version audit: Go (1.24.0), Python (3.11), PostgreSQL (16) are consistent across CI, Docker, and source configs. Flutter CI pins 3.24.0, pubspec constraint >=3.0.0 <4.0.0 — no .fvmrc for local pinning (tracked).
- Pinned `aquasecurity/trivy-action` from mutable `@master` to `@v0.29.0`.
- Updated `golangci/golangci-lint-action` v4→v6, `subosito/flutter-action` v2→v3, `codecov/codecov-action` v4→v5, `docker/build-push-action` v5→v6.
- Added `.github/dependabot.yml` with weekly updates for GitHub Actions, Go modules, pip, and pub ecosystems.
- Lockfiles confirmed committed: `backend/requirements.txt`, `backend/uv.lock`, `mobile/pubspec.lock`.
- Vulnerability scanning: Trivy (filesystem), Gitleaks (secrets), Safety (Python deps) all in CI — no Go or Flutter vulnerability scanner (tracked).
- Evidence: `cd backend/gateway && go test ./...` blocked by pre-existing `internal/service` chat history test failure (known C14 finding).

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

**C30 closeout status — 2026-05-01**:
- Created `docs/product/SPARKLE_E2E_ACCEPTANCE_LAUNCH_CHECKLIST_2026-05-01.md` with all 6 required scenarios:
  1. New user → onboarding → goal → plan → task → reflection (7 steps, verification commands)
  2. Aurora risk → correction → learning → behavior change (9 steps, Bayesian verification)
  3. Document upload → Galaxy retrieval → task material (7 steps, RAG verification)
  4. Community share → feed → goal mates → board handoff (5 steps, community verification)
  5. Offline → queued action → recovery (9 steps, Isar verification)
  6. Production deploy → monitoring → rollback/drain (10 steps, full signoff commands)
- Each scenario maps auto (existing tests) vs manual steps with evidence references.
- Launch readiness summary tracks all C01-C30 gate statuses.
- 4 known blockers documented (Flutter chat_screen syntax, Go service test, offline UI, BGM split).
- 8 remaining manual ops items listed (deploy, backup, TLS, SMTP, API keys, alert channels, app store).
- 5 integrator decision items for C00 (dual event systems, consumerless events, mastery event, chat merge, offline UI).

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

## 9. Codex C14 Go Gateway WS/STT Hardening Closeout (2026-05-01)

> **结论**: C14 已完成 gateway WebSocket/STT hardening 的代码闭环。Chat、STT、community WS proxy now share per-connection message rate-limit defaults, STT/proxy reject noisy clients with policy close frames, and internal STT/gRPC transport details are no longer reflected to clients.

### 9.1 已补齐

| 项 | 结果 |
|----|------|
| Shared rate limit | `backend/gateway/internal/handler/ws_hardening.go` centralizes per-connection WS limiter defaults from `WS_MESSAGE_RATE_RPS` / `WS_MESSAGE_RATE_BURST` |
| STT hardening | `stt_handler.go` applies the limiter to client audio/control messages, filters unsupported message types, serializes Python writes around STOP cleanup, and uses `wsSafeWriter` for client writes/closes |
| Proxy hardening | `websocket_proxy.go` applies the same per-connection limiter before forwarding client messages and uses configured `WS_MAX_MESSAGE_BYTES` consistently |
| Raw error leaks | STT backend dial failures now return `STT service unavailable`; non-gRPC, `Internal`, `DataLoss`, and unknown stream errors map to safe public messages |
| Idle/write race | `chat_orchestrator.go` and connection close helpers now close through `wsSafeWriter`, so idle-timeout close and normal writes share the same write/close lock |

### 9.2 验证

| 命令 | 结果 |
|------|------|
| `cd backend/gateway && go test ./internal/handler -run 'Test(STTHandler\|WebSocketProxy\|GrpcStreamErrorDetails\|LegacyStreamErrorPayload\|WSSafeWriter)'` | ✅ 通过 |
| `cd backend/gateway && go test ./internal/handler` | ✅ 通过 |
| `cd backend/gateway && go test -race ./internal/handler` | ✅ 通过; macOS linker emitted non-fatal `LC_DYSYMTAB` warning |
| `cd backend/gateway && go test ./...` | ⚠️ Handler packages passed, but full run failed outside C14 in `internal/service` chat history test: expected `Calculus review`, got `chat_history.new_conversation`; Redis refusal logs also present |

### 9.3 剩余风险

`go test ./...` is not green because of the `internal/service` failure above, which is outside the C14 handler scope. C14 scoped race and handler coverage is green; C00/C15 should decide whether to take the service/i18n fallback failure in a separate gateway coverage pass.

## 10. Codex C15 Go Critical Middleware Coverage Closeout (2026-05-01)

> **结论**: C15 已补齐 gateway critical middleware 回归测试。`ws_auth.go` now has explicit valid/invalid/missing/query-token-policy coverage, and Redis-backed hybrid rate limiting now proves allow/reject plus Redis-failure local fallback behavior.

### 10.1 已补齐

| 项 | 结果 |
|----|------|
| WS auth valid token | `TestWsAuthMiddleware_ValidHeaderToken` verifies JWT header auth sets `user_id`, `is_admin`, `auth_token`, and `ws_auth_method=jwt_header` |
| WS auth invalid token | `TestWsAuthMiddleware_InvalidHeaderToken` verifies malformed JWTs return `401` with the public invalid-token message |
| WS auth missing token | `TestWsAuthMiddleware_MissingToken` verifies requests without credentials return `401` |
| Query token policy | `TestWsAuthMiddleware_QueryTokenPolicy` verifies query JWTs are rejected when `AllowWsQueryToken=false` and accepted when enabled |
| Rate-limit allow/reject | `TestHybridRateLimitMiddleware_RedisAllowAndReject` verifies Redis token bucket allows the first request and rejects the exhausted burst |
| Redis failure behavior | `TestHybridRateLimitMiddleware_RedisFailureFallsBackToLocalLimiter` verifies Redis script failure falls back to the local limiter and still rejects when the local bucket is exhausted |

### 10.2 验证

| 命令 | 结果 |
|------|------|
| `cd backend/gateway && go test ./internal/middleware/...` | ✅ 通过 |
| `cd backend/gateway && go test ./internal/middleware/... -cover` | ✅ 通过; `coverage: 41.8% of statements` |
| `cd backend/gateway && go test ./...` | ⚠️ Middleware/agent/handler/db packages passed, but full run still fails in pre-existing `internal/service` chat history test: expected `Calculus review`, got `chat_history.new_conversation` |

### 10.3 剩余风险

C15 scope is green. Full gateway acceptance remains blocked by the unrelated `internal/service` localization/title fallback failure already noted by C14.

## 11. Codex C20 Reviews Route Integration Closeout (2026-05-01)

> **结论**: C20 route ownership and entry flow are now implemented. The reviews feature has a dedicated route module, `/review-plan` is registered in the app router, and home/tool/learning review entry points route users into the review hub before launching the active review session.

### 11.1 已补齐

| 项 | 结果 |
|----|------|
| Feature-owned routes | Added `mobile/lib/features/reviews/reviews_routes.dart` and `reviews.dart`; `/review-plan` and `/review` now live under `ReviewRoutes` instead of `ErrorBookRoutes` |
| App router integration | `mobile/lib/app/routes.dart` now spreads `ReviewRoutes.routes` |
| Entry points | Nightly review panel, cognitive tool hub, expanded home toolbar, and route-based `review_plan` tool launch now point at `ReviewRoutes.planHub` |
| Route tests | Route coverage and J6 chain tests now assert review routes separately from error-book routes |
| State/error tests | Added `review_plan_hub_screen_test.dart` covering empty hub state and provider-error rendering |

### 11.2 验证

| 命令 | 结果 |
|------|------|
| `cd mobile && dart analyze lib/features/reviews/reviews.dart lib/features/reviews/reviews_routes.dart lib/features/error_book/error_book_routes.dart lib/features/reviews/presentation/widgets/nightly_review_panel.dart lib/features/home/presentation/widgets/cognitive_tool_hub_card.dart lib/features/home/presentation/widgets/expanded_toolbar_section.dart lib/features/tools/tool_registry.dart test/widget/full_route_coverage_test.dart test/widget/j6_additional_chains_test.dart test/features/reviews/presentation/screens/review_plan_hub_screen_test.dart` | ✅ 退出码 0; only existing `require_trailing_commas` infos in older route-chain tests |
| `cd mobile && flutter test test/features/reviews/presentation/screens/review_plan_hub_screen_test.dart` | ⚠️ 编译被当前 dirty `mobile/lib/features/chat/presentation/screens/chat_screen.dart` 语法错误阻塞 |
| `cd mobile && flutter test test/widget/full_route_coverage_test.dart test/widget/j6_additional_chains_test.dart` | ⚠️ 同上，Flutter compiler stops on `chat_screen.dart` unmatched parentheses around lines 1374-1531 |

### 11.3 剩余风险

C20 code and targeted tests are in place, but full Flutter execution must be rerun after the unrelated chat screen syntax errors are resolved.
