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
import 'package:sparkle/app/theme.dart';
import 'package:sparkle/core/analytics/models/user_analytics_event.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/offline/local_database.dart';
import 'package:sparkle/core/offline/models/focus_session_record.dart';
import 'package:sparkle/core/offline/models/translation_record.dart';
import 'package:sparkle/core/offline/models/vocab_word.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/performance_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/statistics/data/models/cached_statistics_model.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/auth/presentation/screens/login_screen.dart';
import 'package:sparkle/features/calendar/presentation/screens/calendar_stats_screen.dart';
import 'package:sparkle/features/calendar/presentation/screens/daily_detail_screen.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_screen.dart';
import 'package:sparkle/features/community/presentation/screens/create_post_screen.dart';
import 'package:sparkle/features/community/presentation/screens/create_group_screen.dart';
import 'package:sparkle/features/community/presentation/screens/community_main_screen.dart';
import 'package:sparkle/features/community/presentation/screens/friends_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_files_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_members_screen.dart';
import 'package:sparkle/features/community/presentation/screens/group_search_screen.dart';
import 'package:sparkle/features/community/presentation/screens/user_search_screen.dart';
import 'package:sparkle/features/error_book/presentation/screens/add_error_screen.dart';
import 'package:sparkle/features/error_book/presentation/screens/error_detail_screen.dart';
import 'package:sparkle/features/error_book/presentation/screens/error_list_screen.dart';
import 'package:sparkle/features/focus/presentation/screens/focus_main_screen.dart';
import 'package:sparkle/features/galaxy/data/repositories/enhanced_galaxy_repository.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/home/presentation/screens/notification_list_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/growth_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_screen.dart';
import 'package:sparkle/features/photon/presentation/widgets/photon_balance_card.dart';
import 'package:sparkle/features/seed_library/presentation/screens/create_library_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_detail_screen.dart';
import 'package:sparkle/features/seed_library/presentation/screens/seed_library_list_screen.dart';
import 'package:sparkle/features/task/presentation/screens/task_list_screen.dart';
import 'package:sparkle/features/translation/presentation/screens/translation_history_screen.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/features/user/presentation/screens/edit_profile_screen.dart';
import 'package:sparkle/features/user/presentation/screens/password_reset_screen.dart';
import 'package:sparkle/features/user/presentation/screens/persona_onboarding_screen.dart';
import 'package:sparkle/features/user/presentation/screens/profile_screen.dart';
import 'package:sparkle/features/user/presentation/screens/system_updates_screen.dart';
import 'package:sparkle/features/user/presentation/screens/sync_center_screen.dart';
import 'package:sparkle/features/user/presentation/screens/unified_settings_screen.dart';
import 'package:sparkle/features/user/presentation/screens/user_persona_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory hiveDir;
  late Directory isarDir;
  late Isar isar;

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    await Isar.initializeIsarCore(download: true);
    hiveDir = Directory.systemTemp.createTempSync('sparkle_router_hive_');
    isarDir = await Directory.systemTemp.createTemp('sparkle_router_isar_');
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
    PerformanceService.instance.stopMonitoring();
  });

  group('GoRouter smoke', () {
    testWidgets('redirects unauthenticated users to login', (tester) async {
      final harness = await _pumpRouter(
        tester,
        authState: AuthState(isLoading: false, isAuthenticated: false),
        onboardingCompleted: true,
      );

      await _pumpFrames(tester);

      expect(harness.router.routeInformationProvider.value.uri.path, '/login');
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets(
        'redirects authenticated users without onboarding to persona flow',
        (tester) async {
      final harness = await _pumpRouter(
        tester,
        authState: AuthState(
          isLoading: false,
          isAuthenticated: true,
          user: _buildUser(),
        ),
        onboardingCompleted: false,
      );

      await _pumpFrames(tester);

      expect(harness.router.routeInformationProvider.value.uri.path,
          '/onboarding/persona');
      expect(find.byType(PersonaOnboardingScreen), findsOneWidget);
    });

    testWidgets(
        'loads dashboard for authenticated users with onboarding completed',
        (tester) async {
      final harness = await _pumpRouter(
        tester,
        authState: AuthState(
          isLoading: false,
          isAuthenticated: true,
          user: _buildUser(),
        ),
        onboardingCompleted: true,
      );

      await _pumpFrames(tester);

      expect(harness.router.routeInformationProvider.value.uri.path, '/home');
      expect(find.byType(DashboardScreen), findsOneWidget);
    });

    testWidgets('navigates shell routes to the correct top-level screens',
        (tester) async {
      final harness = await _pumpRouter(
        tester,
        authState: AuthState(
          isLoading: false,
          isAuthenticated: true,
          user: _buildUser(),
        ),
        onboardingCompleted: true,
      );

      Future<void> expectRoute(String path, Type screenType) async {
        harness.router.go(path);
        await _pumpFrames(tester);
        expect(harness.router.routeInformationProvider.value.uri.path, path);
        expect(find.byType(screenType), findsOneWidget);
        if (path == '/galaxy') {
          PerformanceService.instance.stopMonitoring();
        }
      }

      await expectRoute('/home', DashboardScreen);
      await expectRoute('/galaxy', GalaxyScreen);
      await expectRoute('/chat', ChatScreen);
      await expectRoute('/community', CommunityMainScreen);
      await expectRoute('/profile', ProfileScreen);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      harness.container.dispose();
    });

    testWidgets(
        'loads critical secondary routes used by dashboard and community actions',
        (tester) async {
      final harness = await _pumpRouter(
        tester,
        authState: AuthState(
          isLoading: false,
          isAuthenticated: true,
          user: _buildUser(),
        ),
        onboardingCompleted: true,
      );

      Future<void> expectRoute(String path, Type screenType) async {
        harness.router.go(path);
        await _pumpFrames(tester);
        expect(
          harness.router.routeInformationProvider.value.uri.toString(),
          path,
        );
        expect(find.byType(screenType), findsOneWidget);
      }

      await expectRoute('/focus', FocusMainScreen);
      await expectRoute('/tasks', TaskListScreen);
      await expectRoute('/notifications', NotificationListScreen);
      await expectRoute(
          '/calendar?date=2026-03-06T00:00:00.000', CalendarStatsScreen);
      await expectRoute(
          '/calendar-stats?date=2026-03-07T00:00:00.000', CalendarStatsScreen);
      await expectRoute(
        '/calendar/day?date=2026-03-08T00:00:00.000',
        DailyDetailScreen,
      );
      await expectRoute('/sprint', SprintScreen);
      await expectRoute('/growth', GrowthScreen);
      await expectRoute('/community/users/search', UserSearchScreen);
      await expectRoute('/community/groups/search', GroupSearchScreen);
      await expectRoute('/community/friends/discover', FriendsScreen);
      await expectRoute('/community/groups/create', CreateGroupScreen);
      await expectRoute('/community/posts/create', CreatePostScreen);
      await expectRoute(
        '/community/groups/group-router-smoke/members?name=Router%20Group',
        GroupMembersScreen,
      );
      await expectRoute(
        '/community/groups/group-router-smoke/files',
        GroupFilesScreen,
      );
      await expectRoute('/profile/edit', EditProfileScreen);
      await expectRoute('/profile/settings', UnifiedSettingsScreen);
      await expectRoute('/profile/persona', UserPersonaScreen);
      await expectRoute('/profile/system-updates', SystemUpdatesScreen);
      await expectRoute('/profile/password-reset', PasswordResetScreen);
      await expectRoute('/profile/sync-center', SyncCenterScreen);
      await expectRoute('/errors', ErrorListScreen);
      await expectRoute('/errors/new', AddErrorScreen);
      await expectRoute('/errors/error-router-smoke', ErrorDetailScreen);
      await expectRoute('/translations/history', TranslationHistoryScreen);
      await expectRoute('/photon/history', TransactionHistoryScreen);
      await expectRoute('/seed-libraries', SeedLibraryListScreen);
      await expectRoute('/seed-libraries/new', CreateLibraryScreen);
      await expectRoute(
        '/seed-libraries/library-router-smoke',
        SeedLibraryDetailScreen,
      );

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
      harness.container.dispose();
    });
  });
}

Future<_RouterHarness> _pumpRouter(
  WidgetTester tester, {
  required AuthState authState,
  required bool onboardingCompleted,
}) async {
  SharedPreferences.setMockInitialValues({
    kOnboardingCompletedKey: onboardingCompleted,
  });
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith((ref) => _FakeAuthNotifier(authState)),
      onboardingCompletedProvider.overrideWith(
        (ref) => _FakeOnboardingCompletedNotifier(onboardingCompleted),
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
      createdAt: DateTime(2026, 1, 1),
      updatedAt: DateTime(2026, 1, 1),
    );

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier(AuthState authState) : super(_UnusedAuthRepository()) {
    state = authState;
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _FakeOnboardingCompletedNotifier extends OnboardingCompletedNotifier {
  _FakeOnboardingCompletedNotifier(bool completed) : super() {
    state = completed;
  }

  @override
  Future<void> setCompleted(bool value) async {
    state = value;
  }
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), _MemorySecureStorage());

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
  Stream<SSEEvent> getGalaxyEventsStream({String? lastEventId}) =>
      Stream<SSEEvent>.multi((controller) {});
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
