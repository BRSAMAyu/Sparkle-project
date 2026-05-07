# CLAUDE.md — Sparkle (星火) AI Growth Companion

> **Architecture**: Go Gateway + Python Engine + Flutter Mobile | **Scale**: Large Monorepo (1,200+ source files)
> **Version**: 1.0.0+1 | **Updated**: 2026-05-03

---

## Project Vision

Sparkle is a Dual-Core Growth OS that helps users become better versions of themselves: achieve goals, reduce internal friction, gain fulfillment and happiness.

### Dual-Core Architecture

```
EXECUTION CORE:  Goal Clarification → Sufficiency Evaluation → Staged Plan → Tasks → Feedback → Adjustment
COGNITIVE CORE:  User Profile → Memory → Cognitive Prism → Emotion/Motivation/State → Personalized Support
Both cores collaborate via DualCoreRouter, not run in parallel isolation.
```

### Growth Loop

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

### Three-Layer Sandwich

```
FLUTTER (Presentation)   →  UI, state, UX | Riverpod | GoRouter | Multi-sensory
GO GATEWAY (Coordination) →  Auth, routing, caching, streams | Gin + WebSocket
PYTHON ENGINE (Intelligence) →  AI, RAG, tools, LLM | LangGraph FSM | FastAPI + gRPC
     ↕ PostgreSQL 16 + pgvector + AGE    ↕ Redis Stack    ↕ gRPC/WebSocket
```

---

## Aurora Adaptive Kernel

Aurora (Stages 4-40) governs how user behavioral signals flow into AI reasoning, routing, and prompt assembly. Safety enforced through **67+ governance rules** (CI via `scripts/run_all_rule_guards.sh`).

**Kill Switch Protocol**: Every Aurora feature ships behind tri-state: `off` → `shadow` → `live`. All switches expose Prometheus gauge. Drill scripts in `scripts/stage{N}/drill_transitions.sh`.

**Key services**: State Aggregator (`backend/app/state_aggregator/service.py`), Dual-Core Router (`backend/app/orchestration/dual_core_router.py`), Metacognition, Idiographic Association, SRL Phase Tracker, Social Signal Bridge, PII Privacy (`backend/app/aurora/privacy.py`), Kill Switch (`backend/app/core/kill_switch.py`).

**Governance**: Rules registered in `scripts/rule_guard_manifest.tsv`. Key families: write boundary (K/Y/Z/AB/AF), eval/safety (AM-AN-AO-AP-AQ), vision compliance (AS-AT-AU-AV), financial (BB/BC), security (AW-AX-AY-AZ). Run: `bash scripts/run_all_rule_guards.sh [--rule XX]`.

---

## Cognitive Protocol

| Level | Indicators | Protocol |
|-------|-----------|----------|
| **L1 Atomic** | Single file, <50 lines, typo/config | Execute immediately |
| **L2 Local** | 2-5 files, same language, single feature | Brief intent → Execute |
| **L3 Cross-Boundary** | Proto change, Go↔Python↔Flutter, DB schema | **Plan Required** |
| **L4 Architectural** | New subsystem, major refactor | **Deep Analysis Required** |

For L3+, output before any tool calls:
```
## Analysis
**Impact Scope**: [Go/Python/Flutter/DB/Proto]
**Risk Assessment**: [Low/Medium/High]
**Dependency Chain**: [A → B → C]

## Execution Plan
1. [Verify] 2. [Change] 3. [Propagate] 4. [Validate]
```

---

## Anti-Patterns (Hard Rules)

```
NEVER wrap XML tool tags in markdown code blocks
NEVER say "I will now..." — just execute
NEVER assume file paths exist — verify if >20% uncertain
NEVER modify generated files directly (see Source of Truth)
NEVER make partial edits that leave code in broken state
NEVER add direct DB calls in Go handlers (use service layer)
NEVER add business logic in Go Gateway (belongs in Python)
NEVER call Python REST from Python gRPC (internal only)
NEVER store secrets in code (use .env files)
NEVER skip proto regeneration after proto changes
NEVER add hardcoded tokens or passwords in production code
```

---

## Source of Truth

```
Proto Definition  →  Generated Code  →  Implementation
     (Edit)              (Generate)        (Edit)
```

| Domain | Source of Truth | Generate |
|--------|-----------------|----------|
| **API Contract** | `proto/*.proto` (buf.yaml) | `make proto-gen` |
| **DB Schema (Go)** | `backend/gateway/internal/db/schema.sql` | `make sync-db` |
| **DB Schema (Py)** | Alembic migrations | `alembic upgrade head` |
| **Design Tokens** | `mobile/lib/core/design/design_system.dart` | Manual |

