# Adaptive Intervention E2E Test Plan

## Objectives
- Validate end-to-end delivery within 1s (gateway → client).
- Verify template rendering and scaffolding updates.
- Ensure feedback and passive signals are recorded.

## Environment
- Backend: `http://localhost:8000`
- Gateway: `http://localhost:8080`
- Redis + PostgreSQL running
- Flutter app connected to gateway WebSocket

## Automated Scripts
- Quick sanity: `python backend/test_intervention_quick.py`
- Mock E2E: `python backend/test_intervention_mock_e2e.py`
- Full E2E:
  - `API_TOKEN=... API_BASE_URL=http://localhost:8080/api/v1 python backend/test_intervention_e2e.py`

## Manual Scenarios
1. **Idle Trigger**
   - Leave app idle >20s.
   - Expect `intervention_push` and toast overlay.
2. **Background → Foreground**
   - Background app for >20s, resume.
   - Expect WebSocket push + overlay.
3. **Distraction Pattern**
   - Switch apps 3+ times within 5 minutes.
   - Expect `distraction_recovery` intent.
4. **Feedback Loop**
   - Tap primary action.
   - Verify feedback recorded in backend.
5. **Gate Cooldown**
   - Trigger twice within 3 minutes.
   - Second trigger should be blocked.

## Success Criteria
- Push received and rendered in <1s (p95) with WebSocket connected.
- Template variables rendered correctly (no `{placeholder}` left).
- Feedback persists in `intervention_feedback` table.
- Scaffolding support level updates after 3 successes or 2 failures.

## Notes
- If WebSocket is disconnected, fallback uses local overlay + notification.
- Ensure `INTERNAL_API_KEY` and `GATEWAY_INTERNAL_URL` are configured.
