import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

Widget buildSharedAxisCompatibleTransition({
  required Animation<double> animation,
  required SharedAxisTransitionType type,
  required Widget child,
  Curve curve = Curves.easeOutCubic,
  Curve reverseCurve = Curves.easeInCubic,
  double fadeBegin = 0.84,
}) {
  final curvedAnimation = CurvedAnimation(
    parent: animation,
    curve: curve,
    reverseCurve: reverseCurve,
  );

  final fadedChild = FadeTransition(
    opacity: Tween<double>(begin: fadeBegin, end: 1).animate(curvedAnimation),
    child: child,
  );

  return switch (type) {
    SharedAxisTransitionType.scaled => ScaleTransition(
        scale: Tween<double>(begin: 0.96, end: 1).animate(curvedAnimation),
        child: fadedChild,
      ),
    SharedAxisTransitionType.vertical => SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, 0.04),
          end: Offset.zero,
        ).animate(curvedAnimation),
        child: fadedChild,
      ),
    SharedAxisTransitionType.horizontal => SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0.05, 0),
          end: Offset.zero,
        ).animate(curvedAnimation),
        child: fadedChild,
      ),
  };
}

Page<dynamic> buildSparkleTransitionPage({
  required GoRouterState state,
  required Widget child,
  SharedAxisTransitionType type = SharedAxisTransitionType.horizontal,
  SparkleMotionToken motionToken = SparkleMotionToken.standard,
}) {
  final reduceMotion = WidgetsBinding
      .instance.platformDispatcher.accessibilityFeatures.disableAnimations;
  final forwardDuration = reduceMotion
      ? const Duration(milliseconds: 140)
      : switch (motionToken) {
          SparkleMotionToken.micro => const Duration(milliseconds: 150),
          SparkleMotionToken.standard => const Duration(milliseconds: 220),
          SparkleMotionToken.scene => const Duration(milliseconds: 280),
          SparkleMotionToken.hero => const Duration(milliseconds: 320),
        };
  final reverseDuration = reduceMotion
      ? const Duration(milliseconds: 120)
      : switch (motionToken) {
          SparkleMotionToken.micro => const Duration(milliseconds: 120),
          SparkleMotionToken.standard => const Duration(milliseconds: 170),
          SparkleMotionToken.scene => const Duration(milliseconds: 220),
          SparkleMotionToken.hero => const Duration(milliseconds: 250),
        };

  return CustomTransitionPage<void>(
    key: state.pageKey,
    transitionDuration: forwardDuration,
    reverseTransitionDuration: reverseDuration,
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      if (reduceMotion) {
        return FadeTransition(
          opacity: Tween<double>(begin: 0.92, end: 1).animate(
            CurvedAnimation(
              parent: animation,
              curve: Curves.easeOutCubic,
              reverseCurve: Curves.easeOutCubic,
            ),
          ),
          child: child,
        );
      }

      final curve = motionToken == SparkleMotionToken.scene
          ? Curves.easeOutQuart
          : DS.motionCurve(motionToken);
      final fadeBegin = switch (motionToken) {
        SparkleMotionToken.micro => 0.9,
        SparkleMotionToken.standard => 0.84,
        SparkleMotionToken.scene => 0.78,
        SparkleMotionToken.hero => 0.72,
      };
      return buildSharedAxisCompatibleTransition(
        animation: animation,
        type: type,
        fadeBegin: fadeBegin,
        curve: curve,
        child: child,
      );
    },
  );
}
