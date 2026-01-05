import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/data/models/notification_model.dart';
import 'package:sparkle/data/repositories/notification_repository.dart';

final unreadNotificationsProvider = StateNotifierProvider<NotificationNotifier,
        AsyncValue<List<NotificationModel>>>(
    (ref) => NotificationNotifier(ref.read(notificationRepositoryProvider)),);

class NotificationNotifier
    extends StateNotifier<AsyncValue<List<NotificationModel>>> {
  NotificationNotifier(this._repository) : super(const AsyncValue.loading()) {
    fetchUnreadNotifications();
  }
  final NotificationRepository _repository;

  Future<void> fetchUnreadNotifications() async {
    try {
      final notifications =
          await _repository.getNotifications(unreadOnly: true);
      state = AsyncValue.data(notifications);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
    }
  }

  Future<void> markAsRead(String id) async {
    try {
      await _repository.markAsRead(id);
      // Optimistically update state
      state.whenData((list) {
        state =
            AsyncValue.data(list.where((element) => element.id != id).toList());
      });
    } catch (e) {
      // Handle error
    }
  }
}
