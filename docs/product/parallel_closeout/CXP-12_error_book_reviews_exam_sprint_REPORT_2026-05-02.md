# CXP-12 Report — Error Book, Reviews, And Exam Sprint

## Goal
Make mistakes become visible strategy: related wrong answers should cluster into review cards, failed reviews should change mastery and plan pressure, and exam sprint diagnostics should remain connected to weak prerequisites and pass probability.

## Work Completed
- Added clustered review-card API support for the Error Book:
  - `GET /errors/review-cards`
  - response schemas for clustered cards, actions, task-card payloads, priority, due counts, mastery averages, root cause, node links, and representative errors.
- Added backend clustering logic over real `ErrorRecord` data:
  - groups by affected knowledge node first;
  - falls back to error type/root cause/chapter when no node is linked;
  - emits review steps tailored to concept gaps, calculation/method errors, careless/time-pressure errors, and generic patterns.
- Connected failed review feedback to strategy adjustment:
  - fixed `forgotten` review performance so it applies the intended mastery penalty;
  - forgotten/fuzzy review feedback now evaluates impacted plans through the existing error-pressure path.
- Updated the existing error-loop test expectation so deprecated `GalaxyService.handle_error_created` remains blocked instead of applying a duplicate mastery penalty.

## User Experience Before / After
Before: the user could record or review a wrong answer, but repeated mistakes were mostly individual rows. A failed review updated scheduling/mastery but did not reliably create plan pressure.

After: the reviews module can show "these mistakes are the same pattern" cards with a concrete reason, repair steps, linked Galaxy node, source error IDs, and a task-card payload. If the user forgets again, mastery drops and impacted plans can be evaluated immediately.

Wrong-answer journey now supported:
wrong answer -> error analysis/linking -> clustered review card -> review feedback -> mastery update -> plan-health pressure evaluation.

## Cross-System Links
- Backend API: `backend/app/api/v1/error_book.py`
- Backend schemas: `backend/app/schemas/error_book.py`
- Error Book service: `backend/app/services/error_book_service.py`
- Mastery and plan pressure bridge: `backend/app/services/error_book_mastery_sync_service.py`
- Tests: `backend/tests/services/test_error_loop.py`
- Exam sprint diagnostic API was re-run to verify the existing pass-probability and bottleneck round trip still works.

## Verification
- `cd backend && pytest tests/services/test_error_loop.py -q`
  - 3 passed
- `cd backend && pytest tests/unit/test_exam_sprint_diagnose_api.py -q`
  - 1 passed

No screenshots were taken; this task was backend/API focused.

## Remaining Risks
- Mobile can consume the new `review-cards` endpoint, but I did not add the UI surface in this pass because the repo already had broad in-flight mobile changes.
- The `create_task` action currently returns a task-card payload for the client/router to materialize; a later integration task should decide whether task creation should be server-side and idempotent.
- Clustering is deterministic and explainable, but still heuristic. A future pass could blend embeddings once production vector availability is confirmed.

## Commit
Branch: `codex/CXP-12-error-book-reviews-exam-sprint`

Commit hash: not created in this pass because the worktree already contained extensive unrelated in-flight modifications before CXP-12 started.
