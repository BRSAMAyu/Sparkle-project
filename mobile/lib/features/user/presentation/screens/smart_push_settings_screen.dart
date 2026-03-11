import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logger/logger.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';
import 'package:sparkle/core/services/notification_service.dart';
import 'package:sparkle/features/auth/auth.dart';
import 'package:sparkle/features/user/data/repositories/user_repository.dart';
import 'package:sparkle/features/user/presentation/providers/settings_provider.dart';
import 'package:sparkle/l10n/app_localizations.dart';
import 'package:sparkle/shared/entities/user_model.dart';

class SmartPushSettingsScreen extends ConsumerStatefulWidget {
  const SmartPushSettingsScreen({super.key});

  @override
  ConsumerState<SmartPushSettingsScreen> createState() =>
      _SmartPushSettingsScreenState();
}

class _SmartPushSettingsScreenState
    extends ConsumerState<SmartPushSettingsScreen> {
  final Logger _logger = Logger();

  // Local state
  String _persona = 'coach';
  int _dailyCap = 5;
  List<Map<String, String>> _activeSlots = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Initialize state from current user
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadPreferences();
    });
  }

  void _loadPreferences() {
    final user = ref.read(authProvider).user;
    if (user != null && user.pushPreferences != null) {
      final prefs = user.pushPreferences!;
      setState(() {
        _persona = prefs.personaType;
        _dailyCap = prefs.dailyCap;
        _activeSlots = List.from(prefs.activeSlots ?? []);
      });
    }
  }

  Future<void> _savePreferences() async {
    final l10n = context.l10n;
    setState(() => _isLoading = true);
    try {
      final prefs = PushPreferences(
        personaType: _persona,
        dailyCap: _dailyCap,
        activeSlots: _activeSlots,
      );

      await ref.read(userRepositoryProvider).updatePushPreferences(prefs);

      // Refresh auth state to update all screens
      await ref.read(authProvider.notifier).refreshUser();

      // Also update push preferences provider
      unawaited(
        ref.read(pushPreferencesProvider.notifier).updatePreferences(
              personaType: _persona,
              dailyCap: _dailyCap,
              activeSlots: _activeSlots,
            ),
      );

      if (mounted) {
        AppFeedback.success(context, l10n.smartPushSettingsSaved);
      }
    } catch (e) {
      _logger.e('Failed to save push settings: $e');
      if (mounted) {
        AppFeedback.error(context, l10n.smartPushSaveFailed(e.toString()));
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _selectTime(int index, bool isStart) async {
    final currentStr =
        isStart ? _activeSlots[index]['start'] : _activeSlots[index]['end'];
    final parts = currentStr?.split(':') ?? ['08', '00'];
    final initialTime =
        TimeOfDay(hour: int.parse(parts[0]), minute: int.parse(parts[1]));

    final picked = await showTimePicker(
      context: context,
      initialTime: initialTime,
    );

    if (picked != null) {
      setState(() {
        final formatted =
            '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
        if (isStart) {
          _activeSlots[index]['start'] = formatted;
        } else {
          _activeSlots[index]['end'] = formatted;
        }
      });
    }
  }

  void _addSlot() {
    setState(() {
      _activeSlots.add({'start': '09:00', 'end': '10:00'});
    });
  }

  void _removeSlot(int index) {
    setState(() {
      _activeSlots.removeAt(index);
    });
  }

  @override
  Widget build(BuildContext context) {
    final l10n = context.l10n;
    return SparklePageScaffold(
      role: SparklePageRole.settings,
      appBar: AppBar(
        leading: SparkleIconButton(
          variant: ButtonVariant.ghost,
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: Text(l10n.smartPushSettings),
        actions: [
          if (_isLoading)
            const Center(
              child: Padding(
                padding: EdgeInsets.only(right: DS.spacing16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
            )
          else
            SparkleIconButton(
              variant: ButtonVariant.ghost,
              icon: const Icon(Icons.save),
              onPressed: _savePreferences,
            ),
        ],
      ),
      child: ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.lg),
          children: [
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle(l10n.smartPushPersonaSection),
                  const SizedBox(height: DS.sm),
                  _buildPersonaSelector(l10n),
                  const SizedBox(height: DS.xl),
                  _buildSectionTitle(l10n.smartPushFrequencySection),
                  _buildFrequencySlider(l10n),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing20),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle(l10n.smartPushActiveSlotsSection),
                  Text(
                    l10n.smartPushActiveSlotsHint,
                    style: TextStyle(
                      color: DS.brandPrimaryConst,
                      fontSize: 12,
                    ),
                  ),
                  const SizedBox(height: DS.sm),
                  _buildActiveSlotsList(l10n),
                  const SizedBox(height: DS.sm),
                  SparkleButton(
                    onPressed: _addSlot,
                    icon: const Icon(Icons.add),
                    label: l10n.smartPushAddTimeSlot,
                    expand: true,
                  ),
                  const SizedBox(height: DS.spacing24),
                  const Divider(),
                  const SizedBox(height: DS.spacing16),
                  Center(
                    child: SparkleButton.ghost(
                      onPressed: () {
                        unawaited(
                          ref.read(notificationServiceProvider).showSmartPush(
                            title: l10n.smartPushDebugTitle,
                            body: l10n.smartPushDebugBody,
                            payload: {'taskId': 'debug_123'},
                          ),
                        );
                        AppFeedback.info(
                          context,
                          l10n.smartPushTestNotificationSent,
                        );
                      },
                      icon: const Icon(Icons.bug_report),
                      label: l10n.smartPushTestNotification,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.spacing20),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title) => Text(
        title,
        style: Theme.of(context)
            .textTheme
            .titleMedium
            ?.copyWith(fontWeight: FontWeight.bold),
      );

  Widget _buildPersonaSelector(AppLocalizations l10n) => Row(
        children: [
          Expanded(
            child: _buildPersonaChip(
              value: 'coach',
              label: l10n.smartPushPersonaCoach,
              icon: Icons.sports_kabaddi,
              description: l10n.smartPushPersonaCoachDesc,
            ),
          ),
          const SizedBox(width: DS.md),
          Expanded(
            child: _buildPersonaChip(
              value: 'anime',
              label: l10n.smartPushPersonaAnime,
              icon: Icons.face_retouching_natural,
              description: l10n.smartPushPersonaAnimeDesc,
            ),
          ),
        ],
      );

  Widget _buildPersonaChip({
    required String value,
    required String label,
    required IconData icon,
    required String description,
  }) {
    final isSelected = _persona == value;
    final colorScheme = Theme.of(context).colorScheme;

    return InkWell(
      onTap: () => setState(() => _persona = value),
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(DS.md),
        decoration: BoxDecoration(
          color: isSelected
              ? colorScheme.primaryContainer
              : colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
          border: isSelected
              ? Border.all(color: colorScheme.primary, width: 2)
              : null,
        ),
        child: Column(
          children: [
            Icon(
              icon,
              color: isSelected
                  ? colorScheme.primary
                  : colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: DS.sm),
            Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: DS.xs),
            Text(
              description,
              style:
                  TextStyle(fontSize: 10, color: colorScheme.onSurfaceVariant),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFrequencySlider(AppLocalizations l10n) => Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(l10n.smartPushFrequencyLabel(3)),
              Text(
                l10n.smartPushFrequencyLabel(_dailyCap),
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 18,
                ),
              ),
              Text(l10n.smartPushFrequencyLabel(10)),
            ],
          ),
          Slider(
            value: _dailyCap.toDouble(),
            min: 3,
            max: 10,
            divisions: 7,
            label: l10n.smartPushFrequencyLabel(_dailyCap),
            onChanged: (val) => setState(() => _dailyCap = val.toInt()),
          ),
        ],
      );

  Widget _buildActiveSlotsList(AppLocalizations l10n) {
    if (_activeSlots.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing16),
        child: Center(child: Text(l10n.smartPushNoSlots)),
      );
    }

    return Column(
      children: List.generate(_activeSlots.length, (index) {
        final slot = _activeSlots[index];
        return Card(
          margin: const EdgeInsets.only(bottom: DS.spacing8),
          child: Padding(
            padding: const EdgeInsets.all(DS.sm),
            child: Row(
              children: [
                const Icon(Icons.access_time, size: 20),
                const SizedBox(width: DS.md),
                Expanded(
                  child: Row(
                    children: [
                      _buildTimeButton(slot['start'] ?? '00:00', index, true),
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: DS.spacing8),
                        child: Text('-'),
                      ),
                      _buildTimeButton(slot['end'] ?? '00:00', index, false),
                    ],
                  ),
                ),
                SparkleIconButton(
                  variant: ButtonVariant.ghost,
                  size: DS.spacing32,
                  icon: Icon(Icons.delete, color: DS.errorAccent),
                  onPressed: () => _removeSlot(index),
                ),
              ],
            ),
          ),
        );
      }),
    );
  }

  Widget _buildTimeButton(String time, int index, bool isStart) => InkWell(
        onTap: () => _selectTime(index, isStart),
        borderRadius: BorderRadius.circular(4),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: DS.spacing12,
            vertical: DS.spacing6,
          ),
          decoration: BoxDecoration(
            border: Border.all(color: DS.brandPrimary.shade400),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            time,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
          ),
        ),
      );
}
