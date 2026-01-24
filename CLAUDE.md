# CLAUDE.md — Opus 4.5 Optimized Edition

> **Model Target**: Claude Opus 4.5 | **Project**: Sparkle (星火) AI Learning Assistant
> **Architecture**: Go Gateway + Python Engine + Flutter Mobile | **Scale**: Large Monorepo

---

## 🧠 Cognitive Protocol for Opus 4.5

This section defines how Claude should think and operate in this complex codebase.

### Mental Model: The Three-Layer Sandwich

```
┌─────────────────────────────────────────────────────────────────┐
│  FLUTTER (Presentation)  →  User intent, UI state, UX flow     │
├─────────────────────────────────────────────────────────────────┤
│  GO GATEWAY (Coordination) →  Auth, routing, caching, streams  │
├─────────────────────────────────────────────────────────────────┤
│  PYTHON ENGINE (Intelligence) →  AI logic, RAG, tools, LLM     │
└─────────────────────────────────────────────────────────────────┘
         ↕ PostgreSQL + pgvector    ↕ Redis    ↕ gRPC/WebSocket
```

### Task Complexity Classification

Before any action, classify the task:

| Level | Indicators | Protocol |
|-------|-----------|----------|
| **L1 Atomic** | Single file, <50 lines, typo/config | Execute immediately, no explanation |
| **L2 Local** | 2-5 files, same language, single feature | Brief intent statement → Execute |
| **L3 Cross-Boundary** | Proto change, Go↔Python, DB schema | 🔍 **Plan Required** (see below) |
| **L4 Architectural** | New subsystem, major refactor, design pattern | 📋 **Deep Analysis Required** |

### 🔍 Planning Protocol (L3+)

For cross-boundary or architectural tasks, output this structure BEFORE any tool calls:

```
## 🔍 Analysis

**Impact Scope**: [List affected layers: Go/Python/Flutter/DB/Proto]
**Risk Assessment**: [Low/Medium/High] — [One-line justification]
**Dependency Chain**: [A → B → C order of changes]

## 📋 Execution Plan

1. [Verification step - what to check first]
2. [Primary change - the core modification]
3. [Propagation - downstream updates]
4. [Validation - how to verify success]
```

---

## 🚫 Anti-Patterns (Hard Rules)

These rules are NON-NEGOTIABLE. Violating them causes cascading failures.

### Code Generation Anti-Patterns
```
❌ NEVER wrap XML tool tags in markdown code blocks
❌ NEVER say "I will now..." or "Here is the code..." — just execute
❌ NEVER assume file paths exist — verify with `ls` or `find` if >20% uncertain
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
```

---

## 📜 Source of Truth Hierarchy

Understanding this hierarchy prevents 90% of bugs in this codebase.

### The Golden Rule
```
Proto Definition  →  Generated Code  →  Implementation
     (Edit)              (Generate)        (Edit)
```

### Detailed Truth Table

| Domain | Source of Truth | Generated From | Never Edit Directly |
|--------|-----------------|----------------|---------------------|
| **API Contract** | `proto/agent_service.proto` | `make proto-gen` | `backend/gateway/gen/`, `backend/app/gen/` |
| **DB Schema (Go)** | `backend/gateway/internal/db/schema.sql` | `make sync-db` | `backend/gateway/internal/db/models.go` |
| **DB Schema (Py)** | Alembic migrations | `alembic upgrade head` | SQLAlchemy models (must match) |
| **Design Tokens** | `mobile/lib/core/design/design_system.dart` | Manual | Component hardcoded values |

### Change Propagation Flowchart

```
Proto Change?
    │
    ├─→ make proto-gen
    │       │
    │       ├─→ Update Go client (backend/gateway/internal/agent/client.go)
    │       └─→ Update Python service (backend/app/services/agent_grpc_service.py)
    │
DB Schema Change?
    │
    ├─→ Create Alembic migration (alembic revision -m "...")
    ├─→ Apply migration (alembic upgrade head)
    └─→ If Go needs data: Update queries → make sync-db
```

---

## 🗺 Codebase Navigation Map

### Critical Path Analysis

