# Cross-Layer Integration Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The cross-layer integration is well-architected with comprehensive proto definitions, consistent gRPC implementations, and thorough event bus infrastructure. All 18 RPC methods defined in `agent_service.proto` are implemented in both the Python gRPC server and Go client. Aurora kill switches are perfectly aligned between dev and prod compose files. However, several issues require attention: Phase 2e/2f/2g gRPC RPCs are implemented in Python but have no corresponding HTTP exposure in the Go gateway, the `glm_batch` Celery worker is missing from prod compose, and `celery_beat` is absent from dev compose. Additionally, the `community_service.proto` is correctly marked deprecated but its generated Go code path diverges from the other protos.

## Critical Issues (P0)

None found.

## High Issues (P1)

### P1-1: `glm_batch` Celery worker absent from `docker-compose.prod.yml`

The dev compose (`docker-compose.yml` line 333-376) defines a `celery_glm_batch_worker` service, but the prod compose (`docker-compose.prod.yml`) has no equivalent. GLM batch tasks queued to the `glm_batch` queue will never be consumed in production.

**Files**:
- `docker-compose.yml:333-376` — dev `celery_glm_batch_worker` defined
- `docker-compose.prod.yml` — no `glm_batch` worker

### P1-2: `celery_beat` missing from dev `docker-compose.yml`

The dev compose has no `celery_beat` service. The Makefile's `celery-up` target creates it ad-hoc via `docker run`, but the main `docker-compose.yml` has no declarative beat service. This means `docker compose up -d` will not start scheduled tasks in dev. Prod compose correctly defines `celery_beat`.

**Files**:
- `docker-compose.yml` — no `celery_beat` service
- `docker-compose.prod.yml:362-393` — `celery_beat` defined
- `Makefile:356-361` — ad-hoc beat container

### P1-3: Phase 2e/2f/2g RPCs not exposed via Go gateway HTTP handlers

The following RPCs are fully implemented in Python gRPC (`agent_grpc_service.py`) and wrapped in the Go client (`client.go`), but no Go gateway handler exposes them as HTTP endpoints:

- `SubmitReviewOverride`
- `SubmitReviewAppeal`
- `GetAppealStatus`
- `SubmitReviewFeedback`
- `RequestRegeneration`
- `GetFeedbackStatistics`
- `GetArbitrationQueue`
- `AssignArbitrationCase`
- `SubmitArbitrationDecision`
- `GetArbitrationQueueStats`

These are directly callable via gRPC from any internal service, but Flutter clients cannot reach them through the Go gateway's REST/WebSocket API. If these are admin-only features accessed through a separate admin tooling path, this is acceptable. If Flutter needs them, handler routes must be added.

**Files**:
- `backend/app/services/agent_grpc_service.py:1006-1783` — Python implementations
- `backend/gateway/internal/agent/client.go:440-570` — Go client wrappers
- `backend/gateway/internal/handler/` — no handler files for these RPCs

## Medium Issues (P2)

### P2-1: Generated Go code path inconsistency for `error_book.proto`

The `error_book.proto` generates to `gen/proto/error_book` while other protos use `gen/<package>/v1` (e.g., `gen/agent/v1`, `gen/galaxy/v1`, `gen/stt/v1`). The Go import path uses `gen/proto/error_book;errorbookv1` vs `gen/agent/v1;agentv1`. This inconsistency makes the codebase harder to navigate and breaks the established convention.

**Files**:
- `proto/error_book.proto:5` — `go_package = "...gen/proto/error_book;errorbookv1"`
- `proto/agent_service.proto:5` — `go_package = "...gen/agent/v1;agentv1"`

### P2-2: `community_service.proto` generated code likely stale

The `community_service.proto` is correctly marked `deprecated` at the service level (line 324) with a clear comment (lines 320-322) stating community features are served by REST/gateway CQRS. However, the proto file still exists with full message definitions, and no `gen/community/` directory was found in the Go gateway's generated code. This is correct behavior, but the proto file should eventually be archived or moved to a `deprecated/` directory to prevent confusion.

**Files**:
- `proto/community_service.proto:320-324` — deprecation notice

### P2-3: `STTService` proto has no Go gateway client or Python implementation

The `stt_service.proto` defines a bidirectional streaming `StreamSpeechToText` RPC, `TranscribeAudio`, and `EnhanceTranscript`. Generated Go code exists at `gen/stt/v1/`, but no corresponding Go client wrapper was found in `backend/gateway/internal/`, and no Python gRPC service implementation was found. This appears to be a forward-looking proto definition not yet implemented.

