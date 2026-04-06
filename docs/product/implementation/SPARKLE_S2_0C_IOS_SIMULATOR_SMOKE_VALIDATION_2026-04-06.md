# Sparkle S2-0C iOS Simulator Smoke Validation

> Date: 2026-04-06  
> Status: Completed  
> Stage: `S2-0 Runnable Golden Path Bring-Up`  
> Pack: `S2-0C Emulator/Simulator Smoke Validation`

---

## 0. Purpose

This note records whether the chosen Stage 2 simulator path is merely runnable once, or repeatable enough to trust as the current local alpha bring-up path.

---

## 1. Validated Target

Validated device target:

- simulator: `iPhone 16e`
- id: `79461B43-C730-47C4-9994-10CA7C5546BD`
- OS runtime: iOS simulator path detected by Flutter on 2026-04-06

Validated smoke:

```bash
cd /Users/brsama/code/GitHub/Sparkle-project/mobile
flutter test integration_test/app_test.dart -d 79461B43-C730-47C4-9994-10CA7C5546BD -r compact
```

This smoke verifies:

- iOS build success
- guest entry
- dashboard shell load
- core-shell tab navigation
- chat history sheet open/close behavior

---

## 2. Validation Method

After the stack was already green, the simulator smoke was run three consecutive times on the same live stack.

Validation window:

- 2026-04-06 10:54:00 CST to 2026-04-06 10:55:52 CST

Log files:

- `/tmp/s2_0c_ios_smoke_run_1.log`
- `/tmp/s2_0c_ios_smoke_run_2.log`
- `/tmp/s2_0c_ios_smoke_run_3.log`

---

## 3. Results

### Consecutive run summary

1. Run 1: pass
   - duration observed from test output: about 42s
2. Run 2: pass
   - duration observed from test output: about 39s
3. Run 3: pass
   - duration observed from test output: about 39s

### Aggregate result

- pass rate in this validation batch: `3 / 3`
- consecutive pass rate in this validation batch: `100%`

---

## 4. Recurring Observations

### Shutdown behavior

All three runs ended cleanly with:

- WebSocket disconnect
- service disposal
- `All tests passed!`

---

## 5. What S2-0C Now Proves

S2-0C is complete enough to support Stage 2 progression because:

1. the chosen simulator target is real and repeatable
2. the shell smoke is not a one-off pass
3. the main guest-entry/core-shell path currently survives repeated local validation
4. startup uncertainty is low enough to move on to the north-star walkthrough stage

---

## 6. Remaining Risks

1. the simulator smoke validates shell viability, not the full north-star product loop
2. this does not yet prove first Sparkle response quality in a real conversational journey
3. this does not yet prove visible adaptation quality after feedback

---

## 7. Exit Assessment

Against the S2-0C goal, this pack is complete:

- one chosen simulator path was used
- the real smoke test was executed repeatedly
- repeatability was measured
- recurring warnings were captured

Recommended next pack:

> `S2-1A North-Star Walkthrough Setup`
