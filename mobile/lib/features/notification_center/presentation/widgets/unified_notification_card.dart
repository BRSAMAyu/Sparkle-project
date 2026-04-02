import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/utils/formatters.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';

/// Unified Notification Card Widget
class UnifiedNotificationCard extends StatelessWidget {
  const UnifiedNotificationCard({
    required this.notification,
    required this.onRead,
    required this.onDelete,
    this.onAccept,
    this.onAct,
    this.onSnooze,
    super.key,
  });

  final UnifiedNotification notification;
  final VoidCallback onRead;
  final VoidCallback onDelete;
  final VoidCallback? onAccept;
  final VoidCallback? onAct;
  final VoidCallback? onSnooze;

  @override
  Widget build(BuildContext context) {
    final acceptAction = onAccept;
    final actAction = onAct;
    final snoozeAction = onSnooze;

    return Dismissible(
      key: Key(notification.id),
      direction: DismissDirection.endToStart,
      onDismissed: (_) => onDelete(),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: DS.spacing20),
        decoration: BoxDecoration(
          color: DS.error,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(Icons.delete, color: DS.onBrandPrimary),
      ),
      child: GestureDetector(
        onTap: () {
          if (!notification.isRead) {
            onRead();
          }
          _handleNavigation(context);
        },
        child: Container(
          margin: const EdgeInsets.only(bottom: DS.spacing12),
          padding: const EdgeInsets.all(DS.md),
          decoration: BoxDecoration(
            color: notification.isRead
                ? DS.surfaceTertiary
                : Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: notification.isRead
                  ? DS.border
                  : Theme.of(context).colorScheme.primary,
              width: notification.isRead ? 1 : 2,
            ),
            boxShadow: [
              BoxShadow(
                color: DS.textPrimary.withValues(alpha: 0.05),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Icon
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: notification.isRead
                      ? DS.neutral200
                      : Theme.of(context).colorScheme.primaryContainer,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Center(
                  child: Text(
                    notification.icon,
                    style: const TextStyle(fontSize: 20),
                  ),
                ),
              ),

              const SizedBox(width: DS.spacing12),

              // Content
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Title
                    Text(
                      notification.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: notification.isRead
                                ? FontWeight.normal
                                : FontWeight.bold,
                          ),
                    ),

                    const SizedBox(height: DS.xs),

                    // Content preview
                    Text(
                      notification.previewText,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: DS.textSecondary,
                          ),
                      maxLines: notification.isIntervention ? 3 : 2,
                      overflow: TextOverflow.ellipsis,
                    ),

                    const SizedBox(height: DS.sm),

                    // Timestamp
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.access_time,
                              size: 12,
                              color: DS.textTertiary,
                            ),
                            const SizedBox(width: DS.xs),
                            Text(
                              Formatters.formatRelativeTime(
                                notification.createdAt,
                              ),
                              style: TextStyle(
                                fontSize: 12,
                                color: DS.textSecondary,
                              ),
                            ),
                          ],
                        ),
                        _buildSourceBadge(context),
                      ],
                    ),
                    if (notification.isIntervention) ...[
                      const SizedBox(height: DS.sm),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          if (notification.canAcceptIntervention &&
                              acceptAction != null)
                            SparkleButton.outline(
                              onPressed: acceptAction,
                              label: context.l10n.focusCandidateAccept,
                            ),
                          if (notification.canActOnIntervention &&
                              actAction != null)
                            SparkleButton(
                              onPressed: actAction,
                              label: context.l10n.taskActionStart,
                            ),
                          if (notification.canAcceptIntervention &&
                              snoozeAction != null)
                            SparkleButton.ghost(
                              onPressed: snoozeAction,
                              label: context.l10n.chatActionLater,
                            ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),

              const SizedBox(width: DS.sm),

              // Unread indicator
              if (!notification.isRead)
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primary,
                    shape: BoxShape.circle,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSourceBadge(BuildContext context) {
    var badgeColor = DS.neutral500;
    var badgeLabel = context.l10n.notificationSourceAll;

    switch (notification.sourceType) {
      case 'system':
        badgeColor = DS.info;
        badgeLabel = context.l10n.notificationSourceSystem;
      case 'intervention':
        badgeColor = DS.warning;
        badgeLabel = context.l10n.notificationSourceIntervention;
      default:
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: badgeColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: badgeColor.withValues(alpha: 0.3)),
      ),
      child: Text(
        badgeLabel,
        style: TextStyle(
          fontSize: 10,
          color: badgeColor,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  void _handleNavigation(BuildContext context) {
    switch (notification.type) {
      case 'intervention':
      case 'intervention_push':
        final planId = notification.planId;
        if (planId != null && planId.isNotEmpty) {
          context.push('/plans/$planId');
        } else {
          _showDetailDialog(context);
        }
        return;

      case 'plan_archived':
      case 'plan_restored':
      case 'plan_deleted':
        final planId = notification.metadata['plan_id'] as String?;
        if (planId != null) {
          context.push('/plans/$planId');
        } else {
          _showDetailDialog(context);
        }
        return;

      case 'settings_updated':
        context.push('/profile/settings');
        return;

      case 'achievement':
        final achievementId =
            notification.metadata['achievement_id'] as String?;
        if (achievementId != null) {
          context.push('/achievements/$achievementId');
        } else {
          context.push('/achievements');
        }
        return;

      case 'task_due':
      case 'task_overdue':
        final taskId = notification.metadata['task_id'] as String?;
        if (taskId != null) {
          context.push('/tasks/$taskId');
        } else {
          _showDetailDialog(context);
        }
        return;

      default:
        _showDetailDialog(context);
        return;
    }
  }

  void _showDetailDialog(BuildContext context) {
    final interactionState = notification.interactionState;
    final outcomeStatus = notification.outcomeStatus;
    final evidence = notification.outcomeEvidence;
    final parameterCompilation = notification.parameterCompilation;

    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(notification.title),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(notification.content),
              if (notification.isIntervention && interactionState != null) ...[
                const SizedBox(height: 12),
                _buildDetailRow(
                  context,
                  '当前状态',
                  _labelForInteractionState(interactionState),
                ),
              ],
              if (notification.isIntervention && outcomeStatus != null) ...[
                const SizedBox(height: 8),
                _buildDetailRow(
                  context,
                  '验证结果',
                  _labelForOutcomeStatus(outcomeStatus),
                ),
              ],
              if (notification.isIntervention &&
                  notification.suggestedStep != null &&
                  notification.suggestedStep!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  '建议动作：${notification.suggestedStep!}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
              ],
              if (notification.isIntervention &&
                  parameterCompilation.isNotEmpty) ...[
                const SizedBox(height: 12),
                _buildDetailRow(
                  context,
                  '参数调整',
                  _buildParameterCompilationSummary(parameterCompilation),
                ),
              ],
              if (notification.isIntervention && evidence.isNotEmpty) ...[
                const SizedBox(height: 12),
                _buildDetailRow(
                  context,
                  '验证证据',
                  _buildEvidenceSummary(evidence),
                ),
              ],
              const SizedBox(height: 16),
              Text(
                Formatters.formatRelativeTime(notification.createdAt),
                style: TextStyle(
                  fontSize: 12,
                  color: DS.textSecondary,
                ),
              ),
            ],
          ),
        ),
        actions: [
          SparkleButton.outline(
            label: context.l10n.commonClose,
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailRow(BuildContext context, String label, String value) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: DS.textSecondary,
                ),
          ),
          const SizedBox(height: 4),
          Text(value),
        ],
      );

  String _labelForInteractionState(String state) {
    switch (state) {
      case 'seen':
        return '已看到';
      case 'accepted':
        return '已接受建议';
      case 'acted':
        return '已开始执行';
      case 'dismissed':
        return '已忽略';
      case 'snoozed':
        return '稍后再看';
      case 'approved':
        return '已确认';
      default:
        return state;
    }
  }

  String _labelForOutcomeStatus(String status) {
    switch (status) {
      case 'EFFECTIVE':
      case 'effective':
        return '已验证有效';
      case 'INEFFECTIVE':
      case 'ineffective':
        return '暂未见效';
      case 'UNKNOWN':
      case 'unknown':
        return '仍在观察';
      case 'PENDING':
      case 'pending':
        return '等待验证';
      default:
        return status;
    }
  }

  String _buildParameterCompilationSummary(Map<String, dynamic> compilation) {
    final result = compilation['result'] as String? ?? 'unknown';
    final affected = compilation['affected_task_count'] as int? ?? 0;
    final inserted = compilation['inserted_task_count'] as int? ?? 0;
    final hidden = compilation['hidden_task_count'] as int? ?? 0;
    return '结果：$result，影响任务 $affected 个，新增 $inserted 个，收起 $hidden 个';
  }

  String _buildEvidenceSummary(Map<String, dynamic> evidence) {
    final improvement = evidence['improvement'];
    if (improvement is Map) {
      final map = Map<String, dynamic>.from(improvement);
      final recovered = map['plan_health_recovered'] == true;
      final masteryImproved = map['mastery_improved'] == true;
      final negativeFeedback =
          map['post_intervention_negative_feedback_count'] as int? ?? 0;
      final feedbackCount =
          map['post_intervention_feedback_count'] as int? ?? 0;
      return [
        if (recovered) '计划健康已恢复',
        if (masteryImproved) '掌握度已提升',
        if (feedbackCount > 0) '后续反馈 $feedbackCount 条',
        if (negativeFeedback > 0) '其中负反馈 $negativeFeedback 条',
      ].where((item) => item.isNotEmpty).join('，');
    }
    return '系统已记录本次干预的后续证据';
  }
}
