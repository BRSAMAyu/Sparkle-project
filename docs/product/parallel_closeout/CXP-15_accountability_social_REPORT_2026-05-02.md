# CXP-15 Report — Accountability, Partners, Squads, And Goal Mates

## Goal
Make accountability reminders feel like a chosen partnership cadence rather than pressure spam, while preserving the existing invite, accept, check-in, milestone, privacy, and Aurora social-signal flows.

## Work Completed
- Tightened the scheduled accountability reminder task so check-in reminders honor each partnership's `check_in_days` cadence.
- Added local-day reminder windows based on the user's push timezone instead of a single UTC day boundary.
- Added suppression for user notification preferences: disabled system notifications, minimal/silent notification levels, accountability reminder type opt-outs, and quiet hours.
- Added same-local-day duplicate suppression so the morning and evening Celery jobs do not create two reminders for the same partnership/user/day.
- Added structured skip counts for cadence, preference, and duplicate suppression, making the background job observable.

## User Experience Before / After
Before: a user who set a two-day partner cadence could still be reminded every scheduled run, and the 9:00 plus 21:00 jobs could both produce reminders.

After: Sparkle waits until the user's chosen cadence is due, respects quiet or disabled notification preferences, and only reminds once per local day. The user feels that the partner agreement has boundaries and a memory of the chosen rhythm.

Invite flow: existing `/accountability/request` and partner notification path remains intact.

Accept flow: existing `/accountability/{partnership_id}/respond` path remains intact.

Check-in flow: existing `/accountability/{partnership_id}/checkin` path still publishes check-in, achievement, and policy events.

Missed check-in flow: the reminder job still routes prolonged misses into `PolicySchedulerService` after the cadence gate allows a reminder.

Milestone celebration: existing progress and achievement evaluation tasks remain intact; reminders now reduce noise around those celebrations.

Privacy toggle and Aurora use: `SocialSignalBridge` already respects explicit `use_social_signals=false` and sanitizes partner check-ins to role labels only. The adjacent regression test verifies no partner name, username, or check-in content leaks into Aurora context.

## Cross-System Links
- Backend scheduled task: `backend/app/tasks/accountability_tasks.py`
- Notifications/preferences: `Notification`, `NotificationPreferences`, `AccountabilityNotificationType`
- Aurora/social context safety: existing `SocialSignalBridge` tests were rerun
- Tests: `backend/tests/unit/test_accountability_reminder_cadence.py`

## Verification
- `cd backend && pytest tests/unit/test_accountability_reminder_cadence.py -q` — 3 passed
- `cd backend && pytest tests/unit/test_accountability_api_helpers.py tests/unit/test_social_signal_relevance.py -q` — 7 passed

## Remaining Risks
- Mobile does not yet expose a dedicated per-partnership reminder preference screen beyond the existing cadence and global notification preference plumbing.
- The scheduled task still sends database/websocket notifications directly; a future pass could route all accountability push behavior through the unified push policy compiler.
- Group/squad recommendation surfaces were inspected but not changed in this slice; this patch closes the highest-risk spam/cadence gap.

## Commit
Branch: `codex/CXP-15-accountability-social`

Commit hash: pending local commit
