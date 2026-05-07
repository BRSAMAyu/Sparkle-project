# R13 / R1A1 -- Onboarding + Auth Deep Audit

**Date**: 2026-05-07
**Scope**: Registration, login, onboarding, modeling chat, self-model, token lifecycle
**Layers**: Flutter -> Go Gateway -> Python Engine -> PostgreSQL / Redis

---

## Summary

| Category | Count |
|----------|-------|
| P0 (must-fix) | 1 |
| P1 (important) | 5 |
| P2 (nice-to-have) | 4 |
| Verified working | 14 |

---

## P0 Findings

### P0-1: Persona onboarding has NO skip button -- user cannot bypass without killing app

**File**: `mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart:18-427`
**Problem**: The `PersonaOnboardingScreen` (5-step stepper for learning goals, style, study time, knowledge level, response preferences) has no skip or cancel button. The `InteractiveOnboardingScreen` before it has a visible skip button, but the router redirect at `routes.dart:133-139` sends authenticated non-guest users who haven't completed onboarding to `/onboarding/persona` -- and this screen offers no escape. If the user wants to skip, they must force-quit the app.

The stepper at line 72-106 only has Continue/Previous buttons. The AppBar has no back/close action because it uses the default `AppBar(title: Text(l10n.personaGuide))`.

**Evidence**: 
```dart
// persona_onboarding_screen.dart:63-106
child: SparklePageScaffold(
  role: SparklePageRole.settings,
  appBar: AppBar(
    title: Text(l10n.personaGuide),
  ),
  // No leading/back button, no skip action
  child: ... Stepper(
    controlsBuilder: (context, details) {
      // Only has "Complete" and "Previous Step" buttons
      return Row(children: [
        SparkleButton(label: isLast ? l10n.personaComplete : l10n.personaNextStep, ...),
        if (_currentStep > 0) SparkleButton(label: l10n.personaPreviousStep, ...),
      ]);
    },
  ),
)
```

Meanwhile the router redirect blocks access to `/home`:
```dart
// routes.dart:133-139
if (isAuthenticated && !isGuestUser && !onboardingCompleted
    && !isOnPersonaOnboarding && !isOnModelingChat) {
  return UserRoutes.personaOnboarding;
}
```

**Fix**: Add a skip/cancel action to `PersonaOnboardingScreen` AppBar, or a "Skip for now" button. On skip, set `onboardingCompletedProvider` to `true` and navigate to `/home`. This matches the pattern in `InteractiveOnboardingScreen` which has `_skipAll()`.

---

## P1 Findings

### P1-1: Interactive onboarding step data is NOT independently persisted -- crash loses progress

**File**: `mobile/lib/features/onboarding/presentation/screens/interactive_onboarding_screen.dart:63-76`
**Problem**: The `_restorePage()` method (line 63) restores only the current page index from SharedPreferences. It does NOT restore the permission choices (notifications, microphone). If the app crashes on page 5 and user returns, they land on page 5 but their previously-granted permissions are not reflected -- the UI shows them as not-enabled, even though the OS-level permissions were granted. This creates a confusing UX where the toggle says "Enable" but the OS already granted permission.

More importantly, the onboarding page index is persisted but the actual step content is purely display-only (feature intros + permissions). The real data collection happens in `PersonaOnboardingScreen` which has NO persistence at all (lines 29-40: all state is in-memory `_goalController`, `_goalType`, `_learningStyle`, etc.).

**Evidence**:
```dart
// interactive_onboarding_screen.dart:63-76 -- only page index saved
Future<void> _restorePage() async {
  final prefs = await SharedPreferences.getInstance();
  final saved = prefs.getInt(_kOnboardingPageKey);
  if (saved != null && saved > 0 && saved < _totalPages && mounted) {
    _currentPage = saved;
    _pageController.jumpToPage(saved);
  }
}
```

```dart
// persona_onboarding_screen.dart:29-40 -- ALL state is ephemeral
String _goalType = 'exam';
String _learningStyle = 'balanced';
String _knowledgeLevel = 'beginner';
double _studyMinutes = 60;
double _depthPreference = 0.5;
double _curiosityPreference = 0.5;
```

**Fix**: For `InteractiveOnboardingScreen`, `_loadPermissionStatuses()` already re-reads OS permission state, so this is mostly cosmetic. For `PersonaOnboardingScreen`, persist step data to SharedPreferences after each step and restore on `initState`.

### P1-2: Login password sent in cleartext over HTTP if base URL is misconfigured

