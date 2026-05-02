# CXP-02 Aurora L3 Core Session Flagship Flow Report

Date: 2026-05-02
Task: CXP-02 Aurora L3 Core Session Flagship Flow

## What Changed

- Added backend agenda metadata for the Core Session UI: estimated minutes, preview steps, interruption policy copy, and resume hint now travel with the session payload.
- Added a mobile agenda renderer in the Aurora Core Session sheet so users see the calibration path before the message exchange: enter session, explain conflict, confirm judgment, apply update, and return Aurora to background.
- Strengthened freeform correction closure. When the user says a correction like "不是没时间，是完全不会做", the session now records:
  - `current_blocker = skill_gap`
  - `policy_directive = diagnose_prerequisite_first`
  - `task_adjustment = create_prerequisite_micro_task`
- Added a focused unit test proving that the freeform correction changes state, policy, directive, and next-task behavior.

## User Impact

Before this slice, the L3 session already existed, but the user had to infer the structure from chat messages. Now the sheet feels like an explicit deep-calibration mode: it opens with an agenda, shows the pause/resume rule, accepts corrections, and closes with visible changes.

The key scenario now behaves correctly:

1. User enters a deep calibration because Aurora has guessed the blocker as task/time pressure.
2. User replies: "不是没时间，是完全不会做。"
3. Aurora keeps the correction as a freeform disconfirmation.
4. Closing the session produces concrete updates: future behavior should diagnose prerequisites first and create a smaller prerequisite task instead of pushing the original card.

## Acceptance Notes

- Clear beginning: session opening and agenda metadata are backend-authored and rendered in the sheet.
- Agenda: mobile now displays agenda items, preview, estimated duration, and active/done status.
- Interruption behavior: agenda includes the `answer_then_resume` policy and the sheet still supports pause/resume with persisted resume token.
- Completion and summary: closure result continues to render state patches, strategy changes, next changes, and "Aurora returned to background" copy.
- Freeform correction: skill-gap corrections now affect blocker state, policy directive, and task adjustment.
- Idle pause/resume: existing idle-pause and resume-token behavior remains covered by tests.

## Evidence

- `cd backend && pytest tests/unit/test_aurora_core_session_entry.py` -> 9 passed.
- `git diff --check -- backend/app/aurora/core_session.py backend/tests/unit/test_aurora_core_session_entry.py mobile/lib/features/aurora/data/models/aurora_core_session.dart mobile/lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart` -> passed.
- `cd mobile && flutter analyze lib/features/aurora/data/models/aurora_core_session.dart lib/features/aurora/presentation/widgets/aurora_core_session_sheet.dart` -> no errors or warnings, but exits non-zero because the existing files still report style-level infos such as `require_trailing_commas` and `prefer_expression_function_bodies`.

## Handoff

The next useful step is wiring these `policy_directive` and `task_adjustment` values into the downstream plan/task mutation pipeline so the session result can immediately propose or create the prerequisite micro-task. This slice records the contract-level result and visible summary; the cross-feature mutation should be handled in the task/plan execution slice.
