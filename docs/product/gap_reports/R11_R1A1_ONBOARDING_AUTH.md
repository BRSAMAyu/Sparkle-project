# R11-R1A1: Onboarding + Auth Journey Audit

**Date**: 2026-05-07
**Auditor**: Claude Code Agent (automated deep trace)
**Scope**: App Install -> First Launch -> Auth -> Onboarding -> Modeling Chat -> Self-Model -> Home Screen

## Summary: PASS with 0 P0, 3 P1, 8 P2

The complete user journey from app launch through onboarding to home screen is functionally complete and production-viable. The authentication layer is robust with JWT refresh, token blacklisting, and social login. The onboarding flow collects persona data, triggers AI modeling, and transitions smoothly to the dashboard. Three P1 issues need attention before launch but none are blockers.

---

## Critical Issues (P0): 0

None found. The complete journey is wired end-to-end.

---

## High Issues (P1): 3

### Finding 1: Onboarding has 5 steps, not 6 as specified

- **Severity**: P1
- **User Impact**: The audit request specified "6 pages" but the Stepper in `PersonaOnboardingScreen` has exactly 5 steps: (1) Learning Goal, (2) Learning Style, (3) Daily Study Time, (4) Knowledge Level, (5) Response Preferences. This is a scope clarification rather than a bug -- the 5-step flow covers all persona dimensions. However, if the product spec mandates 6 steps (e.g., a separate "name/nickname" collection step), one is missing.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart:121-230`
- **Current Code**: `_buildSteps` returns a list of 5 `Step` widgets.
- **Expected**: If the product vision requires 6 pages, a step for nickname/name or a confirmation summary page should be added.
- **Fix**: Add a 6th step (either name collection or a review/confirmation summary) if product spec requires it. The current 5 steps cover: goal type + goal text, learning style, study time, knowledge level, response depth + curiosity. A name/nickname step is notably absent from onboarding.

### Finding 2: No onboarding resume capability -- user who kills app mid-onboarding loses progress

- **Severity**: P1
- **User Impact**: If a user kills the app during the PersonaOnboardingScreen or ModelingChatScreen, their onboarding answers are lost. The onboarding state (goal type, learning style, study time, etc.) is held entirely in local widget state (`_PersonaOnboardingScreenState` fields) and is not persisted until `_handleContinue` submits. On next launch, `onboardingCompletedProvider` checks SharedPreferences and profile context server-side, but partial form data is gone.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart:28-37` (state fields)
- **Current Code**: All form state is in-memory only: `_goalController`, `_goalType`, `_learningStyle`, `_knowledgeLevel`, `_studyMinutes`, `_depthPreference`, `_curiosityPreference`.
- **Expected**: Partial onboarding state should be persisted to SharedPreferences or local storage on each step change, so the user can resume from where they left off.
- **Fix**: Save form state to SharedPreferences after each step change in `_handleContinue`. On `initState`, read and restore saved partial state. Clear the saved state on successful submission.

### Finding 3: ModelingChatScreen has no network reconnection or retry for initial stream

