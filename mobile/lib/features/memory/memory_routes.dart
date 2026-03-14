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
  static const String panel = '/memory';
  static const String settings = '/memory/settings';
  static const String detail = '/memory/detail';

  static void popOrGoPanel(BuildContext context, {String fallback = panel}) {
    final navigator = Navigator.of(context);
    if (navigator.canPop()) {
      context.pop();
      return;
    }
    context.go(fallback);
  }

  static List<RouteBase> get routes => [
        GoRoute(
          path: panel,
          name: 'memoryPanel',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const MemoryPanelScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: settings,
          name: 'memorySettings',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const MemorySettingsScreen(),
          ),
        ),
        GoRoute(
          path: detail,
          name: 'memoryDetail',
          pageBuilder: (context, state) {
            final args = state.extra;
            if (args is! MemoryDetailArgs) {
              return _buildTransitionPage(
                state: state,
                child: const Scaffold(
                  body: Center(child: Text('记忆详情参数缺失')),
                ),
              );
            }
            return _buildTransitionPage(
              state: state,
              child: MemoryDetailScreen(args: args),
            );
          },
        ),
      ];
}
