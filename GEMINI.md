# Sparkle (星火) - AI Learning Assistant

## Project Overview
Sparkle is an AI-powered learning assistant application designed for college students. It integrates an "AI Time Tutor" to guide users through a learning loop: Dialogue → Task Cards → Execution → Feedback → Sprint Plans.

**Target**: MVP completion by February 2, 2025.
**Team**: Student team (Python/AI background, learning Flutter).

## Tech Stack

### Backend
*   **Framework**: FastAPI (Python 3.11+) - Web framework for building RESTful APIs
*   **ASGI Server**: Uvicorn - Used to run the FastAPI application
*   **Database**: PostgreSQL (Production) / SQLite (Dev) via SQLAlchemy 2.0 (Async) - ORM framework for database operations
*   **Async DB Driver**: asyncpg - Asynchronous PostgreSQL driver
*   **Migrations**: Alembic
*   **Data Validation**: Pydantic - Data validation and settings management
*   **Config Management**: Pydantic-settings - Configuration management
*   **JWT Handling**: python-jose - For JWT token processing
*   **Password Hashing**: Passlib - For password hashing
*   **Logging**: Loguru - For structured logging
*   **Tasks**: APScheduler - For scheduled task management
*   **AI**: OpenAI - For interacting with LLMs (OpenAI-compatible API abstraction, supporting Qwen/DeepSeek)
*   **Vector DB**: pgvector - Vector database support for embeddings
*   **Caching/Queue**: Redis - For caching and background task queues

### Mobile (Frontend)
*   **Framework**: Flutter 3.x (Dart)
*   **State Management**: flutter_riverpod - For state management
*   **Navigation**: go_router - For routing management
*   **Networking**: http - HTTP client
*   **API Client**: Dio + Retrofit
*   **Local Storage**: shared_preferences - For local storage
*   **Local Database**: hive - For local database
*   **SVG Rendering**: flutter_svg - For SVG image rendering
*   **Internationalization**: intl - For internationalization support

## Environment & Configuration

### Backend Configuration (`backend/app/config.py`)
Backend configuration is managed via `pydantic-settings`, reading environment variables from `.env` file:

- `APP_NAME`: Application name ("Sparkle")
- `APP_VERSION`: Application version ("0.1.0")
- `DEBUG`: Debug mode switch
- `SECRET_KEY`: Key for JWT signing
- `DATABASE_URL`: Database connection URL
- `BACKEND_CORS_ORIGINS`: CORS whitelist
- `LLM_API_BASE_URL`: LLM API base URL
- `LLM_API_KEY`: LLM API key
- `LLM_MODEL_NAME`: LLM model name
- `LLM_PROVIDER`: LLM provider
- `EMBEDDING_MODEL`: Embedding model name
- `EMBEDDING_DIM`: Embedding dimension (1536)
- `UPLOAD_DIR`: File upload directory
- `MAX_UPLOAD_SIZE`: Maximum upload file size
- `LOG_LEVEL`: Log level
- `DEMO_MODE`: Demo mode switch

These configurations are defined in the `Settings` class and globally instantiated via `settings = Settings()`.

### Mobile Configuration
Mobile configuration primarily manages dependencies via `pubspec.yaml` and uses `shared_preferences` and `hive` for local data storage.



## Error Handling

### Backend Error Handling
The backend uniformly handles HTTP exceptions via `app/core/exceptions.py`, defining various custom exception types such as `BadRequestException`, `UnauthorizedException`, `NotFoundException`, `InternalServerErrorException`, etc. These exceptions are caught in API routes, returning standardized error responses.

Error handling mechanisms include:
1.  **Custom Exception Classes**: Defines various business-related exception types.
2.  **Global Exception Handler**: Registers a global exception handler in `app/main.py` to catch unhandled exceptions.
3.  **HTTP Status Code Mapping**: Maps custom exceptions to standard HTTP status codes.
4.  **Error Logging**: Uses `loguru` to record detailed error logs for debugging and monitoring.
5.  **Unified Error Response Format**: A unified error response format, including error code, error message, and detailed information.

