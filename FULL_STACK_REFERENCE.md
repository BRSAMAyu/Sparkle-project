# Sparkle Full-Stack Reference — Machine-Readable Edition
# 全链路接口规范文档 v1.0
#
# PURPOSE: Single source of truth for all AI agents modifying this codebase.
# USAGE: Read relevant sections BEFORE making any change. Cross-check interfaces here.
# AUDIENCE: AI coding agents, senior engineers
# LAST UPDATED: 2026-03-27

---

## VERIFICATION STATUS

This document was re-audited against the repository source tree and the live local stack on `2026-03-27`.

Incremental refresh on `2026-03-28`:
- This file remains a reference map, not the final acceptance checklist.
- Latest acceptance truth now also includes the incremental audit recorded in:
  - `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/本地发布前完整签收清单_2026-03-21.md`
- Commands re-run during the `2026-03-28` incremental refresh:
  - `cd backend && ./.venv/bin/pytest tests/unit/test_response_feedback_service.py tests/integration/test_websocket_full_stack.py`
  - `cd backend/gateway && go test ./internal/handler ./internal/agent ./internal/api/v1`
  - `cd backend && ./.venv/bin/pytest tests/unit/test_mirofish_phase0_acceptance.py tests/unit/test_mirofish_wiring_finish.py tests/unit/test_theater_seed_and_accuracy.py tests/unit/test_openclaw_phase0.py tests/unit/test_openclaw_phase1.py tests/unit/test_openclaw_phase2.py tests/unit/test_openclaw_phase3.py tests/unit/test_openclaw_phase4.py tests/unit/test_openclaw_gateway_ws.py tests/unit/test_openclaw_admin_api.py`
  - `cd mobile && flutter test test/widget/mirofish_wiring_finish_test.dart test/widget/insights_frontend_smoke_test.dart test/widget/learning_insights_navigation_test.dart test/widget/simulation_interaction_continue_test.dart test/widget/theater_phase2_widget_test.dart test/widget/unified_settings_bgm_test.dart test/core/services/bgm_service_test.dart`
  - `make env-check`
  - `make smoke`
  - `make local-backend-smoke`
- Additional verified conclusions from the `2026-03-28` refresh:
  - AI chat WebSocket path now passes multi-turn context and concurrent-connection acceptance in the live local stack.
  - MiroFish backend acceptance/unit coverage for Theater / Simulation / Learning Report passed (`103` tests in the targeted suite).
  - OpenClaw Phase 0~4 + Gateway WS + admin/user execution API remain green in the targeted backend suite.
  - Mobile MiroFish / Learning Insights / Theater / Unified Settings / BGM widget coverage passed (`18` targeted tests).
  - The local backend acceptance entrypoint now passes end-to-end: auth, community, worker queue, file/vector pipeline, gRPC, and WebSocket integration.
  - Gateway proxy registration now explicitly includes `/client-telemetry/*`; live local verification returned:
    - `POST /api/v1/client-telemetry/events/batch` -> `200`
    - `GET /api/v1/client-telemetry/summary?days=7` -> `200`
    - `GET /api/v1/background-tasks` -> `200`
  - `user_learning_profiles` is now a live Alembic migration (`oc003c4d5e6f7`) and exists in the local PostgreSQL schema.
  - Redis Search index `idx:knowledge` is now auto-created on startup and verified live with `FT.INFO idx:knowledge`.
- Known remaining gaps before full final acceptance:
  - Final full-system signoff still requires the broader manual simulator / real-device / E2E evidence in the checklist to be completed and archived.

This refresh is aligned with:
- `docs/contracts/openapi_snapshot.json` regenerated on `2026-03-27`
- `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/本地发布前完整签收清单_2026-03-21.md`

Acceptance and contract checks completed during this refresh:
- `make env-check`
- `make smoke`
- `backend/scripts/mirofish_bridge_benchmark.py`
- `python3 scripts/check_openapi_contract.py`
- `backend/scripts/ai_chat_multiturn_acceptance.py`
- `backend/scripts/ai_expert_acceptance.py`
- `backend/scripts/memory_acceptance.py`
- `backend/scripts/security_acceptance.py`
- `backend/scripts/auth_smoke.py`
- `backend/scripts/calendar_weather_acceptance.py`
- `backend/scripts/long_term_plan_acceptance.py`
- `backend/scripts/cognitive_capsule_acceptance.py`
- `backend/scripts/community_smoke.py`
- `backend/scripts/community_acceptance.py`
- `backend/scripts/accountability_acceptance.py`
- `backend/scripts/achievement_visual_acceptance.py`
- `backend/scripts/focus_acceptance.py`
- `backend/scripts/insights_acceptance.py`
- `backend/scripts/api_contract_acceptance.py`
- `backend/scripts/galaxy_plan_acceptance.py`
- `backend/scripts/community_share_adopt_acceptance.py`
- `backend/scripts/notes_errorbook_acceptance.py`
- `backend/scripts/document_stt_acceptance.py`
- `backend/scripts/translation_dictionary_acceptance.py`
- `backend/scripts/seed_library_acceptance.py`
- `backend/scripts/celery_acceptance.py`
- `backend/scripts/worker_smoke.py`
- `backend/scripts/verify_data_integrity.py`

Verification labels used in this document:
- `VERIFIED`: confirmed against current source files.
- `CONDITIONAL`: exists only when feature flags or optional dependencies are enabled.
- `CLIENT-ONLY`: present in Flutter constants or UI code, but not confirmed as current server truth.
- `HIGH-RISK DRIFT`: client/server or doc/code mismatch already observed in this repo.

High-risk corrections applied during this audit and refresh:
- Proto contracts are **9 files**, not 4.
- Flutter traffic is **mostly** routed through Go Gateway, but there are **direct mobile gRPC calls** to `agent_service` review endpoints.
- Go Gateway proxying is **not only explicit routes**; it also has a `NoRoute` reverse-proxy fallback.
- Python API surface is much larger than the prior summary: current `backend/app/api/v1/` contains about **525 route decorators** across many modules.
- Current truth for statistics is `/api/v1/stats/*`; older `/statistics/*` references are historical drift.
- Current truth for community encryption is:
  - `POST /api/v1/community/encryption/keys`
  - `GET /api/v1/community/encryption/keys/{user_id}`
  - `DELETE /api/v1/community/encryption/keys/{key_id}`
  - there is no separate `/user/:id` or `/revoke` runtime contract in the current Python API
- Current truth for shared resource adoption is `POST /api/v1/community/shared-resources/{id}/adopt`; older `/share/{id}/adopt` references are stale.
- Notification Center endpoints under `/api/v1/notification-center/*` are active and verified; some Flutter constants are declared across multiple lines and must not be treated as missing.
- MiroFish-era routes are live and verified in the current stack:
  - `POST /api/v1/learning-reports/generate`
  - `GET /api/v1/profile/system-updates`
  - `GET /api/v1/simulation/recommended-seeds`
  - `POST /api/v1/theater/predictions/generate`
  - `POST /api/v1/simulation/sessions/{session_id}/continue`
  - `POST /api/v1/simulation/sessions/{session_id}/continue/stream`
  - `POST /api/v1/ws/ticket`
- Learning insight/profile contracts were re-verified live on `2026-03-27` after the latest MiroFish alignment pass:
  - `GET /api/v1/profile/context` now backfills `knowledge_summary` from error-book/task/study data when `UserNodeStatus` rows are sparse, instead of returning an effectively empty context.
  - `GET /api/v1/profile/context` now emits non-empty `policy_signals` and `risk_signals` for current cognitive patterns (for example `夜间能量错配循环`, `完美主义回避循环`, `理想化排程循环`).
  - `GET /api/v1/profile/inferred-preferences` now includes user-facing `label` and `source_label`, and its `explanation` field is localized for the mobile persona UI.
  - `GET /api/v1/profile/active-policies` now includes `profile_label`, `signal_label`, and `source_pattern_label`, with localized human-readable `effect` text.
  - `GET /api/v1/dashboard/status` returns localized cognitive insight copy under `cognitive`.
- Chat bridge behavior is verified on the live WebSocket path: Theater and Simulation prompts produce preview metadata (`open_theater` / `open_simulation`) in `full_text` events.
- Chat bridge now also covers Learning Report on the live WebSocket path:
  - `open_report` + `report_preview` + `report_deep_link` are emitted in `full_text` events
  - Theater / Simulation / Report all use short-circuit bridge execution instead of full chat generation
  - Bridge deep links now preserve `source_chat_session_id` across Theater / Simulation / Report so downstream screens can return to the originating chat session.
  - The chat bubble now renders MiroFish bridge results as inline experience cards instead of plain link-only previews:
    - Theater cards show route bullets plus “继续在对话里” follow-up chips
    - Simulation cards show round preview plus one-tap “继续模拟一轮 / 让我来回答” prompts that reuse the current chat session
    - Report cards surface trigger badges, structured action buttons, and prompt chips for immediate follow-up
  - Report inline action buttons now also preserve `source_chat_session_id`, so jumping from chat into Theater / Simulation / Report subflows keeps continuity back to the same conversation.
  - Local benchmark on `2026-03-27` measured representative prompts at approximately:
    - Theater preview: `~1.8s`
    - Simulation preview: `~4.8s`
    - Learning Report preview: `~9.3s`
  - Current bridge cost tiers are intentionally asymmetric for balance:
    - Theater: `low`
    - Simulation: `low`
    - Learning Report: `low` via `instant_preview` mode in chat bridge, while API-triggered full reports remain richer/slower
