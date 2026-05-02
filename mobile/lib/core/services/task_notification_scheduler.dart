import 'dart:math';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/core/services/task_notification_id_mapper.dart';
import 'package:sparkle/shared/entities/task_model.dart';

/// Task reminder configuration
class TaskReminderConfig {
  const TaskReminderConfig({
    this.enabled = true,
    this.reminders = const [
      1440,
      60,
      15
    ], // 1 day, 1 hour, 15 minutes (in minutes)
  });

  final bool enabled;
  final List<int> reminders; // Minutes before due date

  TaskReminderConfig copyWith({
    bool? enabled,
    List<int>? reminders,
  }) =>
      TaskReminderConfig(
        enabled: enabled ?? this.enabled,
        reminders: reminders ?? this.reminders,
      );

  static TaskReminderConfig fromJson(Map<String, dynamic> json) =>
      TaskReminderConfig(
        enabled: json['enabled'] as bool? ?? true,
        reminders: (json['reminders'] as List<dynamic>?)
                ?.map((e) => e as int)
                .toList() ??
            const [1440, 60, 15],
      );

  Map<String, dynamic> toJson() => {
        'enabled': enabled,
        'reminders': reminders,
      };
}

/// Scheduler for task reminder notifications
///
/// This service handles:
/// - Scheduling multiple reminders for a task
/// - Canceling all reminders for a task
/// - Re-scheduling when due date changes
class TaskNotificationScheduler {
  TaskNotificationScheduler(
    this._notificationService,
    this._idMapper, {
    Logger? logger,
  }) : _logger = logger ?? Logger();

  final NotificationService _notificationService;
  final TaskNotificationIdMapper _idMapper;
  final Logger _logger;

  /// Base ID for task notifications (ensures uniqueness across app)
  static const int _baseNotificationId = 10000;
  final Random _random = Random();

  /// Schedule reminder notifications for a task
  ///
  /// Returns the list of notification IDs that were scheduled
  Future<List<int>> scheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async {
    if (config != null && !config.enabled) {
      return [];
    }

    // Ensure the mapper is initialized
    await TaskNotificationIdMapper.init();

    // Cancel any existing reminders for this task
    await cancelTaskReminders(task.id);

    if (task.dueDate == null) {
      _logger.d('Task ${task.id} has no due date, skipping reminders');
      return [];
    }

    // Combine due date with a default time (9:00 AM) if no specific time
    final dueDateTime = DateTime(
      task.dueDate!.year,
      task.dueDate!.month,
      task.dueDate!.day,
      9, // Default to 9 AM
    );

    final now = DateTime.now();
    if (dueDateTime.isBefore(now)) {
      _logger.d('Task ${task.id} is already past due, skipping reminders');
      return [];
    }

    final reminderConfig = config ?? const TaskReminderConfig();
    final scheduledIds = <int>[];

    for (final minutesBefore in reminderConfig.reminders) {
      final reminderTime =
          dueDateTime.subtract(Duration(minutes: minutesBefore));

      // Only schedule if reminder time is in the future
      if (reminderTime.isBefore(now)) {
        continue;
      }

      // Generate unique notification ID
      final notificationId = _baseNotificationId + _random.nextInt(90000);

      final payload = {
        'type': 'task_reminder',
        'taskId': task.id,
        'taskTitle': task.title,
        'dueDate': task.dueDate!.toIso8601String(),
        'minutesBefore': minutesBefore,
      };

      // Build notification content based on how close the reminder is
      final title = _buildReminderTitle(minutesBefore);
      final body = '${task.title} - ${_buildReminderBody(minutesBefore)}';

      try {
        await _notificationService.scheduleNotification(
          id: notificationId,
          title: title,
          body: body,
          scheduledDate: reminderTime,
          payload: payload,
        );
        scheduledIds.add(notificationId);
        _logger.i(
          'Scheduled reminder for task ${task.id} at $reminderTime ($minutesBefore minutes before due)',
        );
      } catch (e) {
        _logger.e('Failed to schedule reminder for task ${task.id}: $e');
      }
    }

    // Save the mapping
    if (scheduledIds.isNotEmpty) {
      await _idMapper.saveMapping(task.id, scheduledIds);
    }

    return scheduledIds;
  }

