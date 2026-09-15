import 'package:flutter/material.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/push_navigation_service.dart';
import '../../shared/i18n_test_helper.dart';

Widget _testRouterApp({required GoRouter routerConfig}) => MaterialApp.router(
  locale: const Locale('zh'),
  localizationsDelegates: const [
    AppLocalizations.delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
  ],
  supportedLocales: AppLocalizations.supportedLocales,
  routerConfig: routerConfig,
);

class _FakeInterventionActionService extends InterventionActionService {
  _FakeInterventionActionService() : super(_NoopRef());

  String? lastAction;
  String? lastSurface;
  Map<String, dynamic>? lastPayload;

  @override
  Future<void> reportActionFromPayload({
    required Map<String, dynamic> payload,
    required String action,
    required String surface,
    Map<String, dynamic>? extraPayload,
  }) async {
    lastAction = action;
    lastSurface = surface;
    lastPayload = <String, dynamic>{
      ...payload,
      ...?extraPayload,
    };
  }
}

class _NoopRef implements Ref {
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

GoRouter _buildRouter() => GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/home',
      routes: <RouteBase>[
        GoRoute(
          path: '/home',
          builder: (context, state) =>
              const Scaffold(body: Text('home-screen')),
        ),
        GoRoute(
          path: '/focus',
          builder: (context, state) =>
              const Scaffold(body: Text('focus-screen')),
        ),
        GoRoute(
          path: '/galaxy/node/:id',
          builder: (context, state) => Scaffold(
            body: Text(
              'galaxy-node-${state.pathParameters['id']}-${state.uri.queryParameters['review_mode'] ?? ''}',
            ),
          ),
        ),
        GoRoute(
          path: '/plans',
          builder: (context, state) =>
              const Scaffold(body: Text('plans-screen')),
        ),
        GoRoute(
          path: '/plans/:id',
          builder: (context, state) => Scaffold(
            body: Text(
              'plan-${state.pathParameters['id']}-${state.uri.queryParameters['source'] ?? ''}',
            ),
          ),
        ),
        GoRoute(
          path: '/tasks/:id/execute',
          builder: (context, state) => Scaffold(
            body: Text('task-execute-${state.pathParameters['id']}'),
          ),
        ),
        GoRoute(
          path: '/notification-center',
          builder: (context, state) => Scaffold(
            body: Text(
              'notification-${state.uri.queryParameters['highlight'] ?? ''}',
            ),
          ),
        ),
        GoRoute(
          path: '/achievements/milestone/:milestoneId',
          builder: (context, state) => Scaffold(
            body: Text('milestone-${state.pathParameters['milestoneId']}'),
          ),
        ),
        GoRoute(
          path: '/learning/insights',
          builder: (context, state) => Scaffold(
            body: Text(
              'insights-${state.uri.queryParameters['initialPanel'] ?? ''}',
            ),
          ),
        ),
        GoRoute(
          path: '/chat',
          builder: (context, state) => Scaffold(
            body: Text(
              'chat-${state.uri.queryParameters['entry'] ?? state.uri.queryParameters['chat_mode'] ?? ''}',
            ),
          ),
        ),
      ],
    );