- MiroFish interaction/persistence behavior was re-verified live on `2026-03-27`:
  - `POST /api/v1/simulation/run` now returns `interaction_prompt` + `suggested_replies` at session level, and each round carries `reply_to_speaker` + `turn_goal`.
  - `POST /api/v1/simulation/run/stream` can now stop in `WAITING_FOR_USER`, emit an `interaction` SSE event, and hand the current session back to the client without discarding participant memory.
  - `POST /api/v1/simulation/sessions/{session_id}/continue` and `/continue/stream` resume the same simulation session after the learner replies, preserving participant memory, prior rounds, and the moderator's dynamic round target.
  - Simulation moderator prompts were hardened on `2026-03-27`: the engine now gives the LLM explicit speaker-selection / pause / stop / scenario-adaptation criteria instead of the earlier single-line JSON instruction.
  - Simulation participant context now includes the last 5 memory items plus a cross-agent summary of other participants' most recent viewpoints, which materially improves reply targeting in `knowledge_debate`, `case_analysis`, and `error_diagnosis`.
  - Simulation round targets are now scenario-aware instead of globally capped at `6` (`knowledge_debate` / `case_analysis` can extend to `8`, `error_diagnosis` to `7`), while checkpoints persist `last_active_at` and fall back to in-process storage if Redis is temporarily unavailable.
  - The legacy single-round compatibility helpers were removed after verification; the active simulation path now uses only the moderator-driven `_generate_agent_round` + `_build_user_interaction_point` flow.
  - Celery now includes hourly stale-session cleanup for `simulation:session:*`, marking abandoned sessions as completed and clearing pending interaction state after the 6-hour TTL window.
  - Supported simulation scenarios now include `case_analysis`, `what_if_path`, `concept_map_build`, and `error_diagnosis` in addition to the earlier four templates.
  - `GET /api/v1/profile/system-updates` now includes `simulation_session_ready` entries with `session_payload`, `interaction_prompt`, `suggested_replies`, and a deep link back to `/simulation`.
  - `POST /api/v1/theater/predictions/generate` now tolerates free-text prompts such as `帮我推演特征值与特征向量`; current local graph maps that phrase to target node `线性代数` instead of returning `400`.
  - If no usable knowledge-graph node can be resolved at all, Theater now falls back to `free_mode` path generation instead of failing. In that mode the API keeps `target_name`, omits `target_node_id`, and still returns usable `paths`, `timeline`, and preview metadata.
  - `free_mode` target generation now validates `target_name`, `description`, `prerequisites`, and `milestones` after the LLM call; missing fields are backfilled from a deterministic fallback instead of leaking partial payloads into the route builder.
  - Theater free-mode step risks are no longer position-only heuristics. The backend now runs a lightweight JSON risk assessment over step titles + current mastery and uses that output to label path steps as `low` / `medium` / `high`, with a 12-hour cache keyed by the normalized backbone + mastery fingerprint.
  - Chat-bridge Theater previews now omit `target_node_id` in deep links when the result came from `free_mode`, so `/theater` can reopen safely without tripping UUID validation on the next request.
  - Theater 2.0 responses now expose a daily `timeline` per route instead of only coarse milestones. Each frame includes `day_index`, `route_id`, `projected_mastery`, `projected_completion_rate`, `active_step_node_id`, `active_step_title`, `compare_label`, and `branch_type`, so the mobile timeline player can scrub day-by-day progression.
  - `POST /api/v1/theater/predictions/{prediction_id}/what-if` now accepts both single-node `skip_node_id` and multi-node `skip_node_ids`. The response includes `original_mastery`, `original_completion_rate`, `remaining_path`, `branch_timeline`, `branch_label`, and `branch_focus_node_ids` for side-by-side branch comparison.
  - `POST /api/v1/theater/predictions/{prediction_id}/adopt` now closes the loop by creating first-week tasks and checkpoint dates in the same transaction. The response includes `created_tasks`, `checkpoint_dates`, and `review_due_on`, and the corresponding `theater_route_adopted` system update carries the same metadata.
  - `POST /api/v1/theater/predictions/{prediction_id}/actual-outcome` now updates cached `accuracy_tracking` status from `pending` to `recorded`, allowing the Theater screen to switch from the reminder card to a calibration summary after the learner backfills real outcomes.
  - Celery now runs a daily Theater prediction accuracy sweep. Cached predictions store `user_id`, and due predictions (`accuracy_tracking.due_on`) can automatically pull actual mastery/progress from Galaxy / adopted plans before calling the existing `actual-outcome` path.
  - Prediction indexing is no longer scan-only: prediction records are added to `theater:prediction:users` and per-user `theater:prediction:user:{user_id}` sets so scheduled accuracy checks can avoid a full keyspace scan in the common path.
  - `GET /api/v1/simulation/recommended-seeds` cold start now prefers `onboarding_profile` seeds derived from `user_learning_profiles` / active-plan subject hints before falling back to generic starter graph seeds.
  - `POST /api/v1/learning-reports/generate` now uses recent user chat messages as a cold-start evidence source. When mastery/timeline are empty, the API can emit `starter_focus` from `chat_inference` and synthesize an intro diagnostic instead of a blank baseline report.
  - Learning Report 2.0 payloads now include `diagnosis_cards`, `trend_overview`, `action_cards`, and `trigger_summary`, so the mobile app can render an interactive dashboard instead of relying on Markdown alone.
  - `diagnosis_cards` carry `headline`, `summary`, `evidence`, and optional `deep_link` / `cta_label`; the current app uses them to open bottom-sheet evidence cards and jump directly into Theater, Simulation, Galaxy, or Sprint history.
  - `trend_overview.history_points` provides report-native trend points, while `trend_overview.comparisons` describes deltas such as `本周 vs 上周` with `delta_mastery`, `delta_study_minutes`, and `direction`.
  - `action_cards` now provide one-click execution links for `theater`, `simulation`, `galaxy`, and `plan` follow-ups, including chat/cold-start reports.
  - `trigger_summary` distinguishes `baseline_ready`, `bottleneck`, `breakthrough`, and `manual` report origins. The API accepts `trigger_source` on `POST /api/v1/learning-reports/generate`, and the resulting `learning_report_ready` system update title/description now reflect that trigger mode.
  - Learning Report generation now caches the latest payload per user for 24 hours under `report:latest:{user_id}` using a data fingerprint of mastery/pattern/timeline/chat evidence. Repeat requests on unchanged inputs reuse the cached report instead of re-spending LLM tokens.
  - The report cache now stores a compact payload plus gzip+base64-compressed markdown instead of duplicating the full large response body verbatim in Redis.
  - When `trigger_summary.mode` is `bottleneck` or `breakthrough`, report generation now also emits a lightweight WebSocket-backed notification via the notification service, in addition to the system-update inbox item; failures are logged but do not fail report generation.
  - `GET /api/v1/profile/system-updates` now also includes `theater_prediction_ready` entries with a deep link back to `/theater`.
  - Phase 5 UX polish is now wired on the mobile side:
    - Simulation bubbles highlight the current speaker, render role-aware avatars/stance labels, and keep the latest speaker spotlight in both the participant strip and timeline feed.
    - Theater graph rendering now accepts `selectedNodeId` plus route node highlights, and the painter uses mastery-aware gradients, selected-node emphasis, and route-edge emphasis instead of a single static node style.
    - Theater now exposes a share sheet backed by the universal poster flow. If a route has already been adopted, the community-share action reuses the created `plan_id`; otherwise it falls back to sharing the target knowledge node.
    - Learning Report now exposes the same poster-based share sheet from the app bar, so the dashboard payload can be exported as a polished summary instead of raw markdown text.
    - First successful Simulation / Theater / Learning Report visits now trigger a persisted local MiroFish milestone celebration on mobile (`mirofish_first_simulation`, `mirofish_first_theater`, `mirofish_first_report`), deduped through `SharedPreferences` and recorded into the app event stream as `entity_execution` events with `entity_type=mirofish_milestone`.
  - Phase 6-10 frontend alignment is now in place on the current mobile build:
    - Report trend charts render animated multi-series curves (`掌握度` + `学习时长`) from `trend_overview.history_points`, instead of only a single static mastery line.
    - Report action deep links normalize `/theater`, `/simulation`, `/galaxy`, `/learning-report`, and `/sprint` paths, and they now preserve `source_chat_session_id` whenever continuity back to chat matters.
    - Chat bridge prompt chips are no longer fixed-only text. Theater / Simulation / Report cards now add context-aware follow-up chips based on the recent conversation (for example `考试`, `计划`, `错题`, `复盘`, `表达`).
    - Pure mode accessory previews now use a dialog + carousel/PageView flow instead of a simple bottom sheet, so multiple bridge previews can be swiped without leaving the chat bubble context.
- Focus statistics now use UTC-consistent boundaries in the backend service layer, matching how sessions are persisted.
- Decay timemachine now returns non-empty projections even for users without pre-existing `UserNodeStatus` rows, avoiding empty-state contract breaks during local acceptance.
- Vocabulary lookup/package behavior is now locally acceptance-safe:
  - if the full `data/dictionaries/oaldpe.mdx` asset is present, `/api/v1/vocabulary/lookup` uses MDX directly
  - if that file is only a Git LFS pointer in local checkout, the API falls back to a bundled Oxford starter subset instead of degrading to `llm_fallback`
  - `/api/v1/vocabulary/dictionary/packages` and `/api/v1/vocabulary/dictionary/packages/{id}/download` remain live in both cases
- Local acceptance helpers now tolerate prior auth rate-limit pressure by falling back to locally issued smoke tokens when the shared `chat_test` account is temporarily throttled. This affects validation tooling only; runtime API contracts are unchanged.

Companion pre-release acceptance checklist:
- `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/本地发布前完整签收清单_2026-03-21.md`
- `/Users/brsama/code/GitHub/Sparkle-project/docs/verification/final_release_snapshot_1.0.0.md`

Companion frontend alignment references:
- `/Users/brsama/code/GitHub/Sparkle-project/docs/engineering/前端改进对齐文档_2026-03-22.md`
- `/Users/brsama/code/GitHub/Sparkle-project/docs/engineering/technical_debt_register_2026-03-22.md`

Current feature inventory snapshot from source tree:
- Mobile feature directories currently include: `achievement`, `admin`, `auth`, `calendar`, `chat`, `cognitive`, `community`, `demo`, `document`, `error_book`, `file`, `focus`, `galaxy`, `home`, `insights`, `intent`, `knowledge`, `leaderboard`, `memory`, `notification_center`, `onboarding`, `photon`, `plan`, `reviews`, `seed_library`, `settings`, `shop`, `splash`, `task`, `tools`, `translation`, `user`, `visual_elements`, `vocabulary`
- Python API v1 modules currently include: `accountability`, `achievements`, `agent_stats`, `analytics`, `assets`, `audit`, `auth`, `background_tasks`, `calendar`, `capsules`, `chat`, `client_telemetry`, `cognitive`, `community`, `dashboard`, `decay_timemachine`, `devices`, `dlq_admin`, `error_book`, `errors`, `event_bus_health`, `events`, `experiments`, `feedback_admin`, `files`, `focus`, `galaxy`, `graph_monitor`, `graphrag_trace`, `health`, `health_production`, `ingestion`, `interventions`, `inventory`, `leaderboards`, `learning_paths`, `memory`, `memory_admin`, `memory_settings`, `monitoring`, `multi_agent`, `multi_intent`, `nightly_reviews`, `notification_center`, `notifications`, `observability`, `omnibar`, `photons`, `plans`, `prediction`, `predictive_analytics`, `preferences`, `profile_transparency`, `push_interaction`, `recommendations`, `seed_libraries`, `shop`, `signals`, `statistics`, `stt`, `subjects`, `subtasks`, `suggestions`, `tasks`, `translation`, `user_persona_batch`, `user_settings`, `users`, `visual_elements`, `vocabulary`

## TABLE OF CONTENTS

```
[1]  ARCHITECTURE OVERVIEW
[2]  SERVICES MAP (ports, containers, roles)
[3]  ENVIRONMENT VARIABLES (canonical names)
[4]  PROTO CONTRACTS (gRPC interfaces)
     [4.1] AgentService
     [4.2] GalaxyService
     [4.3] ErrorBookService
     [4.4] WebSocket Proto Messages
     [4.5] CommunityService
     [4.6] STTService
     [4.7] InferenceService
     [4.8] Evidence Messages
     [4.9] Signals Messages
[5]  GO GATEWAY — ROUTES & HANDLERS
     [5.1] WebSocket Endpoints
     [5.2] REST Endpoints (Gateway-native)
     [5.3] Proxy Routes (forwarded to Python API)
     [5.4] Internal Endpoints
     [5.5] WebSocket Message Protocol
[6]  PYTHON API — REST ROUTES (FastAPI /api/v1)
     [6.1] Auth
     [6.2] Users & Profile
     [6.3] Tasks & Subtasks
     [6.4] Plans
     [6.5] Chat
     [6.6] Galaxy / Knowledge Graph
     [6.7] Community (Friends, Groups, Messages)
     [6.8] Focus Sessions
     [6.9] Statistics
     [6.10] Error Book (错题本)
     [6.11] Memory
     [6.12] Cognitive
     [6.13] Achievements & Gamification
     [6.14] Shop, Photons, Inventory
     [6.15] Notifications
     [6.16] Files & Documents
     [6.17] Capsules, Seed Library
     [6.18] Translation, STT, Vocabulary
     [6.19] Other Endpoints
[7]  DATABASE SCHEMA
     [7.1] Extensions
     [7.2] Core Tables (users, auth, sessions)
     [7.3] Task & Plan Tables
     [7.4] Chat & AI Tables
     [7.5] Galaxy / Knowledge Tables
     [7.6] Community Tables
     [7.7] Gamification Tables
     [7.8] Memory & Cognitive Tables
     [7.9] Notification & Event Tables
     [7.10] File Storage Tables
     [7.11] Review & Feedback Tables
     [7.12] Monitoring & Audit Tables
[8]  REDIS KEY NAMESPACES
[9]  CELERY TASK QUEUES
[10] FLUTTER MOBILE — ROUTES & SCREENS
     [10.1] Navigation Tabs (main shell)
     [10.2] Auth Routes
     [10.3] Feature Routes
[11] FLUTTER — API INTEGRATION POINTS
     [11.1] Base URL Resolution
     [11.2] HTTP Endpoints (via Dio)
     [11.3] WebSocket Connections
     [11.4] gRPC Connections
[12] FLUTTER — WEBSOCKET MESSAGE PARSING
[13] AI ORCHESTRATION LAYER
     [13.1] LangGraph Standard Workflow
     [13.2] Chat Modes
     [13.3] Intent Routing
     [13.4] LLM Providers & Tiers
[14] CROSS-LAYER CONTRACT RULES
[15] CRITICAL INVARIANTS (NEVER VIOLATE)
[16] DEPENDENCY VERSIONS
```

---

## [1] ARCHITECTURE OVERVIEW

```
Flutter Mobile App (Dart/Flutter 3.x)
    |
    | HTTP REST (:8080/api/v1)   WebSocket (:8080/ws/*)
    v
Go Gateway (Gin, port 8080)              <-- container: sparkle_gateway
    |
    | gRPC (:50051)          HTTP REST proxy (:8000)
    |           \                /
    v            v              v
Python gRPC     Python FastAPI (:8000)   <-- containers: sparkle_agent + sparkle_api
Agent Engine    REST Engine
    |                |
    +----+-----------+
         |
         v
PostgreSQL (:5432)  +  pgvector  +  Apache AGE (graph)  <-- container: sparkle_db
Redis Stack (:6379)                                       <-- container: sparkle_redis
MinIO (:9000/:9001)                                       <-- container: sparkle_minio
Celery Workers (glm_batch, default, high_priority queues) <-- containers: celery_worker, celery_glm_batch_worker
Tempo/OpenTelemetry (:4317)                               <-- container: sparkle_tempo
```

**Critical rule**: Flutter REST and WebSocket traffic is routed through Go Gateway, but mobile also contains direct gRPC clients for some review flows (`review_grpc_service.dart`, `plan_review_grpc_service.dart`).
**Critical rule**: Go Gateway should not own core AI reasoning; it authenticates, translates protocols, serves file/upload endpoints, and proxies to Python.
**Critical rule**: Python gRPC server (sparkle_agent) is the main AI orchestration boundary.
**Critical rule**: Python REST server (sparkle_api) owns the majority of CRUD/data/business endpoints.

---

## [2] SERVICES MAP

| Container | Image/Build | Port (host:container) | Role |
|---|---|---|---|
| sparkle_db | pgvector-age.Dockerfile | 5432:5432 | PostgreSQL 16 + pgvector + Apache AGE |
| sparkle_redis | redis/redis-stack-server:latest | 6379:6379 | Redis Stack (search + streams) |
| sparkle_minio | minio/minio:latest | 9000:9000 (API), 9001:9001 (console) | Object storage |
| sparkle_api | backend/Dockerfile | 8000:8000 | Python FastAPI REST server |
| sparkle_agent | backend/Dockerfile | 50051:50051 | Python gRPC Agent server |
| sparkle_gateway | backend/gateway/Dockerfile | 8080:8080 | Go Gin gateway |
| celery_worker | backend/Dockerfile | — | Celery (high_priority,default,low_priority) |
| celery_glm_batch_worker | backend/Dockerfile | — | Celery (glm_batch queue) |
| sparkle_tempo | grafana/tempo:latest | 4317:4317 | OpenTelemetry trace collector |
| sparkle_age_init | backend/Dockerfile | — | One-shot: init Apache AGE extension |

