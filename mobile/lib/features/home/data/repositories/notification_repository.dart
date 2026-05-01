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
      final zh = I18nService.instance.isChinese;
      // Return mock notifications for demo mode
      return [
        NotificationModel(
          id: 'demo-1',
          userId: 'demo-user',
          title: zh ? '欢迎使用星火AI学习助手' : 'Welcome to Sparkle AI Learning Assistant',
          content: zh ? '开始您的学习之旅吧！' : 'Start your learning journey!',
          type: 'system',
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(hours: 1)),
        ),
        NotificationModel(
          id: 'demo-2',
          userId: 'demo-user',
          title: zh ? '新任务提醒' : 'New Task Reminder',
          content: zh ? '您有一个即将到期的任务' : 'You have a task due soon',
          type: 'task',
          isRead: false,
          createdAt: DateTime.now().subtract(const Duration(hours: 3)),
        ),
        NotificationModel(
          id: 'demo-3',
          userId: 'demo-user',
          title: zh ? '学习成就解锁' : 'Learning Achievement Unlocked',
          content: zh ? '恭喜您获得"连续学习7天"成就' : 'Congratulations! You\'ve unlocked "7-Day Learning Streak"',
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
