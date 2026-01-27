import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/plan/presentation/screens/growth_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_create_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_detail_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_edit_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/plan_history_screen.dart';
import 'package:sparkle/features/plan/presentation/screens/sprint_history_screen.dart';
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
  // Route constants for deep linking and navigation
  static const String home = '/plans';
  static const String planCreate = '/plans/new';
  static const String planDetail = '/plans/:id';
  static const String planEdit = '/plans/:id/edit';
  static const String planHistory = '/plans/history';
  static const String sprint = '/sprint';
  static const String sprintHistory = '/sprint/history';
  static const String growth = '/growth';

  static List<RouteBase> get routes => [
    // Plan create (modal-like, full-screen)
    GoRoute(
        path: planCreate,
        name: 'createPlan',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) {
          final planType = state.uri.queryParameters['type'];
          return _buildTransitionPage(
            state: state,
            child: PlanCreateScreen(planType: planType),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
    // Plan detail (full-screen, uses root navigator)
    GoRoute(
        path: planDetail,
        name: 'planDetail',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) {
          // id is a required path parameter, so it won't be null
          final planId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: PlanDetailScreen(planId: planId),
          );
        },
      ),
    // Plan edit (modal-like, full-screen)
    GoRoute(
        path: planEdit,
        name: 'editPlan',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) {
          // id is a required path parameter, so it won't be null
          final planId = state.pathParameters['id']!;
          return _buildTransitionPage(
            state: state,
            child: PlanEditScreen(planId: planId),
            type: SharedAxisTransitionType.scaled,
          );
        },
      ),
    GoRoute(
        path: planHistory,
        name: 'planHistory',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const PlanHistoryScreen(),
        ),
      ),
    // Plans list / Sprint screen (detail page, full-screen)
    GoRoute(
        path: home,
        name: 'plans',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintScreen(),
        ),
      ),
    // Sprint alias (detail page, full-screen)
    GoRoute(
        path: sprint,
        name: 'sprint',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintScreen(),
        ),
      ),
    // Sprint history (detail page, full-screen)
    GoRoute(
        path: sprintHistory,
        name: 'sprintHistory',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const SprintHistoryScreen(),
        ),
      ),
    // Growth screen (detail page, full-screen)
    GoRoute(
        path: growth,
        name: 'growth',
        parentNavigatorKey: navigatorKey,
        pageBuilder: (context, state) => _buildTransitionPage(
          state: state,
          child: const GrowthScreen(),
        ),
      ),
  ];
}
