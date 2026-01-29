import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/notification_filter_chip.dart';

/// Notification Center Screen
class NotificationCenterScreen extends ConsumerStatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  ConsumerState<NotificationCenterScreen> createState() => _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends ConsumerState<NotificationCenterScreen> {
  NotificationFilter _filter = NotificationFilter.all;
  SourceTypeFilter _sourceFilter = SourceTypeFilter.all;

  @override
  void initState() {
    super.initState();
    // Load notifications on init
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(notificationCenterProvider.notifier).loadNotifications();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(notificationCenterProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('通知中心'),
        actions: [
          // Mark all as read button
          if (state.unreadCount > 0)
            TextButton.icon(
              onPressed: _markAllAsRead,
              icon: const Icon(Icons.done_all, size: 20),
              label: Text('全部已读 (${state.unreadCount})'),
            ),

          // Menu
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'clear_read') {
                _clearReadNotifications();
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(
                value: 'clear_read',
                child: Row(
                  children: [
                    Icon(Icons.delete_sweep),
                    SizedBox(width: 12),
                    Text('清除已读'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: ContentConstraint(
        child: Column(
          children: [
            // Filter bar
            _buildFilterBar(),

            // Notifications list
            Expanded(
              child: _buildContent(state),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterBar() => Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.colorCode.surface,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.colorCode.borderSubtle,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Status filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: NotificationFilter.values.map((filter) => NotificationFilterChip(
                  label: _getFilterLabel(filter),
                  isSelected: _filter == filter,
                  onTap: () => _setFilter(filter),
                )).toList(),
            ),
          ),

          const SizedBox(height: 8),

          // Source type filter chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: SourceTypeFilter.values.map((filter) => NotificationFilterChip(
                  label: _getSourceFilterLabel(filter),
                  isSelected: _sourceFilter == filter,
                  onTap: () => _setSourceFilter(filter),
                )).toList(),
            ),
          ),
        ],
      ),
    );

  Widget _buildContent(NotificationCenterState state) {
    if (state.isLoading && state.notifications.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }

    if (state.error != null) {
      return _buildError(state.error!);
    }

    if (state.notifications.isEmpty) {
      return _buildEmpty();
    }

    final filteredNotifications = _filterNotifications(state.notifications);

    if (filteredNotifications.isEmpty) {
      return _buildEmpty();
    }

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: filteredNotifications.length,
        itemBuilder: (context, index) {
          final notification = filteredNotifications[index];
          return UnifiedNotificationCard(
            notification: notification,
            onRead: () => _markAsRead(notification),
            onDelete: () => _deleteNotification(notification),
          );
        },
      ),
    );
  }

  Widget _buildError(String error) => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.red),
          const SizedBox(height: 16),
          Text(
            '加载失败',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(error),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _refresh,
            child: const Text('重试'),
          ),
        ],
      ),
    );

  Widget _buildEmpty() => Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.notifications_none, size: 64, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            '暂无通知',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '当有新通知时，会显示在这里',
            style: TextStyle(color: Colors.grey[500]),
          ),
        ],
      ),
    );

  List<UnifiedNotification> _filterNotifications(List<UnifiedNotification> notifications) {
    var filtered = notifications;

    // Apply status filter
    switch (_filter) {
      case NotificationFilter.unread:
        filtered = filtered.where((n) => !n.isRead).toList();
      case NotificationFilter.read:
        filtered = filtered.where((n) => n.isRead).toList();
      case NotificationFilter.all:
        break;
    }

    // Apply source type filter
    switch (_sourceFilter) {
      case SourceTypeFilter.system:
        filtered = filtered.where((n) => n.sourceType == 'system').toList();
      case SourceTypeFilter.intervention:
        filtered = filtered.where((n) => n.sourceType == 'intervention').toList();
      case SourceTypeFilter.all:
        break;
    }

    return filtered;
  }

  String _getFilterLabel(NotificationFilter filter) {
    switch (filter) {
      case NotificationFilter.all:
        return '全部';
      case NotificationFilter.unread:
        return '未读';
      case NotificationFilter.read:
        return '已读';
    }
  }

  String _getSourceFilterLabel(SourceTypeFilter filter) {
    switch (filter) {
      case SourceTypeFilter.all:
        return '所有类型';
      case SourceTypeFilter.system:
        return '系统通知';
      case SourceTypeFilter.intervention:
        return '干预通知';
    }
  }

  void _setFilter(NotificationFilter filter) {
    setState(() {
      _filter = filter;
    });
  }

  void _setSourceFilter(SourceTypeFilter filter) {
    setState(() {
      _sourceFilter = filter;
    });
  }

  Future<void> _markAsRead(UnifiedNotification notification) async {
    await ref.read(notificationCenterProvider.notifier).markAsRead(
      notification.id,
      notification.sourceType,
    );
  }

  Future<void> _markAllAsRead() async {
    await ref.read(notificationCenterProvider.notifier).markAllAsRead();

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('已标记所有通知为已读')),
      );
    }
  }

  Future<void> _deleteNotification(UnifiedNotification notification) async {
    await ref.read(notificationCenterProvider.notifier).deleteNotification(
      notification.id,
      notification.sourceType,
    );
  }

  Future<void> _clearReadNotifications() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('清除已读通知'),
        content: const Text('确定要清除所有已读通知吗？'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('取消'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('确定'),
          ),
        ],
      ),
    );

    if (confirmed ?? false) {
      await ref.read(notificationCenterProvider.notifier).clearReadNotifications();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('已清除已读通知')),
        );
      }
    }
  }

  Future<void> _refresh() async {
    await ref.read(notificationCenterProvider.notifier).refresh();
  }
}

// Extension for ColorScheme
extension ColorSchemeExtension on ColorScheme {
  _CustomColors get colorCode => _CustomColors(this);
}

class _CustomColors {

  _CustomColors(this.colorScheme);
  final ColorScheme colorScheme;

  Color get surface => colorScheme.surface;
  Color get borderSubtle => colorScheme.outline.withValues(alpha: 0.3);
}
