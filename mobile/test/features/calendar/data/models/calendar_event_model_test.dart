import 'package:flutter_test/flutter_test.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';

void main() {
  group('CalendarEventModel', () {
    test('fromJson parses backend snake_case payloads', () {
      final event = CalendarEventModel.fromJson({
        'id': 'event-1',
        'title': '联调日程',
        'description': '验证后端返回结构',
        'start_time': '2026-03-19T10:00:00Z',
        'end_time': '2026-03-19T11:00:00Z',
        'is_all_day': false,
        'location': 'Sparkle Lab',
        'color': '#00BCD4',
        'reminder_minutes': [15, 60],
        'recurrence_rule': 'FREQ=DAILY',
        'recurrence_end_date': '2026-03-26T10:00:00Z',
        'source': 'manual',
        'source_metadata': {'from': 'backend'},
        'task_id': 'task-1',
        'plan_id': 'plan-1',
        'created_at': '2026-03-18T09:00:00Z',
        'updated_at': '2026-03-18T09:30:00Z',
      });

      expect(event.title, '联调日程');
      expect(event.startTime.toUtc().hour, 10);
      expect(event.endTime.toUtc().hour, 11);
      expect(event.location, 'Sparkle Lab');
      expect(event.colorValue, 0xFF00BCD4);
      expect(event.reminderMinutes, [15, 60]);
      expect(event.recurrenceRule, 'FREQ=DAILY');
      expect(event.recurrenceEndDate?.toUtc().day, 26);
      expect(event.sourceMetadata?['from'], 'backend');
      expect(event.taskId, 'task-1');
      expect(event.planId, 'plan-1');
    });

    test('fromJson still supports cached camelCase payloads', () {
      final event = CalendarEventModel.fromJson({
        'id': 'event-2',
        'title': '本地缓存',
        'startTime': '2026-03-19T12:00:00Z',
        'endTime': '2026-03-19T13:00:00Z',
        'createdAt': '2026-03-18T09:00:00Z',
        'updatedAt': '2026-03-18T09:30:00Z',
        'isAllDay': true,
        'colorValue': 0xFF2196F3,
        'isSynced': true,
        'isDeleted': false,
      });

      expect(event.isAllDay, isTrue);
      expect(event.colorValue, 0xFF2196F3);
      expect(event.isSynced, isTrue);
      expect(event.isDeleted, isFalse);
      expect(event.durationMinutes, 60);
    });
  });
}
