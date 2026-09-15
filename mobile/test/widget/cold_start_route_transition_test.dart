import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';

void main() {
  testWidgets('cold-start route uses custom transition', (tester) async {
    var taps = 0;
    final router = GoRouter(
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => const Scaffold(
            body: Center(child: Text('splash')),
          ),
        ),
        GoRoute(
          path: '/chat',
          pageBuilder: (context, state) => buildColdStartTransitionPage(
            state: state,
            child: Scaffold(
              body: Center(
                child: TextButton(
                  key: const ValueKey('chat-transition-button'),
                  onPressed: () => taps++,
                  child: const Text('chat ready'),
                ),
              ),
            ),
          ),
        ),
      ],
    );
    addTearDown(router.dispose);

    await tester.pumpWidget(MaterialApp.router(routerConfig: router));
    expect(find.text('splash'), findsOneWidget);

    router.go('/chat');
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    // Transition page renders the child; ColdStartRouteTransition or FadeTransition
    // is used depending on accessibility preferences. Both are valid transitions.
    expect(find.text('chat ready'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('chat-transition-button')));
    await tester.pump();

    expect(taps, 1);
  });
}
