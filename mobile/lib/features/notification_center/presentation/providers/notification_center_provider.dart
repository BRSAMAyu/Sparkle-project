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
  }) =>
      NotificationCenterState(
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
    state = state.copyWith(isLoading: true);

    try {
      final notifications = await _repository.getNotifications(
        unreadOnly: unreadOnly,
        sourceType: sourceType,
      );
      final dedupedNotifications = _dedupeNotifications(notifications);

      final unreadCount = dedupedNotifications.where((n) => !n.isRead).length;

      state = state.copyWith(
        notifications: dedupedNotifications,
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

  Future<void> markInterventionSeen(UnifiedNotification notification) async {
    if (!notification.isIntervention || notification.isRead) {
      return;
    }
    try {
      await _repository.sendInterventionAction(
        notification.id,
        'seen',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
        },
      );
      _updateInterventionLocalState(notification.id, 'seen');
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> acceptIntervention(UnifiedNotification notification) async {
    if (!notification.isIntervention) {
      return;
    }
    try {
      await _repository.sendInterventionAction(
        notification.id,
        'accepted',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
          'intent_type': notification.intentType,
        },
      );
      _updateInterventionLocalState(notification.id, 'accepted');
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> snoozeIntervention(UnifiedNotification notification) async {
    if (!notification.isIntervention) {
      return;
    }
    try {
      await _repository.sendInterventionAction(
        notification.id,
        'snoozed',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
          'snooze_hours': 24,
        },
      );
      _updateInterventionLocalState(notification.id, 'snoozed');
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> actOnIntervention(
    UnifiedNotification notification, {
    Map<String, dynamic>? actionPayload,
  }) async {
    if (!notification.isIntervention) {
      return;
    }
    try {
      await _repository.sendInterventionAction(
        notification.id,
        'acted',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
          'intent_type': notification.intentType,
          'plan_id': notification.planId,
          ...?actionPayload,
        },
      );
      _updateInterventionLocalState(notification.id, 'acted');
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> dismissPush(UnifiedNotification notification) async {
    if (!notification.isPush) {
      return;
    }
    try {
      await _repository.sendPushAction(
        notification.id,
        'dismissed',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
        },
      );
      _updatePushLocalState(notification.id, 'dismissed');
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<void> disablePushCategory(UnifiedNotification notification) async {
    if (!notification.isPush) {
      return;
    }
    try {
      await _repository.sendPushAction(
        notification.id,
        'disable_category',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
        },
      );
      _updatePushLocalState(notification.id, 'disable_category');
    } catch (e) {
      state = state.copyWith(error: e.toString());
    }
  }

  Future<Map<String, dynamic>> sendAccountabilityEncouragement(
    UnifiedNotification notification,
  ) async {
    if (!notification.canSendAccountabilityEncouragement) {
      return const {'success': false};
    }
    try {
      final result = await _repository.sendAccountabilityEncouragement(
        notification.id,
      );
      _updateAccountabilityEncouragementLocalState(notification.id);
      return result;
    } catch (e) {
      state = state.copyWith(error: e.toString());
      rethrow;
    }
  }

  /// Mark all notifications as read
  Future<void> markAllAsRead() async {
    try {
      await _repository.markAllAsRead();

      // Update local state
      final updatedNotifications =
          state.notifications.map((n) => n.copyWith(isRead: true)).toList();

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
      final updatedNotifications =
          state.notifications.where((n) => n.id != notificationId).toList();

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
      final updatedNotifications =
          state.notifications.where((n) => !n.isRead).toList();

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

  /// 处理 WebSocket 推送的新通知（实时更新）
  void handleNewNotification({
    required Map<String, dynamic> notificationData,
    required String notificationType,
  }) {
    final normalizedSourceType =
        _resolveRealtimeSourceType(notificationData, notificationType);
    final notification = UnifiedNotification.fromJson({
      ...notificationData,
      if (!notificationData.containsKey('metadata') &&
          notificationData['data'] is Map<String, dynamic>)
        'metadata': notificationData['data'],
      'source_type': normalizedSourceType,
    });

    // 检查是否已存在相同 ID 的通知，避免重复
    final existingIds = state.notifications.map((n) => n.id).toSet();
    if (existingIds.contains(notification.id)) {
      // 更新现有通知
      updateNotification(notification);
      return;
    }

    // 添加到列表开头
    final updatedNotifications = _dedupeNotifications([
      notification,
      ...state.notifications,
    ]);

    // 更新未读计数
    final unreadCount = updatedNotifications.where((n) => !n.isRead).length;

    state = state.copyWith(
      notifications: updatedNotifications,
      unreadCount: unreadCount,
    );
  }

  /// 从列表中移除通知
  void removeNotification(String notificationId) {
    final updatedNotifications =
        state.notifications.where((n) => n.id != notificationId).toList();

    final unreadCount = updatedNotifications.where((n) => !n.isRead).length;

    state = state.copyWith(
      notifications: updatedNotifications,
      unreadCount: unreadCount,
    );
  }

  /// 更新单个通知（用于实时更新已读状态等）
  void updateNotification(UnifiedNotification updated) {
    final updatedNotifications = state.notifications
        .map((n) => n.id == updated.id ? updated : n)
        .toList();

    final unreadCount = updatedNotifications.where((n) => !n.isRead).length;

    state = state.copyWith(
      notifications: updatedNotifications,
      unreadCount: unreadCount,
    );
  }

  void _updateInterventionLocalState(String notificationId, String action) {
    final updatedNotifications = state.notifications.map((n) {
      if (n.id != notificationId) {
        return n;
      }
      final metadata = Map<String, dynamic>.from(n.metadata)
        ..['client_intervention_state'] = action;
      return n.copyWith(
        isRead: true,
        metadata: metadata,
      );
    }).toList();

    final unreadCount = updatedNotifications.where((n) => !n.isRead).length;
    state = state.copyWith(
      notifications: updatedNotifications,
      unreadCount: unreadCount,
    );
  }

  void _updatePushLocalState(String notificationId, String action) {
    final updatedNotifications =
        action == 'dismissed' || action == 'disable_category'
            ? state.notifications.where((n) => n.id != notificationId).toList()
            : state.notifications.map((n) {
                if (n.id != notificationId) {
                  return n;
                }
                final metadata = Map<String, dynamic>.from(n.metadata)
                  ..['push_status'] = action;
                return n.copyWith(
                  isRead: true,
                  metadata: metadata,
                );
              }).toList();

    final unreadCount = updatedNotifications.where((n) => !n.isRead).length;
    state = state.copyWith(
      notifications: updatedNotifications,
      unreadCount: unreadCount,
    );
  }

  void _updateAccountabilityEncouragementLocalState(String notificationId) {
    final updatedNotifications = state.notifications.map((n) {
      if (n.id != notificationId) {
        return n;
      }
      final metadata = Map<String, dynamic>.from(n.metadata)
        ..['encouragement_status'] = 'sent';
      return n.copyWith(
        isRead: true,
        metadata: metadata,
      );
    }).toList();

    final unreadCount = updatedNotifications.where((n) => !n.isRead).length;
    state = state.copyWith(
      notifications: updatedNotifications,
      unreadCount: unreadCount,
    );
  }

  List<UnifiedNotification> _dedupeNotifications(
    List<UnifiedNotification> notifications,
  ) {
    final deduped = <UnifiedNotification>[];
    final seenIds = <String>{};
    final seenFingerprints = <String>{};

    for (final notification in notifications) {
      if (notification.id.isNotEmpty && !seenIds.add(notification.id)) {
        continue;
      }

      final fingerprint = _notificationFingerprint(notification);
      if (!seenFingerprints.add(fingerprint)) {
        continue;
      }

      deduped.add(notification);
    }

    deduped.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return deduped;
  }

  String _notificationFingerprint(UnifiedNotification notification) {
    final createdAtSeconds =
        notification.createdAt.toUtc().millisecondsSinceEpoch ~/ 1000;
    return [
      notification.sourceType,
      notification.type ?? '',
      notification.title.trim(),
      notification.content.trim(),
      createdAtSeconds.toString(),
    ].join('|');
  }

  String _resolveRealtimeSourceType(
    Map<String, dynamic> notificationData,
    String notificationType,
  ) {
    if (notificationType == 'intervention') {
      return 'intervention';
    }
    final type = (notificationData['type'] as String? ?? '').toLowerCase();
    if (type == 'intervention' || type == 'intervention_push') {
      return 'intervention';
    }
    return notificationType;
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
  push,
}
