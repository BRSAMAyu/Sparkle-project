import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
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
      await ref.read(authProvider.notifier).updateProfile({
        'schedule_preferences': newPrefs,
      });
      if (mounted) {
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
        ),
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
