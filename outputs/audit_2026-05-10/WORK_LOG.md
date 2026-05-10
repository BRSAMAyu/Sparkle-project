# Audit Fix Work Log — 2026-05-10

## Status Legend
- [ ] Not started
- [~] In progress / verifying
- [x] Done
- [-] Skipped (not real issue / already fixed / out of scope)

---

## Phase 1: P0 Security + Data Integrity

### 1. GetChatHistory missing user_id filter (Gateway P0-05/D-03/E-02)
- Status: [~] Verifying
- File: `backend/gateway/internal/db/query.sql:37-41`
- Analysis: SQL only filters by session_id, not user_id. Any auth'd user who knows session_id can read another's chat.
- Fix plan: Add `AND user_id = $3` to query, update Go caller to pass user_id
- Commit:

### 2. Telemetry POST without auth (Gateway P0-04/A-11)
- Status: [~] Verifying
- File: `backend/gateway/internal/handler/proxy_routes.go:728-735`
- Analysis: POST routes registered before authMiddleware
- Fix plan: Move authMiddleware before POST routes
- Commit:

### 3. achievementtype enum duplicate (Gateway P0-01/A-01)
- Status: [~] Verifying
- File: `backend/gateway/internal/db/schema.sql:122-139`
- Analysis: Both 'planning' and 'PLANNING' in enum
- Fix plan: Remove lowercase 'planning', add migration
- Commit:

### 4. panic() in randomString (Gateway P0-03/A-03)
- Status: [~] Verifying
- File: `backend/gateway/internal/handler/auth.go:142`
- Analysis: panic crashes entire process on crypto/rand failure
- Fix plan: Return error instead of panic
- Commit:

### 5. Null Redis crash in PlanReviewService (Backend P0-01)
- Status: [~] Verifying
- File: `backend/app/orchestration/plan_review_service.py:2429,2446`
- Analysis: self.redis.incr() when redis is None
- Fix plan: Add null guard at top of both methods
- Commit:

### 6. collaboration_node state mutation (Backend P0-03/P1-08)
- Status: [~] Verifying
- File: `backend/app/agents/graph/nodes/collaboration.py:851-893`
- Analysis: Directly mutates state dict instead of returning delta
- Fix plan: Refactor to return delta dicts
- Commit:

### 7. Reflection loop guard broken (My P0-04)
- Status: [~] Verifying
- Files: `standard_workflow.py:3162-3167`, `statechart_engine.py:375-404`
- Analysis: WorkflowState has no review_context, reflection_round always 0
- Fix plan: Read from context_data["review_context"]
- Commit:

### 8. LLMService HTTP pool leak (Backend P0-02/P1-07)
- Status: [~] Verifying
- File: `backend/app/services/llm_service.py:1497-1509`
- Analysis: New provider on every get_llm_service() call
- Fix plan: Cache by role
- Commit:

### 9. Backend Chinese hardcoded prompts (Cross-cutting P0)
- Status: [~] Verifying
- Files: `collaboration.py:622-803`, `plan_review_service.py:659-1079`
- Analysis: All collaboration mode prompts hardcoded Chinese
- Fix plan: Thread user_locale through request path, make prompts bilingual
- Commit:

### 10. Goroutine leak in auth blacklist (Gateway P0-02/A-02)
- Status: [~] Verifying
- File: `backend/gateway/internal/middleware/auth.go:67-80`
- Analysis: Fire-and-forget goroutine with no shutdown
- Fix plan: Add stopCh, Stop() method
- Commit:

---

## Phase 1: P0 Frontend

### 11. LearningPathScreen scaffold/nav/l10n (Frontend P0 ISSUE-022/023/003/047/048)
- Status: [~] Verifying
- File: `mobile/lib/features/insights/presentation/screens/learning_path_screen.dart`
- Analysis: Raw Scaffold, Navigator.pop, hardcoded English title
- Fix plan: Use SparklePageScaffold, context.pop(), ARB l10n
- Commit:

### 12. Router error page hardcoded English (Frontend P0 ISSUE-002)
- Status: [~] Verifying
- File: `mobile/lib/app/routes.dart:73,80,85`
- Fix plan: Use ARB keys for error page strings
- Commit:

### 13. Voice input accessibility labels (Frontend P0 ISSUE-005/026)
- Status: [~] Verifying
- File: `mobile/lib/features/chat/presentation/widgets/voice_input_button.dart:304`
- Fix plan: Add ARB keys for voice input labels
- Commit:

### 14. Static S. accessor locale mismatch (Frontend P0 ISSUE-016)
- Status: [~] Verifying
- File: `mobile/lib/features/galaxy/presentation/widgets/node_detail_sheet.dart:500-511`
- Fix plan: Change _relativeTime to accept BuildContext/AppLocalizations
- Commit:

### 15. 1,685 inline isChinese patterns (Frontend P0 ISSUE-001)
- Status: [ ] Deferred — too large for single session, will fix most visible ones
- Note: Will address high-visibility instances in P1 phase

---

## Phase 2: P1 Backend

### 16. Empty delegates returns no messages (Backend P1-01)
- Status: [ ] Pending
- File: `collaboration.py:743-749`

### 17. Fire-and-forget tasks (Backend P1-02)
- Status: [ ] Pending
- File: `plan_review_service.py:1934-1942`

### 18. Planning graph singleton race condition (Backend P1-03)
- Status: [ ] Pending
- File: `workflow.py:327-340`

### 19. collaboration_index state confusion (Backend P1-04)
- Status: [ ] Pending
- File: `workflow.py:312-323`

### 20. DB session leak in seed examples (Backend P1-05)
- Status: [ ] Pending
- File: `llm_service.py:1627-1659`

### 21. Checkpointer falls back to MemorySaver (Backend P1-06)
- Status: [ ] Pending
- File: `workflow.py:158-167`

### 22. EventBus Redis reconnection thrashing (Backend P1-09)
- Status: [ ] Pending
- File: `event_bus.py:934-938`

### 23. Cross-review same model (Backend P1-10/My P1-B)
- Status: [ ] Pending
- File: `plan_review_service.py:1067-1098`

### 24. Latin-1 doubles checkpoint storage (Backend P1-11)
- Status: [ ] Pending
- File: `langgraph_redis_checkpointer.py:74`

### 25. PlanReviewService singleton without Redis (Backend P1-12)
- Status: [ ] Pending
- File: `plan_review_service.py:2555`

---

## Phase 2: P1 Gateway

### 26. session_id validation (Gateway P1 A-05)
- Status: [ ] Pending

### 27. Stale gRPC context after reconnect (Gateway P1 A-06)
- Status: [ ] Pending

### 28. Missing header forwarding (Gateway P1 A-08)
- Status: [ ] Pending

### 29. Unsafe type assertions in rate limiter (Gateway P1 A-09)
- Status: [ ] Pending

### 30. GetRecentSessionsFromDB missing deleted_at (Gateway P1 B-02)
- Status: [ ] Pending

### 31. chat_messages.content no length limit (Gateway P1 B-01)
- Status: [ ] Pending

### 32. Verify post_likes unique index (Gateway P1 B-03)
- Status: [ ] Pending

### 33. DLQ no TTL (Gateway P1 F-01)
- Status: [ ] Pending

### 34. Retry buffer not bounded (Gateway P1 E-01)
- Status: [ ] Pending

---

## Phase 3: P1 Frontend

### 35-53. Frontend P1 issues (ISSUE-004 through ISSUE-048)
- Status: [ ] Pending

---

## Phase 4: P2 All Layers

### 54+. All P2 issues
- Status: [ ] Pending
