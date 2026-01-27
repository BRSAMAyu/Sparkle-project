import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/features/notification_center/data/models/unified_notification_model.dart';
import 'package:sparkle/features/notification_center/data/models/notification_analytics_model.dart';

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
    try {
      final queryParams = <String, dynamic>{
        'skip': skip,
        'limit': limit,
        if (unreadOnly) 'unreadOnly': true,
        if (sourceType != null) 'sourceType': sourceType,
      };

      final response = await _client.get<List<dynamic>>(
        '/notification-center/notifications',
        queryParameters: queryParams,
      );

      if (response.data == null) {
        return [];
      }

      final notifications = (response.data as List)
          .map((json) => UnifiedNotification.fromJson(json as Map<String, dynamic>))
          .toList();

      return notifications;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Mark a notification as read
  Future<void> markAsRead(String notificationId, String type) async {
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
    try {
      final response = await _client.put<Map<String, dynamic>>(
        '/notification-center/notifications/mark-all-read',
      );

      return response.data?['count'] as int? ?? 0;
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Delete a notification
  Future<void> deleteNotification(String notificationId, String type) async {
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
    try {
      final response = await _client.delete<Map<String, dynamic>>(
        '/notification-center/notifications/clear-read',
      );

      return response.data?['count'] as int? ?? 0;
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

      // Parse items
      final items = (response.data!['items'] as List? ?? [])
          .map((json) => UnifiedNotification.fromJson(json as Map<String, dynamic>))
          .toList();

      return {
        'items': items,
        'total': response.data!['total'] as int? ?? 0,
        'page': response.data!['page'] as int? ?? page,
        'page_size': response.data!['page_size'] as int? ?? pageSize,
        'total_pages': response.data!['total_pages'] as int? ?? 0,
      };
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get notification analytics
  Future<NotificationAnalytics> getAnalytics(String period) async {
    try {
      final response = await _client.get<Map<String, dynamic>>(
        '/notification-center/analytics',
        queryParameters: {'period': period},
      );

      if (response.data == null) {
        throw Exception('No analytics data received');
      }

      return NotificationAnalytics.fromJson(response.data!);
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Get notification preferences
  Future<Map<String, dynamic>> getPreferences() async {
    try {
      final response = await _client.get<Map<String, dynamic>>(
        '/notification-center/preferences',
      );

      return response.data ?? {};
    } on DioException catch (e) {
      throw _handleError(e);
    }
  }

  /// Update notification preferences
  Future<Map<String, dynamic>> updatePreferences(Map<String, dynamic> updates) async {
    try {
      final response = await _client.put<Map<String, dynamic>>(
        '/notification-center/preferences',
        data: updates,
      );

      return response.data ?? {};
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
