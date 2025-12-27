# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sparkle (星火)** - AI Learning Assistant for university students with a "AI Time Tutor" concept. The project uses a hybrid architecture:

- **Go Gateway**: High-performance WebSocket gateway (Gin + Gorilla WebSocket)
- **Python Agent Engine**: AI推理、工具调用、向量检索 (gRPC)
- **Flutter Mobile**: Cross-platform mobile app (Riverpod state management)
- **Database**: PostgreSQL 16 + pgvector for vector search

## Common Development Commands

### Make Commands (Recommended)
```bash
# Start full development environment (3 terminals needed)
make dev-all

# Individual components:
make dev-up              # Start Docker (PostgreSQL, Redis)
make grpc-server         # Start Python gRPC server (port 50051)
make gateway-run         # Start Go Gateway (port 8080)
make gateway-dev         # Start Go Gateway with auto-rebuild

# Code generation
make proto-gen           # Generate gRPC code from protobuf
make sync-db             # Sync DB schema → Go SQLC code

# Testing
make integration-test    # Run WebSocket integration tests
make grpc-test           # Test gRPC server
```

### Manual Commands
```bash
# Backend - Python gRPC
cd backend
python grpc_server.py

# Backend - Go Gateway
cd backend/gateway
go run cmd/server/main.go
go build -o bin/gateway ./cmd/server  # Build binary

# Mobile - Flutter
cd mobile
flutter pub get
flutter run
flutter analyze
```

## High-Level Architecture

### System Flow
```
Mobile (Flutter)
    ↓ WebSocket (port 8080)
Go Gateway (Gin)
    ↓ gRPC (port 50051)
Python Agent Engine (FastAPI)
    ↓
PostgreSQL + pgvector
    ↓
Redis (caching, sessions, queues)
```

### Key Components

#### 1. Go Gateway (`backend/gateway/`)
- **WebSocket Handler**: Real-time bidirectional communication with mobile
- **Auth Middleware**: JWT validation, rate limiting
- **Reverse Proxy**: Forwards REST API requests to Python backend
- **Services**: Quota, chat history, semantic cache
- **Chaos Engineering**: Fault injection for testing

#### 2. Python Agent Engine (`backend/app/`)
- **Orchestration Layer**:
  - `ChatOrchestrator`: Core request processing with FSM states
  - `RequestValidator`: Input validation & security checks
  - `ContextPruner`: Conversation history pruning (keeps last 10 messages)
  - `TokenTracker`: Usage quota management
  - `ResponseComposer`: Unified response building
  - `ToolExecutor`: Dynamic tool execution

- **Services**:
  - `LLMService`: LLM integration (Qwen/DeepSeek/GPT)
  - `GalaxyService`: Knowledge graph operations
  - `ExpansionService`: LLM-driven knowledge expansion
  - `DecayService`: Ebbinghaus forgetting curve implementation
  - `PushService`: Smart notifications (sprint/memory/inactivity strategies)
  - `TaskService`: Task management (6 types: learning, training, error_fix, reflection, social, planning)

- **Tools System** (`app/tools/`):
  - Dynamic tool registry with auto-discovery
  - Tools for knowledge, tasks, and user operations

#### 3. Flutter Mobile (`mobile/`)
- **State Management**: Riverpod
- **Storage**: Hive + SharedPreferences
- **UI Features**:
  - Galaxy Screen: Interactive knowledge graph with GLSL shaders
  - Chat Screen: Real-time AI conversation
  - Task Management: 6 task types with execution modes
  - Sprint/Growth Plans: Time management

### Database Schema (Key Tables)

```sql
-- Core Knowledge System
knowledge_nodes          -- Knowledge points with embeddings
user_node_status         -- User-specific mastery & progress
node_relations           -- Connections between nodes
study_records            -- Learning history
node_expansion_queue     -- LLM expansion queue

-- User & Tasks
users                    -- User profiles
tasks                    -- 6 task types
plans                    -- Sprint/Growth plans
chat_messages            -- Conversation history

-- Smart Push System
push_preferences         -- User notification settings
push_histories           -- Push history for frequency control
notifications            -- User notifications
```

## Critical Code Locations

### Request Processing Flow
1. **Mobile** → WebSocket → **Go Gateway** (`handler/chat_orchestrator.go:HandleWebSocket`)
2. **Go** → gRPC → **Python** (`app/services/agent_grpc_service.py`)
3. **Python Orchestration** (`app/orchestration/orchestrator.py:process_stream`):
   - Validation (`validator.py`)
   - Context building (user + conversation history)
   - RAG retrieval
   - LLM call with tools
   - Response composition

