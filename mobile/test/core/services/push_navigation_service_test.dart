import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/intervention_action_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/push_navigation_service.dart';

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

void main() {
  testWidgets('push navigation service reports seen and navigates to route',
      (tester) async {
    final fakeInterventionService = _FakeInterventionActionService();
    final router = GoRouter(
      navigatorKey: navigatorKey,
      initialLocation: '/',
      routes: <RouteBase>[
        GoRoute(
          path: '/',
          builder: (context, state) =>
              const Scaffold(body: Text('home-screen')),
        ),
        GoRoute(
          path: '/focus',
          builder: (context, state) =>
              const Scaffold(body: Text('focus-screen')),
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
        child: MaterialApp.router(routerConfig: router),
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
    expect(fakeInterventionService.lastAction, 'seen');
    expect(fakeInterventionService.lastSurface, 'push_open');
    expect(
      fakeInterventionService.lastPayload?['intervention_id'],
      'intervention-123',
    );
    expect(fakeInterventionService.lastPayload?['source'], 'widget_test');
  });

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
}
