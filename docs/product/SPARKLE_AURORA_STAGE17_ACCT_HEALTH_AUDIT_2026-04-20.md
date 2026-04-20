# SPARKLE Aurora Stage 17 Accountability Health Audit (2026-04-20)

> Status: Stage 17 MVP audit
> Conclusion: legacy WS9 accountability stack remains dependency-heavy, so Stage 17 ships a thin front-door MVP over inferred commitments only.

## 1. Import / Consumer / Write Surface Review

1. `backend/app/api/v1/accountability.py` is a full partnership system with invitations, timeline, nudges, leaderboard, and achievement dependencies.
2. `backend/app/tasks/accountability_tasks.py` and `accountability_notification_service.py` wire the legacy stack into scheduled notifications and downstream messaging.
3. `accountability_achievement_service.py` and related community models make the legacy path depend on achievements, partnerships, and social graph state.

## 2. Why `SPARKLE_WS9_ACCOUNTABILITY_ENABLED` Stays Default-OFF

The legacy stack is designed around partner check-ins, reminders, and achievement unlocks. It is not a safe thin read surface for Stage 17 because enabling it implicitly activates subsystems that are outside the current workstream boundary.

## 3. Dependency Availability Snapshot

1. Push / reminders: available in repo, but intentionally out of Stage 17 scope
2. Achievement hooks: available, but unnecessary for inferred commitment surfacing
3. Daily check-in / partnership graph: available, but not required for Stage 17 MVP

## 4. Stage 17 Decision

Stage 17 uses `AccountabilityMvpService` plus `/memory/accountability/pending` to surface overdue inferred commitments.

It does not activate:

1. legacy partner invitations
2. nudges or push
3. achievements
4. red-dot or reminder logic
