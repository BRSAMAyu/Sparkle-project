# Adaptive Intervention System Summary

## What Exists
- Backend: guardrails + adaptive intervention creation with FSM + templates.
- Gateway: WebSocket delivery with connection tracking and internal push API.
- Mobile: passive signal triggers, WebSocket handling, overlay UI, offline queue.

## Core Flow
1. Mobile triggers → `/interventions/request`.
2. Backend generates intent + renders template.
3. Backend pushes via gateway internal endpoint.
4. Mobile displays toast/card/modal.
5. Feedback queued and persisted.

## Key Components
- `backend/app/scaffolding/` for FSM + intent generation.
- `backend/app/services/template_*` for templates.
- `backend/gateway/internal/handler` for push + proxy.
- `mobile/lib/core/services/intervention_handler_service.dart` for client flow.

## Config
- `INTERNAL_API_KEY` shared between backend and gateway.
- `GATEWAY_INTERNAL_URL` used by backend to push.

## Tests
- `backend/test_intervention_quick.py`
- `backend/test_intervention_mock_e2e.py`
- `backend/test_intervention_e2e.py`
