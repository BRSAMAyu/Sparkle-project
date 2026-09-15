import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

const _sheetDuration = Duration(milliseconds: 300);
const _sheetReverseDuration = Duration(milliseconds: 220);
const _dialogDuration = Duration(milliseconds: 180);

class SpringCurve extends Curve {
  const SpringCurve({
    this.stiffness = 280,
    this.damping = 26,
    this.initialVelocity = 0.8,
  });

  final double stiffness;
  final double damping;
  final double initialVelocity;

  @override
  double transformInternal(double t) {
    if (t <= 0) return 0;
    if (t >= 1) return 1;

    final envelope = math.exp(-(damping / 10) * t);
    final oscillation = math.cos((stiffness / 34) * t);
    final velocityKick = initialVelocity * (1 - t) * 0.035;
    final value = 1 - (envelope * oscillation) + velocityKick;
    return value.clamp(0.0, 1.02);
  }
}

class SparkleBottomSheet {
  static const Curve _sheetCurve = SpringCurve(
    stiffness: 280,
    damping: 26,
    initialVelocity: 0.8,
  );

  static Future<T?> show<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    Color? backgroundColor,
    ShapeBorder? shape,
    bool isScrollControlled = false,
    bool useRootNavigator = false,
    bool isDismissible = true,
    bool enableDrag = true,
    bool useSafeArea = false,
    Clip? clipBehavior,
    BoxConstraints? constraints,
    RouteSettings? routeSettings,
    Color? barrierColor,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      backgroundColor:
          backgroundColor ?? DS.surfaceRoleColor(SparkleSurfaceRole.modal),
      barrierColor: barrierColor,
      shape: shape ??
          const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
      isScrollControlled: isScrollControlled,
      useRootNavigator: useRootNavigator,
      isDismissible: isDismissible,
      enableDrag: enableDrag,
      useSafeArea: useSafeArea,
      clipBehavior: clipBehavior,
      constraints: constraints,
      routeSettings: routeSettings,
      sheetAnimationStyle: const AnimationStyle(
        duration: _sheetDuration,
        reverseDuration: _sheetReverseDuration,
      ),
      builder: (sheetContext) => _SparkleBottomSheetTransition(
        curve: _sheetCurve,
        child: builder(sheetContext),
      ),
    );
  }
}

Future<T?> showSensoryModalBottomSheet<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  Color? backgroundColor,
  Color? barrierColor,
  ShapeBorder? shape,
  bool isScrollControlled = false,
  bool useRootNavigator = false,
  bool isDismissible = true,
  bool enableDrag = true,
  bool useSafeArea = false,
  Clip? clipBehavior,
  BoxConstraints? constraints,
  RouteSettings? routeSettings,
}) async {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.sheetOpen));
  if (!context.mounted) return null;

  final isDark = Theme.of(context).brightness == Brightness.dark;

  return SparkleBottomSheet.show<T>(
    context: context,
    builder: (sheetContext) => Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        _DragHandle(),
        Flexible(child: builder(sheetContext)),
      ],
    ),
    backgroundColor: backgroundColor,
    shape: shape,
    isScrollControlled: isScrollControlled,
    useRootNavigator: useRootNavigator,
    isDismissible: isDismissible,
    enableDrag: enableDrag,
    useSafeArea: useSafeArea,
    clipBehavior: clipBehavior,
    constraints: constraints,
    routeSettings: routeSettings,
    barrierColor: Colors.black.withValues(alpha: isDark ? 0.65 : 0.50),
  );
}

Future<T?> showSensoryDialog<T>({
  required BuildContext context,
  required WidgetBuilder builder,
  bool barrierDismissible = true,
  Color? barrierColor,
  bool useRootNavigator = true,
  RouteSettings? routeSettings,
  Offset? anchorPoint,
}) async {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.dialogOpen));
  if (!context.mounted) return null;

  final isDark = Theme.of(context).brightness == Brightness.dark;
  final resolvedBarrierColor =
      barrierColor ?? Colors.black.withValues(alpha: isDark ? 0.65 : 0.50);

  return showGeneralDialog<T>(
    context: context,
    pageBuilder: (dialogContext, animation, secondaryAnimation) =>
        builder(dialogContext),
    barrierDismissible: barrierDismissible,
    barrierLabel: MaterialLocalizations.of(context).modalBarrierDismissLabel,
    barrierColor: resolvedBarrierColor,
    useRootNavigator: useRootNavigator,
    routeSettings: routeSettings,
    anchorPoint: anchorPoint,
    transitionDuration: _dialogDuration,
    transitionBuilder: (dialogContext, animation, secondaryAnimation, child) {
      final curved = CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic,
      );
      final fade = Tween<double>(begin: 0.9, end: 1.0).animate(curved);
      final scale = Tween<double>(begin: 0.96, end: 1.0).animate(curved);
      return FadeTransition(
        opacity: fade,
        child: ScaleTransition(
          scale: scale,
          child: child,
        ),
      );
    },
  );
}

class _SparkleBottomSheetTransition extends StatelessWidget {
  const _SparkleBottomSheetTransition({
    required this.child,
    required this.curve,
  });

  final Widget child;
  final Curve curve;

  @override
  Widget build(BuildContext context) {
    final route = ModalRoute.of(context);
    final animation = route?.animation;
    if (animation == null) {
      return child;
    }

    final curved = CurvedAnimation(
      parent: animation,
      curve: curve,
      reverseCurve: Curves.easeInCubic,
    );

    return AnimatedBuilder(
      animation: curved,
      child: child,
      builder: (context, sheetChild) {
        final value = curved.value.clamp(0.0, 1.02);
        final overshoot = value > 1 ? value - 1 : 0.0;
        final slideY = (1 - value.clamp(0.0, 1.0)) * 0.12;
        final scale = 1 + (overshoot * 0.02);

        return FractionalTranslation(
          translation: Offset(0, slideY),
          child: Transform.scale(
            alignment: Alignment.bottomCenter,
            scale: scale,
            child: sheetChild,
          ),
        );
      },
    );
  }
}

Future<T?> showSensoryGeneralDialog<T>({
  required BuildContext context,
  required RoutePageBuilder pageBuilder,
  required RouteTransitionsBuilder transitionBuilder,
  bool barrierDismissible = true,
  Color? barrierColor,
  bool useRootNavigator = true,
  RouteSettings? routeSettings,
  Offset? anchorPoint,
  Duration transitionDuration = _dialogDuration,
  String? barrierLabel,
}) async {
  unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.dialogOpen));
  if (!context.mounted) return null;

  final isDark = Theme.of(context).brightness == Brightness.dark;
  final resolvedBarrierColor =
      barrierColor ?? Colors.black.withValues(alpha: isDark ? 0.65 : 0.50);

  return showGeneralDialog<T>(
    context: context,
    pageBuilder: pageBuilder,
    barrierDismissible: barrierDismissible,
    barrierLabel: barrierLabel ??
        MaterialLocalizations.of(context).modalBarrierDismissLabel,
    barrierColor: resolvedBarrierColor,
    useRootNavigator: useRootNavigator,
    routeSettings: routeSettings,
    anchorPoint: anchorPoint,
    transitionDuration: transitionDuration,
    transitionBuilder: transitionBuilder,
  );
}

class _DragHandle extends StatelessWidget {
  const _DragHandle();

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: DS.spacing8, bottom: DS.spacing8),
        child: Container(
          width: 32,
          height: 4,
          decoration: BoxDecoration(
            color: DS.neutral400.withValues(alpha: 0.72),
            borderRadius: BorderRadius.circular(999),
          ),
        ),
      );
}
