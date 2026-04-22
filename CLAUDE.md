# CLAUDE.md — Sparkle (星火) AI Growth Companion

> **Project**: Sparkle (星火) — Dual-Core Growth OS for University Students
> **Architecture**: Go Gateway + Python Engine + Flutter Mobile | **Scale**: Large Monorepo (1,200+ source files)
> **Version**: 1.0.0+1 | **Last Updated**: 2026-03-31

---

## Project Vision

Sparkle is a Dual-Core Growth OS that helps users become better versions of themselves: achieve goals, reduce internal friction, gain fulfillment and happiness. Every subsystem serves this single purpose.

### The Dual-Core Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  EXECUTION CORE                                                          │
│  Goal Clarification → Sufficiency Evaluation → Staged Plan              │
│  → Executable Tasks → Execution Feedback → Dynamic Adjustment           │
├─────────────────────────────────────────────────────────────────────────┤
│  COGNITIVE CORE                                                          │
│  User Profile → Long/Short-term Memory → Cognitive Prism               │
│  → Emotion/Motivation/State Understanding → Personalized Support        │
├─────────────────────────────────────────────────────────────────────────┤
│  Both cores collaborate via DualCoreRouter, not run in parallel isolation │
└─────────────────────────────────────────────────────────────────────────┘
```

### Growth Loop: 7 Phases

All modules map to one of these phases:

```
Sense → Clarify → Plan → Execute → Reflect → Reinforce → Adapt
  │        │        │       │        │          │          │
  │        │        │       │        │          │          └─ AdaptiveReplanner
  │        │        │       │        │          └─ AchievementEngine
  │        │        │       │        └─ TaskFeedback / Reflection
  │        │        │       └─ DAG Executor / OpenClaw
  │        │        └─ ExecutablePlan v5.0 + 2-tier Review
  │        └─ SufficiencyChecker + GoalQualityEvaluator
  └─ ContextOrchestrator (6-dim aggregation) + Community signals
```

---

## Mental Model: The Three-Layer Sandwich

```
┌─────────────────────────────────────────────────────────────────┐
│  FLUTTER (Presentation)  →  User intent, UI state, UX flow     │
│  732 .dart files | Riverpod | GoRouter | Multi-sensory UX      │
├─────────────────────────────────────────────────────────────────┤
│  GO GATEWAY (Coordination) →  Auth, routing, caching, streams  │
│  24 .go files (production) | 16 middleware | Gin + WebSocket   │
├─────────────────────────────────────────────────────────────────┤
│  PYTHON ENGINE (Intelligence) →  AI logic, RAG, tools, LLM     │
│  319 .py files | LangGraph FSM | FastAPI + gRPC | 26 services  │
└─────────────────────────────────────────────────────────────────┘
         ↕ PostgreSQL 16 + pgvector + AGE    ↕ Redis Stack    ↕ gRPC/WebSocket
```

---

## Cognitive Protocol

### Task Complexity Classification

Before any action, classify the task:

| Level | Indicators | Protocol |
|-------|-----------|----------|
| **L1 Atomic** | Single file, <50 lines, typo/config | Execute immediately |
| **L2 Local** | 2-5 files, same language, single feature | Brief intent statement → Execute |
| **L3 Cross-Boundary** | Proto change, Go↔Python↔Flutter, DB schema | **Plan Required** |
| **L4 Architectural** | New subsystem, major refactor, design pattern | **Deep Analysis Required** |

### Planning Protocol (L3+)

For cross-boundary or architectural tasks, output this structure BEFORE any tool calls:

```
## Analysis

**Impact Scope**: [List affected layers: Go/Python/Flutter/DB/Proto]
**Risk Assessment**: [Low/Medium/High] — [One-line justification]
**Dependency Chain**: [A → B → C order of changes]

## Execution Plan

1. [Verification step - what to check first]
2. [Primary change - the core modification]
3. [Propagation - downstream updates]
4. [Validation - how to verify success]
```

---

## Anti-Patterns (Hard Rules)

These rules are NON-NEGOTIABLE. Violating them causes cascading failures.

### Code Generation Anti-Patterns
```
❌ NEVER wrap XML tool tags in markdown code blocks
❌ NEVER say "I will now..." or "Here is the code..." — just execute
❌ NEVER assume file paths exist — verify with ls or Glob if >20% uncertain
❌ NEVER modify generated files directly (see Source of Truth below)
❌ NEVER make partial edits that leave code in broken state
```

### Architectural Anti-Patterns
```
❌ NEVER add direct DB calls in Go handlers (use service layer)
❌ NEVER add business logic in Go Gateway (belongs in Python)
❌ NEVER call Python REST from Python gRPC (internal only)
❌ NEVER store secrets in code (use .env files)
❌ NEVER skip proto regeneration after proto changes
❌ NEVER add hardcoded tokens or passwords in production code
```

---

## Source of Truth Hierarchy

Understanding this hierarchy prevents 90% of bugs in this codebase.

### The Golden Rule
```
Proto Definition  →  Generated Code  →  Implementation
     (Edit)              (Generate)        (Edit)
