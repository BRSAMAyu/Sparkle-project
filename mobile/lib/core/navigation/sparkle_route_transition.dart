import 'package:animations/animations.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';

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
          SparkleMotionToken.micro => const Duration(milliseconds: 220),
          SparkleMotionToken.standard => const Duration(milliseconds: 320),
          SparkleMotionToken.scene => const Duration(milliseconds: 500),
          SparkleMotionToken.hero => const Duration(milliseconds: 560),
        };
  final reverseDuration = reduceMotion
      ? const Duration(milliseconds: 120)
      : switch (motionToken) {
          SparkleMotionToken.micro => const Duration(milliseconds: 180),
          SparkleMotionToken.standard => const Duration(milliseconds: 260),
          SparkleMotionToken.scene => const Duration(milliseconds: 420),
          SparkleMotionToken.hero => const Duration(milliseconds: 460),
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
      final curvedAnimation = CurvedAnimation(
        parent: animation,
        curve: curve,
        reverseCurve: Curves.easeInCubic,
      );

      return FadeTransition(
        opacity: Tween<double>(begin: fadeBegin, end: 1).animate(
          curvedAnimation,
        ),
        child: SharedAxisTransition(
          animation: curvedAnimation,
          secondaryAnimation: secondaryAnimation,
          transitionType: type,
          fillColor: Colors.transparent,
          child: child,
        ),
      );
    },
  );
}
