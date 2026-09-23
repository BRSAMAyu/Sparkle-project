import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/community/data/models/community_model.dart';
import 'package:sparkle/features/community/data/repositories/community_repository.dart';
import 'package:sparkle/features/community/presentation/widgets/groups_hub_view.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('GroupsHubView squads entry (NAV-IA P-4)', () {
    testWidgets('squads entry tile is visible and pushes /community/squads',
        (tester) async {
      final router = GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: '/groups-hub',
        routes: [
          GoRoute(
            path: '/groups-hub',
            builder: (_, __) => const Scaffold(body: GroupsHubView()),
          ),
          GoRoute(
            path: '/community/squads',
            builder: (_, __) =>
                const Scaffold(body: Center(child: Text('小队列表'))),
          ),
        ],
      );
      addTearDown(router.dispose);

      await _pumpHub(tester, router: router);

      // Community（Groups tab）首行「冲刺小队」入口——同伴关系的家内直达小队。
      expect(
        find.byKey(const ValueKey('community-squads-entry')),
        findsOneWidget,
      );
      expect(find.text('冲刺小队'), findsOneWidget);
      expect(find.text('组队冲刺，互盯完成度'), findsOneWidget);

      await tester
          .tap(find.byKey(const ValueKey('community-squads-entry')));
      await tester.pumpAndSettle();

      // push 后原屏在栈下不可见（offstage），以落点屏内容断言。
      expect(find.text('小队列表'), findsOneWidget);
    });
  });
}

Future<void> _pumpHub(
  WidgetTester tester, {
  required GoRouter router,
}) async {
  tester.view.physicalSize = const Size(390, 1200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        communityRepositoryProvider.overrideWithValue(
          _FakeCommunityRepository(),
        ),
      ],
      child: MaterialApp.router(
        theme: AppThemes.lightTheme,
        darkTheme: AppThemes.darkTheme,
        routerConfig: router,
        locale: const Locale('zh'),
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

class _FakeCommunityRepository extends CommunityRepository {
  _FakeCommunityRepository() : super(_UnusedApiClient());

  @override
  Future<List<GroupListItem>> getMyGroups() async => const [];

  @override
  Future<GroupDirectoryInfo> getGroupDirectory({
    String? keyword,
    GroupType? type,
    List<String>? tags,
    GroupDirectorySort sortBy = GroupDirectorySort.hot,
    int limit = 20,
    int offset = 0,
  }) async =>
      GroupDirectoryInfo(
        sortBy: sortBy,
        availableTags: const [],
        totalCount: 0,
        recommendations: const [],
        groups: const [],
      );

  @override
  Future<List<GroupRecommendationItem>> getGroupRecommendations({
    int limit = 20,
    int cursor = 0,
  }) async =>
      const [];
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
