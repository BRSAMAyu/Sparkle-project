# CXP-13 Community Feed And Social Learning Report

Date: 2026-05-02
Branch: `codex/CXP-13-community-social-learning`

## What Changed

- Fixed mobile feed scope switching so returning from `My Squad`, `Goal Mates`, or `Following` back to `Global Feed` truly clears the backend `scope` query instead of silently reusing the previous scope.
- Added short per-tab scope descriptions in the community header so users can distinguish global, squad, goal-mate, and following semantics before reading the feed.
- Hardened group shared-resource listing:
  - non-members now get `403` and cannot enumerate shared cards/resources by group id;
  - resources shared by users in either direction of a block relationship are filtered out;
  - shared resources whose underlying legacy object was soft-deleted are skipped.
- Added route-level integration coverage for non-member resource access, blocked sharer filtering, and soft-deleted payload filtering.

## User Impact

The user now gets a community feed that behaves like the tab they selected. Global is public, squad is group-related without expanding friend-only visibility, goal mates are accountability partners, and following is accepted friends.

Shared resources feel safer: a user outside a group cannot peek at resources by guessing an id, and blocked or deleted content does not remain visible through old share records.

## Acceptance Coverage

- Feed tabs have distinct semantics: fixed mobile scope reset and added visible descriptions.
- Shared cards render and route correctly: existing shared-resource entity-card response remains intact while access filtering now happens before rendering.
- Blocked/private/deleted content never leaks: added resource-list membership, block, and soft-delete guards plus tests.

## Evidence

- `backend/.venv/bin/python -m pytest backend/tests/integration/test_community_integration.py -q` -> 11 passed, 2 skipped.
- `flutter analyze lib/features/community/presentation/providers/community_providers.dart lib/features/community/presentation/screens/community_screen.dart` -> no issues found.
- `backend/.venv/bin/python -m py_compile backend/app/services/collaboration_service.py backend/app/api/v1/community.py backend/tests/integration/test_community_integration.py` -> passed.

## Handoff Notes

- I did not add screenshots because this slice changed lightweight feed header copy/state rather than a new visual flow.
- A broader follow-up should add end-to-end mobile tests for adopting each shared card type from the feed/resource surfaces.
