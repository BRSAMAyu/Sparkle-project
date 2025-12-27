# Sparkle (星火) - AI Learning Assistant

## Project Overview
Sparkle is an AI-powered learning assistant mobile application designed for university students. It features an "AI Time Tutor", knowledge graph visualization ("Knowledge Galaxy"), and smart task management.

The project utilizes a **hybrid microservices architecture**:
- **Mobile App:** Flutter (Android/iOS).
- **Gateway:** Go (Gin framework) handling WebSockets, Auth, and high-concurrency requests.
- **AI Engine:** Python (FastAPI/gRPC) handling LLM orchestration, RAG (using pgvector), and complex logic.
- **Infrastructure:** PostgreSQL (with pgvector), Redis, Docker.

## Building and Running

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Go 1.21+
- Flutter SDK 3.x

### Quick Start (Development)
The project uses a `Makefile` to orchestrate development services.

1.  **Start Infrastructure (DB & Redis):**
    ```bash
    make dev-up
    ```

2.  **Start Backend Services (requires 3 terminals):**
    *   **Terminal 1 (Infra):** `make dev-up` (if not running detached)
    *   **Terminal 2 (Python AI Engine):**
        ```bash
        # Ensure venv is active and dependencies installed
        cd backend
        pip install -r requirements.txt
        make grpc-server
        ```
    *   **Terminal 3 (Go Gateway):**
        ```bash
        cd backend/gateway
        make gateway-run
        # Or for auto-reload:
        make gateway-dev
        ```

3.  **Start Mobile App:**
    ```bash
    cd mobile
    flutter pub get
    flutter run
    ```

4.  **Full Start (Convenience):**
    ```bash
    make dev-all
    ```

### Testing
- **Integration Tests:** `make integration-test` (Tests WebSocket & gRPC flow)
- **gRPC Tests:** `make grpc-test`
- **Mobile Tests:** `cd mobile && flutter test`

### Database Migrations
- **Python (Alembic):**
    ```bash
    cd backend && alembic upgrade head
    ```
- **Sync Go Models (after DB changes):**
    ```bash
    make sync-db
    ```

## Development Conventions

### Python (AI Engine)
- **Framework:** FastAPI + gRPC.
- **Style:** PEP 8, enforced via `black` and `flake8`.
- **Typing:** Strict type hints used; `mypy` for checking.
- **Config:** `pydantic` for settings and data validation.
- **Observability:** OpenTelemetry integration.

### Go (Gateway)
- **Framework:** Gin Web Framework.
- **Database Access:** `sqlc` is used to generate type-safe Go code from SQL. **Do not write manual SQL queries in Go code**; update `schema.sql` or queries file and run `make sync-db`.
- **Structure:** Follows standard Go project layout (`cmd/`, `internal/`, `pkg/`).

### Flutter (Mobile)
- **State Management:** Riverpod (with `riverpod_generator`).
- **Code Generation:** Heavy use of `build_runner`. Run `dart run build_runner build --delete-conflicting-outputs` after modifying models or providers.
- **Architecture:** Feature-first or Layered architecture.
- **Visuals:** Uses custom shaders (`shaders/`) for the Galaxy view.

### Documentation
- Extensive documentation is located in the `docs/` directory.
- Key architectural docs: `docs/00_项目概览/02_技术架构.md`.
- API references: `docs/02_技术设计文档/03_API参考.md`.
