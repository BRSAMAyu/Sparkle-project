// ignore_for_file: avoid_redundant_argument_values

import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/features/notification_center/data/models/notification_analytics_model.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';

part 'notification_center_repository.g.dart';

/// Notification Center Repository
///
/// Provides methods to fetch, manage, and interact with notifications.
class NotificationCenterRepository {
  NotificationCenterRepository(this._client);

  final ApiClient _client;

  /// Get unified notifications (system + interventions)
  Future<List<UnifiedNotification>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
    String? sourceType,
  }) async {
    if (DemoDataService.isDemoMode) {
      final notifications = _demoNotifications();
      return notifications
          .where((item) {
            if (unreadOnly && item.isRead) {
              return false;
            }
            if (sourceType != null && item.sourceType != sourceType) {
              return false;
            }
            return true;
          })
          .skip(skip)
          .take(limit)
          .toList();
    }

    try {
      final queryParams = <String, dynamic>{
        'skip': skip,
        'limit': limit,
        if (unreadOnly) 'unread_only': true,
        if (sourceType != null) 'source_type': sourceType,
      };

      final response = await _client.get<dynamic>(
        '/notification-center/notifications',
        queryParameters: queryParams,
      );

      final data = ApiResponseParser.unwrapList(response.data,
          action: 'getNotifications');
      return data
          .map((json) =>
              UnifiedNotification.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Mark a notification as read
  Future<void> markAsRead(String notificationId, String type) async {
    if (DemoDataService.isDemoMode) {
      final items = DemoDataService().demoNotifications;
      final index = items.indexWhere((item) => item['id'] == notificationId);
      if (index != -1) {
        items[index] = {
          ...items[index],
          'is_read': true,
          'read_at': DateTime.now().toIso8601String(),
        };
      }
      return;
    }
    try {
      await _client.put<Map<String, dynamic>>(
        '/notification-center/notifications/$notificationId/read',
        queryParameters: {'notification_type': type},
      );
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Mark all notifications as read
  Future<int> markAllAsRead() async {
    if (DemoDataService.isDemoMode) {
      final items = DemoDataService().demoNotifications;
      var updated = 0;
      for (var i = 0; i < items.length; i++) {
        if (items[i]['is_read'] != true) {
          items[i] = {
            ...items[i],
            'is_read': true,
            'read_at': DateTime.now().toIso8601String(),
          };
          updated++;
        }
      }
      return updated;
    }
    try {
      final response = await _client.put<Map<String, dynamic>>(
        '/notification-center/notifications/mark-all-read',
      );

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'markAllAsRead');
      return payload['count'] as int? ?? 0;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Send a real interaction state update for a notification-backed intervention.
  Future<void> sendInterventionAction(
    String notificationId,
    String action, {
    Map<String, dynamic>? actionPayload,
  }) async {
    if (DemoDataService.isDemoMode) {
      final items = DemoDataService().demoNotifications;
      final index = items.indexWhere((item) => item['id'] == notificationId);
      if (index != -1) {
        items[index] = {
          ...items[index],
          'is_read': true,
          'read_at': DateTime.now().toIso8601String(),
          'metadata': {
            ...(items[index]['metadata'] as Map<String, dynamic>? ?? {}),
            'client_intervention_state': action,
          },
        };
      }
      return;
    }

    try {
      await _client.post<Map<String, dynamic>>(
        '/notification-center/notifications/$notificationId/intervention-action',
        data: {
          'action': action,
          'action_payload': actionPayload ?? <String, dynamic>{},
        },
      );
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  Future<void> sendPushAction(
    String notificationId,
    String action, {
    Map<String, dynamic>? actionPayload,
  }) async {
    if (DemoDataService.isDemoMode) {
      final items = DemoDataService().demoNotifications;
      final index = items.indexWhere((item) => item['id'] == notificationId);
      if (index != -1) {
        items[index] = {
          ...items[index],
          'is_read': true,
          'read_at': DateTime.now().toIso8601String(),
          'metadata': {
            ...(items[index]['metadata'] as Map<String, dynamic>? ?? {}),
            'push_status': action,
          },
        };
      }
      return;
    }

    try {
      await _client.post<Map<String, dynamic>>(
        '/notification-center/notifications/$notificationId/push-action',
        data: {
          'action': action,
          'action_payload': actionPayload ?? <String, dynamic>{},
        },
      );
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  Future<Map<String, dynamic>> sendAccountabilityEncouragement(
    String notificationId, {
    String? presetId,
    String? message,
  }) async {
    if (DemoDataService.isDemoMode) {
      final items = DemoDataService().demoNotifications;
      final index = items.indexWhere((item) => item['id'] == notificationId);
      if (index != -1) {
        items[index] = {
          ...items[index],
          'is_read': true,
          'read_at': DateTime.now().toIso8601String(),
          'metadata': {
            ...(items[index]['metadata'] as Map<String, dynamic>? ?? {}),
            'encouragement_status': 'sent',
          },
        };
      }
      return {
        'success': true,
        'message': '他收到了你的鼓励',
      };
    }

    try {
      final response = await _client.post<Map<String, dynamic>>(
        ApiEndpoints.accountabilityStruggleAlertEncourage(notificationId),
        data: {
          if (presetId != null) 'preset_id': presetId,
          if (message != null && message.trim().isNotEmpty)
            'message': message.trim(),
        },
      );
      return ApiResponseParser.unwrapMap(
        response.data,
        action: 'sendAccountabilityEncouragement',
      );
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Delete a notification
  Future<void> deleteNotification(String notificationId, String type) async {
    if (DemoDataService.isDemoMode) {
      DemoDataService()
          .demoNotifications
          .removeWhere((item) => item['id'] == notificationId);
      return;
    }
    try {
      await _client.delete<dynamic>(
        '/notification-center/notifications/$notificationId',
        queryParameters: {'notification_type': type},
      );
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Clear all read notifications
  Future<int> clearReadNotifications() async {
    if (DemoDataService.isDemoMode) {
      final items = DemoDataService().demoNotifications;
      final before = items.length;
      items.removeWhere((item) => item['is_read'] == true);
      return before - items.length;
    }
    try {
      final response = await _client.delete<Map<String, dynamic>>(
        '/notification-center/notifications/clear-read',
      );

      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'clearReadNotifications');
      return payload['count'] as int? ?? 0;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get notification history with pagination
  Future<Map<String, dynamic>> getNotificationHistory({
    int page = 1,
    int pageSize = 50,
    String? type,
    DateTime? startDate,
    DateTime? endDate,
    String? search,
  }) async {
    if (DemoDataService.isDemoMode) {
      final all = _demoNotifications();
      final filtered = all.where((item) {
        if (type != null && item.type != type) return false;
        if (startDate != null && item.createdAt.isBefore(startDate))
          return false;
        if (endDate != null && item.createdAt.isAfter(endDate)) return false;
        if (search != null && search.isNotEmpty) {
          final keyword = search.toLowerCase();
          return item.title.toLowerCase().contains(keyword) ||
              item.content.toLowerCase().contains(keyword);
        }
        return true;
      }).toList();
      return {
        'items': filtered.skip((page - 1) * pageSize).take(pageSize).toList(),
        'total': filtered.length,
        'page': page,
        'page_size': pageSize,
        'total_pages': (filtered.length / pageSize).ceil(),
      };
    }

    try {
      final queryParams = <String, dynamic>{
        'page': page,
        'page_size': pageSize,
        if (type != null) 'type': type,
        if (startDate != null) 'start_date': startDate.toIso8601String(),
        if (endDate != null) 'end_date': endDate.toIso8601String(),
        if (search != null && search.isNotEmpty) 'search': search,
      };

      final response = await _client.get<Map<String, dynamic>>(
        '/notification-center/history',
        queryParameters: queryParams,
      );

      if (response.data == null) {
        return {
          'items': <UnifiedNotification>[],
          'total': 0,
          'page': page,
          'page_size': pageSize,
          'total_pages': 0,
        };
      }

      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'getNotificationHistory');

      // Parse items
      final items = (payload['items'] as List? ?? [])
          .map((json) =>
              UnifiedNotification.fromJson(json as Map<String, dynamic>))
          .toList();

      return {
        'items': items,
        'total': payload['total'] as int? ?? 0,
        'page': payload['page'] as int? ?? page,
        'page_size': payload['page_size'] as int? ?? pageSize,
        'total_pages': payload['total_pages'] as int? ?? 0,
      };
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get notification analytics
  Future<NotificationAnalytics> getAnalytics(String period) async {
    if (DemoDataService.isDemoMode) {
      final notifications = _demoNotifications();
      final totalSent = notifications.length;
      final totalViewed = notifications.where((item) => item.isRead).length;
      final totalClicked =
          notifications.where((item) => item.priority == 'high').length;
      final hourlyDistribution = List<int>.generate(24, (hour) {
        if (hour >= 8 && hour <= 10) return 3;
        if (hour >= 12 && hour <= 14) return 2;
        if (hour >= 15 && hour <= 17) return 4;
        if (hour >= 20 && hour <= 22) return 1;
        return 0;
      });
      return NotificationAnalytics(
        summary: NotificationAnalyticsSummary(
          totalSent: totalSent,
          totalViewed: totalViewed,
          totalClicked: totalClicked,
          totalAccepted: notifications
              .where((item) => item.interactionState == 'accepted')
              .length,
          totalActed: notifications
              .where((item) => item.interactionState == 'acted')
              .length,
          viewRate: totalSent == 0 ? 0 : totalViewed / totalSent,
          clickRate: totalSent == 0 ? 0 : totalClicked / totalSent,
          acceptanceRate: totalViewed == 0
              ? 0
              : notifications
                      .where((item) => item.interactionState == 'accepted')
                      .length /
                  totalViewed,
          actionRate: notifications
                  .where((item) => item.interactionState == 'accepted')
                  .isEmpty
              ? 0
              : notifications
                      .where((item) => item.interactionState == 'acted')
                      .length /
                  notifications
                      .where((item) => item.interactionState == 'accepted')
                      .length,
          avgTimeToAction: 240.0,
        ),
        byType: {
          'system': NotificationTypeStats(
            type: 'system',
            sent: notifications
                .where((item) => item.sourceType == 'system')
                .length,
            viewed: notifications
                .where((item) => item.sourceType == 'system' && item.isRead)
                .length,
            clicked: notifications
                .where((item) =>
                    item.sourceType == 'system' && item.priority == 'high')
                .length,
            accepted: 0,
            acted: 0,
            viewRate: 0.9,
            clickRate: 0.55,
            acceptanceRate: 0,
            actionRate: 0,
          ),
          'intervention': NotificationTypeStats(
            type: 'intervention',
            sent: notifications
                .where((item) => item.sourceType == 'intervention')
                .length,
            viewed: notifications
                .where(
                    (item) => item.sourceType == 'intervention' && item.isRead)
                .length,
            clicked: notifications
                .where((item) =>
                    item.sourceType == 'intervention' &&
                    item.priority == 'high')
                .length,
            accepted: notifications
                .where((item) =>
                    item.sourceType == 'intervention' &&
                    item.interactionState == 'accepted')
                .length,
            acted: notifications
                .where((item) =>
                    item.sourceType == 'intervention' &&
                    item.interactionState == 'acted')
                .length,
            viewRate: 0.88,
            clickRate: 0.62,
            acceptanceRate: 0.5,
            actionRate: 0.7,
          ),
        },
        trends: [
          NotificationTrendData(
            date: DateTime.now()
                .subtract(const Duration(days: 2))
                .toIso8601String()
                .split('T')
                .first,
            sent: 7,
            viewed: 6,
            clicked: 4,
            accepted: 3,
            acted: 2,
          ),
          NotificationTrendData(
            date: DateTime.now()
                .subtract(const Duration(days: 1))
                .toIso8601String()
                .split('T')
                .first,
            sent: 8,
            viewed: 7,
            clicked: 5,
            accepted: 4,
            acted: 3,
          ),
          NotificationTrendData(
            date: DateTime.now().toIso8601String().split('T').first,
            sent: 5,
            viewed: 4,
            clicked: 2,
            accepted: 2,
            acted: 1,
          ),
        ],
        hourlyDistribution: hourlyDistribution,
      );
    }

    try {
      final response = await _client.get<Map<String, dynamic>>(
        '/notification-center/analytics',
        queryParameters: {'period': period},
      );

      if (response.data == null) {
        throw Exception('No analytics data received');
      }

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getAnalytics');
      return NotificationAnalytics.fromJson(payload);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get notification preferences
  Future<Map<String, dynamic>> getPreferences() async {
    if (DemoDataService.isDemoMode) {
      // Return mock preferences for demo mode
      return {
        'enable_system': true,
        'enable_interventions': true,
        'notification_level': 'standard',
        'quiet_hours_enabled': false,
        'quiet_hours_start': '22:00',
        'quiet_hours_end': '08:00',
      };
    }

    try {
      final response = await _client.get<Map<String, dynamic>>(
        '/notification-center/preferences',
      );

      final payload =
          ApiResponseParser.unwrapMap(response.data, action: 'getPreferences');
      return payload;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Update notification preferences
  Future<Map<String, dynamic>> updatePreferences(
      Map<String, dynamic> updates) async {
    if (DemoDataService.isDemoMode) {
      // Return updated mock preferences for demo mode
      return {
        'enable_system': true,
        'enable_interventions': true,
        'notification_level': 'standard',
        'quiet_hours_enabled': false,
        'quiet_hours_start': '22:00',
        'quiet_hours_end': '08:00',
        ...updates,
      };
    }

    try {
      final response = await _client.put<Map<String, dynamic>>(
        '/notification-center/preferences',
        data: updates,
      );

      final payload = ApiResponseParser.unwrapMap(response.data,
          action: 'updatePreferences');
      return payload;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  List<UnifiedNotification> _demoNotifications() => DemoDataService()
      .demoNotifications
      .map(
        (item) => UnifiedNotification(
          id: item['id'] as String,
          sourceType: item['type'] == 'achievement' ||
                  item['type'] == 'plan_progress' ||
                  item['type'] == 'task_reminder' ||
                  item['type'] == 'cognitive_insight'
              ? 'system'
              : 'intervention',
          title: item['title'] as String,
          content: item['message'] as String,
          type: item['type'] as String?,
          priority:
              item['type'] == 'achievement' || item['type'] == 'task_reminder'
                  ? 'high'
                  : item['type'] == 'plan_progress'
                      ? 'medium'
                      : 'low',
          isRead: item['is_read'] as bool? ?? false,
          createdAt: DateTime.parse(item['created_at'] as String),
          readAt: item['read_at'] == null
              ? null
              : DateTime.parse(item['read_at'] as String),
          metadata: const {},
        ),
      )
      .toList();

  Exception _handleError(DioException e) {
    if (e.response != null) {
      final statusCode = e.response?.statusCode;
      final responseData = e.response?.data;
      final message = responseData is Map<String, dynamic>
          ? responseData['message'] ?? 'Unknown error'
          : 'Unknown error';

      switch (statusCode) {
        case 400:
          return Exception('Invalid request: $message');
        case 401:
          return Exception('Unauthorized. Please login again.');
        case 403:
          return Exception('Forbidden: $message');
        case 404:
          return Exception('Resource not found');
        case 500:
          return Exception('Server error. Please try again later.');
        default:
          return Exception('Request failed: $message');
      }
    } else if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return Exception('Connection timeout. Please check your network.');
    } else if (e.type == DioExceptionType.connectionError) {
      return Exception('Connection error. Please check your network.');
    }

    return Exception('An unexpected error occurred: ${e.message}');
  }
}

@riverpod
NotificationCenterRepository notificationCenterRepository(
    NotificationCenterRepositoryRef ref) {
  final client = ref.watch(apiClientProvider);
  return NotificationCenterRepository(client);
}