```

### Detailed Truth Table

| Domain | Source of Truth | Generated From | Never Edit Directly |
|--------|-----------------|----------------|---------------------|
| **API Contract** | `proto/*.proto` (buf.yaml) | `make proto-gen` (Buf) | `backend/gateway/gen/`, `backend/app/gen/`, `mobile/lib/gen/` |
| **DB Schema (Go)** | `backend/gateway/internal/db/schema.sql` | `make sync-db` | `backend/gateway/internal/db/models.go` |
| **DB Schema (Py)** | Alembic migrations (52 files) | `alembic upgrade head` | SQLAlchemy models (must match) |
| **Design Tokens** | `mobile/lib/core/design/design_system.dart` | Manual | Component hardcoded values |

### Proto Files Overview (6 files)

```
proto/
├── agent_service.proto      # Main agent RPC (StreamChat, SubmitPlanReview, etc.)
├── galaxy_service.proto     # Knowledge graph / Galaxy service
├── community_service.proto  # Community, friends, groups, accountability
├── error_book.proto         # Error archive / 错题本 system
├── stt_service.proto        # Speech-to-text service
└── websocket.proto          # WebSocket message types
```

### Change Propagation Flowchart

```
Proto Change?
    │
    ├─→ make proto-gen (uses buf.build, falls back to protoc)
    │       │
    │       ├─→ Update Go client (backend/gateway/internal/agent/client.go)
    │       ├─→ Update Python service (backend/app/services/agent_grpc_service.py)
    │       └─→ Update Flutter: make mobile-gen
    │
DB Schema Change?
    │
    ├─→ Create Alembic migration (alembic revision -m "...")
    ├─→ Apply migration (alembic upgrade head)
    └─→ If Go needs data: Update queries → make sync-db
```

---

## Codebase Navigation Map

### Critical Path Analysis

These are the files you'll touch most often. Memorize their roles.

#### Request Flow (Chat Message)
```
1. mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart  # WebSocket client
   ↓ WebSocket message
2. backend/gateway/internal/handler/websocket_proxy.go   # Connection handler
   ↓ Parse & validate
3. backend/gateway/internal/handler/chat_orchestrator.go  # Flow control
   ↓ gRPC call
4. backend/gateway/internal/agent/client.go              # gRPC client wrapper
   ↓ StreamChat RPC
5. backend/app/services/agent_grpc_service.py            # gRPC service impl
   ↓ Orchestrate
6. backend/app/orchestration/orchestrator.py             # FSM state machine
   ↓ Tool calls / LLM
7. backend/app/services/llm_service.py                   # LLM abstraction
```

#### Request Flow (Plan Review)
```
1. backend/app/orchestration/plan_review_service.py  # Review orchestration
   ↓ Two-tier review (rule-based + LLM-based)
2. backend/app/orchestration/orchestrator.py         # Invokes review
   ↓ Stream response with review result
3. backend/gateway/internal/handler/websocket_proxy.go  # Forwards to client
   ↓ WebSocket message with delta + metadata
4. mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart  # Parses delta
   ↓ Detects metadata['requires_review'] == true
5. Emits PlanReviewWidgetEvent(reviewData: metadata)
   ↓
6. mobile/lib/features/chat/presentation/providers/chat_provider.dart  # State update
   ↓
7. mobile/lib/features/chat/presentation/widgets/plan_review_card.dart  # UI rendering
```

#### Dual-Core Routing Flow
```
1. backend/app/orchestration/dual_core_router.py      # Routes Execution vs Cognitive core
   ↓ DualCoreRoutingInput (intent, confidence, sentiment, plan health, etc.)
   ↓ Outputs DualCoreDecision (mode, reason, cognitive_adjustments, execution_constraints)
2. backend/app/orchestration/orchestrator.py          # Consumes routing decision
   ↓ Adjusts prompt, tone, tool access, verbosity
3. backend/app/orchestration/ux_envelope.py           # UX presentation layer
   ↓ PresentationProfile (mode_label, companion_frame, answer_kind, next_actions)
4. Streamed to Flutter via Go Gateway
```

#### Event Bus Signal Mesh
```
EventBus (Redis Streams) → Consumer Groups → DLQ + Retry
    │
    ├── KnowledgeNodeUpdated  → Galaxy display refresh
    ├── TaskCompleted         → AchievementEngine check + photon reward
    ├── TaskAbandoned         → Reflection trigger + pattern analysis
    ├── ErrorCreated          → Cognitive fragment + knowledge penalty
    ├── ProfilePreferenceUpdated → Prompt injection update
    ├── UserSettingsUpdated   → UX envelope re-evaluation
    └── CalendarEvent*        → Notification scheduling

Cross-system bridges:
    community_signal_bridge.py  → Group activity → Personal context
    galaxy_event_consumer.py    → Knowledge events → Plan constraints
    achievement_event_consumer.py → Achievement unlock → Frontend notification
```

#### State Management Layers
```
Flutter State:    Riverpod providers → mobile/lib/features/*/presentation/providers/
Go State:         Redis cache → backend/gateway/internal/service/chat_history.go
Python State:     FSM context → backend/app/orchestration/orchestrator.py
Persistent State: PostgreSQL (143 tables) → backend/gateway/internal/db/queries/
```

### File Importance Ranking

When exploring unfamiliar territory, prioritize these files:

```
★★★★★ (Core Logic)
├── proto/agent_service.proto              # Main API contract
├── proto/galaxy_service.proto             # Knowledge graph API
├── backend/app/orchestration/orchestrator.py         # AI brain (LangGraph FSM)
├── backend/app/orchestration/dual_core_router.py     # Dual-core routing decision
├── backend/gateway/internal/handler/websocket_proxy.go  # Real-time hub
└── mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart  # Client connection