**Never edit directly**: `backend/gateway/gen/`, `backend/app/gen/`, `mobile/lib/gen/`, `backend/gateway/internal/db/models.go`.

### Proto Files (6 files)

```
proto/
├── agent_service.proto      # Main agent RPC (StreamChat, SubmitPlanReview)
├── galaxy_service.proto     # Knowledge graph / Galaxy service
├── community_service.proto  # Community, friends, groups
├── error_book.proto         # Error archive / 错题本
├── stt_service.proto        # Speech-to-text
└── websocket.proto          # WebSocket message types
```

### Change Propagation

```
Proto change?     → make proto-gen → Update Go client + Python service + Flutter (make mobile-gen)
DB schema change? → alembic revision → alembic upgrade head → (if Go needs) make sync-db
```

---

## Codebase Navigation

### Request Flow (Chat)
```
Flutter websocket_chat_service_v2.dart → Go websocket_proxy.go → chat_orchestrator.go
→ agent/client.go (gRPC) → Python agent_grpc_service.py → orchestrator.py (FSM) → llm_service.py
```

### Request Flow (Plan Review)
```
Python plan_review_service.py → orchestrator.py → Go websocket_proxy.go
→ Flutter websocket_chat_service_v2.dart → chat_provider.dart → plan_review_card.dart
```

### Dual-Core Routing
```
dual_core_router.py → orchestrator.py (adjusts prompt/tone/tools) → ux_envelope.py → Streamed to Flutter
```

### Event Bus (Redis Streams)
```
KnowledgeNodeUpdated → Galaxy refresh | TaskCompleted → Achievement + photon reward
TaskAbandoned → Reflection | ErrorCreated → Cognitive fragment
ProfilePreferenceUpdated → Prompt update | CalendarEvent* → Notification scheduling

Bridges: community_signal_bridge.py, galaxy_event_consumer.py, achievement_event_consumer.py
```

### State Management
```
Flutter:  Riverpod → mobile/lib/features/*/presentation/providers/
Go:       Redis cache → backend/gateway/internal/service/
Python:   FSM context → backend/app/orchestration/orchestrator.py
Persist:  PostgreSQL → backend/gateway/internal/db/queries/
```

### Core Files (★★★★★)

| File | Role |
|------|------|
| `proto/agent_service.proto` | Main API contract |
| `backend/app/orchestration/orchestrator.py` | AI brain (LangGraph FSM) |
| `backend/app/orchestration/dual_core_router.py` | Dual-core routing |
| `backend/gateway/internal/handler/websocket_proxy.go` | Real-time hub |
| `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart` | Client connection |

### Integration Points (★★★★☆)

| File | Role |
|------|------|
| `backend/gateway/internal/agent/client.go` | Go→Python gRPC bridge |
| `backend/app/services/agent_grpc_service.py` | Python gRPC impl |
| `backend/app/orchestration/plan_review_service.py` | Plan review |
| `backend/app/orchestration/ux_envelope.py` | UX presentation adaptation |

---

## Command Reference

```bash
# Daily
make dev-all              # Start infrastructure (DB + Redis + MinIO)
make proto-gen            # After proto changes (uses buf)
make sync-db              # After DB changes (migrate + dump + sqlc)

# Component startup
make gateway-dev          # Go Gateway with hot reload
make grpc-server          # Python gRPC server
make mobile-run           # Flutter mobile app

# Signoff & verification
make env-check                        # Config + connectivity self-check
make smoke                            # Health check on all services
make local-signoff-preflight          # Full preflight: DB/Redis/ports/migrations/indexes
make local-final-signoff              # Complete signoff suite

# Celery
make celery-up / celery-status / celery-logs-worker / celery-flush / celery-stop

# Proto (Buf-based)
make proto-gen / proto-lint / proto-breaking / mobile-proto / mobile-gen

# Testing
cd backend && pytest tests/test_specific.py -v                    # Single Python test
cd backend && python scripts/ai_chat_multiturn_acceptance.py      # Acceptance script
cd backend/gateway && go test ./...                               # Go tests
cd mobile && flutter test                                         # Flutter tests

# Debugging
docker compose logs -f gateway / grpc-server                     # Service logs
grpcurl -plaintext localhost:50051 list                           # List gRPC services

# Utilities
alembic revision -m "desc" && alembic upgrade head                # DB migration
make init-rag / sync-rag                                          # RAG index
cd backend && python scripts/seed_demo_user_enhanced.py           # Demo data

# Quality & governance
make quality-baseline                                             # Full quality checks
python scripts/check_tech_debt_budget.py                          # Tech debt budget
bash scripts/run_all_rule_guards.sh [--rule AO]                   # Rule guards
bash scripts/journey_smoke.sh all                                 # Journey smoke
```

