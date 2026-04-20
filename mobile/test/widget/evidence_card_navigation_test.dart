import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/features/memory/presentation/widgets/evidence_cards.dart';

void main() {
  testWidgets('concept evidence routes to galaxy detail', (tester) async {
    final routed = <String>[];
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: EvidenceCard(
              item: EvidenceResolveItem(
                type: 'concept',
                id: 'node-1',
                status: 'ok',
                payload: const {
                  'concept': {
                    'id': 'node-1',
                    'name': '热力学第二定律',
                    'description': '需要再稳一点',
                  },
                },
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/galaxy/node/:id',
          builder: (context, state) {
            routed.add('/galaxy/node/${state.pathParameters['id']}');
            return Scaffold(body: Text('galaxy:${state.pathParameters['id']}'));
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.tap(find.text('去星图看'));
    await tester.pumpAndSettle();

    expect(find.text('galaxy:node-1'), findsOneWidget);
    expect(routed, ['/galaxy/node/node-1']);
  });

  testWidgets('error evidence routes to error detail', (tester) async {
    final routed = <String>[];
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: EvidenceCard(
              item: EvidenceResolveItem(
                type: 'error',
                id: 'err-1',
                status: 'ok',
                payload: const {
                  'error': {
                    'id': 'err-1',
                    'subject_code': 'PHY',
                    'root_cause': '概念混淆',
                    'study_suggestion': '回看错题',
                  },
                },
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/errors/:id',
          builder: (context, state) {
            routed.add('/errors/${state.pathParameters['id']}');
            return Scaffold(body: Text('error:${state.pathParameters['id']}'));
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.tap(find.text('去错题本看'));
    await tester.pumpAndSettle();

    expect(find.text('error:err-1'), findsOneWidget);
    expect(routed, ['/errors/err-1']);
  });

  testWidgets('event evidence routes to chat session when session marker exists', (
    tester,
  ) async {
    final routed = <String>[];
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: EvidenceCard(
              item: EvidenceResolveItem(
                type: 'event',
                id: 'evt-1',
                status: 'ok',
                payload: const {
                  'event': {
                    'event_type': 'chat_follow_up',
                    'ts_ms': 12345,
                    'payload': {
                      'session_id': 'session-9',
                    },
                  },
                },
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/chat',
          builder: (context, state) {
            final sessionId = state.uri.queryParameters['session_id'] ?? '';
            routed.add('/chat?session_id=$sessionId');
            return Scaffold(body: Text('chat:$sessionId'));
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.tap(find.text('打开相关对话'));
    await tester.pumpAndSettle();

    expect(find.text('chat:session-9'), findsOneWidget);
    expect(routed, ['/chat?session_id=session-9']);
  });

  testWidgets('chat turn evidence routes to original chat session', (tester) async {
    final routed = <String>[];
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: EvidenceCard(
              item: EvidenceResolveItem(
                type: 'chat_turn',
                id: 'turn-1',
                status: 'ok',
                payload: const {
                  'chat_turn': {
                    'id': 'turn-1',
                    'session_id': 'session-42',
                    'role': 'user',
                    'content': '最近我在整理线代错题',
                  },
                },
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/chat',
          builder: (context, state) {
            final sessionId = state.uri.queryParameters['session_id'] ?? '';
            routed.add('/chat?session_id=$sessionId');
            return Scaffold(body: Text('chat:$sessionId'));
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.tap(find.text('打开原对话'));
    await tester.pumpAndSettle();

    expect(find.text('chat:session-42'), findsOneWidget);
    expect(routed, ['/chat?session_id=session-42']);
  });

  testWidgets('unsupported evidence stays non-routable', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: EvidenceCard(
            item: EvidenceResolveItem(
              type: 'summary',
              id: 'summary-1',
              status: 'ok',
              payload: const {
                'summary': {
                  'id': 'summary-1',
                  'review_date': '2026-04-20',
                  'summary_text': '周报',
                },
              },
            ),
          ),
        ),
      ),
    );

    expect(find.text('去星图看'), findsNothing);
    expect(find.text('去错题本看'), findsNothing);
    expect(find.text('打开相关对话'), findsNothing);
  });

  testWidgets('practice outcome evidence routes to error detail', (tester) async {
    final routed = <String>[];
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => Scaffold(
            body: EvidenceCard(
              item: EvidenceResolveItem(
                type: 'practice_outcome',
                id: 'err-2',
                status: 'ok',
                payload: const {
                  'practice_outcome': {
                    'error_id': 'err-2',
                    'review_performance': 'remembered',
                    'mastery_level': 0.7,
                    'reviewed_at': '2026-04-20T12:00:00',
                    'summary': '错题复习结果：remembered',
                  },
                },
              ),
            ),
          ),
        ),
        GoRoute(
          path: '/errors/:id',
          builder: (context, state) {
            routed.add('/errors/${state.pathParameters['id']}');
            return Scaffold(body: Text('error:${state.pathParameters['id']}'));
          },
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    await tester.tap(find.text('回到错题本看'));
    await tester.pumpAndSettle();

    expect(find.text('error:err-2'), findsOneWidget);
    expect(routed, ['/errors/err-2']);
  });
}
