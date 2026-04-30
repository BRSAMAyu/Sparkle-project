import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/home/data/models/notification_model.dart';
import 'package:sparkle/features/home/data/repositories/notification_repository.dart';
import 'package:sparkle/features/home/presentation/screens/notification_list_screen.dart';
import '../shared/i18n_test_helper.dart';

void main() {

  setUp(setUpI18nForTesting);
  testWidgets(
      'notification list opens destination routes through resilient navigation',
      (tester) async {
    final router = GoRouter(
      initialLocation: '/notifications',
      routes: [
        GoRoute(
          path: '/home',
          builder: (context, state) => const Scaffold(body: Text('Home')),
        ),
        GoRoute(
          path: '/notifications',
          builder: (context, state) => const NotificationListScreen(),
        ),
        GoRoute(
          path: '/learning/insights',
          builder: (context, state) => const Scaffold(body: Text('Insights')),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          notificationRepositoryProvider.overrideWithValue(
            _FakeNotificationRepository(
              [
                NotificationModel(
                  id: 'n1',
                  userId: 'u1',
                  title: 'Weekly',
                  content: 'Open report',
                  type: 'weekly_growth_narrative',
                  isRead: false,
                  createdAt: DateTime(2026, 4, 26),
                  data: const {
                    'destination_route':
                        '/learning/insights?initialPanel=weeklyNarrative',
                  },
                ),
              ],
            ),
          ),
        ],
        child: MaterialApp.router(
          theme: AppThemes.lightTheme,
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
    await tester.pumpAndSettle();

    await tester.tap(find.text('Weekly'));
    await tester.pumpAndSettle();

    expect(find.text('Insights'), findsOneWidget);
    expect(
      router.routeInformationProvider.value.uri.path,
      '/learning/insights',
    );
    expect(
      router.routeInformationProvider.value.uri.queryParameters['initialPanel'],
      'weeklyNarrative',
    );
  });
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
