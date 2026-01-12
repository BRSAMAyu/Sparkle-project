# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sparkle (星火) is an AI-powered learning assistant app for college students, featuring an "AI Time Tutor" concept. The app helps users through a complete learning loop: dialogue → task cards → execution → feedback → sprint plans.

**Goal**: Complete MVP by February 2, 2025 for university software innovation competition.

**Tech Stack**:
- Backend: FastAPI (Python 3.11+, tested with 3.14) + PostgreSQL/SQLite + SQLAlchemy 2.0
- Mobile: Flutter 3.x + Riverpod + Dio
- AI: Tongyi Qianwen (Qwen) / DeepSeek via OpenAI-compatible API

## Repository Structure

```
sparkle-flutter/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/v1/   # API endpoints (auth, tasks, chat, plans, statistics, subjects, errors, knowledge, push)
│   │   ├── core/     # Security, exceptions, idempotency
│   │   ├── db/       # Database session and initialization
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas for request/response
│   │   ├── services/ # Business logic (user, task, plan, chat, LLM, subject, knowledge, push)
│   │   └── utils/    # Helper utilities (forgetting curve, vector search)
│   ├── alembic/      # Database migrations
│   └── tests/        # Pytest tests
└── mobile/           # Flutter app
    └── lib/
        ├── app/      # App configuration, routes, theme
        ├── core/     # Constants, errors, network client
        ├── data/     # Models, repositories
        └── presentation/ # Screens, widgets, providers (Riverpod)
```

## Common Development Commands

### Backend

**Setup and Run**:
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, SECRET_KEY, LLM_API_KEY, etc.

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

**Database**:
```bash
# Create new migration (after model changes)
alembic revision --autogen.ate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one version
alembic downgrade -1
```

**Testing**:
```bash
cd backend
pytest                    # Run all tests
pytest tests/test_auth.py # Run specific test file
pytest -v                 # Verbose output
pytest -k "test_name"     # Run tests matching pattern
```

**Code Quality**:
```bash
cd backend
black app/               # Format code
flake8 app/             # Lint code
mypy app/               # Type checking
```

**API Documentation**:
- After starting the server: http://localhost:8000/docs (Swagger UI)
- Alternative: http://localhost:8000/redoc

### Mobile

**Setup and Run**:
```bash
cd mobile

# Install dependencies
flutter pub get

# Generate code (for json_serializable, riverpod_generator, etc.)
flutter pub run build_runner build --delete-conflicting-outputs

# Run app
flutter run

# Run on specific device
flutter run -d <device-id>
```

**Code Generation** (required after changing models/providers):
```bash
cd mobile
flutter pub run build_runner build --delete-conflicting-outputs

# Watch mode for development
flutter pub run build_runner watch --delete-conflicting-outputs
```

**Testing**:
```bash
cd mobile
flutter test            # Run all tests
flutter test test/unit/ # Run specific directory
```

**Code Quality**:
```bash
cd mobile
flutter analyze         # Static analysis
dart format lib/        # Code quality
```

## Architecture & Key Concepts

### Backend Architecture

**Layered Structure**:
1. **API Layer** (`app/api/v1/`): FastAPI routers handling HTTP requests
2. **Service Layer** (`app/services/`): Business logic, orchestrates models and external services
3. **Model Layer** (`app/models/`): SQLAlchemy ORM models (User, Task, Plan, ChatMessage, ErrorRecord, Job, Subject, IdempotencyKey)
4. **Schema Layer** (`app/schemas/`): Pydantic models for validation and serialization

**Key Models**:
- **User**: User accounts with flame_level, flame_brightness, learning preferences (depth_preference, curiosity_preference), and push_settings
- **Task**: Learning task cards with types (learning, training, error_fix, reflection, social, planning) and statuses (pending, in_progress, completed, abandoned)
- **Plan**: Sprint plans (exam prep) or growth plans (long-term learning) with target_date and mastery_level
- **ChatMessage**: AI conversation history with structured actions in JSON format
- **ErrorRecord**: Wrong answer archive for spaced repetition with forgetting curve tracking
- **Job**: Background job system for async task processing (has recovery mechanism on startup)
- **Subject**: Subject/course catalog with caching
- **KnowledgeNode**: Knowledge graph nodes with mastery tracking, vector embeddings for semantic search
- **KnowledgeEdge**: Relationships between knowledge nodes (prerequisite, related, derived)
- **NodeReview**: Spaced repetition review records for knowledge nodes
- **PushLog**: Push notification history with delivery status and user engagement tracking

**LLM Service**:
- Abstracted in `app/services/llm_service.py`
- Uses OpenAI-compatible API (works with Qwen, DeepSeek, OpenAI)
- Configure via `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_NAME` in .env
- Enhanced parsing with "宽容模式" (tolerant mode) v2.2 for robust JSON extraction from LLM responses

**Knowledge Graph Service**:
- Knowledge node management with mastery level tracking
- Vector embeddings for semantic search (using text-embedding models)
- LLM-powered knowledge expansion and relationship inference
- Spaced repetition scheduling based on forgetting curve algorithm
- Service: `app/services/knowledge_service.py`

**Push Notification Service**:
- Persona-based intelligent push generation using LLM
- Three push types: Sprint Reminder, Memory Wake, Sleep Wake
- Configurable push preferences (frequency, time slots, content types)
- Push log tracking with delivery status and user engagement metrics
- Service: `app/services/push_service.py`

**Idempotency System**:
- Middleware-based idempotency using `IdempotencyMiddleware` (in `app/api/middleware.py`)
- Stores in memory (dev) or database via `IdempotencyStore` (`app/core/idempotency.py`)
- Prevents duplicate requests using `Idempotency-Key` header

