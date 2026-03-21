import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/community/presentation/screens/community_main_screen.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_card_config_provider.dart';
import 'package:sparkle/features/home/presentation/screens/dashboard_screen.dart';
import 'package:sparkle/features/home/presentation/widgets/unified_omni_bar.dart';
import 'package:sparkle/features/user/presentation/screens/profile_screen.dart';
import 'package:sparkle/features/user/presentation/widgets/statistics_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_brief.dart';
import 'package:sparkle/shared/entities/user_model.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late Directory hiveDir;

  setUpAll(() async {
    SharedPreferences.setMockInitialValues({});
    hiveDir = Directory.systemTemp.createTempSync('sparkle_main_pages_hive_');
    Hive.init(hiveDir.path);
    await ViewStorageService.ensureInitialized();
  });

  setUp(() {
    DemoDataService.isDemoMode = true;
  });

  tearDown(() {
    DemoDataService.isDemoMode = false;
  });

  group('Main page load smoke', () {
    testWidgets('dashboard renders key sections with authenticated demo user', (
      tester,
    ) async {
      await _pumpPage(tester, const DashboardScreen());

      expect(find.byType(DashboardScreen), findsOneWidget);
      expect(find.byType(CustomScrollView), findsOneWidget);
      expect(find.byType(UnifiedOmniBar), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('community renders tabs and app bar', (tester) async {
      await _pumpPage(tester, const CommunityMainScreen());

      expect(find.byType(CommunityMainScreen), findsOneWidget);
      expect(find.byType(TabBar), findsOneWidget);
      expect(find.byIcon(Icons.search), findsOneWidget);
      expect(find.byIcon(Icons.person_add_outlined), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('profile renders user identity and stats card', (tester) async {
      await _pumpPage(tester, const ProfileScreen());

      expect(find.byType(ProfileScreen), findsOneWidget);
      expect(find.text('Router Test'), findsOneWidget);
      expect(find.byType(StatisticsCard), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('dashboard card config persists after reload', (
      tester,
    ) async {
      await ViewStorageService.instance.clearAll();

      final container = ProviderContainer();
      addTearDown(container.dispose);
      final notifier = container.read(dashboardCardConfigProvider.notifier);
      final currentOrder =
          container.read(dashboardCardConfigProvider).cardOrder;
      notifier.setLayoutMode(DashboardCardLayoutMode.grid);
      notifier.toggleCardVisibility(DashboardCardIds.focus);
      notifier.reorderCards(
        currentOrder.indexOf(DashboardCardIds.longTermPlan),
        0,
      );
      await notifier.saveImmediate();
      await tester.pump(const Duration(milliseconds: 350));
      notifier.restoreDefaults();
      await tester.pump();
      await notifier.reload();
      await tester.pump(const Duration(milliseconds: 100));

      final restored = container.read(dashboardCardConfigProvider);
      expect(restored.layoutMode, DashboardCardLayoutMode.grid);
      expect(restored.visibleCardIds, contains(DashboardCardIds.focus));
      expect(restored.cardOrder.first, DashboardCardIds.longTermPlan);
      await tester.pump(const Duration(milliseconds: 700));
    });
  });
}

Future<void> _pumpPage(WidgetTester tester, Widget page) async {
  SharedPreferences.setMockInitialValues({});
  await ViewStorageService.ensureInitialized();

  final container = ProviderContainer(
    overrides: [
      authProvider.overrideWith((ref) => _FakeAuthNotifier()),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        localizationsDelegates: const [
          ...AppLocalizations.localizationsDelegates,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        supportedLocales: AppLocalizations.supportedLocales,
        home: page,
      ),
    ),
  );

  for (var i = 0; i < 8; i++) {
    await tester.pump(const Duration(milliseconds: 100));
  }
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(
      isAuthenticated: true,
      user: _buildUser(),
    );
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
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

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), _MemorySecureStorage());

  @override
  Future<bool> isLoggedIn() async => true;

  @override
  Future<UserModel> getCurrentUser() async => _buildUser();

  @override
  Future<void> logout({bool keepDemoMode = false}) async {}
}

class _UnusedApiClient implements ApiClient {
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