### Frontend Network Error Handling
When the network is disconnected, the frontend typically displays friendly error messages and provides a retry mechanism. For critical operations, operation records are cached locally and resubmitted once the network connection is restored.

Error handling mechanisms include:
1.  **Network Status Detection**: Uses the `connectivity_plus` plugin to detect network connection status.
2.  **HTTP Error Handling**: Catches HTTP request errors and displays corresponding error messages based on status codes.
3.  **Timeout Handling**: Sets reasonable request timeouts to avoid long waits.
4.  **Retry Mechanism**: Provides a retry button or automatic retry functionality for retriable operations.
5.  **Local Caching**: Uses `hive` or `shared_preferences` to cache critical operations and resubmit them when the network is restored.
6.  **User-Friendly Prompts**: Displays clear and easy-to-understand error messages, avoiding technical jargon.

## Directory and Key File Index

```
backend/
├── app/
│   ├── main.py                           # Application entry point, includes lifespan management
│   ├── config.py                         # Configuration management, using pydantic-settings
│   ├── api/
│   │   ├── v1/
│   │   │   ├── router.py                 # API route aggregation
│   │   │   ├── galaxy.py                 # Knowledge Galaxy API
│   │   │   ├── chat.py                   # Chat API, supports tool calls and streaming responses
│   │   │   ├── tasks.py                  # Task API
│   │   │   ├── plans.py                  # Plan API
│   │   │   ├── auth.py                   # Authentication API
│   │   │   └── ...                       # Other APIs
│   ├── services/
│   │   ├── galaxy_service.py             # Knowledge Galaxy core service, handles galaxy data, node sparking, semantic search
│   │   ├── expansion_service.py          # Knowledge Expansion service, uses LLM to automatically expand knowledge nodes
│   │   ├── decay_service.py              # Forgetting Decay service, implements Ebbinghaus forgetting curve
│   │   ├── llm_service.py                # LLM service, interacts with large language models
│   │   ├── task_service.py               # Task service, handles task business logic
│   │   ├── plan_service.py               # Plan service, handles plan business logic
│   │   ├── user_service.py               # User service, handles user business logic
│   │   ├── notification_service.py       # Notification service, handles system notifications
│   │   ├── push_service.py               # Smart Push service, implements personalized pushes
│   │   ├── scheduler_service.py          # Scheduler service, manages scheduled tasks
│   │   └── ...                           # Other services
│   ├── models/
│   │   ├── galaxy.py                     # Knowledge Galaxy models, includes KnowledgeNode, UserNodeStatus, etc.
│   │   ├── task.py                       # Task model
│   │   ├── plan.py                       # Plan model
│   │   ├── user.py                       # User model
│   │   ├── chat.py                       # Chat message model
│   │   ├── notification.py               # Notification model
│   │   └── ...                           # Other models
│   ├── workers/
│   │   └── expansion_worker.py           # Knowledge Expansion background task, processes node expansion queue
│   ├── core/
│   │   ├── sse.py                        # SSE management, implements real-time event pushing
│   │   ├── exceptions.py                 # Exception handling
│   │   ├── security.py                   # Security related, JWT token processing
│   │   └── ...                           # Core modules
│   ├── tools/
│   │   ├── registry.py                   # Tool registry
│   │   ├── base.py                       # Tool base class
│   │   ├── knowledge_tools.py            # Knowledge related tools
│   │   ├── task_tools.py                 # Task related tools
│   │   └── schemas.py                    # Tool Schema definitions
│   └── orchestration/
│       ├── composer.py                   # Response orchestration
│       ├── executor.py                   # Tool executor
│       ├── prompts.py                    # Prompt management
│       └── error_handler.py              # Error handling
├── alembic/                              # Database migrations
├── seed_data/                            # Seed data
└── ...                                   # Other files

mobile/
├── lib/
│   ├── main.dart                         # Application entry point
│   ├── app/
│   │   ├── app.dart                      # Application root component
│   │   └── routes.dart                   # Route configuration
│   ├── presentation/
│   │   ├── screens/
│   │   │   ├── galaxy_screen.dart        # Knowledge Galaxy interface
│   │   │   ├── chat_screen.dart          # Chat interface
│   │   │   ├── task_list_screen.dart     # Task list interface
│   │   │   ├── task_detail_screen.dart   # Task detail interface
│   │   │   └── ...                       # Other interfaces
│   │   ├── providers/
│   │   │   ├── galaxy_provider.dart      # Knowledge Galaxy state management
│   │   │   ├── chat_provider.dart        # Chat state management
│   │   │   ├── task_provider.dart        # Task state management
│   │   │   └── ...                       # Other state management
│   │   └── widgets/
│   │       ├── galaxy/
│   │       │   ├── flame_core.dart       # Flame core component, uses Fragment Shader
│   │       │   ├── star_map_painter.dart # Star map drawing
│   │       │   ├── energy_particle.dart   # Energy particle animation
│   │       │   └── star_success_animation.dart # Spark success animation
│   │       └── ...                       # Other components
│   ├── data/
│   │   ├── repositories/
│   │   │   ├── galaxy_repository.dart    # Knowledge Galaxy data repository
│   │   │   ├── chat_repository.dart      # Chat data repository
│   │   │   ├── task_repository.dart      # Task data repository
│   │   │   └── ...                       # Other data repositories
│   │   ├── models/
│   │   │   ├── galaxy_model.dart         # Knowledge Galaxy data model
│   │   │   ├── chat_message_model.dart   # Chat message data model
│   │   │   ├── task_model.dart           # Task data model
│   │   │   └── ...                       # Other data models
│   │   └── datasources/
│   │       ├── api_client.dart           # API client
│   │       └── local_storage.dart        # Local storage
│   └── core/
│       ├── services/
│       ├── utils/
│       ├── design/
│       └── constants/
└── shaders/
    └── core_flame.frag                   # Flame shader, GLSL implementation
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

**Startup Process (`backend/app/main.py`):**
1.  On application startup, FastAPI's `lifespan` context manager is invoked.
2.  **Startup Phase**:
    *   Initialize database data (`init_db`).
    *   Recover interrupted Jobs (`JobService.startup_recovery`).
    *   Load subject cache (`SubjectService.load_cache`).
    *   Start scheduled task scheduler (`scheduler_service.start`).
    *   Start knowledge expansion background task (`start_expansion_worker`).
3.  **Shutdown Phase**:
    *   Stop knowledge expansion background task (`stop_expansion_worker`).

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

**Startup Process (`mobile/lib/main.dart`):**
1.  `WidgetsFlutterBinding.ensureInitialized()`: Ensures Flutter binding is initialized.
2.  `Hive.initFlutter()`: Initializes Hive local storage.
3.  `SharedPreferences.getInstance()`: Initializes shared preferences.
4.  `runApp(ProviderScope(...))`: Runs the application with Riverpod for state management.

**Code Generation (Critical):**
Run this command after modifying any file with `@JsonSerializable`, `@Riverpod`, or `@RestApi` annotations:
```bash
flutter pub run build_runner build --delete-conflicting-outputs
```
*   **Watch mode**: `flutter pub run build_runner watch --delete-conflicting-outputs`

## Key Architecture Concepts

## Backend Deep Dive

### API Route Collection

| HTTP Method | Endpoint | Corresponding Controller Function | Core Service Call |
|-------------|----------|-----------------------------------|-------------------|
| GET | `/api/v1/galaxy/graph` | `get_galaxy_graph` | `GalaxyService.get_galaxy_graph` |
| POST | `/api/v1/galaxy/node/{node_id}/spark` | `spark_node` | `GalaxyService.spark_node` |
| GET | `/api/v1/galaxy/node/{node_id}` | `get_node_detail` | `GalaxyService._get_user_status` |
| POST | `/api/v1/galaxy/search` | `search_nodes` | `GalaxyService.semantic_search` |
| GET | `/api/v1/galaxy/review/suggestions` | `get_review_suggestions` | `DecayService.get_review_suggestions` |
| POST | `/api/v1/galaxy/node/{node_id}/decay/pause` | `pause_node_decay` | `DecayService.pause_decay` |
| GET | `/api/v1/galaxy/stats` | `get_galaxy_stats` | `GalaxyService._calculate_user_stats`, `DecayService.get_decay_stats` |
| GET | `/api/v1/galaxy/events` | `galaxy_events_stream` | `sse_manager.connect` |
| POST | `/api/v1/chat` | `chat` | `llm_service.chat_with_tools`, `ToolExecutor.execute_tool_calls` |
| POST | `/api/v1/chat/stream` | `chat_stream` | `llm_service.chat_stream_with_tools`, `ToolExecutor.execute_tool_call` |
| POST | `/api/v1/chat/confirm` | `confirm_action` | `ToolExecutor.execute_tool_call` |
| GET | `/api/v1/tasks` | `get_tasks` | `TaskService.get_multi` |
| POST | `/api/v1/tasks` | `create_task` | `TaskService.create` |
| GET | `/api/v1/tasks/{id}` | `get_task` | `TaskService.get_by_id` |
| PUT | `/api/v1/tasks/{id}` | `update_task` | `TaskService.update` |
| POST | `/api/v1/tasks/{id}/start` | `start_task` | `TaskService.start` |
| POST | `/api/v1/tasks/{id}/complete` | `complete_task` | `TaskService.complete` |
| POST | `/api/v1/tasks/{id}/abandon` | `abandon_task` | `TaskService.abandon` |
| GET | `/api/v1/plans` | `get_plans` | `PlanService.get_multi` |
| POST | `/api/v1/plans` | `create_plan` | `PlanService.create` |

### Data Model Perspective (Database Schema)

#### Core Table Structures

##### `users` (User Table)
- `id` (GUID): Primary Key
- `username` (String): Username
- `email` (String): Email
- `hashed_password` (String): Hashed password
- `nickname` (String): Nickname
- `avatar_url` (String): Avatar URL
- `flame_level` (Integer): Flame level (1-10)
- `flame_brightness` (Float): Flame brightness (0-1)
- `depth_preference` (Float): Depth preference (0-1)
- `curiosity_preference` (Float): Curiosity preference (0-1)
- `schedule_preferences` (JSON): Fragmented time/schedule preferences
- `is_active` (Boolean): Is active

##### `knowledge_nodes` (Knowledge Node Table)
- `id` (GUID): Primary Key
- `subject_id` (Integer): Associated subject ID (Foreign Key to `subjects` table)
- `parent_id` (GUID): Parent node ID (Self-referencing)
- `name` (String): Node name
- `name_en` (String): English name
- `description` (Text): Description
- `keywords` (JSON): Array of keywords
- `importance_level` (Integer): Importance level (1-5)
- `is_seed` (Boolean): Is a seed node
- `source_type` (String): Node source (seed/user_created/llm_expanded)
- `source_task_id` (GUID): Source task ID
- `embedding` (Vector): Vector embedding

##### `user_node_status` (User Node Status Table)
- `user_id` (GUID): User ID (Part of composite primary key)
- `node_id` (GUID): Node ID (Part of composite primary key)
- `mastery_score` (Float): Mastery score (0-100)
- `total_study_minutes` (Integer): Total study minutes
- `study_count` (Integer): Study count
- `is_unlocked` (Boolean): Is unlocked
- `is_collapsed` (Boolean): Is collapsed
- `is_favorite` (Boolean): Is favorite
- `last_study_at` (DateTime): Last study time
- `decay_paused` (Boolean): Is decay paused
- `next_review_at` (DateTime): Next review time
- `first_unlock_at` (DateTime): First unlock time

##### `node_relations` (Node Relations Table)
- `source_node_id` (GUID): Source node ID
- `target_node_id` (GUID): Target node ID
- `relation_type` (String): Relation type (prerequisite/related/application/composition/evolution)
- `strength` (Float): Relation strength (0-1)
- `created_by` (String): Creator (seed/user/llm)

##### `study_records` (Study Records Table)
- `user_id` (GUID): User ID
- `node_id` (GUID): Node ID
- `task_id` (GUID): Associated task ID
- `study_minutes` (Integer): Study minutes
- `mastery_delta` (Float): Mastery delta
- `record_type` (String): Record type (task_complete/review/exploration)

##### `node_expansion_queue` (Node Expansion Queue Table)
- `trigger_node_id` (GUID): Trigger node ID
- `trigger_task_id` (GUID): Trigger task ID
- `user_id` (GUID): User ID
- `expansion_context` (Text): Expansion context
- `status` (String): Status (pending/processing/completed/failed)
- `expanded_nodes` (JSON): Expanded nodes
- `error_message` (Text): Error message
- `processed_at` (DateTime): Processed at

##### `tasks` (Tasks Table)
- `id` (GUID): Primary Key
- `user_id` (GUID): Owner User ID
- `plan_id` (GUID): Associated Plan ID (Optional)
- `title` (String): Task title
- `type` (Enum): Task type (learning/training/error_fix/reflection/social/planning)
- `tags` (JSON): List of tags
- `estimated_minutes` (Integer): Estimated duration (minutes)
- `difficulty` (Integer): Difficulty level (1-5)
- `energy_cost` (Integer): Energy cost (1-5)
- `guide_content` (Text): Guide content (AI generated)
- `status` (Enum): Task status (pending/in_progress/completed/abandoned)
- `started_at` (DateTime): Start time
- `completed_at` (DateTime): Completion time
- `actual_minutes` (Integer): Actual duration
- `user_note` (Text): User note
- `priority` (Integer): Priority
- `due_date` (Date): Due date
- `knowledge_node_id` (GUID): Associated Knowledge Node ID
- `auto_expand_enabled` (Boolean): Auto expansion enabled

##### `plans` (Plans Table)
- `id` (GUID): Primary Key
- `user_id` (GUID): Owner User ID
- `name` (String): Plan name
- `type` (Enum): Plan type (sprint/growth)
- `description` (Text): Plan description
- `target_date` (Date): Target date (for sprint plans)
- `daily_available_minutes` (Integer): Daily available minutes
- `total_estimated_hours` (Float): Total estimated hours
- `mastery_level` (Float): Mastery level (0-1)
- `progress` (Float): Progress percentage (0-1)
- `is_active` (Boolean): Is active

##### `chat_messages` (Chat Messages Table)
- `id` (GUID): Primary Key
- `user_id` (GUID): Owner User ID
- `session_id` (GUID): Session ID (to distinguish different conversations)
- `task_id` (GUID): Associated Task ID (optional, if conversation is task-related)
- `role` (Enum): Message role (user/assistant/system)
- `content` (Text): Message content
- `actions` (JSON): List of actions executed by AI
- `tokens_used` (Integer): Number of tokens consumed
- `model_name` (String): Model name used

##### `notifications` (Notifications Table)
- `id` (GUID): Primary Key
- `user_id` (GUID): Owner User ID
- `title` (String): Notification title
- `content` (String): Notification content
- `type` (String): Notification type (fragmented_time/system/reminder)
- `is_read` (Boolean): Is read
- `read_at` (DateTime): Read time
- `data` (JSON): Associated data

##### `push_preferences` (Push Preferences Table)
- `id` (GUID): Primary Key
- `user_id` (GUID): Owner User ID
- `active_slots` (JSON): Active time slots
- `timezone` (String): Timezone
- `enable_curiosity` (Boolean): Enable curiosity push
- `persona_type` (String): Push persona type (coach/anime)
- `daily_cap` (Integer): Daily push cap
- `last_push_time` (DateTime): Last push time
- `consecutive_ignores` (Integer): Consecutive ignores count

##### `push_histories` (Push Histories Table)
- `id` (GUID): Primary Key
- `user_id` (GUID): Owner User ID
- `trigger_type` (String): Trigger type (memory/sprint/inactivity)
- `content_hash` (String): Content hash
- `status` (String): Status (sent/clicked/snoozed/dismissed)

### Core Service Logic

#### GalaxyService (Knowledge Galaxy Service)
`GalaxyService (backend/app/services/galaxy_service.py)` is responsible for the core functions of the Knowledge Galaxy:

1.  **Retrieve Galaxy Data** (`get_galaxy_graph`):
    *   Queries all knowledge nodes and their statuses for a user.
    *   Queries relationships between nodes.
    *   Assembles the complete galaxy data structure for return.

2.  **Spark Knowledge Node** (`spark_node`):
    *   Calculates mastery increment based on study duration and node importance level.
    *   Updates `UserNodeStatus` model's `mastery_score` field.
    *   Records study history to the `StudyRecord` table.
    *   Triggers LLM expansion when study count reaches 2.

3.  **ExpansionService (Knowledge Expansion Service)**:
    *   `queue_expansion`: Adds expansion requests to the queue.
    *   `_should_expand`: Checks if expansion should be triggered.
    *   `_build_expansion_context`: Builds the expansion context to be sent to the LLM.
    *   `process_expansion`: Processes expansion requests.
    *   `_create_expanded_nodes`: Creates expanded knowledge nodes.

4.  **ExpansionWorker (Expansion Worker Thread)**:
    *   Periodically scans the `node_expansion_queue` table.
    *   Processes `pending` expansion tasks.
    *   Calls `ExpansionService.process_expansion` to handle tasks.
    *   Notifies the frontend via SSE when new nodes are created.

5.  **Semantic Search** (`semantic_search`):
    *   Uses vector similarity search for relevant knowledge points.
    *   Combines with user status information to return search results.

#### LLMService (Large Language Model Service)
`LLMService (backend/app/services/llm_service.py)` is responsible for interacting with large language models:

1.  **Chat Functionality** (`chat_with_tools`):
    *   Chat interface supporting tool calls.
    *   Constructs system prompts and conversation history.
    *   Calls LLM and handles tool calls.

2.  **Streaming Chat** (`chat_stream_with_tools`):
    *   Streams chat content, supporting real-time display.
    *   Handles streaming tool calls.

3.  **Continue Conversation** (`continue_with_tool_results`):
    *   Feeds tool execution results back to the LLM to get the final response.

#### TaskService (Task Service)
`TaskService (backend/app/services/task_service.py)` is responsible for task management:

1.  **Create Task** (`create`)
2.  **Update Task** (`update`)
3.  **Start Task** (`start`)
4.  **Complete Task** (`complete`)
5.  **Abandon Task** (`abandon`)

#### PushService (Smart Push Service)
`PushService (backend/app/services/push_service.py)` is responsible for smart push logic:

1.  **Process All User Pushes** (`process_all_users`):
    *   Retrieves all active users with push preferences.
    *   Calls `process_user_push` method for each user.

2.  **Process Single User Push** (`process_user_push`):
    *   Checks if the user is within active time slots.
    *   Checks frequency limits (daily cap and cooldown).
    *   Evaluates push strategies (Sprint Strategy > Memory Strategy > Inactivity Strategy).
    *   Generates push content.
    *   Sends push and records history.

#### Push Strategies
Push strategies are implemented via the abstract base class `PushStrategy`, including:

1.  **MemoryStrategy**:
    *   Detects important knowledge points with low user mastery.
    *   Triggers when calculated memory retention is less than 0.3 and importance is greater than 4.
    *   Retention is calculated using `DecayService`'s forgetting curve algorithm.

2.  **SprintStrategy**:
    *   Detects user sprint plans nearing their due date.
    *   Triggers when the plan's target date is within 72 hours.

3.  **InactivityStrategy**:
    *   Detects users who have been inactive for a long time.
    *   Triggers when a user has been inactive for more than 24 hours.

#### SchedulerService (Scheduler Service)
`SchedulerService (backend/app/services/scheduler_service.py)` is responsible for scheduled task management:

1.  **Smart Push Cycle**:
    *   Runs `run_smart_push_cycle` every 15 minutes.
    *   Triggers `PushService.process_all_users()`.

2.  **Daily Decay Task**:
    *   Runs `apply_daily_decay` daily at 3 AM.
    *   Applies forgetting curve decay to all users' knowledge points.

#### DecayService (Forgetting Decay Service)
`DecayService (backend/app/services/decay_service.py)` implements the Ebbinghaus forgetting curve:

1.  **Daily Decay** (`apply_daily_decay`):
    *   Applies forgetting decay to all eligible nodes.
    *   Calculates decayed mastery score.

2.  **Get Review Suggestions** (`get_review_suggestions`):
    *   Recommends nodes for review based on mastery and next review time.

## Mobile Deep Dive

### Routing System
The mobile application uses `go_router` for route management, with key pages including:
- `/`: Splash Screen
- `/login`: Login Screen
- `/register`: Register Screen
- `/home`: Home Screen
- `/tasks`: Task List Screen
- `/tasks/:id`: Task Detail Screen
- `/tasks/:id/execute`: Task Execution Screen
- `/chat`: Chat Screen
- `/sprint`: Sprint Plan Screen
- `/growth`: Growth Plan Screen
- `/profile`: Profile Screen
- `/galaxy`: Knowledge Galaxy Screen

### State Management Map
The mobile application uses `Riverpod` for state management, with core Providers including:
- `authProvider`: Authentication state management
- `galaxyProvider`: Knowledge Galaxy state management
- `chatProvider`: Chat state management
- `taskProvider`: Task state management

### Key UI Component Implementation

#### Knowledge Galaxy
`GalaxyScreen (mobile/lib/presentation/screens/galaxy_screen.dart)` is the main interface for the Knowledge Galaxy:

1.  **Star Map Drawing**:
    *   Uses `InteractiveViewer` for a zoomable and draggable canvas.
    *   Uses `CustomPaint` and `StarMapPainter` to draw the star map.
    *   Node positions are calculated by the `_calculateLayout` method.

2.  **Flame Core**:
    *   Uses the `FlameCore` component to render the central flame effect.
    *   Achieves dynamic flame animation through Fragment Shaders.

3.  **Interactive Animations**:
    *   Triggered animation effects when a node is tapped.
    *   Uses `EnergyTransferAnimation` for energy transfer animation.
    *   Uses `StarSuccessAnimation` for successful spark animation.

#### Shader Implementation
`FlameCore (mobile/lib/presentation/widgets/galaxy/flame_core.dart)` uses Fragment Shaders for the flame effect:

1.  **Shader Loading**:
    *   Loads GLSL shader programs via `FragmentProgram.fromAsset`.

2.  **Parameter Passing**:
    *   Passes time, intensity, and other parameters to the shader via `setFloat` methods.

3.  **Rendering**:
    *   Renders using `CustomPaint` and `_ShaderPainter`.

## Critical Business Flows

### "Sparking a Star" End-to-End Flow

1.  **User Taps Star on Frontend**:
    *   `GalaxyScreen` captures the tap event.
    *   Triggers the `_sparkNodeWithAnimation` method.

2.  **API Call**:
    *   Frontend calls the `/api/v1/galaxy/node/{node_id}/spark` endpoint.

3.  **Backend Calculation**:
    *   `GalaxyService.spark_node` calculates the mastery increment.
    *   Updates the `mastery_score` field of the `UserNodeStatus` model.
    *   Records study history to the `StudyRecord` table.

4.  **Database Update**:
    *   SQLAlchemy commits the transaction, updating the database.

5.  **Trigger AI Expansion**:
    *   When the study count reaches 2, `ExpansionService.queue_expansion` adds an expansion request to the queue.

6.  **SSE Push**:
    *   `ExpansionWorker` processes the expansion queue.
    *   Pushes new node information to the frontend via `sse_manager.send_to_user`.

7.  **Frontend Animation Playback**:
    *   The frontend receives the SSE event, updates the UI, and plays an animation.

### AI Conversation Flow

1.  **User Sends Message**:
    *   The user types and sends a message in the chat interface.

2.  **Backend Receives**:
    *   The `chat` or `chat_stream` endpoint receives the message.

3.  **Context Retrieval**:
    *   `get_user_context` retrieves the user's learning status.
    *   `get_conversation_history` retrieves conversation history.

4.  **LLM Call**:
    *   `llm_service.chat_with_tools` calls the LLM and passes tool definitions.

5.  **Streaming Response**:
    *   The LLM streams back text content and tool call information.

6.  **Frontend Rendering**:
    *   The frontend displays the LLM's response in real-time.
    *   Processes tool calls and displays corresponding components.

### Smart Push Flow

1.  **Scheduled Trigger**:
    *   `SchedulerService` triggers the smart push cycle every 15 minutes.

2.  **User Evaluation**:
    *   `PushService.process_all_users` retrieves all active users with push preferences.
    *   Calls the `process_user_push` method for each user.

3.  **Strategy Evaluation**:
    *   Push strategies are evaluated by priority: Sprint Strategy > Memory Strategy > Inactivity Strategy.
    *   `SprintStrategy.should_trigger` checks for sprint plans nearing their due date.
    *   `MemoryStrategy.should_trigger` checks for important knowledge points with low mastery.
    *   `InactivityStrategy.should_trigger` checks if the user has been inactive for a long time.

4.  **Content Generation**:
    *   The triggered strategy is selected, and `get_trigger_data` is called to retrieve trigger data.
    *   `llm_service.generate_push_content` generates personalized push content based on the user's persona type.

5.  **Send Push**:
    *   `NotificationService.create` creates a notification record.
    *   `PushHistory` records the push history for frequency control and analysis.

6.  **Frontend Display**:
    *   Users see push notifications in the notification center.
    *   Tapping a notification can navigate to the corresponding page (plan page, knowledge point page, etc.).

## Error Handling

### Backend Error Handling
The backend uniformly handles HTTP exceptions via `app/core/exceptions.py`, defining various custom exception types such as `BadRequestException`, `UnauthorizedException`, `NotFoundException`, `InternalServerErrorException`, etc. These exceptions are caught in API routes, returning standardized error responses.

Error handling mechanisms include:
1.  **Custom Exception Classes**: Defines various business-related exception types.
2.  **Global Exception Handler**: Registers a global exception handler in `app/main.py` to catch unhandled exceptions.
3.  **HTTP Status Code Mapping**: Maps custom exceptions to standard HTTP status codes.
4.  **Error Logging**: Uses `loguru` to record detailed error logs for debugging and monitoring.
5.  **Unified Error Response Format**: A unified error response format, including error code, error message, and detailed information.

### Frontend Network Error Handling
When the network is disconnected, the frontend typically displays friendly error messages and provides a retry mechanism. For critical operations, operation records are cached locally and resubmitted once the network connection is restored.

Error handling mechanisms include:
1.  **Network Status Detection**: Uses the `connectivity_plus` plugin to detect network connection status.
2.  **HTTP Error Handling**: Catches HTTP request errors and displays corresponding error messages based on status codes.
3.  **Timeout Handling**: Sets reasonable request timeouts to avoid long waits.
4.  **Retry Mechanism**: Provides a retry button or automatic retry functionality for retriable operations.
5.  **Local Caching**: Uses `hive` or `shared_preferences` to cache critical operations and resubmit them when the network is restored.
6.  **User-Friendly Prompts**: Displays clear and easy-to-understand error messages, avoiding technical jargon.



