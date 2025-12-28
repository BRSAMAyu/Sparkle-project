import 'dart:ui';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/presentation/providers/dashboard_provider.dart';

/// SprintCard - Sprint Progress Card for v2.3 dashboard
///
/// 1x1 small card displaying:
/// - Circular progress ring
/// - Days remaining
/// - Sprint name
class SprintCard extends ConsumerWidget {
  final VoidCallback? onTap;

  const SprintCard({super.key, this.onTap});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardState = ref.watch(dashboardProvider);
    final sprint = dashboardState.sprint;

    return GestureDetector(
      onTap: onTap,
      child: ClipRRect(
        borderRadius: AppDesignTokens.borderRadius20,
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 10, sigmaY: 10),
          child: Container(
            decoration: BoxDecoration(
              color: AppDesignTokens.glassBackground,
              borderRadius: AppDesignTokens.borderRadius20,
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            padding: const EdgeInsets.all(DS.lg),
            child: sprint != null
                ? _buildSprintContent(sprint)
                : _buildEmptyState(),
          ),
        ),
      ),
    );
  }

  Widget _buildSprintContent(SprintData sprint) {
    final progress = sprint.progress;
    final daysLeft = sprint.daysLeft;
    final isUrgent = daysLeft <= 3;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Header
        const Text(
          '冲刺',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: DS.brandPrimary70,
          ),
        ),

        const Spacer(),

        // Circular progress
        Center(
          child: SizedBox(
            width: 70,
            height: 70,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CustomPaint(
                  size: const Size(70, 70),
                  painter: _CircularProgressPainter(
                    progress: progress,
                    isUrgent: isUrgent,
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      '$daysLeft',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: isUrgent ? DS.error : DS.brandPrimary,
                      ),
                    ),
                    Text(
                      '天',
                      style: TextStyle(
                        fontSize: 10,
                        color: DS.brandPrimary.withAlpha(180),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),

        const Spacer(),

        // Sprint name
        Text(
          sprint.name,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: DS.brandPrimary,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        const SizedBox(height: 2),
        Text(
          '${(progress * 100).toInt()}% 完成',
          style: TextStyle(
            fontSize: 10,
            color: DS.brandPrimary.withAlpha(150),
          ),
        ),
      ],
    );
  }

  Widget _buildEmptyState() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(DS.sm),
          decoration: BoxDecoration(
            color: DS.brandPrimary.withAlpha(20),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const Icon(
            Icons.flash_on_rounded,
            color: DS.brandPrimary54,
            size: 20,
          ),
        ),

        const Spacer(),

        const Text(
          '无冲刺计划',
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: DS.brandPrimary70,
          ),
        ),
        const SizedBox(height: DS.xs),
        Text(
          '点击创建',
          style: TextStyle(
            fontSize: 11,
            color: DS.brandPrimary.withAlpha(120),
          ),
        ),
      ],
    );
  }
}

class _CircularProgressPainter extends CustomPainter {
  final double progress;
  final bool isUrgent;

  _CircularProgressPainter({
    required this.progress,
    required this.isUrgent,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.width / 2 - 4;

    // Background circle
    final bgPaint = Paint()
      ..color = DS.brandPrimary.withAlpha(30)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6;
    canvas.drawCircle(center, radius, bgPaint);

    // Progress arc
    final progressPaint = Paint()
      ..color = isUrgent ? DS.error : AppDesignTokens.primaryBase
      ..style = PaintingStyle.stroke
      ..strokeWidth = 6
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
  bool shouldRepaint(covariant _CircularProgressPainter oldDelegate) {
    return oldDelegate.progress != progress || oldDelegate.isUrgent != isUrgent;
  }
}
