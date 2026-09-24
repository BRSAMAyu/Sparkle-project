// M6-04 regression tests: deep links must survive the auth-loading window.
//
// Locks two invariants:
//   1. While auth state is loading, navigating to a protected deep link
//      (`/chat?session_id=x`) must preserve the original path + query
//      (staged via the splash redirect parameter) instead of being rewritten
//      to '/' and losing everything.
//   2. Once auth resolves, the deep link is restored verbatim for
//      authenticated users, and carried as `return_to` on /login for
//      unauthenticated users.
import 'dart:ffi' as ffi;
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:isar/isar.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/app/routes.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/offline_chat_message.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage_io.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

import '../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory hiveDir;
  late Directory isarDir;
  late Isar isar;

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    final bundledIsarCore = Platform.isMacOS
        ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs/macos/libisar.dylib'
        : Platform.isLinux
            ? '${Directory.current.path}/third_party_plugins/isar_flutter_libs/linux/libisar.so'
            : null;
    await Isar.initializeIsarCore(
      libraries: bundledIsarCore == null
          ? const {}
          : {
              ffi.Abi.current(): bundledIsarCore,
            },
      download: bundledIsarCore == null,
    );
    hiveDir = Directory.systemTemp.createTempSync('sparkle_dlk_hive_');
    isarDir = await Directory.systemTemp.createTemp('sparkle_dlk_isar_');
    Hive.init(hiveDir.path);
    isar = await Isar.open(
      [
        LocalKnowledgeNodeSchema,
        PendingUpdateSchema,
        LocalCRDTSnapshotSchema,
        OutboxItemSchema,
        UserAnalyticsEventSchema,
        TranslationRecordSchema,
        TranslationWordLinkSchema,
        VocabWordSchema,
        VocabReviewSchema,
        FocusSessionRecordSchema,
        CachedStatisticsModelSchema,
        OfflineChatMessageSchema,
      ],
      directory: isarDir.path,
    );
    LocalDatabase().isar = isar;
    await ViewStorageService.ensureInitialized();
  });

  setUp(() {
    DemoDataService.isDemoMode = true;
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  const deepLink = '/chat?session_id=deep-link-42';

  testWidgets(
      'preserves deep link path and query while auth state is loading, '
      'then restores it after authentication resolves', (tester) async {
    final auth = _MutableFakeAuthNotifier(AuthState(isLoading: true));
    final harness = await _pumpRouter(
      tester,
      authState: auth.state,
      onboardingCompleted: true,
      authNotifierOverride: auth,
    );

    harness.router.go(deepLink);
    await _pumpFrames(tester);

    final duringLoading = harness.router.routeInformationProvider.value.uri;
    if (duringLoading.path == '/') {
      // Rewritten onto splash is acceptable ONLY if the original deep link
      // is staged for restoration.
      expect(
        duringLoading.queryParameters['redirect'],
        deepLink,
        reason:
            'Deep link arriving during auth loading must be staged on the '
            'splash location, not dropped: $duringLoading',
      );
    } else {
      expect(duringLoading.toString(), deepLink);
    }

    // Auth resolves: signed-in user → deep link must be restored verbatim.
    auth.state = AuthState(isAuthenticated: true, user: _buildUser());
    await _pumpFrames(tester);

    final after = harness.router.routeInformationProvider.value.uri;
    expect(
      after.path,
      '/chat',
      reason:
          'Protected deep link must land on its target once auth resolves, '
          'not fall back to /home: $after',
    );
    expect(after.queryParameters['session_id'], 'deep-link-42');

    // Leave the chat surface before tearing down so chat-scoped timers do
    // not leak into the test teardown invariant.
    harness.router.go('/home');
    await _pumpFrames(tester);
    await _tearDownHarness(tester, harness);
  });

  testWidgets(
      'unauthenticated deep link carries return_to on the login location',
      (tester) async {
    final auth = _MutableFakeAuthNotifier(AuthState(isLoading: true));
    final harness = await _pumpRouter(
      tester,
      authState: auth.state,
      onboardingCompleted: true,
      authNotifierOverride: auth,
    );

    harness.router.go(deepLink);
    await _pumpFrames(tester);

    // Auth resolves: anonymous user → login, carrying the intended target.
    auth.state = AuthState();
    await _pumpFrames(tester);

    final uri = harness.router.routeInformationProvider.value.uri;
    expect(uri.path, '/login');
    expect(
      uri.queryParameters['return_to'],
      deepLink,
      reason: 'Login redirect must carry the originally requested deep link',
    );

    await _tearDownHarness(tester, harness);
  });

  testWidgets(
      'rejects backslash protocol-relative redirect payloads (open-redirect '
      'hardening)', (tester) async {
    final harness = await _pumpRouter(
      tester,
      authState: AuthState(isAuthenticated: true, user: _buildUser()),
      onboardingCompleted: true,
    );

    // `/\evil.com` passes a `//`-prefix-only check but browsers treat a
    // backslash like a slash, making it protocol-relative.
    harness.router.go('/?redirect=${Uri.encodeComponent(r'/\evil.com')}');
    await _pumpFrames(tester);

    final uri = harness.router.routeInformationProvider.value.uri;
    expect(
      uri.path,
      '/home',
      reason:
          'An authenticated user hitting splash with a backslash '
          'protocol-relative redirect payload must fall through to /home, '
          'not be navigated to the attacker-controlled location '
          '(observed: $uri)',
    );

    await _tearDownHarness(tester, harness);
  });

  testWidgets(
      'keeps the current landing page while onboarding state is pending '
      '(M6-07 tri-state)', (tester) async {
    final auth = _MutableFakeAuthNotifier(
      AuthState(isAuthenticated: true, user: _buildUser()),
    );
    final harness = await _pumpRouter(
      tester,
      authState: auth.state,
      onboardingCompleted: false,
      authNotifierOverride: auth,
      pendingOnboarding: true,
    );

    // While the onboarding sync is pending (state == null), the router
    // must NOT rewrite locations into the persona onboarding flow.
    harness.router.go(deepLink);
    await _pumpFrames(tester);

    final uri = harness.router.routeInformationProvider.value.uri;
    expect(
      uri.path,
      '/chat',
      reason:
          'During the onboarding-pending window the redirect must not send '
          'users to the persona onboarding (M6-07 flash); observed: '
          '$uri',
    );

    await _tearDownHarness(tester, harness);
  });
}

Future<_RouterHarness> _pumpRouter(
  WidgetTester tester, {
  required AuthState authState,
  required bool onboardingCompleted,
  AuthNotifier? authNotifierOverride,
  bool pendingOnboarding = false,
}) async {
  tester.view.devicePixelRatio = 2.0;
  tester.view.physicalSize = const Size(1440, 2960);
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  SharedPreferences.setMockInitialValues({
    kOnboardingCompletedKey: onboardingCompleted,
  });
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith(
        (ref) => authNotifierOverride ?? _FakeAuthNotifier(authState),
      ),
      onboardingCompletedProvider.overrideWith(
        (ref) => pendingOnboarding
            ? _PendingOnboardingCompletedNotifier(ref)
            : _FakeOnboardingCompletedNotifier(onboardingCompleted, ref),
      ),
      enhancedGalaxyRepositoryProvider.overrideWithValue(
        _TestGalaxyRepository(),
      ),
    ],
  );
  var disposed = false;
  addTearDown(() {
    if (!disposed) {
      disposed = true;
      container.dispose();
    }
  });

  final router = container.read(routerProvider);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp.router(
        routerConfig: router,
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );

  await _pumpFrames(tester);
  return _RouterHarness(router: router, container: container);
}

