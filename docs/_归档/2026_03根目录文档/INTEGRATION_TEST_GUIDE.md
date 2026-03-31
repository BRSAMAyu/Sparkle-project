# Integration Test Guide

This guide explains how to run the comprehensive integration test suite for the Sparkle system.

## Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Integration Test Suite                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Flutter Tests   │         │   Go Tests       │         │
│  │  (Dart)          │         │   (Go)           │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                             │                    │
│           │      WebSocket              │                    │
│           └──────────┬──────────────────┘                    │
│                      │                                       │
│           ┌──────────▼──────────┐                          │
│           │   Go Gateway        │                          │
│           │   (Port 8080)       │                          │
│           └──────────┬──────────┘                          │
│                      │ gRPC                                 │
│           ┌──────────▼──────────┐                          │
│           │  Python Engine      │                          │
│           │  (Port 50051)       │                          │
│           └──────────┬──────────┘                          │
│                      │                                      │
│           ┌──────────▼──────────┐                          │
│           │  PostgreSQL + Redis │                          │
│           └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Start Infrastructure

```bash
make dev-all
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- MinIO (port 9001)

### 2. Apply Database Migrations

```bash
cd backend
alembic upgrade head
```

### 3. Start Python gRPC Server

```bash
cd backend
make grpc-server
```

The server will start on port 50051.

### 4. Start Go Gateway

```bash
cd backend/gateway
make gateway-dev
```

The gateway will start on port 8080.

## Running Tests

### Python Integration Tests

#### Run All Integration Tests

```bash
cd backend
pytest tests/integration/ -v
```

#### Run Specific Test File

```bash
# WebSocket full-stack tests
pytest tests/integration/test_websocket_full_stack.py -v -s

# gRPC streaming tests
pytest tests/integration/test_grpc_streaming_integration.py -v -s

# Notification system tests
pytest tests/integration/test_notification_system_integration.py -v -s

# Cache consistency tests
pytest tests/integration/test_cache_consistency_integration.py -v -s

# Auth flow tests
pytest tests/integration/test_auth_flow_integration.py -v -s
```

#### Run with Coverage

```bash
pytest tests/integration/ \
  --cov=app \
  --cov-report=html \
  --cov-report=term \
  -v
```

### Go Integration Tests

#### Run All Go Tests

```bash
cd backend/gateway
go test ./... -v
```

#### Run Integration Tests Only

```bash
cd backend/gateway/internal/handler
go test -v -tags=integration *_test.go
```

#### Run Plan Review E2E Test

```bash
cd backend/gateway/internal/handler
go test -v -run=TestPlanReviewE2E plan_review_e2e_test.go
```

#### Run WebSocket Integration Test

```bash
cd backend/gateway/internal/handler
go test -v -run=TestWebSocket chat_integration_test.go
```

### Flutter Integration Tests

#### Run All Integration Tests

```bash
cd mobile
flutter test test/integration/ -v
```

#### Run Full-Stack E2E Tests

```bash
cd mobile
flutter test test/integration/full_stack_e2e_test.dart -v
```

#### Run with Environment Variables

```bash
cd mobile
flutter test test/integration/full_stack_e2e_test.dart \
  --dart-define=GATEWAY_HOST=localhost \
  --dart-define=GATEWAY_PORT=8080 \
  --dart-define=TEST_AUTH_TOKEN=your_test_token_here
```

## Test Categories

### 1. WebSocket Full-Stack Tests

**File:** `backend/tests/integration/test_websocket_full_stack.py`

Tests:
- Connection lifecycle
- Chat message flow
- Error handling
- Metadata and events
- Performance metrics

**Run:**
```bash
pytest tests/integration/test_websocket_full_stack.py -v -s
```

### 2. gRPC Streaming Integration Tests

**File:** `backend/tests/integration/test_grpc_streaming_integration.py`

Tests:
- StreamChat RPC
- Tool execution
- Chat modes
- Performance (TTFT, throughput)
- Concurrent requests

**Run:**
```bash
pytest tests/integration/test_grpc_streaming_integration.py -v -s
```

### 3. Notification System Tests

**File:** `backend/tests/integration/test_notification_system_integration.py`

Tests:
- State change notifications
- Settings update notifications
- Notification center API
- Notification analytics
- Multi-user notifications

**Run:**
```bash
pytest tests/integration/test_notification_system_integration.py -v -s
```

### 4. Cache Consistency Tests

**File:** `backend/tests/integration/test_cache_consistency_integration.py`

Tests:
- Redis cache operations
- Cross-layer consistency
- Cache invalidation strategies
- Performance comparisons
- Distributed coherency

**Run:**
```bash
pytest tests/integration/test_cache_consistency_integration.py -v -s
```

### 5. Authentication Flow Tests

**File:** `backend/tests/integration/test_auth_flow_integration.py`

Tests:
- JWT token generation/validation
- Password hashing
- WebSocket authentication
- User login flow
- Session management

**Run:**
```bash
pytest tests/integration/test_auth_flow_integration.py -v -s
```

### 6. Plan Review E2E Tests

**File:** `backend/gateway/internal/handler/plan_review_e2e_test.go`

Tests:
- Complete plan review workflow
- Plan review with issues
- Modification flow
- Rejection flow
- gRPC SubmitPlanReview

**Run:**
```bash
cd backend/gateway/internal/handler
go test -v -run=TestPlanReviewE2E
```

### 7. Flutter Full-Stack E2E Tests

**File:** `mobile/test/integration/full_stack_e2e_test.dart`

Tests:
- WebSocket connection
- Chat message flow
- Plan review workflow
- State change notifications
- Error handling
- Performance metrics
- Reconnection logic

**Run:**
```bash
cd mobile
flutter test test/integration/full_stack_e2e_test.dart -v
```

## Test Configuration

### Environment Variables

Create a `.env.test` file in the backend directory:

```bash
# Database
DATABASE_URL=postgresql://sparkle:test_password@localhost:5432/sparkle_test