★★★★☆ (Integration Points)
├── backend/gateway/internal/agent/client.go   # Go→Python bridge
├── backend/app/services/agent_grpc_service.py  # Python gRPC impl
├── backend/app/orchestration/plan_review_service.py  # Plan review orchestration
├── backend/app/orchestration/ux_envelope.py    # UX presentation adaptation
├── backend/gateway/internal/service/*.go       # Business services (12 files)
├── mobile/lib/features/chat/presentation/providers/*.dart   # State providers (10 files)
└── mobile/lib/features/chat/presentation/widgets/plan_review_card.dart  # Plan review UI

★★★☆☆ (Supporting Infrastructure)
├── backend/gateway/internal/db/schema.sql      # DB structure (13K lines, 143 tables)
├── backend/app/orchestration/dynamic_tool_registry.py  # Tool system
├── backend/app/core/event_bus.py               # Redis Streams event bus
├── backend/app/services/achievement_engine.py  # Achievement + contract + sprint events
├── backend/app/services/cognitive_service.py   # Cognitive prism
├── backend/app/services/memory_service.py      # Long/short-term memory
├── backend/app/services/galaxy_service.py      # Knowledge graph operations
├── backend/app/services/community_service.py   # Community + groups + accountability
├── backend/alembic/                            # DB migrations (52 files)
├── docker-compose.yml                          # 17 services (app + infra + monitoring)
├── mobile/lib/core/design/design_system.dart   # UI tokens
├── mobile/lib/core/services/bgm_service.dart   # Route-aware BGM orchestration
├── mobile/lib/core/services/sensory_feedback_service.dart  # Haptic/SFX budget
├── mobile/lib/core/widgets/scene_audio_scope.dart  # Scene-scoped audio
├── mobile/lib/core/design/widgets/sparkle_motion_primitives.dart  # Motion primitives
└── mobile/lib/core/design/widgets/sparkle_confetti.dart  # Celebration layer
```

---

## System Inventory

### Backend Services (26 service files in `backend/app/services/`)

| Service | File | Purpose |
|---------|------|---------|
| LLM Service | `llm_service.py` | Multi-provider LLM abstraction |
| Memory Service | `memory_service.py` | Episodic + semantic memory |
| Cognitive Service | `cognitive_service.py` | Cognitive prism / patterns |
| Galaxy Service | `galaxy_service.py` | Knowledge graph operations |
| Community Service | `community_service.py` | Groups, friends, accountability |
| Achievement Engine | `achievement_engine.py` | 19 event types, contracts, sprints |
| Community Signal Bridge | `community_signal_bridge.py` | Group→Personal context bridge |
| Galaxy Event Consumer | `galaxy_event_consumer.py` | Knowledge events→Plan constraints |
| Achievement Event Consumer | `achievement_event_consumer.py` | Unlock→Notification |
| Progress Narrative | `progress_narrative_service.py` | Growth storytelling |
| Behavior Signal Collector | `behavior_signal_collector.py` | Behavioral pattern detection |
| OpenClaw Client | `adapters/openclaw/client.py` | Digital task execution |
| Theater Service | `services/theater/` | Path prediction + what-if analysis |
| Simulation Engine | `services/simulation/` | Scenario simulation |
| Learning Report | `services/report/` | Mastery report generation |
| STT Service | `services/stt/` | Speech-to-text |

### Go Gateway Middleware (16 files in `backend/gateway/internal/middleware/`)

| Middleware | File | Purpose |
|-----------|------|---------|
| Auth | `auth.go` | JWT (HS256) with blacklist + fail-closed |
| WS Auth | `ws_auth.go` | WebSocket JWT (header/query/ticket) |
| Rate Limit | `rate_limit.go` | IP + auth + WebSocket + adaptive |
| Distributed Rate Limit | `distributed_rate_limiter.go` | Redis sliding window |
| CORS | `cors.go` | Origin allowlist (not wildcard) |
| Security Headers | `security.go` | CSP + HSTS + X-Frame-Options + Permissions-Policy |
| Timeout | `timeout.go` | Request timeout enforcement |
| Internal API | `internal_api.go` | API key validation (timing-attack resistant) |
| IP Whitelist | `internal_ip_whitelist.go` | /internal endpoints protection |
| Chaos Guard | `chaos_guard.go` | Chaos engineering |
| A/B Test | `ab_test_middleware.go` | Experiment routing |
| Request Context | `request_context.go` | Context injection |

### Flutter Feature Modules (24 route modules)

```
achievement | auth | calendar | chat | cognitive | community | error_book |
focus | galaxy | home | insights | memory | notification_center | openclaw |
photon | plan | report | seed_library | shop | simulation | splash |
task | theater | tools | translation | user | visual_elements
```

### Docker Services (17 containers)

| Category | Services |
|----------|---------|
| **Infrastructure** | sparkle_db (PG16+pgvector+AGE), redis (Stack), minio |
| **Application** | sparkle_api (FastAPI:8000), sparkle_agent (gRPC:50051), sparkle_gateway (Go:8080), celery_worker, celery_glm_batch_worker |
| **Monitoring** | prometheus, grafana, loki, tempo, promtail, alertmanager |

---

## Command Reference

### Quick Reference Card

```bash
# === DAILY WORKFLOW ===
make dev-all              # Start infrastructure (DB + Redis + MinIO)
make proto-gen            # After proto changes (uses buf)
make sync-db              # After DB changes (migrate + dump + sqlc)

# === COMPONENT STARTUP ===
make gateway-dev          # Go Gateway with hot reload
make grpc-server          # Python gRPC server
make mobile-run           # Flutter mobile app

# === SIGNOFF & VERIFICATION ===
make env-check                        # Config + connectivity self-check
make smoke                            # Health check on all services
make local-signoff-preflight          # Full preflight: DB/Redis/ports/migrations/indexes
make local-final-signoff              # Complete signoff suite: preflight + smoke + tests + acceptances

# === CELERY TASK QUEUE ===
make celery-up            # Start Celery worker + beat (optional flower: FLOWER_ENABLE=1)
make celery-status        # Check Celery services status
make celery-logs-worker   # View worker logs
make celery-flush         # Flush Redis queues
make celery-stop          # Stop all Celery services

# === PROTO GENERATION (Buf-based) ===
make proto-gen            # Generate Go/Python/Dart from proto (via buf)
make proto-lint           # Lint proto files
make proto-breaking       # Check for breaking changes vs main branch
make mobile-proto         # Generate only Dart protobufs
make mobile-gen           # Generate Dart protobufs + run build_runner

# === TESTING ===
cd backend && pytest                                              # Python tests (asyncio_mode=auto)
cd backend && pytest tests/test_specific.py -v                    # Single Python test file
cd backend && python scripts/ai_chat_multiturn_acceptance.py      # Run specific acceptance
cd backend/gateway && go test ./...                               # Go tests
cd mobile && flutter test                                         # Flutter tests

# === DEBUGGING ===
docker compose logs -f gateway      # Go logs
docker compose logs -f grpc-server  # Python logs
grpcurl -plaintext localhost:50051 list  # List gRPC services

# === UTILITIES ===
alembic revision -m "desc"              # New Alembic migration
alembic upgrade head                    # Apply migrations
make init-rag                           # Initialize Redis search index (RAG v2.0)
make sync-rag                           # Sync PG knowledge nodes to Redis
cd backend && python scripts/seed_demo_user_enhanced.py  # Seed demo data for testing

# === QUALITY ===
make quality-baseline                   # Run full quality baseline checks
python scripts/check_tech_debt_budget.py  # Check tech debt against budget
```

### Command Decision Tree

```
What changed?
│
├─→ Proto file? → make proto-gen → Update implementations
│
├─→ SQL schema? → alembic revision → alembic upgrade head → make sync-db
│
├─→ Go code? → make gateway-dev (auto-reload)
│
├─→ Python code? → Restart grpc-server
│
└─→ Flutter code? → Hot reload (r) or Hot restart (R)
```

---

## Architectural Invariants

These rules define the system's structural integrity. Never violate them.

### Layer Responsibility Matrix

| Layer | MUST Do | MUST NOT Do |
|-------|---------|-------------|
| **Flutter** | UI rendering, local state, user input | Business logic, direct API calls to Python |
| **Go Gateway** | Auth, WebSocket, caching, routing, rate limiting | AI reasoning, LLM calls, vector search |
| **Python Engine** | AI orchestration, RAG, tool execution, dual-core routing | User auth, session management |
| **PostgreSQL** | Persistent storage, vector similarity, graph queries | Caching (use Redis) |
| **Redis** | Session cache, rate limiting, event bus (Streams), pub/sub | Long-term storage |

### Interface Contracts

```
Flutter ←→ Go Gateway
  Protocol: WebSocket (ws://localhost:8080/ws/chat)
  Format: JSON messages with type field
  Auth: JWT in connection header or single-use ticket

Go Gateway ←→ Python Engine
  Protocol: gRPC (localhost:50051)
  Contract: proto/agent_service.proto (and 5 other proto files)
  Streaming: Server-side streaming for chat

Python Engine ←→ Database
  ORM: SQLAlchemy (async)
  Vectors: pgvector with L2/Cosine distance
  Graph: Apache AGE (sparkle_galaxy schema)
  Migrations: Alembic (52 files)
```

---

## Security Architecture

### Authentication Flow
- **JWT (HS256)**: Access + Refresh tokens with exp/iat/jti/type/iss/aud claims
- **Token Blacklist**: JTI-based revocation + user-level revocation (user_revoked_before)
- **Fail-Closed**: Non-development boots force `REDIS_FAIL_CLOSED=true` when unset; development defaults remain fail-open for local debugging
- **Timing-Attack Resistant**: Gateway secret checks use constant-time comparison when secrets are configured; backend internal endpoints still depend on a non-empty `INTERNAL_API_KEY` to enforce validation

### Multi-Layer Rate Limiting
- IP-based: 10 req/s, burst 30
- Auth endpoints: 5 req/s, burst 15
- WebSocket connection: 5/min, burst 10
- Adaptive: Stricter for auth endpoints under load
- Distributed: Redis sliding window with local fallback

### Security Headers (auto-injected)
- `Content-Security-Policy` (strict, no unsafe-inline for scripts)
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security` (production only)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (restricts geolocation, camera, microphone, payment)

### Production Guards
- `DEBUG=True` in production raises `ValueError`
- Weak `SECRET_KEY` values rejected in production
- `BACKEND_CORS_ORIGINS=["*"]` rejected in production
- gRPC reflection only enabled in DEBUG mode
- HTML sanitization via bluemonday in Go Gateway

---

## Monitoring & Observability

### Stack
```
Prometheus (9090) → Metrics collection + alerting
Grafana (3000)    → Dashboards + datasources (Prometheus + Loki + Tempo)
Loki (3100)       → Log aggregation
Tempo (4317)      → Distributed tracing (OTLP gRPC + HTTP)
Promtail          → Log shipping (Docker socket, read-only)
Alertmanager (9093) → Alert routing (webhook + email)
```

### SLO Alert Rules (11 rules)

| Alert | Severity | Condition |
|-------|----------|-----------|
| SparkleGatewayDown | P1 Critical | Gateway unreachable for 2m |
| SparkleBackendDown | P1 Critical | Backend unreachable for 2m |
| SparkleBackendHigh5xxRate | P2 Warning | 5xx ratio > 2% for 10m |
| SparkleBackendP95LatencyHigh | P2 Warning | P95 > 1.5s for 10m |
| SparkleEventStreamLagHigh | P2 Warning | Event stream lag > 120s |
| SparkleContextPackOverBudgetSpike | P3 Warning | > 20 over-budget events in 10m |
| AIFirstTokenLatency | Baseline | First token latency monitoring |
| AITotalDuration | Baseline | Total AI call duration |
| OutboxBacklog | Baseline | Event outbox accumulation |
| BackendMemory | Baseline | Python backend memory |
| GatewayGoroutines | Baseline | Go goroutine count |

Runbook: `monitoring/runbooks/incident_response.md`

---

## CI/CD Pipeline

### Main CI (`.github/workflows/ci.yml`)

**Triggers**: push to main/develop, tags `v*`, PRs to main
**Tool versions**: Go 1.22.0, Python 3.11, Flutter 3.24.0

| Job | Runs | Key Steps |
|-----|------|-----------|
| **lint** | Always | golangci-lint (22 linters), ruff + mypy, flutter analyze + tech debt budget |
| **backend-test** | After lint | Go tests (race + coverage), Python tests (contract + workflow), proto/OpenAPI/dependency checks |
| **flutter-test** | After lint | Flutter tests + coverage, critical smoke + regression suites |
| **security-scan** | After lint | Trivy vulnerability scanner, Gitleaks secret detection |

### Additional Workflows (9 files)

| Workflow | Purpose |
|----------|---------|
| `e2e-tests.yml` | Nightly E2E test suite |
| `e2e-smoke.yml` | E2E smoke tests |
| `quality-baseline.yml` | Weekly quality baseline |
| `benchmark.yml` | Performance benchmarks |
| `ui-lint.yml` | UI-specific linting |
| `deploy-prod.yml` | Production deployment |
| `cd_k8s.yml` | Kubernetes CD pipeline |
| `gemini-review.yml` | AI-powered code review |
| `gemini-triage.yml` | AI issue triage |

### Pre-commit Hooks (10 hooks)

Python: Ruff lint + format, MyPy type checking
Go: go-fmt, go-vet, go-imports, golangci-lint
Protobuf: buf-lint
Security: gitleaks
Formatting: trailing whitespace, end-of-file, YAML/JSON, merge conflicts, private keys, large files

---

## Testing Strategy

### Test Scale

| Layer | Test Files | Key Acceptance Scripts |
|-------|-----------|----------------------|
| Python | 311 | 21 acceptance scripts covering all major chains |
| Go | 34 (incl. 20 handler tests) | Contract tests, benchmark tests |
| Flutter | 131 | Smoke tests, golden tests, widget tests, integration tests |
| **Total** | **476** | |

### Acceptance Test Coverage (21 scripts in `backend/scripts/`)

```
ai_chat_multiturn_acceptance.py      # AI对话多轮验收
accountability_acceptance.py          # 责任伙伴验收
galaxy_plan_acceptance.py             # 星图计划验收
achievement_visual_acceptance.py      # 成就视觉元素验收
seed_library_acceptance.py            # 种子库验收
insights_acceptance.py                # 学习洞察验收
cognitive_capsule_acceptance.py       # 认知胶囊验收
community_acceptance.py               # 社群验收
community_share_adopt_acceptance.py   # 社群采纳验收
focus_acceptance.py                   # 专注系统验收
calendar_weather_acceptance.py        # 日历天气验收
memory_acceptance.py                  # 记忆系统验收
notes_errorbook_acceptance.py         # 错题本验收
translation_dictionary_acceptance.py  # 翻译词典验收
document_stt_acceptance.py            # 文档语音验收
long_term_plan_acceptance.py          # 长期计划验收
celery_acceptance.py                  # Celery队列验收
security_acceptance.py                # 安全验收
api_contract_acceptance.py            # API契约验收
community_admin_acceptance.py         # 社群管理验收
ai_expert_acceptance.py               # AI专家模式验收
```

### Code Quality Configuration

| Tool | Config | Key Settings |
|------|--------|-------------|
| Python Ruff | `pyproject.toml` | Python 3.11, line-length 120, rules: E/W/F/I/B/C4/UP/ARG/SIM |
| Python MyPy | `pyproject.toml` | `warn_return_any`, `warn_unused_configs`, `ignore_missing_imports` |
| Go golangci-lint | `.golangci.yml` | 22 linters (gosec audit, staticcheck, gocritic), complexity threshold 15 |
| Flutter analyze | `analysis_options.yaml` | strict-casts, strict-inference, strict-raw-types, 60+ rules |

---

## Common Refactoring Patterns

### Pattern 1: Adding a New AI Tool

```
1. Create tool file: backend/app/tools/my_tool.py
   - Inherit from BaseTool
   - Implement execute() method
   - Define schema for LLM function calling

2. Register tool: backend/app/orchestration/dynamic_tool_registry.py
   - Add to tool registry
   - Tool auto-available to orchestrator

3. (Optional) Expose via API: proto/agent_service.proto
   - Only if direct client access needed
```

### Pattern 2: Adding a New API Endpoint

```
1. Define in proto: proto/agent_service.proto (or relevant proto)
   - Add message types
   - Add RPC method

2. Regenerate: make proto-gen

3. Implement Python: backend/app/services/agent_grpc_service.py
   - Add method matching proto definition

4. Implement Go client: backend/gateway/internal/agent/client.go
   - Add wrapper method

5. Expose endpoint: backend/gateway/internal/handler/
   - REST: Add Gin handler
   - WebSocket: Add message type handler
```

### Pattern 3: Database Schema Migration

```
1. Plan migration: Consider both Go and Python access patterns

2. Create Alembic migration:
   cd backend && alembic revision -m "add_user_preferences"

3. Write migration: backend/alembic/versions/xxxx_add_user_preferences.py
   - def upgrade(): ADD changes
   - def downgrade(): REVERSE changes

4. Apply: alembic upgrade head

5. If Go needs access:
   - Update queries: backend/gateway/internal/db/queries/
   - Regenerate: make sync-db
```

### Pattern 4: Adding an Event Bus Signal

```
1. Define event: backend/app/core/event_bus.py
   - Add event class with event_type string

2. Publish event from source service:
   await event_bus.publish(MyEvent(...))

3. Create consumer (if new service needed):
   - Subscribe to event_type
   - Process with DLQ + retry

4. Wire into existing bridges if cross-system:
   - community_signal_bridge.py (community → personal)
   - galaxy_event_consumer.py (knowledge → plan)
   - achievement_event_consumer.py (achievement → UI)
```

### Pattern 5: Backend-Driven Widget Events (Plan Review Style)

```
1. Python Backend (orchestrator.py):
   - Generate review result using plan_review_service.py
   - Send review data in metadata field of delta response

2. Go Gateway (websocket_proxy.go):
   - Forwards response unchanged to Flutter client
   - No special handling needed

3. Flutter WebSocket Service (websocket_chat_service_v2.dart):
   - Parse delta message
   - Check if metadata['requires_review'] == true
   - Emit PlanReviewWidgetEvent(reviewData: metadata)

4. Flutter UI (plan_review_card.dart):
   - Listen for PlanReviewWidgetEvent in chat provider
   - Display review card with animations
   - Handle user actions (approve, reject, modify)

5. User Feedback Loop:
   - User submits decision via SubmitPlanReview gRPC
   - Backend processes and updates plan accordingly
```

### Pattern 6: OpenClaw Integration

```
1. Backend adapter: backend/app/adapters/openclaw/
   - client.py: HTTP or Gateway WebSocket transport
   - intent_translator.py: Internal → OpenClaw format
   - result_parser.py: OpenClaw → Internal format

2. Execution services: backend/app/services/execution/
   - execution_service.py, execution_router.py

3. API exposure: backend/app/api/v1/executions.py
   - REST endpoints for execution management

4. Flutter: features/openclaw/ + settings screens
   - Hub screen, connection panel, settings
```

---

## Debugging Strategies

### Symptom → Diagnosis Table

| Symptom | Likely Cause | Diagnostic Command |
|---------|--------------|-------------------|
| WebSocket won't connect | Gateway not running | `curl http://localhost:8080/api/v1/health` |
| gRPC timeout | Python server down | `grpcurl -plaintext localhost:50051 list` |
| "Field not found" error | Proto out of sync | `make proto-gen` then restart |
| DB query fails | Migration not applied | `alembic current` vs `alembic heads` |
| Flutter type error | Outdated generated code | `flutter pub get && flutter clean` |
| Redis connection refused | Docker not running | `docker compose ps` |
| Signoff preflight fails | Config drift or port conflict | `make env-check` then check `.env` ports |
| Star map / learning path fails | Missing prerequisite baseline | `make local-signoff-preflight` → check knowledge_prerequisite_baseline |
| Achievement / visual elements empty | Demo data not seeded | `python scripts/seed_demo_user_enhanced.py` |

### Log Correlation Strategy

```bash
# Trace a request across layers
# 1. Get request ID from Flutter logs
# 2. Search Go Gateway logs
docker compose logs gateway 2>&1 | grep "request_id"

# 3. Search Python logs
docker compose logs sparkle_agent 2>&1 | grep "request_id"

# 4. Check database if needed
docker compose exec sparkle_db psql -U postgres -d sparkle -c "SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 5;"
```

---

## Performance Considerations

### Hot Paths (Optimize First)
1. **WebSocket message parsing** — Every chat message goes through here
2. **Orchestrator state transitions** — FSM bottleneck
3. **Vector similarity search** — pgvector HNSW query performance
4. **LLM token streaming** — Real-time responsiveness
5. **Event bus throughput** — Redis Streams consumer group lag

### Caching Layers
```
Request → Redis (chat history, rate limits, event streams)
        → Go semantic cache (RAG results)
        → Python LRU (embeddings, tool schemas)
        → PostgreSQL (persistent, 143 tables)
```

### Connection Pools
- Go → PostgreSQL: sqlc with pgxpool (default 10 connections)
- Go → Redis: go-redis with pooling
- Python → PostgreSQL: asyncpg pool
- Go → Python gRPC: Connection reuse

---

## Documentation Locations

| Topic | Location |
|-------|----------|
| Developer Docs Entry | `docs/README.md` |
| Architecture Overview | `docs/00_项目概览/02_技术架构.md` |
| API Reference | `docs/02_技术设计文档/03_API参考.md` |
| Knowledge Graph Design | `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md` |
| Implementation Guides | `docs/03_功能实现指南/` |
| Deployment & Ops | `docs/05_部署与运维/` |
| Engineering Standards | `docs/engineering/` (quality guardrails, SLO targets, tech debt register) |
| Verification Checklists | `docs/verification/` (acceptance checklists, signoff baselines) |
| ADR Records | `docs/adr/` (3 ADRs) |
| Proto Definitions | `proto/*.proto` (6 files, canonical) |
| Runbook | `monitoring/runbooks/incident_response.md` |

---

## Security Checklist

Before any PR involving auth, data, or external calls:

```
□ Secrets only in .env files (never in code)
□ No hardcoded tokens or passwords (including test files)
□ .env.migration and similar files in .gitignore
□ User input validated at Go Gateway layer
□ SQL queries use parameterized statements
□ WebSocket messages sanitized (bluemonday)
□ Rate limiting applied for expensive operations
□ Error messages don't leak internal details
□ Timing-attack resistant comparison for secrets
□ Security headers present (CSP, HSTS, X-Frame-Options)
```

---

## Pre-Commit Checklist

Before considering any task complete:

```
□ Code compiles/lints without errors
□ Generated files regenerated if sources changed
□ Tests pass (at minimum, affected area)
□ No hardcoded secrets or debug code
□ Comments updated if behavior changed
□ Proto backward compatible (if API change)
□ Tech debt budget not exceeded (python scripts/check_tech_debt_budget.py)
```

---

## Local Signoff Protocol

Before final manual verification, run this sequence (do not skip steps):

```
1. Infrastructure:  docker compose up -d sparkle_db redis minio
2. Self-check:      make env-check && make local-signoff-preflight
3. Backend:         Start Python gRPC (50051) + API (8000) + Go Gateway (8080)
4. Smoke:           make smoke
5. Demo data:       cd backend && python scripts/seed_demo_user_enhanced.py
6. Full signoff:    make local-final-signoff
7. Flutter:         flutter run (iOS/Android simulator)
```

**Critical principles**:
- Confirm valid config and ports before trusting service status
- Confirm 8000/8080 healthy before entering simulator
- Seed demo data before testing achievements/visual/community/galaxy
- Local DB default: `127.0.0.1:5432` — if changed, sync `.env` + `backend/.env` + `backend/gateway/.env`

---

## Technical Debt Register

Tracked in `docs/engineering/technical_debt_register_2026-03-22.md` with 10 items (TD-001 through TD-010).

Budget enforced by `scripts/check_tech_debt_budget.py` using `quality/tech_debt_budget.json`.

---

**Document Version**: 3.0.0
**Last Updated**: 2026-03-31
**Project Version**: Sparkle v1.0.0+1
**Current Branch**: 复赛前修复打磨
