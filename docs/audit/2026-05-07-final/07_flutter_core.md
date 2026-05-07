# Flutter Core & Cross-Cutting Audit

**Auditor**: Agent (Opus)
**Date**: 2026-05-07
**Status**: PASS WITH ISSUES

## Summary

The Flutter core infrastructure is architecturally sound, with a mature design system (DS 2.0) supporting light/dark/high-contrast/color-blind modes, proper offline-first sync architecture, and comprehensive error handling. The routing layer uses GoRouter with proper auth guards, deep link handling, and route resilience. However, several issues require attention before launch: a fabricated FPS/memory estimator in the performance monitor, 21 stale generated `.g.dart` files, one missing proto codegen, an unused idempotency interceptor, and version constant drift.

## Critical Issues (P0)

### P0-01: PerformanceMonitor._estimateMemoryUsage() returns fake data
**File**: `mobile/lib/core/services/performance_monitor.dart:422-426`
```dart
int _estimateMemoryUsage() {
  return 100 + (DateTime.now().millisecond % 400); // 模拟100-500MB
}
```
The memory estimator is a random number generator. This feeds directly into Sentry breadcrumbs, anomaly checks (line 362: `metric.memoryMB > 500`), and client observability events. Production monitoring will report meaningless, misleading memory data. Additionally, `_currentFPS` on line 127 is set to `devicePixelRatio`, which is not FPS at all.

**Impact**: All "high memory" and "low FPS" Sentry alerts in production will be based on fabricated data, making performance regression detection impossible.

### P0-02: 21 stale `.g.dart` files (code generation out of sync)
Source files have been modified after their corresponding `.g.dart` files were generated. This means generated serialization/deserialization code may be missing fields or have wrong types. Affected critical files include:
- `mobile/lib/shared/entities/user_model.g.dart`
- `mobile/lib/shared/entities/user_brief.g.dart`
- `mobile/lib/features/auth/data/models/token_model.g.dart`
- `mobile/lib/features/chat/data/models/chat_message_model.g.dart`
- `mobile/lib/features/plan/data/models/plan_model.g.dart`
- `mobile/lib/core/offline/models/offline_chat_message.g.dart`

**Fix**: Run `dart run build_runner build --delete-conflicting-outputs` before launch.

## High Issues (P1)

### P1-01: `community_service.proto` not generated for Flutter
**File**: `proto/community_service.proto` exists, but there is no corresponding `mobile/lib/gen/community_service.*.dart`. The Flutter app has 6 of 7 proto files generated. If any feature needs protobuf-based community types, it will fail at runtime.

**Fix**: Run `make mobile-gen` or regenerate the community proto for Flutter.

### P1-02: IdempotencyInterceptor exists but is never wired in
**File**: `mobile/lib/core/network/idempotency_interceptor.dart` is a well-written interceptor that adds `X-Idempotency-Key` headers to POST/PUT/PATCH requests. However, it is never added to the Dio interceptors in `api_client.dart` (line 23-25 only adds auth, retry, and logging interceptors).

**Impact**: All non-idempotent write operations lack automatic retry-safety headers, which matters for offline sync replay.

### P1-03: `http_parser: any` and `stream_channel: any` are unbounded dependencies
**File**: `mobile/pubspec.yaml:98,131`
```yaml
http_parser: any
stream_channel: any
```
Using `any` allows any version, including breaking changes. This is a supply-chain risk and can cause build failures when upstream publishes a major version bump.

**Fix**: Pin to specific major versions, e.g., `http_parser: ^4.0.0`, `stream_channel: ^2.1.0`.

### P1-04: Version constant drift between pubspec.yaml and AppConstants
**File**: `mobile/pubspec.yaml:4` declares `version: 1.0.0+1` but `mobile/lib/core/constants/app_constants.dart:6` has `static const String appVersion = '0.1.0'`.

**Impact**: Any code referencing `AppConstants.appVersion` (e.g., crash reporting, about screens) reports the wrong version.

## Medium Issues (P2)

