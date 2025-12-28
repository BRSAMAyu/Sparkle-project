# AGENTS.md - Agent-Specific Guidelines

This file provides additional guidance for AI agents working with this repository.

## Project Structure & Module Organization
- **`backend/`**: Python gRPC service, migrations, and tests
  - `backend/app/`: Python AI engine (gRPC server, orchestration, tools)
  - `backend/alembic/`: Database migrations
  - `backend/tests/`: Python tests
- **`backend/gateway/`**: Go WebSocket/HTTP gateway
  - `cmd/server/`: Entry point
  - `internal/`: Core packages (handler, agent, db, service, cqrs)
- **`mobile/`**: Flutter mobile app
  - `lib/presentation/`: UI screens and widgets
  - `lib/core/`: Services, design system, network
  - `lib/data/`: Data layer
  - `lib/domain/`: Business logic
- **`proto/`**: gRPC protocol definitions
  - Generated code: `backend/app/gen/` and `backend/gateway/gen/`
- **`docs/`**: Documentation
- **`scripts/`**: Utility scripts
- **`docker-compose.yml`**: Local infrastructure

## Build, Test, and Development Commands

### Full Development Setup
```bash
make dev-all  # Prints startup instructions for all components
```

### Individual Components
```bash
make dev-up              # Start Docker (PostgreSQL, Redis)
make grpc-server         # Python gRPC service
make gateway-build       # Build Go gateway
make gateway-run         # Run Go gateway
make gateway-dev         # Go gateway with live reload
flutter run              # Mobile app
```

### Code Generation
```bash
make proto-gen           # Regenerate gRPC code from .proto files
make sync-db             # Apply migrations + generate Go SQLC code
```

### Testing
```bash
# Python
cd backend && pytest
cd backend && pytest tests/test_grpc.py

# Go
cd backend/gateway && go test ./...
cd backend/gateway && go test ./internal/service/...

# Flutter
cd mobile && flutter test
cd mobile && flutter test test/widget/

# Integration
make integration-test    # WebSocket client test
make grpc-test           # gRPC server test
```

## Coding Style & Naming Conventions

### Python
- PEP 8 with type hints
- Google-style docstrings
- Format with `black` (line length 120)
- Lint with `ruff`
- `snake_case` for variables/functions
- `PascalCase` for classes

### Go
- Standard Go idioms
- `gofmt` on save
- `camelCase` for variables/functions
- `PascalCase` for exported types

### Dart/Flutter
- Effective Dart conventions
- `flutter_lints` rules
- `camelCase` for fields/functions
- `PascalCase` for types and widgets
- Screens end with `_screen.dart`
- Use `const` constructors where possible

## Cross-Boundary Protocols

### gRPC Boundary (Proto → Go/Python)
**Source of Truth**: `proto/agent_service.proto`
- Never manually edit generated code in `gen/` directories
- Modify `.proto` file, then run `make proto-gen`
- Update both Go and Python implementations accordingly

### Database Boundary (SQL → Go/Python)
**Source of Truth**: `backend/gateway/internal/db/schema.sql`
- Modify via Alembic migrations: `cd backend && alembic revision -m "description"`
- Apply: `alembic upgrade head`
- If Go needs the data: Update `backend/gateway/internal/db/queries/` → `make sync-db`

## Configuration & Secrets
- Copy `backend/.env.example` to `backend/.env`
- Copy `backend/gateway/.env.example` to `backend/gateway/.env` if needed
- Never commit secrets or API keys

## Common Development Scenarios

### Adding a New AI Feature
1. Define in `proto/agent_service.proto`
2. `make proto-gen`
3. Implement in Python: `app/services/agent_grpc_service.py`
4. Call from Go: `backend/gateway/internal/agent/client.go`
5. Expose via WebSocket: `backend/gateway/internal/handler/websocket.go`

### Adding a Database Table
1. Create Alembic migration
2. `alembic upgrade head`
3. If Go needs it: Update queries → `make sync-db`

### Fixing Flutter Issues
```bash
cd mobile
flutter pub get
flutter analyze
./fix_final_const.sh  # If const errors
```

## Debugging Tips

### Logs
```bash
docker compose logs -f gateway
docker compose logs -f grpc-server
```

### WebSocket Issues
Check: `backend/gateway/internal/handler/websocket.go`

### gRPC Issues
- Use `grpcurl` to test
- Check: `backend/app/grpc_server.py`
- Verify: `backend/gateway/internal/agent/client.go`

### Database Issues
```bash
docker exec -it sparkle_db psql -U postgres -d sparkle
```

## Documentation
- **Primary**: `docs/深度技术讲解教案_完整版.md`
- **Architecture**: `docs/00_项目概览/02_技术架构.md`
- **API**: `docs/02_技术设计文档/03_API参考.md`
- **Knowledge Graph**: `docs/02_技术设计文档/02_知识星图系统设计_v3.0.md`

---

**Last Updated**: 2025-12-28