These are the files you'll touch most often. Memorize their roles.

#### Request Flow (Chat Message)
```
1. mobile/lib/core/services/chat_service.dart     # WebSocket client
   ↓ WebSocket message
2. backend/gateway/internal/handler/websocket.go  # Connection handler
   ↓ Parse & validate
3. backend/gateway/internal/handler/chat_orchestrator.go  # Flow control
   ↓ gRPC call
4. backend/gateway/internal/agent/client.go       # gRPC client wrapper
   ↓ StreamChat RPC
5. backend/app/services/agent_grpc_service.py     # gRPC service impl
   ↓ Orchestrate
6. backend/app/orchestration/orchestrator.py      # FSM state machine
   ↓ Tool calls / LLM
7. backend/app/services/llm_service.py            # LLM abstraction
```

#### Request Flow (Plan Review)
```
1. backend/app/orchestration/plan_review_service.py  # Review orchestration
   ↓ Two-tier review (rule-based + LLM-based)
2. backend/app/orchestration/orchestrator.py         # Invokes review
   ↓ Stream response with review result
3. backend/gateway/internal/handler/websocket.go     # Forwards to client
   ↓ WebSocket message with delta + metadata
4. mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart  # Parses delta
   ↓ Detects metadata['requires_review'] == true
5. Emits PlanReviewWidgetEvent(reviewData: metadata)
   ↓
6. mobile/lib/features/chat/presentation/providers/chat_provider.dart  # State update
   ↓
7. mobile/lib/features/chat/presentation/widgets/plan_review_card.dart  # UI rendering
```

**Event Flow Detail:**
```json
// Backend sends:
{
  "type": "delta",
  "delta": "Review completed...",
  "metadata": {
    "requires_review": true,
    "review_data": {
      "plan_id": "plan-123",
      "review_id": "review-456",
      "overall_score": 85,
      "issues": [...]
    }
  }
}

// Flutter receives and emits:
PlanReviewWidgetEvent(reviewData: {...})
```

#### State Management Layers
```
Flutter State:    Riverpod providers → mobile/lib/presentation/providers/
Go State:         Redis cache → backend/gateway/internal/service/chat_history.go
Python State:     FSM context → backend/app/orchestration/orchestrator.py
Persistent State: PostgreSQL → backend/gateway/internal/db/queries/
```

### File Importance Ranking

When exploring unfamiliar territory, prioritize these files:

```
★★★★★ (Core Logic)
├── proto/agent_service.proto              # API contract
├── backend/app/orchestration/orchestrator.py  # AI brain
├── backend/gateway/internal/handler/websocket.go  # Real-time hub
└── mobile/lib/core/services/chat_service.dart  # Client connection

★★★★☆ (Integration Points)
├── backend/gateway/internal/agent/client.go   # Go→Python bridge
├── backend/app/services/agent_grpc_service.py # Python gRPC impl
├── backend/app/orchestration/plan_review_service.py  # Plan review orchestration
├── backend/gateway/internal/service/*.go      # Business services
├── mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart  # WebSocket client
├── mobile/lib/features/chat/presentation/providers/*.dart   # State providers
└── mobile/lib/features/chat/presentation/widgets/plan_review_card.dart  # Plan review UI

★★★☆☆ (Supporting Infrastructure)
├── backend/gateway/internal/db/schema.sql     # DB structure
├── backend/app/orchestration/dynamic_tool_registry.py  # Tool system
├── docker-compose.yml                         # Service definitions
└── mobile/lib/core/design/design_system.dart  # UI tokens
```

---

## 🔧 Command Reference (Optimized)

### Quick Reference Card

