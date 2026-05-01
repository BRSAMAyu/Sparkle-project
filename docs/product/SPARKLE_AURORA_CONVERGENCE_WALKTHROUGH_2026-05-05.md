# Aurora Convergence C4 E2E Walkthrough Report

> Created: 2026-05-01  
> Target artifact: 2026-05-05 per C4 plan  
> Source plan: `docs/product/SPARKLE_AURORA_CONVERGENCE_PLAN_2026-05-01.md`  
> Scope: Report-only walkthrough. No product code was changed.

## Executive Summary

Status: **PASS-WIP, not final signoff**

The backend Aurora convergence paths are in good shape for the scoped journeys covered here: Core Session entry, memory naturalization, calendar context, checkpoint personalization, social relevance, tool history, adaptive replanning, comeback context, daily startup, and correction feedback all passed targeted tests.

The frontend has strong partial coverage: the Core Session sheet, memory receipt, comeback banner, contextual correction bar, runtime follow-up, time-context bar, tool feedback, and chat golden snapshots pass. The main experience blocker is the layered `StatusAwarenessBar`: Layer 2 correction and Layer 3 detail expansion currently fail widget checks because the tap target does not reliably hit the intended control. That creates a real risk of a user dead end in the "Aurora noticed something -> I correct it or inspect it" journey.

Two release blockers remain before C4 can become final acceptance:

1. **C3 backend golden snapshot framework is missing**: `backend/tests/golden/` does not exist, so the C4 dependency "Wave C complete" is not actually satisfied.
2. **Manual simulator/device screenshots were not captured in this pass**: existing chat golden PNGs provide visual regression evidence, but not live end-to-end journey screenshots.

## Evidence Run

| Check | Result | Notes |
|---|---:|---|
| `python3 scripts/check_aurora_config_consistency.py` | PASS | Aurora settings/env/compose defaults are aligned. |
| `cd backend && pytest ... -q` scoped Aurora suite | PASS | 76 passed, 14 warnings. Warnings are AsyncMock pipeline warnings in correction tests. |
| `cd mobile && flutter test ... -r compact` scoped Aurora widgets | FAIL | 21 tests reached; 19 passed, 2 failed in `status_awareness_bar_layers_test.dart`. |
| `cd mobile && flutter test test/goldens/chat_golden_test.dart -r compact` | PASS | 10 chat golden snapshots passed. |
| `cd backend && pytest tests/golden -q` | BLOCKED | `tests/golden` directory not found. |
| `cd mobile && flutter analyze --no-fatal-infos` | FAIL/NOISY | 10,477 issues, mostly info-level and includes vendored `third_party_plugins`. |
| Targeted Flutter analyze for C4 widgets/tests | WARN | 93 issues; 1 warning in test fake notifier, rest info-style lint. |

Backend scoped command:

```bash
cd backend && pytest \
  tests/unit/test_aurora_core_session_entry.py \
  tests/unit/test_aurora_memory_naturalization.py \
  tests/unit/test_calendar_service.py \
  tests/unit/test_checkpoint_b1_personalization.py \
  tests/unit/test_social_signal_relevance.py \
  tests/unit/services/test_tool_history_service.py \
  tests/unit/test_adaptive_replanner_stage34.py \
  tests/aurora/test_comeback_context.py \
  tests/aurora/test_daily_startup_message.py \
  tests/unit/test_t33_predicted_reply_correction.py -q
```

Flutter scoped command:

```bash
cd mobile && flutter test \
  test/features/aurora/presentation/ \
  test/features/chat/presentation/widgets/contextual_correction_bar_test.dart \
  test/features/chat/presentation/widgets/memory_reference_receipt_test.dart \
  test/features/chat/presentation/widgets/comeback_banner_test.dart \
  test/features/chat/presentation/widgets/status_awareness_bar_layers_test.dart \
  test/features/chat/presentation/widgets/status_awareness_bar_time_context_test.dart \
  test/features/chat/presentation/widgets/aurora_runtime_follow_up_test.dart \
  test/features/tools/ -r compact
```

## Screenshot And Visual Evidence

Live simulator screenshots: **not captured in this pass**.

Static visual evidence from passing golden snapshots:

