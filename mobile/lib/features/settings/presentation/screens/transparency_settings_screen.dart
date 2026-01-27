import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sparkle/core/services/user_preferences_service.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

part 'transparency_settings_screen.g.dart';

/// Transparency Settings Screen
/// 透明模式设置屏幕
class TransparencySettingsScreen extends ConsumerWidget {
  const TransparencySettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final preferences = ref.watch(transparencyPreferencesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('透明模式设置'),
      ),
      body: preferences.when(
        data: (prefs) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Global toggle
            Card(
              child: SwitchListTile(
                title: const Text('启用透明模式'),
                subtitle: Text(
                  '显示AI处理步骤、Agent切换和Token使用情况',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                value: prefs.enabled,
                onChanged: (value) {
                  ref.read(transparencyPreferencesProvider.notifier).setEnabled(value);
                },
              ),
            ),
            const SizedBox(height: 16),

            // Detailed options
            if (prefs.enabled) ...[
              Text(
                '显示选项',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
              ),
              const SizedBox(height: 8),
              Card(
                child: Column(
                  children: [
                    SwitchListTile(
                      title: const Text('Token使用情况'),
                      subtitle: Text(
                        '显示每次对话的Token消耗和成本估算',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      value: prefs.showTokenUsage,
                      onChanged: (value) {
                        ref.read(transparencyPreferencesProvider.notifier).setShowTokenUsage(value);
                      },
                    ),
                    const Divider(height: 1),
                    SwitchListTile(
                      title: const Text('Agent切换'),
                      subtitle: Text(
                        '显示不同Agent之间的切换过程',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      value: prefs.showAgentSwitching,
                      onChanged: (value) {
                        ref.read(transparencyPreferencesProvider.notifier).setShowAgentSwitching(value);
                      },
                    ),
                    const Divider(height: 1),
                    SwitchListTile(
                      title: const Text('推理步骤'),
                      subtitle: Text(
                        '显示LLM的详细推理过程',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      value: prefs.showReasoningSteps,
                      onChanged: (value) {
                        ref.read(transparencyPreferencesProvider.notifier).setShowReasoningSteps(value);
                      },
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // Performance warning
              Card(
                color: Colors.orange.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(
                        Icons.info_outline,
                        color: Colors.orange.shade700,
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          '启用详细选项可能会略微增加响应延迟',
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: Colors.orange.shade900,
                              ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text(
                '加载设置失败',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                error.toString(),
                style: Theme.of(context).textTheme.bodyMedium,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Transparency preferences model
class TransparencyPreferences {
  const TransparencyPreferences({
    required this.enabled,
    required this.showTokenUsage,
    required this.showAgentSwitching,
    required this.showReasoningSteps,
  });

  final bool enabled;
  final bool showTokenUsage;
  final bool showAgentSwitching;
  final bool showReasoningSteps;

  factory TransparencyPreferences.fromJson(Map<String, dynamic> json) {
    return TransparencyPreferences(
      enabled: json['enabled'] ?? false,
      showTokenUsage: json['showTokenUsage'] ?? true,
      showAgentSwitching: json['showAgentSwitching'] ?? true,
      showReasoningSteps: json['showReasoningSteps'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'enabled': enabled,
      'showTokenUsage': showTokenUsage,
      'showAgentSwitching': showAgentSwitching,
      'showReasoningSteps': showReasoningSteps,
    };
  }

  TransparencyPreferences copyWith({
    bool? enabled,
    bool? showTokenUsage,
    bool? showAgentSwitching,
    bool? showReasoningSteps,
  }) {
    return TransparencyPreferences(
      enabled: enabled ?? this.enabled,
      showTokenUsage: showTokenUsage ?? this.showTokenUsage,
      showAgentSwitching: showAgentSwitching ?? this.showAgentSwitching,
      showReasoningSteps: showReasoningSteps ?? this.showReasoningSteps,
    );
  }
}

/// Provider for transparency preferences
@riverpod
Future<TransparencyPreferences> transparencyPreferences(Ref ref) async {
  final service = ref.watch(userPreferencesServiceProvider);
  final prefs = await service.getPreferences();

  final transparencyPrefs = prefs['transparency'] as Map<String, dynamic>?;

  if (transparencyPrefs != null) {
    return TransparencyPreferences.fromJson(transparencyPrefs);
  }

  // Default preferences
  return const TransparencyPreferences(
    enabled: false,
    showTokenUsage: true,
    showAgentSwitching: true,
    showReasoningSteps: true,
  );
}

/// Notifier for transparency preferences
@riverpod
class TransparencyPreferencesNotifier extends _$TransparencyPreferencesNotifier {
  Future<void> _updatePreferences(TransparencyPreferences prefs) async {
    state = await AsyncValue.data(prefs);

    final service = ref.read(userPreferencesServiceProvider);
    await service.updatePreferences({
      'transparency': prefs.toJson(),
    });
  }

  Future<void> setEnabled(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: false,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
        );
    await _updatePreferences(current.copyWith(enabled: value));
  }

  Future<void> setShowTokenUsage(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: false,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
        );
    await _updatePreferences(current.copyWith(showTokenUsage: value));
  }

  Future<void> setShowAgentSwitching(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: false,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
        );
    await _updatePreferences(current.copyWith(showAgentSwitching: value));
  }

  Future<void> setShowReasoningSteps(bool value) async {
    final current = state.valueOrNull ??
        const TransparencyPreferences(
          enabled: false,
          showTokenUsage: true,
          showAgentSwitching: true,
          showReasoningSteps: true,
        );
    await _updatePreferences(current.copyWith(showReasoningSteps: value));
  }

  @override
  Future<TransparencyPreferences> build() async {
    final service = ref.watch(userPreferencesServiceProvider);
    final prefs = await service.getPreferences();

    final transparencyPrefs = prefs['transparency'] as Map<String, dynamic>?;

    if (transparencyPrefs != null) {
      return TransparencyPreferences.fromJson(transparencyPrefs);
    }

    return const TransparencyPreferences(
      enabled: false,
      showTokenUsage: true,
      showAgentSwitching: true,
      showReasoningSteps: true,
    );
  }
}
