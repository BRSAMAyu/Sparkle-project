import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';

/// Branded pull-to-refresh indicator with light haptic feedback on trigger.
///
/// Use this everywhere instead of raw [RefreshIndicator] to keep the visual
/// and haptic refresh experience consistent across the app.
class SparkleRefreshIndicator extends StatelessWidget {
  const SparkleRefreshIndicator({
    required this.onRefresh,
    required this.child,
    super.key,
  });

  final Future<void> Function() onRefresh;
  final Widget child;

  @override
  Widget build(BuildContext context) => RefreshIndicator(
        onRefresh: () async {
          await SensoryFeedbackService.emit(
            SensoryFeedbackEvent.tap,
            enableSound: false,
          );
          await onRefresh();
        },
        color: DS.brandPrimary,
        backgroundColor: context.colors.surfaceCard,
        strokeWidth: 2.5,
        displacement: 50,
        child: child,
      );
}
