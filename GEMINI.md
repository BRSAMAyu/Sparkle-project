# Sparkle (星火) - AI Learning Assistant

## Project Overview
Sparkle is an AI-powered learning assistant application designed for college students. It integrates an "AI Time Tutor" to guide users through a learning loop: Dialogue → Task Cards → Execution → Feedback → Sprint Plans.

**Target**: MVP completion by February 2, 2025.
**Team**: Student team (Python/AI background, learning Flutter).

## Tech Stack

### Backend
*   **Framework**: FastAPI (Python 3.11+)
*   **Database**: PostgreSQL (Production) / SQLite (Dev) via SQLAlchemy 2.0 (Async)
*   **Migrations**: Alembic
*   **Tasks**: APScheduler
*   **AI**: OpenAI-compatible API abstraction (supporting Qwen/DeepSeek)

### Mobile (Frontend)
*   **Framework**: Flutter 3.x (Dart)
*   **State Management**: Riverpod
*   **Navigation**: go_router
*   **Networking**: Dio + Retrofit
*   **Storage**: Shared Preferences + Hive

## Directory Structure

```
sparkle-flutter/
├── backend/          # Python FastAPI application
│   ├── app/          # Main application code
│   │   ├── api/      # Route handlers (v1/)
│   │   ├── core/     # Config, security, exceptions
│   │   ├── db/       # Database connection & session
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic data models
│   │   └── services/ # Business logic (LLM, Auth, Tasks)
│   ├── alembic/      # Database migration scripts
│   └── tests/        # Pytest suites
├── mobile/           # Flutter mobile application
│   ├── lib/
│   │   ├── app/      # App config, routing, theme
│   │   ├── core/     # Constants, network, utils
│   │   ├── data/     # Models (DTOs), Repositories
│   │   └── presentation/ # UI Screens, Widgets, Providers
│   └── test/         # Widget and unit tests
└── docs/             # API design & DB schema documentation
```

## Development Workflow

### Backend (`/backend`)

**Setup & Run:**
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure DB and AI keys
alembic upgrade head  # Apply DB migrations
uvicorn app.main:app --reload
```

**Database Migrations:**
*   Create migration: `alembic revision --autogenerate -m "message"`
*   Apply migration: `alembic upgrade head`
*   Rollback: `alembic downgrade -1`

**Testing:**
*   Run all tests: `pytest`
*   Run specific file: `pytest tests/test_api/test_auth.py`

### Mobile (`/mobile`)

**Setup & Run:**
```bash
cd mobile
flutter pub get
flutter run
```

**Code Generation (Critical):**
Run this command after modifying any file with `@JsonSerializable`, `@Riverpod`, or `@RestApi` annotations:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```
*   **Watch mode**: `flutter pub run build_runner watch --delete-conflicting-outputs`

## Key Architecture Concepts

### Backend
*   **Layered Architecture**: API (Routes) -> Service (Logic) -> Model (ORM).
*   **Async/Await**: Used extensively for DB and I/O.
*   **Idempotency**: Implemented via middleware (`IdempotencyMiddleware`) and header `Idempotency-Key` to prevent duplicate operations.
*   **LLM Service**: Abstracted in `app/services/llm_service.py` to support multiple providers via OpenAI-compatible endpoints.
*   **Job System**: `JobService` handles background tasks with startup recovery.

### Mobile
*   **State**: Riverpod is the single source of truth. Use `ref.watch` in widgets.
*   **Data Flow**: UI -> Provider -> Repository -> API Client -> Backend.
*   **JSON Serialization**: Handled by `json_serializable` (requires code gen).
*   **API Response**: All API calls return `ApiResponseModel<T>`.

## Environment Variables (.env)
*   `DATABASE_URL`: Connection string (e.g., `sqlite+aiosqlite:///./sql_app.db` or postgres).
*   `SECRET_KEY`: For JWT encryption.
*   `LLM_API_BASE_URL` & `LLM_API_KEY`: For AI service connection.
*   `LLM_MODEL_NAME`: Specific model to use (e.g., `qwen-plus`).

## Documentation
*   `docs/api_design.md`: Detailed API endpoints and request/response structures.
*   `docs/database_schema.md`: Entity Relationship details.
*   `CLAUDE.md`: Additional project context and guide.
