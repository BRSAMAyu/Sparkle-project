import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';

class HomeNotificationCard extends ConsumerWidget {
  const HomeNotificationCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardMaterial = AppMaterials.ceramic.copyWith(
      backgroundColor: isDark
          ? DS.surfaceTertiary.withValues(alpha: 0.94)
          : DS.surfacePrimaryElevated,
      borderColor:
          isDark ? DS.borderStrong.withValues(alpha: 0.55) : DS.borderSubtle,
      rimLightColor: isDark ? Colors.white.withValues(alpha: 0.06) : null,
    );
    final notificationsAsync = ref.watch(unreadNotificationsProvider);
    final unreadMessageCount = ref.watch(unreadMessageCountProvider);

    // Show community messages notification if there are unread messages
    if (unreadMessageCount > 0) {
      return Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing8,
        ),
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
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing8,
          ),
          child: GestureDetector(
            onTap: () => context.push('/notifications'),
            child: MaterialStyler(
              material: cardMaterial,
              borderRadius: BorderRadius.circular(16),
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing16,
                vertical: DS.spacing12,
              ),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(DS.sm),
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
                  const SizedBox(width: DS.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          latest.title,
                          style: TextStyle(
                            color: DS.textPrimary,
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
                            color: DS.textSecondary,
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
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: DS.error,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        '+${notifications.length - 1}',
                        style: TextStyle(
                          color: DS.textOnPrimary,
                          fontSize: 10,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  const SizedBox(width: DS.sm),
                  Icon(
                    Icons.chevron_right_rounded,
                    color: DS.textSecondary,
                    size: 18,
                  ),
                ],
              ),
            ),
          ),
        );
      },
      loading: SizedBox.shrink,
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
        return DS.warning;
      case 'system':
        return DS.brandSecondary;
      case 'reminder':
        return DS.success;
      default:
        return DS.info;
    }
  }

  Widget _buildCommunityNotificationCard(
    BuildContext context,
    int unreadCount,
  ) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cardMaterial = AppMaterials.ceramic.copyWith(
      backgroundColor: isDark
          ? DS.surfaceTertiary.withValues(alpha: 0.94)
          : DS.surfacePrimaryElevated,
      borderColor:
          isDark ? DS.borderStrong.withValues(alpha: 0.55) : DS.borderSubtle,
      rimLightColor: isDark ? Colors.white.withValues(alpha: 0.06) : null,
    );
    return GestureDetector(
      onTap: () => context.push('/community'),
      child: MaterialStyler(
        material: cardMaterial,
        borderRadius: BorderRadius.circular(16),
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing16,
          vertical: DS.spacing12,
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.sm),
              decoration: BoxDecoration(
                color: DS.capsuleAccent.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: Icon(
                Icons.forum_outlined,
                color: DS.capsuleAccent,
                size: 16,
              ),
            ),
            const SizedBox(width: DS.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    '社交消息',
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontSize: 13,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '你有 $unreadCount 条未读消息',
                    style: TextStyle(
                      color: DS.textSecondary,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: DS.spacing8,
                vertical: DS.spacing4,
              ),
              decoration: BoxDecoration(
                color: DS.error,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                unreadCount > 99 ? '99+' : '$unreadCount',
                style: TextStyle(
                  color: DS.textOnPrimary,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: DS.sm),
            Icon(
              Icons.chevron_right_rounded,
              color: DS.textSecondary,
              size: 18,
            ),
          ],
        ),
      ),
    );
  }
}
