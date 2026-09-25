import 'package:flutter/foundation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/display/lexicon/error_lexicon.dart';
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

  /// N15（A-SPEC3）：UI 可达错误字段只存类型化类别（渲染侧经
  /// error_lexicon owner 出人话）；原始异常细节只进 debugPrint 日志。
  final UiErrorCategory? error;
  final int unreadCount;

  NotificationCenterState copyWith({
    List<UnifiedNotification>? notifications,
    bool? isLoading,
    UiErrorCategory? error,
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
      debugPrint('[notification_center] loadNotifications failed: $e');
      state = state.copyWith(
        isLoading: false,
        error: categorizeUiError(e),
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  /// P-03 四要素之三：「今天不再看」——引擎侧为该建议类型记录 24h 冷却
  /// （拒绝后 cooldown 在生成源头抑制重复建议，非渲染遮蔽）。
  Future<void> ignoreSuggestionToday(UnifiedNotification notification) async {
    if (!notification.canIgnoreTodaySuggestion) {
      return;
    }
    try {
      await _repository.sendSuggestionAction(
        notification.id,
        'ignore_today',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
          'suggestion_type': notification.suggestionType,
        },
      );
      _updateSuggestionFeedbackLocalState(notification.id, 'ignored_today');
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  /// P-03 四要素之四：「不再提醒此类」——引擎侧持久静音该类型，
  /// 卡片随即从列表移除（aurora_confirm mute 同款交互语义）。
  Future<void> muteSuggestionType(UnifiedNotification notification) async {
    if (!notification.canMuteSuggestionType) {
      return;
    }
    try {
      await _repository.sendSuggestionAction(
        notification.id,
        'mute_type',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
          'suggestion_type': notification.suggestionType,
        },
      );
      removeNotification(notification.id);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
    }
  }

  void _updateSuggestionFeedbackLocalState(String notificationId, String status) {
    final updatedNotifications = state.notifications.map((n) {
      if (n.id != notificationId) {
        return n;
      }
      final metadata = Map<String, dynamic>.from(n.metadata)
        ..['suggestion_feedback'] = status;
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

  Future<void> markRecallInaccurate(UnifiedNotification notification) async {
    if (!notification.hasRecallValueDetails) {
      return;
    }
    try {
      await _repository.sendRecallFeedback(
        notification.id,
        isAccurate: false,
        feedbackReason: 'user_marked_recall_inaccurate',
        actionPayload: {
          'source': 'notification_center_card',
          'surface': 'notification_center',
          'trigger_type': notification.metadata['trigger_type'],
          'recall_score': notification.recallScore,
        },
      );
      _updateRecallFeedbackLocalState(notification.id, 'inaccurate');
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志（调用方 rethrow 后自行兜底提示）。
      debugPrint('[notification_center] sendEncouragement failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
      rethrow;
    }
  }

  /// Apply a user response to an Aurora confirmation queue item (B4-INBOX).
  ///
  /// [action] mirrors the existing aurora calibration respond API:
  /// 'confirm' | 'incorrect' | 'mute'.  Responded cards leave the pending
  /// queue engine-side, so the local item is removed instead of flipped
  /// to read.
  Future<void> respondToAuroraCard(
    UnifiedNotification notification,
    String action,
  ) async {
    if (!notification.isAuroraConfirm) {
      return;
    }
    try {
      await _repository.sendAuroraConfirmAction(notification.id, action);
      removeNotification(notification.id);
    } catch (e) {
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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
      // N15：原始异常只进日志；错误字段存类型化类别。
      debugPrint('[notification_center] op failed: $e');
      state = state.copyWith(error: categorizeUiError(e));
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

  void _updateRecallFeedbackLocalState(String notificationId, String status) {
    final updatedNotifications = state.notifications.map((n) {
      if (n.id != notificationId) {
        return n;
      }
      final metadata = Map<String, dynamic>.from(n.metadata)
        ..['recall_feedback_status'] = status
        ..['recall_feedback'] = {
          'is_accurate': status == 'accurate',
        };
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
  auroraConfirm,
}