**File**: `mobile/lib/core/network/api_interceptor.dart:96-119`
**Problem**: The `AuthInterceptor.onRequest` attaches the JWT token via Bearer header but does not verify that the connection is HTTPS. The base URL from `ApiConstants.baseUrl` could be HTTP in dev/staging. When `ApiConstants.baseUrl` is `http://` (non-HTTPS), the password is sent in plaintext during login. The SSL pinning in `http_client_pinning.dart` only verifies certificate fingerprints, not that HTTPS is used.

This is mitigated by: (a) the app should always use HTTPS in production, (b) the `AuthInterceptor` handles Bearer tokens, not the password itself -- the password is in the POST body which follows the same Dio instance's base URL. However, there is no enforcement that prevents HTTP.

**Evidence**: `mobile/lib/core/network/api_interceptor.dart:100-108` -- the interceptor adds auth headers without checking `options.uri.scheme`.

**Fix**: Add a scheme check in `AuthInterceptor.onRequest` that rejects or warns when `scheme == 'http'` in release builds.

### P1-3: Guest login access token has 7-day expiry with no refresh mechanism visible

**File**: `backend/app/api/v1/auth.py:893-905`
**Problem**: Guest login issues an access token with `access_expires_delta=timedelta(days=7)` (line 898) and a standard refresh token. This 7-day access token is 336x longer than the normal 30-minute access token. If the Go gateway's `JWTAccessTokenExpireMinutes` is set to 30 (default), the Go middleware will reject this token after 30 minutes because it validates the `exp` claim against the Go-side configuration, not the Python-side configuration.

The Python side creates a token that expires in 7 days, but the Go gateway's `validateJWT` at `middleware/auth.go:583-594` checks `now.After(expTime.Add(jwtClockSkew))` without knowing this is a guest token. The Go-side config `JWTAccessTokenExpireMinutes` defaults to 30 minutes.

**Evidence**:
```python
# auth.py:893-905
return {
    **await _issue_auth_tokens(
        db=db, user=user, request=request,
        access_expires_delta=timedelta(days=7),  # 7-day access token
        extra_claims={"is_guest": True},
    ),
    "user": {...},
}
```

```go
// middleware/auth.go:142-144 (Go defaults)
expireMinutes := h.cfg.JWTAccessTokenExpireMinutes
if expireMinutes <= 0 { expireMinutes = 30 }
```

The Go gateway does NOT create guest tokens (those go through Python), but it DOES validate all tokens. After 30 minutes, the Go gateway will reject the guest access token with "token expired", and the client needs to use the refresh token.

**Fix**: Either (a) keep guest access tokens at the standard 30-minute expiry and rely on refresh, or (b) ensure the Go gateway respects the `exp` claim embedded in the token (which it does), meaning this actually works correctly if Go does not override. Re-verify: Go validates `now.After(expTime)` where `expTime` comes from the token itself, so the 7-day token IS valid through Go. Downgrading to P2 since the Go gateway reads `exp` from the token payload.

**UPDATE**: After re-reading `middleware/auth.go:583-594`, Go reads the `exp` claim from the JWT itself, so the 7-day guest token will pass Go validation. The Go config `JWTAccessTokenExpireMinutes` is only used when Go *creates* tokens (Apple login), not when validating. This is actually **working correctly**. Downgrading to P2.

### P1-4: Auth refresh failure triggers logout but does not notify user of session expiry

**File**: `mobile/lib/core/network/api_interceptor.dart:192-204`
**Problem**: When token refresh fails in `AuthInterceptor.onError`, the code calls `authRepo.logout()` silently (line 198) and then passes the original 401 error through `super.onError`. The user sees a generic error on their current request, but is not explicitly told their session expired. On the next navigation, the router redirect sends them to `/login`. This can be confusing -- the user sees an error on some action, then suddenly they're on the login screen without understanding why.

**Evidence**:
```dart
// api_interceptor.dart:192-204
} catch (e) {
  _refreshCompleter?.completeError(e);
  // Refresh token failed, logout user -- silent logout
  unawaited(
    _ref.read(authRepositoryProvider).logout(
      keepDemoMode: DemoDataService.isDemoMode,
    ),
  );
  return super.onError(err, handler); // Original 401 propagates
}
```

**Fix**: After logout, navigate to login with a query param or state flag indicating "session expired", and show a localized message.

### P1-5: Persona onboarding completion not detectable by the server -- only client-side flag

**File**: `mobile/lib/features/user/presentation/providers/settings_provider.dart:941-1026`
**Problem**: `onboardingCompletedProvider` determines completion by checking local SharedPreferences keyed by user ID, with a fallback that fetches profile context and infers from preference keys (`study_time_preference`, `knowledge_level`, `response_style`). However, the `setCompleted(true)` method (line 1014) only writes to SharedPreferences -- it does NOT call any server endpoint to record onboarding completion.

