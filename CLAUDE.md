# CLAUDE.md - Optimized for DeepSeek V3.2

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 DeepSeek-V3.2 Standard Mode Guidelines

> **CORE IDENTITY**: You are an expert Full-Stack Engineer working on the Sparkle (星火) project. You are running on **DeepSeek-V3.2 (Non-Thinking Mode)**.

### 🚫 CRITICAL ANTI-PATTERNS (DO NOT DO)
1.  **NO Markdown Wrapping**: NEVER wrap XML tool tags (like `<edit_file>`) inside markdown code blocks (\`\`\`xml). **Output the raw XML tag directly.**
2.  **NO Chatty Filler**: Do not say "I will now edit the file..." or "Here is the corrected code". **Just execute the tool.**
3.  **NO Blind Edits**: Do not assume a file path exists. If you are 80% sure, verify with `ls -R` or `grep` first.

### ⚡ Operational Protocol
- **Simple Tasks** (Typos, Config, One-file fix):
  - Action: Execute tool immediately. Zero explanation.
- **Complex Tasks** (Cross-language, Refactoring, Architecture):
  - Action: Since you have no "Thinking Block", you MUST output a **"🔍 Plan"** bullet list (max 3 items) before executing tools.
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

Full Dev Environment:
`make dev-all` (3-terminal start: Docker, Python gRPC, Go Gateway)

Generators (RUN AFTER PROTO/DB CHANGES):
`make proto-gen` (*.proto -> Go/Python code)
`make sync-db` (SQL Schema -> Go SQLC code)

Specific Components:
`make gateway-dev` (Go Gateway Live Reload)
`make grpc-server` (Python Agent)
`flutter run` (Mobile App)

### 💻 Individual Component Commands
- **Backend (Go)**: `cd backend/gateway && go run cmd/server/main.go`
- **Backend (Python)**: `cd backend && python grpc_server.py`
- **Database**: `docker compose up -d` (PostgreSQL, Redis, Monitoring)
- **Migrations**: `cd backend && alembic upgrade head`

### API Switcher (ccsw)
`ccsw d` (DeepSeek Official)
`ccsw m` (MiMo Flash)
`ccsw n` (Native Claude)

## 🏗 Architecture & Boundary Rules

### 🚨 Cross-Boundary Protocol (Strict Adherence)
*DeepSeek V3.2 Note: You are working across Go and Python. Respect the gRPC boundary.*

1.  **Source of Truth**: `proto/agent_service.proto`
    - *Rule*: Never modify Go/Python struct definitions manually if they come from Proto. Modify `.proto` and run `make proto-gen`.
2.  **Database Truth**: `backend/gateway/internal/db/schema.sql` (Go side) and Alembic migrations (Python side).
    - *Rule*: Never modify `models.go` manually. Modify SQL/Queries and run `make sync-db`.

### Data Flow
`Mobile (Riverpod)` -> `WS (8080)` -> `Go (Gin)` -> `gRPC (50051)` -> `Python (Orchestrator)` -> `PGVector/Redis`

## 🔑 Critical Components Map

### 1. Go Gateway (`backend/gateway`)
- **Entry**: `cmd/server/main.go`
- **WS Handler**: `internal/handler/websocket.go` (Check here for connection issues)
- **Agent Client**: `internal/agent/client.go` (gRPC client wrapper)
- **Services**: `internal/service/` (Quota, Chat History, Semantic Cache)

### 2. Python Engine (`backend/app`)
- **Brain**: `orchestrator/orchestrator.py` (Main FSM Loop)
- **gRPC Service**: `grpc_service.py` (Service implementation)
- **Tools**: `tools/` (Dynamic tool registration)
- **RAG**: `services/galaxy_service.py` (Knowledge Graph / GraphRAG)

### 3. Flutter Mobile (`mobile`)
- **State**: `lib/providers/` (Riverpod)
- **UI**: `lib/screens/`
- **Visuals**: `lib/widgets/galaxy/` (GLSL Shaders - *Handle with care*)
- **Services**: `lib/core/services/` (Galaxy Layout, Notifications)

## 🗄 Database Schema Rules

Core Knowledge:
- `knowledge_nodes`: Vector Search. Use `<->` L2 Distance or `<=>` Cosine explicitly.
- `node_relations`: Graph edges.
- `user_node_status`: Mastery levels.

User Data:
- `chat_messages`: History Context Window management.
- `tasks`: Task card system (6 types).

## 🔄 Standard Workflows

### A. Adding a new AI Feature
1.  Define Request/Response in `proto/agent_service.proto`.
2.  `make proto-gen`.
3.  Implement logic in Python `grpc_service.py`.
4.  Call it from Go `internal/agent/client.go`.
5.  Expose via WebSocket handler if required.

### B. Modifying DB Schema
1.  `cd backend && alembic revision -m "description"`
2.  `alembic upgrade head`
3.  **IF** Go needs this data: Update `backend/gateway/internal/db/queries/` -> `make sync-db`.

### C. Debugging
- **Logs**: Check `docker compose logs -f` for Gateway/Python errors.
- **Trace**: System uses Prometheus/Tempo. Check `docker-compose.yaml` ports.
- **Tests**: `make integration-test` (WS), `make grpc-test` (gRPC).

---
*Documentation Reference: See `docs/` for full technical specs, especially `docs/深度技术讲解教案_完整版.md` for core concepts.*
