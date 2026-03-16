import 'dart:io';

import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/universal_share_service.dart';

/// Widget for displaying a task share card preview
///
/// Used in chat bubbles and quick share pickers
class TaskShareCard extends StatelessWidget {
  const TaskShareCard({
    required this.taskId,
    required this.taskTitle,
    this.taskDescription,
    this.completedAt,
    this.duration,
    this.points,
    this.streak,
    this.isCompact = false,
    this.onTap,
    super.key,
  });

  final String taskId;
  final String taskTitle;
  final String? taskDescription;
  final DateTime? completedAt;
  final int? duration; // in minutes
  final int? points;
  final int? streak;
  final bool isCompact;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    if (isCompact) {
      return _buildCompactCard(context);
    }
    return _buildFullCard(context);
  }

  Widget _buildCompactCard(BuildContext context) => GestureDetector(
        onTap: onTap,
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
                  color: DS.success.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius6,
                ),
                child: const Icon(
                  Icons.task_alt,
                  color: DS.success,
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
                      taskTitle,
                      style: TextStyle(
                        fontWeight: DS.fontWeightMedium,
                        fontSize: DS.fontSizeSm,
                        color: DS.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    if (duration != null)
                      Text(
                        '完成 · ${duration}分钟',
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

  Widget _buildFullCard(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          width: 260,
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                DS.success.withValues(alpha: 0.1),
                DS.brandPrimary.withValues(alpha: 0.05),
              ],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: DS.borderRadius12,
            border: Border.all(color: DS.success.withValues(alpha: 0.3)),
            boxShadow: DS.shadowSm,
          ),
          child: Stack(
            children: [
              // Background decoration
              Positioned(
                right: -20,
                bottom: -20,
                child: Icon(
                  Icons.check_circle_outline,
                  size: 100,
                  color: DS.success.withValues(alpha: 0.1),
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
                            color: DS.success.withValues(alpha: 0.15),
                            borderRadius: DS.borderRadius8,
                          ),
                          child: const Icon(
                            Icons.task_alt,
                            color: DS.success,
                            size: 20,
                          ),
                        ),
                        const SizedBox(width: DS.sm),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '任务完成',
                                style: TextStyle(
                                  fontSize: DS.fontSizeXs,
                                  color: DS.textTertiary,
                                ),
                              ),
                              Text(
                                taskTitle,
                                style: TextStyle(
                                  fontWeight: DS.fontWeightBold,
                                  fontSize: DS.fontSizeMd,
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

                    if (taskDescription != null &&
                        taskDescription!.isNotEmpty) ...[
                      const SizedBox(height: DS.sm),
                      Text(
                        taskDescription!,
                        style: TextStyle(
                          fontSize: DS.fontSizeSm,
                          color: DS.textSecondary,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],

                    const SizedBox(height: DS.md),

                    // Stats row
                    Row(
                      children: [
                        if (duration != null) _buildStat('时长', '${duration}m'),
                        if (points != null) ...[
                          const SizedBox(width: DS.md),
                          _buildStat('积分', '+$points'),
                        ],
                        if (streak != null && streak! > 0) ...[
                          const SizedBox(width: DS.md),
                          _buildStat('连胜', '$streak🔥'),
                        ],
                      ],
                    ),

                    if (completedAt != null) ...[
                      const SizedBox(height: DS.sm),
                      Text(
                        _formatTime(completedAt!),
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: DS.textTertiary,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      );

  Widget _buildStat(String label, String value) => Column(
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
      );

  String _formatTime(DateTime time) {
    final now = DateTime.now();
    final diff = now.difference(time);

    if (diff.inMinutes < 1) {
      return '刚刚';
    } else if (diff.inHours < 1) {
      return '${diff.inMinutes}分钟前';
    } else if (diff.inDays < 1) {
      return '${diff.inHours}小时前';
    } else {
      return '${time.month}/${time.day}';
    }
  }
}

/// Factory for creating task share cards from payload
class TaskShareCardFactory {
  /// Create a TaskShareCard from a UniversalSharePayload
  static Widget fromPayload(
    UniversalSharePayload payload, {
    bool isCompact = false,
    VoidCallback? onTap,
  }) {
    final metadata = payload.metadata ?? {};

    return TaskShareCard(
      taskId: payload.resourceId,
      taskTitle: payload.title,
      taskDescription: payload.subtitle ?? payload.description,
      duration: metadata['duration'] as int?,
      points: metadata['points'] as int?,
      streak: metadata['streak'] as int?,
      completedAt: metadata['completed_at'] != null
          ? DateTime.tryParse(metadata['completed_at'] as String)
          : null,
      isCompact: isCompact,
      onTap: onTap,
    );
  }
}
