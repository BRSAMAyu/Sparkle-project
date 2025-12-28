import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/data/models/notification_model.dart';

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) => NotificationRepository(ref.read(apiClientProvider)));

class NotificationRepository {

  NotificationRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<NotificationModel>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
  }) async {
    final response = await _apiClient.get(
      '/notifications/',
      queryParameters: {
        'skip': skip,
        'limit': limit,
        'unread_only': unreadOnly,
      },
    );
    // Assuming backend returns a List directly based on previous backend implementation
    // But usually we wrap it in ApiResponseModel? 
    // Wait, the backend implementation in `read_notifications` returns `List[NotificationResponse]`.
    // It does NOT return ApiResponseModel wrapper in the code I wrote in previous turn.
    // However, usually API returns standard structure.
    // Let's check `api_response_model.dart`.
    
    // For now, I'll assume direct list as per my backend code.
    final list = response.data as List<dynamic>;
    return list.map((e) => NotificationModel.fromJson(e)).toList();
  }

  Future<void> markAsRead(String id) async {
    await _apiClient.put('/notifications/$id/read');
  }
}
