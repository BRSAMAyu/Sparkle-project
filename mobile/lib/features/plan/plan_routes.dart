import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/plan/presentation/screens/growth_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_create_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_edit_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_screen.dart';

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

class PlanRoutes {
  static List<RouteBase> get routes => [
    GoRoute(
        path: '/plans/new',
        name: 'createPlan',
        pageBuilder: (context, state) {
          final planType = state.uri.queryParameters['type'];
          return _buildTransitionPage(
            state: state,
            child: PlanCreateScreen(planType: planType),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
      GoRoute(
        path: '/plans/:id',
        name: 'planDetail',
        pageBuilder: (context, state) {
          final planId = state.pathParameters['id'];
          return _buildTransitionPage(
            state: state,
            child: PlanDetailScreen(planId: planId),
          );
        },
      ),
      GoRoute(
        path: '/plans/:id/edit',
        name: 'editPlan',
        pageBuilder: (context, state) {
          final planId = state.pathParameters['id'];
          return _buildTransitionPage(
            state: state,
            child: PlanEditScreen(planId: planId),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
      GoRoute(
        path: '/plans', // Alias for sprint for now or a main plan screen if created
        name: 'plans',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintScreen(),
        ),
      ),
      GoRoute(
        path: '/sprint',
        name: 'sprint',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintScreen(),
        ),
      ),
      GoRoute(
        path: '/growth',
        name: 'growth',
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GrowthScreen(),
        ),
      ),
  ];
}
