import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/plan/data/models/plan_model.dart';
import 'package:sparkle/features/plan/presentation/providers/plan_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Plan Context Summary Widget
///
/// Displays a compact summary of a plan's context including:
/// - Plan name with type icon
/// - Progress bar with percentage
/// - Days remaining (for sprint) or mastery level (for growth)
/// - 2-3 next tasks (titles only, tappable to navigate)
class PlanContextSummary extends ConsumerWidget {
  const PlanContextSummary({
    super.key,
    this.planId,
    this.contextData,
  }) : assert(planId != null || contextData != null);

  final String? planId;
  final Map<String, dynamic>? contextData;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final contextPayload = contextData;
    if (contextPayload != null) {
      final parsed = PlanContextData.fromJson(contextPayload);
      final resolvedPlanId = planId ?? parsed.planId;

      if (resolvedPlanId == null) {
        return _PlanContextSnapshotCard(
          isDark: isDark,
          contextData: parsed,
        );
      }

      final planAsync = ref.watch(planDetailProvider(resolvedPlanId));
      return planAsync.when(
        data: (plan) => _PlanContextSnapshotCard(
          isDark: isDark,
          contextData: parsed,
          plan: plan,
        ),
        loading: () => _buildLoadingCard(isDark),
        error: (_, __) => _PlanContextSnapshotCard(
          isDark: isDark,
          contextData: parsed,
        ),
      );
    }

    final plan = planId;
    if (plan == null) {
      return const SizedBox.shrink();
    }

    final planAsync = ref.watch(planDetailProvider(plan));
    return planAsync.when(
      data: (plan) => _PlanContextCard(plan: plan, isDark: isDark),
      loading: () => _buildLoadingCard(isDark),
      error: (_, __) => const SizedBox.shrink(),
    );
  }

  Widget _buildLoadingCard(bool isDark) => Container(
        padding: const EdgeInsets.all(DS.spacing16),
        decoration: BoxDecoration(
          color: isDark ? DS.neutral800 : DS.neutral100,
          borderRadius: DS.borderRadius16,
          border: Border.all(
            color: DS.neutral300,
          ),
        ),
        child: const Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
}

class PlanContextData {
  const PlanContextData({
    required this.facts,
    required this.taskSummary,
    required this.recentFeedback,
    this.planId,
    this.status,
  });

  factory PlanContextData.fromJson(Map<String, dynamic> json) {
    final taskSummary = (json['task_summary'] as Map<String, dynamic>?) ??
        (json['task_index'] as Map<String, dynamic>?) ??
        <String, dynamic>{};
    return PlanContextData(
      planId: json['plan_id'] as String?,
      status: json['status'] as String?,
      facts: (json['facts'] as Map<String, dynamic>?) ?? <String, dynamic>{},
      taskSummary: taskSummary,
      recentFeedback: (json['recent_feedback'] as List<dynamic>?)
              ?.whereType<Map<String, dynamic>>()
              .toList() ??
          <Map<String, dynamic>>[],
    );
  }

  final String? planId;
  final String? status;
  final Map<String, dynamic> facts;
  final Map<String, dynamic> taskSummary;
  final List<Map<String, dynamic>> recentFeedback;
}

class _PlanContextSnapshotCard extends StatefulWidget {
  const _PlanContextSnapshotCard({
    required this.contextData,
    required this.isDark,
    this.plan,
  });

  final PlanContextData contextData;
  final bool isDark;
  final PlanModel? plan;

  @override
  State<_PlanContextSnapshotCard> createState() =>
      _PlanContextSnapshotCardState();
}

