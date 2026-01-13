import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/galaxy/presentation/screens/galaxy_screen.dart';
import 'package:sparkle/features/knowledge/presentation/screens/knowledge_detail_screen.dart';

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

class GalaxyRoutes {
  static const String galaxy = '/galaxy';
  static const String knowledgeDetail = '/galaxy/node/:id';

  static List<RouteBase> get routes => [
        GoRoute(
          path: galaxy,
          name: 'galaxy',
          pageBuilder: (context, state) => _buildTransitionPage(
            state: state,
            child: const GalaxyScreen(),
            type: SharedAxisTransitionType.scaled,
          ),
        ),
        GoRoute(
          path: knowledgeDetail,
          name: 'knowledgeDetail',
          pageBuilder: (context, state) {
            final nodeId = state.pathParameters['id'];
            return _buildTransitionPage(
              state: state,
              child: KnowledgeDetailScreen(nodeId: nodeId),
            );
          },
        ),
      ];
}
