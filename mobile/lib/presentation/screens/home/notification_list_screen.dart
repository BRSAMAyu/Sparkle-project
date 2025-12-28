import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/data/models/notification_model.dart';
import 'package:sparkle/presentation/providers/notification_provider.dart';
import 'package:sparkle/presentation/widgets/common/loading_indicator.dart';

class NotificationListScreen extends ConsumerWidget {
  const NotificationListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(unreadNotificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
      ),
      body: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return const Center(child: Text('No new notifications'));
          }
          return ListView.builder(
            itemCount: notifications.length,
            itemBuilder: (context, index) {
              final notification = notifications[index];
              return NotificationItem(notification: notification);
            },
          );
        },
        loading: () => Center(child: LoadingIndicator.circular()),
        error: (error, stack) => Center(child: Text('Error: $error')),
      ),
    );
  }
}

class NotificationItem extends ConsumerWidget {
  final NotificationModel notification;

  const NotificationItem({required this.notification, super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListTile(
      title: Text(notification.title, style: const TextStyle(fontWeight: FontWeight.bold)),
      subtitle: Text(notification.content),
      trailing: !notification.isRead ? const Icon(Icons.circle, size: 12, color: DS.brandPrimary) : null,
      onTap: () {
        ref.read(unreadNotificationsProvider.notifier).markAsRead(notification.id);
        if (notification.type == 'fragmented_time' && notification.data != null) {
          final taskId = notification.data!['task_id'];
          if (taskId != null) {
            context.push('/tasks/$taskId');
          }
        }
      },
    );
  }
}
