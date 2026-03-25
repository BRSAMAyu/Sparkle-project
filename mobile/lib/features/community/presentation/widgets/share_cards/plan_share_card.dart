import 'package:flutter/material.dart';
import 'package:sparkle/core/design/components/atoms/sparkle_pressable.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/universal_share_service.dart';

/// Widget for displaying a plan progress share card preview
///
/// Used in chat bubbles and quick share pickers
class PlanShareCard extends StatelessWidget {
  const PlanShareCard({
    required this.planId,
    required this.planTitle,
    this.sharedResourceId,
    this.progress,
    this.completedTasks,
    this.totalTasks,
    this.milestones,
    this.deadline,
    this.isCompact = false,
    this.onTap,
    this.onAdopt,
    super.key,
  });

  final String planId;
  final String planTitle;
  final String? sharedResourceId;
  final double? progress; // 0.0 - 1.0
  final int? completedTasks;
  final int? totalTasks;
  final int? milestones;
  final DateTime? deadline;
  final bool isCompact;
  final VoidCallback? onTap;
  final VoidCallback? onAdopt;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactCard(context);
    }
    return _buildFullCard(context);
  }

  Widget _buildCompactCard(BuildContext context) => SparklePressable(
        onTap: onTap,
        padding: EdgeInsets.zero,
        borderRadius: DS.borderRadius8,
        child: Container(
          padding: const EdgeInsets.all(DS.sm),
          decoration: BoxDecoration(
            color: DS.surfaceSecondary,
            borderRadius: DS.borderRadius8,
            border: Border.all(color: DS.border),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: DS.info.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  Icons.flag,
                  color: DS.info,
                  size: 18,
                ),
              ),
              const SizedBox(width: DS.sm),
              Flexible(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      planTitle,
                      style: TextStyle(
                        fontWeight: DS.fontWeightMedium,
                        fontSize: DS.fontSizeSm,
                        color: DS.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (progress != null)
                      Text(
                        '进度 ${(_progressPercent!)}%',
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textTertiary,
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildFullCard(BuildContext context) => SparklePressable(
        onTap: onTap,
        padding: EdgeInsets.zero,
        borderRadius: DS.borderRadius12,
        child: Builder(
          builder: (context) {
            final isDarkMode = Theme.of(context).brightness == Brightness.dark;
            return Container(
          width: 280,
          decoration: BoxDecoration(
            gradient: isDarkMode
                ? LinearGradient(
                    colors: [
                      DS.info.withValues(alpha: 0.1),
                      DS.brandPrimary.withValues(alpha: 0.05),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  )
                : null,
            color: isDarkMode ? null : DS.surfacePanel,
            borderRadius: DS.borderRadius12,
            border: Border.all(
              color: isDarkMode
                  ? DS.info.withValues(alpha: 0.3)
                  : DS.borderSubtle,
            ),
            boxShadow: DS.shadowSm,
          ),
          child: Stack(
            children: [
              // Background decoration
              Positioned(
                right: -10,
                bottom: -10,
                child: Icon(
                  Icons.flag_outlined,
                  size: 80,
                  color: DS.info.withValues(alpha: 0.1),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(DS.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Header
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(DS.sm),
                          decoration: BoxDecoration(
                            color: DS.info.withValues(alpha: 0.15),
                            borderRadius: DS.borderRadius8,
                          ),
                          child: Icon(
                            Icons.flag,
                            color: DS.info,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: DS.sm),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '学习计划',
                                style: TextStyle(
                                  fontSize: DS.fontSizeXs,
                                  color: DS.textTertiary,
                                ),
                              ),
                              Text(
                                planTitle,
                                style: TextStyle(
                                  fontWeight: DS.fontWeightBold,
                                  fontSize: DS.fontSizeBase,
                                  color: DS.textPrimary,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),

                    // Progress indicator
                    if (progress != null) ...[
                      const SizedBox(height: DS.md),
                      Row(
                        children: [
                          Expanded(
                            child: ClipRRect(
                              borderRadius: DS.borderRadius4,
                              child: LinearProgressIndicator(
                                value: progress!,
                                backgroundColor: DS.neutral200,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  _getProgressColor(),
                                ),
                                minHeight: 8,
                              ),
                            ),
                          ),
                          const SizedBox(width: DS.sm),
                          Text(
                            '${_progressPercent!}%',
                            style: TextStyle(
                              fontWeight: DS.fontWeightBold,
                              fontSize: DS.fontSizeSm,
                              color: _getProgressColor(),
                            ),
                          ),
                        ],
                      ),
                    ],

                    const SizedBox(height: DS.md),

                    // Stats row
                    Wrap(
                      spacing: DS.md,
                      runSpacing: DS.sm,
                      children: [
                        if (completedTasks != null && totalTasks != null)
                          _buildStat(
                            '任务',
                            '$completedTasks/$totalTasks',
                            Icons.task_alt,
                          ),
                        if (milestones != null && milestones! > 0) ...[
                          _buildStat(
                            '里程碑',
                            '$milestones',
                            Icons.emoji_events,
                          ),
                        ],
                        if (deadline != null) ...[
                          _buildStat(
                            '截止',
                            _formatDeadline(deadline!),
                            Icons.calendar_today,
                          ),
                        ],
                      ],
                    ),
                    if (onAdopt != null) ...[
                      const SizedBox(height: DS.sm),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 160),
                          child: TextButton.icon(
                            icon: const Icon(Icons.add_task, size: DS.iconSizeSm),
                            label: const Text(
                              '采纳计划',
                              overflow: TextOverflow.ellipsis,
                            ),
                            onPressed: onAdopt,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
            );
          },
        ),
      );

  String? get _progressPercent =>
      progress != null ? (progress! * 100).toStringAsFixed(0) : null;

  Color _getProgressColor() {
    if (progress == null) return DS.info;
    if (progress! >= 0.8) return DS.success;
    if (progress! >= 0.5) return DS.info;
    if (progress! >= 0.25) return DS.warning;
    return DS.error;
  }

  Widget _buildStat(String label, String value, IconData icon) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: DS.textTertiary,
          ),
          const SizedBox(width: DS.xs),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.textTertiary,
                ),
              ),
              Text(
                value,
                style: TextStyle(
                  fontWeight: DS.fontWeightBold,
                  fontSize: DS.fontSizeSm,
                  color: DS.textPrimary,
                ),
              ),
            ],
          ),
        ],
      );

  String _formatDeadline(DateTime date) {
    final now = DateTime.now();
    final diff = date.difference(now);

    if (diff.inDays < 0) {
      return '已过期';
    } else if (diff.inDays == 0) {
      return '今天';
    } else if (diff.inDays < 7) {
      return '${diff.inDays}天后';
    } else {
      return '${date.month}/${date.day}';
    }
  }
}

/// Factory for creating plan share cards from payload
class PlanShareCardFactory {
  /// Create a PlanShareCard from a UniversalSharePayload
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
    String? sharedResourceId,
    VoidCallback? onAdopt,
  }) {
    final metadata = payload.metadata ?? {};
    final progress = metadata['progress'] as double? ??
        (payload.subtitle != null && payload.subtitle!.contains('%')
            ? _parseProgressFromSubtitle(payload.subtitle!)
            : null);

    return PlanShareCard(
      planId: payload.resourceId,
      planTitle: payload.title,
      sharedResourceId: sharedResourceId,
      progress: progress,
      completedTasks: metadata['completed_tasks'] as int?,
      totalTasks: metadata['total_tasks'] as int?,
      milestones: metadata['milestones'] as int?,
      deadline: metadata['deadline'] != null
          ? DateTime.tryParse(metadata['deadline'] as String)
          : null,
      isCompact: isCompact,
      onTap: onTap,
      onAdopt: onAdopt,
    );
  }

  static double? _parseProgressFromSubtitle(String subtitle) {
    final match = RegExp(r'(\d+)%').firstMatch(subtitle);
    if (match != null) {
      return int.parse(match.group(1)!) / 100.0;
    }
    return null;
  }
}