This means: if the user completes onboarding on device A, clears app data, or logs in on device B, they will be sent through onboarding again (unless the server-side profile context happens to contain the right preference keys).

**Evidence**:
```dart
// settings_provider.dart:1014-1026
Future<void> setCompleted(bool value) async {
  if (state == value) return;
  state = value;
  try {
    final prefs = await SharedPreferences.getInstance();
    final user = _ref.read(authProvider).user;
    if (user != null) {
      await prefs.setBool(_storageKeyForUser(user.id), value);
    }
  } catch (_) {}
}
```

The `syncForUser` method (line 975) does try to infer from server-side profile context, so this is partially mitigated -- if the persona onboarding's `submitOnboarding` call persists preferences server-side (which it does via `repo.submitOnboarding`), then on device B the inference from profile context will return true.

**Fix**: Consider adding an explicit `onboarding_completed` flag to the user profile on the server, so the check is deterministic rather than heuristic.

---

## P2 Findings

### P2-1: Guest token 7-day access expiry is inconsistent with normal 30-minute tokens

**File**: `backend/app/api/v1/auth.py:898`
**Problem**: Guest access tokens expire in 7 days while normal access tokens expire in 30 minutes. While this works (Go validates `exp` from the token), it's inconsistent and means a leaked guest token remains valid much longer. This is a design choice for convenience but is a security tradeoff.

**Fix**: Consider using the same 30-minute access token with a longer refresh token, matching the standard flow.

### P2-2: Password minimum length only 6 characters -- no server-side complexity enforcement

**File**: `mobile/lib/features/auth/presentation/screens/register_screen.dart:219`
**Problem**: Flutter-side password validation requires only 6 characters. The Python server's `UserRegister` schema may also only enforce minimum length. No enforcement of uppercase, numbers, or special characters. The password strength meter is visual-only and does not block submission.

**Evidence**:
```dart
// register_screen.dart:218-222
validator: (value) {
  if (value == null || value.length < 6) {
    return l10n.passwordMinLength;
  }
  return null;
},
```

**Fix**: Enforce minimum complexity on the server-side `UserRegister` schema.

### P2-3: No maximum password length enforced -- potential DoS vector

**File**: `mobile/lib/features/auth/presentation/screens/register_screen.dart:192-224`
**Problem**: Neither the Flutter client nor visible server-side schema enforces a maximum password length. An attacker could submit a very long password string (e.g., 10MB) to cause expensive bcrypt hashing. The `get_password_hash` function will process any length input.

**Fix**: Add a max password length (e.g., 128 chars) in both the Flutter validator and the Python `UserRegister` schema.

### P2-4: Onboarding page index persisted in plain SharedPreferences (not secure)

**File**: `mobile/lib/features/onboarding/presentation/screens/interactive_onboarding_screen.dart:17,72-74`
**Problem**: The onboarding page index is stored in `SharedPreferences` (unencrypted). This is low-sensitivity data (just a page number), so the risk is minimal. However, it uses a different storage mechanism than tokens (which use `flutter_secure_storage`). This is a consistency concern rather than a security issue.

**Fix**: Low priority. The data is not sensitive. No action needed.

---

## Verified Working

### 1. JWT Token Storage -- Secure
Tokens stored in `FlutterSecureStorage` with `AndroidOptions(encryptedSharedPreferences: true)` and `IOSOptions(accessibility: KeychainAccessibility.first_unlock)`.
- `auth_repository.dart:775-782`

### 2. JWT Token Refresh -- Automatic, Silent, Concurrent-Safe
`AuthInterceptor` at `api_interceptor.dart:122-217` implements:
- Automatic 401 detection
- Concurrent refresh deduplication via `Completer<String>`
- Retry with new token
- Silent logout on refresh failure
- No infinite recursion (auth paths excluded)

### 3. Rate Limiting -- Comprehensive
- **Go gateway**: Adaptive rate limiting with separate auth limits (`5 req/s`, burst 15) at `rate_limit.go:272-273`
- **Python engine**: Per-endpoint rate limits via `@limiter.limit()` decorators (e.g., `AUTH_RATE_LIMIT = "5/15minutes"` in production) at `auth.py:62-69`

### 4. Account Lockout -- Server-Side
Python `account_lockout_service` tracks failed login attempts and locks accounts after threshold, with auto-unlock after 15 minutes.
- `auth.py:439-443`

### 5. Anti-Enumeration -- Registration
Registration endpoint checks both username AND email in a single query, returns a generic error message.
- `auth.py:323-335`

