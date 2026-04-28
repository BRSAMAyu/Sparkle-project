import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/widgets/app_permission_dialog.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/i18n_service.dart';
import 'package:sparkle/core/services/notification_service.dart';
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
    final service = ref.read(notificationServiceProvider);
    final status = await service.checkPermissionStatus();
    if (status.hasPermission) {
      return true;
    }
    if (!mounted) {
      return false;
    }
    final requested = await _requestNotificationPermission();
    if (!requested && mounted) {
      _showPermissionDialog();
    }
    return requested;
  }

  Future<bool> _requestNotificationPermission() async {
    final granted =
        await ref.read(notificationServiceProvider).requestPermission();
    if (!granted && mounted && context.mounted) {
      AppFeedback.warning(
        context,
        context.l10n.taskReminderPermissionDenied,
      );
    }
    return granted;
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
        title: Text(context.l10n.taskReminderSettingsTitle),
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
          title: Text(context.l10n.taskReminderEnableTitle),
          subtitle: Text(context.l10n.taskReminderEnableSubtitle),
          value: config.enabled,
          onChanged: (value) async {
            if (value) {
              final granted = await _checkNotificationPermission();
              if (!granted) {
                return;
              }
            }
            try {
              await ref.read(taskReminderConfigProvider.notifier).updateConfig(
                    enabled: value,
                  );
            } catch (e) {
              if (!context.mounted) return;
              AppFeedback.error(
                context,
                context.l10n.taskReminderUpdateFailed(e.toString().replaceFirst('Exception: ', '').trim()),
              );
            }
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
                context.l10n.taskReminderTimesTitle,
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
                    ? (value) async {
                        final newReminders = List<int>.from(config.reminders);
                        if (value ?? false) {
                          if (!newReminders.contains(minutes)) {
                            newReminders.add(minutes);
                            newReminders.sort();
                          }
                        } else {
                          newReminders.remove(minutes);
                        }
                        try {
                          await ref
                              .read(taskReminderConfigProvider.notifier)
                              .updateConfig(
                                reminders: newReminders,
                              );
                        } catch (e) {
                          if (!context.mounted) return;
                          AppFeedback.error(
                            context,
                            context.l10n.taskReminderTimeFailed(e.toString().replaceFirst('Exception: ', '').trim()),
                          );
                        }
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
            try {
              final scheduler = ref.read(taskNotificationSchedulerProvider);
              final taskRepo = ref.read(taskRepositoryProvider);
              final tasks = await taskRepo.getTasks();
              final config = ref.read(taskReminderConfigProvider);

              await scheduler.refreshAllReminders(tasks.items, config: config);

              if (mounted) {
                AppFeedback.success(
                  context,
                  context.l10n.taskReminderRefreshSuccess,
                );
              }
            } catch (e) {
              if (mounted) {
                AppFeedback.error(
                  context,
                  context.l10n.taskReminderRefreshFailed(e.toString().replaceFirst('Exception: ', '').trim()),
                );
              }
            }
          },
          icon: Icon(Icons.refresh, color: DS.brandPrimary),
          label: Text(
            context.l10n.taskReminderRefreshAll,
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
                    context.l10n.taskReminderInfoTitle,
                    style: TextStyle(
                      color: DS.textPrimary,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                context.l10n.taskReminderInfoBody,
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
    final l10n = I18nService.instance.l10n;
    if (minutes >= 1440) {
      final days = minutes ~/ 1440;
      return l10n.timeDaysAgo(days);
    } else if (minutes >= 60) {
      final hours = minutes ~/ 60;
      return l10n.timeHoursAgo(hours);
    } else {
      return l10n.timeMinutesAgo(minutes);
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
