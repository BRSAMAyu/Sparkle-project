# chat_service.py

- Stage 34 disposition: archived as orphan service.
- Reason: no runtime import path remained in `backend/app/**`; active chat flow is owned by the orchestrator / gateway stack.
- Replacement: `backend/app/orchestration/` and `backend/app/services/agent_grpc_service.py`.
- Removal earliest: after Stage 35 confirms no legacy fallback path depends on it.
