import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/data/models/calendar_event_model.dart';

class CalendarRepository {

  CalendarRepository(this._notificationService);
  final NotificationService _notificationService;
  static const String _boxName = 'calendar_events_v1';

  Future<Box> _getBox() async {
    if (!Hive.isBoxOpen(_boxName)) {
      return Hive.openBox(_boxName);
    }
    return Hive.box(_boxName);
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
    _scheduleReminders(event);
  }

  Future<void> updateEvent(CalendarEventModel event) async {
    final box = await _getBox();
    await box.put(event.id, event.toJson());
    _cancelReminders(event.id); 
    _scheduleReminders(event); 
  }

  Future<void> deleteEvent(String id) async {
    final box = await _getBox();
    await box.delete(id);
    _cancelReminders(id);
  }

  void _scheduleReminders(CalendarEventModel event) {
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
        _notificationService.scheduleNotification(
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

  void _cancelReminders(String eventId) {
    final baseId = eventId.hashCode;
    for (var i = 0; i < 5; i++) {
      _notificationService.cancelNotification(baseId + i);
    }
  }
}

final calendarRepositoryProvider = Provider<CalendarRepository>((ref) {
  final notificationService = ref.watch(notificationServiceProvider);
  return CalendarRepository(notificationService);
});