import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_history_provider.dart';
import 'package:sparkle/features/plan/presentation/widgets/sprint_history_detail.dart';

/// Sprint history screen - displays list of archived/completed sprints
class SprintHistoryScreen extends ConsumerWidget {
  const SprintHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyState = ref.watch(sprintHistoryProvider);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('冲刺历史'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(sprintHistoryProvider.notifier).refresh(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(sprintHistoryProvider.notifier).refresh(),
        child: _buildBody(context, historyState),
      ),
    );
  }

  Widget _buildBody(BuildContext context, SprintHistoryState state) {
    if (state.isLoading && state.items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.items.isEmpty) {
      return _buildErrorState(context, state.error!);
    }

    if (state.items.isEmpty) {
      return _buildEmptyState(context);
    }

    return ListView.separated(
      padding: const EdgeInsets.all(DS.spacing16),
      itemCount: state.items.length,
      separatorBuilder: (context, index) => const SizedBox(height: DS.spacing12),
      itemBuilder: (context, index) {
        final item = state.items[index];
        return _SprintHistoryCard(item: item);
      },
    );
  }

  Widget _buildEmptyState(BuildContext context) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.history,
            size: 48,
            color: DS.textSecondary.withValues(alpha: 0.5),
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '暂无冲刺历史',
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
        ],
      ),
    );

  Widget _buildErrorState(BuildContext context, String error) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 48,
            color: DS.semanticError,
          ),
          const SizedBox(height: DS.spacing12),
          Text(
            '加载失败',
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            error,
            style: context.sparkleTypography.bodySmall.copyWith(
              color: DS.semanticError,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
}

class _SprintHistoryCard extends StatelessWidget {
  const _SprintHistoryCard({required this.item});

  final SprintHistoryItem item;

  @override
  Widget build(BuildContext context) {
    final dateFormat = DateFormat('yyyy/MM/dd');

    return GestureDetector(
      onTap: () => _showDetail(context),
      child: Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: DS.surfaceSecondary,
          borderRadius: DS.borderRadius12,
          border: Border.all(
            color: DS.border,
            width: 1,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row with name and status
            Row(
              children: [
                Expanded(
                  child: Text(
                    item.name,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                _StatusChip(
                  status: item.status,
                  text: item.statusText,
                ),
              ],
            ),
            const SizedBox(height: DS.spacing12),

            // Date range
            Row(
              children: [
                Icon(
                  Icons.calendar_today_rounded,
                  size: DS.iconSizeXs,
                  color: DS.textSecondary,
                ),
                const SizedBox(width: DS.spacing4),
                Text(
                  '${dateFormat.format(item.startDate)} - ${item.endDate != null ? dateFormat.format(item.endDate!) : '进行中'}',
                  style: context.sparkleTypography.bodySmall.copyWith(
                    color: DS.textSecondary,
                  ),
                ),
              ],
            ),
            const SizedBox(height: DS.spacing8),

            // Progress bar
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '完成进度',
                        style: context.sparkleTypography.labelSmall.copyWith(
                          color: DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing4),
                      Stack(
                        children: [
                          Container(
                            height: 6,
                            decoration: BoxDecoration(
                              color: DS.surfaceTertiary,
                              borderRadius: DS.borderRadiusFull,
                            ),
                          ),
                          FractionallySizedBox(
                            widthFactor: item.finalProgress.clamp(0.0, 1.0),
                            child: Container(
                              height: 6,
                              decoration: BoxDecoration(
                                color: _getProgressColor(item.finalProgress),
                                borderRadius: DS.borderRadiusFull,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: DS.spacing16),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '${(item.finalProgress * 100).toInt()}%',
                      style: context.sparkleTypography.labelLarge.copyWith(
                        fontWeight: FontWeight.bold,
                        color: _getProgressColor(item.finalProgress),
                      ),
                    ),
                    Text(
                      '${item.completedTasks}/${item.totalTasks} 任务',
                      style: context.sparkleTypography.labelSmall.copyWith(
                        color: DS.textSecondary,
                        fontSize: 10,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  void _showDetail(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => SprintHistoryDetailSheet(item: item),
    );
  }

  Color _getProgressColor(double progress) {
    if (progress >= 0.75) return DS.semanticSuccess;
    if (progress >= 0.5) return DS.info;
    if (progress >= 0.25) return DS.semanticWarning;
    return DS.semanticError;
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.status,
    required this.text,
  });

  final SprintStatus status;
  final String text;

  @override
  Widget build(BuildContext context) {
    Color color;
    Color backgroundColor;

    switch (status) {
      case SprintStatus.completed:
        color = DS.semanticSuccess;
        backgroundColor = DS.semanticSuccess.withValues(alpha: 0.1);
        break;
      case SprintStatus.abandoned:
        color = DS.semanticError;
        backgroundColor = DS.semanticError.withValues(alpha: 0.1);
        break;
      case SprintStatus.extended:
        color = DS.semanticWarning;
        backgroundColor = DS.semanticWarning.withValues(alpha: 0.1);
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: DS.borderRadius8,
        border: Border.all(
          color: color.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: Text(
        text,
        style: context.sparkleTypography.labelSmall.copyWith(
          color: color,
          fontWeight: FontWeight.w500,
          fontSize: 10,
        ),
      ),
    );
  }
}