**Files**:
- `proto/stt_service.proto` — full service definition
- `backend/gateway/gen/stt/v1/` — generated Go code exists
- `backend/gateway/internal/agent/` — no STT client wrapper

### P2-4: Dev compose `sparkle_db` uses custom Dockerfile, prod uses plain `pgvector`

The dev compose builds a custom PostgreSQL image from `docker/pgvector-age.Dockerfile` (which adds Apache AGE for graph queries), while prod uses the plain `pgvector/pgvector:pg16` image without AGE. If the application uses AGE graph queries (which the CLAUDE.md and proto files suggest it does), the prod database will be missing the AGE extension.

**Files**:
- `docker-compose.yml:6-8` — `dockerfile: docker/pgvector-age.Dockerfile`
- `docker-compose.prod.yml:396-397` — `image: pgvector/pgvector:pg16`

### P2-5: Redis ACL in prod compose not present in dev compose

Prod compose defines per-service Redis ACLs (gateway, engine, celery users with restricted key patterns and command sets), while dev compose uses a single `REDIS_PASSWORD` with no ACL separation. This is expected for development convenience but means privilege escalation bugs won't be caught until prod.

**Files**:
- `docker-compose.prod.yml:441-448` — Redis ACL configuration
- `docker-compose.yml:60` — single password auth

### P2-6: No `user_state.proto` found despite Makefile references

The Makefile `proto-gen-legacy` target (line 268-272) generates code for `proto/user_state.proto`, but this file was not found in the proto directory. The buf-based `proto-gen` target does not reference it, suggesting this is a stale legacy reference.

**Files**:
- `Makefile:268-272` — references `proto/user_state.proto`

## Low Issues (P3)

### P3-1: REST API response format inconsistency across endpoints

The Aurora endpoints (`aurora.py`) return `dict[str, Any]` with varied envelope shapes. Some use `{"ok": True, ...}`, others return raw dicts. The cards API (`cards.py`) uses `{"success": True, "data": {...}}`. The signals API (`signals.py`) mixes both patterns. A consistent envelope (e.g., `{"success": bool, "data": ..., "error": ...}`) would improve client-side error handling.

**Files**:
- `backend/app/api/v1/aurora.py` — varied response shapes
- `backend/app/api/v1/cards.py` — `{"success": True, "data": ...}` pattern
- `backend/app/api/v1/signals.py` — mixed patterns

### P3-2: `Error.created_at` field naming inconsistency in `ErrorAnalysisResult`

The `ErrorAnalysisResult` proto message (error_book.proto:72-81) uses `ocr_text` as field 8 but the `ErrorRecord` message uses `created_at` and `updated_at` as timestamp fields. The `SimilarErrorSummary` uses `google.protobuf.Timestamp` for `created_at` while `ArbitrationCaseInfo` uses `string` for all timestamp fields (`created_at`, `assigned_at`, `resolved_at`). Mixing `Timestamp` and `string` for temporal fields across protos creates inconsistency.

**Files**:
- `proto/agent_service.proto:509-528` — `ArbitrationCaseInfo` uses `string` for timestamps
- `proto/error_book.proto:109` — `SimilarErrorSummary` uses `google.protobuf.Timestamp`

### P3-3: Large inlined Pydantic request models in `aurora.py`

The aurora endpoint file defines 13+ Pydantic request/response models inline rather than in a separate `schemas.py` module. While functionally correct, this makes the file (1233 lines) harder to maintain. Other API files like `cards.py` follow the same pattern.

**Files**:
- `backend/app/api/v1/aurora.py:34-138` — inline model definitions

### P3-4: Event bus consumer ordering not guaranteed

The event bus uses Redis Streams with consumer groups but does not guarantee ordering within a stream. For events where order matters (e.g., `TaskStarted` before `TaskCompleted`), the lack of partition key means events from different users may interleave, and events from the same user may be processed out of order under load. This is acceptable for the current use case but worth documenting.

**Files**:
- `backend/app/core/event_bus.py:1016-1071` — publish method
- `backend/app/core/event_bus.py:1219-1273` — consume loop

## Positive Findings

1. **Proto contract completeness**: All 6 proto files are well-documented with field numbers that follow clean sequences, proper use of `reserved` for retired fields, and good use of `oneof` for discriminated unions (`ChatRequest.input`, `ChatResponse.content`).

