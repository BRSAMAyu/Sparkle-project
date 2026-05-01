import 'dart:async';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/calendar/data/datasources/calendar_remote_datasource.dart';
import 'package:sparkle/features/calendar/data/models/calendar_event_model.dart';
import 'package:sparkle/shared/entities/task_model.dart';

final _calendarLogger = Logger();

class Log {
  static void i(String tag, String message) =>
      _calendarLogger.i('[$tag] $message');
  static void w(String tag, String message) =>
      _calendarLogger.w('[$tag] $message');
  static void e(String tag, String message) =>
      _calendarLogger.e('[$tag] $message');
}

class CalendarMutationResult {
  const CalendarMutationResult({
    required this.event,
    required this.persistedRemotely,
    this.message,
  });

  final CalendarEventModel event;
  final bool persistedRemotely;
  final String? message;
}

class CalendarRepository {
  CalendarRepository(
    this._notificationService,
    this._remoteDataSource,
  );

  final NotificationService _notificationService;
  final CalendarRemoteDataSource _remoteDataSource;
  static const String _boxName = 'calendar_events_v2';

  Future<Box<dynamic>> _getBox() async {
    if (!Hive.isBoxOpen(_boxName)) {
      return Hive.openBox<dynamic>(_boxName);
    }
    return Hive.box<dynamic>(_boxName);
  }

  /// 获取事件（云端 + 本地缓存）
  Future<List<CalendarEventModel>> getEvents({
    DateTime? startDate,
    DateTime? endDate,
    bool forceRemote = false,
  }) async {
    // 1. 如果强制远程，直接从云端获取
    if (forceRemote) {
      try {
        final remoteEvents = await _remoteDataSource.getEvents(
          startDate: startDate,
          endDate: endDate,
        );
        await _cacheEvents(remoteEvents);
        return _filterEventsByDateRange(remoteEvents, startDate, endDate);
      } catch (e) {
        Log.w('CalendarRepository', 'Failed to fetch from remote: $e');
        // 回退到本地缓存
      }
    }

    // 2. 先返回本地缓存
    final localEvents = await _getLocalEvents();

    // 3. 如果本地无数据，等待远程结果
    if (localEvents.isEmpty) {
      try {
        final remoteEvents = await _remoteDataSource.getEvents(
          startDate: startDate,
          endDate: endDate,
        );
        await _cacheEvents(remoteEvents);
        return _filterEventsByDateRange(remoteEvents, startDate, endDate);
      } catch (e) {
        Log.w('CalendarRepository', 'Failed to fetch from remote: $e');
        return [];
      }
    }

    // 4. 异步后台同步（不阻塞返回）
    unawaited(_syncInBackground(startDate, endDate));

    return _filterEventsByDateRange(localEvents, startDate, endDate);
  }

  /// 创建事件（云端优先）
  Future<CalendarMutationResult> addEvent(CalendarEventModel event) async {
    try {
      // 1. 先保存到云端
      final createdEvent = await _remoteDataSource.createEvent(event);

      // 2. 更新本地缓存（标记为已同步）
      final box = await _getBox();
      await box.put(createdEvent.id, createdEvent.toJson());

      // 3. 调度本地提醒
      await _scheduleReminders(createdEvent);

      Log.i('CalendarRepository', 'Event created and synced: ${createdEvent.id}');
      return CalendarMutationResult(
        event: createdEvent.copyWith(isSynced: true),
        persistedRemotely: true,
      );
    } catch (e) {
      Log.w('CalendarRepository', 'Failed to sync event to cloud: $e');

      // 保存到本地（标记为未同步）
      final localEvent = event.copyWith(isSynced: false);
      final box = await _getBox();
      await box.put(localEvent.id, localEvent.toJson());

      // 调度提醒
      await _scheduleReminders(localEvent);

      return CalendarMutationResult(
        event: localEvent,
        persistedRemotely: false,
        message: I18nService.instance.isChinese
            ? '云端暂时不可用，已先保存到本地并将在稍后同步。'
            : 'Cloud temporarily unavailable, saved locally and will sync later.',
      );
    }
  }