  /// Cancel all reminder notifications for a task
  Future<void> cancelTaskReminders(String taskId) async {
    await TaskNotificationIdMapper.init();

    final notificationIds = await _idMapper.getNotificationIds(taskId);
    for (final id in notificationIds) {
      try {
        await _notificationService.cancelNotification(id);
      } catch (e) {
        _logger.e('Failed to cancel notification $id: $e');
      }
    }

    await _idMapper.removeMapping(taskId);
    _logger.i('Cancelled ${notificationIds.length} reminders for task $taskId');
  }

  /// Re-schedule reminders for a task (e.g., when due date changes)
  Future<List<int>> rescheduleTaskReminders(
    TaskModel task, {
    TaskReminderConfig? config,
  }) async {
    await cancelTaskReminders(task.id);
    return scheduleTaskReminders(task, config: config);
  }

  Future<void> showTaskResumeReminder(TaskModel task) async {
    final payload = {
      'type': 'task_resume',
      'taskId': task.id,
      'taskTitle': task.title,
      'destination_route': '/tasks/${task.id}',
      'deep_link': '/tasks/${task.id}',
    };
    try {
      await _notificationService.showSmartPush(
        title: '任务已暂停',
        body: '你刚暂停了「${task.title}」。回来时可以从恢复卡继续。',
        payload: payload,
      );
    } catch (e) {
      _logger.e('Failed to show resume reminder for task ${task.id}: $e');
    }
  }

  /// Refresh all pending task reminders
  ///
  /// Call this on app startup to ensure all pending tasks have reminders
  Future<void> refreshAllReminders(
    List<TaskModel> pendingTasks, {
    TaskReminderConfig? config,
  }) async {
    await TaskNotificationIdMapper.init();

    // Cancel every previously scheduled reminder before rebuilding mappings,
    // otherwise toggling reminders off still leaves old local notifications.
    final existingTaskIds = await _idMapper.getAllTaskIds();
    for (final taskId in existingTaskIds) {
      await cancelTaskReminders(taskId);
    }

    if (config != null && !config.enabled) {
      _logger.i(
          'Task reminders disabled, cleared ${existingTaskIds.length} mappings');
      return;
    }

    for (final task in pendingTasks) {
      if (task.status != TaskStatus.completed &&
          task.status != TaskStatus.abandoned &&
          task.dueDate != null) {
        try {
          await scheduleTaskReminders(task, config: config);
        } catch (e) {
          _logger.e('Failed to schedule reminders for task ${task.id}: $e');
        }
      }
    }

    _logger.i('Refreshed reminders for ${pendingTasks.length} tasks');
  }

  String _buildReminderTitle(int minutesBefore) {
    if (minutesBefore >= 1440) {
      return '任务提醒';
    } else if (minutesBefore >= 60) {
      return '任务即将到期';
    } else {
      return '任务即将到期';
    }
  }

  String _buildReminderBody(int minutesBefore) {
    if (minutesBefore >= 1440) {
      final days = minutesBefore ~/ 1440;
      return '$days天后到期';
    } else if (minutesBefore >= 60) {
      final hours = minutesBefore ~/ 60;
      return '$hours小时后到期';
    } else {
      return '$minutesBefore分钟后到期';
    }
  }
}

/// Provider for the task notification scheduler
final taskNotificationSchedulerProvider =
    Provider<TaskNotificationScheduler>((ref) {
  final notificationService = ref.watch(notificationServiceProvider);
  final idMapper = TaskNotificationIdMapper();
  return TaskNotificationScheduler(notificationService, idMapper);
});

/// Provider for task reminder settings
final taskReminderConfigProvider =
    StateProvider<TaskReminderConfig>((ref) => const TaskReminderConfig());
