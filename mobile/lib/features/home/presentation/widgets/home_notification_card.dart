import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/chat/chat.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';
import 'package:sparkle/features/home/presentation/widgets/dashboard_motion.dart';

class HomeNotificationCard extends ConsumerWidget {
  const HomeNotificationCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(unreadNotificationsProvider);
    final unreadMessageCount = ref.watch(unreadMessageCountProvider);

    if (unreadMessageCount > 0) {
      return ContentConstraint(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            DS.spacing16,
            0,
            DS.spacing16,
            DS.spacing8,
          ),
          child: _NotificationBanner(
            icon: Icons.forum_outlined,
            iconColor: DS.capsuleAccent,
            summary: unreadMessageCount > 99
                ? '99+ 条未读消息'
                : '$unreadMessageCount 条未读消息',
            actionLabel: '查看',
            onTap: () => context.push('/community'),
          ),
        ),
      );
    }

    return notificationsAsync.when(
      data: (notifications) {
        if (notifications.isEmpty) {
          return const SizedBox.shrink();
        }

        return ContentConstraint(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(
              DS.spacing16,
              0,
              DS.spacing16,
              DS.spacing8,
            ),
            child: _NotificationBanner(
              icon: _getIcon(notifications.first.type),
              iconColor: _getIconColor(notifications.first.type),
              summary: notifications.length == 1
                  ? '1 条未读通知'
                  : '${notifications.length} 条未读通知',
              actionLabel: '查看',
              onTap: () => context.push('/notifications'),
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
}

class _NotificationBanner extends StatelessWidget {
  const _NotificationBanner({
    required this.icon,
    required this.iconColor,
    required this.summary,
    required this.actionLabel,
    required this.onTap,
  });

  final IconData icon;
  final Color iconColor;
  final String summary;
  final String actionLabel;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => DashboardEntrance(
        index: 5,
        slideOffset: const Offset(0, -0.06),
        duration: DS.durationFast,
        child: DashboardPressable(
          onTap: onTap,
          borderRadius: DS.borderRadius16,
          child: MaterialStyler(
            material: AppMaterials.ceramic,
            borderRadius: DS.borderRadius16,
            padding: const EdgeInsets.symmetric(
              horizontal: DS.spacing12,
              vertical: DS.spacing10,
            ),
            child: Row(
              children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    color: DS.surfaceOverlay,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    icon,
                    color: iconColor,
                    size: 14,
                  ),
                ),
                const SizedBox(width: DS.spacing10),
                Expanded(
                  child: Text(
                    summary,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: context.sparkleTypography.labelLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: DS.fontWeightSemiBold,
                    ),
                  ),
                ),
                InkWell(
                  onTap: onTap,
                  borderRadius: BorderRadius.circular(999),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: DS.spacing4,
                      vertical: 2,
                    ),
                    child: Text(
                      '$actionLabel →',
                      style: context.sparkleTypography.labelLarge.copyWith(
                        color: DS.brandPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}
