# CXP-22 Report — Calendar, Schedule, And Time Awareness

Date: 2026-05-02
Branch: `codex/CXP-22-calendar-schedule-time`

## What Improved

- Smart scheduling now respects the requested task duration. A 120-minute task only receives slots with at least 120 free minutes, instead of being fit into a generic one-hour window.
- Smart scheduling now treats calendar events that overlap the target day as blockers, including events that start the previous night and continue into today.
- Explicit duration feedback such as `too_long` / "this took longer than you think" now becomes an immediate `time_overrun` plan-health signal. That makes the adaptive replanner adjust future duration buffers without waiting for several historical overruns.

## User Impact

The user can trust suggested time slots more: long tasks are not squeezed into impossible windows, and overnight or cross-boundary calendar events are no longer ignored. When the user corrects Sparkle's estimate, Sparkle treats it as schedule evidence, not just a complaint, and the plan can reserve more realistic time next.

## Acceptance Evidence

- Today planning: existing calendar context still drives generated daily task specs into safe time blocks.
- Deadline crunch: existing calendar conflict service still flags tight exam/deadline days.
- Missed task / reschedule: existing adaptive compression and calendar-safe slot selection remain covered by planning tests.
- Duration correction: new test proves `too_long` feedback forces a `time_overrun` adjustment report.
- Calendar conflict path: new smart schedule test proves overlapping calendar events block suggested slots.

## Verification

```bash
cd backend && pytest tests/unit/test_smart_schedule_service.py tests/unit/test_adaptive_replanner_evolution.py tests/unit/test_calendar_service.py tests/orchestration/test_planning_workflow.py -k "smart_schedule or duration_feedback or calendar or adaptive or compressed"
# 13 passed, 32 deselected
```

## Files Touched

- `backend/app/services/smart_schedule_service.py`
- `backend/app/orchestration/adaptive_replanner.py`
- `backend/tests/unit/test_smart_schedule_service.py`
- `backend/tests/unit/test_adaptive_replanner_evolution.py`

## Handoff Notes

- The workspace already contained a large set of unrelated modified files before this task. I kept this slice to schedule/time files plus the required report.
- Mobile surfaces already show task duration/deadline chips and calendar-driven daily briefing copy; I did not broaden UI changes in this pass to avoid conflicting with parallel mobile polish work.
