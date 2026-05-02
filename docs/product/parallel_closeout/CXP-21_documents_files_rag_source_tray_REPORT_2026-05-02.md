# CXP-21 Report — Documents, Files, RAG, And Source Tray

Date: 2026-05-02
Branch: `codex/CXP-21-documents-rag-source-tray`

## Goal

Make uploaded materials more trustworthy as answer context: cited sources must be visible, correctable, permission-bound, and honest when Sparkle answers without loaded source material.

## Work Completed

- Citation feedback now persists synchronously whenever a DB session is available, so explicit or implicit source corrections immediately update document quality scoring and retrieval demotion.
- Citation feedback events still publish to the event bus, but consumer-side duplicate persistence is skipped when the request path already stored the record.
- Citation feedback now validates file access before accepting feedback: owners and public files pass, group files require actual group membership and the configured `view_role`.
- Citation feedback now validates that a submitted `chunk_id` belongs to the cited file, preventing cross-file citation poisoning.
- Source tray retrieval plans now expose token budget metadata and skip auto-loaded materials that would exceed budget, while preserving user-explicit and directive-required loads.
- Source receipts now say whether an answer is `source_grounded` or `general_reasoning`, expose source uncertainty, and include a correction hint for source tray UI.

## User Experience Before / After

Before: a user could mark a bad citation, but with Redis available the correction could wait for an async consumer before retrieval quality changed. Group-visible files were also too broadly accepted by the citation feedback endpoint.

After: source corrections affect retrieval quality immediately, group file feedback respects group view permissions, and no-source answers can be labeled as general reasoning instead of looking source-backed.

## Cross-System Links

- Backend document API: `backend/app/api/v1/documents.py`
- Document feedback loop: `backend/app/services/document_service.py`
- Feedback event consumer: `backend/app/services/document_feedback_event_consumer.py`
- Source tray planning and receipts: `backend/app/signals/source_tray_integration.py`
- Focused regression tests: `backend/tests/test_document_feedback_loop.py`, `backend/tests/unit/spine/test_production_wiring.py`, `backend/tests/unit/test_signal_spine.py`

## Acceptance Evidence

- Upload path: existing document upload/status flow remains in `backend/app/api/v1/documents.py`; no upload contract change was made.
- Ask with citation: existing citation registration and implicit next-turn feedback tests still pass.
- Correct bad source: new synchronous persistence keeps negative feedback immediately available for quality scoring and GraphRAG reranking.
- Share/group material path: new group-file permission test proves citation feedback requires membership and sufficient group `view_role`.
- Permission failure path: private/non-member paths still fail closed; invalid or mismatched chunks now fail with 400/404.
- No-source failure path: source receipt now returns `answer_basis=general_reasoning` and `source_uncertainty=no_sources_available`.
- Cost/budget path: source tray auto-loading now reports budget used/remaining and skips auto sources that exceed the token budget.

## Verification

```bash
cd backend && pytest tests/test_document_feedback_loop.py
# 6 passed

cd backend && pytest tests/unit/spine/test_production_wiring.py -k "source_tray or source_receipt"
# 18 passed, 149 deselected
```

## Remaining Risks

- Mobile source tray rendering should consume the new `answer_basis`, `source_uncertainty`, and `correction_hint` fields in a follow-up UI pass.
- The task/knowledge creation-from-source paths already exist through document draft nodes and task document linking, but I did not broaden this patch into card-generation UI to avoid conflicting with parallel CXP mobile/card work.
- Group-file feedback currently validates view permission; if future product wants feedback only from users with download permission, CXP-25/final integration should tighten that policy explicitly.

## Commit

Branch: `codex/CXP-21-documents-rag-source-tray`
Commit hash: pending final commit.