# Redis
REDIS_URL=redis://localhost:6379/1

# gRPC
GRPC_HOST=localhost
GRPC_PORT=50051

# Gateway
GATEWAY_HOST=localhost
GATEWAY_PORT=8080

# JWT
SECRET_KEY=test_secret_key_for_integration_tests
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Test Users
TEST_USER_EMAIL=auth_test@example.com
TEST_USER_PASSWORD=test_password_123
```

### Flutter Test Configuration

Update `mobile/test/integration/full_stack_e2e_test.dart` or use command-line arguments:

```bash
flutter test test/integration/full_stack_e2e_test.dart \
  --dart-define=GATEWAY_HOST=localhost \
  --dart-define=GATEWAY_PORT=8080 \
  --dart-define=TEST_AUTH_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/integration-tests.yml`:

```yaml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  python-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_USER: sparkle
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: sparkle_test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run migrations
        run: |
          cd backend
          alembic upgrade head

      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration/ -v --cov=app

  go-integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_USER: sparkle
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: sparkle_test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      - name: Run Go integration tests
        run: |
          cd backend/gateway
          go test ./... -v -tags=integration

  flutter-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.16.0'

      - name: Run Flutter integration tests
        run: |
          cd mobile
          flutter test test/integration/ -v
```

## Troubleshooting

### Tests Fail to Connect

**Problem:** Tests fail with connection refused errors.

**Solution:** Ensure all services are running:
```bash
make dev-all              # Infrastructure
make grpc-server          # Python gRPC
make gateway-dev          # Go Gateway
```

### Database Migrations Fail

**Problem:** `alembic upgrade head` fails.

**Solution:** Check database connection and create test database:
```bash
createdb sparkle_test
export DATABASE_URL=postgresql://sparkle:password@localhost:5432/sparkle_test
alembic upgrade head
```

### WebSocket Tests Timeout

**Problem:** WebSocket tests timeout after 30 seconds.

**Solution:**
1. Check Gateway is running on port 8080
2. Check authentication token is valid
3. Increase timeout in test file if needed

### gRPC Tests Fail

**Problem:** gRPC tests fail with "connection refused".

**Solution:** Ensure Python gRPC server is running:
```bash
make grpc-server
```

### Flutter Tests Can't Find Backend

**Problem:** Flutter tests fail to connect to backend.

**Solution:** Use `--dart-define` to set correct host/port:
```bash
flutter test test/integration/ \
  --dart-define=GATEWAY_HOST=10.0.2.2 \
  --dart-define=GATEWAY_PORT=8080
```

## Best Practices

### 1. Test Isolation

Each test should:
- Create its own test data
- Clean up after itself
- Not depend on other tests

### 2. Test Speed

- Use pytest-xdist for parallel test execution:
  ```bash
  pytest tests/integration/ -n auto
  ```

- Mock external services when possible

### 3. Test Data

- Use fixtures for common test data
- Create a test database separate from development
- Use transaction rollbacks for cleanup

### 4. Assertions

- Use specific assertions (assertEqual, assertIn, etc.)
- Include helpful error messages
- Check both success and failure cases

### 5. Debugging Failed Tests

- Use `-v` flag for verbose output
- Use `-s` flag to see print statements
- Use `--pdb` to drop into debugger on failure

## Coverage Goals

Target coverage for integration tests:
- Critical paths: 100%
- Important features: 80%+
- Overall system: 60%+

View coverage report:
```bash
pytest tests/integration/ --cov=app --cov-report=html
open htmlcov/index.html
```

## Contributing

When adding new integration tests:

1. Follow existing test structure
2. Add fixtures for test data
3. Include documentation in docstrings
4. Update this guide with new test categories
5. Ensure tests are idempotent (can run multiple times)

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Go Testing Guide](https://golang.org/doc/tutorial/add-a-test)
- [Flutter Testing Guide](https://docs.flutter.dev/cookbook/testing)
- [WebSocket Testing Guide](https://websockets.readthedocs.io/)
- [gRPC Testing Guide](https://grpc.io/docs/languages/python/testing/)
