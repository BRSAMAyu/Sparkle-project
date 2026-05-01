import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/splash/splash.dart';

Page<dynamic> _buildTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
}) =>
    CustomTransitionPage<void>(
      key: state.pageKey,
      child: child,
      transitionDuration: const Duration(milliseconds: 400),
      reverseTransitionDuration: const Duration(milliseconds: 220),
      transitionsBuilder: (context, animation, secondaryAnimation, child) {
        final entering = buildSharedAxisCompatibleTransition(
          animation: animation,
          type: type,
          child: child,
        );

        return FadeTransition(
          opacity: Tween<double>(begin: 1, end: 0).animate(
            CurvedAnimation(
              parent: secondaryAnimation,
              curve: Curves.easeOutCubic,
              reverseCurve: Curves.easeInCubic,
            ),
          ),
          child: entering,
        );
      },
    );

class SplashRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/',
          name: 'splash',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const SplashScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
      ];
}
