import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/data/models/learning_path_progress_model.dart';

class LearningPathProgressBar extends StatelessWidget {
  const LearningPathProgressBar({
    required this.progress,
    this.showLabel = true,
    super.key,
  });

  final LearningPathProgressModel progress;
  final bool showLabel;

  @override
  Widget build(BuildContext context) {
    if (progress.nodes.isEmpty) {
      return const SizedBox.shrink();
    }

    final masteredCount =
        progress.nodes.where((n) => n.status == 'mastered').length;
    final totalCount = progress.nodes.length;

    return SparkleStaggerItem(
      index: 0,
      child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (showLabel) ...[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '学习路径进度',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: DS.brandPrimary,
                ),
              ),
              Text(
                '$masteredCount/$totalCount',
                style: TextStyle(
                  fontSize: 12,
                  color: DS.brandPrimary54,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.xs),
        ],
        TweenAnimationBuilder<double>(
          tween: Tween<double>(begin: 0, end: 1),
          duration: DS.motionDuration(SparkleMotionToken.hero),
          curve: DS.motionCurve(SparkleMotionToken.hero),
          builder: (context, reveal, _) => Container(
            height: 32,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: DS.brandPrimary10),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(7),
              child: Row(
                children: _buildSegments(reveal),
              ),
            ),
          ),
        ),
        const SizedBox(height: DS.xs),
        Wrap(
          spacing: DS.md,
          runSpacing: DS.xs,
          children: [
            _buildLegendItem('已掌握', DS.semanticSuccess),
            _buildLegendItem('学习中', DS.brandPrimary),
            _buildLegendItem('待解锁', DS.brandPrimary20),
          ],
        ),
      ],
      ),
    );
  }

  List<Widget> _buildSegments(double reveal) {
    final segments = <Widget>[];
    final totalNodes = progress.nodes.length;

    for (final node in progress.nodes) {
      final color = _getNodeColor(node.status);
      final flex = (100 / totalNodes).round();

      segments.add(
        Expanded(
          flex: flex,
          child: Tooltip(
            message: '${node.name} (${node.mastery}%)',
            child: GestureDetector(
              onTap: () {
                // TRACKED(TD-002): Navigate to galaxy node detail
              },
              child: ColoredBox(
                color: color.withValues(alpha: 0.35 + (0.65 * reveal)),
                child: node.isTarget
                    ? Center(
                        child: Icon(
                          Icons.star,
                          size: 16,
                          color: Colors.white.withValues(alpha: 0.9),
                        ),
                      )
                    : null,
              ),
            ),
          ),
        ),
      );
    }

    return segments;
  }

  Color _getNodeColor(String status) {
    switch (status) {
      case 'mastered':
        return DS.semanticSuccess;
      case 'unlocked':
        return DS.brandPrimary;
      case 'locked':
        return DS.brandPrimary20;
      default:
        return DS.brandPrimary10;
    }
  }

  Widget _buildLegendItem(String label, Color color) => Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: DS.xs),
        Text(
          label,
          style: TextStyle(
            fontSize: 11,
            color: DS.brandPrimary54,
          ),
        ),
      ],
    );
}