void main() {

  setUp(setUpI18nForTesting);
  testWidgets('push navigation service reports seen and navigates to route',
      (tester) async {
    final fakeInterventionService = _FakeInterventionActionService();
    final router = _buildRouter();
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          interventionActionServiceProvider
              .overrideWithValue(fakeInterventionService),
        ],
        child: _testRouterApp(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.text('home-screen')),
      listen: false,
    );

    await container.read(pushNavigationServiceProvider).handleOpenedPayload(
      payload: <String, dynamic>{
        'destination_route': '/focus',
        'intervention_id': 'intervention-123',
      },
      source: 'widget_test',
    );
    await tester.pumpAndSettle();

    expect(find.text('focus-screen'), findsOneWidget);
    // Navigate back to home — handleOpenedPayload uses go() which replaces,
    // so there is no pop stack. Explicitly return to verify round-trip.
    router.go('/home');
    await tester.pumpAndSettle();
    expect(find.text('home-screen'), findsOneWidget);

    await container.read(pushNavigationServiceProvider).handleOpenedPayload(
      payload: <String, dynamic>{
        'destination_route': '/focus',
        'intervention_id': 'intervention-123',
      },
      source: 'widget_test',
    );
    await tester.pumpAndSettle();

    expect(find.text('focus-screen'), findsOneWidget);
    expect(fakeInterventionService.lastAction, 'seen');
    expect(fakeInterventionService.lastSurface, 'push_open');
    expect(
      fakeInterventionService.lastPayload?['intervention_id'],
      'intervention-123',
    );
    expect(fakeInterventionService.lastPayload?['source'], 'widget_test');
  });

  testWidgets(
    'push navigation service routes audited destination routes',
    (tester) async {
      final fakeInterventionService = _FakeInterventionActionService();
      final router = _buildRouter();
      addTearDown(router.dispose);

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            interventionActionServiceProvider
                .overrideWithValue(fakeInterventionService),
          ],
          child: _testRouterApp(routerConfig: router),
        ),
      );
      await tester.pumpAndSettle();

      final container = ProviderScope.containerOf(
        tester.element(find.text('home-screen')),
        listen: false,
      );

      final cases = <({String route, String expectedText})>[
        (
          route: '/plans/plan-42?source=push_sprint_reminder',
          expectedText: 'plan-plan-42-push_sprint_reminder',
        ),
        (
          route: '/plans/plan-7?source=comeback_nudge',
          expectedText: 'plan-plan-7-comeback_nudge',
        ),
        (
          route: '/achievements/milestone/30_day_learner?study_days=30',
          expectedText: 'milestone-30_day_learner',
        ),
        (
          route:
              '/learning/insights?initialPanel=weeklyNarrative&weekStart=2026-04-20',
          expectedText: 'insights-weeklyNarrative',
        ),
        (
          route: '/chat?entry=spaced_repetition',
          expectedText: 'chat-spaced_repetition',
        ),
      ];

      for (final testCase in cases) {
        await container.read(pushNavigationServiceProvider).handleOpenedPayload(
          payload: <String, dynamic>{
            'destination_route': testCase.route,
            'intervention_id': 'intervention-${testCase.expectedText}',
          },
          source: 'widget_test',
        );
        await tester.pumpAndSettle();

        expect(find.text(testCase.expectedText), findsOneWidget);
      }
    },
  );

  test('push navigation service parses debug uri payload', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final service = container.read(pushNavigationServiceProvider);
    final payload = service.payloadFromDebugUri(
      Uri.parse(
        'sparkle://push-open?destination_route=/focus&intervention_id=abc123',
      ),
    );

    expect(service.canHandleDebugUri(Uri.parse('sparkle://push-open')), isTrue);
    expect(payload['destination_route'], '/focus');
    expect(payload['intervention_id'], 'abc123');
  });

  test('push navigation service resolves JPush behavior context payloads', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final service = container.read(pushNavigationServiceProvider);

    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'goal_context':
            '{"goal_id":"goal-42","task_id":"task-42","deadline_pressure":"medium"}',
        'suggested_action':
            '{"type":"open_task","task_id":"task-42","estimated_minutes":5}',
      }),
      '/tasks/task-42/execute',
    );
    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'goal_context': '{"goal_id":"plan-42"}',
      }),
      '/plans/plan-42',
    );
    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'type': 'recall',
        'recall_type': 'task_not_started',
      }),
      '/chat?entry=recall&recall_type=task_not_started',
    );
    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'notification_id': 'notif-42',
      }),
      '/notification-center?highlight=notif-42',
    );
    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'deep_link': 'sparkle://task/task-7',
      }),
      '/tasks/task-7/execute',
    );
    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'deep_link': 'sparkle://chat/session-7',
      }),
      '/chat?session_id=session-7',
    );
    expect(
      service.resolveRouteForPayload(<String, dynamic>{
        'deep_link': 'sparkle://plan/plan-7/review',
      }),
      '/exam-sprint/review?plan_id=plan-7',
    );
  });

  testWidgets('push navigation service opens task from JPush extras',
      (tester) async {
    final fakeInterventionService = _FakeInterventionActionService();
    final router = _buildRouter();
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          interventionActionServiceProvider
              .overrideWithValue(fakeInterventionService),
        ],
        child: _testRouterApp(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.text('home-screen')),
      listen: false,
    );

    await container.read(pushNavigationServiceProvider).handleOpenedPayload(
      payload: <String, dynamic>{
        'goal_context': '{"task_id":"task-42"}',
        'suggested_action': '{"type":"open_task","task_id":"task-42"}',
      },
      source: 'jpush',
    );
    await tester.pumpAndSettle();

    expect(find.text('task-execute-task-42'), findsOneWidget);
    expect(fakeInterventionService.lastAction, 'seen');
    expect(fakeInterventionService.lastPayload?['source'], 'jpush');
  });

  testWidgets(
      'push navigation service opens review chat route with node context',
      (tester) async {
    final fakeInterventionService = _FakeInterventionActionService();
    final router = GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/home',
      routes: <RouteBase>[
        GoRoute(
          path: '/home',
          builder: (context, state) =>
              const Scaffold(body: Text('home-screen')),
        ),
        GoRoute(
          path: '/chat',
          builder: (context, state) => Scaffold(
            body: Text(
              'review:${state.uri.queryParameters['review_node']}|${state.uri.queryParameters['node_label']}',
            ),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          interventionActionServiceProvider
              .overrideWithValue(fakeInterventionService),
        ],
        child: _testRouterApp(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    final container = ProviderScope.containerOf(
      tester.element(find.text('home-screen')),
      listen: false,
    );

    await container.read(pushNavigationServiceProvider).handleOpenedPayload(
      payload: <String, dynamic>{
        'destination_route': Uri(
          path: '/chat',
          queryParameters: const <String, String>{
            'chat_mode': 'study_plan',
            'review_node': 'node-123',
            'node_label': 'TCP 流量控制',
            'prompt': '带我复习',
          },
        ).toString(),
      },
      source: 'widget_test',
    );
    await tester.pumpAndSettle();

    expect(find.text('review:node-123|TCP 流量控制'), findsOneWidget);
  });
}