class _PlanContextSnapshotCardState extends State<_PlanContextSnapshotCard>
    with TickerProviderStateMixin {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final plan = widget.plan;
    final planName = plan?.name ?? l10n.planContextTitle;
    final statusLabel =
        _statusLabel(widget.contextData.status, plan?.isActive, l10n);
    final statusColor = _statusColor(widget.contextData.status, plan?.isActive);
    final summary = _taskSummary();

    return SparkleStaggerItem(
      index: 0,
      child: MaterialStyler(
        material: AppMaterials.ceramic.copyWith(
          backgroundColor: widget.isDark ? DS.neutral900 : DS.neutral100,
          borderColor: statusColor.withValues(alpha: 0.2),
        ),
        borderRadius: DS.borderRadius16,
        padding: const EdgeInsets.all(DS.spacing16),
        child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing8,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: DS.borderRadius12,
                ),
                child: Text(
                  statusLabel,
                  style: TextStyle(
                    color: statusColor,
                    fontSize: DS.fontSizeXs,
                    fontWeight: DS.fontWeightSemibold,
                  ),
                ),
              ),
              const SizedBox(width: DS.spacing10),
              Expanded(
                child: Text(
                  planName,
                  style: TextStyle(
                    fontSize: DS.fontSizeBase,
                    fontWeight: DS.fontWeightBold,
                    color: widget.isDark ? DS.neutral100 : DS.neutral900,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              SparkleIconButton(
                variant: ButtonVariant.ghost,
                size: DS.spacing32,
                icon: Icon(
                  _expanded
                      ? Icons.keyboard_arrow_up_rounded
                      : Icons.keyboard_arrow_down_rounded,
                  color: widget.isDark ? DS.neutral300 : DS.neutral600,
                ),
                onPressed: () {
                  unawaited(
                    SensoryFeedbackService.emit(SensoryFeedbackEvent.selection),
                  );
                  setState(() => _expanded = !_expanded);
                },
              ),
            ],
          ),
          const SizedBox(height: DS.spacing12),
          _buildProgress(l10n, summary),
          AnimatedSize(
            duration: AnimationSystem.normal,
            curve: AnimationSystem.smooth,
            alignment: Alignment.topCenter,
            child: _expanded
                ? _buildExpandedContent(l10n)
                : _buildCollapsedHint(l10n),
          ),
        ],
      ),
      ),
    );
  }

  Map<String, int> _taskSummary() {
    final total =
        (widget.contextData.taskSummary['total'] as num?)?.toInt() ?? 0;
    final completed =
        (widget.contextData.taskSummary['completed'] as num?)?.toInt() ?? 0;
    return {'total': total, 'completed': completed};
  }

  Widget _buildProgress(AppLocalizations l10n, Map<String, int> summary) {
    final total = summary['total'] ?? 0;
    final completed = summary['completed'] ?? 0;
    final progress = total > 0 ? completed / total : 0.0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              l10n.planTaskProgress,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: widget.isDark ? DS.neutral400 : DS.neutral600,
              ),
            ),
            Text(
              l10n.tasksCompleted(completed, total),
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: widget.isDark ? DS.neutral300 : DS.neutral600,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
          ],
        ),
        const SizedBox(height: DS.spacing6),
        ClipRRect(
          borderRadius: DS.borderRadius4,
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: (widget.isDark ? DS.neutral800 : DS.neutral200),
            valueColor: AlwaysStoppedAnimation<Color>(DS.primaryBase),
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _buildCollapsedHint(AppLocalizations l10n) {
    final factCount = widget.contextData.facts.length;
    final feedbackCount = widget.contextData.recentFeedback.length;
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing12),
      child: Row(
        children: [
          Icon(
            Icons.info_outline,
            size: DS.iconSizeXs,
            color: widget.isDark ? DS.neutral400 : DS.neutral500,
          ),
          const SizedBox(width: DS.spacing6),
          Text(
            l10n.planFactsFeedbackSummary(factCount, feedbackCount),
            style: TextStyle(
              fontSize: DS.fontSizeXs,
              color: widget.isDark ? DS.neutral400 : DS.neutral600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpandedContent(AppLocalizations l10n) {
    final facts = widget.contextData.facts.entries.toList();
    final feedbacks = widget.contextData.recentFeedback;
    return Padding(
      padding: const EdgeInsets.only(top: DS.spacing12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (facts.isNotEmpty) ...[
            Text(
              l10n.planKeyFacts,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: widget.isDark ? DS.neutral400 : DS.neutral600,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing8),
            Wrap(
              spacing: DS.spacing8,
              runSpacing: DS.spacing8,
              children: facts.map((entry) {
                final value = entry.value;
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: DS.spacing8,
                    vertical: DS.spacing4,
                  ),
                  decoration: BoxDecoration(
                    color: DS.primaryBase.withValues(alpha: 0.08),
                    borderRadius: DS.borderRadius12,
                  ),
                  child: Text(
                    '${entry.key}: $value',
                    style: TextStyle(
                      fontSize: DS.fontSizeXs,
                      color: DS.primaryBase,
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
          if (feedbacks.isNotEmpty) ...[
            const SizedBox(height: DS.spacing12),
            Text(
              l10n.planRecentFeedback,
              style: TextStyle(
                fontSize: DS.fontSizeXs,
                color: widget.isDark ? DS.neutral400 : DS.neutral600,
                fontWeight: DS.fontWeightSemibold,
              ),
            ),
            const SizedBox(height: DS.spacing6),
            ...feedbacks.take(2).map((feedback) {
              final content = feedback['content']?.toString() ?? '';
              return Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.chat_bubble_outline,
                      size: DS.iconSizeXs,
                      color: widget.isDark ? DS.neutral400 : DS.neutral500,
                    ),
                    const SizedBox(width: DS.spacing6),
                    Expanded(
                      child: Text(
                        content.isEmpty ? l10n.planNoContent : content,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: widget.isDark ? DS.neutral200 : DS.neutral700,
                        ),
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ],
      ),
    );
  }

  String _statusLabel(
    String? status,
    bool? isActive,
    AppLocalizations l10n,
  ) {
    if (status != null) {
      switch (status) {
        case 'active':
          return l10n.planStatusActive;
        case 'paused':
          return l10n.planStatusPaused;
        case 'completed':
          return l10n.planStatusCompleted;
        case 'archived':
          return l10n.planStatusArchived;
      }
    }
    if (isActive ?? false) {
      return l10n.planStatusActive;
    }
    if (isActive == false) {
      return l10n.planStatusCompleted;
    }
    return l10n.planStatusUnknown;
  }

  Color _statusColor(String? status, bool? isActive) {
    if (status != null) {
      switch (status) {
        case 'active':
          return DS.success;
        case 'paused':
          return DS.warning;
        case 'completed':
          return DS.info;
        case 'archived':
          return DS.neutral500;
      }
    }
    return isActive ?? false ? DS.success : DS.neutral500;
  }
}

class _PlanContextCard extends StatelessWidget {
  const _PlanContextCard({
    required this.plan,
    required this.isDark,
  });

  final PlanModel plan;
  final bool isDark;

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final planColor = _getPlanColor();

    return Container(
      padding: const EdgeInsets.all(DS.spacing16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            planColor.withValues(alpha: 0.08),
            planColor.withValues(alpha: 0.03),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: DS.borderRadius16,
        border: Border.all(
          color: planColor.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Icon + Name + Type
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(DS.spacing8),
                decoration: BoxDecoration(
                  color: planColor.withValues(alpha: 0.15),
                  borderRadius: DS.borderRadius8,
                ),
                child: Icon(
                  _getPlanIcon(),
                  color: planColor,
                  size: DS.iconSizeBase,
                ),
              ),
              const SizedBox(width: DS.spacing12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      plan.name,
                      style: TextStyle(
                        fontSize: DS.fontSizeBase,
                        fontWeight: DS.fontWeightBold,
                        color: isDark ? DS.neutral100 : DS.neutral900,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      _getPlanTypeLabel(l10n),
                      style: TextStyle(
                        fontSize: DS.fontSizeXs,
                        color: DS.neutral500,
                      ),
                    ),
                  ],
                ),
              ),
              _buildProgressChip(planColor),
            ],
          ),
          const SizedBox(height: DS.spacing12),

          // Progress Bar
          _buildProgressBar(l10n, planColor),
          const SizedBox(height: DS.spacing12),

          // Days Remaining or Mastery Level
          _buildMetadataRow(l10n, planColor),
          const SizedBox(height: DS.spacing12),

          // Next Tasks
          if (plan.tasks != null && plan.tasks!.isNotEmpty)
            _buildNextTasksSection(context, l10n),
        ],
      ),
    );
  }

  Widget _buildProgressChip(Color planColor) {
    final percentage = (plan.progress * 100).toInt();
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: planColor.withValues(alpha: 0.15),
        borderRadius: DS.borderRadius12,
      ),
      child: Text(
        '$percentage%',
        style: TextStyle(
          color: planColor,
          fontSize: DS.fontSizeXs,
          fontWeight: DS.fontWeightSemibold,
        ),
      ),
    );
  }

  Widget _buildProgressBar(AppLocalizations l10n, Color planColor) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                l10n.planProgressLabel,
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.neutral500,
                ),
              ),
              Text(
                l10n.tasksCompleted(_getCompletedTasks(), _getTotalTasks()),
                style: TextStyle(
                  fontSize: DS.fontSizeXs,
                  color: DS.neutral500,
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing4),
          ClipRRect(
            borderRadius: DS.borderRadius4,
            child: LinearProgressIndicator(
              value: plan.progress,
              backgroundColor: planColor.withValues(alpha: 0.1),
              valueColor: AlwaysStoppedAnimation<Color>(planColor),
              minHeight: 6,
            ),
          ),
        ],
      );

  Widget _buildMetadataRow(AppLocalizations l10n, Color planColor) {
    String metadata;
    IconData icon;

    if (plan.type == PlanType.sprint && plan.targetDate != null) {
      final daysRemaining = plan.targetDate!.difference(DateTime.now()).inDays;
      if (daysRemaining > 0) {
        metadata = l10n.planDaysRemaining(daysRemaining);
        icon = Icons.schedule;
      } else if (daysRemaining == 0) {
        metadata = l10n.planDueToday;
        icon = Icons.today;
      } else {
        metadata = l10n.planOverdueDays(-daysRemaining);
        icon = Icons.warning_amber_rounded;
      }
    } else {
      // Growth plan - show mastery level
      final mastery = (plan.masteryLevel * 100).toInt();
      metadata = l10n.planTargetMastery(mastery);
      icon = Icons.stars_rounded;
    }

    return Row(
      children: [
        Icon(icon, size: DS.iconSizeSm, color: planColor),
        const SizedBox(width: DS.spacing4),
        Text(
          metadata,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.neutral600,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
      ],
    );
  }

  Widget _buildNextTasksSection(BuildContext context, AppLocalizations l10n) {
    final nextTasks = _getNextTasks();
    if (nextTasks.isEmpty) return const SizedBox.shrink();

    final textColor = isDark ? DS.neutral300 : DS.neutral700;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.planUpcomingTasks,
          style: TextStyle(
            fontSize: DS.fontSizeXs,
            color: DS.neutral500,
            fontWeight: DS.fontWeightMedium,
          ),
        ),
        const SizedBox(height: DS.spacing4),
        ...nextTasks.take(3).map(
              (task) => Padding(
                padding: const EdgeInsets.only(bottom: DS.spacing4),
                child: Row(
                  children: [
                    Icon(
                      Icons.radio_button_unchecked,
                      size: 12,
                      color: _getTaskStatusColor(task.status),
                    ),
                    const SizedBox(width: DS.spacing8),
                    Expanded(
                      child: Text(
                        task.title,
                        style: TextStyle(
                          fontSize: DS.fontSizeXs,
                          color: textColor,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
      ],
    );
  }

  Color _getPlanColor() {
    switch (plan.type) {
      case PlanType.sprint:
        return DS.error;
      case PlanType.growth:
        return DS.success;
    }
  }

  IconData _getPlanIcon() {
    switch (plan.type) {
      case PlanType.sprint:
        return Icons.directions_run_rounded;
      case PlanType.growth:
        return Icons.trending_up_rounded;
    }
  }

  String _getPlanTypeLabel(AppLocalizations l10n) {
    switch (plan.type) {
      case PlanType.sprint:
        return l10n.planTypeSprint;
      case PlanType.growth:
        return l10n.planTypeGrowth;
    }
  }

  int _getCompletedTasks() =>
      plan.tasks?.where((t) => t.status == TaskStatus.completed).length ?? 0;

  int _getTotalTasks() => plan.tasks?.length ?? 0;

  List<TaskModel> _getNextTasks() {
    final tasks = plan.tasks ?? [];
    // Return pending tasks sorted by created date
    return tasks.where((t) => t.status == TaskStatus.pending).toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
  }

  Color _getTaskStatusColor(TaskStatus status) {
    switch (status) {
      case TaskStatus.completed:
        return DS.success;
      case TaskStatus.inProgress:
        return DS.info;
      case TaskStatus.pending:
        return DS.neutral400;
      case TaskStatus.abandoned:
        return DS.error;
    }
  }
}
