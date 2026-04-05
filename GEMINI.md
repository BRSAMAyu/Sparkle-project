# GEMINI.md — Sparkle (星火) AI Growth Companion

This file provides the foundational context and instructional mandates for AI agents interacting with the Sparkle (星火) project. Sparkle is a sophisticated, dual-core AI growth operating system designed to assist users in personal development and goal achievement.

## Project Overview

Sparkle is an AI-driven digital companion that combines goal execution with cognitive understanding. It utilizes a three-layer "sandwich" architecture:

-   **Frontend:** Flutter Mobile App (3.24+, Riverpod, Multi-sensory UX).
-   **Middleware:** Go Gateway (1.22+, Auth, WebSocket, gRPC Bridge, Rate Limiting).
-   **Backend:** Python AI Engine (3.11+, LangGraph FSM, GraphRAG, Multi-Agent Orchestration).
-   **Infrastructure:** PostgreSQL 16 (pgvector + Apache AGE), Redis 7+ (Streams/Cache), MinIO (S3 storage).

## Core Architecture: Dual-Core Growth OS

1.  **Execution Core:** Focuses on "getting things done" — goal clarification, staged planning (DAG), task execution, and dynamic adjustment.
2.  **Cognitive Core:** Focuses on "understanding the user" — 4D user profiling (Knowledge, Cognitive, Motivation, Social), long/short-term memory, and emotional state.

These cores collaborate via a `DualCoreRouter` to provide personalized, context-aware growth support.

## Critical Development Mandates

### Source of Truth Hierarchy
Always follow the generation flow. **Never edit generated files directly.**
1.  **API Contracts:** `proto/*.proto` (Source) → `make proto-gen` → Generated Code in Go, Python, and Dart.
2.  **Database (Go):** `backend/gateway/internal/db/schema.sql` (Source) → `make sync-db` → Generated `models.go`.
3.  **Database (Python):** Alembic Migrations (Source) → `alembic upgrade head` → Python Models (must match).

### Architectural Hard Rules
-   **Go Gateway:** Handles Auth, WebSockets, and Caching. **NO AI reasoning or business logic.**
-   **Python Engine:** Handles RAG, Orchestration, and LLM calls. **NO User Auth.**
-   **Database Access:** Go handlers must use the **Service Layer**, never direct DB calls.

## Key Directories & Files

### Infrastructure & Orchestration
-   `proto/`: Canonical Protobuf definitions (API contracts).
-   `backend/app/orchestration/orchestrator.py`: The AI brain (LangGraph FSM).
-   `backend/gateway/internal/handler/websocket_proxy.go`: Real-time WebSocket hub.
-   `backend/app/orchestration/dual_core_router.py`: Logic for Execution vs. Cognitive core routing.

### Backend (Python Engine)
-   `backend/app/services/`: 26+ core services (Memory, Cognitive, Galaxy, Achievement, etc.).
-   `backend/app/adapters/openclaw/`: Integration with external digital executors.
-   `backend/app/tools/`: Custom AI tools for the orchestrator.

### Gateway (Go)
-   `backend/gateway/cmd/server/main.go`: Gateway entry point.
-   `backend/gateway/internal/middleware/`: 16 middleware files (Auth, RateLimit, ChaosGuard, etc.).
-   `backend/gateway/internal/agent/client.go`: Go-to-Python gRPC client.

### Frontend (Flutter)
-   `mobile/lib/features/`: 24 feature modules (Chat, Galaxy, Task, Achievement, etc.).
-   `mobile/lib/core/design/`: Design System V2 (Design Tokens & Motion Primitives).
-   `mobile/lib/core/services/`: Global services (BGM, Haptic Feedback, Audio Policy).

## Building and Running

| Command | Description |
| :--- | :--- |
| `make dev-all` | Start infrastructure (PostgreSQL, Redis, MinIO) |
| `make proto-gen` | Generate code from Protobuf definitions |
| `make sync-db` | Apply DB migrations and regenerate SQLC (Go) |
| `make grpc-server` | Start the Python AI gRPC server |
| `make gateway-dev` | Start the Go Gateway with hot-reload |
| `make mobile-run` | Launch the Flutter mobile application |
| `make smoke` | Run health checks across all services |
| `make local-final-signoff` | Execute full test suite and acceptance scripts |

## Development Conventions

1.  **Task Classification:** Use `CLAUDE.md` to classify tasks from L1 (Atomic) to L4 (Architectural).
2.  **Planning (L3+):** Provide a clear Impact Scope and Dependency Chain before implementation.
3.  **Testing:** The project has 470+ tests and 21+ acceptance scripts. **Always verify changes with `pytest` (Python), `go test` (Go), or `flutter test` (Flutter).**
4.  **Linting:** Adhere to Ruff/MyPy (Python), Golangci-lint (Go), and strict Flutter analysis rules.

## Documentation Index
-   **General Reference:** `CLAUDE.md` (Crucial for AI developers).
-   **Technical Design:** `docs/00_项目概览/02_技术架构.md`.
-   **Knowledge Graph:** `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md`.
-   **Testing:** `backend/scripts/` (Acceptance scripts).
