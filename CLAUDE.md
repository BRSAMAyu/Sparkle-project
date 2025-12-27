# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 Model Guidelines

> **CRITICAL INSTRUCTION**: Identify the task complexity and follow the specific requirements below to ensure reliability on all supported backends (DeepSeek/MiMo/Native).

### ⚡ General Principles
- **Conciseness**: Be extremely brief for simple tasks (ls, cat, environment checks). Do NOT explain your actions unless requested.
- **Tool Use**: **Strictly** use XML tool tags. Do not output code in Markdown blocks if you intend to write it to a file.
- **Output**: No conversational filler like "Here is the code". Direct terminal commands or code edits only.
- **Thinking**: If running on a reasoning model (like DeepSeek-R1), analyze potential side effects before editing complex logic.

---

## Project Overview

**Sparkle (星火)** - AI Learning Assistant for university students. A hybrid architecture:

- **Go Gateway**: High-performance WebSocket gateway (Gin + Gorilla WebSocket).
- **Python Agent Engine**: AI reasoning, tool calls, vector search (gRPC).
- **Flutter Mobile**: Cross-platform mobile app (Riverpod).
- **Database**: PostgreSQL 16 + pgvector for vector search.

## Common Development Commands

### Make Commands (Recommended)
```bash
make dev-all           # Start full environment (3 terminals)
make dev-up            # Start Docker (PostgreSQL, Redis)
make grpc-server       # Start Python gRPC server (port 50051)
make gateway-run       # Start Go Gateway (port 8080)
make gateway-dev       # Start Go Gateway with live reload
make proto-gen         # Generate gRPC code from protobuf
make sync-db           # Sync DB schema → Go SQLC code
make integration-test  # Run WebSocket integration test
make grpc-test        # Test gRPC server connectivity
```

### Individual Component Commands

```bash
# Database
docker compose up -d    # Start all services (PostgreSQL, Redis, monitoring)
docker compose down     # Stop all services

# Python Agent Engine
cd backend
pip install -r requirements.txt  # Install Python dependencies
alembic upgrade head            # Run database migrations
python grpc_server.py           # Start gRPC server directly

# Go Gateway
cd backend/gateway
go mod tidy                     # Clean up Go dependencies
go build -o bin/gateway ./cmd/server  # Build gateway binary
go run cmd/server/main.go       # Run with live reload

# Flutter Mobile
cd mobile
flutter pub get                 # Get Dart dependencies
flutter run                     # Run on connected device/emulator
flutter analyze                # Static analysis
flutter build apk --release    # Build Android APK
```

### API Switcher (ccsw)

```bash
ccsw d                 # Switch to DeepSeek Official API
ccsw m                 # Switch to MiMo API (Flash)
ccsw n                 # Switch back to Native Claude
```

## High-Level Architecture

### System Flow

`Mobile (Flutter)` → `WebSocket (8080)` → `Go Gateway (Gin)` → `gRPC (50051)` → `Python Agent Engine` → `PostgreSQL/Redis`

### Cross-Boundary Debugging

- **Protocol Definition**: `proto/agent_service.proto` (Source of truth).
- **Boundary**: Change `.proto` → `make proto-gen` → Update Python `grpc_service.py` → Update Go `internal/agent/client.go`.
- **Database Schema**: Change SQL → `make sync-db` → Updates Go SQLC generated code.

## Key Components

### 1. Go Gateway (`backend/gateway/`)

- **WebSocket**: Real-time bidirectional communication (ws://localhost:8080/ws/chat).
- **Services**: Quota management, chat history, semantic cache.
- **Structure**: `cmd/server/` (entry), `internal/handler/` (HTTP/WS handlers), `internal/agent/` (gRPC client).

### 2. Python Agent Engine (`backend/app/`)

- **Orchestrator**: Core FSM processing (`orchestrator.py`).
- **Services**: Galaxy (Knowledge Graph), Decay (Ebbinghaus), Push (Notifications).
- **gRPC**: `grpc_server.py` (server), `grpc_service.py` (service implementation).

### 3. Flutter Mobile (`mobile/`)

- **State Management**: Riverpod with code generation.
- **Networking**: Dio for HTTP, WebSocket for real-time.
- **Key Features**: Knowledge Galaxy (GLSL shaders), task cards, focus timer.

### 4. Database & Infrastructure

- **PostgreSQL**: Core relational data + pgvector for embeddings.
- **Redis**: Caching and session management.
- **Monitoring**: Prometheus, Grafana, Loki, Tempo (in docker-compose).

## Database Schema

```sql
-- Core Knowledge System
knowledge_nodes          -- Use `<->` operator for cosine distance in vector search.
user_node_status         -- User mastery progress.
node_relations           -- Graph connections.

-- Key tables for AI features
tasks                    -- Task card system (6 types)
chat_messages            -- AI conversation history
user_progress            -- Learning analytics
```

## Development Workflows

### Adding New gRPC Methods

1. Edit `proto/agent_service.proto`
2. Run `make proto-gen`
3. Implement in Python: `backend/app/grpc_service.py`
4. Update Go client: `backend/gateway/internal/agent/client.go`
5. Add WebSocket handler if needed

### Database Changes

1. Create Alembic migration: `cd backend && alembic revision -m "description"`
2. Apply migration: `alembic upgrade head`
3. Sync to Go: `make sync-db`
4. Update Go queries in `backend/gateway/internal/db/queries/`

### Mobile Feature Development

1. Add dependencies to `mobile/pubspec.yaml`
2. Run `flutter pub get`
3. Create Riverpod providers in `mobile/lib/providers/`
4. Implement UI in `mobile/lib/screens/`

## Documentation

- `README.md`: Project overview and quick start.
- `Claude_Code_API_Alignment_Guide.md`: API switcher documentation.
- `docs/`: Complete documentation system (8 categories).
- `docs/深度技术讲解教案_完整版.md`: 200+知识点完整技术教程.
