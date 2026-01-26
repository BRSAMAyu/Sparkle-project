import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/plan/presentation/providers/sprint_history_provider.dart';
import 'package:sparkle/features/plan/presentation/widgets/sprint_history_detail.dart';
import 'package:sparkle/l10n/app_localizations.dart';

/// Sprint history screen - displays list of archived/completed sprints
class SprintHistoryScreen extends ConsumerWidget {
  const SprintHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyState = ref.watch(sprintHistoryProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.sprintHistory),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(sprintHistoryProvider.notifier).refresh(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.read(sprintHistoryProvider.notifier).refresh(),
        child: _buildBody(context, historyState, l10n),
      ),
    );
  }

  Widget _buildBody(BuildContext context, SprintHistoryState state, AppLocalizations l10n) {
    if (state.isLoading && state.items.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null && state.items.isEmpty) {
      return _buildErrorState(context, state.error!, l10n);
    }

    if (state.items.isEmpty) {
      return _buildEmptyState(context, l10n);
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

  Widget _buildEmptyState(BuildContext context, AppLocalizations l10n) => Center(
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
            l10n.noSprintHistory,
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
        ],
      ),
    );

  Widget _buildErrorState(BuildContext context, String error, AppLocalizations l10n) => Center(
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
            l10n.loadingFailed,
            style: context.sparkleTypography.bodyMedium.copyWith(
              color: DS.textSecondary,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Text(
            error,
            style: context.sparkleTypography.labelSmall.copyWith(
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

  String _getStatusText(AppLocalizations l10n) {
    switch (item.status) {
      case SprintStatus.completed:
        return l10n.sprintCompleted;
      case SprintStatus.abandoned:
        return l10n.sprintAbandoned;
      case SprintStatus.extended:
        return l10n.sprintExtended;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
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
                  text: _getStatusText(l10n),
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
                  '${dateFormat.format(item.startDate)} - ${item.endDate != null ? dateFormat.format(item.endDate!) : l10n.ongoing}',
                  style: context.sparkleTypography.labelSmall.copyWith(
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
                        l10n.completionProgress,
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
                      l10n.tasksCompleted(
                        item.completedTasks.toString(),
                        item.totalTasks.toString(),
                      ),
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