**Local development (non-Docker)**:
- Go Gateway: `make gateway-dev` → localhost:8080
- Python gRPC: `make grpc-server` → localhost:50051
- Python API: `make grpc-server` also starts FastAPI on :8000 (same process, SERVICE_ROLE=api)
- Flutter: `make mobile-run`

---

## [3] ENVIRONMENT VARIABLES

All services load from repo root `.env`. Docker compose overrides host-specific names to container DNS names.

### Core Secrets (MUST be set)
```
JWT_SECRET=<shared secret — used by both Go Gateway and Python for JWT verification>
INTERNAL_API_KEY=<key for /internal/* routes on Go Gateway>
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<password>
POSTGRES_DB=sparkle
REDIS_PASSWORD=<password>
MINIO_ROOT_USER=<user>
MINIO_ROOT_PASSWORD=<password>
```

### Database
```
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>:5432/<db>   # Python async (asyncpg)
# Go uses: postgresql://<user>:<pass>@<host>:5432/<db>             # Go sync (pgx)
POSTGRES_HOST=sparkle_db          # Docker; local: 127.0.0.1
POSTGRES_PORT=5432
```

### Redis
```
REDIS_URL=redis://:<pass>@sparkle_redis:6379/0
REDIS_HOST=sparkle_redis          # Docker; local: 127.0.0.1
REDIS_PORT=6379
CELERY_BROKER_URL=redis://:<pass>@sparkle_redis:6379/1
CELERY_RESULT_BACKEND=redis://:<pass>@sparkle_redis:6379/2
```

### Service Addresses
```
AGENT_ADDRESS=sparkle_agent:50051     # Go Gateway → gRPC agent
BACKEND_URL=http://sparkle_api:8000   # Go Gateway → Python REST proxy
MINIO_ENDPOINT=minio:9000
```

### LLM Providers
```
LLM_PROVIDER=xiaomi          # Primary: xiaomi | deepseek | zhipu | qwen | openai
LLM_MODEL_NAME=qwen-plus
LLM_REASON_MODEL_NAME=deepseek-reasoner

XIAOMI_MIMO_API_KEY=<key>
XIAOMI_MIMO_BASE_URL=https://api.xiaomimimo.com/v1
XIAOMI_CHAT_MODEL=mimo-v2-flash       # Fast tier
XIAOMI_PRO_MODEL=mimo-v2-pro          # Standard/reasoning tier

DEEPSEEK_API_KEY=<key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_CHAT_MODEL=deepseek-chat
DEEPSEEK_REASON_MODEL=deepseek-reasoner

ZHIPU_API_KEY=<key>
ZHIPU_CHAT_MODEL=glm-4.7
ZHIPU_FLASH_MODEL=glm-4.7-flashx
GLM_4_7_FLASH_MODEL=glm-4.7-flash

DASHSCOPE_API_KEY=<key>              # Aliyun/Qwen
DASHSCOPE_CHAT_MODEL=qwen3.5-plus
DASHSCOPE_FAST_MODEL=qwen3.5-flash
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4
DASHSCOPE_RERANK_MODEL=qwen3-rerank

SILICONFLOW_API_KEY=<key>
SILICONFLOW_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
SILICONFLOW_RERANK_MODEL=Qwen/Qwen3-Reranker-4B
```

### Embedding & RAG
```
EMBEDDING_PROVIDER=dashscope         # dashscope | siliconflow
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIM=1024
RERANK_PROVIDER=dashscope
RERANK_MODEL=qwen3-rerank
```

### STT / OCR / Translation
```
STT_PROVIDER=zhipu
ZHIPU_ASR_MODEL=glm-asr-2512
OCR_PROVIDER=zhipu                  # zhipu | siliconflow
TRANSLATION_PRIMARY_PROVIDER=hunyuan
HUNYUAN_TRANSLATE_MODEL=tencent/Hunyuan-MT-7B
```

### JWT Config
```
JWT_ISSUER=sparkle-gateway
JWT_AUDIENCE=sparkle-app
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Feature Flags (all default values shown)
```
USE_CONTEXT_PACK=true
SEMANTIC_CACHE_ENABLED=true
RERANKER_ENABLED=true
GLM_BATCH_ENABLED=true
COMPLEXITY_ROUTING_ENABLED=true
STANDARD_CHAT_FORCE_FAST_TIER=true
ENABLE_GRAPHRAG_MONITOR_API=false     # Set true to expose /monitor/graph routes
ENABLE_SUMMARIZATION_WORKER=true
PROMPT_SNAPSHOT_ENABLED=false
```

---

## [4] PROTO CONTRACTS

**Source files**: `proto/` directory.
**Generated code**:
- Go: `backend/gateway/gen/`
- Python: `backend/app/gen/`
- Dart: `mobile/lib/gen/`
**NEVER edit generated files directly. Run `make proto-gen` after proto changes.**

**Audit correction**: current repo contains **9 proto files**:
- `proto/agent_service.proto`
- `proto/community_service.proto`
- `proto/error_book.proto`
- `proto/galaxy_service.proto`
- `proto/stt_service.proto`
- `proto/websocket.proto`
- `proto/sparkle/inference/v1/inference.proto`
- `proto/sparkle/rag/v1/evidence.proto`
- `proto/sparkle/signals/v1/signals.proto`

**Contract classification**:
- External RPC/service contracts: `agent_service`, `galaxy_service`, `error_book`, `community_service`, `stt_service`, `inference`
- Transport/envelope contracts: `websocket`
- Shared payload/message contracts: `evidence`, `signals`

### [4.1] AgentService — `proto/agent_service.proto`

**Package**: `agent.v1`
**Go package**: `github.com/sparkle/gateway/gen/agent/v1;agentv1`
**gRPC address**: `sparkle_agent:50051` (Docker) / `localhost:50051` (local)

| RPC | Request | Response | Notes |
|---|---|---|---|
| StreamChat | ChatRequest | stream ChatResponse | Server-side streaming. Primary AI chat. |
| RetrieveMemory | MemoryQuery | MemoryResult | RAG/vector search |
| GetUserProfile | ProfileRequest | UserProfile | |
| GetWeeklyReport | WeeklyReportRequest | WeeklyReport | |
| SubmitResponseFeedback | ResponseFeedbackRequest | ResponseFeedbackResponse | |
| SubmitPlanReview | PlanReviewRequest | PlanReviewResponse | |
| SubmitContentReviewFeedback | ContentReviewFeedbackRequest | ContentReviewFeedbackResponse | |
| SubmitReviewOverride | ReviewOverrideRequest | ReviewOverrideResponse | Phase 2e |
| SubmitReviewAppeal | ReviewAppealRequest | ReviewAppealResponse | Phase 2e |
| GetAppealStatus | AppealStatusRequest | AppealStatusResponse | Phase 2e |
| SubmitReviewFeedback | ReviewFeedbackRequest | ReviewFeedbackResponse | Phase 2f |
| RequestRegeneration | RegenerationRequest | RegenerationResponse | Phase 2f |
| GetFeedbackStatistics | FeedbackStatisticsRequest | FeedbackStatisticsResponse | Phase 2f |
| GetArbitrationQueue | GetArbitrationQueueRequest | GetArbitrationQueueResponse | Phase 2g |
| AssignArbitrationCase | AssignArbitrationCaseRequest | AssignArbitrationCaseResponse | Phase 2g |
| SubmitArbitrationDecision | SubmitArbitrationDecisionRequest | SubmitArbitrationDecisionResponse | Phase 2g |
| GetArbitrationQueueStats | GetArbitrationQueueStatsRequest | GetArbitrationQueueStatsResponse | Phase 2g |

#### ChatRequest Fields
```
user_id         string           # Required
session_id      string           # Empty = new session
message         string           # oneof input: text message
tool_result     ToolResult       # oneof input: tool execution result
user_profile    UserProfile      # Populated by Go Gateway from DB
extra_context   google.Struct    # Dynamic key/value context
history         []ChatMessage    # Recent history (optional)
config          ChatConfig       # model, temperature, max_tokens, tools_enabled
request_id      string           # Trace ID
file_ids        []string         # Scope RAG to files
include_references bool
active_tools    []string
chat_mode       string           # "standard"|"deep_analysis"|"study_plan"|
                                 # "error_diagnosis"|"expert_auto"|"expert::<id>"
