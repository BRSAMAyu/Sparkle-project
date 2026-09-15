import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/network/api_client.dart';
import 'package:sparkle/core/network/response_parser.dart';
import 'package:sparkle/core/services/demo_data_service.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/features/home/data/models/notification_model.dart';

final notificationRepositoryProvider = Provider<NotificationRepository>(
  (ref) => NotificationRepository(ref.read(apiClientProvider)),
);

class NotificationRepository {
  NotificationRepository(this._apiClient);
  final ApiClient _apiClient;

  Future<List<NotificationModel>> getNotifications({
    int skip = 0,
    int limit = 50,
    bool unreadOnly = false,
  }) async {
    if (DemoDataService.isDemoMode) {
      final l10n = I18nService.instance.l10n;
      // Return mock notifications for demo mode
      return [
        NotificationModel(
          id: 'demo-1',
          userId: 'demo-user',
          title: l10n.notificationWelcomeTitle,
          content: l10n.notificationWelcomeContent,
          type: 'system',
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
        ),
        NotificationModel(
          id: 'demo-2',
          userId: 'demo-user',
          title: l10n.notificationNewTaskTitle,
          content: l10n.notificationNewTaskContent,
          type: 'task',
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(hours: 3)),
        ),
        NotificationModel(
          id: 'demo-3',
          userId: 'demo-user',
          title: l10n.notificationAchievementTitle,
          content: l10n.notificationAchievementContent,
          type: 'achievement',
          isRead: true,
          createdAt: DateTime.now().subtract(const Duration(days: 1)),
        ),
      ];
    }

    final response = await _apiClient.get<dynamic>(
      '/notifications',
      queryParameters: {
        'skip': skip,
        'limit': limit,
        'unread_only': unreadOnly,
      },
    );

    final data =
        ApiResponseParser.unwrapList(response.data, action: 'getNotifications');
    return data
        .map((e) => NotificationModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<void> markAsRead(String id) async {
    if (DemoDataService.isDemoMode) {
      // No-op in demo mode
      return;
    }
    await _apiClient.put<dynamic>('/notifications/$id/read');
  }
}
