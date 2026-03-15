import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/presentation/providers/notification_center_provider.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/notification_filter_chip.dart';
import 'package:sparkle/features/notification_center/presentation/widgets/unified_notification_card.dart';

/// Notification Center Screen
class NotificationCenterScreen extends ConsumerStatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  ConsumerState<NotificationCenterScreen> createState() =>
      _NotificationCenterScreenState();
}

class _NotificationCenterScreenState
    extends ConsumerState<NotificationCenterScreen> {
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

    return SparklePageScaffold(
      role: SparklePageRole.content,
      appBar: AppBar(
        title: Text(context.l10n.notificationCenterTitle),
        actions: [
          // Mark all as read button
          if (state.unreadCount > 0)
            SparkleIconButton(
              onPressed: _markAllAsRead,
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(Icons.done_all, size: DS.iconSizeBase),
                  Positioned(
                    right: -6,
                    top: -6,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 4,
                        vertical: 1,
                      ),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primary,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        state.unreadCount > 99 ? '99+' : '${state.unreadCount}',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              color: Theme.of(context).colorScheme.onPrimary,
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ),
                  ),
                ],
              ),
              semanticLabel:
                  context.l10n.notificationMarkAllRead(state.unreadCount),
              variant: ButtonVariant.ghost,
            ),

          // Menu
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'clear_read') {
                _clearReadNotifications();
              }
            },
            itemBuilder: (context) => [
              PopupMenuItem(
                value: 'clear_read',
                child: Row(
                  children: [
                    const Icon(Icons.delete_sweep),
                    const SizedBox(width: DS.spacing12),
                    Text(context.l10n.notificationClearRead),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      child: ContentConstraint(
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

  Widget _buildFilterBar() => Padding(
        padding: const EdgeInsets.fromLTRB(
          DS.spacing16,
          DS.spacing12,
          DS.spacing16,
          0,
        ),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.panel,
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing16,
            vertical: DS.spacing12,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: NotificationFilter.values
                      .map(
                        (filter) => NotificationFilterChip(
                          label: _getFilterLabel(filter),
                          isSelected: _filter == filter,
                          onTap: () => _setFilter(filter),
                        ),
                      )
                      .toList(),
                ),
              ),
              const SizedBox(height: DS.spacing8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: SourceTypeFilter.values
                      .map(
                        (filter) => NotificationFilterChip(
                          label: _getSourceFilterLabel(filter),
                          isSelected: _sourceFilter == filter,
                          onTap: () => _setSourceFilter(filter),
                        ),
                      )
                      .toList(),
                ),
              ),
            ],
          ),
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
        padding: const EdgeInsets.all(DS.spacing16),
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
            Icon(Icons.error_outline, size: DS.spacing64, color: DS.error),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.loadingFailed,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: DS.spacing8),
            Text(error),
            const SizedBox(height: DS.spacing16),
            SparkleButton(
              onPressed: _refresh,
              label: context.l10n.retry,
            ),
          ],
        ),
      );

  Widget _buildEmpty() => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.notifications_none,
                size: DS.spacing64, color: DS.textTertiary,),
            const SizedBox(height: DS.spacing16),
            Text(
              context.l10n.notificationEmptyTitle,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: DS.textSecondary,
                  ),
            ),
            const SizedBox(height: DS.spacing8),
            Text(
              context.l10n.notificationEmptyDescription,
              style: TextStyle(color: DS.textTertiary),
            ),
          ],
        ),
      );

  List<UnifiedNotification> _filterNotifications(
      List<UnifiedNotification> notifications,) {
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
        filtered =
            filtered.where((n) => n.sourceType == 'intervention').toList();
      case SourceTypeFilter.all:
        break;
    }

    return filtered;
  }

  String _getFilterLabel(NotificationFilter filter) {
    switch (filter) {
      case NotificationFilter.all:
        return context.l10n.notificationFilterAll;
      case NotificationFilter.unread:
        return context.l10n.notificationFilterUnread;
      case NotificationFilter.read:
        return context.l10n.notificationFilterRead;
    }
  }

  String _getSourceFilterLabel(SourceTypeFilter filter) {
    switch (filter) {
      case SourceTypeFilter.all:
        return context.l10n.notificationSourceAll;
      case SourceTypeFilter.system:
        return context.l10n.notificationSourceSystem;
      case SourceTypeFilter.intervention:
        return context.l10n.notificationSourceIntervention;
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
      AppFeedback.success(context, context.l10n.notificationMarkedAllRead);
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
        title: Text(context.l10n.notificationClearReadTitle),
        content: Text(context.l10n.notificationClearReadMessage),
        actions: [
          SparkleButton.ghost(
            onPressed: () => Navigator.pop(context, false),
            label: context.l10n.cancel,
          ),
          SparkleButton(
            onPressed: () => Navigator.pop(context, true),
            label: context.l10n.confirm,
          ),
        ],
      ),
    );

    if (confirmed ?? false) {
      await ref
          .read(notificationCenterProvider.notifier)
          .clearReadNotifications();

      if (mounted) {
        AppFeedback.success(context, context.l10n.notificationClearReadSuccess);
      }
    }
  }

  Future<void> _refresh() async {
    await ref.read(notificationCenterProvider.notifier).refresh();
  }
}