Future<void> _tearDownHarness(
  WidgetTester tester,
  _RouterHarness harness,
) async {
  await tester.pumpWidget(const SizedBox.shrink());
  await tester.pump();
  harness.container.dispose();
}

Future<void> _pumpFrames(WidgetTester tester) async {
  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000001',
      username: 'router_test_user',
      email: 'router@example.com',
      nickname: 'Router Test',
      flameLevel: 3,
      flameBrightness: 0.8,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      status: UserStatus.online,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(AuthState authState)
      : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _MutableFakeAuthNotifier extends _FakeAuthNotifier {
  _MutableFakeAuthNotifier(super.authState);
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _FakeOnboardingCompletedNotifier(this._completed, Ref ref) : super(ref);

  final bool _completed;

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = _completed;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
}

/// M6-07: stays in the pending (null) state for the whole test so the
/// router redirect's onboarding branches must not fire.
class _PendingOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _PendingOnboardingCompletedNotifier(super.ref);

  @override
  Future<void> syncForUser(UserModel? user) async {
    state = null;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), SecureTokenStorage(storage: _MemorySecureStorage()));

  @override
  Future<bool> isLoggedIn() async => false;

  @override
  Future<UserModel> getCurrentUser() {
    throw UnimplementedError();
  }

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _TestGalaxyRepository extends EnhancedGalaxyRepository {
  _TestGalaxyRepository() : super(_UnusedApiClient());

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _MemorySecureStorage implements FlutterSecureStorage {
  final Map<String, String> _values = <String, String>{};

  @override
  Future<void> write({
    required String key,
    String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _values.remove(key);
    } else {
      _values[key] = value;
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _values[key];

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    _values.remove(key);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _RouterHarness {
  _RouterHarness({required this.router, required this.container});

  final GoRouter router;
  final ProviderContainer container;
}
