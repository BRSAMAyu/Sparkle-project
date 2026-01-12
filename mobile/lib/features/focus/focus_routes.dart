import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
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
  static List<RouteBase> get routes => [
    GoRoute(
        path: '/focus',
        name: 'focus',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const FocusMainScreen(),
          type: SharedAxisTransitionType.scaled,
        ),
      ),
      GoRoute(
        path: '/focus/mindfulness/:id',
        name: 'mindfulness',
        pageBuilder: (context, state) {
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