- **Severity**: P1
- **User Impact**: The `_startModelingStream('_onboarding_start_')` call in `initState` fires automatically. If the network is momentarily unavailable at that point, the error is shown via `AppFeedback.error` but the user cannot easily retry -- the screen offers no explicit "retry" button for the initial AI greeting. The user would need to manually type something or kill the app.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart:57-67`
- **Current Code**: `initState` calls `_startModelingStream('_onboarding_start_')` unconditionally with no retry logic.
- **Expected**: If the initial stream fails, show a prominent retry button or automatically retry with backoff, so the user is not stuck on an empty chat screen.
- **Fix**: Add a `_initialLoadFailed` state flag. When `_handleStreamError` fires for the initial request ID, set the flag. Show a centered retry button in the chat area when the message list is empty and `_initialLoadFailed` is true.

---

## Medium Issues (P2): 8

### Finding 4: No biometric auth option

- **Severity**: P2
- **User Impact**: Users cannot use Face ID / Touch ID / fingerprint to re-authenticate. They must type their password or use social login every time their session expires.
- **File**: N/A (feature does not exist)
- **Current Code**: No biometric auth integration found anywhere in `mobile/lib/features/auth/`.
- **Expected**: Optional biometric auth for returning users with valid refresh tokens.
- **Fix**: Add `local_auth` package integration. After initial login, offer to enable biometric unlock. Store a flag in FlutterSecureStorage. On `checkAuthStatus`, if refresh token exists and biometric is enabled, prompt biometric before refreshing.

### Finding 5: Google Sign-In scopes commented out

- **Severity**: P2
- **User Impact**: The `GoogleSignIn` instance is created without explicit scopes: `GoogleSignIn()` with commented-out `scopes: ['email', 'profile']`. Default scopes may not include email on all platforms, potentially causing the backend to receive incomplete user info.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/services/social_auth_service.dart:93-95`
- **Current Code**: `final GoogleSignIn _googleSignIn = GoogleSignIn();` with commented-out scopes.
- **Expected**: Scopes `['email', 'profile']` should be explicitly set.
- **Fix**: Uncomment the scopes or add them explicitly: `GoogleSignIn(scopes: ['email', 'profile'])`.

### Finding 6: Token refresh does not trigger auth state rebuild

- **Severity**: P2
- **User Impact**: When `AuthInterceptor.onError` refreshes the token and retries the request, the `AuthNotifier` state is not updated with the new token. This works for the retried request, but if the user's `refreshUser()` call happens later, it uses the repository's internally cached token (which is updated). This is fine functionally but could lead to subtle race conditions.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/core/network/api_interceptor.dart:182-193`
- **Current Code**: Token refresh updates `AuthRepository` internal cache but does not notify `AuthNotifier`.
- **Expected**: Not strictly required since the repository caches tokens. But a cleaner pattern would refresh the auth state.
- **Fix**: Low priority. The current pattern works because `AuthRepository._cachedAccessToken` is updated on refresh.

### Finding 7: Onboarding step validation is missing -- "Next" always enabled

- **Severity**: P2
- **User Impact**: The user can advance through onboarding steps without entering a learning goal. The Stepper's `onStepContinue` always allows progression. Only the final step's "Complete" button submits data -- if the goal text is empty, it sends `null`.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/persona_onboarding_screen.dart:386-426`
- **Current Code**: `_handleContinue` always advances: `if (_currentStep < totalSteps - 1) { setState(() => _currentStep += 1); return; }`. The goal text is nullable in the submission payload.
- **Expected**: Step 0 (Learning Goal) should require the user to enter text before allowing progression. Steps with slider selections have valid defaults.
- **Fix**: Add validation in `_handleContinue` for step 0: if `_goalController.text.trim().isEmpty`, show an error and prevent advancement.

### Finding 8: ModelingChatScreen planning auto-launch timeout is 75 seconds with no user feedback during wait

- **Severity**: P2
- **User Impact**: After the modeling chat completes, the screen auto-starts plan generation with a 75-second timeout. During this time, a small spinner is shown but no progress updates. If the plan generation takes a long time, the user sees only "Generating sprint plan..." with no indication of progress.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart:691-714`
- **Current Code**: `stream.timeout(const Duration(seconds: 75), ...)` with a static loading message.
- **Expected**: Progressive feedback or a determinate progress indicator. Also, the skip/later option is only shown on error, not during the loading phase.
- **Fix**: Show the "Later" skip button alongside the loading spinner so users can skip the planning step without waiting for an error.

### Finding 9: Self-model ("I understand you") snapshot is shown on dashboard but not explicitly after modeling chat

- **Severity**: P2
- **User Impact**: After the modeling chat completes, the user is taken directly to plan generation, then redirected to the plan route or home. The "I understand you" snapshot (UnderstandingSnapshotCard) appears on the dashboard but there is no dedicated self-model presentation moment immediately following onboarding. The vision says the user should see an "I understand you" snapshot.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/user/presentation/screens/modeling_chat_screen.dart:619-629` (`_finish` method)
- **Current Code**: `_finish()` calls `context.go('/home')` or `context.go('/chat')`, never showing the UnderstandingSnapshotCard as a dedicated post-onboarding screen.
- **Expected**: A brief self-model presentation screen or modal after modeling chat before plan generation, showing what Sparkle understands about the user.
- **Fix**: Add an intermediate step in `_finish` that shows the UnderstandingSnapshotCard as a modal or dedicated screen, with a "Looks good" / "Needs correction" button, before proceeding to the home screen.