### 6. Password Reset -- Full End-to-End Flow
- Forgot password: `forgot_password_screen.dart` -> Python `/auth/forgot-password` -> Celery email task
- Reset: `reset_password_screen.dart` -> Python `/auth/reset-password` with token TTL
- Resets all sessions on password change
- `auth.py:662-735`

### 7. Social Login -- Three Providers
Google, Apple, WeChat all implemented:
- Go handles Apple login directly (`auth.go:50-130`)
- Python handles Google + WeChat (`auth.py:479-564`)
- Flutter dispatches to correct endpoints (`auth_repository.dart:105-160`)

### 8. Guest Mode -- Complete Flow
- Guest login via Python `/auth/guest` creates a real user with demo data
- Guest upgrade to email or social account: `/auth/upgrade-guest` and `/auth/upgrade-guest/social`
- Guest users skip persona onboarding (router redirect at `routes.dart:142-145`)

### 9. Account Deletion -- Complete with GDPR Compliance
- `delete_account_screen.dart` requires "DELETE" confirmation + password/social reauth
- Python endpoint soft-deletes, anonymizes PII, revokes all tokens
- Schedules hard-delete via Celery after 30 days
- `users.py:531-597`

### 10. Onboarding Flow -- 6 Pages + 5-Step Persona + Modeling Chat
Total onboarding sequence:
1. **Interactive Onboarding** (6 pages): Welcome, Architecture, Galaxy, Chat, Tasks, Personalization
2. **Persona Onboarding** (5 steps): Learning goal, style, study time, knowledge level, response preferences
3. **Modeling Chat**: AI conversation with auto-start, streaming, plan generation

### 11. Onboarding Resume -- Partial
`InteractiveOnboardingScreen` restores page index via SharedPreferences on `_restorePage()`.
- `interactive_onboarding_screen.dart:63-69`

### 12. Token Blacklist -- Multi-Level
Go gateway validates tokens against:
- Per-JTI blacklist (Redis)
- Per-user revocation timestamp (Redis)
- Per-session revocation (Redis)
- Local in-memory cache fallback
- Fail-closed mode in production
- `middleware/auth.go:498-580`

### 13. Logout -- Thorough Cleanup
Client: clears tokens + user-scoped local data + chat cache + view storage
Server: blacklists refresh + access JTIs, revokes session
- `auth_provider.dart:570-579`, `auth_repository.dart:173-202`, `auth.py:608-659`

### 14. Modeling Chat -- Robust Error Handling
- Auto-starts first AI message on load (`modeling_chat_screen.dart:57-67`)
- Streaming with chunk append and replace
- Skip sends explicit skip signal to backend
- Planning auto-starts after modeling complete
- Retry on planning failure
- Timeout protection (75s for planning)
- `modeling_chat_screen.dart:1-998`

---

## Cross-Layer Data Flow Trace

### Registration Path
```
Flutter RegisterScreen._submit()
  -> AuthNotifier.register()
    -> AuthRepository.register() [HTTP POST /api/v1/auth/register]
      -> Go Gateway: NoRoute proxy (setup.go:858-861)
        -> Python /auth/register [rate limited, anti-enum, account lockout ready]
          -> User created in PostgreSQL
          -> Celery: send verification email
          -> JWT tokens issued (access 30m + refresh 7d)
          -> Session persisted in user_sessions table
      <- Token + User JSON response
    <- saveTokens() to FlutterSecureStorage
  <- AuthState updated, router redirect to /onboarding/persona
```

### Login Path
```
Flutter LoginScreen._submit()
  -> AuthNotifier.login()
    -> AuthRepository.login() [HTTP POST /api/v1/auth/login]
      -> Go Gateway: NoRoute proxy with rate limiting
        -> Python /auth/login [rate limited 5/15min]
          -> Find user by username OR email
          -> Check account lockout status
          -> Verify password (bcrypt)
          -> Record audit log
          -> Issue tokens + create session
      <- Token + User JSON
    <- saveTokens(), clear guest data
  <- AuthState updated, router redirect
```

### Onboarding Path (Non-Guest)
```
Router redirect -> InteractiveOnboardingScreen (6 pages, skip available)
  onComplete -> Router redirect check (onboardingCompleted still false)
    -> PersonaOnboardingScreen (5-step stepper, NO skip button -- P0-1)
      _handleContinue(last step)
        -> UserRepository.submitOnboarding() [HTTP POST to server]
        -> context.go('/onboarding/modeling-chat')
          -> ModelingChatScreen
            -> Auto-starts AI stream
            -> modeling_complete metadata -> auto-start planning
            -> context.go('/plans/{id}' or '/home')
              -> onboardingCompletedProvider.setCompleted(true)
```
