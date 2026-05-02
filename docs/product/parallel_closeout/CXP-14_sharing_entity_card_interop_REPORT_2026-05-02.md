# CXP-14 Report — Sharing System And Entity Card Interop

## Goal
Make sharing a first-class cross-product protocol instead of a set of resource-specific shortcuts. Shared plans, tasks, achievements, knowledge nodes, seed content, vocabulary sets, and review results should preserve owner, visibility, preview, source receipt, adoption action, and availability semantics.

## Work Completed
- Extended backend entity-card share payloads with owner, visibility, preview, source receipt, adoption action, expiration/revocation, and availability fields.
- Updated community resource sharing so group/direct shares emit the richer protocol while preserving legacy `SharedResource` compatibility.
- Hardened Card Protocol adoption so revoked, expired, or private shares fail clearly before import.
- Added card share API response metadata for expiry and availability.
- Updated Flutter entity-card fallback parsing so share cards can route/adopt when available and hide adoption when a share is revoked or unavailable.

## User Experience Before / After
Before: sharing could render as a card, but the receiving user could not reliably know who owned it, whether it was adoptable, whether it had expired, or which product route should handle it.

After: a received share has a clear preview, permission/availability semantics, and a concrete adoption route. Revoked, expired, or private shares degrade gracefully instead of becoming confusing broken cards.

## Cross-System Links
- Backend card builders: `backend/app/tools/entity_cards.py`
- Community share API: `backend/app/api/v1/community.py`
- Card Protocol adoption: `backend/app/services/card_protocol/card_snapshot_service.py`
- Card share API schema: `backend/app/api/v1/cards.py`
- Flutter parser/actions: `mobile/lib/shared/utils/entity_card_payloads.dart`
- Parser tests: `mobile/test/shared/entity_card_payloads_test.dart`

## Verification
- Backend entity-card tests cover seven shareable resource types.
- Backend Card Protocol tests cover revoked, expired, and private share rejection.
- Flutter parser tests cover mobile adoption routing and revoked-share graceful degradation.
- Final integration will re-run the combined entity-card and card-protocol suites after all CXP branches are merged.

## Remaining Risks
- Adoption is still split between legacy shared-resource adoption and Card Protocol import. The final integrator should prefer Card Protocol for new surfaces and keep legacy compatibility only for existing routes.
- Some resource types may still need richer preview copy after product QA, but the protocol can carry the required fields.

## Commit
Branch: integrated through `codex/final-closeout-integration-2026-05-02`
Commit: included in integration baseline `ccf83242e`