### Finding 10: No loading skeleton on first dashboard load for new users

- **Severity**: P2
- **User Impact**: After completing onboarding and landing on the dashboard, multiple async providers (`understandingSnapshotProvider`, `homeGrowthStateProvider`, etc.) need to fetch data. The dashboard shows the `_shouldShowFirstGoalEmptyState` path which may flash an empty state briefly before data loads.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/home/presentation/screens/dashboard_screen.dart:195-202`
- **Current Code**: `_shouldShowFirstGoalEmptyState` checks `state.isLoading || state.error != null` but does not show a skeleton during the first load.
- **Expected**: A polished loading skeleton during the initial dashboard data fetch for first-time users.
- **Fix**: Add a full-page loading skeleton when `state.isLoading` is true and no previous data exists.

### Finding 11: Register screen lacks password strength indicator

- **Severity**: P2
- **User Impact**: Users can submit weak passwords without feedback. The register screen validates non-empty but does not show password strength.
- **File**: `/Users/brsama/code/GitHub/Sparkle-project/mobile/lib/features/auth/presentation/screens/register_screen.dart:21-28`
- **Current Code**: Only `_isPasswordVisible` toggle exists; no strength meter or validation beyond "non-empty."
- **Expected**: Password strength indicator showing minimum requirements (length, character types).
- **Fix**: Add a password strength indicator widget below the password field that shows requirements and strength as the user types.

---

## Findings Detail: Verified End-to-End Flow

### 1. App Launch & Startup

**Trace**: `main.dart` -> `SparkleApp` -> `routerProvider` -> GoRouter redirect logic

- `main.dart` initializes Hive, LocalDatabase (Isar), SharedPreferences, Sentry/performance monitoring, and theme manager before `runApp`.
- `_ColdStartFade` provides a smooth 320ms fade-in animation on first frame.
- `SparkleApp` watches `authProvider` and `onboardingCompletedProvider` to trigger router refresh.
- GoRouter `redirect` logic handles all auth state combinations:
  - Loading -> shows splash (`/`)
  - Not authenticated -> redirects to `/login`
  - Authenticated + on auth/splash -> redirects to `/home`
  - Authenticated + not guest + not onboarded -> redirects to `/onboarding/persona`
  - Authenticated + guest/onboarded on persona -> redirects to `/home`
- **FATAL ERROR HANDLER**: If startup fails, a minimal error app is shown with the stack trace.

### 2. Authentication

**Trace**: LoginScreen -> AuthNotifier.login -> AuthRepository -> Go Gateway -> Python Backend

#### Flutter Layer
- `LoginScreen` has proper form validation, loading state on button (`authState.isLoading` disables button and shows spinner).
- Error display via `ref.listen<AuthState>` with `AppFeedback.error` snack bar.
- Three social login buttons: Google, Apple, WeChat -- all wired to `SocialAuthService`.
- Guest login button available (calls `loginAsGuest()` which hits `/auth/guest`).
- Forgot password link navigates to `/forgot-password`.
- Register link navigates to `/register`.
- Legal links (Terms/Privacy) navigate to `/legal/terms` and `/legal/privacy`.

#### Social Auth
- `SocialAuthService` (singleton) implements Google (`google_sign_in`), Apple (`sign_in_with_apple`), WeChat (`fluwx`).
- Apple sign-in correctly requests `email` and `fullName` scopes.
- Cancel handling: Google returns `null`, Apple throws `AuthorizationErrorCode.canceled` -> returns `null`.
- WeChat has timeout (2 min), availability check (`isWeChatInstalled`), and code exchange.

#### Token Management
- `AuthInterceptor` (Dio interceptor) adds Bearer token to all requests.
- **Token Refresh**: On 401, interceptor attempts refresh via `AuthRepository.refreshToken()`.
- **Concurrent refresh protection**: `Completer<String>` prevents multiple simultaneous refreshes.
- **Refresh failure**: Calls `AuthRepository.logout()` to clear local tokens.
- Token stored in `FlutterSecureStorage` with encrypted shared preferences on Android and Keychain on iOS.
- Legacy token key migration is handled (`_readToken` falls back from primary to legacy key).

#### Go Gateway Auth
- `AuthMiddleware` validates JWT from `Authorization: Bearer` header.
- `validateJWT` checks: signing method (HS256), claims (sub, type=access), expiration (30s clock skew), issuer, audience.
- Token blacklist checked via Redis with Fail-Closed/Fail-Open mode.
- Three blacklist levels: JTI (specific token), user-level (all tokens before timestamp), session-level (device logout).
- Local blacklist cache for when Redis is unavailable.
- Rate limiting: auth routes at 5/15min, API routes at 15/30s.

#### Python Backend Auth
- `/api/v1/auth/register` -- creates user, hashes password, issues tokens, records audit.
- `/api/v1/auth/login` -- verifies password, checks account lockout, issues tokens.
- `/api/v1/auth/social-login` -- verifies Google/Apple/WeChat tokens, creates/finds user.
- `/api/v1/auth/guest` -- guest login with seeded demo data.
- `/api/v1/auth/refresh` -- validates refresh token, issues new access token.
- Account lockout service prevents brute force.
- Session management with `user_sessions` table.
- Terms acceptance validation required for register and upgrade-guest.

### 3. Onboarding Flow (PersonaOnboardingScreen)

**Trace**: GoRouter redirect -> `/onboarding/persona` -> `PersonaOnboardingScreen` -> 5 Stepper steps -> `submitOnboarding` -> `/onboarding/modeling-chat`

#### Step Content (5 steps)
1. **Learning Goal**: ChoiceChips for goal type (exam/skill/interest) + TextField for goal description + AI preview card
2. **Learning Style**: ChoiceChips (balanced/visual/practice/logic)
3. **Daily Study Time**: Slider 10-180 minutes
4. **Knowledge Level**: ChoiceChips (beginner/intermediate/advanced)
5. **Response Preferences**: Sliders for depth and curiosity

#### AI Preview
- `_loadPreview()` calls `UserRepository.fetchOnboardingPreview()` -> `POST /profile/onboarding/preview`.
- Debounced at 450ms after any input change.
- Shows an animated card with "AI Understanding" feedback.
- Falls back gracefully on error with a localized message.

#### Submission
- `_handleContinue` on final step calls `UserRepository.submitOnboarding()` -> `POST /profile/onboarding`.
- Python backend stores learning_style, knowledge_level, study_time, depth, curiosity as explicit preferences.
- Creates a learning goal memory record.
- Bootstraps Galaxy scaffold nodes from goal.
- Generates personalized first-session message.
- Records North Star cold start metrics.
- Invalidates profile context providers.
- Navigates to `UserRoutes.modelingChat` with `post_onboarding_message`.

#### Back Navigation
- `_handleBack` decrements `_currentStep`. No data loss -- all form state is preserved in widget fields.

#### Skip (Guest)
- Guest users bypass onboarding entirely (`onboardingCompletedProvider` sets `true` for guests).

### 4. Modeling Chat (ModelingChatScreen)

**Trace**: PersonaOnboardingScreen -> `/onboarding/modeling-chat` -> `ModelingChatScreen` -> chat stream -> modeling_complete metadata -> auto-planning -> redirect

#### Chat Mechanics
- `initState` auto-starts `_startModelingStream('_onboarding_start_')` with `mode: 'onboarding_modeling'`.
- Uses the same `chatRepositoryProvider.chatStream()` as regular chat, with `extraContext` including `mode: 'onboarding_modeling'`, `aurora_surface: 'aurora_modeling'`, `aurora_runtime_enabled: true`.
- Python backend routes `onboarding_modeling` mode to `planning_workflow_manager.process_onboarding_turn()` which runs the modeling FSM.
- Streaming message display with `_appendAssistantChunk` / `_replaceAssistantChunk`.
- Typing indicator shown during streaming.

#### Completion Detection
- `_applyMetadata` watches for `modeling_complete: true` in stream metadata.
- Captures `modeling_output_json` from metadata.
- Sets `_completed = true` and shows `_PlanningBridgeStatus`.

#### Auto-Planning
- After modeling completes, `_autoStartPlanning()` sends a follow-up message with `from_modeling_complete: true` and modeling output.
- Extracts `plan_id` and `plan_route` from stream metadata or `planning_widgets_json`.
- 75-second timeout with `PLANNING_TIMEOUT` error event.
- On success, navigates to the plan route.
- On failure, shows error card with retry and "Later" skip buttons.

#### Skip
- AppBar "Skip" button calls `_skip()` which sends `_onboarding_skip_` with `skip: true`.
- Python backend routes to `planning_workflow_manager.skip_onboarding()`.
- Timeout 3 seconds for skip acknowledgment.
- Calls `_finish()` which marks onboarding complete and navigates to home or chat.

#### Finish
- `_finish()` sets `onboardingCompletedProvider` to `true`.
- If `postOnboardingMessage` exists, navigates to `/chat` with `initial_ai_message`.
- Otherwise navigates to `/home`.

### 5. Self-Model Presentation

**Trace**: After onboarding, `UnderstandingSnapshotCard` on dashboard

- The self-model is NOT presented as a dedicated post-onboarding screen.
- `UnderstandingSnapshotCard` appears on the `DashboardScreen` (line 1122).
- It fetches data from `GET /experience/understanding-snapshot`.
- Python endpoint `get_understanding_snapshot` calls `AuroraControlSurfaceService.build_snapshot()` and `SparkleSelfModelService.get_readout_summary()`.
- Returns: status, confidence, facets, claims, evidence, memory claims, open questions.
- **Correction capability**: User can correct understanding via `POST /experience/understanding-snapshot/corrections`.
- The dashboard's `AuroraStatusBand` also provides correction options (chip-based and freeform).

### 6. First Home Screen (DashboardScreen)

**Trace**: GoRouter -> `/home` -> `DashboardScreen` inside `MainNavigationShell`

#### Navigation
- `MainNavigationShell` uses `StatefulShellRoute.indexedStack` with 5 tabs: Home, Galaxy, Chat, Community, Profile.
- `ResponsiveScaffold` provides adaptive layout (bottom nav mobile, side rail tablet).
- Tab switching with sensory feedback (haptic + sound).
- `InAppNotificationOverlay` wraps the content for real-time notifications.

#### Dashboard Content
- `WeatherHeader` with daily context.
- `AuroraStatusBand` with correction options.
- `GoalSwitcher` for multi-goal support.
- `UnderstandingSnapshotCard` ("I understand you" panel).
- `TaskBoardCard` for today's tasks.
- `ExamSprintDashboardCard` for sprint tracking.
- `AchievementProgressBanner` for achievement system.
- `UnifiedOmniBar` for quick search/action.
- Various card sections configurable via `dashboardCardConfigProvider`.
- Loading, error, and empty states handled for all providers.
- Pull-to-refresh via `_refreshHomeGrowthState()`.

#### All Nav Destinations Have Real Content
- `/home` -> `DashboardScreen` (verified: full implementation)
- `/galaxy` -> `GalaxyScreen` (verified: exists)
- `/chat` -> `ChatScreen` (verified: full streaming chat)
- `/community` -> `CommunityMainScreen` (verified: exists)
- `/profile` -> `ProfileScreen` (verified: exists)

---

## Verified Working: Complete List

1. **App Startup**: main.dart initializes all services, error handler shows crash screen on fatal error
2. **Splash Screen**: GoRouter redirects based on auth state with cold-start fade animation
3. **Login Screen**: Form validation, loading state, error feedback, three social login options, guest mode
4. **Register Screen**: Username/email/password form with TOS/privacy acceptance, localized validation
5. **Forgot/Reset Password**: Complete flow via `/forgot-password` and `/reset-password`
6. **Token Storage**: FlutterSecureStorage with encrypted shared prefs (Android) and Keychain (iOS)
7. **Token Refresh**: Automatic on 401, concurrent refresh protection, fallback to logout
8. **Go Gateway Auth**: JWT validation with blacklist, session revocation, rate limiting
9. **Python Auth**: Register, login, social login, guest login, refresh, password reset -- all endpoints exist and are complete
10. **Social Login (Apple)**: Full flow via sign_in_with_apple with identity token verification
11. **Social Login (Google)**: Full flow via google_sign_in with ID token verification
12. **Social Login (WeChat)**: Full flow via fluwx with code exchange and timeout handling
13. **Onboarding Stepper**: 5 steps collecting goal, style, time, level, preferences
14. **Onboarding Preview**: Real-time AI preview card with debounced API calls
15. **Onboarding Submission**: Persists all preferences to Python backend, creates goal memory, bootstraps Galaxy
16. **Back Navigation**: All onboarding steps support back without data loss
17. **Modeling Chat**: Auto-starts onboarding modeling stream, displays streaming responses
18. **Modeling Completion**: Detects `modeling_complete` metadata, captures output
19. **Auto-Planning**: After modeling, auto-generates sprint plan with 75s timeout
20. **Planning Failure Recovery**: Error card with retry and "Later" skip options
21. **Skip Modeling**: Skip button with graceful backend notification
22. **Onboarding Complete State**: Properly persisted in SharedPreferences per-user and inferred from server profile context
23. **Self-Model Service**: `SparkleSelfModelService.get_readout_summary()` exists and is called by the understanding snapshot endpoint
24. **Understanding Snapshot Card**: Displays on dashboard with confidence, facets, claims, and correction capability
25. **Understanding Correction**: User can submit corrections via `POST /experience/understanding-snapshot/corrections`
26. **Dashboard**: Full featured with weather header, Aurora status band, goal switcher, task board, understanding snapshot, achievement banner, omni bar
27. **Navigation Shell**: 5-tab navigation with responsive layout, achievement unlock handling, community events
28. **Route Protection**: All protected routes require auth middleware; public routes (login, register, legal) are accessible without auth
29. **Guest Mode**: Complete guest login flow with real backend tokens, bypasses onboarding, upgrade path available
30. **Error States**: Login, register, and modeling chat all handle errors with user-facing feedback
31. **Loading States**: All screens show loading indicators during async operations
32. **Screen Transitions**: Custom `buildColdStartTransitionPage` and `buildSparkleTransitionPage` with motion tokens
33. **i18n**: All auth and onboarding screens use `AppLocalizations` for localized strings
34. **Security**: Token blacklisting, session management, account lockout, rate limiting, input validation
35. **Legal Compliance**: TOS and privacy acceptance required at registration with version tracking
