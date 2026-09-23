import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';
import 'package:sparkle/features/chat/chat_routes.dart';
import 'package:sparkle/features/chat/presentation/screens/chat_settings_screen.dart';
import 'package:sparkle/features/seed_library/data/models/seed_library_model.dart';
import 'package:sparkle/features/seed_library/data/repositories/seed_library_repository.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);

  setUpAll(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('ChatSettingsScreen (NAV-IA P-1 死链修复)', () {
    testWidgets(
        'renders all settings sections without the dead transparency entry',
        (tester) async {
      final prefs = await SharedPreferences.getInstance();
      await _pumpChatSettings(tester, prefs: prefs);

      // 页面其余设置项照常渲染（不整页破坏）。
      expect(find.text('对话体验'), findsOneWidget);
      expect(find.text('种子库'), findsOneWidget);

      // 死链入口已移除：「打开高级设置」曾 push 未注册路由
      // /settings/transparency，点击必落 404（NAV-IA A-1/P-1）。
      expect(find.text('打开高级设置'), findsNothing);
      expect(find.text('进入透明模式的详细配置页面。'), findsNothing);
    });

    testWidgets(
        'route /settings/transparency is not registered anywhere in ChatRoutes',
        (tester) async {
      // 双保险：全路由表中不存在该路径（grep = 0 的测试化表达）。
      expect(
        _registeredPaths(ChatRoutes.routes.toList()),
        isNot(contains('/settings/transparency')),
      );
    });
  });
}

Set<String> _registeredPaths(List<RouteBase> routes) {
  final paths = <String>{};
  void walk(List<RouteBase> routes) {
    for (final route in routes) {
      if (route is GoRoute) {
        if (route.path.startsWith('/')) paths.add(route.path);
        walk(route.routes);
      }
    }
  }

  walk(routes);
  return paths;
}

Future<void> _pumpChatSettings(
  WidgetTester tester, {
  required SharedPreferences prefs,
}) async {
  tester.view.physicalSize = const Size(390, 1600);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        userPreferencesServiceProvider
            .overrideWithValue(UserPreferencesService(prefs)),
        seedLibraryRepositoryProvider.overrideWithValue(
          _FakeSeedLibraryRepository(),
        ),
      ],
      child: testMaterialApp(home: const ChatSettingsScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

class _FakeSeedLibraryRepository extends SeedLibraryRepository {
  _FakeSeedLibraryRepository() : super(_UnusedApiClient());

  @override
  Future<PaginatedResponse<UserLibrarySubscription>> getMySubscriptions({
    bool? isEnabled,
    int page = 1,
    int pageSize = 20,
  }) async =>
      PaginatedResponse<UserLibrarySubscription>(
        items: const [],
        total: 0,
        page: 1,
        pageSize: pageSize,
        totalPages: 1,
      );
}

class _UnusedApiClient extends ApiClient {
  _UnusedApiClient() : super(_UnusedRef());
}

class _UnusedRef implements Ref {
  @override
  T read<T>(ProviderListenable<T> provider) {
    if (T == Interceptor) {
      return InterceptorsWrapper() as T;
    }
    throw UnimplementedError('Unsupported read for $provider');
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}
