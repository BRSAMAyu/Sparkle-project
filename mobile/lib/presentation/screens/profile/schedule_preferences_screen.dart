import 'package:flutter/material.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/presentation/providers/auth_provider.dart';

class SchedulePreferencesScreen extends ConsumerStatefulWidget {
  const SchedulePreferencesScreen({super.key});

  @override
  ConsumerState<SchedulePreferencesScreen> createState() => _SchedulePreferencesScreenState();
}

class _SchedulePreferencesScreenState extends ConsumerState<SchedulePreferencesScreen> {
  final _commuteStartController = TextEditingController();
  final _commuteEndController = TextEditingController();
  final _lunchStartController = TextEditingController();
  final _lunchEndController = TextEditingController();

  @override
  void initState() {
    super.initState();
    // Initialize controllers from current user data
    final user = ref.read(currentUserProvider);
    if (user != null && user.schedulePreferences != null) {
      final prefs = user.schedulePreferences!;
      if (prefs['commute'] != null) {
        final commute = prefs['commute'] as List;
        if (commute.length == 2) {
          _commuteStartController.text = commute[0];
          _commuteEndController.text = commute[1];
        }
      }
      if (prefs['lunch'] != null) {
        final lunch = prefs['lunch'] as List;
        if (lunch.length == 2) {
          _lunchStartController.text = lunch[0];
          _lunchEndController.text = lunch[1];
        }
      }
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

  Future<void> _selectTime(BuildContext context, TextEditingController controller) async {
    final TimeOfDay? picked = await showTimePicker(
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

    final Map<String, dynamic> newPrefs = {};

    if (commuteStart.isNotEmpty && commuteEnd.isNotEmpty) {
      newPrefs['commute'] = [commuteStart, commuteEnd];
    }
    if (lunchStart.isNotEmpty && lunchEnd.isNotEmpty) {
      newPrefs['lunch'] = [lunchStart, lunchEnd];
    }

    try {
      await ref.read(authProvider.notifier).updateProfile({
        'schedule_preferences': newPrefs,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Preferences saved')),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving preferences: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Schedule Preferences'),
        actions: [
          IconButton(
            onPressed: _save,
            icon: const Icon(Icons.save),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Set your fragmented time slots to receive proactive task suggestions.',
              style: TextStyle(color: DS.brandPrimary),
            ),
            const SizedBox(height: 20),
            _buildTimeSlot(
              'Commute Time',
              _commuteStartController,
              _commuteEndController,
            ),
            const SizedBox(height: 20),
            _buildTimeSlot(
              'Lunch Break',
              _lunchStartController,
              _lunchEndController,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeSlot(
    String label,
    TextEditingController startController,
    TextEditingController endController,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: DS.sm),
        Row(
          children: [
            Expanded(
              child: TextFormField(
                controller: startController,
                decoration: const InputDecoration(
                  labelText: 'Start Time',
                  border: OutlineInputBorder(),
                  suffixIcon: Icon(Icons.access_time),
                ),
                readOnly: true,
                onTap: () => _selectTime(context, startController),
              ),
            ),
            const SizedBox(width: DS.lg),
            Expanded(
              child: TextFormField(
                controller: endController,
                decoration: const InputDecoration(
                  labelText: 'End Time',
                  border: OutlineInputBorder(),
                  suffixIcon: Icon(Icons.access_time),
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
}
