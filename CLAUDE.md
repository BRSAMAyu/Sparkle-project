# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚫 CRITICAL ANTI-PATTERNS (DO NOT DO)
1.  **NO Markdown Wrapping**: NEVER wrap XML tool tags (like `<edit_file>`) inside markdown code blocks. **Output the raw XML tag directly.**
2.  **NO Chatty Filler**: Do not say "I will now edit the file..." or "Here is the corrected code". **Just execute the tool.**
3.  **NO Blind Edits**: Do not assume a file path exists. If you are 80% sure, verify with `ls -R` or `grep` first.

### ⚡ Operational Protocol
- **Simple Tasks** (Typos, Config, One-file fix):
  - Action: Execute tool immediately. Zero explanation.
- **Complex Tasks** (Cross-language, Refactoring, Architecture):
  - Action: Output a **"🔍 Plan"** bullet list (max 3 items) before executing tools.
  - Example: "- Verify proto definition -> - Regen proto -> - Update Python implementation."

---

## Project Overview

**Sparkle (星火)** - AI Learning Assistant. Hybrid Architecture:
- **Go Gateway**: WebSocket/Gin (`backend/gateway`). High-performance gateway for real-time communication.
- **Python Engine**: Logic/RAG/gRPC (`backend/app`). AI reasoning, tool calls, and vector search.
- **Flutter**: Mobile UI (`mobile`). Cross-platform app using Riverpod for state management.
- **DB**: Postgres 16 + pgvector. Core relational data and vector embeddings.

## 🛠 Common Development Commands

### 🔥 Quick Actions (High Frequency)

**Full Dev Environment:**
```bash
make dev-all  # 3-terminal start: Docker, Python gRPC, Go Gateway
```

**Generators (RUN AFTER PROTO/DB CHANGES):**
```bash
make proto-gen   # *.proto -> Go/Python code
make sync-db     # SQL Schema -> Go SQLC code
```

**Specific Components:**
```bash
make gateway-dev   # Go Gateway Live Reload
make grpc-server   # Python Agent
flutter run        # Mobile App
```

**Individual Component Commands:**
- **Backend (Go)**: `cd backend/gateway && go run cmd/server/main.go`
- **Backend (Python)**: `cd backend && python grpc_server.py`
- **Database**: `docker compose up -d` (PostgreSQL, Redis, Monitoring)
- **Migrations**: `cd backend && alembic upgrade head`
- **Tests**: `cd backend && pytest` (Python), `cd backend/gateway && go test ./...` (Go)

## 🏗 Architecture & Boundary Rules

### 🚨 Cross-Boundary Protocol (Strict Adherence)

**Source of Truth**: `proto/agent_service.proto`
- *Rule*: Never modify Go/Python struct definitions manually. Modify `.proto` and run `make proto-gen`.

**Database Truth**: `backend/gateway/internal/db/schema.sql` (Go side) and Alembic migrations (Python side).
- *Rule*: Never modify `models.go` manually. Modify SQL/Queries and run `make sync-db`.

### Data Flow
```
Mobile (Riverpod)
  → WebSocket (ws://localhost:8080/ws/chat)
  → Go Gateway (Gin, port 8080)
  → gRPC (localhost:50051)
  → Python Orchestrator
  → PGVector/Redis
```

### Component Responsibilities

**Go Gateway (`backend/gateway`):**
- WebSocket connection management & real-time streaming
- Authentication & authorization
- Protocol translation (WS ↔ gRPC)
- Chat history caching (Redis)
- Semantic cache for RAG queries
- CQRS event publishing
- Reverse proxy for Python REST APIs

**Python Engine (`backend/app`):**
- AI orchestration (FSM-based state machine)
- LLM integration (Qwen/DeepSeek/GPT)
- RAG & Vector search (pgvector)
- Tool execution & dynamic tool registry
- Knowledge graph management
- Token usage tracking & cost calculation

**Flutter Mobile (`mobile`):**
- Riverpod state management
- WebSocket client for real-time AI updates
- UI components with design system tokens
- Local storage (Hive, SharedPreferences)
- GLSL shaders for visualizations (Galaxy view)

## 🔑 Critical Component Paths

### Go Gateway Internal Structure
```
backend/gateway/
├── cmd/server/main.go          # Entry point
├── internal/
│   ├── agent/client.go         # gRPC client wrapper
│   ├── handler/
│   │   ├── websocket.go        # WebSocket handler (check for connection issues)
│   │   └── chat_orchestrator.go # Chat flow orchestration
│   ├── service/
│   │   ├── quota_service.go    # Rate limiting
│   │   ├── chat_history.go     # Redis chat cache
│   │   └── semantic_cache.go   # RAG result caching
│   ├── db/
│   │   ├── schema.sql          # Source of truth for DB schema
│   │   └── queries/            # SQLC generated queries
│   └── cqrs/                   # Event sourcing infrastructure
└── gen/agent/v1/               # Protobuf generated code
```

