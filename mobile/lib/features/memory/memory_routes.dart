import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/memory/memory.dart';

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

class MemoryRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/memory',
          name: 'memoryPanel',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const MemoryPanelScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: '/memory/settings',
          name: 'memorySettings',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const MemorySettingsScreen(),
            type: SharedAxisTransitionType.horizontal,
          ),
        ),
      ];
}
