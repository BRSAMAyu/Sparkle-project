# CXP-05 Memory, Profile, And Return Context Report

Date: 2026-05-02
Branch: `codex/CXP-05-memory-return-context`

## What changed

- Expanded memory ranking beyond evidence/freshness/correction to include query relevance, confidence, importance, and goal/task/plan linkage.
- Passed the active user query into context-pack ranking so return context favors memories connected to what the user is trying to resume.
- Marked surfaced goals and episodic memories with `claim_status`, `source_label`, `rank_factors`, and correction actions that route to existing memory inspection/correction endpoints.
- Added `metadata.memory_claims` so important claims can be inspected and corrected without treating prompt-injected memory as hidden system truth.
- Added the missing shared `time_utils` module already referenced by memory services so the branch is self-contained in a clean checkout.

## User impact

Returning users should now hear the memory that matters to the resumed goal, not merely the newest or highest-evidence item. A confirmed TCP sprint blocker can outrank a newer but unrelated inferred music preference when the user returns to a networking sprint. Inferred claims are explicitly labeled as AI inference and carry correction actions, so Aurora can sound personal without pretending guesses are facts.

## Return scenarios

- 30min: short-gap resume remains quiet unless context is needed; ranking can still bias toward the active query if a prompt is built.
- 8h: same-day return can surface high-confidence, goal-linked memories before unrelated recent details.
- 2d: medium return favors active plan/task-linked memories and keeps inferred claims visibly tentative.
- 4d: longer comeback context can still draw from relevant episodic memories, but corrected or denied claims are penalized and exposed with correction affordances.

## Evidence

- `pytest tests/unit/test_context_ranker.py tests/unit/test_context_pack_ranking.py -q` passed, 5 tests.
- `ruff check app/core/time_utils.py app/core/context_ranker.py app/core/context_pack.py tests/unit/test_context_ranker.py tests/unit/test_context_pack_ranking.py` passed.
- `python3 -m py_compile app/core/time_utils.py app/core/context_ranker.py app/core/context_pack.py` passed.
- Wider memory API tests were blocked in the clean worktree by missing generated `app.gen` modules before test execution.

## Residual risk

- Mobile surfaces need to render the new `correction_actions` and `memory_claims` affordances where context-pack metadata is exposed. Backend payloads now provide the contract, but this lane did not edit Flutter UI.
