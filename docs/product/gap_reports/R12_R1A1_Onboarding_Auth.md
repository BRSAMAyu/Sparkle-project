# R12 / R1A1 — Onboarding_Auth 二次深度审查
**Date**: 2026-05-07 (Simulated)
**Scope**: Onboarding + Auth
**Layers**: Flutter → Go Gateway → Python Engine → PostgreSQL / Redis
**Vision check**: The core onboarding and auth flows align with the vision but still lack some resilience (persistence) and accessibility (biometrics, semantics).

*Note: This investigation was interrupted due to turn limits. The findings below represent a partial trace focused on verifying R11 issues.*

---

## Summary
| Category | Count |
|----------|-------|
| P0 (must-fix before launch) | 0 |
| P1 (important gap, ship with plan) | 3 |
| P2 (nice to have, post-launch) | 2 |
| Verified working | 4 |

---

## R11 P0 验证
No P0 issues were reported in R11.

---

## P0 Findings (Must Fix Before Launch)
None found in the limited trace.

---

## P1 Findings (Important, Ship With Plan)

### P1-1: Onboarding data is not persisted locally
**File**: `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart`
**Lines**: N/A
**Problem**: User onboarding state is held entirely in memory. If the app is killed during onboarding, progress is lost.
**Evidence**: A search for `SharedPreferences` usage within the user presentation screens returned no matches, confirming the R11 finding that state is not saved incrementally.
**Expected**: Partial onboarding state should be saved to local storage on each step change to allow resuming.
**Fix recommendation**: Implement `SharedPreferences` to persist the state of the onboarding stepper after each step.

### P1-2: ModelingChatScreen lacks retry for initial stream
**File**: `mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart`
**Lines**: 57-67
**Problem**: The initial stream starts automatically in `initState`. If it fails due to network issues, there is no UI state or button to retry.
**Evidence**: A search for `_initialLoadFailed` or similar retry flags in the screen's code returned no results. The `_startModelingStream` is fired unconditionally.
**Expected**: If `_startModelingStream` fails initially, the UI should provide a retry button.
**Fix recommendation**: Add an error state flag and a retry button for the initial AI greeting.

### P1-3: Missing biometric authentication support
**File**: `mobile/lib/features/auth/`
**Lines**: N/A
**Problem**: Users cannot use Face ID or Touch ID to log in.
**Evidence**: A search for `local_auth` across the auth presentation screens returned no results.
**Expected**: Returning users should have the option to authenticate via biometrics.
**Fix recommendation**: Integrate the `local_auth` package and provide a biometric login option.

---

## P2 Findings (Post-Launch)

### P2-1: Lack of accessibility Semantics in Auth flow
**File**: `mobile/lib/features/auth/presentation/screens/`
**Lines**: N/A
**Problem**: The authentication screens lack explicit `Semantics` widgets to aid screen readers.
**Evidence**: A search for `Semantics` in the auth screens directory returned zero matches.
**Expected**: Interactive elements and forms should have appropriate semantic labels.
**Fix recommendation**: Add `Semantics` widgets to buttons, inputs, and toggle icons.

### P2-2: Basic password validation lacks strength indicator
**File**: `mobile/lib/features/auth/presentation/screens/register_screen.dart`
**Lines**: 209, 229
**Problem**: Password validation only checks for minimum length (6 characters) and matching fields.
**Evidence**: The register screen code shows basic length checks (`return l10n.passwordMinLength`) but no visual strength meter.
**Expected**: A visual password strength indicator should guide the user.
**Fix recommendation**: Add a password strength meter widget.

---

## Verified Working (Strengths)

### V-1: Auth Route Registration
- **Verification**: `mobile/lib/app/routes.dart` and `mobile/lib/features/auth/auth_routes.dart` correctly map `/login`, `/register`, `/forgot-password`, etc., to their respective screens with `SharedAxisTransitionType`.
- **Verdict**: PASS. GoRouter configuration is solid.

### V-2: Go Gateway JWT Refresh Logic
- **Verification**: `backend/gateway/internal/handler/auth.go` contains robust logic for token refresh (`createRefreshToken`, blacklist checking).
- **Verdict**: PASS.

### V-3: Social Auth Implementations
- **Verification**: `mobile/lib/core/services/social_auth_service.dart` initializes Google, Apple, and WeChat sign-in providers.
- **Verdict**: PASS.

### V-4: Python Auth Endpoints
- **Verification**: `backend/app/api/v1/auth.py` contains endpoints for `/auth/login`, `/auth/register`, and session revocation, integrating with `_issue_auth_tokens`.
- **Verdict**: PASS.

---

## Cross-Route Integration Issues
Investigation interrupted. Further trace required to map `/profile/onboarding` from Go Gateway proxy directly to Python engine endpoint.

---

## Code Quality Observations
The Flutter presentation layer maintains clean separation of UI and state, relying on Riverpod providers. Go Gateway handlers are well-tested as evidenced by corresponding `_test.go` files.