**Application Lifecycle**:
- `app/main.py` uses `@asynccontextmanager` for startup/shutdown hooks
- On startup: recovers interrupted Jobs, loads Subject cache
- Includes CORS middleware and idempotency middleware

**Database**:
- Production: PostgreSQL with asyncpg driver
- Development: SQLite with aiosqlite (switch via DATABASE_URL)
- All models inherit from `BaseModel` (in `app/models/base.py`) with UUID primary keys
- Uses Alembic for migrations

### Mobile Architecture

**State Management**:
- Uses Riverpod for state management
- Providers in `lib/presentation/providers/` (auth, chat, task, plan)
- `ProviderScope` wraps the app in `main.dart`

**Navigation**:
- go_router for declarative routing
- Route configuration in `lib/app/routes.dart`
- Authentication-aware redirects

**Data Flow**:
1. **Models** (`lib/data/models/`): Data classes with json_serializable annotations (require code generation)
2. **Repositories** (`lib/data/repositories/`): API communication layer using Dio
3. **Providers** (`lib/presentation/providers/`): Business logic and state management
4. **Screens** (`lib/presentation/screens/`): UI pages organized by feature

**Network Layer**:
- API client in `lib/core/network/api_client.dart`
- Endpoints defined in `lib/core/network/api_endpoints.dart`
- Interceptors: `api_interceptor.dart` (auth), `idempotency_interceptor.dart` (request deduplication)

**Key Features**:
- Chat interface with AI tutor (chat_screen.dart, chat_bubble.dart, action_card.dart)
- Task management with execution timer (task screens, timer_widget.dart)
- Sprint and growth plan screens
- Knowledge map visualization with graph view
- Push notification settings and preferences
- Guest mode for quick onboarding
- Profile and statistics with flame level/brightness display

### Code Generation Requirements

**Backend**: Not required (Python is interpreted)

**Mobile**: **MUST** run code generation after modifying:
- Data models with `@JsonSerializable()` annotations
- Riverpod providers with annotations
- Retrofit API definitions

Run: `flutter pub run build_runner build --delete-conflicting-outputs`

Files ending in `.g.dart` are generated and should not be manually edited.

## Environment Configuration

### Backend .env

Required variables (see `.env.example`):
- `SECRET_KEY`: JWT secret (change in production!)
- `DATABASE_URL`: PostgreSQL or SQLite connection string
- `LLM_API_BASE_URL`: AI service endpoint (e.g., Qwen, DeepSeek)
- `LLM_API_KEY`: API key for LLM service
- `LLM_MODEL_NAME`: Model identifier (e.g., qwen3-coder-plus, deepseek-chat)

Optional:
- `BACKEND_CORS_ORIGINS`: Comma-separated allowed origins
- `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`: JWT expiry

### Mobile Configuration

API endpoint configured in `lib/core/constants/api_constants.dart` or `lib/core/network/api_endpoints.dart`

## API Endpoints

Base: `/api/v1`

- `/auth` - Registration, login, token refresh, guest mode
- `/users` - User profile management, push settings, notification preferences
- `/tasks` - Task CRUD, start, complete operations
- `/chat` - AI conversation with action suggestions
- `/plans` - Plan management, AI task generation
- `/statistics` - Learning overview, flame level/brightness
- `/subjects` - Subject catalog
- `/errors` - Error record management with forgetting curve
- `/knowledge` - Knowledge graph management (nodes, edges, reviews)
- `/knowledge/expand` - LLM-powered knowledge expansion
- `/knowledge/search` - Vector semantic search for knowledge nodes
- `/push` - Push notification management, delivery logs, testing

See `docs/api_design.md` for detailed API specs.

## Database Schema

Key tables: users, tasks, plans, chat_messages, error_records, jobs, subjects, idempotency_keys, knowledge_nodes, knowledge_edges, node_reviews, push_logs

**New Features**:
- **Knowledge Graph**: knowledge_nodes (with vector embeddings), knowledge_edges (prerequisites/related), node_reviews (spaced repetition)
- **Push System**: push_logs (delivery tracking), user.push_settings (JSONB preferences)
- **Forgetting Curve**: Enhanced error_records with next_review_at calculation

See `docs/database_schema.md` for full schema and relationships.

## Development Notes

- **Team**: 4 sophomore/junior CS students, experienced with Python/AI tools, learning Dart/Flutter
- **Target**: MVP by 2025-02-02 for competition
- **AI Integration**: Core feature uses LLM for personalized learning guidance
- **Data**: Chinese language interface (comments and UI are in Chinese)

## Important Patterns

### Backend

1. **Dependency Injection**: Use FastAPI's `Depends()` for database sessions and authentication
2. **Async/Await**: All database operations are async using SQLAlchemy 2.0 async session
3. **Error Handling**: Centralized exceptions in `app/core/exceptions.py`
4. **Job Recovery**: Background jobs recover on startup via `JobService.startup_recovery()`

### Mobile

1. **Riverpod Providers**: Use `ref.watch()` to listen, `ref.read()` for one-time reads
2. **Code Generation**: Always regenerate after model/provider changes
3. **API Responses**: Wrapped in `ApiResponseModel<T>` for consistent error handling
4. **Navigation**: Use `context.go()` or `context.push()` from go_router

## Testing Strategy

- Backend: pytest with async support (`pytest-asyncio`)
- Mobile: Flutter test framework (test directory structure not yet created)
- Test configuration in `backend/tests/conftest.py`

## Documentation

- `docs/api_design.md` - REST API specifications
- `docs/database_schema.md` - Database models and schema
- `docs/development_guide.md` - Additional development guidance
