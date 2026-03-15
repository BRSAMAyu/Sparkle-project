import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/services/task_notification_scheduler.dart'
    show TaskReminderConfig, taskNotificationSchedulerProvider;
import 'package:sparkle/features/task/data/repositories/task_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart'
    show taskReminderConfigProvider;

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
    final ios = plugin.resolvePlatformSpecificImplementation<
        IOSFlutterLocalNotificationsPlugin>();
    if (android != null) {
      final granted = await android.areNotificationsEnabled();
      if ((granted ?? false) == false && mounted) {
        final requested = await _requestNotificationPermission();
        if (!requested && mounted) {
          _showPermissionDialog();
        }
      }
      return granted ?? false;
    }
    if (ios != null) {
      final requested = await _requestNotificationPermission();
      if (!requested && mounted) {
        _showPermissionDialog();
      }
      return requested;
    }
    return true;
  }

  Future<bool> _requestNotificationPermission() async {
    final plugin = FlutterLocalNotificationsPlugin();
    final android = plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    final ios = plugin.resolvePlatformSpecificImplementation<
        IOSFlutterLocalNotificationsPlugin>();
    if (android != null) {
      final granted = await android.requestNotificationsPermission();
      if ((granted ?? false) == false && mounted) {
        if (context.mounted) {
          AppFeedback.warning(context, '通知权限被拒绝，您将无法收到任务提醒');
        }
      }
      return granted ?? false;
    }
    if (ios != null) {
      final granted = await ios.requestPermissions(
        alert: true,
        badge: true,
        sound: true,
      );
      if ((granted ?? false) == false && mounted) {
        if (context.mounted) {
          AppFeedback.warning(context, '通知权限被拒绝，您将无法收到任务提醒');
        }
      }
      return granted ?? false;
    }
    return true;
  }

  void _showPermissionDialog() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(
        showAppPermissionDialog(
          context,
          permission: AppPermissionKind.notifications,
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(taskReminderConfigProvider);

    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        title: const Text('任务提醒设置'),
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back_ios_new),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      child: ContentConstraint(
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

  Widget _buildEnableSwitch(TaskReminderConfig config) => GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        margin: const EdgeInsets.all(DS.lg),
        padding: EdgeInsets.zero,
        child: SwitchListTile(
          title: const Text('启用任务提醒'),
          subtitle: const Text('在任务到期前发送通知'),
          value: config.enabled,
          onChanged: (value) {
            ref.read(taskReminderConfigProvider.notifier).updateConfig(
                  enabled: value,
                );
          },
          activeThumbColor: DS.primaryBase,
        ),
      );

  Widget _buildReminderTimesSection(TaskReminderConfig config) =>
      GraphiteCardSurface(
        surfaceRole: SparkleSurfaceRole.card,
        margin: const EdgeInsets.symmetric(horizontal: DS.lg),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(DS.lg),
              child: Text(
                '提醒时间',
                style: TextStyle(
                  color: DS.textPrimary,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            ...TaskReminderSettingsConfigExt.defaultReminders.map(
              (minutes) => CheckboxListTile(
                title: Text(
                  _formatReminderTime(minutes),
                  style: TextStyle(color: DS.textPrimary),
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
                        ref
                            .read(taskReminderConfigProvider.notifier)
                            .updateConfig(
                              reminders: newReminders,
                            );
                      }
                    : null,
                activeColor: DS.primaryBase,
                checkColor: DS.textPrimary,
              ),
            ),
          ],
        ),
      );

  Widget _buildRefreshButton() => Padding(
        padding: const EdgeInsets.all(DS.lg),
        child: FilledButton.tonalIcon(
          onPressed: () async {
            final scheduler = ref.read(taskNotificationSchedulerProvider);
            final taskRepo = ref.read(taskRepositoryProvider);
            final tasks = await taskRepo.getTasks();
            final config = ref.read(taskReminderConfigProvider);

            await scheduler.refreshAllReminders(tasks.items, config: config);

            if (mounted) {
              AppFeedback.success(context, '已刷新所有任务提醒');
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
        padding: const EdgeInsets.all(DS.lg),
        child: GraphiteCardSurface(
          surfaceRole: SparkleSurfaceRole.accent,
          padding: const EdgeInsets.all(DS.lg),
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
                      color: DS.textPrimary,
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
                  color: DS.textSecondary,
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
  static const List<int> defaultReminders = [
    1440,
    60,
    15,
  ]; // 1 day, 1 hour, 15 min
}
