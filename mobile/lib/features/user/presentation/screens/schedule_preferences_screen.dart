import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/sensory_feedback_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/calendar/data/services/smart_schedule_service.dart';
import 'package:sparkle/features/user/user_routes.dart';

class SchedulePreferencesScreen extends ConsumerStatefulWidget {
  const SchedulePreferencesScreen({super.key});

  @override
  ConsumerState<SchedulePreferencesScreen> createState() =>
      _SchedulePreferencesScreenState();
}

class _SchedulePreferencesScreenState
    extends ConsumerState<SchedulePreferencesScreen> {
  final _commuteStartController = TextEditingController();
  final _commuteEndController = TextEditingController();
  final _lunchStartController = TextEditingController();
  final _lunchEndController = TextEditingController();
  FocusPeriod _focusPeriod = FocusPeriod.morning;
  int _preferredTaskDuration = 45;
  int _preferredBreakDuration = 15;

  @override
  void initState() {
    super.initState();
    // Initialize controllers from current user data
    final user = ref.read(currentUserProvider);
    if (user != null && user.schedulePreferences != null) {
      final prefs = user.schedulePreferences!; // 使用!断言，因为已经检查过不为null
      final commute = prefs['commute'];
      if (commute is List && commute.length == 2) {
        _commuteStartController.text = commute[0] as String;
        _commuteEndController.text = commute[1] as String;
      }
      final lunch = prefs['lunch'];
      if (lunch is List && lunch.length == 2) {
        _lunchStartController.text = lunch[0] as String;
        _lunchEndController.text = lunch[1] as String;
      }
      // Load focus period preference
      final focusPeriodStr = prefs['focus_period'] as String?;
      if (focusPeriodStr != null) {
        _focusPeriod = _parseFocusPeriod(focusPeriodStr);
      }
      // Load task duration preference
      _preferredTaskDuration = prefs['preferred_task_duration'] as int? ?? 45;
      _preferredBreakDuration = prefs['preferred_break_duration'] as int? ?? 15;
    }
  }

  FocusPeriod _parseFocusPeriod(String value) {
    switch (value) {
      case 'morning':
        return FocusPeriod.morning;
      case 'afternoon':
        return FocusPeriod.afternoon;
      case 'evening':
        return FocusPeriod.evening;
      default:
        return FocusPeriod.morning;
    }
  }

  @override
  void dispose() {
    _commuteStartController.dispose();
    _commuteEndController.dispose();
    _lunchStartController.dispose();
    _lunchEndController.dispose();
    super.dispose();
  }

  Future<void> _selectTime(
    BuildContext context,
    TextEditingController controller,
  ) async {
    final picked = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );
    if (picked != null) {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.selection));
      // Format as HH:mm
      final hour = picked.hour.toString().padLeft(2, '0');
      final minute = picked.minute.toString().padLeft(2, '0');
      controller.text = '$hour:$minute';
    }
  }

  Future<void> _save() async {
    final commuteStart = _commuteStartController.text;
    final commuteEnd = _commuteEndController.text;
    final lunchStart = _lunchStartController.text;
    final lunchEnd = _lunchEndController.text;

    final newPrefs = <String, dynamic>{};

    if (commuteStart.isNotEmpty && commuteEnd.isNotEmpty) {
      newPrefs['commute'] = [commuteStart, commuteEnd];
    }
    if (lunchStart.isNotEmpty && lunchEnd.isNotEmpty) {
      newPrefs['lunch'] = [lunchStart, lunchEnd];
    }

    // Add focus period preference
    newPrefs['focus_period'] = _focusPeriod.name;

    // Add duration preferences
    newPrefs['preferred_task_duration'] = _preferredTaskDuration;
    newPrefs['preferred_break_duration'] = _preferredBreakDuration;

    try {
      unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.confirm));
      await ref.read(authProvider.notifier).updateProfile({
        'schedule_preferences': newPrefs,
      });
      if (mounted) {
        unawaited(SensoryFeedbackService.emit(SensoryFeedbackEvent.success));
        AppFeedback.success(context, context.l10n.schedulePreferencesSaved);
        UserRoutes.popOrGoProfile(context);
      }
    } catch (e) {
      if (mounted) {
        AppFeedback.error(
          context,
          context.l10n.schedulePreferencesSaveFailed(e.toString()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => SparklePageScaffold(
        role: SparklePageRole.settings,
        appBar: AppBar(
          leading: SparkleIconButton(
            variant: ButtonVariant.ghost,
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
          ),
          title: Text(context.l10n.schedulePreferences),
          actions: [
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              onPressed: _save,
              icon: const Icon(Icons.save),
            ),
          ],
        ),
        child: ContentConstraint(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(DS.lg),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Info card explaining the feature
                SparkleStaggerItem(index: 0, child: _buildInfoCard(context)),
                const SizedBox(height: DS.spacing20),
                SparkleStaggerItem(
                  index: 1,
                  child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.l10n.schedulePreferencesHint,
                        style: TextStyle(color: DS.brandPrimary),
                      ),
                      const SizedBox(height: 20),
                      _buildTimeSlot(
                        context.l10n.scheduleCommuteTime,
                        _commuteStartController,
                        _commuteEndController,
                      ),
                      const SizedBox(height: 20),
                      _buildTimeSlot(
                        context.l10n.scheduleLunchBreak,
                        _lunchStartController,
                        _lunchEndController,
                      ),
                    ],
                  ),
                ),
                ),
                const SizedBox(height: DS.spacing20),
                // Focus period preference
                SparkleStaggerItem(
                  index: 2,
                  child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.bolt_rounded,
                            color: DS.brandPrimary,
                            size: 20,
                          ),
                          const SizedBox(width: DS.spacing10),
                          Text(
                            '专注时段偏好',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: DS.brandPrimary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        '选择您精力最充沛的时段，系统会优先在这些时间安排高难度任务',
                        style: TextStyle(
                          fontSize: 13,
                          color: DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing16),
                      _buildFocusPeriodSelector(),
                    ],
                  ),
                ),
                ),
                const SizedBox(height: DS.spacing20),
                // Task duration preference
                SparkleStaggerItem(
                  index: 3,
                  child: GraphiteCardSurface(
                  surfaceRole: SparkleSurfaceRole.card,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Icon(
                            Icons.timer_outlined,
                            color: DS.brandPrimary,
                            size: 20,
                          ),
                          const SizedBox(width: DS.spacing10),
                          Text(
                            '任务时长偏好',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: DS.brandPrimary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: DS.spacing8),
                      Text(
                        '设置您偏好的单次专注时长和休息间隔',
                        style: TextStyle(
                          fontSize: 13,
                          color: DS.textSecondary,
                        ),
                      ),
                      const SizedBox(height: DS.spacing16),
                      _buildDurationSlider(
                        label: '专注时长',
                        value: _preferredTaskDuration,
                        min: 15,
                        max: 120,
                        unit: '分钟',
                        onChanged: (value) {
                          setState(() {
                            _preferredTaskDuration = value.round();
                          });
                        },
                      ),
                      const SizedBox(height: DS.spacing16),
                      _buildDurationSlider(
                        label: '休息间隔',
                        value: _preferredBreakDuration,
                        min: 5,
                        max: 30,
                        unit: '分钟',
                        onChanged: (value) {
                          setState(() {
                            _preferredBreakDuration = value.round();
                          });
                        },
                      ),
                    ],
                  ),
                ),
                ),
                const SizedBox(height: DS.spacing20),
              ],
            ),
          ),
        ),
      );

  Widget _buildInfoCard(BuildContext context) => Container(
        padding: const EdgeInsets.all(DS.lg),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              DS.brandPrimary.withValues(alpha: 0.1),
              DS.brandPrimary.withValues(alpha: 0.05),
            ],
          ),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: DS.brandPrimary.withValues(alpha: 0.2),
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(DS.spacing10),
              decoration: BoxDecoration(
                color: DS.brandPrimary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                Icons.calendar_today_rounded,
                color: DS.brandPrimary,
                size: 24,
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '日历智能排程',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: DS.brandPrimary,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    '设置偏好后，日历将为您智能推荐最佳任务时间',
                    style: TextStyle(
                      fontSize: 12,
                      color: DS.brandPrimary.withValues(alpha: 0.8),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _buildFocusPeriodSelector() => Row(
        children: FocusPeriod.values.map((period) {
          final isSelected = _focusPeriod == period;
          return Expanded(
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _focusPeriod = period;
                });
              },
              child: Container(
                margin: const EdgeInsets.symmetric(horizontal: DS.spacing4),
                padding: const EdgeInsets.symmetric(
                  vertical: DS.spacing12,
                ),
                decoration: BoxDecoration(
                  color: isSelected
                      ? DS.brandPrimary.withValues(alpha: 0.15)
                      : DS.surfaceOverlay,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isSelected
                        ? DS.brandPrimary.withValues(alpha: 0.5)
                        : DS.borderSubtle,
                  ),
                ),
                child: Column(
                  children: [
                    Icon(
                      _getFocusPeriodIcon(period),
                      color: isSelected ? DS.brandPrimary : DS.textSecondary,
                      size: 24,
                    ),
                    const SizedBox(height: DS.spacing6),
                    Text(
                      _getFocusPeriodLabel(period),
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
                        color: isSelected ? DS.brandPrimary : DS.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        }).toList(),
      );

  IconData _getFocusPeriodIcon(FocusPeriod period) {
    switch (period) {
      case FocusPeriod.morning:
        return Icons.wb_sunny_rounded;
      case FocusPeriod.afternoon:
        return Icons.wb_twilight_rounded;
      case FocusPeriod.evening:
        return Icons.nightlight_round_rounded;
    }
  }

  String _getFocusPeriodLabel(FocusPeriod period) {
    switch (period) {
      case FocusPeriod.morning:
        return '上午';
      case FocusPeriod.afternoon:
        return '下午';
      case FocusPeriod.evening:
        return '晚上';
    }
  }

  Widget _buildDurationSlider({
    required String label,
    required int value,
    required int min,
    required int max,
    required String unit,
    required ValueChanged<double> onChanged,
  }) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                label,
                style: TextStyle(
                  fontSize: 14,
                  color: DS.brandPrimary,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: DS.spacing10,
                  vertical: DS.spacing4,
                ),
                decoration: BoxDecoration(
                  color: DS.brandPrimary.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '$value$unit',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: DS.brandPrimary,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: DS.spacing8),
          SliderTheme(
            data: SliderThemeData(
              activeTrackColor: DS.brandPrimary,
              inactiveTrackColor: DS.brandPrimary.withValues(alpha: 0.2),
              thumbColor: DS.brandPrimary,
              overlayColor: DS.brandPrimary.withValues(alpha: 0.1),
              trackHeight: 4,
            ),
            child: Slider(
              value: value.toDouble(),
              min: min.toDouble(),
              max: max.toDouble(),
              divisions: (max - min) ~/ 5,
              onChanged: onChanged,
            ),
          ),
        ],
      );

  Widget _buildTimeSlot(
    String label,
    TextEditingController startController,
    TextEditingController endController,
  ) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: DS.sm),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: startController,
                  decoration: InputDecoration(
                    labelText: context.l10n.scheduleStartTime,
                    border: const OutlineInputBorder(),
                    suffixIcon: const Icon(Icons.access_time),
                  ),
                  readOnly: true,
                  onTap: () => _selectTime(context, startController),
                ),
              ),
              const SizedBox(width: DS.lg),
              Expanded(
                child: TextFormField(
                  controller: endController,
                  decoration: InputDecoration(
                    labelText: context.l10n.scheduleEndTime,
                    border: const OutlineInputBorder(),
                    suffixIcon: const Icon(Icons.access_time),
                  ),
                  readOnly: true,
                  onTap: () => _selectTime(context, endController),
                ),
              ),
            ],
          ),
        ],
      );
}
