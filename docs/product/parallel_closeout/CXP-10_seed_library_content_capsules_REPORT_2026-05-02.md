# CXP-10 Seed Library And Content Capsules Report

Date: 2026-05-02
Agent: Codex CXP-10

## Outcome

Seed libraries now behave less like passive collections and more like reusable growth starters. A user can browse or search seeds using the correct backend wire values, adopt a seed library, and immediately see routeable next actions such as creating a plan, creating a task, creating a knowledge draft, starting review, asking Aurora to apply a template, or sharing the seed safely to community.

## What Changed

- Added `SeedAdoptionAction` to the seed-library API contract and attached `adoption_next_actions` to library, item, and subscription responses.
- Added backend action builders that derive concrete next actions from library category and item types:
  - `teaching_content` -> plan creation
  - `exercise` -> task creation
  - `knowledge` -> Galaxy draft / knowledge-node creation
  - `flashcard` -> review
  - `template` / `few_shot` -> Aurora/chat usage
  - all libraries -> community share with adopt permission
- Community adoption of shared `seed_library` and `seed_item` resources now returns the same adoption-action hints after creating the recipient-owned private copy.
- Fixed mobile seed-library API enum serialization. The app now sends `few_shot`, `teaching_content`, `reply_template`, `beginner`, etc. instead of Dart enum names like `fewShot`.
- Extended mobile seed models to parse adoption actions and render action chips on the seed detail screen.
- Wrapped seed-item share sheet calls in `unawaited()` to avoid discarded future analyzer noise.

## User Journeys

### Seed To Plan

Before: Adopting a seed mainly toggled a subscription. The user had to infer how to turn it into a plan.

After: A `teaching_content` seed exposes a `生成学习计划` action routed to `/plans/new?seed_library_id=...`. Exercise items in the same library expose `变成练习任务`, so the user can either plan the full seed or start from one concrete task.

### Seed To Community

Before: Seed sharing existed, but adoption did not communicate the safe next step after a recipient forked the content.

After: Shared seed libraries/items still create recipient-owned private copies, and the adoption response includes `adoption_next_actions`. Share metadata marks `permission=adopt` and `safe_share=true`, so the product can explain that the recipient acts on their copy rather than mutating the original.

## Acceptance Notes

- Browse/search/adopt flows are less brittle because enum filters and create/update payloads now match backend schema values.
- Adopting a seed produces concrete next actions in API responses and mobile detail UI.
- Seeds can be shared or linked to community safely through existing `seed_library` and `seed_item` shared-resource paths, with private-copy adoption preserved.

## Evidence

- `cd backend && pytest tests/unit/test_seed_library_stage22.py tests/unit/test_seed_library_service.py`
  - Result: 27 passed, 1 pre-existing AsyncMock runtime warning.
- `cd backend && ruff check app/schemas/seed_content.py app/services/seed_library_service.py app/api/v1/seed_libraries.py app/api/v1/community.py tests/unit/test_seed_library_stage22.py`
  - Result: all checks passed.
- `cd mobile && dart analyze lib/features/seed_library/data/models/seed_library_model.dart lib/features/seed_library/data/repositories/seed_library_repository.dart lib/features/seed_library/presentation/screens/seed_library_detail_screen.dart`
  - Result: exit 0; info-level style hints remain in the existing large detail screen.

## What The User Can Now Accomplish

The user no longer ends at "subscribed." A good seed now offers a visible next move: turn it into a plan, a task, a knowledge node, a review item, an Aurora reference, or a safe community share.
