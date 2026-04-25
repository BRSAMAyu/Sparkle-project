import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/features/galaxy/galaxy_routes.dart';
import 'package:sparkle/features/home/home_routes.dart';
import 'package:sparkle/features/plan/plan_routes.dart';
import 'package:sparkle/features/task/task_routes.dart';
import 'package:sparkle/features/user/user_routes.dart';

class RouteResilienceScope extends StatelessWidget {
  const RouteResilienceScope({
    required this.fallbackRoute,
    required this.child,
    super.key,
  });

  final String fallbackRoute;
  final Widget child;

  @override
  Widget build(BuildContext context) => PopScope<void>(
        canPop: false,
        onPopInvokedWithResult: (didPop, result) {
          if (didPop) {
            return;
          }
          RouteResilience.popOrGo(context, fallbackRoute: fallbackRoute);
        },
        child: child,
      );
}

class RouteResilience {
  RouteResilience._();

  static void popOrGo(
    BuildContext context, {
    required String fallbackRoute,
  }) {
    final router = GoRouter.of(context);
    if (router.canPop()) {
      router.pop();
      return;
    }
    router.go(fallbackRoute);
  }

  static Future<void> openExternalRoute(
    BuildContext context,
    String route, {
    String? fallbackRoute,
    BuildContext? Function()? currentContextLookup,
  }) async {
    final router = GoRouter.of(context);
    final effectiveFallback =
        fallbackRoute ?? fallbackRouteForExternalRoute(route);

    if (_matchesExactly(route, effectiveFallback)) {
      router.go(route);
      return;
    }

    router.go(effectiveFallback);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final nextContext = currentContextLookup?.call() ?? context;
      if (!nextContext.mounted) {
        return;
      }
      unawaited(GoRouter.of(nextContext).push(route));
    });
  }

  static String fallbackRouteForExternalRoute(String route) {
    final path = Uri.tryParse(route)?.path ?? route;

    if (path == PlanRoutes.learningPortfolio) {
      return UserRoutes.profile;
    }
    if (path.startsWith('/profile')) {
      return UserRoutes.profile;
    }
    if (path.startsWith('/galaxy')) {
      return GalaxyRoutes.home;
    }
    if (path.startsWith('/tasks')) {
      return TaskRoutes.home;
    }
    if (path.startsWith('/plans') ||
        path == PlanRoutes.sprint ||
        path == PlanRoutes.sprintHistory ||
        path == PlanRoutes.growth ||
        path.startsWith('/exam-sprint')) {
      return PlanRoutes.home;
    }
    if (path.startsWith('/chat')) {
      return HomeRoutes.home;
    }

    return HomeRoutes.home;
  }

  static bool _matchesExactly(String route, String fallbackRoute) {
    final routeUri = Uri.tryParse(route);
    final fallbackUri = Uri.tryParse(fallbackRoute);
    if (routeUri == null || fallbackUri == null) {
      return route == fallbackRoute;
    }
    return routeUri.path == fallbackUri.path &&
        routeUri.query == fallbackUri.query;
  }
}
