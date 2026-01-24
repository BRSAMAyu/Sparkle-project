import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/focus/presentation/screens/focus_main_screen.dart';
import 'package:sparkle/features/focus/presentation/screens/mindfulness_mode_screen.dart';

Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionsBuilder: (context, animation, secondaryAnimation, child) =>
          SharedAxisTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        transitionType: type,
        child: child,
      ),
    );

class FocusRoutes {
  // Route constants for deep linking and navigation
  static const String home = '/focus';
  static const String mindfulness = '/focus/mindfulness/:id';

  static List<RouteBase> get routes => [
    // Focus main screen (detail page, full-screen)
    GoRoute(
        path: home,
        name: 'focus',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const FocusMainScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
    // Mindfulness mode (modal-like, full-screen)
    GoRoute(
        path: mindfulness,
        name: 'mindfulness',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) {
          // id is a required path parameter, so it won't be null
          final taskId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: MindfulnessModeScreen(taskId: taskId),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
  ];
}
