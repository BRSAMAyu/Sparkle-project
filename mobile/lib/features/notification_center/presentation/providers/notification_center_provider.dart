import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/data/repositories/notification_center_repository.dart';

part 'notification_center_provider.g.dart';

/// Notification Center State
class NotificationCenterState {

  const NotificationCenterState({
    this.notifications = const [],
    this.isLoading = false,
    this.error,
    this.unreadCount = 0,
  });
  final List<UnifiedNotification> notifications;
  final bool isLoading;
  final String? error;
  final int unreadCount;

  NotificationCenterState copyWith({
    List<UnifiedNotification>? notifications,
    bool? isLoading,
    String? error,
    int? unreadCount,
  }) => NotificationCenterState(
      notifications: notifications ?? this.notifications,
      isLoading: isLoading ?? this.isLoading,
      error: error,
      unreadCount: unreadCount ?? this.unreadCount,
    );
}

/// Notification Center Notifier
@riverpod
class NotificationCenter extends _$NotificationCenter {
  late NotificationCenterRepository _repository;

  @override
  NotificationCenterState build() {
    _repository = ref.watch(notificationCenterRepositoryProvider);
    return const NotificationCenterState();
  }

  /// Load notifications
  Future<void> loadNotifications({
    bool unreadOnly = false,
    String? sourceType,
  }) async {
    state = state.copyWith(isLoading: true, error: null);

    try {
      final notifications = await _repository.getNotifications(
        unreadOnly: unreadOnly,
        sourceType: sourceType,
      );

      final unreadCount = notifications.where((n) => !n.isRead).length;

      state = state.copyWith(
        notifications: notifications,
        isLoading: false,
        unreadCount: unreadCount,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Mark notification as read
  Future<void> markAsRead(String notificationId, String type) async {
    try {
      await _repository.markAsRead(notificationId, type);

      // Update local state
      final updatedNotifications = state.notifications.map((n) {
        if (n.id == notificationId) {
          return n.copyWith(isRead: true);
        }
        return n;
      }).toList();

      final unreadCount = updatedNotifications.where((n) => !n.isRead).length;

      state = state.copyWith(
        notifications: updatedNotifications,
        unreadCount: unreadCount,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Mark all notifications as read
  Future<void> markAllAsRead() async {
    try {
      await _repository.markAllAsRead();

      // Update local state
      final updatedNotifications = state.notifications.map((n) => n.copyWith(isRead: true)).toList();

      state = state.copyWith(
        notifications: updatedNotifications,
        unreadCount: 0,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Delete notification
  Future<void> deleteNotification(String notificationId, String type) async {
    try {
      await _repository.deleteNotification(notificationId, type);

      // Remove from local state
      final updatedNotifications = state.notifications
          .where((n) => n.id != notificationId)
          .toList();

      final unreadCount = updatedNotifications.where((n) => !n.isRead).length;

      state = state.copyWith(
        notifications: updatedNotifications,
        unreadCount: unreadCount,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Clear all read notifications
  Future<void> clearReadNotifications() async {
    try {
      await _repository.clearReadNotifications();

      // Remove read notifications from local state
      final updatedNotifications = state.notifications
          .where((n) => !n.isRead)
          .toList();

      state = state.copyWith(
        notifications: updatedNotifications,
      );
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  /// Refresh notifications
  Future<void> refresh() async {
    final currentFilter = state.notifications.isEmpty
        ? null
        : (state.notifications.first.sourceType);

    await loadNotifications(sourceType: currentFilter);
  }
}

/// Filter options for notifications
enum NotificationFilter {
  all,
  unread,
  read,
}

/// Source type filter
enum SourceTypeFilter {
  all,
  system,
  intervention,
}
