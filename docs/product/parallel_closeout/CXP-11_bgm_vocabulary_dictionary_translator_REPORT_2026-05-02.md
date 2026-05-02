# CXP-11 Report - BGM, Vocabulary, Dictionary, And Translator Tools

Date: 2026-05-02
Intended branch: codex/CXP-11-learning-tools
Workspace note: this shared worktree changed active branches externally during execution, so the final status should be checked before committing.

## User Outcome

Saving a translated or looked-up word now exposes a visible learning loop instead of silently creating an isolated wordbook row. The response tells the client where the word appears next: vocabulary card, review schedule, optional knowledge graph card, optional learning asset, and task recommendation eligibility.

## What Changed

- Added `learning_loop` metadata to vocabulary responses so saved words show review schedule, knowledge-card link, learning-asset link, and recommendation hint.
- Extended `POST /api/v1/vocabulary/wordbook` with optional `save_to_knowledge`, `create_learning_asset`, language/domain/source fields, and recoverable warnings when downstream graph or asset creation fails.
- Added translation response actions for `save_to_vocabulary` and `create_knowledge_card`, plus retry/fallback metadata on translation failure.
- Added equivalent widget actions to the translation tool response so chat cards can route directly into save flows.
- Let task recommendations include low-mastery translation nodes, so a newly saved vocabulary graph node can become a review task instead of being filtered out at mastery `0`.
- Scoped vocabulary review recording by current user in the API path.

## Acceptance Flows

Lookup:
`GET /api/v1/vocabulary/lookup?word=...` still resolves MDX, packaged fallback, DB mirror, then LLM fallback with visible source metadata.

Translate:
`POST /api/v1/translation/translate` now returns action metadata for saving the translation as vocabulary or as a knowledge card.

Save:
`POST /api/v1/vocabulary/wordbook` saves the word, creates an active learning asset by default, can create a draft graph node with `save_to_knowledge=true`, and returns `learning_loop`.

Review:
Saved words keep `next_review_at`; `GET /api/v1/vocabulary/wordbook/review` returns the same `learning_loop` payload so the review surface can explain why the word is due.

Graph Link:
When graph creation succeeds, the wordbook row stores a `learning_loop` tag with the knowledge node id and response metadata returns `knowledge_card.created=true`.

## Verification

- `python3 -m py_compile app/api/v1/vocabulary.py app/api/v1/translation.py app/services/vocabulary_service.py app/services/task_recommendation_service.py app/tools/translation_tool.py`
- `pytest tests/services/test_vocabulary_service.py tests/services/test_translation_signals.py`
- Result: 23 passed.

## Notes For Integration

- The BGM surface was inspected as part of routing/import discovery, but the safe CXP-11 implementation landed on the learning-tool data loop because that was the acceptance-critical gap.
- The workspace had many unrelated dirty files before this task; this report covers only the CXP-11-scoped files changed here.
