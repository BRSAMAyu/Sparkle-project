import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart'
    show
        TaskNotificationScheduler,
        TaskReminderConfig,
        taskNotificationSchedulerProvider,
        taskReminderConfigProvider;
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/task/presentation/providers/task_provider.dart'
    show taskListProvider;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Screen for configuring task reminder settings
class TaskReminderSettingsScreen extends ConsumerStatefulWidget {
  const TaskReminderSettingsScreen({super.key});

  @override
  ConsumerState<TaskReminderSettingsScreen> createState() =>
      _TaskReminderSettingsScreenState();
}

class _TaskReminderSettingsScreenState
    extends ConsumerState<TaskReminderSettingsScreen> {
  @override
  void initState() {
    super.initState();
    _checkNotificationPermission();
  }

  Future<bool> _checkNotificationPermission() async {
    final plugin = FlutterLocalNotificationsPlugin();
    final android = plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    if (android != null) {
      final granted = await android.areNotificationsEnabled();
      if ((granted ?? false) == false && mounted) {
        _showPermissionDialog();
      }
      return granted ?? false;
    }
    return true;
  }

  Future<void> _requestNotificationPermission() async {
    final plugin = FlutterLocalNotificationsPlugin();
    final android = plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    if (android != null) {
      final granted = await android.requestNotificationsPermission();
      if ((granted ?? false) == false && mounted) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('通知权限被拒绝，您将无法收到任务提醒')),
          );
        }
      }
    }
  }

  void _showPermissionDialog() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          backgroundColor: DS.surfaceBase,
          title: Text('开启通知权限', style: TextStyle(color: DS.brandPrimary)),
          content: Text(
            '为了在任务到期前提醒您，请允许发送通知',
            style: TextStyle(color: DS.brandPrimary70),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('取消', style: TextStyle(color: DS.brandPrimary54)),
            ),
            TextButton(
              onPressed: () {
                Navigator.pop(context);
                _requestNotificationPermission();
              },
              child: Text('去设置', style: TextStyle(color: DS.primaryBase)),
            ),
          ],
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(taskReminderConfigProvider);

    return Scaffold(
      backgroundColor: DS.deepSpaceStart,
      appBar: AppBar(
        backgroundColor: DS.deepSpaceStart,
        title: Text(
          '任务提醒设置',
          style: TextStyle(color: DS.brandPrimary),
        ),
        leading: IconButton(
          icon: Icon(Icons.arrow_back_ios_new, color: DS.brandPrimary),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ContentConstraint(
        child: ListView(
          children: [
          _buildEnableSwitch(config),
          Divider(color: DS.brandPrimary10),
          _buildReminderTimesSection(config),
          Divider(color: DS.brandPrimary10),
          _buildRefreshButton(),
          const SizedBox(height: 20),
          _buildInfoSection(),
        ],
        ),
      ),
    );
  }

  Widget _buildEnableSwitch(TaskReminderConfig config) => SwitchListTile(
      title: Text('启用任务提醒', style: TextStyle(color: DS.brandPrimary)),
      subtitle: Text(
        '在任务到期前发送通知',
        style: TextStyle(color: DS.brandPrimary54),
      ),
      value: config.enabled,
      onChanged: (value) {
        ref.read(taskReminderConfigProvider.notifier).state =
            config.copyWith(enabled: value);
      },
      activeThumbColor: DS.primaryBase,
    );

  Widget _buildReminderTimesSection(TaskReminderConfig config) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            '提醒时间',
            style: TextStyle(
              color: DS.brandPrimary,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        ...TaskReminderSettingsConfigExt.defaultReminders.map((minutes) => CheckboxListTile(
            title: Text(
              _formatReminderTime(minutes),
              style: TextStyle(color: DS.brandPrimary),
            ),
            value: config.reminders.contains(minutes),
            onChanged: config.enabled
                ? (value) {
                    final newReminders = List<int>.from(config.reminders);
                    if (value ?? false) {
                      if (!newReminders.contains(minutes)) {
                        newReminders.add(minutes);
                        newReminders.sort();
                      }
                    } else {
                      newReminders.remove(minutes);
                    }
                    ref.read(taskReminderConfigProvider.notifier).state =
                        config.copyWith(reminders: newReminders);
                  }
                : null,
            activeColor: DS.primaryBase,
            checkColor: DS.brandPrimary,
          ),),
      ],
    );

  Widget _buildRefreshButton() => Padding(
      padding: const EdgeInsets.all(16),
      child: FilledButton.tonalIcon(
        onPressed: () async {
          final scheduler = ref.read(taskNotificationSchedulerProvider);
          final taskRepo = ref.read(taskRepositoryProvider);
          final tasks = await taskRepo.getTasks();
          final config = ref.read(taskReminderConfigProvider);

          await scheduler.refreshAllReminders(tasks.items, config: config);

          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('已刷新所有任务提醒')),
            );
          }
        },
        icon: Icon(Icons.refresh, color: DS.brandPrimary),
        label: Text(
          '刷新所有任务提醒',
          style: TextStyle(color: DS.brandPrimary),
        ),
        style: ButtonStyle(
          backgroundColor: WidgetStateProperty.all(DS.brandPrimary10),
          foregroundColor: WidgetStateProperty.all(DS.brandPrimary),
        ),
      ),
    );

  Widget _buildInfoSection() => Padding(
      padding: const EdgeInsets.all(16),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: DS.brandPrimary10,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.info_outline, color: DS.primaryBase, size: 20),
                const SizedBox(width: 8),
                Text(
                  '关于任务提醒',
                  style: TextStyle(
                    color: DS.brandPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              '• 提醒将在任务到期前按设定时间发送\n'
              '• 修改任务截止日期会自动重新调度提醒\n'
              '• 完成或删除任务会自动取消提醒\n'
              '• 建议开启系统通知权限以接收提醒',
              style: TextStyle(
                color: DS.brandPrimary70,
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );

  String _formatReminderTime(int minutes) {
    if (minutes >= 1440) {
      final days = minutes ~/ 1440;
      return '$days天前';
    } else if (minutes >= 60) {
      final hours = minutes ~/ 60;
      return '$hours小时前';
    } else {
      return '$minutes分钟前';
    }
  }
}

extension TaskReminderSettingsConfigExt on TaskReminderConfig {
  static const List<int> defaultReminders = [1440, 60, 15]; // 1 day, 1 hour, 15 min
}
