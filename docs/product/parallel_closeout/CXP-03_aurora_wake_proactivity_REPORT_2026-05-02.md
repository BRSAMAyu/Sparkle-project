# CXP-03 Aurora Wake, Proactivity, And Notification Judgment Report

Date: 2026-05-02
Branch: codex/CXP-03-aurora-wake-proactivity

## What improved

Aurora wake decisions now carry user-understandable reasons instead of only an energy score. The wake payload can explain risk drift, missed plan drift, return after silence, useful recall, and calibration opportunities with evidence and a user control hint.

Wrong or ignored wakes now reduce future confidence. `AuroraWakePolicyService.record_wake_feedback()` stores 14-day feedback in Redis, applies a confidence multiplier to future wake scores, and suppresses a wake kind after repeated negative feedback for that kind.

Push and notification paths now expose the same respectfulness contract:

- Stage 18 push metadata includes `wake_type`, `proactive_reason`, `intrusiveness_level`, and `feedback_controls`.
- Existing dismissal counts still reduce or suppress future category pushes.
- Push action APIs accept negative judgments such as `wrong`, `not_useful`, `too_much`, and `bad_timing`; delivery normalizes these into dismissal behavior.
- Galaxy spaced-repetition reminders now include `wake_type=recall` and a specific `proactive_reason`.

## Required wake examples

Risk:
Input signals: `days_left=2`, `pass_probability=0.38`, `plan_completion_rate=0.32`.
Result: wake reason `risk` explains that a near deadline plus low pass/completion signals should produce a strategy reset, not generic encouragement.

Comeback:
Input signal: `hours_since_last_active=52`.
Result: wake reason `comeback` asks Aurora to resume context gently and offer a low-pressure restart.

Recall:
Input signals: `same_cause_error_streak=4`, quiz accuracy `[0.84, 0.57]`, topic `condition probability`.
Result: wake reason `recall` tells Aurora to return to the concrete stuck concept or review node.

Plan drift:
Input signals: `plan_completion_rate=0.32`, `expected_plan_completion_rate=0.78`.
Result: wake reason `plan_drift` focuses the response on replanning the smallest next step instead of pushing harder.

## Negative feedback behavior

Two `wrong` feedback events for `plan_drift` produce:

- Lower future `wake_score` through `feedback_profile.confidence_multiplier`.
- `negative_count_14d=2`.
- `plan_drift` added to `suppressed_kinds`.
- Future wake payloads omit `plan_drift` until feedback expires or positive evidence offsets it.

This means the user can now accomplish a real correction loop: "That wake was wrong" changes future proactive behavior instead of only becoming telemetry.

## Verification

Commands run:

```bash
cd backend && ruff check app/aurora/runtime_v1/wake_policy.py app/services/notification_center_service.py app/services/push_policy_compiler.py app/services/push_delivery_service.py app/schemas/unified_notification.py app/api/v1/push_interaction.py app/services/push_feedback_service.py tests/unit/test_aurora_runtime_wake_policy.py tests/unit/test_push_policy_compiler.py
pytest backend/tests/unit/test_aurora_runtime_wake_policy.py backend/tests/unit/test_push_policy_compiler.py backend/tests/unit/test_push_delivery_service.py -q
```

Result:

- Ruff: all checks passed.
- Pytest: 21 passed.

## Manual QA notes

Mobile notification center already renders push `proactive_reason`, category, dismissal, and disable-category controls. Manual QA should verify:

- A push card shows the reason under trigger evidence in light and dark themes.
- Tapping "Not this time" dismisses the push and reduces category intrusiveness on future previews.
- Tapping category disable uses the existing disable-category flow.
- A recall notification deep-links to chat with the review node prompt.
