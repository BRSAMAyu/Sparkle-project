import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/chat/data/services/message_notification_service.dart';
import 'package:sparkle/features/home/data/models/notification_model.dart';
import 'package:sparkle/features/home/data/repositories/notification_repository.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/home/presentation/widgets/home_notification_card.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import '../../../../shared/i18n_test_helper.dart';

void main() {
  setUp(setUpI18nForTesting);
  tearDown(tearDownI18n);

  group('HomeNotificationCard (NAV-IA P-3 通知落点统一)', () {
    testWidgets('unread banner pushes /notification-center, not legacy path',
        (tester) async {
      final router = GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: '/home',
        routes: [
          GoRoute(
            path: '/home',
            builder: (_, __) => const Scaffold(body: HomeNotificationCard()),
          ),
          GoRoute(
            path: '/notification-center',
            builder: (_, __) =>
                const Scaffold(body: Center(child: Text('通知中心'))),
          ),
        ],
      );
      addTearDown(router.dispose);

      await _pumpCard(tester, router: router);

      // 有未读通知：banner 可见（「查看详情」动作）。
      expect(find.textContaining('查看详情'), findsOneWidget);

      await tester.tap(find.textContaining('查看详情'));
      await tester.pumpAndSettle();

      // 通知落点唯一：与推送侧一致指向 /notification-center（老路径
      // /notifications 已降级为 redirect，不再作为 push 目标）。
      // push 后原屏在栈下不可见（offstage），以落点屏内容断言。
      expect(find.text('通知中心'), findsOneWidget);
      expect(find.textContaining('未读通知'), findsNothing);
    });

    testWidgets('legacy /notifications redirects to /notification-center',
        (tester) async {
      final router = GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: '/notifications',
        routes: [
          ...HomeRoutes.routes,
          GoRoute(
            path: '/notification-center',
            builder: (_, __) =>
                const Scaffold(body: Center(child: Text('通知中心'))),
          ),
        ],
      );
      addTearDown(router.dispose);

      await tester.pumpWidget(
        ProviderScope(
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

      // 老路径可达（redirect 模式照 chat legacy redirect），落同一屏。
      expect(
        router.routeInformationProvider.value.uri.path,
        '/notification-center',
      );
      expect(find.text('通知中心'), findsOneWidget);
    });

    testWidgets('unread messages banner keeps community tab destination',
        (tester) async {
      final router = GoRouter(
        navigatorKey: navigatorKey,
        initialLocation: '/home',
        routes: [
          GoRoute(
            path: '/home',
            builder: (_, __) => const Scaffold(body: HomeNotificationCard()),
          ),
          GoRoute(
            path: '/community',
            builder: (_, __) => const Scaffold(body: Center(child: Text('社群'))),
          ),
        ],
      );
      addTearDown(router.dispose);

      // 私信/群聊未读 > 0 时 banner 指向 Community tab（既有语义，不回归）。
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            unreadMessageCountProvider.overrideWith(
              (ref) => UnreadMessageCountNotifier()..add(3),
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

      expect(find.textContaining('3'), findsOneWidget);
      await tester.tap(find.textContaining('查看详情'));
      await tester.pumpAndSettle();

      expect(
        router.routeInformationProvider.value.uri.path,
        '/community',
      );
    });
  });
}

Future<void> _pumpCard(
  WidgetTester tester, {
  required GoRouter router,
}) async {
  tester.view.physicalSize = const Size(390, 800);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        notificationRepositoryProvider.overrideWithValue(
          _FakeNotificationRepository([
            NotificationModel(
              id: 'n1',
              userId: 'u1',
              title: '周报',
              content: '查看本周成长',
              type: 'weekly_growth_narrative',
              isRead: false,
              createdAt: DateTime(2026, 9, 21),
            ),
          ]),
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

class _FakeNotificationRepository extends NotificationRepository {
  _FakeNotificationRepository(this.notifications) : super(_FakeApiClient());

  final List<NotificationModel> notifications;

  @override
  Future<List<NotificationModel>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
  }) async =>
      notifications;

  @override
  Future<void> markAsRead(String id) async {}
}

class _FakeApiClient implements ApiClient {
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnimplementedError();
}
