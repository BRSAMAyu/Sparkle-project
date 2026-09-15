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
          SparkleMotionToken.quick => const Duration(milliseconds: 160),
          SparkleMotionToken.responsive => const Duration(milliseconds: 180),
          SparkleMotionToken.standard => const Duration(milliseconds: 200),
          SparkleMotionToken.deliberate => const Duration(milliseconds: 230),
          SparkleMotionToken.scene => const Duration(milliseconds: 260),
          SparkleMotionToken.hero => const Duration(milliseconds: 300),
        };
  final reverseDuration = reduceMotion
      ? const Duration(milliseconds: 120)
      : switch (motionToken) {
          SparkleMotionToken.micro => const Duration(milliseconds: 120),
          SparkleMotionToken.quick => const Duration(milliseconds: 130),
          SparkleMotionToken.responsive => const Duration(milliseconds: 140),
          SparkleMotionToken.standard => const Duration(milliseconds: 150),
          SparkleMotionToken.deliberate => const Duration(milliseconds: 170),
          SparkleMotionToken.scene => const Duration(milliseconds: 180),
          SparkleMotionToken.hero => const Duration(milliseconds: 200),
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
        SparkleMotionToken.quick => 0.88,
        SparkleMotionToken.responsive => 0.84,
        SparkleMotionToken.standard => 0.82,
        SparkleMotionToken.deliberate => 0.78,
        SparkleMotionToken.scene => 0.74,
        SparkleMotionToken.hero => 0.68,
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

Page<dynamic> buildColdStartTransitionPage({
  required GoRouterState state,
  required Widget child,
}) {
  final reduceMotion = WidgetsBinding
      .instance.platformDispatcher.accessibilityFeatures.disableAnimations;

  return CustomTransitionPage<void>(
    key: state.pageKey,
    transitionDuration: reduceMotion
        ? const Duration(milliseconds: 140)
        : const Duration(milliseconds: 400),
    reverseTransitionDuration: reduceMotion
        ? const Duration(milliseconds: 120)
        : const Duration(milliseconds: 220),
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      if (reduceMotion) {
        return FadeTransition(
          opacity: Tween<double>(begin: 0.94, end: 1).animate(
            CurvedAnimation(parent: animation, curve: Curves.easeOutCubic),
          ),
          child: child,
        );
      }

      return ColdStartRouteTransition(
        animation: animation,
        secondaryAnimation: secondaryAnimation,
        child: child,
      );
    },
  );
}

class ColdStartRouteTransition extends StatefulWidget {
  const ColdStartRouteTransition({
    required this.animation,
    required this.secondaryAnimation,
    required this.child,
    super.key,
  });

  final Animation<double> animation;
  final Animation<double> secondaryAnimation;
  final Widget child;

  @override
  State<ColdStartRouteTransition> createState() =>
      _ColdStartRouteTransitionState();
}

class _ColdStartRouteTransitionState extends State<ColdStartRouteTransition> {
  bool _skipRequested = false;

  void _skip() {
    if (_skipRequested || !mounted) {
      return;
    }
    setState(() {
      _skipRequested = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_skipRequested) {
      return widget.child;
    }

    final curved = CurvedAnimation(
      parent: widget.animation,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );
    final outgoing = CurvedAnimation(
      parent: widget.secondaryAnimation,
      curve: Curves.easeOutCubic,
      reverseCurve: Curves.easeInCubic,
    );

    return Listener(
      behavior: HitTestBehavior.translucent,
      onPointerDown: (_) => _skip(),
      child: FadeTransition(
        opacity: Tween<double>(begin: 0, end: 1).animate(curved),
        child: FadeTransition(
          opacity: Tween<double>(begin: 1, end: 0.88).animate(outgoing),
          child: SlideTransition(
            position: Tween<Offset>(
              begin: const Offset(0, 0.018),
              end: Offset.zero,
            ).animate(curved),
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