| Snapshot | Path |
|---|---|
| Chat, light | `mobile/test/goldens/chat_light_5_messages.png` |
| Chat, dark | `mobile/test/goldens/chat_dark_5_messages.png` |
| Chat, mobile | `mobile/test/goldens/chat_mobile.png` |
| Chat, tablet | `mobile/test/goldens/chat_tablet.png` |
| Empty chat | `mobile/test/goldens/chat_empty.png` |
| Plan review card | `mobile/test/goldens/chat_with_plan_review.png` |
| Typing state | `mobile/test/goldens/chat_typing.png` |
| Error state | `mobile/test/goldens/chat_error.png` |

These snapshots are useful regression evidence, but they do not replace the required C4 manual journey screenshots. The next C4 pass should capture one screenshot per journey at the key Aurora moment.

## Seven Journey Walkthroughs

### 1. New User -> Goal -> Plan -> First Task -> First Reflection

Score: **3/5**  
Status: **PASS-WIP**

Observed support:
- Configuration defaults are aligned and Aurora runtime is enabled by default.
- Existing E2E checklist covers the onboarding/goal/plan/task/reflection path.
- Final acceptance ledger records broad backend and Flutter coverage for the growth loop.

Breakpoints:
- This pass did not run a fresh-install simulator onboarding.
- No live screenshot evidence for onboarding, plan approval, first task completion, or reflection.
- The C4-specific Aurora "receipt" experience is not proven on this journey.

Priority: **P1 manual evidence gap**

### 2. User Gets Stuck -> Aurora Detects -> Core Session -> Plan Adjusts -> Recovery

Score: **4/5 backend, 3/5 frontend**  
Status: **PASS-WIP**

Observed support:
- `test_aurora_core_session_entry.py` passed.
- `test_adaptive_replanner_stage34.py` passed.
- Core Session sheet tests passed for status entry, checkpoint entry, task-stuck entry, freeform correction, pause/resume, expired restart, and closure results.
- Task-stuck UI path has test coverage.

Breakpoints:
- Layered `StatusAwarenessBar` expansion fails in two widget tests. A user may not reliably reach correction or deep-detail controls from the status band.
- No live task execution sequence was performed to prove "three stuck tasks -> Aurora intervention -> plan adjustment" end to end.

Priority: **P1 interaction blocker**

### 3. User Corrects Aurora -> Correction Chip -> Rejudgment -> Next Round Validation

Score: **3/5**  
Status: **REOPEN**

Observed support:
- `test_t33_predicted_reply_correction.py` passed.
- `contextual_correction_bar_test.dart` passed and confirms natural chip text without leaking semantic tokens.
- Core Session freeform correction path passed.

Breakpoints:
- `status_awareness_bar_layers_test.dart` fails when tapping the "time not enough" correction option; expected correction receipt text does not appear.
- The failed tap warning says the derived tap point would not hit-test on the displayed text, suggesting the interactive surface or test target is not robust.
- Next-turn rejudgment is covered at backend level but not proven from this exact status-band correction UI path.

Priority: **P1 product trust risk**

### 4. Cross-Session Memory -> Reopen -> Aurora Naturally References Context

Score: **4/5**  
Status: **PASS-WIP**

Observed support:
- `test_aurora_memory_naturalization.py` passed.
- `test_comeback_context.py` passed.
- `memory_reference_receipt_test.dart` passed.
- `comeback_banner_test.dart` passed.

Breakpoints:
- This pass did not close/reopen the real app.
- No screenshot evidence for the comeback banner plus memory receipt in a live chat thread.
- User correction of a memory receipt is covered by component behavior, not a full chat round-trip.

Priority: **P2 manual proof gap**

### 5. Community Interaction -> Partner Activity -> Aurora Mentions Gently

Score: **3/5**  
Status: **PASS-WIP**

Observed support:
- `test_social_signal_relevance.py` passed.
- Context receipt infrastructure exists for social/tool/memory receipt display.
- Final acceptance ledger marks social/task/share paths as broadly wired.

Breakpoints:
- No live community feed, partner activity, or accountability flow was run.
- No screenshot proving Aurora mentions partner activity without privacy leakage.
- Cross-user privacy should be manually rechecked before release because this journey is socially sensitive.

Priority: **P1 manual privacy/UX proof gap**

### 6. Tool Use -> Aurora Notices -> Next Chat Uses Context

Score: **3/5**  
Status: **PASS-WIP**

Observed support:
- `test_tool_history_service.py` passed.
- `tool_context_effect_feedback_test.dart` passed, including undoing a saved tool event.
- Tool history repository and tool feedback widgets are present in the worktree.

