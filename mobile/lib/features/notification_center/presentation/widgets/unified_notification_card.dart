import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';

/// Unified Notification Card Widget
class UnifiedNotificationCard extends StatelessWidget {
  const UnifiedNotificationCard({
    required this.notification,
    required this.onRead,
    required this.onDelete,
    super.key,
  });

  final UnifiedNotification notification;
  final VoidCallback onRead;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) => Dismissible(
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
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: notification.isRead
                                      ? FontWeight.normal
                                      : FontWeight.bold,
                                ),
                      ),

                      const SizedBox(height: DS.xs),

                      // Content preview
                      Text(
                        notification.content,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                              color: DS.textSecondary,
                            ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),

                      const SizedBox(height: DS.sm),

                      // Timestamp
                      Row(
                        children: [
                          Icon(
                            Icons.access_time,
                            size: 12,
                            color: DS.textTertiary,
                          ),
                          const SizedBox(width: DS.xs),
                          Text(
                            notification.relativeTime,
                            style: TextStyle(
                              fontSize: 12,
                              color: DS.textSecondary,
                            ),
                          ),
                          const Spacer(),
                          // Source type badge
                          _buildSourceBadge(context),
                        ],
                      ),
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

  Widget _buildSourceBadge(BuildContext context) {
    var badgeColor = DS.neutral500;
    var badgeLabel = '通知';

    switch (notification.sourceType) {
      case 'system':
        badgeColor = DS.info;
        badgeLabel = '系统';
      case 'intervention':
        badgeColor = DS.warning;
        badgeLabel = '干预';
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
    // Navigate based on notification type
    switch (notification.type) {
      case 'plan_archived':
      case 'plan_restored':
      case 'plan_deleted':
        final planId = notification.metadata['plan_id'] as String?;
        if (planId != null) {
          // Navigate to plan detail
          // TODO: Implement navigation
        }

      case 'settings_updated':
      // Navigate to settings
      // TODO: Implement navigation

      case 'achievement':
      // Navigate to achievements
      // TODO: Implement navigation

      default:
        // Show detail dialog
        _showDetailDialog(context);
    }
  }

  void _showDetailDialog(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(notification.title),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(notification.content),
            const SizedBox(height: 16),
            Text(
              notification.relativeTime,
              style: TextStyle(
                fontSize: 12,
                color: DS.textSecondary,
              ),
            ),
          ],
        ),
        actions: [
          SparkleButton.outline(
            label: '关闭',
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
    );
  }
}
