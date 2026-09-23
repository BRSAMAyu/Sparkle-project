import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/view_storage_service.dart';
import 'package:sparkle/core/storage/token_storage.dart';
import 'package:sparkle/features/achievement/data/repositories/achievement_repository.dart';
import 'package:sparkle/features/achievement/presentation/providers/achievement_provider.dart';
import 'package:sparkle/features/auth/data/repositories/auth_repository.dart';
import 'package:sparkle/features/auth/presentation/providers/auth_provider.dart';
import 'package:sparkle/features/user/presentation/providers/profile_context_provider.dart';
import 'package:sparkle/features/user/presentation/screens/profile_screen.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';
import 'package:sparkle/shared/providers/visual_element_provider.dart';

import '../../shared/i18n_test_helper.dart';

/// V13-MAJORS M-03：光子面此前唯一链路是
/// 首页 metrics_row → 成就 → 连续记录 → 商城 → 兑换（深埋，且新用户空态连
/// metrics_row 都不渲染，实际不可达）。本卡在「我的」页个人成长区加直达
/// tile。本测试钉住：tile 可见（新用户空 profileContext 也渲染）且点击
/// 1 跳直达 /photon/redeem-pro。
void main() {
  setUp(setUpI18nForTesting);
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('profile growth section exposes one-hop photon redeem entry',
      (tester) async {
    SharedPreferences.setMockInitialValues({});
    await ViewStorageService.ensureInitialized();

    final container = ProviderContainer(
      overrides: [
        authProvider.overrideWith((ref) => _FakeAuthNotifier()),
        achievementProvider.overrideWith(
          (ref) => _FakeAchievementNotifier(
            AchievementState.loading().copyWith(
              achievements: const [],
              isLoading: false,
            ),
          ),
        ),
        visualElementProvider.overrideWith(
          (ref) => VisualElementNotifier(_UnusedApiClient()),
        ),
        // 空上下文 = 新注册零数据用户的面貌。
        profileContextProvider.overrideWith((ref) async => <String, dynamic>{}),
      ],
    );
    addTearDown(container.dispose);

    final router = GoRouter(
      initialLocation: '/profile',
      routes: [
        GoRoute(
          path: '/profile',
          builder: (context, state) => const ProfileScreen(),
        ),
        GoRoute(
          path: '/photon/redeem-pro',
          pageBuilder: (context, state) => const NoTransitionPage<void>(
            child: Scaffold(body: Center(child: Text('PHOTON_REDEEM_STUB'))),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(
          routerConfig: router,
          locale: const Locale('zh'),
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          supportedLocales: AppLocalizations.supportedLocales,
        ),
      ),
    );
    for (var i = 0; i < 8; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }

    // 空数据新用户也能看到入口（无条件渲染，不依赖任何学习状态）。
    final tile = find.text('光子兑换');
    expect(tile, findsOneWidget);

    // 1 跳直达光子兑 Pro。
    await tester.ensureVisible(tile);
    await tester.pump();
    await tester.tap(tile);
    for (var i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    expect(find.text('PHOTON_REDEEM_STUB'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}

class _FakeAchievementNotifier extends AchievementNotifier {
  _FakeAchievementNotifier(AchievementState initialState)
      : super(_UnusedAchievementRepository(), _UnusedRef()) {
    state = initialState;
  }

  @override
  Future<void> loadInitialData() async {}
}

class _FakeAuthNotifier extends AuthNotifier {
  _FakeAuthNotifier() : super(_UnusedRef(), _UnusedAuthRepository()) {
    state = AuthState(isAuthenticated: true, user: _buildUser());
  }

  @override
  Future<void> checkAuthStatus() async {}
}

class _UnusedAchievementRepository extends AchievementRepository {
  _UnusedAchievementRepository() : super(_UnusedApiClient());
}

class _UnusedAuthRepository extends AuthRepository {
  _UnusedAuthRepository() : super(_UnusedApiClient(), _UnusedTokenStorage());
}

class _UnusedRef implements Ref<Object?> {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _UnusedTokenStorage implements TokenStorage {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

UserModel _buildUser() => UserModel(
      id: '00000000-0000-0000-0000-000000000043',
      username: 'photon_entry_user',
      email: 'photon@example.com',
      nickname: 'Photon Entry',
      flameLevel: 1,
      flameBrightness: 0.5,
      depthPreference: 0.5,
      curiosityPreference: 0.5,
      isActive: true,
      createdAt: DateTime(2026),
      updatedAt: DateTime(2026),
    );
