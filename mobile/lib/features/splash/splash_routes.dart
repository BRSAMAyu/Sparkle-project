import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/navigation/sparkle_route_transition.dart';
import 'package:sparkle/features/splash/splash.dart';

class SplashRoutes {
  static List<RouteBase> get routes => [
        GoRoute(
          path: '/',
          name: 'splash',
          pageBuilder: (context, state) => buildSparkleTransitionPage(
            state: state,
            child: const SplashScreen(),
            type: SharedAxisTransitionType.scaled,
            motionToken: SparkleMotionToken.scene,
          ),
        ),
      ];
}
