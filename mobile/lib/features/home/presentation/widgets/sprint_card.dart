import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/home/presentation/providers/dashboard_provider.dart';

/// SprintCard - Sprint Progress Card for v2.3 dashboard
///
/// 1x1 small card displaying:
/// - Circular progress ring
/// - Days remaining
/// - Sprint name
class SprintCard extends ConsumerWidget {
  const SprintCard({super.key, this.onTap});
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final sprint = dashboardState.sprint;

    return GestureDetector(
      onTap: onTap,
      child: MaterialStyler(
        material: AppMaterials.ceramic,
        borderRadius: DS.borderRadius20,
        padding: const EdgeInsets.all(DS.lg),
        child: sprint != null
            ? _buildSprintContent(context, sprint)
            : _buildEmptyState(context),
      ),
    );
  }

  Widget _buildSprintContent(BuildContext context, SprintData sprint) {
    final progress = sprint.progress.clamp(0.0, 1.0);
    final daysLeft = sprint.daysLeft;
    final isUrgent = daysLeft <= 3;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Header
        Text(
          '冲刺',
          style: context.sparkleTypography.labelSmall.copyWith(
            color: DS.textSecondary,
            fontWeight: FontWeight.w500,
          ),
        ),

        const SizedBox(height: 8),

        // Circular progress - use Expanded to take available space
        Expanded(
          child: Center(
            child: LayoutBuilder(
              builder: (context, constraints) {
                // Use the smaller of available width/height, capped at 56
                final ringSize = math.min(
                  constraints.maxWidth.clamp(0, 56).toDouble(),
                  constraints.maxHeight.clamp(0, 56).toDouble(),
                );
                return TweenAnimationBuilder<double>(
                  tween: Tween<double>(begin: 0, end: progress),
                  duration: DS.durationSlow,
                  curve: Curves.easeOutCubic,
                  builder: (context, animatedProgress, child) => SizedBox(
                    width: ringSize,
                    height: ringSize,
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        CustomPaint(
                          size: Size(ringSize, ringSize),
                          painter: _CircularProgressPainter(
                            progress: animatedProgress,
                            isUrgent: isUrgent,
                          ),
                        ),
                        child!,
                      ],
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        '$daysLeft',
                        style: context.sparkleTypography.headingMedium.copyWith(
                          fontSize: ringSize * 0.3,
                          fontWeight: FontWeight.bold,
                          color: isUrgent ? DS.error : DS.brandPrimary,
                        ),
                      ),
                      Text(
                        '天',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          fontSize: ringSize * 0.17,
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),

        const SizedBox(height: 4),

        // Sprint name
        SparkleStaggerItem(
          index: 0,
          child: Text(
            sprint.name,
            style: context.sparkleTypography.labelSmall.copyWith(
              fontWeight: FontWeight.w600,
              color: DS.textPrimary,
            ),
          ),
        ),
        SparkleStaggerItem(
          index: 1,
          child: Text(
            '${(progress * 100).toInt()}% 完成',
            style: context.sparkleTypography.labelSmall.copyWith(
              fontSize: 10,
              color: DS.textSecondary,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            padding: const EdgeInsets.all(DS.sm),
            decoration: BoxDecoration(
              color: DS.brandPrimary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              Icons.flash_on_rounded,
              color: DS.brandPrimaryConst,
              size: 20,
            ),
          ),
          const Expanded(child: SizedBox()),
          Text(
            '无冲刺计划',
            style: context.sparkleTypography.labelSmall.copyWith(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: DS.textPrimary,
            ),
          ),
          const SizedBox(height: DS.xs),
          Text(
            '点击创建',
            style: TextStyle(
              fontSize: 11,
              color: DS.textSecondary,
            ),
          ),
        ],
      );
}

class _CircularProgressPainter extends CustomPainter {
  _CircularProgressPainter({
    required this.progress,
    required this.isUrgent,
  });
  final double progress;
  final bool isUrgent;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    const strokeWidth = 5.0;
    // Inset by half stroke width so the ring stays fully inside the canvas
    final radius = size.width / 2 - strokeWidth / 2 - 1;

    // Background circle
    final bgPaint = Paint()
      ..color = DS.brandPrimary.withValues(alpha: 0.12)
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth;
    canvas.drawCircle(center, radius, bgPaint);

    // Progress arc
    final progressPaint = Paint()
      ..color = isUrgent ? DS.error : DS.primaryBase
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    final sweepAngle = 2 * math.pi * progress;
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      sweepAngle,
      false,
      progressPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _CircularProgressPainter oldDelegate) =>
      oldDelegate.progress != progress || oldDelegate.isUrgent != isUrgent;
}
