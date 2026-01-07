import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/user/user.dart';

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

class UserRoutes {
  static List<RouteBase> get routes => [
    GoRoute(
        path: '/settings/learning-mode',
        name: 'learningMode',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const LearningModeScreen(),
        ),
      ),
      // Add more user routes as needed
  ];
}
