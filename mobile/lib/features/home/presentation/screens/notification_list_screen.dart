import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/loading_indicator.dart';
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
        title: const Text('Notifications'),
      ),
      child: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return const Center(child: Text('No new notifications'));
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
        error: (error, stack) => Center(child: Text('Error: $error')),
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
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            subtitle: Text(notification.content),
            trailing: !notification.isRead
                ? Icon(Icons.circle, size: 12, color: DS.brandPrimary)
                : null,
            onTap: () {
              ref
                  .read(unreadNotificationsProvider.notifier)
                  .markAsRead(notification.id);
              if (notification.type == 'fragmented_time' &&
                  notification.data != null) {
                final taskId = notification.data!['task_id'];
                if (taskId != null) {
                  context.push('/tasks/$taskId');
                }
              }
            },
          ),
        ),
      );
}