### Key Files to Read
- **Backend Entry**: `backend/app/main.py` (FastAPI lifespan)
- **Go Entry**: `backend/gateway/cmd/server/main.go`
- **gRPC Server**: `backend/grpc_server.py`
- **Orchestration**: `backend/app/orchestration/orchestrator.py`
- **Mobile Entry**: `mobile/lib/main.dart`

## Development Notes

### Environment Setup
1. Copy `.env.example` to `.env` and configure:
   - Database URL
   - Redis URL
   - LLM API keys (Qwen/DeepSeek)
   - JWT secret

2. Install dependencies:
   ```bash
   # Python
   cd backend && pip install -r requirements.txt

   # Go
   cd backend/gateway && go mod tidy

   # Flutter
   cd mobile && flutter pub get
   ```

3. Run migrations:
   ```bash
   cd backend && alembic upgrade head
   ```

### Testing Strategy
- **Unit Tests**: `backend/tests/`
- **Integration Tests**: `test_websocket_client.py`, `test_grpc_client.py`
- **Demo Data**: `backend/setup_demo_data.py`

### Key Features Implementation

#### 1. Knowledge Galaxy (知识星图)
- **Backend**: `services/galaxy_service.py`, `services/expansion_service.py`
- **Frontend**: `mobile/lib/presentation/screens/galaxy_screen.dart`
- **Visual**: GLSL shaders for flame effect, particle systems for animations

#### 2. Smart Push System
- **Strategies**: `services/push_service.py` (Memory/Sprint/Inactivity)
- **Scheduler**: `services/scheduler_service.py` (15-min cycles)
- **Frequency Control**: Daily caps, cooldowns, user preferences

#### 3. Context Pruning
- **Implementation**: `app/orchestration/context_pruner.py`
- **Logic**: Keeps last 10 messages, summarizes older ones, 1-hour cache TTL

#### 4. Dynamic Tools
- **Registry**: `app/orchestration/dynamic_tool_registry.py`
- **Auto-discovery**: Scans `app/tools/` package
- **Execution**: `app/orchestration/executor.py`

### Common Issues & Solutions

**Issue**: gRPC connection fails
- Check if Python gRPC server is running on port 50051
- Verify `settings.GRPC_PORT` in `.env`

**Issue**: WebSocket disconnects
- Check Go Gateway logs for auth failures
- Verify Redis connection for session management

**Issue**: Database schema mismatch
- Run `make sync-db` to regenerate Go SQLC code
- Run `alembic upgrade head` for Python migrations

### Production Considerations
- **Security**: Rate limiting, input validation, SQL injection prevention
- **Monitoring**: OpenTelemetry tracing, Prometheus metrics
- **Performance**: Redis caching, connection pooling, async operations
- **Scalability**: Horizontal scaling with Redis for state management

## Documentation

- **README.md**: Project overview and quick start
- **docs/**: Comprehensive documentation (Chinese)
  - `02_技术设计文档/01_技术白皮书.md`: System architecture
  - `02_技术设计文档/02_知识星图系统设计_v3.0.md`: Galaxy feature design
  - `02_技术设计文档/07_后端知识星图设计.md`: Backend implementation

## Production-Grade Enhancements (2025-12-27)

### ContextPruner Production Fixes
All critical issues from code review have been resolved:

1. **Serialization**: ✅ JSON instead of pickle
2. **Concurrency Safety**: ✅ Message ID tracking to prevent duplicates
3. **Error Handling**: ✅ Graceful degradation for Redis/LLM failures
4. **Circuit Breaker**: ✅ Prevents queue buildup and OOM
5. **Monitoring**: ✅ Prometheus metrics integration
6. **Health Checks**: ✅ Comprehensive HTTP endpoints
7. **Structured Logging**: ✅ JSON format with context
8. **Configuration**: ✅ Production-grade settings management

### New Production Files
- `backend/app/orchestration/orchestrator_production.py`: Production orchestrator
- `backend/app/config_production.py`: Enhanced configuration system
- `backend/app/api/v1/health_production.py`: Complete health check endpoints
- `docs/06_安全与质量报告/03_生产部署指南.md`: Deployment guide
- `docs/06_安全与质量报告/04_生产级修复总结.md`: Fix summary

### Production Readiness Score: 9.5/10

## Recent Changes (Git Log)
- `27b84d3`: Added ContextPruner for conversation history management
- `4371fc1`: Migrated Apple login to Go gateway
- `254e73c`: Added user preferences and context models
- `e9c53bc`: Added distributed tracing and monitoring stack