### Decision Tree
```
Proto file?    → make proto-gen → Update implementations
SQL schema?    → alembic revision → alembic upgrade head → make sync-db
Go code?       → make gateway-dev (auto-reload)
Python code?   → Restart grpc-server
Flutter code?  → Hot reload (r) or Hot restart (R)
```

---

## Architectural Invariants

| Layer | MUST Do | MUST NOT Do |
|-------|---------|-------------|
| **Flutter** | UI rendering, local state, user input | Business logic, direct API calls to Python |
| **Go Gateway** | Auth, WebSocket, caching, routing, rate limiting | AI reasoning, LLM calls, vector search |
| **Python Engine** | AI orchestration, RAG, tool execution, dual-core routing | User auth, session management |
| **PostgreSQL** | Persistent storage, vector similarity, graph queries | Caching (use Redis) |
| **Redis** | Session cache, rate limiting, event bus, pub/sub | Long-term storage |

### Interface Contracts

```
Flutter ←→ Go:    WebSocket (ws://localhost:8080/ws/chat), JSON, JWT auth
Go ←→ Python:     gRPC (localhost:50051), proto/agent_service.proto, server-streaming
Python ←→ DB:     SQLAlchemy (async), pgvector, Apache AGE, Alembic migrations
```

---

## Common Patterns

### Add AI Tool: `backend/app/tools/` → register in `dynamic_tool_registry.py` → (optional) expose via proto
### Add API Endpoint: Define in proto → `make proto-gen` → implement Python gRPC → implement Go client → expose handler
### DB Migration: `alembic revision` → write upgrade/downgrade → `alembic upgrade head` → (if Go) update queries + `make sync-db`
### Event Bus Signal: Define in `event_bus.py` → publish from source → create consumer with DLQ+retry → wire into bridges
### Backend-Driven Widget: Python sends metadata in delta → Go forwards unchanged → Flutter parses + emits widget event
### Aurora Kill Switch: `KillSwitchBinding` + settings attr + `read_mode()` check + register in manifest + drill script
### Governance Rule Guard: Script exits 0/non-zero → register in `rule_guard_manifest.tsv` → CI auto-discovers

---

## Debugging

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| WebSocket won't connect | Gateway down | `curl localhost:8080/api/v1/health` |
| gRPC timeout | Python server down | `grpcurl -plaintext localhost:50051 list` |
| "Field not found" | Proto out of sync | `make proto-gen` then restart |
| DB query fails | Migration not applied | `alembic current` vs `alembic heads` |
| Flutter type error | Outdated generated code | `flutter pub get && flutter clean` |
| Redis connection refused | Docker not running | `docker compose ps` |
| Signoff preflight fails | Config drift | `make env-check` then check `.env` ports |
| Achievement/visual empty | Demo data not seeded | `python scripts/seed_demo_user_enhanced.py` |

Trace across layers: `docker compose logs gateway 2>&1 | grep "request_id"` → same for `sparkle_agent` → DB query.

---

## Performance Hot Paths

1. WebSocket message parsing — every chat message
2. Orchestrator state transitions — FSM bottleneck
3. Vector similarity search — pgvector HNSW
4. LLM token streaming — real-time responsiveness
5. Event bus throughput — Redis Streams consumer lag

---

## Security Checklist (before any PR with auth/data/external calls)

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

Production guards: `DEBUG=True` raises ValueError, weak SECRET_KEY rejected, CORS `["*"]` rejected, gRPC reflection only in DEBUG.

---

## Pre-Commit Checklist

```
□ Code compiles/lints without errors
□ Generated files regenerated if sources changed
□ Tests pass (at minimum, affected area)
□ No hardcoded secrets or debug code
□ Proto backward compatible (if API change)
□ Tech debt budget not exceeded
```

---

## Local Signoff Protocol

```
1. Infrastructure:  docker compose up -d sparkle_db redis minio
2. Self-check:      make env-check && make local-signoff-preflight
3. Backend:         Start Python gRPC (50051) + API (8000) + Go Gateway (8080)
4. Smoke:           make smoke
5. Demo data:       cd backend && python scripts/seed_demo_user_enhanced.py
6. Full signoff:    make local-final-signoff
7. Flutter:         flutter run (iOS/Android simulator)
```

Confirm valid config/ports before trusting service status. Seed demo data before testing achievements/community/galaxy.

---

**Aurora Status**: Full Vision Complete (25/25 FV cards + 62/62 governance rules passing)
