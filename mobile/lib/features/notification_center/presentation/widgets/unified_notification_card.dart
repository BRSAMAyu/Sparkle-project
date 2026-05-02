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
    this.onPushDismiss,
    this.onPushDisableCategory,
    this.onRecallInaccurate,
    this.onAccountabilityEncourage,
    super.key,
  });

  final UnifiedNotification notification;
  final VoidCallback onRead;
  final VoidCallback onDelete;
  final VoidCallback? onAccept;
  final VoidCallback? onAct;
  final VoidCallback? onSnooze;
  final VoidCallback? onPushDismiss;
  final VoidCallback? onPushDisableCategory;
  final VoidCallback? onRecallInaccurate;
  final VoidCallback? onAccountabilityEncourage;

  @override
  Widget build(BuildContext context) {
    final acceptAction = onAccept;
    final actAction = onAct;
    final snoozeAction = onSnooze;
    final pushDismissAction = onPushDismiss;
    final pushDisableCategoryAction = onPushDisableCategory;
    final recallInaccurateAction = onRecallInaccurate;
    final accountabilityEncourageAction = onAccountabilityEncourage;

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
                                : DS.fontWeightBold,
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
                    if (notification.hasRecallValueDetails) ...[
                      const SizedBox(height: DS.sm),
                      _buildRecallValueDisclosure(
                        context,
                        onInaccurate: recallInaccurateAction,
                      ),
                    ],
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
                    if (notification.isPush) ...[
                      const SizedBox(height: DS.sm),
                      Wrap(
                        spacing: DS.spacing8,
                        runSpacing: DS.spacing8,
                        children: [
                          if (pushDismissAction != null)
                            SparkleButton.ghost(
                              onPressed: pushDismissAction,
                              label: context.l10n.notificationDismissPush,
                            ),
                          if (notification.canDisablePushCategory &&
                              pushDisableCategoryAction != null)
                            SparkleButton.outline(
                              onPressed: pushDisableCategoryAction,
                              label:
                                  context.l10n.notificationDisablePushCategory,
                            ),
                        ],
                      ),
                    ],
                    if (notification.isAccountabilityStruggleAlert) ...[
                      const SizedBox(height: DS.sm),
                      if (notification.canSendAccountabilityEncouragement &&
                          accountabilityEncourageAction != null)
                        SparkleButton(
                          onPressed: accountabilityEncourageAction,
                          label: notification.accountabilityEncouragementLabel,
                        )
                      else
                        Text(
                          context.l10n.notificationEncouraged,
                          style: DS.bodySmall.copyWith(color: DS.success),
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
      case 'push':
        badgeColor = DS.success;
        badgeLabel = context.l10n.notificationPushReminder;
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
          fontWeight: DS.fontWeightMedium,
        ),
      ),
    );
  }

  Widget _buildRecallValueDisclosure(
    BuildContext context, {
    VoidCallback? onInaccurate,
  }) {
    final score = notification.recallScore;
    final boundedScore = score == null ? null : score.clamp(0.0, 1.0);
    return Container(
      decoration: BoxDecoration(
        color: DS.surfaceSecondary,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: DS.border),
      ),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: DS.spacing12),
          childrenPadding: const EdgeInsets.fromLTRB(
            DS.spacing12,
            0,
            DS.spacing12,
            DS.spacing12,
          ),
          title: Text(
            context.l10n.notificationRecallWhyTitle,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontWeight: DS.fontWeightSemibold,
                ),
          ),
          children: [
            if (_hasText(notification.valueReason))
              _buildDetailRow(
                context,
                context.l10n.notificationRecallGoalValue,
                notification.valueReason!,
              ),
            if (_hasText(notification.recallReason)) ...[
              const SizedBox(height: DS.spacing8),
              _buildDetailRow(
                context,
                context.l10n.notificationRecallReason,
                notification.recallReason!,
              ),
            ],
            if (_hasText(notification.effortEstimate)) ...[
              const SizedBox(height: DS.spacing8),
              _buildDetailRow(
                context,
                context.l10n.notificationRecallEffort,
                notification.effortEstimate!,
              ),
            ],
            if (_hasText(notification.deadlinePressureLabel)) ...[
              const SizedBox(height: DS.spacing8),
              _buildDetailRow(
                context,
                context.l10n.notificationRecallDeadlinePressure,
                notification.deadlinePressureLabel!,
              ),
            ],
            if (boundedScore != null) ...[
              const SizedBox(height: DS.spacing8),
              _buildDetailRow(
                context,
                context.l10n.notificationRecallScore,
                '${(boundedScore * 100).round()}%',
              ),
            ],
            const SizedBox(height: DS.spacing12),
            if (onInaccurate != null)
              Align(
                alignment: Alignment.centerLeft,
                child: SparkleButton.ghost(
                  onPressed: onInaccurate,
                  label: context.l10n.notificationRecallInaccurate,
                ),
              )
            else
              Text(
                context.l10n.notificationRecallFeedbackRecorded,
                style: DS.bodySmall.copyWith(color: DS.success),
              ),
          ],
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

      case 'accountability_struggle_alert':
      case 'accountability_encouragement_received':
        final partnershipId =
            notification.metadata['partnership_id'] as String?;
        if (partnershipId != null && partnershipId.isNotEmpty) {
          context.push('/community/accountability/$partnershipId');
        } else {
          context.push('/community/accountability');
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
                  context.l10n.notificationCurrentState,
                  _labelForInteractionState(context, interactionState),
                ),
              ],
              if (notification.isIntervention && outcomeStatus != null) ...[
                const SizedBox(height: 8),
                _buildDetailRow(
                  context,
                  context.l10n.notificationVerificationResult,
                  _labelForOutcomeStatus(context, outcomeStatus),
                ),
              ],
              if (notification.isIntervention &&
                  notification.suggestedStep != null &&
                  notification.suggestedStep!.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  context.l10n
                      .notificationSuggestedAction(notification.suggestedStep!),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontWeight: DS.fontWeightSemibold,
                      ),
                ),
              ],
              if (notification.isIntervention &&
                  parameterCompilation.isNotEmpty) ...[
                const SizedBox(height: 12),
                _buildDetailRow(
                  context,
                  context.l10n.notificationParameterAdjustment,
                  _buildParameterCompilationSummary(
                    context,
                    parameterCompilation,
                  ),
                ),
              ],
              if (notification.isIntervention && evidence.isNotEmpty) ...[
                const SizedBox(height: 12),
                _buildDetailRow(
                  context,
                  context.l10n.notificationVerificationEvidence,
                  _buildEvidenceSummary(context, evidence),
                ),
              ],
              if (notification.isPush) ...[
                const SizedBox(height: 12),
                _buildDetailRow(
                  context,
                  context.l10n.notificationTriggerEvidence,
                  notification.proactiveReason ??
                      notification.evidenceToken ??
                      context.l10n.notificationNotProvided,
                ),
                const SizedBox(height: 8),
                _buildDetailRow(
                  context,
                  context.l10n.notificationReminderCategory,
                  _labelForPushCategory(context, notification.pushCategory),
                ),
                if (notification.retractableUntil != null) ...[
                  const SizedBox(height: 8),
                  _buildDetailRow(
                    context,
                    context.l10n.notificationRetractableTo,
                    notification.retractableUntil!,
                  ),
                ],
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

  bool _hasText(String? value) => value != null && value.trim().isNotEmpty;

  String _labelForInteractionState(BuildContext context, String state) {
    switch (state) {
      case 'seen':
        return context.l10n.notificationInteractionSeen;
      case 'accepted':
        return context.l10n.notificationInteractionAccepted;
      case 'acted':
        return context.l10n.notificationInteractionActed;
      case 'dismissed':
        return context.l10n.notificationInteractionDismissed;
      case 'snoozed':
        return context.l10n.notificationInteractionSnoozed;
      case 'approved':
        return context.l10n.notificationInteractionApproved;
      default:
        return state;
    }
  }

  String _labelForOutcomeStatus(BuildContext context, String status) {
    switch (status) {
      case 'EFFECTIVE':
      case 'effective':
        return context.l10n.notificationOutcomeEffective;
      case 'INEFFECTIVE':
      case 'ineffective':
        return context.l10n.notificationOutcomeIneffective;
      case 'UNKNOWN':
      case 'unknown':
        return context.l10n.notificationOutcomeUnknown;
      case 'PENDING':
      case 'pending':
        return context.l10n.notificationOutcomePending;
      default:
        return status;
    }
  }

  String _buildParameterCompilationSummary(
    BuildContext context,
    Map<String, dynamic> compilation,
  ) {
    final result = compilation['result'] as String? ?? 'unknown';
    final affected = compilation['affected_task_count'] as int? ?? 0;
    final inserted = compilation['inserted_task_count'] as int? ?? 0;
    final hidden = compilation['hidden_task_count'] as int? ?? 0;
    return context.l10n
        .notificationCompilationSummary(result, affected, inserted, hidden);
  }

  String _buildEvidenceSummary(
    BuildContext context,
    Map<String, dynamic> evidence,
  ) {
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
        if (recovered) context.l10n.notificationEvidencePlanHealthRecovered,
        if (masteryImproved) context.l10n.notificationEvidenceMasteryImproved,
        if (feedbackCount > 0)
          context.l10n.notificationEvidenceFeedbackCount(feedbackCount),
        if (negativeFeedback > 0)
          context.l10n.notificationEvidenceNegativeFeedback(negativeFeedback),
      ].where((item) => item.isNotEmpty).join('，');
    }
    return context.l10n.notificationEvidenceRecorded;
  }

  String _labelForPushCategory(BuildContext context, String? category) {
    switch (category) {
      case 'commitment_follow_up':
        return context.l10n.notificationPushCategoryCommitmentFollowUp;
      case 'engagement_recovery':
        return context.l10n.notificationPushCategoryEngagementRecovery;
      default:
        return category ?? context.l10n.notificationPushCategoryUnknown;
    }
  }
}
