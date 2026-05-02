# CXP-06 Report — AI Conversation And Card Protocol

## Mission

Make AI conversation cards behave like real product objects rather than decorative text. This slice focused on schema validation, backend card builders, and mobile parser/routing coverage for the card types that were still most likely to fall through as inert generic widgets.

## What Changed

- Added `validate_entity_card()` in `backend/app/tools/entity_cards.py` so generated cards can be checked for required schema fields, primary actions, route-bearing open actions, share payload completeness, and malformed secondary actions.
- Added backend builders for review, vocabulary, and seed cards:
  - `build_review_entity_card()`
  - `build_vocabulary_entity_card()`
  - `build_seed_entity_card()`
- Extended the mobile entity-card fallback parser in `mobile/lib/shared/utils/entity_card_payloads.dart` so legacy/raw chat widget payloads for `review`, `vocabulary`, `seed`, and `shared_resource` become routable `EntityCardPayload`s with primary actions, share metadata, and adoption actions where appropriate.
- Added focused backend and Flutter tests for the core CXP-06 card journeys.

## Acceptance Evidence

### Backend Schema Validation

Validated all core conversation journeys through `validate_entity_card()`:

- Task card: opens `/tasks/{id}` and exposes share metadata.
- Plan card: opens `/plans/{id}` and exposes share metadata.
- Knowledge card: opens Galaxy with node context and exposes knowledge share metadata.
- Share card: opens the shared resource and exposes an adoption action.
- Review card: opens `/review?mode=today...` with plan/review context.
- Vocabulary card: opens `/tools/vocabulary_lookup?word=...` and links to `/tools/wordbook`.
- Seed card: opens `/seed-libraries/{id}` and exposes adopt/share actions.

Negative validation now catches an inert `open_detail` card with no route.

Command:

```bash
cd backend && uv run pytest tests/unit/test_entity_cards.py
```

Result: `7 passed`.

### Mobile Route / Action Path

Verified the mobile parser creates concrete route/action paths for the previously weak card types:

- Review fallback payload produces `/review?mode=today...`.
- Vocabulary fallback payload produces `/tools/vocabulary_lookup?word=derive` plus secondary `/tools/wordbook`.
- Seed fallback payload produces `/seed-libraries/seed-1` plus `adopt_resource`.
- Shared resource fallback payload routes a shared plan to `/plans/plan-1` plus `adopt_shared_resource`.

Command:

```bash
cd mobile && flutter test test/shared/entity_card_payloads_test.dart
```

Result: `9 passed`.

## User-Visible Improvement

When Aurora or chat proposes a review, vocabulary item, seed, shared plan/task, knowledge node, plan, or task, the card now has a clear primary destination and recoverable metadata on both backend and mobile. A user can tap into the next product surface instead of seeing a pretty but dead suggestion.

## Handoff Notes

- `backend/app/tools/entity_cards.py` had overlapping uncommitted edits in the shared worktree around share-card owner/visibility/adoption metadata. I preserved those changes and added CXP-06 validation/builders on top.
- The generic mobile `ActionCard` still has richer bespoke layouts only for task list and plan cards. Review/vocabulary/seed are now routable through `EntityCardPayload`, but a future UI-polish pass could add dedicated compact card layouts.
