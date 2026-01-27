import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/notification_center/notification_center.dart';

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

class NotificationCenterRoutes {
  static List<RouteBase> get routes => [
    GoRoute(
      path: '/notification-center',
      name: 'notificationCenter',
      pageBuilder: (context, state) => _buildTransitionPage(
        state: state,
        child: const NotificationCenterScreen(),
        type: SharedAxisTransitionType.scaled,
      ),
    ),
    GoRoute(
      path: '/notification-analytics',
      name: 'notificationAnalytics',
      pageBuilder: (context, state) => _buildTransitionPage(
        state: state,
        child: const NotificationAnalyticsScreen(),
        type: SharedAxisTransitionType.scaled,
      ),
    ),
  ];
}
