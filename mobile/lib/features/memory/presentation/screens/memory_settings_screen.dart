import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';

class MemorySettingsScreen extends ConsumerStatefulWidget {
  const MemorySettingsScreen({super.key});

  @override
  ConsumerState<MemorySettingsScreen> createState() =>
      _MemorySettingsScreenState();
}

class _MemorySettingsScreenState extends ConsumerState<MemorySettingsScreen> {
  bool _loading = true;
  bool _saving = false;
  String? _error;

  bool _enabled = true;
  bool _allowPreferences = true;
  bool _allowGoals = true;
  bool _allowEpisodic = true;
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
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    if (!AppFeatureFlags.enableUserMemoryControls) {
      setState(() {
        _loading = false;
        _error = '记忆控制未启用';
      });
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final service = ref.read(memoryApiServiceProvider);
      final settings = await service.getMemorySettings();
      if (!mounted) {
        return;
      }
      setState(() {
        _enabled = settings.enabled;
        _allowPreferences = settings.allowPreferences;
        _allowGoals = settings.allowGoals;
        _allowEpisodic = settings.allowEpisodic;
        _captureLevel = settings.captureLevel;
        _blockedPrefKeys
          ..clear()
          ..addAll(settings.blockedPrefKeys);
        _blockedSources
          ..clear()
          ..addAll(settings.blockedSources);
        _loading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = '加载记忆设置失败: $e';
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
        captureLevel: _captureLevel,
        blockedPrefKeys: _blockedPrefKeys.toList(),
        blockedSources: _blockedSources.toList(),
      );
      final updated = await service.updateMemorySettings(settings);
      if (!mounted) {
        return;
      }
      setState(() {
        _enabled = updated.enabled;
        _allowPreferences = updated.allowPreferences;
        _allowGoals = updated.allowGoals;
        _allowEpisodic = updated.allowEpisodic;
        _captureLevel = updated.captureLevel;
        _blockedPrefKeys
          ..clear()
          ..addAll(updated.blockedPrefKeys);
        _blockedSources
          ..clear()
          ..addAll(updated.blockedSources);
        _saving = false;
      });
      AppFeedback.success(context, '记忆设置已更新');
    } catch (e) {
      if (!mounted) {
        return;
      }
      setState(() {
        _saving = false;
        _error = '保存失败: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: DS.deepSpaceStart,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
            variant: ButtonVariant.ghost,
            size: DS.touchTargetMinSize,
          ),
          title: Text('记忆控制', style: TextStyle(color: DS.brandPrimary)),
          iconTheme: IconThemeData(color: DS.brandPrimary),
          backgroundColor: DS.surfacePrimary.withValues(alpha: 0),
          elevation: 0,
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _buildError(context)
                : _buildContent(context),
      );

  Widget _buildError(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(DS.lg),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _error ?? '记忆控制不可用',
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: DS.md),
              SparkleButton.primary(
                label: '重试',
                onPressed: _loadSettings,
              ),
            ],
          ),
        ),
      );

  Widget _buildContent(BuildContext context) => ContentConstraint(
        child: ListView(
          padding: const EdgeInsets.all(DS.lg),
          children: [
            _buildSectionTitle('总开关'),
            SwitchListTile(
              value: _enabled,
              onChanged: (value) => setState(() => _enabled = value),
              title: const Text('启用长期记忆'),
              subtitle: const Text('关闭后将暂停所有记忆写入'),
            ),
            const SizedBox(height: DS.lg),
            _buildSectionTitle('记忆类型'),
            SwitchListTile(
              value: _allowPreferences,
              onChanged: _enabled
                  ? (value) => setState(() => _allowPreferences = value)
                  : null,
              title: const Text('偏好'),
            ),
            SwitchListTile(
              value: _allowGoals,
              onChanged: _enabled
                  ? (value) => setState(() => _allowGoals = value)
                  : null,
              title: const Text('目标'),
            ),
            SwitchListTile(
              value: _allowEpisodic,
              onChanged: _enabled
                  ? (value) => setState(() => _allowEpisodic = value)
                  : null,
              title: const Text('经历'),
            ),
            const SizedBox(height: DS.lg),
            _buildSectionTitle('捕获强度'),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'low', label: Text('低')),
                ButtonSegment(value: 'medium', label: Text('中')),
                ButtonSegment(value: 'high', label: Text('高')),
              ],
              selected: {_captureLevel},
              onSelectionChanged: _enabled
                  ? (selection) {
                      setState(() => _captureLevel = selection.first);
                    }
                  : null,
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                backgroundColor: WidgetStateProperty.resolveWith<Color>(
                  (states) {
                    if (states.contains(WidgetState.selected)) {
                      return DS.primaryBase;
                    }
                    return DS.brandPrimary10;
                  },
                ),
                foregroundColor: WidgetStateProperty.all(DS.brandPrimary),
              ),
            ),
            const SizedBox(height: DS.lg),
            _buildSectionTitle('屏蔽偏好'),
            Wrap(
              spacing: DS.sm,
              runSpacing: DS.sm,
              children: _prefKeyOptions
                  .map(
                    (key) => FilterChip(
                      label: Text(key),
                      selected: _blockedPrefKeys.contains(key),
                      onSelected: _enabled && _allowPreferences
                          ? (selected) => _togglePrefKey(key, selected)
                          : null,
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.lg),
            _buildSectionTitle('屏蔽来源'),
            Wrap(
              spacing: DS.sm,
              runSpacing: DS.sm,
              children: _sourceOptions
                  .map(
                    (source) => FilterChip(
                      label: Text(source),
                      selected: _blockedSources.contains(source),
                      onSelected: _enabled
                          ? (selected) => _toggleSource(source, selected)
                          : null,
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: DS.xl),
            SparkleButton.primary(
              label: _saving ? '保存中...' : '保存设置',
              onPressed: _saving ? () {} : _saveSettings,
            ),
          ],
        ),
      );

  Widget _buildSectionTitle(String title) => Padding(
        padding: const EdgeInsets.only(bottom: DS.sm),
        child: Text(
          title,
          style: Theme.of(context)
              .textTheme
              .titleMedium
              ?.copyWith(color: DS.brandPrimary),
        ),
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
}
