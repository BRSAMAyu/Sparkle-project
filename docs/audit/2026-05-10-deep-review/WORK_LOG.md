# Fix Work Log — 2026-05-10 Deep Review

**Status**: In Progress
**Approach**: Fix P0 → P1 → P2 → P3, verify before each fix, commit after each batch

---

## P0 Issues (7 total)

### P0-1: Prompt Injection — plan_review_service.py
- **Status**: Pending verification
- **File**: `backend/app/orchestration/plan_review_service.py:1240-1254`
- **Claim**: `_build_review_prompt` directly interpolates `user_message` and `plan.rationale` without sanitization

### P0-2: gRPC StreamChat error yield exception
- **Status**: Pending verification
- **File**: `backend/app/services/agent_grpc_service.py:397`
- **Claim**: yield in except handler can throw if gRPC context cancelled

### P0-3: JWT hardcoded fallback secret
- **Status**: Pending verification
- **File**: `backend/gateway/internal/config/config.go:678`
- **Claim**: Dev mode falls back to predictable JWT secret

### P0-4: Docker Compose gateway missing env vars
- **Status**: Pending verification
- **File**: `docker-compose.yml:437-488`
- **Claim**: Gateway container missing ENVIRONMENT, JWT_ALGORITHM, etc.

### P0-5: gRPC TLS variable ordering
- **Status**: Pending verification
- **File**: `backend/grpc_server.py:212 vs 226`
- **Claim**: _ca_cert_path referenced before defined

### P0-6: JWT token fallback to URL query param
- **Status**: Pending verification
- **File**: `mobile/lib/features/chat/data/services/websocket_chat_service_v2.dart:1696-1703`
- **Claim**: Falls back to token-in-URL when ticket fails

### P0-7: 749 hardcoded i18n strings
- **Status**: Pending verification
- **Files**: Across all feature modules
- **Claim**: Massive i18n violation using inline ternary instead of ARB

---

## P1 Issues (24 total)
- Tracking in progress

---

## P2 Issues (56 total)
- Tracking in progress

---

## P3 Issues (41 total)
- Tracking in progress

---

## Change Log

| Time | Action | Files Changed |
|------|--------|---------------|
| (start) | Work log created | - |
