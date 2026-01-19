# Adaptive Intervention Integration Guide

## Overview
This guide describes how to run the adaptive intervention pipeline end-to-end across backend, gateway, and mobile.

## Prerequisites
- PostgreSQL + Redis running (local Docker is fine).
- Go gateway (`backend/gateway`) and Python backend (`backend`) available.
- Flutter app running on a simulator/device.

## Configuration
Backend (`backend/.env`):
- `INTERNAL_API_KEY`: shared secret used by gateway internal endpoints.
- `GATEWAY_INTERNAL_URL`: gateway base URL, e.g. `http://localhost:8080`.

Gateway (`backend/gateway/.env`):
- `INTERNAL_API_KEY`: must match backend.
- `BACKEND_URL`: Python backend base URL, e.g. `http://localhost:8000`.

## Code Generation
- Go/Python: `make proto-gen-legacy` (or `make proto-gen` if buf is configured).
- Dart: `protoc --proto_path=proto --dart_out=grpc:mobile/lib/core/network/proto proto/websocket.proto`.

## Database
- Run migrations: `cd backend && alembic upgrade head`.
- If Go SQLC code is needed: `make sync-db`.

## Runtime Flow
1. Mobile triggers local signals → queues `/interventions/request` via SyncEngine.
2. Backend builds intent + template → writes intervention request row.
3. Backend calls gateway internal `/internal/interventions/push`.
4. Gateway pushes `intervention_push` over WebSocket.
5. Mobile shows toast/card/modal and records feedback via SyncEngine.

## Entry Points
- Mobile:
  - `InterventionHandlerService` listens for signals + WebSocket pushes.
  - `InterventionOverlayManager` renders overlays.
- Backend:
  - `POST /api/v1/interventions/request` creates adaptive interventions.
  - `POST /api/v1/interventions/requests/{id}/feedback` records feedback.
  - `POST /api/v1/interventions/passive-signals` records passive signals.
  - `POST /api/v1/interventions/outcomes` records outcomes.
- Gateway:
  - `POST /internal/interventions/push` pushes to connected clients.
  - `/api/v1/interventions/*` proxied to backend.

## Verification
- Quick sanity: `python backend/test_intervention_quick.py`.
- Mock E2E: `python backend/test_intervention_mock_e2e.py`.
- Full E2E: `API_TOKEN=... python backend/test_intervention_e2e.py`.

## Notes
- If `INTERNAL_API_KEY` or `GATEWAY_INTERNAL_URL` is missing, real-time delivery is skipped.
- Templates are loaded from `backend/config/intervention_templates.yaml`.