  /// 更新事件
  Future<void> updateEvent(CalendarEventModel event) async {
    try {
      // 1. 更新云端
      await _remoteDataSource.updateEvent(event);

      // 2. 更新本地缓存
      final box = await _getBox();
      await box.put(event.id, event.copyWith(isSynced: true).toJson());

      // 3. 重新调度提醒
      await _cancelReminders(event.id);
      await _scheduleReminders(event);

      Log.i('CalendarRepository', 'Event updated and synced: ${event.id}');
    } catch (e) {
      Log.w('CalendarRepository', 'Failed to sync update to cloud: $e');

      // 更新本地（标记为未同步）
      final box = await _getBox();
      await box.put(event.id, event.copyWith(isSynced: false).toJson());

      // 重新调度提醒
      await _cancelReminders(event.id);
      await _scheduleReminders(event);
    }
  }

  /// 删除事件
  Future<void> deleteEvent(String id) async {
    try {
      // 1. 删除云端
      await _remoteDataSource.deleteEvent(id);

      // 2. 删除本地缓存
      final box = await _getBox();
      await box.delete(id);

      // 3. 取消提醒
      await _cancelReminders(id);

      Log.i('CalendarRepository', 'Event deleted and synced: $id');
    } catch (e) {
      Log.w('CalendarRepository', 'Failed to sync delete to cloud: $e');

      // 软删除本地（标记为删除）
      final box = await _getBox();
      final eventData = box.get(id);
      if (eventData != null) {
        final event = CalendarEventModel.fromJson(
          Map<String, dynamic>.from(eventData as Map),
        );
        await box.put(id, event.copyWith(isDeleted: true, isSynced: false).toJson());
      }

      // 取消提醒
      await _cancelReminders(id);
    }
  }

  /// 恢复已删除的事件
  Future<void> restoreEvent(String id) async {
    try {
      await _remoteDataSource.restoreEvent(id);

      final box = await _getBox();
      final eventData = box.get(id);
      if (eventData != null) {
        final event = CalendarEventModel.fromJson(
          Map<String, dynamic>.from(eventData as Map),
        );
        await box.put(id, event.copyWith(isDeleted: false, isSynced: true).toJson());
      }
    } catch (e) {
      Log.w('CalendarRepository', 'Failed to restore event: $e');
      rethrow;
    }
  }

  Future<CalendarEventModel?> getTaskLinkedEvent(String taskId) async {
    final events = await _getLocalEvents();
    for (final event in events) {
      if (event.taskId == taskId) {
        return event;
      }
    }
    return null;
  }

  Future<void> removeTaskLinkedEvent(String taskId) async {
    final existing = await getTaskLinkedEvent(taskId);
    if (existing == null) return;
    await deleteEvent(existing.id);
  }

  Future<CalendarEventModel?> syncTaskLinkedEvent(TaskModel task) async {
    if (task.dueDate == null) {
      await removeTaskLinkedEvent(task.id);
      return null;
    }

    final existing = await getTaskLinkedEvent(task.id);
    final linkedEvent = _buildTaskLinkedEvent(task, existing: existing);

    if (existing != null) {
      await updateEvent(linkedEvent);
      return linkedEvent.copyWith(isSynced: true);
    }

    final result = await addEvent(linkedEvent);
    return result.event;
  }

  /// 获取事件统计摘要
  Future<Map<String, dynamic>> getSummary() async {
    try {
      return await _remoteDataSource.getSummary();
    } catch (e) {
      Log.w('CalendarRepository', 'Failed to get summary from remote: $e');
      // 计算本地统计
      final events = await _getLocalEvents();
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final weekLater = today.add(const Duration(days: 7));

      return {
        'total': events.where((e) => !e.isDeleted).length,
        'today': events.where((e) {
          final eventDate = DateTime(e.startTime.year, e.startTime.month, e.startTime.day);
          return eventDate == today && !e.isDeleted;
        }).length,
        'upcoming': events
            .where(
              (e) =>
                  e.startTime.isAfter(now) &&
                  e.startTime.isBefore(weekLater) &&
                  !e.isDeleted,
            )
            .length,
        'recurring': events.where((e) => e.isRecurring && !e.isDeleted).length,
      };
    }
  }

