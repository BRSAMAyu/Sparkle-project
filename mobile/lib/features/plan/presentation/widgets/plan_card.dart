import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/sparkle_tappable.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/shared/utils/entity_card_payloads.dart';

/// 计划卡片组件
/// 用于在聊天中显示 AI 生成的计划
class PlanCard extends StatefulWidget {
  const PlanCard({
    required this.data,
    super.key,
    this.onTap,
    this.onShare,
    this.compact = false,
  });
  final Map<String, dynamic> data;
  final VoidCallback? onTap;
  final VoidCallback? onShare;
  final bool compact;

  @override
  State<PlanCard> createState() => _PlanCardState();
}

class _PlanCardState extends State<PlanCard> {
  void _handleTap() {
    unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
    if (widget.onTap != null) {
      widget.onTap!();
      return;
    }
    final payload = PlanCardPayload.fromMap(widget.data);
    final planId = payload.id;
    final route = payload.entity.detailRoute;
    if (route != null && route.isNotEmpty) {
      unawaited(context.push(route));
      return;
    }
    if (planId != null && planId.isNotEmpty) {
      unawaited(context.push('/plans/$planId'));
      return;
    }
    if (payload.type == 'sprint') {
      unawaited(context.push('/sprint'));
    } else if (payload.type == 'growth') {
      unawaited(context.push('/growth'));
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    final payload = PlanCardPayload.fromMap(widget.data);
    final targetDateLabel = payload.targetDate != null
        ? l10n.planTargetDate(payload.targetDate!.toIso8601String().split('T').first)
        : null;
    final masteryPercent = payload.targetMastery != null
        ? (payload.targetMastery! * 100).round().clamp(0, 100)
        : null;
    final progressValue = (payload.progress ?? 0).clamp(0, 1).toDouble();
    final hasProgress = payload.progress != null;
    final showMeta = !widget.compact &&
        (targetDateLabel != null ||
            masteryPercent != null ||
            payload.taskCount != null ||
            (payload.subject?.isNotEmpty ?? false));

    return SparkleTappable(
      onTap: _handleTap,
      hapticEvent: SensoryFeedbackEvent.selection,
      borderRadius: BorderRadius.circular(16),
      child: GraphiteCardSurface(
        padding: EdgeInsets.all(widget.compact ? DS.md : DS.lg),
        margin: const EdgeInsets.symmetric(vertical: 8),
        borderColor: _chipColor(context, payload.type).withValues(alpha: 0.24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildTypeIcon(payload.type),
                const SizedBox(width: DS.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        payload.title,
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                        maxLines: widget.compact ? 2 : 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if ((payload.description?.isNotEmpty ?? false) &&
                          !widget.compact) ...[
                        const SizedBox(height: DS.xs),
                        Text(
                          payload.description!,
                          style: Theme.of(context).textTheme.bodyMedium,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(width: DS.sm),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    _buildPlanTypeChip(context, payload.type),
                    if ((payload.planStage?.isNotEmpty ?? false) &&
                        !widget.compact) ...[
                      const SizedBox(height: DS.spacing6),
                      _buildPlanStageChip(payload.planStage!),
                    ],
                  ],
                ),
              ],
            ),
            if (hasProgress) ...[
              const SizedBox(height: DS.md),
              ClipRRect(
                borderRadius: BorderRadius.circular(999),
                child: LinearProgressIndicator(
                  value: progressValue,
                  minHeight: widget.compact ? 6 : 8,
                  backgroundColor: DS.neutral200,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _chipColor(context, payload.type),
                  ),
                ),
              ),
              const SizedBox(height: DS.spacing6),
              Text(
                l10n.planProgressPercent(
                  (progressValue * 100).round().toString(),
                ),
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: DS.textSecondary,
                    ),
              ),
            ],
            if (showMeta) ...[
              const SizedBox(height: DS.md),
              Wrap(
                spacing: DS.spacing8,
                runSpacing: DS.spacing8,
                children: [
                  if (payload.subject?.isNotEmpty ?? false)
                    _buildInfoPill(
                      Icons.auto_stories_outlined,
                      payload.subject!,
                    ),
                  if (targetDateLabel != null)
                    _buildInfoPill(Icons.event_outlined, targetDateLabel),
                  if (masteryPercent != null)
                    _buildInfoPill(
                      Icons.track_changes_outlined,
                      l10n.planTargetMastery(masteryPercent),
                    ),
                  if (payload.taskCount != null)
                    _buildInfoPill(
                      Icons.task_alt_outlined,
                      context.l10n.planTaskCount(payload.taskCount!),
                    ),
                ],
              ),
            ],
            if ((widget.onShare != null || payload.entity.share != null) &&
                !widget.compact) ...[
              const SizedBox(height: DS.md),
              Row(
                children: [
                  Expanded(
                    child: SparkleButton.ghost(
                      label: context.l10n.planShareCard,
                      icon: const Icon(Icons.share_outlined),
                      onPressed: () => widget.onShare?.call(),
                    ),
                  ),
                  const SizedBox(width: DS.spacing8),
                  Expanded(
                    child: SparkleButton(
                      label: context.l10n.planViewDetails,
                      icon: const Icon(Icons.arrow_forward_rounded),
                      onPressed: _handleTap,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildTypeIcon(String type) {
    IconData icon;
    Color color;

    switch (type) {
      case 'sprint':
        icon = Icons.directions_run;
        color = DS.warning;
      case 'growth':
        icon = Icons.trending_up;
        color = DS.success;
      default:
        icon = Icons.assignment;
        color = DS.neutral500;
    }

    // Ensure minimum 48x48 touch target
    return Container(
      width: DS.touchTargetMinSize,
      height: DS.touchTargetMinSize,
      padding: const EdgeInsets.all(DS.spacing8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius8,
      ),
      child: Icon(icon, size: DS.iconSizeBase, color: color),
    );
  }

  Widget _buildPlanTypeChip(BuildContext context, String type) {
    final color = _chipColor(context, type);
    final label = type == 'sprint'
        ? context.l10n.planTypeSprint
        : type == 'growth'
            ? context.l10n.planTypeGrowth
            : type;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: DS.spacing8,
        vertical: DS.spacing4,
      ),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: DS.borderRadius12,
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          color: color,
          fontSize: DS.fontSizeXs,
        ),
      ),
    );
  }

  Widget _buildPlanStageChip(String stage) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing4,
        ),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
        ),
        child: Text(
          stage,
          style: TextStyle(
            color: DS.textSecondary,
            fontSize: DS.fontSizeXs,
          ),
        ),
      );

  Widget _buildInfoPill(IconData icon, String label) => Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing8,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: DS.neutral100,
          borderRadius: DS.borderRadius12,
          border: Border.all(color: DS.neutral200),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: DS.iconSizeXs, color: DS.textSecondary),
            const SizedBox(width: DS.spacing4),
            Text(
              label,
              style: TextStyle(
                color: DS.textSecondary,
                fontSize: DS.fontSizeXs,
              ),
            ),
          ],
        ),
      );

  Color _chipColor(BuildContext context, String type) =>
      context.colors.getPlanColor(type);
}
