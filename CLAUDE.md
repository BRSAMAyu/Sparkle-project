# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🤖 Model Guidelines (Intelligence Isolation Compatible)

> **CRITICAL INSTRUCTION**: Identify your capability level based on the current task and follow the specific mode below.

### ⚡ Mode: Fast/Flash (Haiku Level)
*Applicable for `ls`, `cat`, simple fixes, or exploring file structure.*
- **Conciseness**: Be extremely brief. Do NOT explain your actions.
- **Output**: Direct terminal commands or code edits only. No conversational filler.
- **Safety**: Do not attempt complex refactoring. If a task is complex, ask the user to switch to High-Performance mode.

### 🧠 Mode: High-Performance (Sonnet/Opus Level)
*Applicable for architecture, refactoring, or complex logic.*
- **Thinking**: If using a reasoning model (e.g., DeepSeek-R1), use reasoning to analyze side effects before editing.
- **Tool Use**: **Strictly** use XML tool tags. Do not output code in Markdown blocks if intended for a file.
- **Intelligence Isolation**: To trigger the Opus tier (R1), the user may use keywords like "Switch to Opus" or "Reason about this".
- **Thinking Toggle**: Type `/config` to toggle **Thinking mode** to **True** for deep reasoning, and back to **False** for routine tasks.

---

## Project Overview

**Sparkle (星火)** - AI Learning Assistant for university students with a "AI Time Tutor" concept. The project uses a hybrid architecture:

- **Go Gateway**: High-performance WebSocket gateway (Gin + Gorilla WebSocket)
- **Python Agent Engine**: AI reasoning, tool calls, vector search (gRPC)
- **Flutter Mobile**: Cross-platform mobile app (Riverpod)
- **Database**: PostgreSQL 16 + pgvector for vector search

## Common Development Commands

### Make Commands (Recommended)
```bash
make dev-all           # Start full environment (3 terminals)
make dev-up            # Start Docker (PostgreSQL, Redis)
make grpc-server       # Start Python gRPC server (port 50051)
make gateway-run       # Start Go Gateway (port 8080)
make proto-gen         # Generate gRPC code from protobuf
make sync-db           # Sync DB schema → Go SQLC code
```

### Intelligence Isolation (ccsw)
```bash
ccsw iso               # Activate Intelligence Isolation (Flash/V3.2/R1)
ccsw d                 # Switch to DeepSeek Chat
ccsw m                 # Switch to MiMo Flash
ccsw n                 # Switch back to Native Claude
```

## High-Level Architecture

### System Flow
`Mobile (Flutter)` → `WebSocket (8080)` → `Go Gateway (Gin)` → `gRPC (50051)` → `Python Agent Engine` → `PostgreSQL/Redis`

### Cross-Boundary Debugging
- **Protocol Definition**: `proto/agent_service.proto` (Source of truth).
- **If changing API**:
  1. Modify `.proto` file.
  2. Run `make proto-gen`.
  3. Update Python `app/services/agent_grpc_service.py`.
  4. Update Go `internal/agent/client.go`.

## Key Components

### 1. Go Gateway (`backend/gateway/`)
- **WebSocket**: Real-time bidirectional communication.
- **Services**: Quota, chat history, semantic cache, chaos injection.

### 2. Python Agent Engine (`backend/app/`)
- **Orchestrator**: Core FSM processing (`orchestrator.py`).
- **Services**: Galaxy (Knowledge Graph), Decay (Ebbinghaus), Push (Smart Notifications), Task (6 types).
- **Tools**: Dynamic tool registry in `app/tools/`.

### 3. Flutter Mobile (`mobile/`)
- **Galaxy Screen**: Interactive knowledge graph with GLSL shaders.
- **State**: Riverpod management.

## Database Schema (Key Tables)

```sql
-- Core Knowledge System
knowledge_nodes          -- Nodes with embeddings. Use `<->` operator for cosine distance.
user_node_status         -- User mastery & progress.
node_relations           -- Graph connections.
```

## Documentation
- `Claude_Code_API_Alignment_Guide.md`: API switcher documentation.
- `docs/02_技术设计文档/`: Comprehensive system architecture.