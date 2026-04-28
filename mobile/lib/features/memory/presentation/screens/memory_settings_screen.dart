import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/core/extensions/context_l10n.dart';

class MemorySettingsScreen extends ConsumerStatefulWidget {
  const MemorySettingsScreen({super.key});

  @override
  ConsumerState<MemorySettingsScreen> createState() =>
      _MemorySettingsScreenState();
}

class _MemorySettingsScreenState extends ConsumerState<MemorySettingsScreen> {
  static const String _socialSourcePrefix = 'social:';
  static const List<String> _socialSubjectTypes = [
    'self',
    'person_mention',
    'relationship',
    'commitment',
  ];

  bool _loading = true;
  bool _saving = false;
  String? _error;

  bool _enabled = true;
  bool _allowPreferences = true;
  bool _allowGoals = true;
  bool _allowEpisodic = true;
  bool _allowInferredEpisodic = true;
  bool _pushEnabled = false;
  bool _allowCommitmentFollowUp = false;
  bool _allowEngagementRecovery = false;
  String _pushQuietStart = '22:00';
  String _pushQuietEnd = '08:00';
  String _pushTimezone = 'Asia/Shanghai';
  final Map<String, bool> _socialTypeEnabled = {
    'self': true,
    'person_mention': true,
    'relationship': true,
    'commitment': true,
  };
  String _captureLevel = 'medium';
  final Set<String> _blockedPrefKeys = {};
  final Set<String> _blockedSources = {};

  static const List<String> _prefKeyOptions = [
    'depth_preference',
    'curiosity_preference',
    'learning_style',
    'study_time_preference',
    'schedule_preferences',
    'weather_preferences',
    'language',
    'timezone',
    'notification_frequency',
    'response_style',
    'feedback_tone',
    'task_priority_bias',
    'coaching_style',
    'focus_mode',
    'sprint_mode',
  ];

  static const List<String> _sourceOptions = [
    'chat',
    'task',
    'error',
  ];

  @override
  void initState() {
    super.initState();
    unawaited(_loadSettings());
  }

  void _goBack() {
    final navigator = Navigator.maybeOf(context);
    if (navigator?.canPop() ?? false) {
      navigator!.pop();
    } else {
      try {
        context.go('/profile');
      } catch (_) {
        // The screen can be rendered in isolated widget tests without GoRouter.
      }
    }
  }

