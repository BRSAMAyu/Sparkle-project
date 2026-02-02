import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/api_client.dart';
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
      // Return mock notifications for demo mode
      return [
        UnifiedNotification(
          id: 'demo-1',
          sourceType: 'system',
          title: '欢迎使用星火AI学习助手',
          content: '开始您的学习之旅吧！',
          priority: 'medium',
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
          type: 'system',
        ),
        UnifiedNotification(
          id: 'demo-2',
          sourceType: 'intervention',
          title: '休息提醒',
          content: '您已经连续工作45分钟，建议休息一下',
          priority: 'high',
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(minutes: 30)),
          type: 'intervention',
        ),
      ];
    }

    try {
      final queryParams = <String, dynamic>{
        'skip': skip,
        'limit': limit,
        if (unreadOnly) 'unreadOnly': true,
        if (sourceType != null) 'sourceType': sourceType,
      };

      final response = await _client.get<dynamic>(
        '/notification-center/notifications',
        queryParameters: queryParams,
      );

      final data = ApiResponseParser.unwrapList(response.data, action: 'getNotifications');
      return data
          .map((json) => UnifiedNotification.fromJson(json as Map<String, dynamic>))
          .toList();
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Mark a notification as read
  Future<void> markAsRead(String notificationId, String type) async {
    if (DemoDataService.isDemoMode) {
      // No-op in demo mode
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
      // Return mock count for demo mode
      return 2;
    }
    try {
      final response = await _client.put<Map<String, dynamic>>(
        '/notification-center/notifications/mark-all-read',
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'markAllAsRead');
      return payload['count'] as int? ?? 0;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Delete a notification
  Future<void> deleteNotification(String notificationId, String type) async {
    if (DemoDataService.isDemoMode) {
      // No-op in demo mode
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
      // Return mock count for demo mode
      return 1;
    }
    try {
      final response = await _client.delete<Map<String, dynamic>>(
        '/notification-center/notifications/clear-read',
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'clearReadNotifications');
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
      // Return mock history for demo mode
      return {
        'items': [
          UnifiedNotification(
            id: 'demo-history-1',
            sourceType: 'system',
            title: '历史通知1',
            content: '这是一条历史通知',
            priority: 'low',
            isRead: true,
            createdAt: DateTime.now().subtract(const Duration(days: 2)),
            type: 'system',
          ),
        ],
        'total': 1,
        'page': page,
        'page_size': pageSize,
        'total_pages': 1,
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

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getNotificationHistory');

      // Parse items
      final items = (payload['items'] as List? ?? [])
          .map((json) => UnifiedNotification.fromJson(json as Map<String, dynamic>))
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
      // Return mock analytics for demo mode
      return NotificationAnalytics(
        summary: NotificationAnalyticsSummary(
          totalSent: 50,
          totalViewed: 45,
          totalClicked: 30,
          viewRate: 0.9,
          clickRate: 0.6,
          avgTimeToAction: 300.0,
        ),
        byType: {
          'system': NotificationTypeStats(
            type: 'system',
            sent: 30,
            viewed: 27,
            clicked: 18,
            viewRate: 0.9,
            clickRate: 0.6,
          ),
          'intervention': NotificationTypeStats(
            type: 'intervention',
            sent: 20,
            viewed: 18,
            clicked: 12,
            viewRate: 0.9,
            clickRate: 0.6,
          ),
        },
        trends: [],
        hourlyDistribution: List.generate(24, (i) => i * 2),
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

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getAnalytics');
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
        'enable_system_notifications': true,
        'enable_intervention_notifications': true,
        'quiet_hours_start': '22:00',
        'quiet_hours_end': '08:00',
        'sound_enabled': true,
      };
    }

    try {
      final response = await _client.get<Map<String, dynamic>>(
        '/notification-center/preferences',
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'getPreferences');
      return payload;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Update notification preferences
  Future<Map<String, dynamic>> updatePreferences(Map<String, dynamic> updates) async {
    if (DemoDataService.isDemoMode) {
      // Return updated mock preferences for demo mode
      return {
        'enable_system_notifications': true,
        'enable_intervention_notifications': true,
        'quiet_hours_start': '22:00',
        'quiet_hours_end': '08:00',
        'sound_enabled': true,
        ...updates,
      };
    }

    try {
      final response = await _client.put<Map<String, dynamic>>(
        '/notification-center/preferences',
        data: updates,
      );

      final payload = ApiResponseParser.unwrapMap(response.data, action: 'updatePreferences');
      return payload;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  Exception _handleError(DioException e) {
    if (e.response != null) {
      final statusCode = e.response?.statusCode;
      final message = e.response?.data?['message'] ?? 'Unknown error';

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
NotificationCenterRepository notificationCenterRepository(NotificationCenterRepositoryRef ref) {
  final client = ref.watch(apiClientProvider);
  return NotificationCenterRepository(client);
}
