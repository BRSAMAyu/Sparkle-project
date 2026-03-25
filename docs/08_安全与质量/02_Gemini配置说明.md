# Sparkle (星火) - AI Learning Assistant

## Project Overview
Sparkle is an AI-powered learning assistant application designed for college students. It integrates an "AI Time Tutor" to guide users through a learning loop: Dialogue → Task Cards → Execution → Feedback → Sprint Plans.

**Target**: MVP completion by February 2, 2025.
**Team**: Student team (Python/AI background, learning Flutter).

## Recent Achievements (Step 5+ Integration)
- **Go Backend Refactor**: Implemented a Go Gateway (`backend/gateway`) to handle high-concurrency WebSocket connections and orchestrate AI tool execution.
- **Python Agent gRPC**: Decoupled AI reasoning logic into a dedicated Python gRPC server (`backend/grpc_server.py`) for better scalability.
- **WebSocket Chat**: Full duplex communication between Flutter and Go Gateway, supporting real-time AI status updates (THINKING, SEARCHING, etc.) and tool calls.
- **Session Recovery**: Implemented history loading and session selection in the Chat UI.
- **Real User Integration**: Deep integration with `authProvider` to use dynamic user IDs and nicknames in conversations.
- **UI Modernization**: Fixed deprecated Flutter APIs (`withOpacity` -> `withValues`) and added AI status indicators to message bubbles.

## Tech Stack

### Infrastructure
*   **Database**: PostgreSQL 16 (pgvector for embeddings)
*   **Cache/Queue**: Redis Stack (used for session storage, rate limiting, and semantic cache)
*   **Containerization**: Docker Compose for DB and Redis

### Backend (Python Agent)
*   **Framework**: FastAPI (Management APIs)
*   **gRPC**: `grpcio` for agent communication with Go Gateway
*   **AI**: OpenAI-compatible APIs (supporting Qwen/DeepSeek/OpenAI)
*   **Config**: Pydantic v2 + `python-dotenv` for robust environment management

### Gateway (Go)
*   **Framework**: Gin (HTTP/WebSocket)
*   **gRPC Client**: Communication with Python Agent
*   **Database Access**: `pgx` + `sqlc` for type-safe SQL
*   **Config**: Viper

### Mobile (Frontend)
*   **Framework**: Flutter 3.x (Dart)
*   **State Management**: Riverpod
*   **WebSocket**: `web_socket_channel` with custom `WebSocketChatService`
*   **UI Components**: `flutter_markdown` for AI responses, Custom Fragment Shaders for Galaxy effects.

## Environment & Configuration

### Backend Configuration (`backend/app/config.py`)
Uses `pydantic-settings` v2 with `SettingsConfigDict`. Explicitly loads `.env` from the project root using `python-dotenv` with `override=True`.

### Gateway Configuration (`backend/gateway/internal/config/config.go`)
Uses Viper to load from environment variables with sensible defaults (Port: 8080, Agent: 50051).

## Directory and Key File Index

```
backend/
├── app/                  # Python FastAPI & Core Logic
│   ├── config.py         # Pydantic v2 Settings
│   ├── services/         # Business services (Galaxy, Task, LLM)
│   └── grpc_server.py    # Python gRPC Agent Entry
├── gateway/              # Go Gateway (High performance orchestration)
│   ├── cmd/server/       # Go Entry point
│   └── internal/         # Go business logic & handlers
├── alembic/              # DB Migrations
└── .env                  # Shared secrets and keys

mobile/
├── lib/
│   ├── core/services/    # WebSocketChatService, API Client
│   ├── presentation/
│   │   ├── providers/    # ChatProvider, AuthProvider (Riverpod)
│   │   ├── screens/      # ChatScreen, GalaxyScreen
│   │   └── widgets/      # AiStatusIndicator, ChatBubble
│   └── data/models/      # ChatMessageModel (JsonSerializable)
```

## Critical Business Flows

### WebSocket AI Chat Flow
1. **Flutter**: `ChatNotifier` triggers `WebSocketChatService.sendMessage`.
2. **Go Gateway**: Receives WS connection, validates user/quota.
3. **Python Agent**: Go Gateway calls Python Agent via gRPC `StreamChat`.
4. **LLM Interaction**: Python Agent streams delta tokens and tool calls back to Go.
5. **Go Gateway**: Pushes events (delta, status_update, tool_call) to Flutter via WebSocket.
6. **Flutter**: `ChatProvider` updates UI in real-time; `ChatBubble` displays `AiStatusBubble` for tool calls.

## Development Workflow

### Starting the System
1. **Infrastructure**: `docker-compose up -d` (Postgres & Redis)
2. **Python Agent**: `cd backend && PYTHONPATH=. python3 grpc_server.py` (Port 50051)
3. **Go Gateway**: `cd backend/gateway && REDIS_PASSWORD=devpassword go run cmd/server/main.go` (Port 8080)
4. **Mobile**: `cd mobile && flutter run`

### Code Generation
For Flutter models/providers:
`flutter pub run build_runner build --delete-conflicting-outputs`