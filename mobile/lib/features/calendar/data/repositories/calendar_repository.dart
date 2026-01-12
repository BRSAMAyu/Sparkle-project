import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';

class CalendarRepository {
  CalendarRepository(this._notificationService);
  final NotificationService _notificationService;
  static const String _boxName = 'calendar_events_v1';

  Future<Box<dynamic>> _getBox() async {
    if (!Hive.isBoxOpen(_boxName)) {
      return Hive.openBox<dynamic>(_boxName);
    }
    return Hive.box<dynamic>(_boxName);
  }

  Future<List<CalendarEventModel>> getEvents() async {
    final box = await _getBox();
    return box.values.map((e) {
      if (e is Map) {
        return CalendarEventModel.fromJson(Map<String, dynamic>.from(e));
      }
      return e as CalendarEventModel;
    }).toList();
  }

  Future<void> addEvent(CalendarEventModel event) async {
    final box = await _getBox();
    await box.put(event.id, event.toJson());
    await _scheduleReminders(event);
  }

  Future<void> updateEvent(CalendarEventModel event) async {
    final box = await _getBox();
    await box.put(event.id, event.toJson());
    await _cancelReminders(event.id);
    await _scheduleReminders(event);
  }

  Future<void> deleteEvent(String id) async {
    final box = await _getBox();
    await box.delete(id);
    await _cancelReminders(id);
  }

  Future<void> _scheduleReminders(CalendarEventModel event) async {
    final baseId = event.id.hashCode;

    DateTimeComponents? matchComponents;
    if (event.recurrenceRule == 'daily') {
      matchComponents = DateTimeComponents.time;
    } else if (event.recurrenceRule == 'weekly') {
      matchComponents = DateTimeComponents.dayOfWeekAndTime;
    } else if (event.recurrenceRule == 'monthly') {
      matchComponents = DateTimeComponents.dayOfMonthAndTime;
    }

    for (var i = 0; i < event.reminderMinutes.length; i++) {
      final minutes = event.reminderMinutes[i];
      final reminderTime = event.startTime.subtract(Duration(minutes: minutes));

      if (matchComponents != null || reminderTime.isAfter(DateTime.now())) {
        await _notificationService.scheduleNotification(
          id: baseId + i,
          title: '日程提醒: ${event.title}',
          body: minutes == 0 ? '现在开始' : '还有 $minutes 分钟开始',
          scheduledDate: reminderTime,
          payload: {'eventId': event.id},
          matchDateTimeComponents: matchComponents,
        );
      }
    }
  }

  Future<void> _cancelReminders(String eventId) async {
    final baseId = eventId.hashCode;
    for (var i = 0; i < 5; i++) {
      await _notificationService.cancelNotification(baseId + i);
    }
  }
}

final calendarRepositoryProvider = Provider<CalendarRepository>((ref) {
  final notificationService = ref.watch(notificationServiceProvider);
  return CalendarRepository(notificationService);
});