### Python Engine Structure
```
backend/app/
├── grpc_server.py              # gRPC server entry
├── services/
│   ├── agent_grpc_service.py   # gRPC service implementation
│   ├── llm_service.py          # LLM abstraction layer
│   ├── galaxy_service.py       # Knowledge graph / RAG
│   └── knowledge_service.py    # Vector search
├── orchestration/
│   ├── orchestrator.py         # Main FSM loop
│   ├── executor.py             # Tool execution
│   └── dynamic_tool_registry.py # Tool registration
├── agents/                     # Multi-agent workflows
├── gen/agent/v1/               # Protobuf generated code
└── models/                     # Pydantic models
```

### Flutter Mobile Structure
```
mobile/lib/
├── main.dart                   # App entry
├── core/
│   ├── services/
│   │   ├── chat_service.dart   # WebSocket client
│   │   └── galaxy_service.dart # Galaxy layout engine
│   ├── design/
│   │   ├── design_system.dart  # Design tokens
│   │   └── tokens_v2/          # Theme management
│   └── network/
│       └── api_interceptor.dart # HTTP interceptors
├── presentation/
│   ├── providers/              # Riverpod providers
│   ├── screens/                # UI screens
│   └── widgets/                # Reusable widgets
└── domain/                     # Business logic
```

## 🗄 Database Schema Rules

### Key Tables
- **`knowledge_nodes`**: Vector Search. Use `<->` L2 Distance or `<=>` Cosine.
- **`node_relations`**: Graph edges for knowledge graph.
- **`user_node_status`**: Mastery levels & learning progress.
- **`chat_messages`**: Conversation history (context window).
- **`tasks`**: Task card system (6 types: learn, train, correct, reflect, social, plan).
- **`users`**: User profiles & preferences.

### Schema Changes Workflow
1. Modify Alembic migration: `cd backend && alembic revision -m "description"`
2. Apply migration: `alembic upgrade head`
3. If Go needs the data: Update `backend/gateway/internal/db/queries/` → `make sync-db`

## 🔄 Standard Workflows

### Adding a New AI Feature
1. Define interface in `proto/agent_service.proto`
2. Regenerate: `make proto-gen`
3. Implement in Python: `app/services/agent_grpc_service.py`
4. Call from Go: `backend/gateway/internal/agent/client.go`
5. Expose via WebSocket: `backend/gateway/internal/handler/websocket.go`

### Adding a New Tool
1. Create tool in `backend/app/tools/`
2. Register in `backend/app/orchestration/dynamic_tool_registry.py`
3. Tool is automatically available to LLM via function calling

### Modifying UI Components
1. Update design tokens: `mobile/lib/core/design/design_system.dart`
2. Update theme: `mobile/lib/core/design/tokens_v2/theme_manager.dart`
3. Modify widget: `mobile/lib/presentation/widgets/`
4. Run const fixer if needed: `./mobile/fix_final_const.sh`

### Debugging
- **Logs**: `docker compose logs -f gateway` or `docker compose logs -f grpc-server`
- **WebSocket**: Check `backend/gateway/internal/handler/websocket.go`
- **gRPC**: Use `grpcurl` or `make grpc-test`
- **Tracing**: Prometheus/Tempo at ports defined in `docker-compose.yml`

## 🧪 Testing Commands

**Python Tests:**
```bash
cd backend && pytest                    # All tests
cd backend && pytest tests/test_grpc.py # Specific test
```

**Go Tests:**
```bash
cd backend/gateway && go test ./...     # All tests
cd backend/gateway && go test ./internal/service/...  # Service tests
```

**Flutter Tests:**
```bash
cd mobile && flutter test               # All tests
cd mobile && flutter test test/widget/  # Widget tests
```

**Integration Tests:**
```bash
make integration-test  # WebSocket client test
make grpc-test         # gRPC server test
```

## 🎯 Common Tasks & Quick Fixes

### Fix Flutter Const Errors
```bash
cd mobile && ./fix_final_const.sh
```

### Regenerate After Proto Change
```bash
make proto-gen
# Then update any Go/Python code that uses the new interface
```

### Sync Database After Schema Change
```bash
make sync-db
# This applies migrations and regenerates Go SQLC code
```

### Start Everything for Development
```bash
# Terminal 1
make dev-up  # Start Docker (DB, Redis)

# Terminal 2
make grpc-server  # Python gRPC

# Terminal 3
make gateway-dev  # Go Gateway

# Terminal 4 (optional, for mobile)
cd mobile && flutter run
```

## 🔧 Configuration Files

- **Backend**: `backend/.env` (copy from `.env.example`)
- **Go Gateway**: `backend/gateway/.env`
- **Flutter**: `mobile/pubspec.yaml` (dependencies)
- **Docker**: `docker-compose.yml` (services)
- **Protobuf**: `buf.yaml`, `buf.gen.yaml`

## 📚 Documentation Reference

- **Full Docs**: `docs/深度技术讲解教案_完整版.md` - Comprehensive technical guide
- **Architecture**: `docs/00_项目概览/02_技术架构.md`
- **API Reference**: `docs/02_技术设计文档/03_API参考.md`
- **Knowledge Graph**: `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md`

---

**Last Updated**: 2025-12-28
**Version**: MVP v0.3.0 (Go + Python Hybrid Architecture)