  Future<void> _loadSettings() async {
    if (!AppFeatureFlags.enableUserMemoryControls) {
      setState(() {
        _loading = false;
        _error = context.l10n.memNotEnabled;
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = ref.read(memoryApiServiceProvider);
      MemorySettingsModel settings;
      PushOptInSettingsModel pushSettings;
      try {
        settings = await service.getMemorySettings();
      } catch (_) {
        settings = MemorySettingsModel(
          enabled: true,
          allowPreferences: true,
          allowGoals: true,
          allowEpisodic: true,
          allowInferredEpisodic: true,
          captureLevel: 'medium',
          blockedPrefKeys: [],
          blockedSources: [],
        );
      }
      try {
        pushSettings = await service.getPushSettings();
      } catch (_) {
        pushSettings = PushOptInSettingsModel(
          enabled: false,
          allowCommitmentFollowUp: false,
          allowEngagementRecovery: false,
          quietHoursStart: '22:00',
          quietHoursEnd: '08:00',
          timezone: 'Asia/Shanghai',
        );
      }
      if (!mounted) {
        return;
      }
      setState(() {
        _enabled = settings.enabled;
        _allowPreferences = settings.allowPreferences;
        _allowGoals = settings.allowGoals;
        _allowEpisodic = settings.allowEpisodic;
        _allowInferredEpisodic = settings.allowInferredEpisodic;
        _captureLevel = settings.captureLevel;
        _blockedPrefKeys
          ..clear()
          ..addAll(settings.blockedPrefKeys);
        _blockedSources
          ..clear()
          ..addAll(settings.blockedSources);
        _pushEnabled = pushSettings.enabled;
        _allowCommitmentFollowUp = pushSettings.allowCommitmentFollowUp;
        _allowEngagementRecovery = pushSettings.allowEngagementRecovery;
        _pushQuietStart = pushSettings.quietHoursStart;
        _pushQuietEnd = pushSettings.quietHoursEnd;
        _pushTimezone = pushSettings.timezone;
        _hydrateSocialTypeFlags(settings.blockedSources);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = context.l10n.memLoadSettingsFailed(e.toString());
        _loading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final service = ref.read(memoryApiServiceProvider);
      final settings = MemorySettingsModel(
        enabled: _enabled,
        allowPreferences: _allowPreferences,
        allowGoals: _allowGoals,
        allowEpisodic: _allowEpisodic,
        allowInferredEpisodic: _allowInferredEpisodic,
        captureLevel: _captureLevel,
        blockedPrefKeys: _blockedPrefKeys.toList(),
        blockedSources: _resolvedBlockedSources(),
      );
      final pushSettings = PushOptInSettingsModel(
        enabled: _pushEnabled,
        allowCommitmentFollowUp: _allowCommitmentFollowUp,
        allowEngagementRecovery: _allowEngagementRecovery,
        quietHoursStart: _pushQuietStart,
        quietHoursEnd: _pushQuietEnd,
        timezone: _pushTimezone,
      );
      final updated = await service.updateMemorySettings(settings);
      final updatedPush = await service.updatePushSettings(pushSettings);
      if (!mounted) {
        return;
      }
      setState(() {
        _enabled = updated.enabled;
        _allowPreferences = updated.allowPreferences;
        _allowGoals = updated.allowGoals;
        _allowEpisodic = updated.allowEpisodic;
        _allowInferredEpisodic = updated.allowInferredEpisodic;
        _captureLevel = updated.captureLevel;
        _blockedPrefKeys
          ..clear()
          ..addAll(updated.blockedPrefKeys);
        _blockedSources
          ..clear()
          ..addAll(updated.blockedSources);
        _pushEnabled = updatedPush.enabled;
        _allowCommitmentFollowUp = updatedPush.allowCommitmentFollowUp;
        _allowEngagementRecovery = updatedPush.allowEngagementRecovery;
        _pushQuietStart = updatedPush.quietHoursStart;
        _pushQuietEnd = updatedPush.quietHoursEnd;
        _pushTimezone = updatedPush.timezone;
        _hydrateSocialTypeFlags(updated.blockedSources);
        _saving = false;
      });
      AppFeedback.success(context, '记忆设置已更新');
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _saving = false;
        _error = context.l10n.memSaveFailed(e.toString());
      });
    }
  }

  @override
  Widget build(BuildContext context) => GraphiteScaffold(
        role: SparklePageRole.settings,
        safeArea: false,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _goBack,
            variant: ButtonVariant.ghost,
            semanticLabel: context.l10n.memBack,
          ),
          title: Text(
            '记忆控制',
            style: DS.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: DS.fontWeightBold,
            ),
          ),
          iconTheme: IconThemeData(color: DS.textPrimary),
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          elevation: 0,
        ),
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _buildError(context)
                : _buildContent(context),
      );

  Widget _buildError(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: GraphiteCardSurface(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.memory_rounded,
                  size: 28,
                  color: DS.textSecondary,
                ),
                const SizedBox(height: DS.spacing12),
                Text(
                  _error ?? context.l10n.memUnavailable,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: DS.md),
                SparkleButton.primary(
                  label: context.l10n.memRetry,
                  onPressed: _loadSettings,
                ),
              ],
            ),
          ),
        ),
      );

  Widget _buildContent(BuildContext context) => ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.lg),
          children: [
            SparkleStaggerItem(
              index: 0,
              child: GraphiteCardSurface(
                surfaceRole: SparkleSurfaceRole.panel,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: [
                        _buildStatusChip(
                          icon: Icons.auto_awesome_outlined,
                          label: _enabled ? context.l10n.memEnabled : context.l10n.memPaused,
                          color: _enabled ? DS.primaryBase : DS.textSecondary,
                        ),
                        _buildStatusChip(
                          icon: Icons.privacy_tip_outlined,
                          label: context.l10n.memPrefControlled,
                          color: const Color(0xFF71917D),
                        ),
                      ],
                    ),
                    const SizedBox(height: DS.spacing12),
                    Text(
                      '控制系统长期记忆如何学习你的偏好、目标与经历。默认更克制，只有对后续决策真正有价值的信息才应保留。',
                      style: DS.bodyMedium.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 1,
              child: GraphiteCardSurface(
                child: Column(
                  children: [
                    _buildToggleRow(
                      title: context.l10n.memEnableLongTerm,
                      description: context.l10n.memDisableDesc,
                      value: _enabled,
                      onChanged: (value) => setState(() => _enabled = value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 2,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '社交语义子开关',
                      style: DS.titleMedium.copyWith(
                        color: DS.textPrimary,
                        fontWeight: DS.fontWeightBold,
                      ),
                    ),
                    const SizedBox(height: DS.sm),
                    Text(
                      'Stage 17 只做记忆声明与前门读取。关闭某一类后，该类社交语义会在前门中被隐藏。',
                      style: DS.bodySmall.copyWith(
                        color: DS.textSecondary,
                        height: 1.45,
                      ),
                    ),
                    const SizedBox(height: DS.md),
                    _buildToggleRow(
                      title: context.l10n.memSelfMemory,
                      description: 'self',
                      value: _socialTypeEnabled['self'] ?? true,
                      onChanged: (value) =>
                          setState(() => _socialTypeEnabled['self'] = value),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memPeopleMention,
                      description: 'person_mention',
                      value: _socialTypeEnabled['person_mention'] ?? true,
                      onChanged: (value) => setState(
                        () => _socialTypeEnabled['person_mention'] = value,
                      ),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memRelationshipDynamics,
                      description: 'relationship',
                      value: _socialTypeEnabled['relationship'] ?? true,
                      onChanged: (value) => setState(
                        () => _socialTypeEnabled['relationship'] = value,
                      ),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memCommitments,
                      description: 'commitment',
                      value: _socialTypeEnabled['commitment'] ?? true,
                      onChanged: (value) => setState(
                        () => _socialTypeEnabled['commitment'] = value,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 3,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionTitle(
                      '主动提醒',
                      subtitle: context.l10n.memCommitmentStageNote,
                    ),
                    _buildToggleRow(
                      title: context.l10n.memEnableProactive,
                      description: context.l10n.memProactiveMaster,
                      value: _pushEnabled,
                      onChanged: (value) =>
                          setState(() => _pushEnabled = value),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memCommitmentFollowup,
                      description: context.l10n.memCommitmentFollowupDesc,
                      value: _allowCommitmentFollowUp,
                      enabled: _pushEnabled,
                      onChanged: (value) =>
                          setState(() => _allowCommitmentFollowUp = value),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memActivityRecovery,
                      description: context.l10n.memActivityRecoveryDesc,
                      value: _allowEngagementRecovery,
                      enabled: _pushEnabled,
                      isLast: true,
                      onChanged: (value) =>
                          setState(() => _allowEngagementRecovery = value),
                    ),
                    const SizedBox(height: DS.md),
                    _buildSectionTitle(
                      '静默时段',
                      subtitle: context.l10n.memQuietHoursNote,
                    ),
                    _buildChoiceGroup(
                      title: context.l10n.memStartTime,
                      values: const ['22:00', '22:30', '23:00'],
                      selected: _pushQuietStart,
                      enabled: _pushEnabled,
                      onSelected: (value) =>
                          setState(() => _pushQuietStart = value),
                    ),
                    const SizedBox(height: DS.spacing12),
                    _buildChoiceGroup(
                      title: context.l10n.memEndTime,
                      values: const ['07:00', '07:30', '08:00'],
                      selected: _pushQuietEnd,
                      enabled: _pushEnabled,
                      onSelected: (value) =>
                          setState(() => _pushQuietEnd = value),
                    ),
                    const SizedBox(height: DS.md),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '当前时区：$_pushTimezone',
                            style: DS.bodySmall.copyWith(
                              color: DS.textSecondary,
                            ),
                          ),
                        ),
                        SparkleButton.ghost(
                          label: context.l10n.memViewInbox,
                          onPressed: () => context.push('/notification-center'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 4,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionTitle(
                      '记忆类型',
                      subtitle: context.l10n.memDecideWhat,
                    ),
                    _buildToggleRow(
                      title: context.l10n.memPreference,
                      description: context.l10n.memPreferenceDesc,
                      value: _allowPreferences,
                      enabled: _enabled,
                      onChanged: (value) =>
                          setState(() => _allowPreferences = value),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memGoals,
                      description: context.l10n.memGoalsDesc,
                      value: _allowGoals,
                      enabled: _enabled,
                      onChanged: (value) => setState(() => _allowGoals = value),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memExperience,
                      description: context.l10n.memExperienceDesc,
                      value: _allowEpisodic,
                      enabled: _enabled,
                      onChanged: (value) =>
                          setState(() => _allowEpisodic = value),
                    ),
                    _buildToggleRow(
                      title: context.l10n.memAiAutoMemory,
                      description: context.l10n.memAiAutoMemoryDesc,
                      value: _allowInferredEpisodic,
                      enabled: _enabled && _allowEpisodic,
                      isLast: true,
                      onChanged: (value) =>
                          setState(() => _allowInferredEpisodic = value),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 5,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionTitle(
                      '捕获强度',
                      subtitle: context.l10n.memSensitivityNote,
                    ),
                    Wrap(
                      spacing: DS.spacing8,
                      runSpacing: DS.spacing8,
                      children: const [
                        ('low', '低'),
                        ('medium', '中'),
                        ('high', '高'),
                      ].map((entry) {
                        final value = entry.$1;
                        final label = entry.$2;
                        return _MemoryChoiceChip(
                          value: value,
                          label: label,
                          selected: _captureLevel == value,
                          enabled: _enabled,
                          onSelected: () {
                            setState(() {
                              _captureLevel = value;
                            });
                          },
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 6,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionTitle(
                      '屏蔽偏好',
                      subtitle: context.l10n.memExcludeNote,
                    ),
                    Wrap(
                      spacing: DS.sm,
                      runSpacing: DS.sm,
                      children: _prefKeyOptions
                          .map(
                            (key) => _MemoryFilterChip(
                              label: key,
                              selected: _blockedPrefKeys.contains(key),
                              enabled: _enabled && _allowPreferences,
                              onSelected: (selected) =>
                                  _togglePrefKey(key, selected),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.lg),
            SparkleStaggerItem(
              index: 7,
              child: GraphiteCardSurface(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionTitle(
                      '屏蔽来源',
                      subtitle: context.l10n.memSourceLimit,
                    ),
                    Wrap(
                      spacing: DS.sm,
                      runSpacing: DS.sm,
                      children: _sourceOptions
                          .map(
                            (source) => _MemoryFilterChip(
                              label: source,
                              selected: _blockedSources.contains(source),
                              enabled: _enabled,
                              onSelected: (selected) =>
                                  _toggleSource(source, selected),
                            ),
                          )
                          .toList(),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: DS.xl),
            SparkleStaggerItem(
              index: 8,
              child: SparkleButton.primary(
                label: _saving ? context.l10n.memSaving : context.l10n.memSaveSettings,
                onPressed: _saving ? () {} : _saveSettings,
              ),
            ),
          ],
        ),
      );

  Widget _buildStatusChip({
    required IconData icon,
    required String label,
    required Color color,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(
          horizontal: DS.spacing10,
          vertical: DS.spacing6,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withValues(alpha: 0.16)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: DS.spacing6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: color,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
          ],
        ),
      );

  Widget _buildSectionTitle(String title, {String? subtitle}) => Padding(
        padding: const EdgeInsets.only(bottom: DS.sm),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: DS.textPrimary,
                    fontWeight: DS.fontWeightBold,
                  ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: DS.spacing4),
              Text(
                subtitle,
                style: DS.bodySmall.copyWith(
                  color: DS.textSecondary,
                  height: 1.4,
                ),
              ),
            ],
          ],
        ),
      );

  Widget _buildToggleRow({
    required String title,
    required String description,
    required bool value,
    required ValueChanged<bool> onChanged,
    bool enabled = true,
    bool isLast = false,
  }) =>
      Container(
        padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
        decoration: BoxDecoration(
          border: isLast
              ? null
              : Border(bottom: BorderSide(color: DS.borderSubtle)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: DS.bodyLarge.copyWith(
                      color: enabled ? DS.textPrimary : DS.textDisabled,
                      fontWeight: DS.fontWeightSemibold,
                    ),
                  ),
                  const SizedBox(height: DS.spacing4),
                  Text(
                    description,
                    style: DS.bodySmall.copyWith(
                      color: enabled ? DS.textSecondary : DS.textDisabled,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: DS.spacing12),
            Switch.adaptive(
              value: value,
              onChanged: enabled ? onChanged : null,
              activeThumbColor: DS.primaryBase,
              activeTrackColor: DS.primaryBase.withValues(alpha: 0.28),
            ),
          ],
        ),
      );

  Widget _buildChoiceGroup({
    required String title,
    required List<String> values,
    required String selected,
    required bool enabled,
    required ValueChanged<String> onSelected,
  }) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: DS.bodyMedium.copyWith(
              color: enabled ? DS.textPrimary : DS.textDisabled,
              fontWeight: DS.fontWeightSemibold,
            ),
          ),
          const SizedBox(height: DS.spacing8),
          Wrap(
            spacing: DS.spacing8,
            runSpacing: DS.spacing8,
            children: values
                .map(
                  (value) => _MemoryChoiceChip(
                    value: value,
                    label: value,
                    selected: selected == value,
                    enabled: enabled,
                    onSelected: () => onSelected(value),
                  ),
                )
                .toList(),
          ),
        ],
      );

  void _togglePrefKey(String key, bool selected) {
    setState(() {
      if (selected) {
        _blockedPrefKeys.add(key);
      } else {
        _blockedPrefKeys.remove(key);
      }
    });
  }

  void _toggleSource(String source, bool selected) {
    setState(() {
      if (selected) {
        _blockedSources.add(source);
      } else {
        _blockedSources.remove(source);
      }
    });
  }

  void _hydrateSocialTypeFlags(List<String> blockedSources) {
    final blocked = Set<String>.from(blockedSources);
    for (final key in _socialSubjectTypes) {
      _socialTypeEnabled[key] = !blocked.contains('$_socialSourcePrefix$key');
    }
  }

  List<String> _resolvedBlockedSources() {
    final blocked = _blockedSources
        .where((value) => !value.startsWith(_socialSourcePrefix))
        .toSet();
    for (final entry in _socialTypeEnabled.entries) {
      if (!entry.value) {
        blocked.add('$_socialSourcePrefix${entry.key}');
      }
    }
    return blocked.toList()..sort();
  }
}

class _MemoryChoiceChip extends StatelessWidget {
  const _MemoryChoiceChip({
    required this.value,
    required this.label,
    required this.selected,
    required this.enabled,
    required this.onSelected,
  });

  final String value;
  final String label;
  final bool selected;
  final bool enabled;
  final VoidCallback onSelected;

  @override
  Widget build(BuildContext context) => ChoiceChip(
        label: Text(label),
        selected: selected,
        onSelected: enabled ? (_) => onSelected() : null,
        selectedColor: DS.primaryBase.withValues(alpha: 0.14),
        backgroundColor: DS.surfaceSecondary,
        side: BorderSide(
          color: selected
              ? DS.primaryBase.withValues(alpha: 0.28)
              : DS.borderSubtle,
        ),
        labelStyle: DS.bodySmall.copyWith(
          color: selected ? DS.primaryBase : DS.textSecondary,
          fontWeight: DS.fontWeightSemibold,
        ),
      );
}

class _MemoryFilterChip extends StatelessWidget {
  const _MemoryFilterChip({
    required this.label,
    required this.selected,
    required this.enabled,
    required this.onSelected,
  });

  final String label;
  final bool selected;
  final bool enabled;
  final ValueChanged<bool> onSelected;

  @override
  Widget build(BuildContext context) => FilterChip(
        label: Text(label),
        selected: selected,
        onSelected: enabled ? onSelected : null,
        selectedColor: DS.primaryBase.withValues(alpha: 0.12),
        backgroundColor: DS.surfaceSecondary,
        disabledColor: DS.surfaceSecondary.withValues(alpha: 0.8),
        side: BorderSide(
          color: selected
              ? DS.primaryBase.withValues(alpha: 0.22)
              : DS.borderSubtle,
        ),
        labelStyle: DS.bodySmall.copyWith(
          color: enabled
              ? (selected ? DS.primaryBase : DS.textSecondary)
              : DS.textDisabled,
          fontWeight: DS.fontWeightSemibold,
        ),
        checkmarkColor: DS.primaryBase,
      );
}
