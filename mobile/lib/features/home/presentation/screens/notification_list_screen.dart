import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
import 'package:sparkle/core/navigation/route_resilience.dart';
import 'package:sparkle/core/services/deep_link_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/data/models/notification_model.dart';
import 'package:sparkle/features/home/presentation/providers/notification_provider.dart';

class NotificationListScreen extends ConsumerWidget {
  const NotificationListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(unreadNotificationsProvider);

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        leading: SparkleIconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
          variant: ButtonVariant.ghost,
        ),
        title: Text(I18nService.instance.isChinese ? '通知' : 'Notifications'),
      ),
      child: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            final zh = I18nService.instance.isChinese;
            return Center(
              child: Padding(
                padding: EdgeInsets.all(DS.spacing24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.notifications_none_rounded, size: 48),
                    SizedBox(height: DS.spacing12),
                    Text(zh ? '暂无新通知' : 'No new notifications'),
                    SizedBox(height: DS.spacing6),
                    Text(
                      zh ? '学习提醒和周报需要您关注时，会显示在这里。' : 'Study reminders and weekly reports will appear here when they need your attention.',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          }
          return ContentConstraint(
            child: ListView.builder(
              padding: const EdgeInsets.all(DS.spacing16),
              itemCount: notifications.length,
              itemBuilder: (context, index) {
                final notification = notifications[index];
                return NotificationItem(notification: notification);
              },
            ),
          );
        },
        loading: () => Center(child: LoadingIndicator.circular()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.notifications_off_outlined,
                  size: 48, color: DS.textSecondary),
              const SizedBox(height: DS.spacing12),
              Text(I18nService.instance.isChinese ? '加载通知失败，请稍后重试' : 'Failed to load notifications. Please try again later.', style: TextStyle(color: DS.textSecondary)),
            ],
          ),
        ),
      ),
    );
  }
}

class NotificationItem extends ConsumerWidget {
  const NotificationItem({required this.notification, super.key});
  final NotificationModel notification;

  @override
  Widget build(BuildContext context, WidgetRef ref) => Padding(
        padding: const EdgeInsets.only(bottom: DS.spacing12),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.card,
          padding: EdgeInsets.zero,
          child: ListTile(
            title: Text(
              notification.title,
              style: const TextStyle(fontWeight: DS.fontWeightBold),
            ),
            subtitle: Text(notification.content),
            trailing: !notification.isRead
                ? Icon(Icons.circle, size: 12, color: DS.brandPrimary)
                : null,
            onTap: () {
              ref
                  .read(unreadNotificationsProvider.notifier)
                  .markAsRead(notification.id);
              final data = notification.data;
              if (data != null) {
                final destinationRoute = data['destination_route']?.toString();
                if (destinationRoute != null && destinationRoute.isNotEmpty) {
                  unawaited(
                    RouteResilience.openExternalRoute(
                      context,
                      destinationRoute,
                    ),
                  );
                  return;
                }

                final deepLink = data['deep_link']?.toString();
                if (deepLink != null &&
                    deepLink.isNotEmpty &&
                    DeepLinkService.handleExternalDeepLink(context, deepLink)) {
                  return;
                }

                if (notification.type == 'fragmented_time') {
                  final taskId = data['task_id'];
                  if (taskId != null) {
                    unawaited(
                      RouteResilience.openExternalRoute(
                        context,
                        '/tasks/$taskId',
                      ),
                    );
                  }
                }
              }
            },
          ),
        ),
      );
}
