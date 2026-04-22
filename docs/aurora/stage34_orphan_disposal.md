# Stage 34 Orphan Disposal

## Kept

- `backend/app/services/permission_service.py`
  - Kept as the single surviving permission helper.
  - Stage 34 wire-on: registration/auth path now records default community member permissions in audit and journey metadata.

## Archived

- `backend/app/services/chat_service.py`
- `backend/app/services/content_moderation_service.py`
- `backend/app/services/file_cascade_service.py`
- `backend/app/services/llm_service_secure.py`
- `backend/app/services/multi_plan_state_manager.py`
- `backend/app/services/push_router_service.py`
- `backend/app/services/galaxy/conflict_resolver.py`
- `backend/app/services/galaxy/permission_service.py`

Each archived file moved via `git mv` into `backend/app/_deprecated/stage34/` and keeps a colocated `REASON.md` for recovery traceability.