```bash
# === DAILY WORKFLOW ===
make dev-all              # Start everything (3 terminals)
make proto-gen            # After proto changes
make sync-db              # After DB changes

# === COMPONENT STARTUP ===
make gateway-dev          # Go Gateway with hot reload
make grpc-server          # Python gRPC server
flutter run               # Mobile app

# === DEBUGGING ===
docker compose logs -f gateway      # Go logs
docker compose logs -f grpc-server  # Python logs
grpcurl -plaintext localhost:50051 list  # List gRPC services

# === TESTING ===
cd backend && pytest                    # Python tests
cd backend/gateway && go test ./...     # Go tests
cd mobile && flutter test               # Flutter tests

# === UTILITIES ===
cd mobile && ./fix_final_const.sh       # Fix Flutter const errors
alembic revision -m "desc"              # New migration
alembic upgrade head                    # Apply migrations
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

## 🏗 Architectural Invariants

These rules define the system's structural integrity. Never violate them.

### Layer Responsibility Matrix

| Layer | MUST Do | MUST NOT Do |
|-------|---------|-------------|
| **Flutter** | UI rendering, local state, user input | Business logic, direct API calls to Python |
| **Go Gateway** | Auth, WebSocket, caching, routing | AI reasoning, LLM calls, vector search |
| **Python Engine** | AI orchestration, RAG, tool execution | User auth, session management |
| **PostgreSQL** | Persistent storage, vector similarity | Caching (use Redis) |
| **Redis** | Session cache, rate limiting, pub/sub | Long-term storage |

### Interface Contracts

```
Flutter ←→ Go Gateway
  Protocol: WebSocket (ws://localhost:8080/ws/chat)
  Format: JSON messages with type field
  Auth: JWT in connection header

Go Gateway ←→ Python Engine
  Protocol: gRPC (localhost:50051)
  Contract: proto/agent_service.proto
  Streaming: Server-side streaming for chat

Python Engine ←→ Database
  ORM: SQLAlchemy (async)
  Vectors: pgvector with L2/Cosine distance
  Migrations: Alembic
```

---

## 🔄 Common Refactoring Patterns

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
1. Define in proto: proto/agent_service.proto
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

### Pattern 4: Cross-Language Feature

```
Example: Add "learning streak" feature

1. Database Layer:
   - Alembic migration for streak table
   - SQLC queries if Go needs direct access

2. Python Layer:
   - Service in backend/app/services/streak_service.py
   - Integrate with orchestrator if AI-aware

3. Proto Layer:
   - Define GetStreak RPC in proto
   - make proto-gen

4. Go Layer:
   - Client wrapper in agent/client.go
   - Handler in handler/ directory
   - WebSocket message type if real-time

5. Flutter Layer:
   - Provider in presentation/providers/
   - UI widget in presentation/widgets/
```

### Pattern 5: Backend-Driven Widget Events (Plan Review Style)

```
Example: Plan review results sent as WebSocket events

1. Python Backend (orchestrator.py):
   - Generate review result using plan_review_service.py
   - Send review data in metadata field of delta response:
     await stream_callback(ChatResponse(
         content=ChatResponse_Delta(
             delta="Some text...",
             metadata={
                 "requires_review": True,
                 "review_data": review_result.to_dict()
             }
         )
     ))

2. Go Gateway (websocket.go):
   - Forwards response unchanged to Flutter client
   - No special handling needed

3. Flutter WebSocket Service (websocket_chat_service_v2.dart):
   - Parse delta message
   - Check if metadata['requires_review'] == true
   - Emit PlanReviewWidgetEvent(reviewData: metadata)
   - Otherwise emit TextEvent with metadata

4. Flutter Event Model (chat_stream_events.dart):
   - Add metadata field to ChatStreamEvent base class
   - Create PlanReviewWidgetEvent with reviewData field

5. Flutter UI (plan_review_card.dart):
   - Listen for PlanReviewWidgetEvent in chat provider
   - Display review card with animations
   - Handle user actions (approve, reject, modify)

6. User Feedback Loop:
   - User submits decision via SubmitPlanReview gRPC
   - Backend processes and updates plan accordingly
```

---

## 🐛 Debugging Strategies

### Symptom → Diagnosis Table

| Symptom | Likely Cause | Diagnostic Command |
|---------|--------------|-------------------|
| WebSocket won't connect | Gateway not running | `curl http://localhost:8080/health` |
| gRPC timeout | Python server down | `grpcurl -plaintext localhost:50051 list` |
| "Field not found" error | Proto out of sync | `make proto-gen` then restart |
| DB query fails | Migration not applied | `alembic current` vs `alembic heads` |
| Flutter type error | Outdated generated code | `flutter pub get && flutter clean` |
| Redis connection refused | Docker not running | `docker compose ps` |

### Log Correlation Strategy

```bash
# Trace a request across layers
# 1. Get request ID from Flutter logs
# 2. Search Go Gateway logs
docker compose logs gateway 2>&1 | grep "request_id"

# 3. Search Python logs
docker compose logs grpc-server 2>&1 | grep "request_id"

# 4. Check database if needed
docker compose exec postgres psql -U sparkle -c "SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT 5;"
```

---

## 📊 Performance Considerations

### Hot Paths (Optimize First)
1. **WebSocket message parsing** — Every chat message goes through here
2. **Orchestrator state transitions** — FSM bottleneck
3. **Vector similarity search** — pgvector query performance
4. **LLM token streaming** — Real-time responsiveness

### Caching Layers
```
Request → Redis (chat history, rate limits)
        → Go semantic cache (RAG results)
        → Python LRU (embeddings, tool schemas)
        → PostgreSQL (persistent)
```

### Connection Pools
- Go → PostgreSQL: sqlc with pgxpool (default 10 connections)
- Go → Redis: go-redis with pooling
- Python → PostgreSQL: asyncpg pool
- Go → Python gRPC: Connection reuse

---

## 🧪 Testing Strategy

### Test Pyramid for This Project

```
                    ╱╲
                   ╱  ╲
                  ╱ E2E ╲        ← WebSocket integration tests
                 ╱────────╲
                ╱Integration╲    ← gRPC service tests
               ╱──────────────╲
              ╱   Unit Tests    ╲ ← Pure function tests
             ╱────────────────────╲
```

### Critical Test Coverage Areas

```python
# Python: Must test
- Orchestrator state transitions (FSM logic)
- Tool execution edge cases
- LLM response parsing
- Vector search accuracy

# Go: Must test
- WebSocket message routing
- Auth middleware
- gRPC client error handling
- Cache invalidation

# Flutter: Must test
- Provider state changes
- WebSocket reconnection
- Offline behavior
```

---

## 📚 Documentation Locations

| Topic | Location |
|-------|----------|
| Full Technical Guide | `docs/深度技术讲解教案_完整版.md` |
| Architecture Overview | `docs/00_项目概览/02_技术架构.md` |
| API Reference | `docs/02_技术设计文档/03_API参考.md` |
| Knowledge Graph Design | `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md` |
| Proto Definitions | `proto/agent_service.proto` (canonical) |

---

## 🎯 Opus 4.5 Specific Optimizations

### Leverage Extended Context
This codebase benefits from loading multiple related files simultaneously. When analyzing a feature:

```
Load order for maximum context:
1. Proto definition (API contract)
2. Python implementation (logic)
3. Go handler (integration)
4. Flutter provider (client state)
```

### Multi-Step Reasoning
For complex refactoring, use chain-of-thought:

```
Step 1: Map all touchpoints (grep for function/type name)
Step 2: Identify dependency direction (who imports whom)
Step 3: Plan change order (leaves → roots)
Step 4: Execute with verification at each step
```

### Parallel Verification
After significant changes, verify all affected layers:

```bash
# Run in parallel if possible
cd backend && pytest &
cd backend/gateway && go test ./... &
cd mobile && flutter test &
wait
```

---

## 🔒 Security Checklist

Before any PR involving auth, data, or external calls:

```
□ Secrets only in .env files (never in code)
□ User input validated at Go Gateway layer
□ SQL queries use parameterized statements
□ WebSocket messages sanitized
□ Rate limiting applied for expensive operations
□ Error messages don't leak internal details
```

---

## 📋 Pre-Commit Checklist

Before considering any task complete:

```
□ Code compiles/lints without errors
□ Generated files regenerated if sources changed
□ Tests pass (at minimum, affected area)
□ No hardcoded secrets or debug code
□ Comments updated if behavior changed
□ Proto backward compatible (if API change)
```

---

**Document Version**: 2.0.0 (Opus 4.5 Optimized)
**Last Updated**: 2025-12-28
**Project Version**: Sparkle MVP v0.3.0