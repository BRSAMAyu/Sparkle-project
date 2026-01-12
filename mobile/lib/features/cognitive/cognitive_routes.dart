import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/cognitive/cognitive.dart';

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

class CognitiveRoutes {
  static List<RouteBase> get routes => [
    GoRoute(
        path: '/cognitive/patterns',
        name: 'patternList',
        pageBuilder: (context, state) {
          final highlightId = state.uri.queryParameters['highlight'];
          return _buildTransitionPage(
            state: state,
            child: PatternListScreen(highlightId: highlightId),
          );
        },
      ),
      GoRoute(
        path: '/curiosity-capsule',
        name: 'curiosityCapsule',
        pageBuilder: (context, state) {
          final highlightId = state.uri.queryParameters['highlight'];
          return _buildTransitionPage(
            state: state,
            child: CuriosityCapsuleScreen(highlightId: highlightId),
          );
        },
      ),
  ];
}