  /// 手动触发同步
  Future<void> syncNow() async {
    try {
      final box = await _getBox();

      // 1. 上传未同步的本地更改
      final localEvents = await _getLocalEvents();
      final unsyncedEvents = localEvents.where((e) => !e.isSynced);

      for (final event in unsyncedEvents) {
        if (event.isDeleted) {
          try {
            await _remoteDataSource.deleteEvent(event.id);
            await box.delete(event.id);
          } catch (_) {
            // 忽略删除失败
          }
        } else {
          try {
            await _remoteDataSource.createEvent(event);
            await box.put(event.id, event.copyWith(isSynced: true).toJson());
          } catch (_) {
            // 保留未同步状态
          }
        }
      }

      // 2. 下载云端数据
      final remoteEvents = await _remoteDataSource.getEvents();
      await _cacheEvents(remoteEvents);

      Log.i('CalendarRepository', 'Sync completed');
    } catch (e) {
      Log.e('CalendarRepository', 'Sync failed: $e');
      rethrow;
    }
  }

  // ========== 私有辅助方法 ==========

  Future<List<CalendarEventModel>> _getLocalEvents() async {
    final box = await _getBox();
    return box.values
        .map((e) {
          if (e is Map) {
            return CalendarEventModel.fromJson(Map<String, dynamic>.from(e));
          }
          return null;
        })
        .whereType<CalendarEventModel>()
        .where((e) => !e.isDeleted)
        .toList();
  }

  Future<void> _cacheEvents(List<CalendarEventModel> events) async {
    final box = await _getBox();
    for (final event in events) {
      await box.put(event.id, event.copyWith(isSynced: true).toJson());
    }
  }

  Future<void> _syncInBackground(DateTime? startDate, DateTime? endDate) async {
    try {
      final remoteEvents = await _remoteDataSource.getEvents(
        startDate: startDate,
        endDate: endDate,
      );
      await _cacheEvents(remoteEvents);
    } catch (_) {
      // 静默失败，使用本地数据
    }
  }

  List<CalendarEventModel> _filterEventsByDateRange(
    List<CalendarEventModel> events,
    DateTime? startDate,
    DateTime? endDate,
  ) {
    if (startDate == null && endDate == null) {
      return events.where((e) => !e.isDeleted).toList();
    }

    return events.where((e) {
      if (e.isDeleted) return false;
      if (startDate != null && e.endTime.isBefore(startDate)) return false;
      if (endDate != null && e.startTime.isAfter(endDate)) return false;
      return true;
    }).toList();
  }

  Future<void> _scheduleReminders(CalendarEventModel event) async {
    final zh = I18nService.instance.isChinese;
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
          title: zh ? '日程提醒: ${event.title}' : 'Schedule: ${event.title}',
          body: minutes == 0
              ? (zh ? '现在开始' : 'Starting now')
              : (zh ? '还有 $minutes 分钟开始' : '$minutes minutes until start'),
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

  CalendarEventModel _buildTaskLinkedEvent(
    TaskModel task, {
    CalendarEventModel? existing,
  }) {
    final dueDate = task.dueDate!;
    final isAllDay = dueDate.hour == 0 &&
        dueDate.minute == 0 &&
        dueDate.second == 0 &&
        dueDate.millisecond == 0;
    final startTime = isAllDay
        ? DateTime(dueDate.year, dueDate.month, dueDate.day)
        : dueDate;
    final endTime = isAllDay
        ? startTime.add(const Duration(days: 1))
        : startTime.add(
            Duration(
              minutes: task.estimatedMinutes.clamp(30, 180),
            ),
          );

    return CalendarEventModel(
      id: existing?.id ?? 'task_event_${task.id}',
      title: task.title,
      description: task.guideContent,
      startTime: startTime,
      endTime: endTime,
      isAllDay: isAllDay,
      colorValue: existing?.colorValue ?? 0xFF4CAF50,
      reminderMinutes: existing?.reminderMinutes ?? const [15],
      source: 'task',
      sourceMetadata: {
        'task_sync': true,
        'task_status': task.status.name,
        'estimated_minutes': task.estimatedMinutes,
      },
      taskId: task.id,
      planId: task.planId,
      isSynced: existing?.isSynced ?? false,
      location: existing?.location,
      createdAt: existing?.createdAt ?? DateTime.now(),
      updatedAt: DateTime.now(),
    );
  }
}

final calendarRepositoryProvider = Provider<CalendarRepository>((ref) {
  final notificationService = ref.watch(notificationServiceProvider);
  final remoteDataSource = ref.watch(calendarRemoteDataSourceProvider);
  return CalendarRepository(notificationService, remoteDataSource);
});