2. **gRPC streaming robustness**: The Python `StreamChat` implementation handles errors gracefully, always yields at least one response (even on error), manages DB session lifecycle correctly, and implements session ID fallback logic. The Go client has retry with exponential backoff, reconnection logic with rate-limiting, circuit breaker protection, and Prometheus metrics on every RPC call.

3. **Event bus infrastructure**: The Redis Streams event bus is production-grade with DLQ support (dual persistence to both Redis DLQ stream and PostgreSQL `EventBusDLQEntry`), idempotent consumption, configurable retry with exponential backoff, auto-restart on consumer failure, stale message reclamation via `XAUTOCLAIM`, and comprehensive Prometheus metrics (`EVENT_BUS_CONSUMER_FAILURE_TOTAL`, `EVENT_BUS_DLQ_DEPTH`, `EVENT_BUS_PUBLISH_RETRIES_TOTAL`).

4. **Aurora switch alignment**: All 28 Aurora tri-state kill switches are perfectly aligned between dev and prod compose files. The same set of switches with the same `live` default appears in both `docker-compose.yml` and `docker-compose.prod.yml` for both `sparkle_api` and `sparkle_agent` services.

5. **Security**: The Go gRPC client properly injects `x-internal-api-key`, `user-id`, and `x-trace-id` metadata. The Python gRPC server validates authorization metadata and has admin-only endpoint guards. TLS/mTLS is configurable but optional for local dev.

6. **Docker health checks**: Every service in both compose files has appropriate health checks with proper `start_period`, `interval`, and `retries`. The gRPC health check uses a TCP socket test rather than relying on a separate HTTP endpoint.

7. **Proto evolution safety**: The `websocket.proto` properly uses `reserved` for retired fields (field 6 "timestamp" renamed to field 7 `event_time`). The `agent_service.proto` similarly reserves field 13 and field 1 of the `Error` message. This prevents wire-format breakage.

8. **Monitoring stack**: Both compose files include a complete observability stack: Tempo (traces), Prometheus (metrics), Loki (logs), Promtail (log shipping), Grafana (visualization), and Alertmanager with environment-variable-driven configuration.

9. **Production hardening**: Prod compose uses network isolation (`edge` + `app` with `internal: true`), per-service Redis ACLs, MinIO RBAC with per-bucket access keys, blue/green gateway deployments, non-root container users, and resource limits via YAML anchors.

10. **Input validation**: REST endpoints use Pydantic models with field constraints (e.g., `min_length`, `ge`, `le`, `pattern` regexes). The signals API validates `feedback_type` against a whitelist and `action_type` length bounds.

## Files Audited

### Proto definitions
- `proto/agent_service.proto` (783 lines)
- `proto/galaxy_service.proto` (194 lines)
- `proto/community_service.proto` (422 lines)
- `proto/error_book.proto` (216 lines)
- `proto/stt_service.proto` (230 lines)
- `proto/websocket.proto` (108 lines)

### Python gRPC implementation
- `backend/app/services/agent_grpc_service.py` (1784 lines)

### Go gRPC client
- `backend/gateway/internal/agent/client.go` (582 lines)

### REST API endpoints
- `backend/app/api/v1/aurora.py` (1233 lines)
- `backend/app/api/v1/cards.py` (479 lines)
- `backend/app/api/v1/experience.py` (591 lines)
- `backend/app/api/v1/signals.py` (338 lines)

### Event bus
- `backend/app/core/event_bus.py` (1495 lines)

### Celery
- `backend/app/core/celery_tasks.py` (200+ lines, partial read)

### Docker compose
- `docker-compose.yml` (545 lines)
- `docker-compose.prod.yml` (759 lines)

### Build
- `Makefile` (566 lines)

### Environment
- `.env.example` (260 lines)

### Generated code (verified existence)
- `backend/gateway/gen/agent/v1/agent_service.pb.go`
- `backend/gateway/gen/agent/v1/agent_service_grpc.pb.go`
- `backend/gateway/gen/galaxy/v1/`
- `backend/gateway/gen/stt/v1/`
- `backend/gateway/gen/proto/error_book/`
- `backend/app/gen/agent/v1/`

### Go gateway handlers (verified)
- `backend/gateway/internal/handler/websocket_proxy.go` (765 lines)
- `backend/gateway/internal/handler/chat_orchestrator.go`
- `backend/gateway/internal/handler/chat_orchestrator_feedback.go`
- `backend/gateway/internal/handler/chat_orchestrator_chatflow.go`
- `backend/gateway/internal/handler/health.go`
- `backend/gateway/internal/handler/error_book.go`
