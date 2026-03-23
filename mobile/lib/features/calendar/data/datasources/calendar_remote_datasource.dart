import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/api_endpoints.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';

/// 日历事件远程数据源
class CalendarRemoteDataSource {
  CalendarRemoteDataSource(this._apiClient);
  final ApiClient _apiClient;

  /// 获取日历事件列表
  Future<List<CalendarEventModel>> getEvents({
    DateTime? startDate,
    DateTime? endDate,
    bool includeDeleted = false,
    int page = 1,
    int pageSize = 50,
  }) async {
    final queryParams = <String, dynamic>{
      'page': page,
      'page_size': pageSize,
      'include_deleted': includeDeleted,
    };
    if (startDate != null) {
      queryParams['start_date'] = _formatDate(startDate);
    }
    if (endDate != null) {
      queryParams['end_date'] = _formatDate(endDate);
    }

    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.calendarEvents,
      queryParameters: queryParams,
    );

    final data = response.data?['data'] as List<dynamic>? ?? [];
    return data
        .map(
            (json) => CalendarEventModel.fromJson(json as Map<String, dynamic>),)
        .toList();
  }

  /// 获取事件统计摘要
  Future<Map<String, dynamic>> getSummary() async {
    final response = await _apiClient.get<Map<String, dynamic>>(
      ApiEndpoints.calendarEventsSummary,
    );
    return response.data ?? {};
  }

  /// 创建日历事件
  Future<CalendarEventModel> createEvent(CalendarEventModel event) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.calendarEvents,
      data: event.toApiJson(),
    );
    return CalendarEventModel.fromJson(response.data!);
  }

  /// 更新日历事件
  Future<CalendarEventModel> updateEvent(CalendarEventModel event) async {
    final response = await _apiClient.put<Map<String, dynamic>>(
      ApiEndpoints.calendarEvent(event.id),
      data: event.toApiJson(),
    );
    return CalendarEventModel.fromJson(response.data!);
  }

  /// 删除日历事件
  Future<void> deleteEvent(String eventId, {bool hardDelete = false}) async {
    await _apiClient.delete<void>(
      ApiEndpoints.calendarEvent(eventId),
      queryParameters: {'hard_delete': hardDelete},
    );
  }

  /// 恢复已删除的事件
  Future<CalendarEventModel> restoreEvent(String eventId) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.calendarEventRestore(eventId),
    );
    return CalendarEventModel.fromJson(
        response.data?['data'] as Map<String, dynamic>,);
  }

  /// 批量操作
  Future<Map<String, dynamic>> batchOperations(
      List<Map<String, dynamic>> operations,) async {
    final response = await _apiClient.post<Map<String, dynamic>>(
      ApiEndpoints.calendarEventsBatch,
      data: {'operations': operations},
    );
    return response.data ?? {};
  }

  String _formatDate(DateTime date) =>
      '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
}

/// Provider for CalendarRemoteDataSource
final calendarRemoteDataSourceProvider =
    Provider<CalendarRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return CalendarRemoteDataSource(apiClient);
});
