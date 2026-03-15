import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sparkle/core/constants/app_constants.dart';
import 'package:sparkle/core/design/design_system.dart';
import 'package:sparkle/core/models/memory_models.dart';
import 'package:sparkle/core/services/memory_api_service.dart';
import 'package:sparkle/features/memory/memory_routes.dart';

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
      MemoryRoutes.popOrGoPanel(context);
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
  Widget build(BuildContext context) => GraphiteScaffold(
        role: SparklePageRole.settings,
        safeArea: false,
        appBar: AppBar(
          leading: SparkleIconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => context.pop(),
            variant: ButtonVariant.ghost,
          ),
          title: Text(
            '记忆控制',
            style: DS.titleLarge.copyWith(
              color: DS.textPrimary,
              fontWeight: FontWeight.w700,
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
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '记忆控制',
                    style: DS.titleLarge.copyWith(
                      color: DS.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: DS.spacing8),
                  Text(
                    '控制系统长期记忆如何学习你的偏好、目标与经历。默认更克制，只有对后续决策真正有价值的信息才应保留。',
                    style: DS.bodyMedium.copyWith(color: DS.textSecondary),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              child: Column(
                children: [
                  _buildToggleRow(
                    title: '启用长期记忆',
                    description: '关闭后会暂停新的记忆写入，但不会删除历史记录。',
                    value: _enabled,
                    onChanged: (value) => setState(() => _enabled = value),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle('记忆类型'),
                  _buildToggleRow(
                    title: '偏好',
                    description: '记录回答风格、学习节奏和常见偏好。',
                    value: _allowPreferences,
                    enabled: _enabled,
                    onChanged: (value) =>
                        setState(() => _allowPreferences = value),
                  ),
                  _buildToggleRow(
                    title: '目标',
                    description: '记录已确认的长期目标和阶段意图。',
                    value: _allowGoals,
                    enabled: _enabled,
                    onChanged: (value) => setState(() => _allowGoals = value),
                  ),
                  _buildToggleRow(
                    title: '经历',
                    description: '记录对后续决策有帮助的关键事件与反馈。',
                    value: _allowEpisodic,
                    enabled: _enabled,
                    isLast: true,
                    onChanged: (value) =>
                        setState(() => _allowEpisodic = value),
                  ),
                ],
              ),
            ),
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle('捕获强度'),
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
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle('屏蔽偏好'),
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
            const SizedBox(height: DS.lg),
            GraphiteCardSurface(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _buildSectionTitle('屏蔽来源'),
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
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: DS.textPrimary,
                fontWeight: FontWeight.w700,
              ),
        ),
      );

  Widget _buildToggleRow({
    required String title,
    required String description,
    required bool value,
    required ValueChanged<bool> onChanged,
    bool enabled = true,
    bool isLast = false,
  }) => Container(
      padding: const EdgeInsets.symmetric(vertical: DS.spacing8),
      decoration: BoxDecoration(
        border:
            isLast ? null : Border(bottom: BorderSide(color: DS.borderSubtle)),
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
                    fontWeight: FontWeight.w600,
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
        color:
            selected ? DS.primaryBase.withValues(alpha: 0.28) : DS.borderSubtle,
      ),
      labelStyle: DS.bodySmall.copyWith(
        color: selected ? DS.primaryBase : DS.textSecondary,
        fontWeight: FontWeight.w600,
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
        color:
            selected ? DS.primaryBase.withValues(alpha: 0.22) : DS.borderSubtle,
      ),
      labelStyle: DS.bodySmall.copyWith(
        color: enabled
            ? (selected ? DS.primaryBase : DS.textSecondary)
            : DS.textDisabled,
        fontWeight: FontWeight.w600,
      ),
      checkmarkColor: DS.primaryBase,
    );
}