Breakpoints:
- This pass did not run breathing/calculator/translator in the app and then send a follow-up chat.
- The "Aurora naturally references the just-used tool" behavior is proven by service/widget slices, not by one complete user path.
- No live receipt screenshot was captured.

Priority: **P2 manual journey proof gap**

### 7. Checkpoint Return -> Personalized Debrief -> Follow-Up -> Action

Score: **4/5**  
Status: **PASS-WIP**

Observed support:
- `test_checkpoint_b1_personalization.py` passed.
- `test_daily_startup_message.py` passed.
- `test_comeback_context.py` passed.
- `aurora_runtime_follow_up_test.dart` passed.
- Core Session checkpoint entry test passed.

Breakpoints:
- No real delayed-return app session was performed.
- No screenshot proving personalized debrief, follow-up card, and action CTA in sequence.
- Backend golden snapshots are missing, so future prompt drift for this journey is not guarded.

Priority: **P1 C3 dependency + manual proof gap**

## Experience Breakpoints

| ID | Priority | Area | Finding | Evidence |
|---|---:|---|---|---|
| C4-001 | P0 | Golden tests | Backend golden snapshot framework is absent, so Wave C dependency C3 is not complete. | `pytest tests/golden -q` -> directory not found. |
| C4-002 | P1 | Status band UX | Layer 2 correction chip does not reliably record/show correction from the widget path. | `status_awareness_bar_layers_test.dart`, "layer 2 shows evidence and correction choices" failed. |
| C4-003 | P1 | Status band UX | Layer 3 "View Aurora details" does not reveal the four deep cards in the widget path. | `status_awareness_bar_layers_test.dart`, "layer 3 renders four collapsible deep cards" failed. |
| C4-004 | P1 | Manual evidence | The seven journeys were traced through code/tests/docs, but not run on a simulator/device with screenshots. | No live screenshots captured in this pass. |
| C4-005 | P2 | Test reliability | Correction backend suite passes but emits AsyncMock pipeline warnings. | 14 warnings in `test_t33_predicted_reply_correction.py`. |
| C4-006 | P2 | Flutter hygiene | Targeted C4 analyze has one warning and many style infos; broad analyzer includes vendored plugin noise. | Targeted analyze: 93 issues, 1 warning. Broad analyze: 10,477 issues. |
| C4-007 | P2 | i18n debt | Final ledger still tracks remaining hardcoded Chinese strings outside the already converted files. | `SPARKLE_FINAL_ACCEPTANCE_LEDGER_2026-05-01.md`, section 6. |

## Fix Priority Suggestions

1. **P0: Finish C3 before claiming C4 final**  
   Add `backend/tests/golden/`, text snapshot fixtures, drift detector, banned-token checks, and CI/update flow. Re-run `pytest tests/golden -q`.

2. **P1: Repair `StatusAwarenessBar` expanded interaction reliability**  
   Make correction/detail controls tappable by stable button/key/semantics targets, not only visible text. Re-run `status_awareness_bar_layers_test.dart` until Layer 2 and Layer 3 pass.

3. **P1: Run one live simulator C4 pass with screenshots**  
   Capture the seven journey screenshots at the point where Aurora observes, explains, remembers, or adjusts. Add those image paths to this report.

4. **P2: Tighten analyzer scope**  
   Exclude vendored `third_party_plugins` from normal app analyze gates or run a repo-approved scoped analyzer target so C4 does not drown in external plugin style output.

5. **P2: Clean targeted C4 warnings**  
   Fix the fake notifier `dispose()` must-call-super warning in the test, then address the highest-signal C4 widget infos opportunistically.

## C4 Acceptance Checklist

| Requirement | Status | Notes |
|---|---|---|
| 7 core journeys traced | DONE | Traced via current docs, code, and targeted tests. |
| Each journey scored | DONE | Scores included above. |
| Experience breakpoints recorded and classified | DONE | See C4-001 through C4-007. |
| Walkthrough report delivered | DONE | This file. |
| Screenshots included | PARTIAL | Existing chat goldens linked; live journey screenshots still missing. |
| Code untouched | DONE | This C4 pass only adds the report. |

## Final C4 Decision

Do not mark Aurora Convergence C4 as final release acceptance yet.

Mark it **PASS-WIP** for report delivery and backend/frontend scoped evidence, with **P0 reopen on C3 golden tests** and **P1 reopen on StatusAwarenessBar expanded interactions**. After those two are fixed, rerun this walkthrough on a simulator/device and attach the seven journey screenshots.