```

#### ChatResponse (streaming) Content Types (oneof)
```
delta           string           # Incremental text chunk
tool_call       ToolCall         # {id, name, arguments}
status_update   AgentStatus      # {state: THINKING|SEARCHING|EXECUTING_TOOL|GENERATING|IDLE, details, active_agent}
full_text       string           # Final complete text
error           Error            # {message, retryable, details, error_code}
usage           Usage            # {prompt_tokens, completion_tokens, total_tokens, cost_micro_usd}
citations       CitationBlock    # [{id, title, content, source_type, url, score, file_id, ...}]
tool_result     ToolResultPayload # {tool_name, success, data, widget_type, widget_data, ...}
intervention    InterventionPayload # Adaptive intervention request
```

#### ChatResponse Metadata Keys (map<string,string> — JSON-decoded by Go Gateway)
```
collaboration_timeline   # JSON object
review_data              # JSON object — plan review data
state_change_event       # JSON object
visualization            # JSON object
selected_experts         # JSON object
answer_experts           # JSON object
routing_strategy         # JSON object
fallback_reason          # JSON object
route_confidence         # JSON object
expert_entry_source      # JSON object
ux_turn                  # JSON object — UX envelope: turn-level
ux_progress              # JSON object — UX envelope: progress update
ux_result                # JSON object — UX envelope: final result
ux_followthrough         # JSON object — UX envelope: follow-through
ux_sources               # JSON object — UX envelope: sources
ux_evolution             # JSON object — UX evolution info
continuity_banner        # JSON object
mode_explanation         # JSON object
collaboration_summary    # JSON object
```

#### FinishReason Enum
```
NULL=0, STOP=1, LENGTH=2, TOOL_CALLS=3, CONTENT_FILTER=4, ERROR=5
```

#### InterventionLevel Enum
```
SILENT_MARKER=0, TOAST=1, CARD=2, FULL_SCREEN_MODAL=3
```

#### AgentType Enum
```
AGENT_UNKNOWN=0, ORCHESTRATOR=1, KNOWLEDGE=2, MATH=3, CODE=4,
DATA_ANALYSIS=5, TRANSLATION=6, IMAGE=7, AUDIO=8, WRITING=9, REASONING=10
```

### [4.2] GalaxyService — `proto/galaxy_service.proto`

**Package**: `galaxy.v1`

| RPC | Request | Response |
|---|---|---|
| UpdateNodeMastery | UpdateNodeMasteryRequest | UpdateNodeMasteryResponse |
| SyncCollaborativeGalaxy | SyncCollaborativeGalaxyRequest | SyncCollaborativeGalaxyResponse |

#### UpdateNodeMasteryRequest
```
user_id    string
node_id    string
mastery    int32    # 0-100 mastery level
reason     string
request_id string
revision   int64    # Logical clock for conflict resolution
```

### [4.3] ErrorBookService — `proto/error_book.proto`

**Package**: `error_book`

| RPC | Notes |
|---|---|
| CreateError | Create error record |
| ListErrors | With filtering |
| GetError | Single detail |
| GetErrorSemanticSummary | AI summary |
| UpdateError | Patch fields |
| DeleteError | Soft delete |
| AnalyzeError | Trigger AI re-analysis |
| SubmitReview | Record SRS review performance |
| GetReviewStats | Aggregate stats |
| GetTodayReviews | SRS due list |

### [4.4] WebSocket Proto Messages — `proto/websocket.proto`

**Package**: `sparkle.ws`

| Message | Purpose |
|---|---|
| WebSocketMessage | Outer envelope: {version, type, payload(bytes), trace_id, request_id, event_time} |
| ChatMessage | User chat payload: {session_id, user_id, message, tool_calls} |
| UpdateNodeMasteryRequest | Galaxy mastery update via WebSocket |
| InterventionPushMessage | Server push: {intervention_id, level, content, actions, expires_at} |
| MessageAck | Server ack: {message_id, status, timestamp, error_code} |
| MessageNack | Server reject: {message_id, error_code, error_message, retry_after_ms, permanent} |
| HeartbeatPing | Client ping: {timestamp, client_id} |
| HeartbeatPong | Server pong: {client_timestamp, server_timestamp} |

### [4.5] CommunityService — `proto/community_service.proto`

**Package**: `sparkle.community`
**Role**: community domain contract definitions for friendship, groups, group/private messaging, check-in, moderation, and privacy.

Key enum families:
- `FriendshipStatus`
- `GroupType`
- `GroupRole`
- `MessageType`
- `SearchVisibility`

Key message families:
- User summaries: `UUID`, `UserBrief`
- Friend system: `FriendRequest`, `FriendResponse`, `FriendshipInfo`, `BlockUserRequest`, `BlockUserInfo`
- Group system: `GroupCreate`, `GroupInfo`, `GroupMemberInfo`
- Messaging: `MessageSend`, `MessageInfo`, `PrivateMessageSend`, `PrivateMessageInfo`
- Check-in: `CheckinRequest`, `CheckinResponse`

Important note:
- `proto/community_service.proto` does define a full `CommunityService` RPC surface.
- However, the currently audited application paths that are most obviously user-facing are still REST endpoints under `/api/v1/community/*` plus proxied community WebSocket routes.

### [4.6] STTService — `proto/stt_service.proto`

**Package**: `stt.v1`

| RPC | Request | Response | Notes |
|---|---|---|---|
| StreamSpeechToText | stream `AudioChunk` | stream `TranscriptionResult` | real-time streaming STT |
| TranscribeAudio | `TranscribeRequest` | `TranscribeResponse` | batch/file transcription |
| EnhanceTranscript | `EnhanceRequest` | `EnhanceResponse` | transcript post-processing |

Important message groups:
- streaming: `AudioChunk`, `TranscriptionResult`, `TranscriptionError`
- batch: `TranscribeRequest`, `TranscribeResponse`, `WordTimestamp`, `TranscriptionMetadata`
- enhancement: `EnhanceRequest`, `EnhancementOptions`, `EnhanceResponse`

### [4.7] InferenceService — `proto/sparkle/inference/v1/inference.proto`

**Package**: `sparkle.inference.v1`
**Transport note**: contains `google.api.http` mapping:
- `POST /v1/inference:run`

| RPC | Request | Response |
|---|---|---|
| RunInference | `InferenceRequest` | `InferenceResponse` |

Core enums:
- `TaskType`
- `Priority`
- `ResponseFormat`
- `ErrorReason`
- `ArtifactScope`

Important note:
- This is a formal service contract in the repo, but it is not currently documented as a mainstream mobile entry path in the audited Flutter code.

### [4.8] Evidence Messages — `proto/sparkle/rag/v1/evidence.proto`

**Package**: `sparkle.rag.v1`
**Purpose**: shared RAG evidence payloads, not a standalone service definition.

Messages:
- `EvidenceNode`
- `EvidencePack`

### [4.9] Signals Messages — `proto/sparkle/signals/v1/signals.proto`

**Package**: `sparkle.signals.v1`
**Purpose**: legacy candidate-action payloads plus v2 signals/context plane messages.

Legacy messages:
- `CandidateAction`
- `NextActionsCandidateSet`

Signals plane v2 messages:
- `ContextEnvelope`
- `FocusMetrics`
- `ComprehensionMetrics`
- `TimeContext`
- `ContentContext`
- `FeatureExtractResult`
- `Signals`
- `Signal`
- `CandidateActionV2`

---

## [5] GO GATEWAY — ROUTES & HANDLERS

**Source**: `backend/gateway/`
**Entry**: `backend/gateway/cmd/server/main.go`
**Router setup**: `backend/gateway/cmd/server/setup.go`
**Framework**: Gin v1.9.1
**Base port**: 8080

### [5.1] WebSocket Endpoints

| Path | Handler | Auth | Notes |
|---|---|---|---|
| `GET /ws/chat` | ChatOrchestrator.HandleWebSocket | WsAuthMiddleware | Primary AI chat stream |
| `GET /ws/files` | FileEventHandler.HandleWebSocket | WsAuthMiddleware | File processing events |
| `GET /ws/stt` | STTHandler.HandleWebSocket | WsAuthMiddleware | Speech-to-text stream, proxied to Python |
| `GET /api/v1/community/groups/:group_id/ws` | WebSocketProxy.HandleCommunityWS | WsAuthMiddleware | Group chat WebSocket |
| `GET /api/v1/community/ws/connect` | WebSocketProxy.HandlePersonalWS | WsAuthMiddleware | Personal chat WebSocket |

**WsAuthMiddleware**: Validates JWT from query param `token` or `Authorization` header.

#### /ws/chat Message Flow
```
Client → Go Gateway WebSocket:
  {"message": "...", "session_id": "...", "request_id": "...", "chat_mode": "standard"}

Envelope (v2 protocol):
  {"message_id": "...", "request_id": "...", "payload": {"message": "...", "session_id": "..."}}

Go Gateway → Python gRPC StreamChat → streams ChatResponse frames → JSON to client:
  {"type": "delta",  "delta": "...", "metadata": {...}, "session_id": "..."}
  {"type": "status_update", "state": "THINKING", "details": "..."}
  {"type": "tool_call", "id": "...", "name": "...", "arguments": "..."}
  {"type": "usage", "prompt_tokens": N, "completion_tokens": N}
  {"type": "done", "finish_reason": "STOP"}
  {"type": "error", "message": "...", "retryable": true}
```

### [5.2] REST Endpoints (Gateway-native, NOT proxied)

| Method | Path | Handler | Auth | Notes |
|---|---|---|---|---|
| GET | `/healthz` | HealthHandler | None | Liveness |
| GET | `/readyz` | HealthHandler | None | Readiness |
| GET | `/live` | HealthHandler | None | Liveness alias |
| GET | `/ready` | HealthHandler | None | Readiness alias |
| GET | `/health` | HealthHandler | None | Detailed component health |
| GET | `/health/live` | HealthHandler | None | Liveness alias |
| GET | `/health/ready` | HealthHandler | None | Readiness alias |
| GET | `/metrics` | Prometheus handler | None | Prometheus metrics |
| GET | `/api/v1/health` | inline | None | {"status":"ok"} |
| GET | `/api/v1/health/cqrs` | inline | None | CQRS outbox pending count |
| POST | `/api/v1/auth/apple` | AuthHandler.AppleLogin | RateLimit | Apple Sign-In |
| POST | `/api/v1/ws/ticket` | WSTicketHandler.Issue | JWT | Issue WS auth ticket |
| GET | `/api/v1/chat/sessions` | ChatHistoryHandler.GetRecentSessions | JWT | Recent chat sessions |
| GET | `/api/v1/chat/history/:conversation_id` | ChatHistoryHandler.GetConversationHistory | JWT | |
| GET | `/api/v1/groups/:group_id/messages` | GroupChatHandler.GetMessages | JWT | Group message history |
| POST | `/internal/interventions/push` | InterventionPushHandler.HandlePush | InternalAPIKey | Push intervention to user WS |
| POST | `/internal/signals/push` | SignalPushHandler.HandlePush | InternalAPIKey | Push signal to user WS |

**Error Book routes** (registered via `handlers.errorBookHandler.RegisterRoutes`):
- CRUD routes under `/api/v1/errors` — proxied via gRPC to Python ErrorBookService

### [5.3] Proxy Routes (forwarded to Python API at BACKEND_URL)

Audit correction:
- Go Gateway has both **explicit proxy route registration** and a **`NoRoute` reverse-proxy fallback**.
- `NoRoute` forwards unresolved paths to Python, applying auth middleware for non-public paths.
- Public paths explicitly allowed through fallback include:
  - `/api/v1/auth*`
  - `/api/v1/health`
  - `/docs*`
  - `/redoc*`
  - `/openapi.json`

Implemented in: `backend/gateway/internal/handler/proxy_routes.go` and `backend/gateway/internal/handler/websocket_proxy.go`

Major explicit proxy groups registered in `proxy_routes.go`:
- `/api/v1/accountability`
- `/api/v1/tasks`
- `/api/v1/plans`
- `/api/v1/learning-paths`
- `/api/v1/achievements`
- `/api/v1/calendar`
- `/api/v1/recommendations`
- `/api/v1/capsules`
- `/api/v1/seed-libraries`
- `/api/v1/community`
- `/api/v1/interventions/*`
- `/api/v1/dashboard/*`
- `/api/v1/predictive/*`
- `/api/v1/stt/transcribe`

### [5.4] Internal Endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/internal/interventions/push` | INTERNAL_API_KEY header | Push adaptive intervention |
| POST | `/internal/signals/push` | INTERNAL_API_KEY header | Push signal update |

**Internal auth**: Header `X-Internal-API-Key: <INTERNAL_API_KEY>`

### [5.5] WebSocket Protocol Detail

**Auth**:
- `Authorization: Bearer <jwt>` header
- `?token=<jwt>` query param when `AllowWsQueryToken=true`
- recommended short-lived WS ticket flow using `ticket`
- ticket can also be passed via `Sec-WebSocket-Protocol` entries like `ticket=<...>` / `ws-ticket=<...>`

**WS Ticket flow** (recommended):
1. Client calls `POST /api/v1/ws/ticket` with JWT → gets short-lived ticket token
2. Client connects `GET /ws/chat?ticket=<ticket>` or equivalent subprotocol ticket
3. Gateway validates ticket against Redis (TTL = `WS_TICKET_TTL_SECONDS`, default 60s)

**Rate limits** (from config):
```
WSTicketRateRPS=5
WSTicketRateBurst=10
WSMaxMessageBytes=65536    # 64KB
WSMessageRateRPS=2.0
WSMessageRateBurst=5
WSMaxConnections=3         # per user
```

**Message modes**:
- `wsModeLegacy`: Plain JSON `{"message":"...","session_id":"..."}`
- `wsModeEnvelope`: Envelope JSON with `message_id`, `traceparent`, `payload`

---

## [6] PYTHON API — REST ROUTES (FastAPI /api/v1)

**Base**: `http://sparkle_api:8000/api/v1`
**Source**: `backend/app/api/v1/router.py`
**Auth**: Bearer JWT (same JWT_SECRET as Go Gateway)
**Framework**: FastAPI + SQLAlchemy async

**Audit correction**:
- The current Python v1 surface is much larger than the previous summary: about **525 route decorators** across `backend/app/api/v1/`.
- The authoritative source of truth is the router inclusion map in `backend/app/api/v1/router.py`, not mobile endpoint constants and not older prose summaries.
- This section now prioritizes:
  1. router ownership and prefix truth
  2. high-value/high-risk endpoints
  3. known client/server drift

### Verified Router Inclusion Map

| Prefix / Mount | Module |
|---|---|
| `/auth` | `auth.py` |
| `/users` | `users.py` |
| `/suggestions` | `suggestions.py` |
| `/documents` | `ingestion.py` |
| `/files*` | `files.py` |
| `/interventions` | `interventions.py` |
| `/events` | `events.py` |
| `/reviews/nightly` | `nightly_reviews.py` |
| `/admin/*` | `feedback_admin.py`, `dlq_admin.py`, `event_bus_health.py` |
| `/audit` | `audit.py` |
| `/galaxy` | `galaxy.py` |
| `/errors` | `error_book.py` |
| `/learning-paths` | `learning_paths.py` |
| `/chat` | `chat.py` |
| `/tasks` | `tasks.py` |
| `/tasks/{task_id}/subtasks`, `/subtasks/{id}` | `subtasks.py` |
| `/plans` | `plans.py` |
| `/subjects` | `subjects.py` |
| `/stats` | `statistics.py` |
| `/notifications` | `notifications.py` |
| `/notification-center` | `notification_center.py` |
| `/capsules` | `capsules.py` |
| `/community` | `community.py` |
| `/cognitive` | `cognitive.py` |
| `/omnibar` | `omnibar.py` |
| `/dashboard` | `dashboard.py` |
| `/analytics` | `analytics.py` |
| `/stt` | `stt.py` |
| `/focus` | `focus.py` |
| `/vocabulary` | `vocabulary.py` |
| `/translation` | `translation.py` |
| `/health` | `health_production.py` |
| `/memory/*` | `memory.py`, `memory_settings.py`, `memory_admin.py` |
| `/preferences` | `preferences.py` |
| `/push/interaction` | `push_interaction.py` |
| `/seed-libraries` | `seed_libraries.py` |
| `/experiments` | `experiments.py` |
| `/achievements` | `achievements.py` |
| `/multi-intent` | `multi_intent.py` |
| `/prediction` | `prediction.py` |
| `/predictive` | `predictive_analytics.py` |
| `/recommendations` | `recommendations.py` |
| `/leaderboards` | `leaderboards.py` |
| `/profile/*` | `profile_transparency.py` |
| `/user/settings` | `user_settings.py` |
| `/user/persona/*` | `user_persona_batch.py` |
| `/shop` | `shop.py` |
| `/photons` | `photons.py` |
| `/inventory` | `inventory.py` |
| `/visual-elements` | `visual_elements.py` |
| `/devices` | `devices.py` |
| `/ws/*` | `monitoring.py` |
| `/decay/*` | `decay_timemachine.py` |
| `/multi-agent/*` | `multi_agent.py` |
| `/calendar` | `calendar.py` |
| `/accountability` | `accountability.py` |

**Conditional mounts**:
- `/monitor/graph/*` and `/graphrag/*` only when `ENABLE_GRAPHRAG_MONITOR_API=true`

**Separate v2 surface**:
- `/api/v2/agent/chat` from `backend/app/api/v2/agent_graph.py`

### High-Risk Endpoint Shape Corrections

These are the interface mismatches most likely to break AI-generated changes:

| Area | Correct shape | Prior/common mistaken shape |
|---|---|---|
| Statistics | `/api/v1/stats/{overview,weekly,flame,daily}` | `/api/v1/statistics/*` |
| User settings | `/api/v1/user/settings` | `/api/v1/user-settings` |
| User persona batch | `/api/v1/user/persona/{batch-update,export,import,batch-edit-suggestions}` | flattened `/user-persona-batch` |
| Delete account | `POST /api/v1/users/me/delete-account` | `DELETE /api/v1/users/me/delete-account` |
| Unlink social | `POST /api/v1/users/me/unlink-social` | `DELETE /api/v1/users/me/unlink-social` |
| Task suggestions | `POST /api/v1/tasks/suggestions` | `GET /api/v1/tasks/suggestions` |
| Subtasks list/create | `/api/v1/tasks/{task_id}/subtasks` | root `/api/v1/subtasks` collection |
| Chat stream | `POST /api/v1/chat/chat/stream` | `GET /api/v1/chat/stream` |
| Galaxy viewport/positions | `POST /api/v1/galaxy/nodes/viewport`, `POST /api/v1/galaxy/nodes/positions` | `GET` variants |
| Predict-next | `POST /api/v1/galaxy/predict-next` | `GET /api/v1/galaxy/predict-next` |
| ErrorBook review list | `GET /api/v1/errors/today-review` | `GET /api/v1/errors/today` |
| Notification center | `/api/v1/notification-center/*` | `/api/v1/notification-center` unread-count style assumptions |
| Device registration | `/api/v1/devices/{register,unregister,list}` | `/api/v1/devices` CRUD guesses |
| Community key lookup | `GET /api/v1/community/encryption/keys/{user_id}` | `/community/encryption/keys/user/{user_id}` |
| Community key revoke | `DELETE /api/v1/community/encryption/keys/{key_id}` | `POST /community/encryption/keys/{key_id}/revoke` |
| Shared resource adopt | `POST /api/v1/community/shared-resources/{shared_resource_id}/adopt` | `/community/share/{id}/adopt` |
| File uploads | `prepare/complete` are Gateway-native under `/api/v1/files/upload/*` | assuming Python `files.py` owns them |

The thematic subsections below are retained for fast navigation, but when a subsection conflicts with:
1. the router inclusion map above,
2. the high-risk correction table above, or
3. the source module itself,

the source module wins.

### [6.1] Auth — `/api/v1/auth`

| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/auth/register` | None | Email+password or guest registration |
| POST | `/auth/login` | None | Returns {access_token, refresh_token} |
| POST | `/auth/social-login` | None | Social auth login |
| POST | `/auth/refresh` | None | Refresh token rotation |
| POST | `/auth/logout` | JWT | Invalidate refresh token |
| POST | `/auth/forgot-password` | None | |
| POST | `/auth/reset-password` | None | |
| POST | `/auth/send-verification` | JWT | Send email verification |
| POST | `/auth/verify-email` | None | |
| POST | `/auth/guest` | None | Guest account creation |
| POST | `/auth/upgrade-guest` | JWT | Upgrade guest account to full |
| POST | `/auth/upgrade-guest/social` | JWT | |
| POST | `/auth/apple` | Gateway-native | Apple OAuth handled on Go Gateway |

**JWT format**:
```json
{
  "sub": "<user_id>",
  "iss": "sparkle-gateway",
  "aud": "sparkle-app",
  "exp": <unix_ts>,
  "iat": <unix_ts>
}
```

### [6.2] Users & Profile — `/api/v1/users`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/users/me` | JWT | Current user profile |
| PUT | `/users/me` | JWT | Update profile |
| POST | `/users/me/delete-account` | JWT | |
| GET | `/users/me/sessions` | JWT | Active sessions list |
| GET | `/users/me/security-log` | JWT | |
| POST | `/users/me/set-password` | JWT | |
| GET | `/users/me/social-accounts` | JWT | |
| POST | `/users/me/link-social` | JWT | |
| POST | `/users/me/unlink-social` | JWT | |
| GET | `/users/:id` | JWT | Public profile |
| GET | `/user/settings` | JWT | User settings |
| POST | `/user/settings` | JWT | Update user settings |
| POST | `/user/persona/batch-update` | JWT | Batch update persona keys |
| POST | `/user/persona/export` | JWT | Export persona |
| POST | `/user/persona/import` | JWT | Import persona |
| POST | `/preferences/preview` | JWT | Preference preview |
| GET | `/preferences/effectiveness` | JWT | Preference effectiveness |
| GET | `/profile/transparent` | JWT | Transparency summary |
| GET | `/profile/context` | JWT | Context explanation; current live payload includes `knowledge_summary` and `cognitive_summary` with fallback-derived mastery/timeline/policy signals when direct node-status data is sparse |
| GET | `/profile/inferred-preferences` | JWT | Inferred preference list; live payload includes `label`, `source_label`, localized `explanation` |
| GET | `/profile/active-policies` | JWT | Applied personalization policies; live payload includes `profile_label`, `signal_label`, localized `effect`, `source_pattern_label` |
| GET | `/profile/system-updates` | JWT | Insight/report/theater update inbox used by MiroFish surfaces |

### [6.3] Tasks & Subtasks — `/api/v1/tasks`, `/api/v1/subtasks`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/tasks` | JWT | List user tasks |
| POST | `/tasks` | JWT | Create task |
| GET | `/tasks/today` | JWT | Today's tasks |
| GET | `/tasks/recommended` | JWT | AI-recommended tasks |
| POST | `/tasks/suggestions` | JWT | Task suggestions |
| GET | `/tasks/:id` | JWT | |
| PUT | `/tasks/:id` | JWT | |
| DELETE | `/tasks/:id` | JWT | |
| POST | `/tasks/:id/start` | JWT | Start task (creates focus session) |
| POST | `/tasks/:id/complete` | JWT | Complete task |
| POST | `/tasks/:id/abandon` | JWT | |
| POST | `/tasks/:id/feedback` | JWT | Task feedback |
| GET | `/tasks/feedback/:feedbackId/reflection` | JWT | AI reflection |
| POST | `/tasks/:id/next-action-selection` | JWT | |
| GET | `/tasks/:taskId/subtasks` | JWT | List subtasks for task |
| POST | `/tasks/:taskId/subtasks` | JWT | Create subtask under task |
| PUT | `/subtasks/:id` | JWT | |
| DELETE | `/subtasks/:id` | JWT | |
| POST | `/subtasks/reorder` | JWT | Reorder subtasks |

**Task status values**: `pending`, `in_progress`, `completed`, `abandoned`

### [6.4] Plans — `/api/v1/plans`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/plans` | JWT | List plans |
| POST | `/plans` | JWT | Create plan |
| GET | `/plans/:id` | JWT | |
| PUT | `/plans/:id` | JWT | |
| DELETE | `/plans/:id` | JWT | |
| POST | `/plans/:planId/generate-tasks` | JWT | AI-generate tasks for plan |
| POST | `/plans/:id/archive` | JWT | |
| POST | `/plans/:id/restore` | JWT | |
| GET | `/plans/:id/progress` | JWT | |
| GET | `/plans/stats/summary` | JWT | |
| GET | `/plans/quota/status` | JWT | |
| GET/POST | `/plans/primary` | JWT | Primary plan selector |
| GET | `/plans/archived` | JWT | |
| PATCH | `/plans/:id/priority` | JWT | |
| GET | `/plans/:planId/learning-path-progress` | JWT | |

### [6.5] Chat — `/api/v1/chat`

Note: Real-time AI chat uses WebSocket at `/ws/chat` (Go Gateway). Python also exposes legacy HTTP chat endpoints.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/chat/sessions` | JWT | Via Go Gateway (native handler) |
| GET | `/chat/history/:sessionId` | JWT | Via Go Gateway (native handler) |
| POST | `/chat/task/:task_id` | JWT | Task-scoped HTTP chat |
| POST | `/chat/chat` | JWT | Legacy HTTP chat (non-streaming) |
| POST | `/chat/chat/stream` | JWT | Streaming chat endpoint |
| POST | `/chat/confirm` | JWT | Confirm chat result |

### [6.6] Galaxy / Knowledge Graph — `/api/v1/galaxy`

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/galaxy/graph` | JWT | Full knowledge graph |
| POST | `/galaxy/nodes/viewport` | JWT | Viewport-clipped nodes |
| POST | `/galaxy/nodes/positions` | JWT | Persist node positions |
| POST | `/galaxy/predict-next` | JWT | Predict next node to study |
| POST | `/galaxy/search` | JWT | Semantic search |
| POST | `/galaxy/node/:id/spark` | JWT | Mark node as sparked |
| GET | `/galaxy/events` | JWT | Recent galaxy events |
| GET | `/galaxy/node/:id` | JWT | Node detail |
| POST | `/galaxy/node/:id/favorite` | JWT | |
| POST | `/galaxy/node/:id/decay/pause` | JWT | Pause decay |
| GET | `/learning-paths/:targetNodeId` | JWT | |
| POST | `/learning-paths/:targetNodeId/plan` | JWT | |
| POST | `/learning-paths/:targetNodeId/full-plan` | JWT | |

**gRPC UpdateNodeMastery** is also available via WebSocket message type `"update_mastery"`.

### [6.7] Community — `/api/v1/community`

#### Friends
| Method | Path | Notes |
|---|---|---|
| GET | `/community/feed` | Social feed |
| POST | `/community/posts` | Create post |
| POST | `/community/posts/:id/like` | |
| GET | `/community/friends` | Friend list |
| POST | `/community/friends/request` | Send request |
| POST | `/community/friends/respond` | Accept/reject |
| GET | `/community/friends/pending` | Pending requests |
| GET | `/community/friends/recommendations` | AI recommendations |
| GET | `/community/friends/:friendId/messages` | DMs |
| POST | `/community/messages` | Send DM |
| POST | `/community/messages/:id/revoke` | Revoke |
| PATCH | `/community/messages/:id` | Edit |
| POST | `/community/messages/:id/reactions` | |
| GET | `/community/friends/:friendId/messages/search` | |
| GET | `/community/users/search` | |
| GET/PUT | `/community/users/privacy` | Privacy settings |
| GET | `/community/users/blocked` | |
| POST | `/community/users/block` | |
| DELETE | `/community/users/block/:userId` | |
| DELETE | `/community/friends/:friendshipId` | Remove friend |
| PUT | `/community/status` | Online status |
| POST | `/community/share` | Share resource |
| POST | `/community/shared-resources/:id/adopt` | Adopt shared resource |

#### Groups
| Method | Path | Notes |
|---|---|---|
| GET/POST | `/community/groups` | List/create groups |
| GET | `/community/groups/recommendations` | AI group recs |
| GET | `/community/groups/search` | |
| GET/DELETE | `/community/groups/:id` | |
| POST | `/community/groups/:id/join` | |
| POST | `/community/groups/:id/leave` | |
| GET | `/community/groups/:id/members` | |
| POST | `/community/groups/:groupId/members/:userId/kick` | |
| POST | `/community/groups/:groupId/members/:userId/promote` | |
| POST | `/community/groups/:groupId/members/:userId/demote` | |
| POST | `/community/groups/:groupId/members/:userId/transfer-ownership` | |
| GET/POST | `/community/groups/:id/messages` | |
| PATCH | `/community/groups/:groupId/messages/:messageId` | |
| POST | `/community/groups/:groupId/messages/:messageId/revoke` | |
| POST | `/community/groups/:groupId/messages/:messageId/reactions` | |
| POST | `/community/groups/:groupId/messages/read` | Mark read |
| GET | `/community/groups/:groupId/messages/search` | |
| POST | `/community/groups/:groupId/messages/search/advanced` | Advanced search |
| GET | `/community/groups/:groupId/threads/:threadRootId` | Thread |
| GET/POST | `/community/groups/:id/tasks` | Group tasks |
| POST | `/community/tasks/:id/claim` | Claim group task |
| POST | `/community/checkin` | Daily check-in |
| GET | `/community/groups/:id/flame` | Group streak/flame |
| GET | `/community/groups/:groupId/files` | Group file sharing |
| POST | `/community/groups/:groupId/files/:fileId/share` | Share file |
| PUT | `/community/groups/:groupId/files/:fileId/permissions` | File permissions |
| GET | `/community/groups/:groupId/files/categories` | File category stats |

#### Encryption (E2E)
| Method | Path |
|---|---|
| POST | `/community/encryption/keys` |
| GET | `/community/encryption/keys/:userId` |
| DELETE | `/community/encryption/keys/:keyId` |

#### WebSocket (community chat)
```
GET /api/v1/community/groups/:group_id/ws    # Group chat WS (via Go Gateway proxy)
GET /api/v1/community/ws/connect             # Personal chat WS (via Go Gateway proxy)
```

### [6.8] Focus Sessions — `/api/v1/focus`

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/focus/sessions` | List/start focus sessions |
| GET | `/focus/stats` | Focus statistics |
| POST | `/focus/llm/guide` | AI focus guide |
| POST | `/focus/llm/breakdown` | AI task breakdown |

**FocusSession model**: `{id, user_id, task_id, started_at, ended_at, duration_minutes, quality_rating, interruptions}`

### [6.9] Statistics — `/api/v1/stats`

| Method | Path | Notes |
|---|---|---|
| GET | `/stats/daily` | User daily stats |
| GET | `/stats/overview` | User stats overview |
| GET | `/stats/weekly` | Weekly summary |
| GET | `/stats/flame` | Streak/flame stats |

**HIGH-RISK DRIFT**: current mobile constants still reference `/statistics/*`; server router is `/stats/*`.

### [6.10] Error Book — `/api/v1/errors`

REST routes registered via `ErrorBookHandler.RegisterRoutes`. Internally calls Python gRPC `ErrorBookService`.

| Method | Path | Notes |
|---|---|---|
| POST | `/errors` | Create error record |
| GET | `/errors` | List errors |
| GET | `/errors/:id` | Detail |
| PATCH | `/errors/:id` | Update |
| DELETE | `/errors/:id` | Delete |
| POST | `/errors/:id/analyze` | Re-analyze |
| POST | `/errors/:id/review` | Submit SRS review |
| GET | `/errors/today-review` | Today's SRS list |
| GET | `/errors/stats` | Review statistics |
| GET | `/errors/:id/semantic` | Semantic summary |

### [6.11] Memory — `/api/v1/memory`, `/api/v1/memory-settings`, `/api/v1/memory-admin`

| Method | Path | Notes |
|---|---|---|
| GET | `/memory/preferences` | Memory-derived preferences |
| GET | `/memory/preferences/{pref_key}/history` | Preference history |
| GET | `/memory/goals` | Memory goals |
| GET | `/memory/episodic` | Episodic items |
| POST | `/memory/retract` | Retract memory |
| POST | `/memory/export` | Export memories |
| POST | `/memory/correction` | Correct memory |
| GET | `/memory/settings` | Memory governance settings |
| PUT | `/memory/settings` | Update |
| GET | `/memory-admin/*` | Admin: memory health, rollout, eval, policies |

### [6.12] Cognitive — `/api/v1/cognitive`

| Method | Path | Notes |
|---|---|---|
| GET | `/cognitive/fragments` | Cognitive fragments |
| GET | `/cognitive/patterns` | Pattern analysis |

### [6.13] Achievements & Gamification — `/api/v1/achievements`, `/api/v1/leaderboards`

| Method | Path | Notes |
|---|---|---|
| GET | `/achievements` | User achievements |
| GET | `/achievements/stats` | |
| GET | `/achievements/map` | Achievement map |
| GET | `/achievements/streak` | Streak info |
| GET | `/achievements/streak/history` | |
| GET | `/achievements/:id` | Detail |
| POST | `/achievements/:id/share` | Share achievement |
| POST | `/achievements/:id/pin` | Pin |
| GET | `/leaderboards` | Leaderboard |
| GET | `/leaderboards/:type` | |

### [6.14] Shop, Photons, Inventory — `/api/v1/shop`, `/api/v1/photons`, `/api/v1/inventory`

| Method | Path | Notes |
|---|---|---|
| GET | `/shop/items` | Shop catalog |
| GET | `/shop/items/:itemId` | Item detail |
| POST | `/shop/purchase` | Purchase item (costs Photons) |
| GET | `/photons/balance` | User Photon balance |
| GET | `/photons/transactions` | Transaction history |
| GET | `/photons/transactions/summary` | Transaction summary |
| POST | `/photons/transfer` | Transfer photons |
| POST | `/photons/adjust` | Admin adjustment |
| GET | `/inventory` | User inventory |
| POST | `/inventory/equip` | Equip item |
| GET | `/inventory/owned` | Owned item ids |
| POST | `/inventory/consumables/use` | Use consumable |

**Photon**: In-app currency. Earned via tasks/achievements, spent in shop.

### [6.15] Notifications — `/api/v1/notifications`, `/api/v1/notification-center`

| Method | Path | Notes |
|---|---|---|
| GET | `/notifications` | List notifications |
| POST | `/notifications` | Create notification |
| PUT | `/notifications/:id/read` | Mark read |
| GET | `/notification-center/notifications` | Notification center list |
| PUT | `/notification-center/notifications/{id}/read` | Mark read |
| PUT | `/notification-center/notifications/mark-all-read` | |
| DELETE | `/notification-center/notifications/{id}` | |
| DELETE | `/notification-center/notifications/clear-read` | |
| GET | `/notification-center/history` | |
| GET | `/notification-center/analytics` | |
| GET/PUT | `/notification-center/preferences` | |
| POST | `/devices/register` | Register device token |
| DELETE | `/devices/unregister` | Unregister device |
| GET | `/devices/list` | Registered devices |
| POST | `/push/interaction` | Record push interaction |

**Push providers**: JPush (`jpush_flutter`), Firebase FCM (`firebase_messaging`)

### [6.16] Files & Documents — `/api/v1/files`, `/api/v1/documents`

| Method | Path | Notes |
|---|---|---|
| POST | `/files/upload/prepare` | Gateway-native: presign MinIO upload URL |
| POST | `/files/upload/complete` | Gateway-native: confirm upload |
| GET | `/files/:id` | File metadata |
| GET | `/files/:id/download` | Presigned download |
| GET | `/files/:id/thumbnail` | |
| DELETE | `/files/:id` | |
| GET | `/me/files` | User's files |
| GET | `/me/files/search` | |
| POST | `/documents/clean` | Python: async upload/clean document |
| GET | `/documents/clean/{task_id}` | Python: cleaning task status |
| POST | `/files/process` | Python internal file processing trigger |
| GET | `/files/{file_id}/status` | Python internal processing status |

**File processing pipeline**: Upload to MinIO → OCR (Zhipu/SiliconFlow) → Chunking → Embedding (DashScope/SiliconFlow) → pgvector

### [6.17] Capsules, Seed Library — `/api/v1/capsules`, `/api/v1/seed-libraries`

| Method | Path | Notes |
|---|---|---|
| GET/POST | `/capsules` | Curiosity capsules list/create |
| GET | `/capsules/:id` | |
| POST | `/capsules/:id/favorite` | |
| POST | `/capsules/:id/share` | |
| POST | `/capsules/:id/feedback` | |
| GET | `/seed-libraries` | Seed library list |
| GET | `/seed-libraries/:id` | |
| POST | `/user/seed-libraries/:id/subscribe` | |

### [6.18] Translation, STT, Vocabulary — `/api/v1/translation`, `/api/v1/stt`, `/api/v1/vocabulary`

| Method | Path | Notes |
|---|---|---|
| POST | `/translation/translate` | Translate text (Hunyuan MT) |
| GET | `/translation/languages` | Supported languages |
| POST | `/stt` | Sync STT |
| `WS` | `/ws/stt` (Go Gateway) | Streaming STT (proxied to Python) |
| GET | `/vocabulary/lookup` | Dictionary lookup |
| GET/POST | `/vocabulary/wordbook` | Word book CRUD |
| GET | `/vocabulary/dictionary/packages` | Dictionary packages |
| GET | `/vocabulary/dictionary/packages/:id/download` | |

### [6.19] Other Endpoints

| Prefix | Notes |
|---|---|
| `/api/v1/subjects` | Subject management |
| `/api/v1/calendar` | Calendar events |
| `/api/v1/accountability` | Accountability partnerships |
| `/api/v1/interventions` | Adaptive intervention system |
| `/api/v1/prediction/intent/predict` | Intent prediction |
| `/api/v1/prediction/intent/types` | |
| `/api/v1/recommendations` | AI recommendations |
| `/api/v1/suggestions` | Suggestions (Vision item 3) |
| `/api/v1/omnibar/dispatch` | OmniBar command dispatch |
| `/api/v1/dashboard/status` | Dashboard data; live `cognitive` block is localized and aligned with current MiroFish insight cards |
| `/api/v1/analytics` | Analytics |
| `/api/v1/visual-elements` | Visual element system |
| `/api/v1/reviews/nightly/latest` | Nightly review |
| `/api/v1/reviews/nightly/:id/feedback` | |
| `/api/v1/experiments` | A/B experiments |
| `/api/v1/multi-intent` | Multi-intent processing |
| `/api/v1/multi-agent` | Multi-agent dispatch |
| `/api/v1/health/production` | Production health |
| `/api/v1/admin/*` | Event bus health, DLQ admin |
| `/api/v1/audit` | Audit log |
| `/api/v1/signals` | Behavior signals |

---

## [7] DATABASE SCHEMA

**Engine**: PostgreSQL 16 + pgvector + Apache AGE
**ORM (Python)**: SQLAlchemy async + Alembic migrations
**ORM (Go)**: sqlc-generated from `backend/gateway/internal/db/queries/query.sql`
**Schema source of truth**: `backend/gateway/internal/db/schema.sql` (Go) + Alembic migrations (Python)

### [7.1] Extensions
```sql
CREATE EXTENSION pgcrypto;   -- Cryptographic functions
CREATE EXTENSION vector;      -- pgvector (1024-dim embeddings)
-- Apache AGE extension for graph queries (installed via pgvector-age.Dockerfile)
```

### [7.2] Core Tables

**users**
```
id              UUID PRIMARY KEY DEFAULT gen_random_uuid()
email           TEXT UNIQUE NOT NULL
username        TEXT UNIQUE
nickname        TEXT
password_hash   TEXT
avatar_url      TEXT
level           INT DEFAULT 1
is_pro          BOOLEAN DEFAULT false
is_guest        BOOLEAN DEFAULT false
timezone        TEXT DEFAULT 'Asia/Shanghai'
language        TEXT DEFAULT 'zh-CN'
photon_balance  INT DEFAULT 0         -- In-app currency
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
last_active_at  TIMESTAMPTZ
```

**user_sessions** (auth sessions)
```
id              UUID PRIMARY KEY
user_id         UUID REFERENCES users(id)
refresh_token   TEXT UNIQUE
device_id       TEXT
ip_address      TEXT
user_agent      TEXT
expires_at      TIMESTAMPTZ
created_at      TIMESTAMPTZ
```

**auth_audit_log**
```
id, user_id, action, ip_address, user_agent, created_at
```

### [7.3] Task & Plan Tables

**tasks**
```
id              UUID PRIMARY KEY
user_id         UUID REFERENCES users(id)
plan_id         UUID REFERENCES plans(id) NULL
subject_id      UUID REFERENCES subjects(id) NULL
title           TEXT NOT NULL
description     TEXT
status          TEXT -- pending|in_progress|completed|abandoned
priority        INT DEFAULT 0
due_date        TIMESTAMPTZ
estimated_minutes INT
actual_minutes  INT
tags            TEXT[]
metadata        JSONB
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
completed_at    TIMESTAMPTZ
```

**subtasks**
```
id, task_id, title, status, order_index, created_at, updated_at
```

**plans**
```
id              UUID PRIMARY KEY
user_id         UUID REFERENCES users(id)
title           TEXT
description     TEXT
subject_id      UUID NULL
status          TEXT -- active|completed|archived
goal            TEXT
target_date     TIMESTAMPTZ
metadata        JSONB
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
```

**plan_states** — FSM state for AI plan execution
```
id, plan_id, state, context JSONB, version INT, created_at, updated_at
```

**plan_execution_records**
```
id, plan_id, user_id, action, result JSONB, created_at
```

**subjects**
```
id, user_id, name, code, color, icon, parent_id, created_at
```

**task_feedbacks**
```
id, task_id, user_id, rating, comment, emotional_state, energy_level, created_at
```

### [7.4] Chat & AI Tables

**chat_sessions**
```
id              UUID PRIMARY KEY
user_id         UUID REFERENCES users(id)
title           TEXT
mode            TEXT DEFAULT 'standard'
created_at      TIMESTAMPTZ
updated_at      TIMESTAMPTZ
last_message_at TIMESTAMPTZ
```

**chat_messages**
```
id              UUID PRIMARY KEY
session_id      UUID REFERENCES chat_sessions(id)
user_id         UUID REFERENCES users(id)
role            TEXT -- user|assistant|system|tool
content         TEXT
metadata        JSONB
tokens_used     INT
model           TEXT
created_at      TIMESTAMPTZ
```

**response_feedback**
```
id, user_id, response_id, trace_id, feedback_type, reasons TEXT[], free_text,
workflow_id, prompt_version, meta JSONB, created_at
```

**review_history** — content review records
```
id, user_id, response_id, review_score FLOAT, decision TEXT,
issues JSONB, created_at
```

**review_feedback**
```
id, review_id, user_id, rating INT, was_helpful BOOL, was_accurate BOOL,
specificity_level TEXT, comments TEXT, created_at
```

**review_overrides**
```
id, review_id, user_id, original_decision TEXT, new_decision TEXT,
reason TEXT, created_at
```

**appeals** — review appeals
```
id, review_id, user_id, status TEXT, appeal_reason TEXT,
secondary_decision TEXT, secondary_score FLOAT, resolved_at TIMESTAMPTZ
```

**arbitration_cases**, **arbitration_decisions** — Phase 2g arbitration tables

**token_usage**
```
id, user_id, session_id, model, prompt_tokens, completion_tokens,
total_tokens, cost_micro_usd, created_at
```

**idempotency_keys**
```
key TEXT PRIMARY KEY, status TEXT, response_body TEXT, created_at, expires_at
```

### [7.5] Galaxy / Knowledge Tables

**user_node_status**
```
id, user_id, node_id UUID, mastery INT (0-100), is_active BOOL,
revision INT, last_studied_at TIMESTAMPTZ, created_at, updated_at
```

**knowledge_nodes** (via Apache AGE graph or PostgreSQL table)
```
id UUID, title, content, subject_id, embedding vector(1024),
type TEXT, metadata JSONB, created_at
```

**node_relations**
```
id, from_node_id, to_node_id, relation_type TEXT, weight FLOAT
```

**semantic_links**
```
id, source_id, target_id, similarity FLOAT, relation_type TEXT
```

**document_chunks**
```
id, document_id, content TEXT, embedding vector(1024),
chunk_index INT, page_number INT, metadata JSONB
```

**strategy_nodes** — Learning strategy nodes

**node_expansion_queue** — Async node expansion jobs

**collaborative_galaxies** — Collaborative CRDT-synced galaxies

### [7.6] Community Tables

**friendships**
```
id, user_id, friend_id, status TEXT -- pending|accepted|blocked, created_at
```

**groups**
```
id UUID, name, description, owner_id, member_count,
is_public BOOL, settings JSONB, created_at
```

**group_members**
```
id, group_id, user_id, role TEXT -- owner|admin|member, joined_at
```

**group_messages**
```
id UUID, group_id, user_id, content TEXT, message_type TEXT,
reply_to_id UUID NULL, is_revoked BOOL, created_at, edited_at
```

**private_messages**
```
id, sender_id, receiver_id, content TEXT, is_revoked BOOL,
created_at, read_at
```

**posts**
```
id, user_id, content TEXT, media_urls TEXT[], visibility TEXT,
like_count INT, created_at
```

**user_blocks** — Blocked users
**message_reports** — Reported messages
**message_favorites** — Favorited messages
**group_files**, **group_task_claims**, **group_tasks**
**offline_message_queue** — Messages queued for offline users

### [7.7] Gamification Tables

**achievements** — Achievement definitions
```
id, name, description, type achievementtype, rarity achievementrarity,
icon_url, photon_reward INT, conditions JSONB
```

**user_achievements** — User unlocked achievements
```
id, user_id, achievement_id, unlocked_at, is_pinned BOOL
```

**spark_contracts** — Accountability contracts
```
id, user_id, partner_id, goal TEXT, status contractstatus,
started_at, ends_at, created_at
```

**user_streak_stats**
```
id, user_id, current_streak INT, max_streak INT,
last_active_date DATE, updated_at
```

**user_streak_days** — Individual streak day records

**shop_items**
```
id UUID, name TEXT, description TEXT, type TEXT, rarity TEXT,
photon_price INT, metadata JSONB, is_active BOOL
```

**shop_purchases**
```
id, user_id, item_id, photon_spent INT, purchased_at
```

**photon_transaction_history**
```
id, user_id, amount INT, balance_after INT, reason TEXT, created_at
```

**user_consumables** — Item inventory
**user_titles** — User earned titles
**user_visual_configs** — Visual customization
**galaxy_skins**, **user_galaxy_skins**

### [7.8] Memory & Cognitive Tables

**episodic_memories**
```
id UUID, user_id, content TEXT, embedding vector(1024),
source TEXT, importance FLOAT, is_retracted BOOL,
created_at, expires_at
```

**cognitive_fragments**
```
id UUID, user_id, content TEXT, type TEXT,
embedding vector(1024), tags TEXT[], created_at
```

**persona_snapshots** — User persona snapshots over time

**behavior_patterns** — Detected behavior patterns

**passive_signals** — Passive tracking signals

**user_irt_ability** — IRT (Item Response Theory) ability estimates

**irt_item_parameters** — IRT item parameters

**context_budget_profiles** — Context window budget profiles

**scaffolding_states** — Learning scaffolding states (shallow/medium/deep)

### [7.9] Notification & Event Tables

**notifications**
```
id UUID, user_id, type TEXT, title TEXT, body TEXT,
data JSONB, is_read BOOL, created_at
```

**notification_preferences**
```
id, user_id, channel TEXT, type TEXT, enabled BOOL
```

**push_histories** — Push notification delivery records

**push_preferences** — Push notification preferences

**user_devices** — Registered devices for push
```
id, user_id, device_token TEXT UNIQUE, platform TEXT -- ios|android,
push_provider TEXT -- fcm|jpush, is_active BOOL
```

**event_store** — Event sourcing store
**event_outbox** — Transactional outbox for reliable event delivery
**event_sequence_counters** — Sequence counters per aggregate

**intervention_requests** — Adaptive intervention records
**intervention_audit_logs** — Intervention audit trail
**intervention_templates** — Template definitions

**tracking_events** — User behavior tracking

### [7.10] File Storage Tables

**stored_files**
```
id UUID, user_id, filename TEXT, content_type TEXT,
size_bytes BIGINT, minio_key TEXT, bucket TEXT,
is_processed BOOL, thumbnail_key TEXT, created_at
```

**curiosity_capsules**
```
id UUID, user_id, title TEXT, content TEXT, source_url TEXT,
capsule_type TEXT, embedding vector(1024), created_at
```

**seed_items**, **seed_libraries** — Seed library system

**dictionary_entries** — MDX dictionary entries

**word_books** — User vocabulary lists

### [7.11] Review & Feedback Tables

Already covered: `response_feedback`, `review_history`, `review_feedback`, `review_overrides`, `appeals`, `arbitration_cases`, `arbitration_decisions`

**task_resource_links** — Task↔resource relationships
**task_knowledge_links** — Task↔knowledge node links
**expansion_feedback** — Knowledge expansion feedback

### [7.12] Monitoring & Audit Tables

**ab_experiments**, **ab_experiment_variants**, **ab_experiment_assignments**, **ab_experiment_metrics**

**security_audit_logs** — Security-sensitive action log

**compliance_check_logs** — Compliance audit

**data_access_logs** — GDPR data access log

**system_config_change_logs**

**smoke_document_vectors** — Smoke test vectors

**user_encryption_keys** — E2E encryption public keys

**crypto_shredding_certificates** — Crypto shredding for GDPR

**alembic_version** — Alembic migration state

---

## [8] REDIS KEY NAMESPACES

**DB allocation**:
```
DB 0: Application (sessions, cache, pub/sub, rate limiting)
DB 1: Celery broker
DB 2: Celery result backend
```

**Key patterns (DB 0)**:
```
session:<session_id>              # Chat session state (Go Gateway)
user:<user_id>:context            # User context cache
user:<user_id>:preferences        # User preferences cache
rate_limit:<user_id>:<action>     # Rate limiting counters
ws_ticket:<ticket_id>             # WS auth tickets (TTL: WS_TICKET_TTL_SECONDS)
semantic_cache:<hash>             # Semantic response cache
dedup:<message_hash>              # Message deduplication
chat_history:<session_id>         # Recent chat history
intervention:<user_id>:budget     # Intervention daily budget
intervention:<user_id>:cooldown   # Intervention cooldown
```

**Pub/Sub channels**:
```
galaxy:events:<user_id>           # Galaxy streaming events
signal:push:<user_id>             # Signal push channel
intervention:push:<user_id>       # Intervention push channel
```

---

## [9] CELERY TASK QUEUES

**Broker**: Redis DB 1 (`CELERY_BROKER_URL`)
**Result Backend**: Redis DB 2 (`CELERY_RESULT_BACKEND`)
**App**: `app.core.celery_app`

| Queue | Priority | Worker | Use Cases |
|---|---|---|---|
| `high_priority` | High | celery_worker | Urgent AI tasks, user-facing responses |
| `default` | Medium | celery_worker | General background tasks |
| `low_priority` | Low | celery_worker | Analytics, cleanup, reporting |
| `glm_batch` | Batch | celery_glm_batch_worker | GLM-4.7-Flash batch API calls, capsule generation, cognitive analysis |

**GLM Batch config**:
```
concurrency: 1-6 (adaptive, peak 2, offpeak 3)
peak hours: 14:00-18:00
spillover: enabled when backlog > 2x capacity
```

**Key scheduled tasks** (`app/celery_schedule.py`):
- Decay processing (behavior decay)
- Memory governance (retraction, consolidation)
- Evidence health check
- Nightly review generation
- Notification delivery

---

## [10] FLUTTER MOBILE — ROUTES & SCREENS

**Framework**: Flutter 3.x + go_router 13.x + Riverpod 2.x
**Entry**: `mobile/lib/main.dart`
**Router**: `mobile/lib/app/routes.dart` (`routerProvider`)
**Audit note**: current mobile code contains about **97 `GoRoute(...)` definitions** across feature modules.

### [10.1] Navigation Tabs (Main Shell — StatefulShellRoute)

| Index | Path | Screen | Notes |
|---|---|---|---|
| 0 | `/home` | DashboardScreen | Main dashboard |
| 1 | `/galaxy` | GalaxyScreen | Knowledge galaxy |
| 2 | `/chat` | ChatScreen | AI chat (query params: `prompt`, `chat_mode`) |
| 3 | `/community` | CommunityMainScreen | Social |
| 4 | `/profile` | ProfileScreen | User profile |

### [10.2] Auth Routes

| Path | Screen |
|---|---|
| `/` | SplashScreen |
| `/login` | LoginScreen |
| `/register` | RegisterScreen |
| `/forgot-password` | ForgotPasswordScreen |
| `/reset-password` | ResetPasswordScreen |
| `/legal/terms` | TermsScreen |
| `/legal/privacy` | PrivacyScreen |
| `/user/persona-onboarding` | PersonaOnboardingScreen |

**Auth guard logic**:
- Not authenticated → `/login`
- Authenticated + onboarding incomplete → `/user/persona-onboarding`
- Authenticated + accessing auth pages → `/home`

### [10.3] Feature Routes (outside main shell)

| Feature | Routes |
|---|---|
| Tasks | TaskRoutes (task detail, create, edit) |
| Plans | PlanRoutes (plan detail, create, edit) |
| Insights | InsightsRoutes |
| Focus | FocusRoutes (focus timer, sessions) |
| Galaxy | GalaxyRoutes (node detail, expanded) |
| Chat | ChatRoutes (history, session) |
| Community | CommunityRoutes (group chat, friend chat, profile) |
| Cognitive | CognitiveRoutes |
| Memory | MemoryRoutes |
| Error Book | ErrorBookRoutes |
| Achievements | AchievementRoutes |
| Shop | ShopRoutes |
| Photon | PhotonRoutes |
| Seed Library | SeedLibraryRoutes |
| Visual Elements | VisualElementsRoutes |
| Settings | UserRoutes (settings, persona) |
| Notification Center | NotificationCenterRoutes |
| Calendar | CalendarRoutes |
| Translation | TranslationRoutes |
| Tools | ToolsRoutes |

---

## [11] FLUTTER — API INTEGRATION POINTS

### [11.1] Base URL Resolution

```dart
// HTTP base (points to Go Gateway :8080)
ApiConstants.baseUrl  →  default: http://localhost:8080
                          Android emulator: http://10.0.2.2:8080
                          Override: --dart-define=API_BASE_URL=<url>

// API path prefix
ApiConstants.apiBasePath = '/api/v1'

// Full base for all REST calls
ApiEndpoints.baseUrl = '${ApiConstants.baseUrl}${ApiConstants.apiBasePath}'
// e.g., http://localhost:8080/api/v1

// WebSocket base
ApiConstants.wsBaseUrl  →  default: ws://localhost:8080
                            Android emulator: ws://10.0.2.2:8080
                            Override: --dart-define=WS_BASE_URL=<url>

// gRPC (direct to Python, port 50051) — used for direct proto calls
ApiConstants.grpcHost  →  host extracted from baseUrl
ApiConstants.grpcPort = 50051
```

**Build-time overrides** (`--dart-define`):
```
API_BASE_URL=<http url>
WS_BASE_URL=<ws url>
ANDROID_EMULATOR_URL=<url>
ANDROID_DEVICE_URL=<url>
IOS_SIMULATOR_URL=<url>
IOS_DEVICE_URL=<url>
ANDROID_USE_EMULATOR=true|false
API_CERT_SHA256=<sha256>    # For certificate pinning
```

### [11.2] HTTP Endpoints (via Dio)

HTTP client: `mobile/lib/core/network/api_client.dart` (Dio + interceptors)
Interceptors: auth token injection, idempotency, response parsing

Timeouts: connect=30s, receive=30s, send=30s

All endpoint paths defined in: `mobile/lib/core/network/api_endpoints.dart`

**Authentication header**: `Authorization: Bearer <access_token>`

**Token refresh**: Automatic via `session_refresh_service.dart` — intercepts 401 and refreshes.

### [11.3] WebSocket Connections

| Connection | URL | Service | Notes |
|---|---|---|---|
| Chat | `${wsBaseUrl}/ws/chat?token=<jwt>` | WebSocketChatServiceV2 | Main AI chat |
| Files | `${wsBaseUrl}/ws/files?token=<jwt>` | (file events) | File processing updates |
| STT | `${wsBaseUrl}/ws/stt?token=<jwt>` | STT WS service | Streaming speech-to-text |
| Group Chat | `${baseUrl}/api/v1/community/groups/:id/ws?token=<jwt>` | Community WS | |
| Personal Chat | `${baseUrl}/api/v1/community/ws/connect?token=<jwt>` | Community WS | |

**Auth token**: Passed as query parameter `token=<jwt>` or as HTTP header during WS upgrade.

**Reconnect policy** (`WebSocketService`):
- Max attempts: 10
- Base delay: 1000ms
- Exponential backoff

### [11.4] gRPC Connections

Direct gRPC used for:
- review flows via `mobile/lib/features/chat/data/services/review_grpc_service.dart`
- plan review flows via `mobile/lib/features/chat/data/services/plan_review_grpc_service.dart`

Audit correction:
- The mobile app ships generated gRPC stubs for multiple services, but the audited direct connection usage is concentrated in `agent_service` review-related services.
- This means invariant statements like "Flutter NEVER calls Python directly" are too strong for the current repository state.

```dart
// Connection
host: ApiConstants.grpcHost
port: ApiConstants.grpcPort  // 50051
```

---

## [12] FLUTTER — WEBSOCKET MESSAGE PARSING

**Source**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart`

### Incoming Message Types (from Go Gateway)

All messages are JSON with a `type` field:

```json
{"type": "delta",        "delta": "text chunk", "metadata": {...}, "session_id": "..."}
{"type": "status_update","state": "THINKING",   "details": "..."}
{"type": "tool_call",    "id": "...", "name": "...", "arguments": "..."}
{"type": "tool_result",  "tool_name": "...", "success": true, "data": {...}, "widget_type": "..."}
{"type": "citations",    "citations": [...]}
{"type": "usage",        "prompt_tokens": N, "completion_tokens": N, "total_tokens": N}
{"type": "done",         "finish_reason": "STOP"}
{"type": "error",        "message": "...", "retryable": true}
{"type": "intervention", "request": {...}}
```

### ChatStreamEvent Types (Dart)

| Event | Trigger condition |
|---|---|
| `TextEvent(text, metadata)` | `type == "delta"` with no special metadata |
| `PlanReviewWidgetEvent(reviewData)` | `delta` + metadata `requires_review == true` |
| `ToolCallEvent(id, name, arguments)` | `type == "tool_call"` |
| `ToolResultEvent(...)` | `type == "tool_result"` |
| `CitationEvent(citations)` | `type == "citations"` |
| `StatusUpdateEvent(state, details)` | `type == "status_update"` |
| `UsageEvent(promptTokens, completionTokens)` | `type == "usage"` |
| `DoneEvent(finishReason)` | `type == "done"` |
| `ErrorEvent(code, message, retryable)` | `type == "error"` |
| `InterventionEvent(request)` | `type == "intervention"` |
| `DagExecutionEvent(...)` | metadata contains `dag_execution_event` |

### Special Metadata Keys (parsed as JSON objects)

The following `metadata` keys, when present in a `delta` message, are decoded from JSON string to Map:
```
collaboration_timeline, review_data, state_change_event, visualization,
selected_experts, answer_experts, routing_strategy, fallback_reason,
route_confidence, expert_entry_source, ux_turn, ux_progress, ux_result,
ux_followthrough, ux_sources, ux_evolution, continuity_banner,
mode_explanation, collaboration_summary
```

---

## [13] AI ORCHESTRATION LAYER

### [13.1] LangGraph Standard Workflow

**Source**: `backend/app/agents/standard_workflow.py`
**Orchestrator**: `backend/app/orchestration/orchestrator.py`

The orchestrator uses a LangGraph `StateGraph` (statechart engine) with these key nodes:

```
ENTRY
  → context_builder       # Assembles user context, history, RAG results
  → routing_engine        # UnifiedIntentRouter: classifies intent
  → validation_gate       # Validates request, checks quota
  ↓
  [branch by intent]
  → standard_chat_node    # Standard conversational response
  → planning_node         # Goal/plan generation (calls sufficiency checker)
  → execution_node        # Tool execution loop
  → deep_analysis_node    # Deep analysis workflow
  → collaboration_node    # Multi-agent collaboration
  ↓
  → review_node           # Content review (plan review service)
  → response_builder      # Assembles final response + UX envelope
  → persistence_layer     # Save to DB, update metrics
  → DONE
```

**Checkpointing**: Redis-backed via `RedisCheckpointer`
**Context window**: Managed by `ContextPruner` + `FocusedContextAssembler`

### [13.2] Chat Modes

| mode value | Behavior |
|---|---|
| `standard` | Default conversational mode |
| `deep_analysis` | Extended reasoning, multiple passes |
| `study_plan` | Plan generation focused |
| `error_diagnosis` | Error book analysis mode |
| `expert_auto` | Auto-select specialist agent |
| `expert::<expert_id>` | Lock to specific expert agent |
| `team::<spec>` | Multi-agent team collaboration |

### [13.3] Intent Routing

**Router**: `backend/app/core/unified_intent_router.py`

```
UnifiedIntentType values:
  TASK_MANAGEMENT      # Create/modify tasks
  PLAN_CREATION        # Create study plan
  KNOWLEDGE_QUERY      # Knowledge retrieval / Q&A
  PROGRESS_REFLECTION  # Review progress
  EMOTIONAL_SUPPORT    # Emotional/motivational
  CLARIFICATION        # Clarify ambiguous intent
  TOOL_USE             # Direct tool invocation
  STANDARD_CHAT        # General conversation
```

**Routing decision factors**: chat_mode, user message text, user_profile, session history, active tools

### [13.4] LLM Providers & Tiers

**Tier routing** (configured via env vars `LLM_TIER_*`):

| Tier | Env Var | Default model | Use case |
|---|---|---|---|
| `FAST` | `LLM_TIER_FAST` | `mimo-v2-flash` | Fast responses, simple chat |
| `FREE_FAST` | `LLM_TIER_FREE_FAST` | `glm-4.7-flashx` | Free tier fast |
| `STANDARD` | `LLM_TIER_STANDARD` | `mimo-v2-pro` / `glm-4.7` | Standard quality |
| `REASONING` | `LLM_TIER_REASONING` | `deepseek-reasoner` | Complex reasoning |
| `FREE_REASONING` | `LLM_TIER_FREE_REASONING` | `glm-4.7-flash` (thinking) | Free tier reasoning |
| `GLM_BATCH` | `LLM_TIER_GLM_BATCH` | `glm-4.7-flash` | Batch background tasks |
| `SPECIALIST` | `LLM_TIER_SPECIALIST` | — | Expert agents |

**Key rule**: `STANDARD_CHAT_FORCE_FAST_TIER=true` → first response in standard chat uses FAST tier.

---

## [14] CROSS-LAYER CONTRACT RULES

These rules prevent interface mismatch bugs. AI agents MUST check these before modifying cross-layer code.

### R1: JSON WebSocket Envelope
Go Gateway sends JSON to Flutter. The `convertResponseToJSON` function in `chat_orchestrator_protocol.go:52` converts protobuf → JSON. Keys listed in `jsonMetadataKeys` are JSON-decoded from string.
- **DO NOT** add new structured metadata keys in Python without also adding them to `jsonMetadataKeys` in Go.

### R2: JWT Token Compatibility
Python and Go use the SAME `JWT_SECRET`. Python signs with `app/config/settings.py:SECRET_KEY` (alias of `JWT_SECRET`). Go verifies with `config.JWTSecret`.
- **DO NOT** use different secret keys for Python-issued tokens vs Go verification.

### R3: Proto Field Numbers are IMMUTABLE
Once deployed, proto field numbers must never change. Add new fields with new numbers. Use `reserved` for removed fields.
- Before adding fields: check if number is already `reserved`.

### R4: Database URL Format
- Python (asyncpg): `postgresql+asyncpg://...`
- Go (pgx): `postgresql://...`
- Config normalizer in `settings.py` auto-converts `postgres://` → `postgresql+asyncpg://`.

### R5: gRPC Metadata Header
Go Gateway attaches user JWT in gRPC metadata header `authorization: Bearer <token>`. Python verifies this in `backend/app/api/grpc_auth.py`.
- Internal calls also send `x-internal-api-key` header for service-to-service auth.

### R6: Session ID propagation
The `session_id` field must flow: Flutter → Go Gateway (WS message) → ChatRequest → ChatResponse → Flutter. Go Gateway preserves `session_id` from the response's `session_id` field.

### R7: Internal API routes
Routes under `/internal/*` on Go Gateway require `X-Internal-API-Key: <INTERNAL_API_KEY>` header. This is for Python → Go server-push calls (interventions, signals).

### R8: File Upload Flow
Files go directly Flutter → MinIO (presigned URL), NOT through the app server.
1. Flutter calls `POST /api/v1/files/upload/prepare` → gets presigned PUT URL
2. Flutter uploads directly to MinIO
3. Flutter calls `POST /api/v1/files/upload/complete` → triggers processing

### R9: Photon Balance Consistency
`users.photon_balance` must be updated atomically with `photon_transaction_history` insert. Never update balance without a corresponding transaction record.

### R10: Galaxy Node Mastery
`user_node_status.revision` is a logical clock. Always increment revision on update. Use optimistic concurrency: reject updates with stale revision.

### R11: Prefer router source over mobile constants
When `mobile/lib/core/network/api_endpoints.dart` conflicts with `backend/app/api/v1/router.py` + the owning FastAPI module, the server router is authoritative. Current known drift exists in statistics and some community encryption paths.

### R12: Gateway-native file upload endpoints are not Python REST endpoints
`/api/v1/files/upload/prepare` and `/api/v1/files/upload/complete` are implemented by Go Gateway file handlers. Python `files.py` owns internal processing endpoints such as `/files/process` and `/files/{file_id}/status`.

### R13: Gateway reverse-proxy behavior includes `NoRoute`
Do not assume only explicitly registered Gin routes reach Python. Unmatched paths can still be reverse-proxied by `NoRoute`, with different auth behavior for public vs protected paths.

### R14: Mobile direct gRPC is an allowed exception
Current repository state includes direct mobile gRPC calls to Python agent review services. Any refactor that removes or changes direct gRPC requires coordinated mobile updates.

---

## [15] CRITICAL INVARIANTS (NEVER VIOLATE)

```
[I1]  Flutter REST/WS traffic should go through Go Gateway (:8080), but current repo
      also includes direct mobile gRPC calls to Python agent services.
[I2]  Go Gateway NEVER implements AI logic or LLM calls.
[I3]  Python gRPC server (sparkle_agent) is the ONLY component that calls LLMs.
[I4]  Secrets (JWT_SECRET, API keys) live ONLY in .env, never in code.
[I5]  Proto-generated files are NEVER manually edited.
      Edit proto → run `make proto-gen` → edit implementations.
[I6]  DB schema changes: Alembic migration (Python) + `make sync-db` (Go sqlc).
      Never hand-edit models.go or schema.sql to add tables.
[I7]  Proto field numbers are IMMUTABLE once deployed.
[I8]  Redis DB 0 = app data, DB 1 = Celery broker, DB 2 = Celery results.
      Never cross-contaminate.
[I9]  The `metadata` keys in ChatResponse that contain JSON objects MUST be
      registered in `jsonMetadataKeys` in `chat_orchestrator_protocol.go`.
[I10] All user-visible top-level routes in Flutter should go through GoRouter (`routerProvider`).
      Never use Navigator.push for top-level navigation.
[I11] WebSocket auth uses short-lived tickets from `/api/v1/ws/ticket`,
      NOT long-lived JWTs directly (preferred flow for production).
[I12] Photon balance changes are ALWAYS atomic with transaction history.
[I13] Apache AGE graph and PostgreSQL tables are both used for knowledge graph.
      Do not assume only one is canonical.
```

---

## [16] DEPENDENCY VERSIONS

### Go Gateway (`backend/gateway/go.mod`)
```
go 1.24.0
gin v1.9.1
golang-jwt/jwt v5.3.0
gorilla/websocket v1.5.1
jackc/pgx v5.7.2
redis/go-redis v9.17.2
google.golang.org/grpc v1.78.0
google.golang.org/protobuf v1.36.11
go.opentelemetry.io/otel v1.39.0
prometheus/client_golang v1.23.2
minio/minio-go v7.0.71
go.uber.org/zap v1.27.0
spf13/viper v1.18.2
```

### Python Backend (`backend/requirements.txt`)
```
fastapi
sqlalchemy[asyncio]
alembic
asyncpg
pydantic-settings
grpcio
protobuf
langchain / langgraph
opentelemetry-*
celery
redis
loguru
passlib[bcrypt]
python-jose[cryptography]
```

### Flutter Mobile (`mobile/pubspec.yaml`)
```
flutter sdk: '>=3.0.0 <4.0.0'
flutter_riverpod: ^2.4.9
go_router: ^13.0.0
dio: ^5.4.0
web_socket_channel: ^3.0.3
grpc: ^5.1.0
protobuf: ^6.0.0
hive: ^2.2.3
isar: ^3.1.0+1
firebase_messaging: ^15.0.0
jpush_flutter: ^2.4.0
flutter_local_notifications: ^17.0.0
sentry_flutter: ^8.0.0
lottie: ^3.0.0
fl_chart: ^0.66.0
```

### Database
```
PostgreSQL: 16.x
pgvector: latest (from pgvector-age.Dockerfile)
Apache AGE: PG16/v1.6.0-rc0
Redis Stack: latest
```

### Build Tools
```
buf (protobuf toolchain): via docker/proto-toolchain.Dockerfile
sqlc: backend/gateway/sqlc.yaml
Alembic: Python migration tool
```

---

## QUICK REFERENCE: Adding a Feature

### New REST endpoint (Python only, no proto change)
1. Add route in `backend/app/api/v1/<module>.py`
2. Register in `backend/app/api/v1/router.py`
3. Add Flutter endpoint constant in `mobile/lib/core/network/api_endpoints.dart`
4. Add Flutter service method using Dio

### New gRPC method (cross-layer)
1. Edit proto file in `proto/`
2. Run `make proto-gen`
3. Implement in Python: `backend/app/services/agent_grpc_service.py`
4. Add Go client wrapper: `backend/gateway/internal/agent/client.go`
5. Add Go handler if needed: `backend/gateway/internal/handler/`
6. Add Flutter client: use generated `mobile/lib/gen/*.pb.dart`

### New WebSocket metadata key (structured JSON)
1. Add key to Python ChatResponse metadata dict
2. Add key to `jsonMetadataKeys` map in `backend/gateway/internal/handler/chat_orchestrator_protocol.go:29`
3. Add parsing in Flutter `websocket_chat_service_v2.dart`

### New database table
1. `cd backend && alembic revision -m "add_<table_name>"`
2. Write upgrade/downgrade in generated migration file
3. `alembic upgrade head`
4. If Go needs access: add query to `backend/gateway/internal/db/queries/query.sql`, run `make sync-db`

### New Celery task
1. Create task in `backend/app/tasks/` or `backend/app/workers/`
2. Register in `backend/app/celery_schedule.py` if periodic
3. Choose queue: `high_priority`, `default`, `low_priority`, or `glm_batch`
