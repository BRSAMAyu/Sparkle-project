import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_tokens.dart';
import 'package:sparkle/core/services/message_notification_service.dart';
import 'package:sparkle/presentation/providers/notification_provider.dart';

class HomeNotificationCard extends ConsumerWidget {
  const HomeNotificationCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(unreadNotificationsProvider);
    final unreadMessageCount = ref.watch(unreadMessageCountProvider);

    // Show community messages notification if there are unread messages
    if (unreadMessageCount > 0) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: _buildCommunityNotificationCard(context, unreadMessageCount),
      );
    }

    return notificationsAsync.when(
      data: (notifications) {
        if (notifications.isEmpty) {
          return const SizedBox.shrink();
        }

        final latest = notifications.first;
        
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: GestureDetector(
            onTap: () => context.push('/notifications'),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: AppDesignTokens.glassBackground,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: AppDesignTokens.glassBorder),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: EdgeInsets.all(DS.sm),
                        decoration: BoxDecoration(
                          color: _getIconColor(latest.type).withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          _getIcon(latest.type),
                          color: _getIconColor(latest.type),
                          size: 16,
                        ),
                      ),
                      SizedBox(width: DS.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              latest.title,
                              style: TextStyle(
                                color: DS.brandPrimaryConst,
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 2),
                            Text(
                              latest.content,
                              style: TextStyle(
                                color: DS.brandPrimary.withValues(alpha: 0.7),
                                fontSize: 11,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      if (notifications.length > 1)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: AppDesignTokens.error,
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(
                            '+${notifications.length - 1}',
                            style: TextStyle(
                              color: DS.brandPrimaryConst,
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      SizedBox(width: DS.sm),
                      Icon(
                        Icons.chevron_right_rounded,
                        color: DS.brandPrimary.withValues(alpha: 0.3),
                        size: 18,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }

  IconData _getIcon(String type) {
    switch (type) {
      case 'fragmented_time':
        return Icons.timer_outlined;
      case 'system':
        return Icons.notifications_none_rounded;
      case 'reminder':
        return Icons.alarm_rounded;
      default:
        return Icons.message_outlined;
    }
  }

  Color _getIconColor(String type) {
    switch (type) {
      case 'fragmented_time':
        return AppDesignTokens.warningAccent;
      case 'system':
        return DS.brandPrimaryAccent;
      case 'reminder':
        return DS.successAccent;
      default:
        return Colors.purpleAccent;
    }
  }

  Widget _buildCommunityNotificationCard(BuildContext context, int unreadCount) => GestureDetector(
      onTap: () => context.push('/community'),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppDesignTokens.glassBackground,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppDesignTokens.glassBorder),
            ),
            child: Row(
              children: [
                Container(
                  padding: EdgeInsets.all(DS.sm),
                  decoration: BoxDecoration(
                    color: Colors.purple.withValues(alpha: 0.2),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.forum_outlined,
                    color: Colors.purple,
                    size: 16,
                  ),
                ),
                SizedBox(width: DS.md),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const Text(
                        '社交消息',
                        style: TextStyle(
                          color: DS.brandPrimaryConst,
                          fontSize: 13,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '你有 $unreadCount 条未读消息',
                        style: TextStyle(
                          color: DS.brandPrimary.withValues(alpha: 0.7),
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppDesignTokens.error,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    unreadCount > 99 ? '99+' : '$unreadCount',
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                SizedBox(width: DS.sm),
                Icon(
                  Icons.chevron_right_rounded,
                  color: DS.brandPrimary.withValues(alpha: 0.3),
                  size: 18,
                ),
              ],
            ),
          ),
        ),
      ),
    );
}