### P2-01: ThemeManager._parseSimpleJson is a hand-rolled JSON parser
**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart:288-315`
The comment says "simplified parser, should use dart:convert in production." The implementation breaks on nested objects, escaped quotes, and values containing commas or colons. `dart:convert` is already imported transitively through `SharedPreferences`. The `_stringifySimpleJson` method at line 318 has the same issue.

### P2-02: ThemeManager.dispose() intentionally swallows super.dispose()
**File**: `mobile/lib/core/design/tokens_v2/theme_manager.dart:347-351`
```dart
@override
// ignore: must_call_super
void dispose() {
  // Prevent disposal of the singleton instance...
}
```
While the comment explains the rationale (singleton pattern with Riverpod ownership), this is fragile. If Riverpod ever double-disposes, the ChangeNotifier internals may be in an inconsistent state. A better pattern is to return the same instance from the provider using `ref.watch` with `keepAlive`.

### P2-03: `flutter_lints` is deprecated
**File**: `mobile/pubspec.yaml:121`, `mobile/analysis_options.yaml:5`
The `flutter_lints` package was deprecated in favor of `flutter_lints` -> `lints` (Dart 3). The current package `flutter_lints: ^3.0.1` still works but is no longer maintained. Recommended migration to `flutter_lints` -> use the built-in `flutter analyze` or migrate to `lints: ^5.0.0`.

### P2-04: Error fallback messages in ErrorMessages.getUserFriendlyMessage contain hardcoded Chinese
**File**: `mobile/lib/core/utils/error_messages.dart:120-151`
When `l10n` is null, all fallback messages are hardcoded Chinese strings. While `getLocalizedMessage` handles the bilingual case correctly, the fallback path could confuse users whose locale is English.

### P2-05: SyncEngine creates new Logger() instance per construction
**File**: `mobile/lib/core/offline/sync_engine.dart:29`
```dart
final Logger _logger = Logger();
```
Each `SyncEngine` instance creates a new `Logger`, which allocates a new `PrettyPrinter` and `LogOutput`. This should be a shared singleton or injected dependency.

### P2-06: No Sentry DSN validation
**File**: `mobile/lib/core/services/performance_monitor.dart:61`
The code checks `normalizedDsn.isEmpty` but does not validate the DSN format. A malformed DSN string (e.g., a typo) will silently fail at `SentryFlutter.init`, and all error reporting will be lost without any indication.

## Low Issues (P3)

### P3-01: DS class has redundant `Const` aliases
**File**: `mobile/lib/core/design/design_system.dart:723-729`
Properties like `brandPrimaryConst`, `brandPrimary10Const`, etc. are getters that return the same non-const value. The "const" in the name is misleading because the underlying `ThemeManager().current` is not a compile-time constant. These exist for "backward compatibility with const constructors" but cannot actually be used in const contexts.

### P3-02: Excessive spacing aliases in DS
**File**: `mobile/lib/core/design/design_system.dart:976-990`
The DS class has both semantic spacing (`xs`, `sm`, `md`, `lg`, `xl`, `xxl`, `xxxl`) and numeric aliases (`spacing2`, `spacing4`, `spacing6`, ...). These overlap and create confusion about which to use.

### P3-03: ApiConstants prints base URL to debug console in production
**File**: `mobile/lib/core/constants/api_constants.dart:29,44,48`
```dart
debugPrint('... API Base URL (override): $_baseUrlOverride');
```
These `debugPrint` calls appear outside of `kDebugMode` guards, meaning they print to console even in release builds (debugPrint is not stripped in release, just throttled).

### P3-04: UserFacingError messages are English-only
**File**: `mobile/lib/core/errors/user_facing_error.dart`
The `UserFacingError.from()` method returns only English strings. The more sophisticated `ErrorMessages` class and `AppFailure.userMessage` properly use i18n, so this class may be redundant or should delegate to the i18n system.

### P3-05: AuthInterceptor retry Dio does not have receive timeout
**File**: `mobile/lib/core/network/api_interceptor.dart:75-83`
The retry Dio instance has `connectTimeout` and `receiveTimeout`, but does not add the `RetryInterceptor`. If the retry itself gets a 502/503/504, it won't be retried again.

## Positive Findings

1. **Design System 2.0 is comprehensive**: Full light/dark/high-contrast/color-blind theme support with proper `ThemeExtension` integration, semantic color tokens, and responsive breakpoints. The `SparkleColors.lerp()` implementation correctly animates all 32 color tokens for smooth theme transitions.

2. **Error handling architecture is mature**: Three-layer error system (`AppFailure` sealed class, `UserFacingError` for UI, `ErrorMessages` with i18n) with proper error classification, retryability signals, and recovery labels. `AppFailureMapper` correctly maps Dio exceptions to typed failures.

3. **Auth interceptor handles token refresh correctly**: Concurrent 401 deduplication via `Completer<String>`, separate retry Dio to avoid recursion, and proper edge case handling (teardown, demo mode, missing refresh tokens).

4. **Offline-first architecture is solid**: CRDT-based sync engine with outbox pattern, exponential backoff with jitter, connectivity-aware processing, and proper ACK timeout handling. The `OutboxItem` schema is well-designed with deduplication, priority, and trace IDs.

5. **SSL certificate pinning is properly implemented**: Platform-aware IO/stub pattern with SHA-256 pin validation. Falls back gracefully when no pin is configured.

6. **Route resilience is well-designed**: `RouteResilienceScope` handles back-navigation fallback, external route opening with error recovery, and per-feature fallback mapping.

7. **Navigation observer integrates sensory feedback**: `SensoryNavigationObserver` properly debounces feedback events (160ms) and skips the initial route, with observability tracking.

8. **Client observability service is production-ready**: Batch event upload, offline queueing with persistence (SharedPreferences), max queue size limits (200 events), and periodic flush. Properly skips its own HTTP calls with `skip_client_telemetry` flag.

9. **Test coverage for core services**: SSEEvent parsing, client observability flush, hash utils, smart cache, sync engine, i18n service all have dedicated unit tests. Smoke tests cover router and main pages.

10. **Startup sequence is well-structured**: Ordered initialization (Hive -> Isar -> SharedPrefs -> Sentry -> ThemeManager -> TracingService), branded error screen for startup failures, deferred warmups, and first-frame timing instrumentation.

## Files Audited

### Core Design System
- `mobile/lib/core/design/design_system.dart`
- `mobile/lib/core/design/breakpoints.dart`
- `mobile/lib/core/design/color_extensions.dart`
- `mobile/lib/core/design/materials.dart`
- `mobile/lib/core/design/motion.dart`
- `mobile/lib/core/design/responsive_widgets.dart`
- `mobile/lib/core/design/theme/performance_tier.dart`
- `mobile/lib/core/design/theme/sparkle_context_extension.dart`
- `mobile/lib/core/design/theme/sparkle_theme_extension.dart`
- `mobile/lib/core/design/tokens_v2/animation_token.dart`
- `mobile/lib/core/design/tokens_v2/color_token.dart`
- `mobile/lib/core/design/tokens_v2/responsive_system.dart`
- `mobile/lib/core/design/tokens_v2/spacing_token.dart`
- `mobile/lib/core/design/tokens_v2/theme_manager.dart`
- `mobile/lib/core/design/tokens_v2/typography_token.dart`
- `mobile/lib/core/design/tokens/color_tokens_v2.dart`
- `mobile/lib/core/design/tokens/task_colors.dart`
- `mobile/lib/core/design/adaptive/emotion_responsive_theme.dart`

### Core Networking
- `mobile/lib/core/network/api_client.dart`
- `mobile/lib/core/network/api_endpoints.dart`
- `mobile/lib/core/network/api_interceptor.dart`
- `mobile/lib/core/network/dio_provider.dart`
- `mobile/lib/core/network/http_client_pinning.dart`
- `mobile/lib/core/network/http_client_pinning_io.dart`
- `mobile/lib/core/network/http_client_pinning_stub.dart`
- `mobile/lib/core/network/idempotency_interceptor.dart`
- `mobile/lib/core/network/response_parser.dart`

### Core Navigation
- `mobile/lib/core/navigation/route_resilience.dart`
- `mobile/lib/core/navigation/sensory_navigation_observer.dart`
- `mobile/lib/core/navigation/shell_navigation.dart`
- `mobile/lib/core/navigation/sparkle_route_transition.dart`

### Core Constants
- `mobile/lib/core/constants/api_constants.dart`
- `mobile/lib/core/constants/app_constants.dart`
- `mobile/lib/core/constants/push_config.dart`

### Core Errors
- `mobile/lib/core/errors/failures.dart`
- `mobile/lib/core/errors/user_facing_error.dart`
- `mobile/lib/core/utils/error_messages.dart`

### Core Services
- `mobile/lib/core/services/performance_monitor.dart`
- `mobile/lib/core/services/client_observability_service.dart`
- `mobile/lib/core/services/performance_service.dart`

### Core Providers
- `mobile/lib/core/providers/theme_provider.dart`
- `mobile/lib/core/providers/locale_provider.dart`
- `mobile/lib/core/providers/core_keep_alive_provider.dart`
- `mobile/lib/core/providers/experience_envelope_provider.dart`
- `mobile/lib/core/providers/persistent_state_notifier.dart`

### Core Tracing
- `mobile/lib/core/tracing/tracing_service.dart`
- `mobile/lib/core/tracing/noop_tracing_service.dart`
- `mobile/lib/core/tracing/tracing_service_impl_io.dart`
- `mobile/lib/core/tracing/tracing_service_impl_web.dart`

### Core Offline
- `mobile/lib/core/offline/local_database.dart`
- `mobile/lib/core/offline/connectivity_provider.dart`
- `mobile/lib/core/offline/sync_engine.dart`
- `mobile/lib/core/offline/sync_queue.dart`
- `mobile/lib/core/offline/sync_metadata.dart`
- `mobile/lib/core/offline/crdt_sync_manager.dart`
- `mobile/lib/core/offline/crdt_persistence.dart`
- `mobile/lib/core/offline/conflict_resolver.dart`
- `mobile/lib/core/offline/network_monitor.dart`
- `mobile/lib/core/offline/offline_providers.dart`
- `mobile/lib/core/offline/offline_crdt_document.dart`

### Shared
- `mobile/lib/shared/entities/achievement_model.dart`
- `mobile/lib/shared/entities/galaxy_model.dart`
- `mobile/lib/shared/entities/photon_model.dart`
- `mobile/lib/shared/entities/task_model.dart`
- `mobile/lib/shared/entities/user_model.dart`
- `mobile/lib/shared/entities/user_brief.dart`
- `mobile/lib/shared/models/api_response_model.dart`
- `mobile/lib/shared/models/base_model.dart`
- `mobile/lib/shared/widgets/card_picker_sheet.dart`
- `mobile/lib/shared/widgets/draggable_task_card.dart`

### Generated Protobuf
- `mobile/lib/gen/agent_service.pb.dart`
- `mobile/lib/gen/agent_service.pbenum.dart`
- `mobile/lib/gen/agent_service.pbgrpc.dart`
- `mobile/lib/gen/agent_service.pbjson.dart`
- `mobile/lib/gen/error_book.pb.dart` (and related)
- `mobile/lib/gen/galaxy_service.pb.dart` (and related)
- `mobile/lib/gen/stt_service.pb.dart` (and related)
- `mobile/lib/gen/user_state.pb.dart` (and related)
- `mobile/lib/gen/websocket.pb.dart` (and related)

### App Entry Points
- `mobile/lib/main.dart`
- `mobile/lib/app/app.dart`
- `mobile/lib/app/routes.dart`
- `mobile/lib/app/theme.dart`

### Configuration
- `mobile/pubspec.yaml`
- `mobile/analysis_options.yaml`

### Tests
- `mobile/test/unit/api_client_test.dart`
- `mobile/test/unit/client_observability_service_test.dart`
- `mobile/test/unit/sync_engine_test.dart`
- `mobile/test/unit/hash_utils_test.dart`
- `mobile/test/unit/smart_cache_test.dart`
- `mobile/test/unit/i18n_service_test.dart`
- `mobile/test/unit/offline_sync_test.dart`
- `mobile/test/app/router_smoke_test.dart`
- `mobile/test/app/main_pages_load_smoke_test.dart`
- `mobile/test/core/p2_10_core_service_test_harness.dart`
- (and 279 other test files)
