import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_history_provider.dart';

/// Sprint history detail bottom sheet
class SprintHistoryDetailSheet extends StatelessWidget {
  const SprintHistoryDetailSheet({
    required this.item, super.key,
  });

  final SprintHistoryItem item;

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('yyyy年MM月dd日');

    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      decoration: BoxDecoration(
        color: DS.surfacePrimary,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(DS.spacing20),
          topRight: Radius.circular(DS.spacing20),
        ),
      ),
      child: Column(
        children: [
          // Handle bar
          Container(
            margin: const EdgeInsets.only(top: DS.spacing12),
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: DS.surfaceTertiary,
              borderRadius: DS.borderRadiusFull,
            ),
          ),
          // Header
          Padding(
            padding: const EdgeInsets.all(DS.spacing20),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.name,
                        style: context.sparkleTypography.headingLarge.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Text(
                        '${dateFormat.format(item.startDate)} - ${item.endDate != null ? dateFormat.format(item.endDate!) : '进行中'}',
                        style: context.sparkleTypography.bodyMedium.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
                _StatusIndicator(status: item.status),
              ],
            ),
          ),
          const Divider(height: 1),
          // Content
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(DS.spacing20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Progress overview
                  _buildProgressSection(context),
                  const SizedBox(height: DS.spacing24),

                  // Task summary
                  _buildTaskSummary(context),
                  const SizedBox(height: DS.spacing24),

                  // Duration info
                  _buildDurationSection(context),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressSection(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '完成进度',
            style: context.sparkleTypography.labelLarge.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: DS.spacing16),
          Row(
            children: [
              // Circular progress
              SizedBox(
                width: 100,
                height: 100,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 100,
                      height: 100,
                      child: CircularProgressIndicator(
                        value: item.finalProgress.clamp(0.0, 1.0),
                        strokeWidth: 8,
                        backgroundColor: DS.surfaceTertiary,
                        valueColor: AlwaysStoppedAnimation<Color>(
                          _getProgressColor(item.finalProgress),
                        ),
                      ),
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          '${(item.finalProgress * 100).toInt()}%',
                          style: context.sparkleTypography.headingLarge.copyWith(
                            fontWeight: FontWeight.bold,
                            fontSize: 24,
                          ),
                        ),
                        Text(
                          '完成率',
                          style: context.sparkleTypography.labelSmall.copyWith(
                            color: DS.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: DS.spacing24),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildStatRow(
                      context,
                      label: '总任务',
                      value: '${item.totalTasks}',
                    ),
                    const SizedBox(height: DS.spacing8),
                    _buildStatRow(
                      context,
                      label: '已完成',
                      value: '${item.completedTasks}',
                      color: DS.semanticSuccess,
                    ),
                    const SizedBox(height: DS.spacing8),
                    _buildStatRow(
                      context,
                      label: '未完成',
                      value: '${item.totalTasks - item.completedTasks}',
                      color: DS.semanticWarning,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      );

  Widget _buildTaskSummary(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '任务统计',
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildTaskStat(
                  context,
                  label: '完成率',
                  value: '${(item.finalProgress * 100).toInt()}%',
                  icon: Icons.check_circle,
                  color: DS.semanticSuccess,
                ),
                _buildTaskStat(
                  context,
                  label: '持续天数',
                  value: '${item.durationDays}',
                  icon: Icons.calendar_today,
                  color: DS.info,
                ),
                _buildTaskStat(
                  context,
                  label: '状态',
                  value: item.statusText,
                  icon: _getStatusIcon(item.status),
                  color: _getStatusColor(item.status),
                ),
              ],
            ),
          ],
        ),
      );

  Widget _buildDurationSection(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '冲刺信息',
              style: context.sparkleTypography.labelLarge.copyWith(
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: DS.spacing12),
            _buildInfoRow(
              context,
              label: '开始日期',
              value: DateFormat('yyyy年MM月dd日 EEEE', 'zh_CN').format(item.startDate),
            ),
            const SizedBox(height: DS.spacing8),
            if (item.endDate != null)
              _buildInfoRow(
                context,
                label: '结束日期',
                value: DateFormat('yyyy年MM月dd日 EEEE', 'zh_CN').format(item.endDate!),
              ),
            const SizedBox(height: DS.spacing8),
            _buildInfoRow(
              context,
              label: '持续时间',
              value: '${item.durationDays} 天',
            ),
          ],
        ),
      );

  Widget _buildStatRow(
    BuildContext context, {
    required String label,
    required String value,
    Color? color,
  }) =>
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
          Text(
            value,
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: color ?? DS.textPrimary,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      );

  Widget _buildTaskStat(
    BuildContext context, {
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) =>
      Column(
        children: [
          Container(
            padding: const EdgeInsets.all(DS.spacing8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(
              icon,
              color: color,
              size: DS.iconSizeSm,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            value,
            style: context.sparkleTypography.labelLarge.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
              fontSize: 10,
            ),
          ),
        ],
      );

  Widget _buildInfoRow(
    BuildContext context, {
    required String label,
    required String value,
  }) =>
      Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textSecondary,
            ),
          ),
          Text(
            value,
            style: context.sparkleTypography.labelSmall.copyWith(
              color: DS.textPrimary,
            ),
          ),
        ],
      );

  Color _getProgressColor(double progress) {
    if (progress >= 0.75) return DS.semanticSuccess;
    if (progress >= 0.5) return DS.info;
    if (progress >= 0.25) return DS.semanticWarning;
    return DS.semanticError;
  }

  IconData _getStatusIcon(SprintStatus status) {
    switch (status) {
      case SprintStatus.completed:
        return Icons.check_circle;
      case SprintStatus.abandoned:
        return Icons.cancel;
      case SprintStatus.extended:
        return Icons.arrow_forward;
    }
  }

  Color _getStatusColor(SprintStatus status) {
    switch (status) {
      case SprintStatus.completed:
        return DS.semanticSuccess;
      case SprintStatus.abandoned:
        return DS.semanticError;
      case SprintStatus.extended:
        return DS.semanticWarning;
    }
  }
}

class _StatusIndicator extends StatelessWidget {
  const _StatusIndicator({required this.status});

  final SprintStatus status;

  @override
  Widget build(BuildContext context) {
    Color color;
    IconData icon;

    switch (status) {
      case SprintStatus.completed:
        color = DS.semanticSuccess;
        icon = Icons.check_circle;
      case SprintStatus.abandoned:
        color = DS.semanticError;
        icon = Icons.cancel;
      case SprintStatus.extended:
        color = DS.semanticWarning;
        icon = Icons.arrow_forward;
    }

    return Container(
      padding: const EdgeInsets.all(DS.spacing8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        shape: BoxShape.circle,
      ),
      child: Icon(
        icon,
        color: color,
        size: DS.iconSizeSm,
      ),
    );
  }
}
